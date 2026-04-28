"""Repository for macro_indicators table with bulk upsert."""

from datetime import date as date_type

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import MacroIndicator


class MacroRepository:
    """Repository for MacroIndicator model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert macro indicators. Dedup on (indicator_type, period)."""
        if not rows:
            return 0
        stmt = pg_insert(MacroIndicator).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in MacroIndicator.__table__.columns
            if col.name not in ("id", "indicator_type", "period")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_macro_indicator",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info("macro_repo.bulk_upserted", rows=len(rows))
        return len(rows)

    async def get_latest_by_type(self, indicator_type: str) -> MacroIndicator | None:
        """Get the most recent indicator for a given type."""
        stmt = (
            select(MacroIndicator)
            .where(MacroIndicator.indicator_type == indicator_type)
            .order_by(MacroIndicator.recorded_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_latest(self) -> list[MacroIndicator]:
        """Get the latest row for each distinct indicator_type.

        Uses subquery: max(recorded_at) grouped by indicator_type,
        then joins back to get the full row.
        """
        # Subquery: latest recorded_at per indicator_type
        latest_sub = (
            select(
                MacroIndicator.indicator_type,
                func.max(MacroIndicator.recorded_at).label("max_recorded"),
            )
            .group_by(MacroIndicator.indicator_type)
            .subquery()
        )
        # Main query: join to get full rows
        stmt = select(MacroIndicator).join(
            latest_sub,
            (MacroIndicator.indicator_type == latest_sub.c.indicator_type)
            & (MacroIndicator.recorded_at == latest_sub.c.max_recorded),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
