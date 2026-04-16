#!/usr/bin/env python3
"""Run the full pipeline for all ~400 HOSE stocks.

Usage:
    uv run python bin/crawl_all.py
    uv run python bin/crawl_all.py --type backfill
"""

import asyncio
import sys

from loguru import logger

from localstock.db.database import async_session
from localstock.services.pipeline import Pipeline


async def main(run_type: str = "daily") -> None:
    logger.info(f"Starting full pipeline ({run_type})...")
    async with async_session() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_full(run_type=run_type)

    print(f"\n{'='*50}")
    print(f"Status:          {result.status}")
    print(f"Run type:        {result.run_type}")
    print(f"Symbols total:   {result.symbols_total}")
    print(f"Symbols success: {result.symbols_success}")
    print(f"Symbols failed:  {result.symbols_failed}")
    print(f"Started:         {result.started_at}")
    print(f"Completed:       {result.completed_at}")
    if result.errors:
        print(f"Errors:          {result.errors}")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_type = "daily"
    if len(sys.argv) > 1 and sys.argv[1] == "--type":
        run_type = sys.argv[2] if len(sys.argv) > 2 else "daily"

    asyncio.run(main(run_type))
