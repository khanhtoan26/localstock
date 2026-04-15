"""API endpoints for technical and fundamental analysis results.

Endpoints per Research section 9:
- GET /api/analysis/{symbol}/technical — latest technical indicators
- GET /api/analysis/{symbol}/fundamental — latest financial ratios
- GET /api/analysis/{symbol}/trend — trend direction + S/R levels
- POST /api/analysis/run — trigger full analysis run
- GET /api/industry/groups — list industry groups
- GET /api/industry/{group_code}/averages — industry average ratios
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.models import IndustryAverage
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.industry_repo import IndustryRepository
from localstock.db.repositories.ratio_repo import RatioRepository
from localstock.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api")


@router.get("/analysis/{symbol}/technical")
async def get_technical(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get latest technical indicators for a symbol."""
    repo = IndicatorRepository(session)
    indicator = await repo.get_latest(symbol.upper())
    if not indicator:
        raise HTTPException(status_code=404, detail=f"No technical data for {symbol}")
    return {
        "symbol": indicator.symbol,
        "date": str(indicator.date),
        "sma_20": indicator.sma_20,
        "sma_50": indicator.sma_50,
        "sma_200": indicator.sma_200,
        "ema_12": indicator.ema_12,
        "ema_26": indicator.ema_26,
        "rsi_14": indicator.rsi_14,
        "macd": indicator.macd,
        "macd_signal": indicator.macd_signal,
        "macd_histogram": indicator.macd_histogram,
        "bb_upper": indicator.bb_upper,
        "bb_middle": indicator.bb_middle,
        "bb_lower": indicator.bb_lower,
        "stoch_k": indicator.stoch_k,
        "stoch_d": indicator.stoch_d,
        "adx": indicator.adx,
        "obv": indicator.obv,
        "avg_volume_20": indicator.avg_volume_20,
        "relative_volume": indicator.relative_volume,
        "volume_trend": indicator.volume_trend,
    }


@router.get("/analysis/{symbol}/fundamental")
async def get_fundamental(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get latest financial ratios for a symbol."""
    repo = RatioRepository(session)
    ratio = await repo.get_latest(symbol.upper())
    if not ratio:
        raise HTTPException(status_code=404, detail=f"No fundamental data for {symbol}")
    return {
        "symbol": ratio.symbol,
        "year": ratio.year,
        "period": ratio.period,
        "pe_ratio": ratio.pe_ratio,
        "pb_ratio": ratio.pb_ratio,
        "eps": ratio.eps,
        "roe": ratio.roe,
        "roa": ratio.roa,
        "de_ratio": ratio.de_ratio,
        "revenue_qoq": ratio.revenue_qoq,
        "revenue_yoy": ratio.revenue_yoy,
        "profit_qoq": ratio.profit_qoq,
        "profit_yoy": ratio.profit_yoy,
        "market_cap": ratio.market_cap,
        "current_price": ratio.current_price,
    }


@router.get("/analysis/{symbol}/trend")
async def get_trend(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get trend direction and support/resistance for a symbol."""
    repo = IndicatorRepository(session)
    indicator = await repo.get_latest(symbol.upper())
    if not indicator:
        raise HTTPException(status_code=404, detail=f"No trend data for {symbol}")
    return {
        "symbol": indicator.symbol,
        "date": str(indicator.date),
        "trend_direction": indicator.trend_direction,
        "trend_strength": indicator.trend_strength,
        "pivot_point": indicator.pivot_point,
        "support_1": indicator.support_1,
        "support_2": indicator.support_2,
        "resistance_1": indicator.resistance_1,
        "resistance_2": indicator.resistance_2,
        "nearest_support": indicator.nearest_support,
        "nearest_resistance": indicator.nearest_resistance,
    }


@router.post("/analysis/run")
async def trigger_analysis(
    session: AsyncSession = Depends(get_session),
):
    """Trigger full analysis run for all HOSE stocks.

    This is a long-running operation — may take several minutes for ~400 stocks.
    """
    service = AnalysisService(session)
    result = await service.run_full()
    return result


@router.get("/industry/groups")
async def list_industry_groups(
    session: AsyncSession = Depends(get_session),
):
    """List all Vietnamese industry groups."""
    repo = IndustryRepository(session)
    groups = await repo.get_all_groups()
    return [
        {
            "group_code": g.group_code,
            "group_name_vi": g.group_name_vi,
            "group_name_en": g.group_name_en,
        }
        for g in groups
    ]


@router.get("/industry/{group_code}/averages")
async def get_industry_averages(
    group_code: str,
    year: int | None = None,
    period: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get industry average ratios for a specific group.

    If year/period not specified, returns the latest available.
    """
    repo = IndustryRepository(session)
    if year and period:
        avg = await repo.get_averages(group_code.upper(), year, period)
    else:
        # Get latest — query ordered by year desc, period desc
        stmt = (
            select(IndustryAverage)
            .where(IndustryAverage.group_code == group_code.upper())
            .order_by(IndustryAverage.year.desc(), IndustryAverage.period.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        avg = result.scalar_one_or_none()

    if not avg:
        raise HTTPException(
            status_code=404,
            detail=f"No averages for group {group_code}",
        )
    return {
        "group_code": avg.group_code,
        "year": avg.year,
        "period": avg.period,
        "avg_pe": avg.avg_pe,
        "avg_pb": avg.avg_pb,
        "avg_roe": avg.avg_roe,
        "avg_roa": avg.avg_roa,
        "avg_de": avg.avg_de,
        "avg_revenue_growth_yoy": avg.avg_revenue_growth_yoy,
        "avg_profit_growth_yoy": avg.avg_profit_growth_yoy,
        "stock_count": avg.stock_count,
    }
