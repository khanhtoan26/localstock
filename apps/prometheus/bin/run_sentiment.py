#!/usr/bin/env python3
"""Crawl news and run sentiment analysis.

Requires: Ollama running with model configured in .env

Usage:
    uv run python apps/prometheus/bin/run_sentiment.py
"""

import asyncio

from localstock.observability import configure_logging
configure_logging()

from loguru import logger

from localstock import configure_ssl, configure_vnstock_api_key
from localstock.db.database import get_session_factory
from localstock.services.news_service import NewsService

configure_ssl()
configure_vnstock_api_key()
from localstock.services.sentiment_service import SentimentService


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        # Step 1: Crawl news
        logger.info("Crawling news from CafeF + VnExpress...")
        news_service = NewsService(session)
        news_result = await news_service.crawl_and_store()
        print(f"News: {news_result.get('articles_stored', 0)} articles saved")

        # Step 2: Run sentiment analysis
        logger.info("Running sentiment analysis via Ollama...")
        sentiment_service = SentimentService(session)
        sent_result = await sentiment_service.run_full()
        print(f"Sentiment: {sent_result.get('articles_processed', 0)} articles analyzed")
        print(f"Failed: {sent_result.get('failed', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
