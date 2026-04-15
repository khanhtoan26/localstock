"""Repository for news_articles table with bulk upsert."""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import NewsArticle


class NewsRepository:
    """Repository for NewsArticle model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert news articles. Dedup on URL (unique constraint)."""
        if not rows:
            return 0
        stmt = pg_insert(NewsArticle).values(rows)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in NewsArticle.__table__.columns
            if col.name not in ("id", "url")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["url"],
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Upserted {len(rows)} news articles")
        return len(rows)

    async def get_recent(self, days: int = 7, limit: int = 200) -> list[NewsArticle]:
        """Fetch recent articles within N days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.published_at >= cutoff)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_url(self, url: str) -> NewsArticle | None:
        """Get article by URL."""
        stmt = select(NewsArticle).where(NewsArticle.url == url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_unprocessed(self, limit: int = 100) -> list[NewsArticle]:
        """Get articles that haven't been sentiment-analyzed yet.

        An article is unprocessed if it has no corresponding SentimentScore row.
        """
        from localstock.db.models import SentimentScore

        subq = select(SentimentScore.article_id).distinct().subquery()
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.id.notin_(select(subq)))
            .where(NewsArticle.content.isnot(None))
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total articles."""
        stmt = select(func.count()).select_from(NewsArticle)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
