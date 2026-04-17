"""API endpoints for stock scoring and rankings.

Endpoints:
- GET /api/scores/top — Top-ranked stocks with grades and breakdown (SCOR-03)
- GET /api/scores/{symbol} — Latest composite score for a specific stock
- POST /api/scores/run — Trigger full scoring pipeline
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.services.scoring_service import ScoringService

router = APIRouter(prefix="/api")
_scoring_lock = asyncio.Lock()


@router.get("/scores/top")
async def get_top_scores(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get top-ranked stocks by composite score.

    Per SCOR-03: Returns ranked list with scores, grades, and per-dimension breakdown.
    """
    service = ScoringService(session)
    stocks = await service.get_top_stocks(limit=limit)
    if not stocks:
        return {"stocks": [], "count": 0, "message": "No scores computed yet. Run POST /api/scores/run first."}
    return {"stocks": stocks, "count": len(stocks)}


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
    if _scoring_lock.locked():
        raise HTTPException(status_code=409, detail="Scoring already in progress")
    async with _scoring_lock:
        service = ScoringService(session)
        result = await service.run_full()
        return result
