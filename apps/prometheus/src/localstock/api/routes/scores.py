"""API endpoints for stock scoring and rankings.

Endpoints:
- GET /api/scores/top — Top-ranked stocks with grades and breakdown (SCOR-03)
- GET /api/scores/{symbol} — Latest composite score for a specific stock
- POST /api/scores/run — Trigger full scoring pipeline

Phase 26 / CACHE-01:
- /scores/top is wrapped in ``get_or_compute(namespace='scores:ranking', ...)``
  with version key ``limit={limit}:run={pipeline_run_id}`` (CONTEXT D-01,
  TTL D-02 = 24h via registry).
- ``_scoring_lock`` (legacy module-level lock) was removed: ``get_or_compute``
  provides per-key single-flight via WeakValueDictionary (P-2 hazard fix).
- ``/scores/run`` keeps a *separate* run-prevention lock for the long-running
  pipeline trigger; that lock has nothing to do with read-path caching.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.cache import get_or_compute
from localstock.db.database import get_session
from localstock.db.models import PipelineRun
from localstock.services.scoring_service import ScoringService

router = APIRouter(prefix="/api")
# Pipeline-trigger guard for /scores/run only (NOT the read path).
_pipeline_run_lock = asyncio.Lock()


async def resolve_latest_run_id(session: AsyncSession) -> int | None:
    """Return the id of the latest ``status='completed'`` pipeline run.

    Phase 26 fallback shim for the helper that 26-03 will eventually
    expose as ``localstock.cache.resolve_latest_run_id``. Cached for 5s
    under namespace ``pipeline:latest_run_id`` (CONTEXT D-02, key
    ``current``) so per-request overhead stays bounded.

    NB: the canonical 26-03 signature takes a ``session_factory``. This
    fallback intentionally takes the *current* request session instead —
    that avoids touching the module-singleton engine, which under
    pytest-asyncio's function-scoped event loops becomes bound to a
    closed loop after the first DB-using test and breaks subsequent
    direct route-call tests with ``RuntimeError: Event loop is closed``
    (observed in tests/test_market_route.py::test_endpoint_calls_repo
    with the full suite). When 26-03 lands, callers can either keep
    using this shim or switch to the canonical factory-based helper.
    """

    async def _compute() -> int | None:
        stmt = (
            select(PipelineRun.id)
            .where(PipelineRun.status == "completed")
            .order_by(PipelineRun.completed_at.desc().nulls_last())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    return await get_or_compute(
        namespace="pipeline:latest_run_id",
        key="current",
        compute_fn=_compute,
    )


@router.get("/scores/top")
async def get_top_scores(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get top-ranked stocks by composite score (SCOR-03; cached, CACHE-01).

    Cache key composition (CONTEXT D-01):
        namespace = "scores:ranking"
        key       = f"limit={limit}:run={pipeline_run_id}"

    Cache miss runs the scoring query; subsequent calls in the 24h TTL
    window (and same pipeline_run_id) return < 50ms p95 (ROADMAP SC #1).

    When no completed pipeline run exists yet (``run_id is None``), the
    handler bypasses the cache and computes directly — refusing to
    poison a versioned key with the empty/'no scores yet' shape
    (T-26-04-04).
    """
    run_id = await resolve_latest_run_id(session)

    async def _compute():
        service = ScoringService(session)
        stocks = await service.get_top_stocks(limit=limit)
        if not stocks:
            return {
                "stocks": [],
                "count": 0,
                "message": "No scores computed yet. Run POST /api/scores/run first.",
            }
        return {"stocks": stocks, "count": len(stocks)}

    if run_id is None:
        # Bypass cache entirely — empty shape must NOT be cached under a
        # versioned key (T-26-04-04). The cache_outcome_var stays at
        # whatever the run_id resolution set it to (likely 'miss' on
        # first call, 'hit' afterwards) — that is acceptable: the
        # X-Cache header still reflects whether the request touched the
        # cache layer, just not the scoring cache specifically.
        return await _compute()

    return await get_or_compute(
        namespace="scores:ranking",
        key=f"limit={limit}:run={run_id}",
        compute_fn=_compute,
    )


@router.get("/scores/{symbol}")
async def get_score(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get latest composite score for a specific stock."""
    from localstock.db.repositories.score_repo import ScoreRepository
    repo = ScoreRepository(session)
    score = await repo.get_latest(symbol.upper())
    if not score:
        raise HTTPException(
            status_code=404,
            detail=f"No composite score for {symbol}. Run scoring pipeline first.",
        )
    return {
        "symbol": score.symbol,
        "date": str(score.date),
        "total_score": round(score.total_score, 1),
        "grade": score.grade,
        "rank": score.rank,
        "technical_score": round(score.technical_score, 1) if score.technical_score else None,
        "fundamental_score": round(score.fundamental_score, 1) if score.fundamental_score else None,
        "sentiment_score": round(score.sentiment_score, 1) if score.sentiment_score else None,
        "macro_score": round(score.macro_score, 1) if score.macro_score else None,
        "dimensions_used": score.dimensions_used,
        "weights": score.weights_json,
    }


@router.post("/scores/run")
async def trigger_scoring(
    session: AsyncSession = Depends(get_session),
):
    """Trigger full scoring pipeline for all HOSE stocks.

    Steps: normalize dimensions → compute composite → assign ranks → store.
    This is a long-running operation.
    """
    if _pipeline_run_lock.locked():
        raise HTTPException(status_code=409, detail="Scoring already in progress")
    async with _pipeline_run_lock:
        service = ScoringService(session)
        result = await service.run_full()
        return result
