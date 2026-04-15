"""Health check endpoint — returns pipeline status and data stats."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.models import PipelineRun, Stock, StockPrice

router = APIRouter()


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Returns system health and latest pipeline run info.

    Response includes:
    - status: 'healthy'
    - stocks: total stock count in DB
    - prices: total price rows in DB
    - last_pipeline_run: latest PipelineRun details or None
    """
    # Latest pipeline run
    latest_run = await session.execute(
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    run = latest_run.scalar_one_or_none()

    # Data counts
    stock_count = await session.execute(
        select(func.count()).select_from(Stock)
    )
    price_count = await session.execute(
        select(func.count()).select_from(StockPrice)
    )

    return {
        "status": "healthy",
        "stocks": stock_count.scalar() or 0,
        "prices": price_count.scalar() or 0,
        "last_pipeline_run": {
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat()
            if run and run.completed_at
            else None,
            "symbols_total": run.symbols_total,
            "symbols_success": run.symbols_success,
            "symbols_failed": run.symbols_failed,
        }
        if run
        else None,
    }
