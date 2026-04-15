"""Financial statement crawler using vnstock Finance API.

Uses KBS source first (more stable per research issue #218),
falls back to VCI if KBS fails. Fetches balance sheet, income
statement, and cash flow for any HOSE ticker.

All vnstock calls are synchronous — wrapped in ``run_in_executor``
to avoid blocking the async event loop.
"""

import asyncio

import pandas as pd
from loguru import logger
from vnstock import Vnstock

from localstock.crawlers.base import BaseCrawler


class FinanceCrawler(BaseCrawler):
    """Crawls financial statements from vnstock Finance API.

    Fetches three report types per symbol:
    - balance_sheet
    - income_statement
    - cash_flow

    Source priority: KBS first (more stable for financials per
    research), then VCI as fallback.
    """

    REPORT_TYPES = ["balance_sheet", "income_statement", "cash_flow"]
    SOURCES = ["KBS", "VCI"]  # KBS first — more stable for financials

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(delay_seconds=delay_seconds)

    async def fetch(self, symbol: str, **kwargs) -> dict[str, pd.DataFrame]:
        """Fetch all financial statements for a symbol.

        Tries KBS source first, falls back to VCI (per research issue #218).

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Keyword Args:
            period: 'quarter' or 'year' (default: 'quarter').

        Returns:
            Dict mapping report type names to DataFrames:
            ``{"balance_sheet": df, "income_statement": df, "cash_flow": df}``

        Raises:
            ValueError: If all sources fail for this symbol.
        """
        period = kwargs.get("period", "quarter")

        for source in self.SOURCES:
            try:
                results = await self._fetch_from_source(symbol, source, period)
                if results:
                    logger.info(
                        f"Fetched {len(results)} financial reports for {symbol} "
                        f"from {source} (period={period})"
                    )
                    return results
            except Exception as e:
                logger.warning(f"{source} failed for {symbol} financials: {e}")
                continue

        raise ValueError(f"All sources failed for {symbol} financials")

    async def _fetch_from_source(
        self, symbol: str, source: str, period: str
    ) -> dict[str, pd.DataFrame]:
        """Fetch all 3 report types from a single source.

        Wraps synchronous vnstock calls in ``run_in_executor`` to avoid
        blocking the async event loop.

        Args:
            symbol: Stock ticker.
            source: Data source ('KBS' or 'VCI').
            period: 'quarter' or 'year'.

        Returns:
            Dict of report type to DataFrame.
        """

        def _sync_fetch():
            client = Vnstock(source=source)
            stock = client.stock(symbol=symbol, source=source)
            fin = stock.finance
            return {
                "balance_sheet": fin.balance_sheet(period=period),
                "income_statement": fin.income_statement(period=period),
                "cash_flow": fin.cash_flow(period=period),
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_fetch)

    @staticmethod
    def normalize_unit(value: float, detected_unit: str) -> float:
        """Normalize financial values to billion VND (tỷ đồng).

        Prevents Pitfall 4: companies report in different units.
        All values are converted to billion_vnd at ingestion time.

        Args:
            value: Raw financial value.
            detected_unit: Unit string from source data.

        Returns:
            Value normalized to billion VND.

        Conversion table:
            - 'dong' or 'vnd': divide by 1,000,000,000
            - 'trieu' or 'million_vnd' or 'million': divide by 1,000
            - 'ty' or 'billion_vnd' or 'billion': no change
        """
        multipliers = {
            "dong": 1e-9,
            "vnd": 1e-9,
            "trieu": 1e-3,
            "million_vnd": 1e-3,
            "million": 1e-3,
            "ty": 1.0,
            "billion_vnd": 1.0,
            "billion": 1.0,
        }
        factor = multipliers.get(detected_unit.lower(), 1.0)
        return value * factor
