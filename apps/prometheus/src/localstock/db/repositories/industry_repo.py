"""Repository for industry_groups, stock_industry_mapping, and industry_averages tables."""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import IndustryAverage, IndustryGroup, StockIndustryMapping


class IndustryRepository:
    """Repository for industry group tables.

    Manages VN-specific industry groups, stock-to-group mapping,
    and precomputed industry average ratios.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Industry Groups ---

    async def upsert_groups(self, groups: list[dict]) -> int:
        """Upsert industry group definitions.

        Args:
            groups: List of dicts with keys: group_code, group_name_vi,
                    group_name_en (optional), description (optional).

        Returns:
            Count of upserted groups.
        """
        if not groups:
            return 0

        stmt = pg_insert(IndustryGroup).values(groups)
        stmt = stmt.on_conflict_do_update(
            index_elements=["group_code"],
            set_={
                "group_name_vi": stmt.excluded.group_name_vi,
                "group_name_en": stmt.excluded.group_name_en,
                "description": stmt.excluded.description,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info("industry_repo.groups_upserted", rows=len(groups))
        return len(groups)

    async def get_all_groups(self) -> list[IndustryGroup]:
        """Return all industry groups."""
        stmt = select(IndustryGroup).order_by(IndustryGroup.group_code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # --- Stock-Industry Mapping ---

    async def upsert_mappings(self, mappings: list[dict]) -> int:
        """Upsert stock-to-industry mappings.

        Args:
            mappings: List of dicts with keys: symbol, group_code.

        Returns:
            Count of upserted mappings.
        """
        if not mappings:
            return 0

        rows = [
            {
                "symbol": m["symbol"],
                "group_code": m["group_code"],
                "assigned_at": datetime.now(UTC),
            }
            for m in mappings
        ]
        stmt = pg_insert(StockIndustryMapping).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "group_code": stmt.excluded.group_code,
                "assigned_at": stmt.excluded.assigned_at,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info("industry_repo.mappings_upserted", rows=len(rows))
        return len(rows)

    async def get_symbols_by_group(self, group_code: str) -> list[str]:
        """Return all symbols in a given industry group."""
        stmt = (
            select(StockIndustryMapping.symbol)
            .where(StockIndustryMapping.group_code == group_code)
            .order_by(StockIndustryMapping.symbol)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_group_for_symbol(self, symbol: str) -> str | None:
        """Return the group_code for a symbol, or None if unmapped."""
        stmt = select(StockIndustryMapping.group_code).where(
            StockIndustryMapping.symbol == symbol
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Industry Averages ---

    async def upsert_averages(self, averages: list[dict]) -> int:
        """Upsert industry average ratio rows.

        Args:
            averages: List of dicts with keys matching IndustryAverage columns.

        Returns:
            Count of upserted rows.
        """
        if not averages:
            return 0

        stmt = pg_insert(IndustryAverage).values(averages)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in IndustryAverage.__table__.columns
            if col.name not in ("id", "group_code", "year", "period")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_industry_average",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info("industry_repo.averages_upserted", rows=len(averages))
        return len(averages)

    async def get_averages(
        self, group_code: str, year: int, period: str
    ) -> IndustryAverage | None:
        """Get industry averages for a specific group, year, period."""
        stmt = select(IndustryAverage).where(
            IndustryAverage.group_code == group_code,
            IndustryAverage.year == year,
            IndustryAverage.period == period,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
