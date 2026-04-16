#!/usr/bin/env python3
"""Run composite scoring to rank all stocks.

Requires: Analysis and sentiment data exist.

Usage:
    uv run python bin/run_scoring.py
"""

import asyncio

from loguru import logger

from localstock.db.database import async_session
from localstock.services.scoring_service import ScoringService


async def main() -> None:
    logger.info("Running composite scoring...")
    async with async_session() as session:
        service = ScoringService(session)
        result = await service.run_full()

    print(f"\n{'='*50}")
    print(f"Scored:    {result.get('scored', 0)} stocks")
    print(f"Failed:    {result.get('failed', 0)}")

    # Show top 10
    top = await get_top_stocks()
    if top:
        print(f"\nTop 10 stocks:")
        print(f"{'Rank':<6} {'Symbol':<8} {'Score':<8} {'Grade':<6}")
        print("-" * 30)
        for s in top:
            print(f"{s.rank:<6} {s.symbol:<8} {s.total_score:<8.1f} {s.grade:<6}")
    print(f"{'='*50}")


async def get_top_stocks():
    from localstock.db.repositories.score_repo import ScoreRepository

    async with async_session() as session:
        repo = ScoreRepository(session)
        return await repo.get_top_ranked(limit=10)


if __name__ == "__main__":
    asyncio.run(main())
