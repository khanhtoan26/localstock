"""Repository for sector_snapshots table with bulk upsert."""

from datetime import date as date_type

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import SectorSnapshot


class SectorSnapshotRepository:
    """Repository for SectorSnapshot model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert sector snapshots. Dedup on (date, group_code)."""
        if not rows:
            return 0
        stmt = pg_insert(SectorSnapshot).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in SectorSnapshot.__table__.columns
            if col.name not in ("id", "date", "group_code")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_sector_snapshot",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Upserted {len(rows)} sector snapshots")
        return len(rows)

    async def get_latest(self, group_code: str) -> SectorSnapshot | None:
        """Get most recent snapshot for a sector group."""
        stmt = (
            select(SectorSnapshot)
            .where(SectorSnapshot.group_code == group_code)
            .order_by(SectorSnapshot.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date(self, target_date: date_type) -> list[SectorSnapshot]:
        """Get all sector snapshots for a specific date."""
        stmt = (
            select(SectorSnapshot)
            .where(SectorSnapshot.date == target_date)
            .order_by(SectorSnapshot.avg_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_date_range(
        self, start_date: date_type, end_date: date_type
    ) -> list[SectorSnapshot]:
        """Get sector snapshots in a date range for rotation analysis."""
        stmt = (
            select(SectorSnapshot)
            .where(SectorSnapshot.date >= start_date)
            .where(SectorSnapshot.date <= end_date)
            .order_by(SectorSnapshot.date.desc(), SectorSnapshot.avg_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
