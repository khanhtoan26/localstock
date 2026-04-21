"""MacroCrawler — fetches exchange rate from VCB XML endpoint.

VCB endpoint returns XML with Exrate elements for each currency.
We extract the USD/VND sell rate for macro scoring.

Per T-04-03: Validate rate is numeric and in reasonable range (20000-30000).
Per T-04-04: Returns None on failure; manual entry is the fallback.
"""

from datetime import date, datetime, UTC

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from localstock.config import get_settings

VCB_EXCHANGE_RATE_URL = (
    "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
)

# Reasonable VND/USD range for validation (T-04-03)
MIN_RATE = 20_000.0
MAX_RATE = 30_000.0


class MacroCrawler:
    """Fetches macro-economic data from external sources."""

    async def fetch_exchange_rate(
        self, previous_value: float | None = None
    ) -> dict | None:
        """Fetch USD/VND exchange rate from VCB XML endpoint.

        Args:
            previous_value: Previous exchange rate for trend calculation.

        Returns:
            Dict with value, source, indicator_type, period, recorded_at, trend.
            None if fetch or parse fails.
        """
        try:
            async with httpx.AsyncClient(timeout=15, verify=get_settings().ssl_verify) as client:
                response = await client.get(VCB_EXCHANGE_RATE_URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "xml")
            usd_element = soup.find("Exrate", {"CurrencyCode": "USD"})

            if usd_element is None:
                logger.warning("VCB XML: No USD Exrate element found")
                return None

            sell_str = usd_element.get("Sell", "")
            if not sell_str:
                logger.warning("VCB XML: No Sell attribute on USD element")
                return None

            # Parse rate — VCB uses comma as thousands separator
            sell_rate = float(sell_str.replace(",", ""))

            # Validate range (T-04-03)
            if not (MIN_RATE <= sell_rate <= MAX_RATE):
                logger.warning(
                    f"VCB XML: USD rate {sell_rate} outside valid range "
                    f"[{MIN_RATE}, {MAX_RATE}]"
                )
                return None

            # Compute trend
            trend: str | None = None
            if previous_value is not None:
                if sell_rate > previous_value:
                    trend = "rising"  # VND weakening
                elif sell_rate < previous_value:
                    trend = "falling"  # VND strengthening
                else:
                    trend = "stable"

            today = date.today()
            return {
                "value": sell_rate,
                "source": "vcb",
                "indicator_type": "exchange_rate_usd_vnd",
                "period": today.isoformat(),
                "recorded_at": today,
                "trend": trend,
                "fetched_at": datetime.now(UTC),
            }

        except Exception as e:
            logger.warning(f"VCB exchange rate fetch failed: {e}")
            return None

    async def determine_macro_conditions(
        self, indicators: list
    ) -> dict[str, str]:
        """Extract macro conditions from MacroIndicator objects.

        Maps indicator_type + trend to condition dict.
        E.g., interest_rate with trend="rising" → {"interest_rate": "rising"}.

        For exchange_rate_usd_vnd, strips the prefix to just "exchange_rate".

        Args:
            indicators: List of MacroIndicator objects with indicator_type and trend.

        Returns:
            Dict like {"interest_rate": "rising", "exchange_rate": "falling"}.
        """
        conditions: dict[str, str] = {}

        for ind in indicators:
            if ind.trend is None:
                continue

            # Normalize indicator type to condition key
            itype = ind.indicator_type
            if itype == "exchange_rate_usd_vnd":
                key = "exchange_rate"
            else:
                key = itype

            conditions[key] = ind.trend

        return conditions
