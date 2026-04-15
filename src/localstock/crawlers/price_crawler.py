"""OHLCV price crawler using vnstock v3.5.1 (per D-01)."""

import asyncio
from datetime import date, timedelta

import pandas as pd
from loguru import logger
from vnstock import Vnstock

from localstock.config import get_settings
from localstock.crawlers.base import BaseCrawler


class PriceCrawler(BaseCrawler):
    """Crawls OHLCV price data from vnstock Quote.history().

    Uses VCI source by default (per D-01). Configurable via settings.
    Implements incremental crawling: only fetches data after the latest
    date already in the database.

    The vnstock library is synchronous — all calls are wrapped in
    ``run_in_executor`` to avoid blocking the async event loop.
    """

    def __init__(self, delay_seconds: float | None = None):
        settings = get_settings()
        super().__init__(delay_seconds=delay_seconds if delay_seconds is not None else settings.crawl_delay_seconds)
        self.source: str = settings.vnstock_source  # 'VCI' or 'KBS'

    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch OHLCV data for a single symbol from vnstock.

        Wraps synchronous vnstock call in ``run_in_executor`` (T-01-05
        compliant — respects crawl delay between batch requests).

        Args:
            symbol: Stock ticker (e.g., ``'ACB'``).

        Keyword Args:
            start_date: ``YYYY-MM-DD`` string. Default: 2 years ago.
            end_date: ``YYYY-MM-DD`` string. Default: today.
            source: Override default data source (``'VCI'`` or ``'KBS'``).

        Returns:
            DataFrame with columns: time, open, high, low, close, volume.

        Raises:
            ValueError: If vnstock returns empty or ``None`` data.
        """
        start = kwargs.get("start_date", self.get_backfill_start_date())
        end = kwargs.get("end_date", date.today().isoformat())
        source = kwargs.get("source", self.source)

        # vnstock is synchronous — run in thread pool to avoid blocking
        def _fetch_sync() -> pd.DataFrame:
            client = Vnstock(source=source)
            stock = client.stock(symbol=symbol, source=source)
            df = stock.quote.history(start=start, end=end, interval="1D")
            return df

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _fetch_sync)

        if df is None or df.empty:
            raise ValueError(f"No price data returned for {symbol} ({start} to {end})")

        logger.info(f"Fetched {len(df)} price rows for {symbol} ({start} to {end})")
        return df

    def get_backfill_start_date(self) -> str:
        """Return start date for historical backfill (2 years ago per DATA-02).

        Returns:
            ISO-formatted date string ~730 days before today.
        """
        return (date.today() - timedelta(days=730)).isoformat()
