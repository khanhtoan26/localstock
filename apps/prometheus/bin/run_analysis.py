#!/usr/bin/env python3
"""Run technical + fundamental analysis for all HOSE stocks.

Requires: Data already crawled (run crawl_all.py or crawl_single.py first).

Usage:
    uv run python apps/prometheus/bin/run_analysis.py
"""

import asyncio

from loguru import logger

from localstock.db.database import get_session_factory
from localstock.services.analysis_service import AnalysisService


async def main() -> None:
    logger.info("Running technical + fundamental analysis...")
    factory = get_session_factory()
    async with factory() as session:
        service = AnalysisService(session)
        result = await service.run_full()

    print(f"\n{'='*50}")
    print(f"Analyzed:  {result.get('analyzed', 0)} symbols")
    print(f"Failed:    {result.get('failed', 0)} symbols")
    if result.get("errors"):
        print(f"Errors:    {len(result['errors'])}")
        for err in result["errors"][:5]:
            print(f"  - {err}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
