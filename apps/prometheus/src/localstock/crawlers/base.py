"""Abstract base crawler with error-tolerant batch processing (per D-02)."""

import asyncio
from abc import ABC, abstractmethod

import pandas as pd
from loguru import logger


class BaseCrawler(ABC):
    """Abstract base for all data crawlers.

    Implements error-tolerant batch processing: skip failed tickers,
    continue others, log errors (per D-02 decision).
    """

    def __init__(self, delay_seconds: float = 1.0):
        self.delay_seconds = delay_seconds

    @abstractmethod
    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch data for a single symbol. Returns DataFrame."""
        pass

    async def fetch_batch(
        self, symbols: list[str], **kwargs
    ) -> tuple[dict[str, pd.DataFrame], list[tuple[str, str]]]:
        """Fetch data for multiple symbols with error tolerance.

        Per D-02: skip failed tickers, continue others, log errors.

        Returns:
            Tuple of (results_dict, failed_list) where failed_list
            is [(symbol, error_msg)].
        """
        results: dict[str, pd.DataFrame] = {}
        failed: list[tuple[str, str]] = []

        for symbol in symbols:
            try:
                df = await self.fetch(symbol, **kwargs)
                if df is not None and not df.empty:
                    results[symbol] = df
                else:
                    failed.append((symbol, "Empty DataFrame returned"))
                    logger.warning("crawl.symbol.skipped", symbol=symbol, reason="empty_data")
            except Exception as e:
                failed.append((symbol, str(e)))
                logger.warning("crawl.symbol.skipped", symbol=symbol, error=str(e))

            await asyncio.sleep(self.delay_seconds)

        if failed:
            logger.error(
                "crawl.batch.partial_failure",
                failed_count=len(failed),
                total=len(symbols),
                failed_symbols=[f[0] for f in failed],
            )

        return results, failed
