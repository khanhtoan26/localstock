"""Financial statement crawler using vnstock Finance API.

Uses direct module access (KBS/VCI Finance classes) to bypass the
broken Vnstock.stock() initializer. Fetches each report type
independently so partial results are returned on failure.

All vnstock calls are synchronous — wrapped in ``run_in_executor``
to avoid blocking the async event loop.
"""

import asyncio
import importlib

import pandas as pd
from loguru import logger

from localstock.crawlers import suppress_vnstock_output
from localstock.crawlers.base import BaseCrawler
from localstock.observability.decorators import observe


class FinanceCrawler(BaseCrawler):
    """Crawls financial statements from vnstock Finance API.

    Fetches three report types per symbol:
    - balance_sheet
    - income_statement
    - cash_flow

    Uses direct module access (bypasses broken Vnstock.stock()).
    Tries KBS first, then VCI. Each report type is fetched
    independently — partial results are returned on failure.
    """

    REPORT_TYPES = ["balance_sheet", "income_statement", "cash_flow"]

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(delay_seconds=delay_seconds)

    @observe("crawl.financial.fetch")
    async def fetch(self, symbol: str, **kwargs) -> dict[str, pd.DataFrame]:
        """Fetch all financial statements for a symbol.

        Tries KBS and VCI sources with direct module access.
        Each report type is fetched independently so partial
        results are returned even if some fail.

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Keyword Args:
            period: 'quarter' or 'year' (default: 'quarter').

        Returns:
            Dict mapping report type names to DataFrames.
            May be empty if all sources fail.
        """
        period = kwargs.get("period", "quarter")
        results: dict[str, pd.DataFrame] = {}

        # Try each source with direct module access
        sources = [
            ("KBS", "vnstock.explorer.kbs.financial", "Finance"),
            ("VCI", "vnstock.explorer.vci.financial", "Finance"),
        ]

        for source_name, module_path, class_name in sources:
            try:
                source_results = await self._fetch_from_source(
                    symbol, source_name, module_path, class_name, period
                )
                # Merge: keep first successful result for each report type
                for rtype, df in source_results.items():
                    if rtype not in results:
                        results[rtype] = df
                if len(results) == len(self.REPORT_TYPES):
                    break  # Got all 3 report types
            except Exception as e:
                logger.warning(
                    "crawl.finance.source_failed",
                    source=source_name,
                    symbol=symbol,
                    error=str(e),
                )

        if results:
            logger.info(
                "crawl.finance.fetched",
                symbol=symbol,
                report_count=len(results),
                report_types=list(results.keys()),
            )
        else:
            logger.info("crawl.finance.unavailable", symbol=symbol)

        return results

    async def fetch_batch(
        self, symbols: list[str], **kwargs
    ) -> tuple[dict[str, dict[str, pd.DataFrame]], list[tuple[str, str]]]:
        """Fetch financials for multiple symbols with error tolerance.

        Overrides BaseCrawler.fetch_batch because FinanceCrawler.fetch()
        returns dict[str, DataFrame] (not a single DataFrame).
        """
        results: dict[str, dict[str, pd.DataFrame]] = {}
        failed: list[tuple[str, str]] = []

        # DQ-05 (D-03): verified isolated — per-symbol try/except wraps
        # fetch() and the outer batch returns (results, failed). RESEARCH
        # §Audit List 2026-04-29 (25-06).
        for symbol in symbols:
            try:
                reports = await self.fetch(symbol, **kwargs)
                if reports:
                    results[symbol] = reports
                else:
                    failed.append((symbol, "No financial data available"))
            except Exception as e:
                failed.append((symbol, str(e)))
                logger.warning("crawl.finance.symbol_skipped", symbol=symbol, error=str(e))

            await asyncio.sleep(self.delay_seconds)

        if failed:
            logger.warning(
                "crawl.finance.batch_partial_failure",
                failed_count=len(failed),
                total=len(symbols),
                failed_symbols=[f[0] for f in failed],
            )

        return results, failed

    async def _fetch_from_source(
        self, symbol: str, source_name: str, module_path: str,
        class_name: str, period: str
    ) -> dict[str, pd.DataFrame]:
        """Fetch report types independently from a single source.

        Each report type is fetched in its own try/catch so partial
        results are returned.

        Returns:
            Dict of report type to DataFrame (may be partial).
        """
        def _sync_fetch():
            with suppress_vnstock_output():
                mod = importlib.import_module(module_path)
                FinanceClass = getattr(mod, class_name)
                try:
                    fin = FinanceClass(symbol)
                except (KeyError, Exception) as e:
                    logger.debug(
                        f"{source_name} init failed for {symbol}: "
                        f"API returned invalid response (missing key: {e})"
                    )
                    return {}

                results = {}
                for rtype in self.REPORT_TYPES:
                    try:
                        method = getattr(fin, rtype)
                        df = method(period=period)
                        if df is not None and not df.empty:
                            results[rtype] = df
                    except KeyError as e:
                        logger.debug(
                            f"{source_name} {rtype} failed for {symbol}: "
                            f"missing API response key '{e.args[0]}'"
                        )
                    except Exception as e:
                        logger.debug(
                            f"{source_name} {rtype} failed for {symbol}: {e}"
                        )
                return results

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
