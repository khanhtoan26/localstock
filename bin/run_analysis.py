#!/usr/bin/env python3
"""Run technical + fundamental analysis for all HOSE stocks.

Requires: Data already crawled (run crawl_all.py or crawl_single.py first).

Usage:
    uv run python bin/run_analysis.py
"""

import asyncio

from loguru import logger

from localstock.db.database import async_session
from localstock.services.analysis_service import AnalysisService


async def main() -> None:
    logger.info("Running technical + fundamental analysis...")
    async with async_session() as session:
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
