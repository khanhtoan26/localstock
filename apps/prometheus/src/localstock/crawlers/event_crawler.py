"""Corporate event crawler using vnstock Company.events().

Uses KBS source directly — VCI source broken (Company.__init__ crash
in vnstock 3.5.1). Fetches corporate actions (splits, stock dividends,
rights issues) needed for backward price adjustment (DATA-05).

All vnstock calls are synchronous — wrapped in ``run_in_executor``
to avoid blocking the async event loop.
"""

import asyncio

import pandas as pd
from loguru import logger

from localstock.crawlers import suppress_vnstock_output
from localstock.crawlers.base import BaseCrawler
from localstock.observability.decorators import observe


class EventCrawler(BaseCrawler):
    """Crawls corporate events from vnstock Company.events().

    Uses KBS direct module access (bypasses broken Vnstock.stock()).
    Unlike other crawlers, returns empty DataFrame (not raising ValueError)
    when no events exist — most stocks have few or no corporate events,
    and that's normal.
    """

    # Mapping from vnstock event_list_code to canonical event_type
    EVENT_TYPE_MAP = {
        "split": "split",
        "stock_dividend": "stock_dividend",
        "cash_dividend": "cash_dividend",
        "rights_issue": "rights_issue",
        "bonus_share": "stock_dividend",
    }

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(delay_seconds=delay_seconds)

    @observe("crawl.event.fetch")
    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch corporate events for a symbol from vnstock.

        Uses KBS direct module access (VCI broken in v3.5.1).

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Returns:
            DataFrame with corporate events. Empty DataFrame if no events
            (this is normal — not an error).
        """

        def _sync_fetch():
            with suppress_vnstock_output():
                from vnstock.explorer.kbs.company import Company as KBSCompany
                company = KBSCompany(symbol)
                return company.events()

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _sync_fetch)

        if df is None or df.empty:
            logger.info("crawl.events.empty", symbol=symbol)
            return pd.DataFrame()

        logger.info("crawl.events.fetched", symbol=symbol, rows=len(df))
        return df

    @classmethod
    def parse_event_type(cls, event_list_code: str | None) -> str:
        """Map vnstock event_list_code to canonical event_type.

        Known mappings:
        - 'split' → 'split'
        - 'stock_dividend' → 'stock_dividend'
        - 'cash_dividend' → 'cash_dividend'
        - 'rights_issue' → 'rights_issue'
        - 'bonus_share' → 'stock_dividend' (same adjustment as stock dividend)

        Unknown codes default to the original code string (per T-01-11:
        only apply adjustments for known split/dividend types).

        Args:
            event_list_code: Event type code from vnstock.

        Returns:
            Canonical event type string.
        """
        if not event_list_code:
            return "unknown"
        return cls.EVENT_TYPE_MAP.get(
            event_list_code.lower().strip(), event_list_code.lower().strip()
        )
