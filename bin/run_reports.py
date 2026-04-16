#!/usr/bin/env python3
"""Generate AI reports for top-ranked stocks.

Requires: Ollama running, scoring data exists.

Usage:
    uv run python bin/run_reports.py
    uv run python bin/run_reports.py --top 5
"""

import asyncio
import sys

from loguru import logger

from localstock.db.database import async_session
from localstock.services.report_service import ReportService


async def main(top_n: int = 10) -> None:
    logger.info(f"Generating AI reports for top {top_n} stocks...")
    async with async_session() as session:
        service = ReportService(session)
        result = await service.run_full(top_n=top_n)

    print(f"\n{'='*50}")
    print(f"Reports generated: {result.get('reports_generated', 0)}")
    print(f"Reports failed:    {result.get('reports_failed', 0)}")
    if result.get("errors"):
        for err in result["errors"][:5]:
            print(f"  ⚠ {err}")
    print(f"{'='*50}")


if __name__ == "__main__":
    top_n = 10
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 < len(sys.argv):
            top_n = int(sys.argv[idx + 1])

    asyncio.run(main(top_n))
