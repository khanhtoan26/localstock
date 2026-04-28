"""Repository for sentiment_scores table with bulk upsert."""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import SentimentScore


class SentimentRepository:
    """Repository for SentimentScore model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert sentiment scores. Dedup on (article_id, symbol)."""
        if not rows:
            return 0
        stmt = pg_insert(SentimentScore).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in SentimentScore.__table__.columns
            if col.name not in ("id", "article_id", "symbol")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_sentiment_score",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info("sentiment_repo.bulk_upserted", rows=len(rows))
        return len(rows)

    async def get_by_symbol(
        self, symbol: str, days: int = 7, limit: int = 20
    ) -> list[SentimentScore]:
        """Get sentiment scores for a symbol within N days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(SentimentScore)
            .where(
                SentimentScore.symbol == symbol,
                SentimentScore.computed_at >= cutoff,
            )
            .order_by(SentimentScore.computed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_symbols_with_sentiment(self) -> list[str]:
        """Return list of symbols that have sentiment scores."""
        stmt = select(SentimentScore.symbol).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
