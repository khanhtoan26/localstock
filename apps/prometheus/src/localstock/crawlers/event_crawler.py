"""Corporate event crawler using vnstock Company.events().

Fetches corporate actions (splits, stock dividends, rights issues)
needed for backward price adjustment (DATA-05).

All vnstock calls are synchronous — wrapped in ``run_in_executor``
to avoid blocking the async event loop.
"""

import asyncio

import pandas as pd
from loguru import logger
from vnstock import Vnstock

from localstock.config import get_settings
from localstock.crawlers.base import BaseCrawler


class EventCrawler(BaseCrawler):
    """Crawls corporate events from vnstock Company.events().

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
        self.source: str = get_settings().vnstock_source

    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch corporate events for a symbol from vnstock.

        Returns DataFrame with: event_title, exright_date, record_date,
        event_list_code, ratio, value, public_date.

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Keyword Args:
            source: Override default source (default: 'VCI').

        Returns:
            DataFrame with corporate events. Empty DataFrame if no events
            (this is normal — not an error).

        Raises:
            Exception: Only if vnstock API itself errors (network, auth, etc.)
        """
        source = kwargs.get("source", self.source)

        def _sync_fetch():
            client = Vnstock(source=source)
            stock = client.stock(symbol=symbol, source=source)
            return stock.company.events()

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _sync_fetch)

        if df is None or df.empty:
            logger.info(f"No corporate events for {symbol}")
            return pd.DataFrame()  # No events is normal, not an error

        logger.info(f"Fetched {len(df)} corporate events for {symbol}")
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
