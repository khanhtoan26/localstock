#!/usr/bin/env python3
"""Run composite scoring to rank all stocks.

Requires: Analysis and sentiment data exist.

Usage:
    uv run python apps/prometheus/bin/run_scoring.py
"""

import asyncio

from localstock.observability import configure_logging
configure_logging()

from loguru import logger

from localstock.db.database import get_session_factory
from localstock.services.scoring_service import ScoringService


async def main() -> None:
    factory = get_session_factory()
    logger.info("Running composite scoring...")
    async with factory() as session:
        service = ScoringService(session)
        result = await service.run_full()

    print(f"\n{'='*50}")
    print(f"Scored:    {result.get('scored', 0)} stocks")
    print(f"Failed:    {result.get('failed', 0)}")

    # Show top 10
    from localstock.db.repositories.score_repo import ScoreRepository

    async with factory() as session:
        repo = ScoreRepository(session)
        top = await repo.get_top_ranked(limit=10)
    if top:
        print(f"\nTop 10 stocks:")
        print(f"{'Rank':<6} {'Symbol':<8} {'Score':<8} {'Grade':<6}")
        print("-" * 30)
        for s in top:
            print(f"{s.rank:<6} {s.symbol:<8} {s.total_score:<8.1f} {s.grade:<6}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
