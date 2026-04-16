"""API endpoints for OHLCV price history and indicator time-series.

Endpoints:
- GET /api/prices/{symbol} — OHLCV price history for candlestick charts (DASH-02)
- GET /api/prices/{symbol}/indicators — Technical indicator time-series for chart overlays (DASH-02)
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.price_repo import PriceRepository

router = APIRouter(prefix="/api")


@router.get("/prices/{symbol}")
async def get_price_history(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Z0-9]+$"),
    days: int = Query(default=365, ge=30, le=730),
    session: AsyncSession = Depends(get_session),
):
    """Get OHLCV price history for charting.

    Returns time-series data for lightweight-charts candlestick rendering.
    Per T-06-02: symbol validated with regex pattern.
    """
    repo = PriceRepository(session)
    start_date = date.today() - timedelta(days=days)
    prices = await repo.get_prices(symbol.upper(), start_date=start_date)
    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
    return {
        "symbol": symbol.upper(),
        "count": len(prices),
        "prices": [
            {
                "time": str(p.date),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ],
    }


@router.get("/prices/{symbol}/indicators")
async def get_indicator_history(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Z0-9]+$"),
    days: int = Query(default=365, ge=30, le=730),
    session: AsyncSession = Depends(get_session),
):
    """Get technical indicator time-series for chart overlays.

    Returns SMA, EMA, BB, MACD, RSI values aligned with price dates.
    """
    repo = IndicatorRepository(session)
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()
    indicators = await repo.get_by_date_range(symbol.upper(), start_date, end_date)
    if not indicators:
        raise HTTPException(status_code=404, detail=f"No indicator data for {symbol}")
    return {
        "symbol": symbol.upper(),
        "count": len(indicators),
        "indicators": [
            {
                "time": str(ind.date),
                "sma_20": ind.sma_20,
                "sma_50": ind.sma_50,
                "sma_200": ind.sma_200,
                "ema_12": ind.ema_12,
                "ema_26": ind.ema_26,
                "rsi_14": ind.rsi_14,
                "macd": ind.macd,
                "macd_signal": ind.macd_signal,
                "macd_histogram": ind.macd_histogram,
                "bb_upper": ind.bb_upper,
                "bb_middle": ind.bb_middle,
                "bb_lower": ind.bb_lower,
            }
            for ind in indicators
        ],
    }
