"""Repository for composite_scores table with bulk upsert."""

from datetime import date as date_type

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import CompositeScore


class ScoreRepository:
    """Repository for CompositeScore model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert composite scores. Dedup on (symbol, date)."""
        if not rows:
            return 0
        stmt = pg_insert(CompositeScore).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in CompositeScore.__table__.columns
            if col.name not in ("id", "symbol", "date")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_composite_score",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Upserted {len(rows)} composite scores")
        return len(rows)

    async def get_latest(self, symbol: str) -> CompositeScore | None:
        """Get the most recent composite score for a symbol."""
        stmt = (
            select(CompositeScore)
            .where(CompositeScore.symbol == symbol)
            .order_by(CompositeScore.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_top_ranked(
        self, target_date: date_type | None = None, limit: int = 20
    ) -> list[CompositeScore]:
        """Get top-ranked stocks by total_score for a given date.

        If target_date is None, uses the most recent scoring date.
        """
        if target_date is None:
            # Find the most recent date with scores
            max_date_stmt = select(func.max(CompositeScore.date))
            max_result = await self.session.execute(max_date_stmt)
            target_date = max_result.scalar()
            if target_date is None:
                return []

        stmt = (
            select(CompositeScore)
            .where(CompositeScore.date == target_date)
            .order_by(CompositeScore.total_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_date(self, target_date: date_type) -> list[CompositeScore]:
        """Get all scores for a specific date."""
        stmt = (
            select(CompositeScore)
            .where(CompositeScore.date == target_date)
            .order_by(CompositeScore.total_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
