"""Price repository — CRUD operations for the stock_prices table."""

from datetime import date

import pandas as pd
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import StockPrice

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
