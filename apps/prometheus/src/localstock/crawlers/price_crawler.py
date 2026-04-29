"""OHLCV price crawler using vnstock v3.5.1 (per D-01).

Uses KBS source directly — VCI source broken (Company.__init__ crash).
"""

import asyncio
from datetime import date, timedelta

import pandas as pd
from loguru import logger

from localstock.config import get_settings
from localstock.crawlers import suppress_vnstock_output
from localstock.crawlers.base import BaseCrawler
from localstock.observability.decorators import observe


class PriceCrawler(BaseCrawler):
    """Crawls OHLCV price data from vnstock Quote.history().

    Uses KBS source (VCI broken in v3.5.1). Implements incremental
    crawling: only fetches data after the latest date already in DB.

    All vnstock calls are synchronous — wrapped in ``run_in_executor``
    to avoid blocking the async event loop.
    """

    def __init__(self, delay_seconds: float | None = None):
        settings = get_settings()
        super().__init__(delay_seconds=delay_seconds if delay_seconds is not None else settings.crawl_delay_seconds)

    @observe("crawl.ohlcv.fetch")
    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch OHLCV data for a single symbol from vnstock.

        Args:
            symbol: Stock ticker (e.g., ``'ACB'``).

        Keyword Args:
            start_date: ``YYYY-MM-DD`` string. Default: 2 years ago.
            end_date: ``YYYY-MM-DD`` string. Default: today.

        Returns:
            DataFrame with columns: time, open, high, low, close, volume.

        Raises:
            ValueError: If vnstock returns empty or ``None`` data.
        """
        start = kwargs.get("start_date", self.get_backfill_start_date())
        end = kwargs.get("end_date", date.today().isoformat())

        def _fetch_sync() -> pd.DataFrame:
            with suppress_vnstock_output():
                from vnstock.explorer.kbs.quote import Quote as KBSQuote
                quote = KBSQuote(symbol)
                return quote.history(start=start, end=end, interval="1D")

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _fetch_sync)

        if df is None or df.empty:
            raise ValueError(f"No price data returned for {symbol} ({start} to {end})")

        logger.info(
            "crawl.prices.fetched",
            symbol=symbol,
            rows=len(df),
            start=str(start),
            end=str(end),
        )
        return df

    def get_backfill_start_date(self) -> str:
        """Return start date for historical backfill (2 years ago per DATA-02).

        Returns:
            ISO-formatted date string ~730 days before today.
        """
        return (date.today() - timedelta(days=730)).isoformat()
