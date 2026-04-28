#!/usr/bin/env python3
"""Crawl a single stock symbol — prices, financials, company, events.

Usage:
    uv run python apps/prometheus/bin/crawl_single.py ACB
    uv run python apps/prometheus/bin/crawl_single.py VNM
"""

import asyncio
import sys

from localstock.observability import configure_logging
configure_logging()

from loguru import logger

from localstock import configure_ssl, configure_vnstock_api_key
from localstock.db.database import get_session_factory
from localstock.services.pipeline import Pipeline

configure_ssl()
configure_vnstock_api_key()


async def main(symbol: str) -> None:
    logger.info("cli.crawl_single.started", symbol=symbol)
    factory = get_session_factory()
    async with factory() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_single(symbol)

    print(f"\n{'='*50}")
    print(f"Symbol:     {result['symbol']}")
    print(f"Status:     {result['status']}")
    print(f"Prices:     {result.get('prices', 'N/A')} phiên")
    print(f"Financials: {result.get('financials', 'N/A')} báo cáo")
    print(f"Company:    {result.get('company', 'N/A')}")
    print(f"Events:     {result.get('events', 'N/A')} sự kiện")
    if result.get("errors"):
        print(f"Errors:     {result['errors']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python apps/prometheus/bin/crawl_single.py <SYMBOL>")
        print("Example: uv run python apps/prometheus/bin/crawl_single.py ACB")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    asyncio.run(main(symbol))
