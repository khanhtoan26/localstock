"""API endpoints for market summary data (Phase 17 — MKT-04)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.models import StockPrice
from localstock.db.repositories.price_repo import PriceRepository

router = APIRouter(prefix="/api")


class VnindexData(BaseModel):
    """VN-Index value and day change percentage."""

    value: float | None
    change_pct: float | None


class MarketSummaryResponse(BaseModel):
    """Market summary data for the most recent trading day.

    All nullable fields return None when data is unavailable
    (e.g., fresh install with no prices yet).
    """

    vnindex: VnindexData | None
    total_volume: int | None
    total_volume_change_pct: float | None
    advances: int
    declines: int
    breadth: float | None
    as_of: str | None


@router.get("/market/summary", response_model=MarketSummaryResponse)
async def get_market_summary(
    session: AsyncSession = Depends(get_session),
) -> MarketSummaryResponse:
    """Get market summary: VN-Index, total volume, advances, declines, breadth.

    Data comes from the daily crawl pipeline. The as_of field indicates
    which trading day the data reflects (may lag by 1 day on weekends/holidays).

    Returns structured nulls when no price data is available — never raises 404
    or 500 for missing data. This allows the frontend to show graceful fallback.
    """
    repo = PriceRepository(session)

    # --- VN-Index data ---
    vnindex_data: VnindexData | None = None
    latest_vnindex = await repo.get_latest("VNINDEX")

    if latest_vnindex is not None:
        # Get previous VNINDEX row for % change computation
        prev_stmt = (
            select(StockPrice)
            .where(StockPrice.symbol == "VNINDEX")
            .order_by(StockPrice.date.desc())
            .offset(1)
            .limit(1)
        )
        prev_result = await session.execute(prev_stmt)
        prev_vnindex = prev_result.scalar_one_or_none()

        change_pct: float | None = None
        if prev_vnindex is not None and prev_vnindex.close and prev_vnindex.close != 0:
            change_pct = (latest_vnindex.close - prev_vnindex.close) / prev_vnindex.close * 100

        vnindex_data = VnindexData(
            value=latest_vnindex.close,
            change_pct=change_pct,
        )

    # --- Advances/declines/volume ---
    aggregate = await repo.get_market_aggregate()

    advances: int = aggregate["advances"]
    declines: int = aggregate["declines"]
    total_volume: int | None = aggregate["total_volume"]  # repo returns int or None
    total_volume_change_pct: float | None = aggregate["total_volume_change_pct"]
    as_of_date = aggregate["as_of"]

    # --- Market breadth: advances / (advances + declines) ---
    breadth: float | None = None
    total_moving = advances + declines
    if total_moving > 0:
        breadth = advances / total_moving * 100

    return MarketSummaryResponse(
        vnindex=vnindex_data,
        total_volume=total_volume,
        total_volume_change_pct=total_volume_change_pct,
        advances=advances,
        declines=declines,
        breadth=breadth,
        as_of=as_of_date.isoformat() if as_of_date else None,
    )
