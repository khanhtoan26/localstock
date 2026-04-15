"""News acquisition service — orchestrates RSS crawl → parse → store.

Pipeline:
1. Fetch RSS feeds (CafeF 4 feeds + VnExpress 1 feed)
2. Parse and sanitize articles
3. Extract tickers from titles/descriptions
4. Store articles in DB via NewsRepository
5. Optionally enrich with full article text
"""

import asyncio

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.config import get_settings
from localstock.crawlers.news_crawler import NewsCrawler, extract_tickers
from localstock.db.repositories.news_repo import NewsRepository
from localstock.db.repositories.stock_repo import StockRepository


class NewsService:
    """Orchestrates news crawling and storage."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.news_repo = NewsRepository(session)
        self.stock_repo = StockRepository(session)
        self.crawler = NewsCrawler()

    async def crawl_and_store(self, enrich: bool = True) -> dict:
        """Crawl all RSS feeds and store articles.

        Args:
            enrich: If True, fetch full article text for stored articles.

        Returns:
            Summary dict with articles_found, articles_stored, errors.
        """
        summary = {"articles_found": 0, "articles_stored": 0, "errors": []}

        try:
            articles = await self.crawler.crawl_feeds()
            summary["articles_found"] = len(articles)

            if not articles:
                logger.warning("No articles found from RSS feeds")
                return summary

            # Get valid symbols for ticker extraction
            valid_symbols = set(await self.stock_repo.get_all_hose_symbols())

            # Prepare rows for bulk upsert
            rows = []
            for article in articles:
                # Extract tickers from title + description
                text = f"{article.get('title', '')} {article.get('description', '')}"
                tickers = extract_tickers(text, valid_symbols)

                rows.append({
                    "url": article["url"],
                    "title": article["title"],
                    "summary": article.get("description"),
                    "content": article.get("content"),
                    "source": article["source"],
                    "source_feed": article.get("source_feed"),
                    "published_at": article["published_at"],
                })

            count = await self.news_repo.bulk_upsert(rows)
            summary["articles_stored"] = count

            # Enrich with full article content
            if enrich:
                unprocessed = await self.news_repo.get_unprocessed(limit=50)
                # Note: enrichment fetches article pages — do in Plan 02's NewsCrawler
                # For now, articles have summary from RSS description

        except Exception as e:
            summary["errors"].append(str(e))
            logger.error(f"News crawl failed: {e}")

        logger.info(
            f"News crawl: found={summary['articles_found']}, "
            f"stored={summary['articles_stored']}"
        )
        return summary
