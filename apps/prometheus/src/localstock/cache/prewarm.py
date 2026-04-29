"""Phase 26 / D-05 — pre-warm hot keys at end of run_daily_pipeline.

Q-3 — pre-warm goes through the SAME ``get_or_compute`` choke point
that routes use. No direct cache writes; no double-compute hazard.
The single-flight lock collapses pre-warm + concurrent first-user-
request into one computation (P-6 belt-and-suspenders: invalidate→
prewarm has no awaitable gap on the cache keys themselves).

Failure semantics (P-5): every error is caught + counted via
``cache_prewarm_errors_total{cache_name=...}`` + logged, NEVER
re-raised. The caller (``AutomationService.run_daily_pipeline``)
treats pre-warm as best-effort.
"""
from __future__ import annotations

from typing import Any, AsyncContextManager, Callable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.cache import get_or_compute, resolve_latest_run_id
from localstock.observability.metrics import get_metrics


def _inc_prewarm_error(cache_name: str) -> None:
    """Increment the prewarm-errors counter, swallowing metric failures."""
    try:
        get_metrics()["cache_prewarm_errors_total"].labels(
            cache_name=cache_name
        ).inc()
    except Exception:  # pragma: no cover — defensive only
        pass


async def prewarm_hot_keys(
    session_factory: Callable[[], AsyncContextManager[AsyncSession]],
    *,
    ranking_limit: int = 50,
) -> None:
    """Pre-warm /scores/top (top ``ranking_limit``) and /market/summary.

    Calls go through ``get_or_compute`` so a concurrent first-user
    request hitting the same key collapses into the same single-flight
    compute (Q-3, P-6).

    No-op + warning when no completed pipeline run exists yet — the
    cache keys are versioned by ``run_id`` and there is nothing to warm
    against.
    """
    try:
        run_id = await resolve_latest_run_id(session_factory)
    except Exception:
        logger.exception("automation.cache.prewarm_failed", phase="resolve_run_id")
        _inc_prewarm_error("pipeline:latest_run_id")
        return

    if run_id is None:
        logger.warning("cache.prewarm.skipped", reason="no_completed_run")
        return

    # --- /scores/top -----------------------------------------------------
    try:
        # Local import keeps top-level import graph clean (avoid pulling
        # ScoringService at module load time).
        from localstock.services.scoring_service import ScoringService

        async def _compute_ranking() -> dict[str, Any]:
            async with session_factory() as session:
                service = ScoringService(session)
                stocks = await service.get_top_stocks(limit=ranking_limit)
                if not stocks:
                    return {
                        "stocks": [],
                        "count": 0,
                        "message": "No scores computed yet. Run POST /api/scores/run first.",
                    }
                return {"stocks": stocks, "count": len(stocks)}

        await get_or_compute(
            namespace="scores:ranking",
            key=f"limit={ranking_limit}:run={run_id}",
            compute_fn=_compute_ranking,
        )
        logger.info(
            "cache.prewarm.ok",
            namespace="scores:ranking",
            key=f"limit={ranking_limit}:run={run_id}",
        )
    except Exception:
        logger.exception(
            "automation.cache.prewarm_failed", namespace="scores:ranking"
        )
        _inc_prewarm_error("scores:ranking")

    # --- /market/summary -------------------------------------------------
    try:
        # 26-04 extracted the route's compute body into a module-level
        # helper so prewarm can mirror it exactly without duplicating
        # the SQL aggregation logic.
        from localstock.api.routes.market import build_market_summary

        async def _compute_market() -> Any:
            async with session_factory() as session:
                return await build_market_summary(session)

        await get_or_compute(
            namespace="market:summary",
            key=f"run={run_id}",
            compute_fn=_compute_market,
        )
        logger.info(
            "cache.prewarm.ok",
            namespace="market:summary",
            key=f"run={run_id}",
        )
    except Exception:
        logger.exception(
            "automation.cache.prewarm_failed", namespace="market:summary"
        )
        _inc_prewarm_error("market:summary")

    logger.info("cache.prewarm.completed", run_id=run_id)
