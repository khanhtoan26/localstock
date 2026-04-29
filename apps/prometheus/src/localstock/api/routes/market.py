"""API endpoints for market summary data (Phase 17 — MKT-04).

Phase 26 / CACHE-01:
- ``/market/summary`` is wrapped in
  ``get_or_compute(namespace='market:summary', key='run={run_id}', ...)``
  with TTL 1h (CONTEXT D-02 via registry).
- The data-build logic lives in module-level ``build_market_summary``
  so 26-05 pre-warm can call the same compute path and collapse with
  user requests via single-flight (Q-3, P-6).
- When no completed pipeline run exists yet, the handler bypasses the
  cache (T-26-04-04 — don't poison a versioned key with empty data).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.api.routes.scores import resolve_latest_run_id
from localstock.cache import get_or_compute
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


async def build_market_summary(session: AsyncSession) -> MarketSummaryResponse:
    """Build the market summary response from the given session.

    Pure data-build helper — no caching, no run_id resolution. The
    route handler wraps this in ``get_or_compute(...)``; pre-warm
    (cache/prewarm.py, 26-05) imports and reuses it so that a
    single-flight lock collapses pre-warm + first-user-request into
    one computation (RESEARCH §1 Q-3, P-6).
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
    total_volume: int | None = aggregate["total_volume"]
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


@router.get("/market/summary", response_model=MarketSummaryResponse)
async def get_market_summary(
    session: AsyncSession = Depends(get_session),
) -> MarketSummaryResponse:
    """Get market summary: VN-Index, total volume, advances, declines, breadth.

    Data comes from the daily crawl pipeline. The as_of field indicates
    which trading day the data reflects (may lag by 1 day on weekends/holidays).

    Returns structured nulls when no price data is available — never raises 404
    or 500 for missing data. This allows the frontend to show graceful fallback.

    Phase 26 / CACHE-01: response is cached per ``pipeline_run_id`` for
    1h (D-02). When no completed run exists yet, cache is bypassed
    (T-26-04-04).
    """
    run_id = await resolve_latest_run_id(session)

    async def _compute() -> MarketSummaryResponse:
        return await build_market_summary(session)

    if run_id is None:
        return await _compute()

    return await get_or_compute(
        namespace="market:summary",
        key=f"run={run_id}",
        compute_fn=_compute,
    )
