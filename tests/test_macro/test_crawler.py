"""Tests for MacroCrawler — VCB exchange rate parsing."""

import pytest

from localstock.macro.crawler import MacroCrawler


# Sample VCB XML response
VCB_XML_VALID = """<?xml version="1.0" encoding="utf-8"?>
<ExrateList>
    <DateTime>04/16/2026 11:02:15 AM</DateTime>
    <Exrate CurrencyCode="AUD" CurrencyName="ÐÔLA ÚC"
        Buy="16,260.22" Transfer="16,424.47" Sell="16,920.97"/>
    <Exrate CurrencyCode="USD" CurrencyName="ÐÔ LA MỸ"
        Buy="25,450.00" Transfer="25,480.00" Sell="25,850.00"/>
    <Exrate CurrencyCode="EUR" CurrencyName="EURO"
        Buy="28,372.26" Transfer="28,657.85" Sell="29,541.59"/>
</ExrateList>"""

VCB_XML_NO_USD = """<?xml version="1.0" encoding="utf-8"?>
<ExrateList>
    <DateTime>04/16/2026 11:02:15 AM</DateTime>
    <Exrate CurrencyCode="AUD" CurrencyName="ÐÔLA ÚC"
        Buy="16,260.22" Transfer="16,424.47" Sell="16,920.97"/>
</ExrateList>"""

VCB_XML_MALFORMED = """<?xml version="1.0"?>
<ExrateList><broken>"""


class TestFetchExchangeRate:
    """Test MacroCrawler.fetch_exchange_rate()."""

    @pytest.mark.asyncio
    async def test_parses_valid_xml(self, mocker):
        """Should parse VCB XML and return dict with value, source, trend."""
        mock_response = mocker.AsyncMock()
        mock_response.status_code = 200
        mock_response.text = VCB_XML_VALID

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate()

        assert result is not None
        assert result["value"] == 25850.0
        assert result["source"] == "vcb"
        assert result["indicator_type"] == "exchange_rate_usd_vnd"
        assert "period" in result
        assert "recorded_at" in result

    @pytest.mark.asyncio
    async def test_trend_rising_when_value_higher(self, mocker):
        """Trend should be 'rising' (vnd weakening) when current > previous."""
        mock_response = mocker.AsyncMock()
        mock_response.status_code = 200
        mock_response.text = VCB_XML_VALID

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate(previous_value=25000.0)

        assert result is not None
        assert result["trend"] == "rising"

    @pytest.mark.asyncio
    async def test_trend_falling_when_value_lower(self, mocker):
        """Trend should be 'falling' (vnd strengthening) when current < previous."""
        mock_response = mocker.AsyncMock()
        mock_response.status_code = 200
        mock_response.text = VCB_XML_VALID

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate(previous_value=26000.0)

        assert result is not None
        assert result["trend"] == "falling"

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, mocker):
        """Should return None on connection errors."""
        import httpx

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate()

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_malformed_xml(self, mocker):
        """Should return None on malformed XML."""
        mock_response = mocker.AsyncMock()
        mock_response.status_code = 200
        mock_response.text = VCB_XML_MALFORMED

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate()

        assert result is None

    @pytest.mark.asyncio
    async def test_validates_rate_range(self, mocker):
        """Rate outside 20000-30000 VND/USD should return None (T-04-03)."""
        bad_xml = VCB_XML_VALID.replace("25,850.00", "5,000.00")
        mock_response = mocker.AsyncMock()
        mock_response.status_code = 200
        mock_response.text = bad_xml

        mock_client = mocker.AsyncMock()
        mock_client.get = mocker.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        crawler = MacroCrawler()
        result = await crawler.fetch_exchange_rate()

        assert result is None


class TestDetermineMacroConditions:
    """Test MacroCrawler.determine_macro_conditions()."""

    @pytest.mark.asyncio
    async def test_extracts_conditions_from_indicators(self):
        """Should map indicator trends to macro condition dict."""

        class FakeIndicator:
            def __init__(self, itype, trend):
                self.indicator_type = itype
                self.trend = trend

        indicators = [
            FakeIndicator("interest_rate", "rising"),
            FakeIndicator("exchange_rate_usd_vnd", "falling"),
        ]

        crawler = MacroCrawler()
        conditions = await crawler.determine_macro_conditions(indicators)

        assert conditions["interest_rate"] == "rising"
        assert conditions["exchange_rate"] == "falling"

    @pytest.mark.asyncio
    async def test_skips_stable_indicators(self):
        """Stable indicators should still be included."""

        class FakeIndicator:
            def __init__(self, itype, trend):
                self.indicator_type = itype
                self.trend = trend

        indicators = [FakeIndicator("cpi", "stable")]
        crawler = MacroCrawler()
        conditions = await crawler.determine_macro_conditions(indicators)

        assert conditions["cpi"] == "stable"

    @pytest.mark.asyncio
    async def test_empty_indicators_returns_empty_dict(self):
        """No indicators should return empty conditions."""
        crawler = MacroCrawler()
        conditions = await crawler.determine_macro_conditions([])

        assert conditions == {}

    @pytest.mark.asyncio
    async def test_skips_indicators_without_trend(self):
        """Indicators with None trend should be skipped."""

        class FakeIndicator:
            def __init__(self, itype, trend):
                self.indicator_type = itype
                self.trend = trend

        indicators = [FakeIndicator("gdp", None)]
        crawler = MacroCrawler()
        conditions = await crawler.determine_macro_conditions(indicators)

        assert "gdp" not in conditions
