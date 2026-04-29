"""Company profile crawler using vnstock Company.overview().

Uses KBS source directly — VCI source broken (Company.__init__ crash
in vnstock 3.5.1). KBS provides company overview, officers, events.

All vnstock calls are synchronous — wrapped in ``run_in_executor``
to avoid blocking the async event loop.
"""

import asyncio

import pandas as pd
from loguru import logger

from localstock.config import get_settings
from localstock.crawlers import suppress_vnstock_output
from localstock.crawlers.base import BaseCrawler
from localstock.observability.decorators import observe


class CompanyCrawler(BaseCrawler):
    """Crawls company profile data from vnstock Company.overview().

    Uses KBS direct module access (bypasses broken Vnstock.stock()).
    Populates the stocks table with:
    - ICB industry classification (icb_name3 = sector, icb_name4 = subsector)
    - issue_shares (outstanding shares count)
    - charter_capital (in billion VND)
    """

    def __init__(self, delay_seconds: float | None = None):
        settings = get_settings()
        super().__init__(
            delay_seconds=delay_seconds
            if delay_seconds is not None
            else settings.crawl_delay_seconds,
        )

    @observe("crawl.company.fetch")
    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch company overview for a single symbol from vnstock.

        Uses KBS direct module access (VCI broken in v3.5.1).

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Returns:
            DataFrame with company overview data.

        Raises:
            ValueError: If vnstock returns empty or None data.
        """

        def _sync_fetch():
            with suppress_vnstock_output():
                from vnstock.explorer.kbs.company import Company as KBSCompany
                company = KBSCompany(symbol)
                return company.overview()

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _sync_fetch)

        if df is None or df.empty:
            raise ValueError(f"No company data returned for {symbol}")

        logger.info("crawl.company.fetched", symbol=symbol)
        return df

    def overview_to_stock_dict(self, overview_df: pd.DataFrame) -> dict:
        """Convert vnstock Company.overview() DataFrame to a dict
        matching Stock model columns.

        Maps vnstock columns to model columns:
        - 'symbol' → symbol
        - 'company_name' or 'short_name' → name
        - 'exchange' → exchange
        - 'icb_name3' → industry_icb3
        - 'icb_name4' → industry_icb4
        - 'issue_share' → issue_shares
        - 'charter_capital' → charter_capital

        Args:
            overview_df: DataFrame from vnstock Company.overview().

        Returns:
            Dict with keys matching Stock model columns.
        """
        row = overview_df.iloc[0]
        name_col = (
            "company_name"
            if "company_name" in overview_df.columns
            else "short_name"
        )
        return {
            "symbol": row.get("symbol", ""),
            "name": row.get(name_col, ""),
            "exchange": row.get("exchange", "HOSE"),
            "industry_icb3": row.get("icb_name3")
            if pd.notna(row.get("icb_name3"))
            else None,
            "industry_icb4": row.get("icb_name4")
            if pd.notna(row.get("icb_name4"))
            else None,
            "issue_shares": float(row.get("issue_share", 0))
            if row.get("issue_share") is not None
            and pd.notna(row.get("issue_share"))
            else None,
            "charter_capital": float(row.get("charter_capital", 0))
            if row.get("charter_capital") is not None
            and pd.notna(row.get("charter_capital"))
            else None,
        }
