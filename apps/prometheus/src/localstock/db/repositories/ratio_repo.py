"""Repository for financial_ratios table with upsert."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import FinancialRatio


class RatioRepository:
    """Repository for FinancialRatio model operations.

    Provides upsert for computed financial ratios and
    query methods for analysis results.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_ratio(self, ratio_data: dict) -> None:
        """Upsert a single financial ratio row.

        Uses ON CONFLICT (symbol, year, period) DO UPDATE.

        Args:
            ratio_data: Dict with keys matching FinancialRatio columns.
                        Required keys: symbol, year, period.
        """
        stmt = pg_insert(FinancialRatio).values(**ratio_data)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in FinancialRatio.__table__.columns
            if col.name not in ("id", "symbol", "year", "period")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_financial_ratio",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Bulk upsert financial ratio rows.

        Args:
            rows: List of dicts with FinancialRatio column values.

        Returns:
            Count of upserted rows.
        """
        if not rows:
            return 0

        stmt = pg_insert(FinancialRatio).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in FinancialRatio.__table__.columns
            if col.name not in ("id", "symbol", "year", "period")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_financial_ratio",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info("ratio_repo.bulk_upserted", rows=len(rows))
        return len(rows)

    async def get_latest(self, symbol: str) -> FinancialRatio | None:
        """Get the most recent ratio for a symbol (by year, period desc)."""
        stmt = (
            select(FinancialRatio)
            .where(FinancialRatio.symbol == symbol)
            .order_by(FinancialRatio.year.desc(), FinancialRatio.period.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_period(
        self, symbol: str, year: int, period: str
    ) -> FinancialRatio | None:
        """Get ratio for a specific symbol, year, period."""
        stmt = select(FinancialRatio).where(
            FinancialRatio.symbol == symbol,
            FinancialRatio.year == year,
            FinancialRatio.period == period,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_symbol(self, symbol: str) -> list[FinancialRatio]:
        """Get all ratios for a symbol ordered by year and period."""
        stmt = (
            select(FinancialRatio)
            .where(FinancialRatio.symbol == symbol)
            .order_by(FinancialRatio.year, FinancialRatio.period)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
