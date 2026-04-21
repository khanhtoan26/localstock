#!/usr/bin/env python3
"""Run the full daily pipeline: crawl → analyze → sentiment → score → report.

This is the master script that runs everything in sequence.
Requires: Supabase DB configured, Ollama running (optional for reports).

Usage:
    uv run python apps/prometheus/bin/run_daily.py
    uv run python apps/prometheus/bin/run_daily.py --skip-reports    # Skip LLM reports
"""

import asyncio
import sys
from datetime import UTC, datetime

from loguru import logger

from localstock import configure_ssl
from localstock.db.database import get_session_factory
from localstock.services.pipeline import Pipeline
from localstock.services.analysis_service import AnalysisService
from localstock.services.news_service import NewsService
from localstock.services.sentiment_service import SentimentService
from localstock.services.scoring_service import ScoringService
from localstock.services.report_service import ReportService

configure_ssl()


async def main(skip_reports: bool = False) -> None:
    factory = get_session_factory()
    start = datetime.now(UTC)
    print(f"🚀 LocalStock Daily Pipeline — {start.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    async with factory() as session:
        logger.info("Step 1/6: Crawling market data...")
        pipeline = Pipeline(session)
        crawl = await pipeline.run_full(run_type="daily")
        print(f"✅ Crawl: {crawl.symbols_success}/{crawl.symbols_total} stocks")

    async with factory() as session:
        logger.info("Step 2/6: Running analysis...")
        analysis = AnalysisService(session)
        anal_result = await analysis.run_full()
        print(f"✅ Analysis: {anal_result.get('technical_success', 0)} stocks")

    async with factory() as session:
        logger.info("Step 3/6: Crawling news...")
        news = NewsService(session)
        news_result = await news.crawl_and_store()
        print(f"✅ News: {news_result.get('articles_stored', 0)} articles")

    async with factory() as session:
        logger.info("Step 4/6: Sentiment analysis...")
        sentiment = SentimentService(session)
        sent_result = await sentiment.run_full()
        print(f"✅ Sentiment: {sent_result.get('articles_processed', 0)} analyzed")

    async with factory() as session:
        logger.info("Step 5/6: Scoring...")
        scoring = ScoringService(session)
        score_result = await scoring.run_full()
        print(f"✅ Scoring: {score_result.get('stocks_scored', 0)} stocks ranked")

    if not skip_reports:
        async with factory() as session:
            logger.info("Step 6/6: Generating AI reports...")
            reports = ReportService(session)
            report_result = await reports.run_full(top_n=10)
            print(f"✅ Reports: {report_result.get('reports_generated', 0)} generated")
    else:
        print("⏭ Reports: skipped (--skip-reports)")

    elapsed = (datetime.now(UTC) - start).total_seconds()
    print("=" * 60)
    print(f"🏁 Pipeline complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    skip_reports = "--skip-reports" in sys.argv
    asyncio.run(main(skip_reports))
