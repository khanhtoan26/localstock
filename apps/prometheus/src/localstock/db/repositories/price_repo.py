"""Price repository — CRUD operations for the stock_prices table."""

from datetime import date

import pandas as pd
from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import StockPrice, TechnicalIndicator

# Required columns in the OHLCV DataFrame (vnstock output format)
REQUIRED_COLUMNS = {"time", "open", "high", "low", "close", "volume"}


class PriceRepository:
    """Repository for StockPrice model operations.

    Provides upsert semantics for OHLCV price data and
    query methods for incremental crawling support.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_prices(self, symbol: str, prices_df: pd.DataFrame) -> int:
        """Upsert OHLCV prices for a symbol.

        Expected DataFrame columns (vnstock Quote.history() output):
            time, open, high, low, close, volume.

        Column 'time' maps to 'date' in the StockPrice model.
        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE on (symbol, date).

        Args:
            symbol: Stock ticker symbol (e.g., 'ACB').
            prices_df: DataFrame with OHLCV data.

        Returns:
            Count of upserted rows.

        Raises:
            ValueError: If required columns are missing.
        """
        if prices_df is None or prices_df.empty:
            return 0

        # Validate required columns
        missing = REQUIRED_COLUMNS - set(prices_df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Build rows for bulk upsert
        rows = []
        for _, row in prices_df.iterrows():
            # Validate essential fields (T-01-04: reject null symbol/date/close)
            price_date = row["time"]
            if isinstance(price_date, str):
                price_date = date.fromisoformat(price_date)

            close_val = float(row["close"])
            volume_val = int(row["volume"])

            # T-01-04: log anomalies
            if close_val < 0:
                logger.warning(f"Negative close price for {symbol} on {price_date}: {close_val}")
            if volume_val == 0:
                logger.warning(f"Zero volume for {symbol} on {price_date}")

            rows.append(
                {
                    "symbol": symbol,
                    "date": price_date,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": close_val,
                    "volume": volume_val,
                    "adj_close": None,
                    "adj_factor": 1.0,
                }
            )

        stmt = pg_insert(StockPrice).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_stock_price",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Upserted {len(rows)} price rows for {symbol}")
        return len(rows)

    async def get_latest_date(self, symbol: str) -> date | None:
        """Return the most recent date for a symbol, or None if no data.

        Used to determine incremental crawl start date.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Most recent date in stock_prices for this symbol, or None.
        """
        stmt = select(func.max(StockPrice.date)).where(StockPrice.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_latest(self, symbol: str) -> StockPrice | None:
        """Return the most recent price row for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'VNM').

        Returns:
            Latest StockPrice row or None if no data.
        """
        stmt = (
            select(StockPrice)
            .where(StockPrice.symbol == symbol)
            .order_by(StockPrice.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_prices(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[StockPrice]:
        """Fetch prices for a symbol within an optional date range.

        Args:
            symbol: Stock ticker symbol.
            start_date: Optional start date filter (inclusive).
            end_date: Optional end date filter (inclusive).

        Returns:
            List of StockPrice model instances ordered by date.
        """
        stmt = select(StockPrice).where(StockPrice.symbol == symbol)

        if start_date is not None:
            stmt = stmt.where(StockPrice.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(StockPrice.date <= end_date)

        stmt = stmt.order_by(StockPrice.date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_market_aggregate(self) -> dict:
        """Compute advances/declines/volume for the most recent trading day.

        Uses a two-date self-join on stock_prices to compare today's close
        vs the previous trading day's close. Never uses date.today() —
        always derives dates from MAX(date) in the DB.

        Excludes VNINDEX (symbol='VNINDEX') from all aggregate counts.

        Returns:
            dict with keys:
                as_of: date | None          — most recent trading day
                advances: int               — stocks with close > prev_close
                declines: int               — stocks with close < prev_close
                flat: int                   — stocks with close == prev_close
                total_volume: int           — sum of volume on latest date
                total_volume_change_pct: float | None
                                            — vs 20-day avg, None if unavailable
        """
        # Step 1: Find the two most recent distinct dates across all tracked stocks
        # (excluding VNINDEX — it's an index, not a traded stock)
        dates_stmt = (
            select(StockPrice.date)
            .where(StockPrice.symbol != "VNINDEX")
            .distinct()
            .order_by(StockPrice.date.desc())
            .limit(2)
        )
        dates_result = await self.session.execute(dates_stmt)
        dates = list(dates_result.scalars().all())

        if not dates:
            return {
                "as_of": None,
                "advances": 0,
                "declines": 0,
                "flat": 0,
                "total_volume": 0,
                "total_volume_change_pct": None,
            }

        latest_date = dates[0]

        # Step 2: Total volume for the latest date (excluding VNINDEX)
        vol_stmt = select(func.coalesce(func.sum(StockPrice.volume), 0)).where(
            StockPrice.date == latest_date,
            StockPrice.symbol != "VNINDEX",
        )
        vol_result = await self.session.execute(vol_stmt)
        total_volume = vol_result.scalar() or 0

        # Step 3: 20-day average volume from TechnicalIndicator (latest date)
        # Sum of avg_volume_20 across all stocks on the latest indicator date
        avg_vol_stmt = select(func.sum(TechnicalIndicator.avg_volume_20)).where(
            TechnicalIndicator.date == latest_date,
            TechnicalIndicator.symbol != "VNINDEX",
            TechnicalIndicator.avg_volume_20.is_not(None),
        )
        avg_vol_result = await self.session.execute(avg_vol_stmt)
        avg_vol_20d = avg_vol_result.scalar()

        total_volume_change_pct: float | None = None
        if avg_vol_20d and avg_vol_20d > 0:
            total_volume_change_pct = (total_volume - avg_vol_20d) / avg_vol_20d * 100

        # Step 4: Advances/declines — requires 2 trading days
        if len(dates) < 2:
            # Only 1 day of data — can't compute direction
            count_stmt = select(func.count(StockPrice.symbol)).where(
                StockPrice.date == latest_date,
                StockPrice.symbol != "VNINDEX",
            )
            count_result = await self.session.execute(count_stmt)
            total_stocks = count_result.scalar() or 0
            return {
                "as_of": latest_date,
                "advances": 0,
                "declines": 0,
                "flat": total_stocks,
                "total_volume": int(total_volume),
                "total_volume_change_pct": total_volume_change_pct,
            }

        prev_date = dates[1]

        # Self-join: today's prices vs previous day's prices
        today = StockPrice.__table__.alias("today")
        prev = StockPrice.__table__.alias("prev")

        direction_stmt = (
            select(
                func.count(
                    case((today.c.close > prev.c.close, 1), else_=None)
                ).label("advances"),
                func.count(
                    case((today.c.close < prev.c.close, 1), else_=None)
                ).label("declines"),
                func.count(
                    case((today.c.close == prev.c.close, 1), else_=None)
                ).label("flat"),
            )
            .select_from(
                today.join(prev, (today.c.symbol == prev.c.symbol))
            )
            .where(
                today.c.date == latest_date,
                prev.c.date == prev_date,
                today.c.symbol != "VNINDEX",
            )
        )

        direction_result = await self.session.execute(direction_stmt)
        row = direction_result.one()

        return {
            "as_of": latest_date,
            "advances": int(row.advances),
            "declines": int(row.declines),
            "flat": int(row.flat),
            "total_volume": int(total_volume),
            "total_volume_change_pct": total_volume_change_pct,
        }
