"""Repository for technical_indicators table with bulk upsert."""

from datetime import date

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import TechnicalIndicator


class IndicatorRepository:
    """Repository for TechnicalIndicator model operations.

    Provides bulk upsert for computed indicators and
    query methods for analysis results.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Bulk upsert technical indicator rows.

        Uses PostgreSQL INSERT ... ON CONFLICT (symbol, date) DO UPDATE.

        Args:
            rows: List of dicts with keys matching TechnicalIndicator columns.
                  Required keys: symbol, date. All indicator columns optional.

        Returns:
            Count of upserted rows.
        """
        if not rows:
            return 0

        stmt = pg_insert(TechnicalIndicator).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in TechnicalIndicator.__table__.columns
            if col.name not in ("id", "symbol", "date")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_technical_indicator",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Upserted {len(rows)} technical indicator rows")
        return len(rows)

    async def get_latest(self, symbol: str) -> TechnicalIndicator | None:
        """Get the most recent indicator row for a symbol."""
        stmt = (
            select(TechnicalIndicator)
            .where(TechnicalIndicator.symbol == symbol)
            .order_by(TechnicalIndicator.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date_range(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[TechnicalIndicator]:
        """Fetch indicator rows for a symbol within a date range."""
        stmt = (
            select(TechnicalIndicator)
            .where(
                TechnicalIndicator.symbol == symbol,
                TechnicalIndicator.date >= start_date,
                TechnicalIndicator.date <= end_date,
            )
            .order_by(TechnicalIndicator.date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_symbols_with_indicators(self) -> list[str]:
        """Return list of symbols that have computed indicators."""
        stmt = select(TechnicalIndicator.symbol).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_symbol(self, symbol: str) -> int:
        """Count indicator rows for a symbol."""
        stmt = select(func.count()).where(TechnicalIndicator.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
