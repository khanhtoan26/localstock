"""Tests for PriceCrawler with mocked vnstock."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from localstock.crawlers.price_crawler import PriceCrawler


@pytest.fixture
def mock_settings():
    """Mock get_settings to avoid needing .env file."""
    with patch("localstock.crawlers.price_crawler.get_settings") as mock:
        settings = MagicMock()
        settings.crawl_delay_seconds = 0.0
        settings.vnstock_source = "VCI"
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_vnstock(sample_ohlcv_df):
    """Mock vnstock to return sample data without API calls."""
    with patch("localstock.crawlers.price_crawler.Vnstock") as mock_cls:
        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.quote.history.return_value = sample_ohlcv_df
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance
        yield mock_cls


async def test_fetch_returns_ohlcv_dataframe(mock_settings, mock_vnstock, sample_ohlcv_df):
    """PriceCrawler.fetch() returns DataFrame with OHLCV columns."""
    crawler = PriceCrawler(delay_seconds=0)
    df = await crawler.fetch("ACB", start_date="2024-01-01", end_date="2024-01-04")
    assert not df.empty
    assert "close" in df.columns
    assert "volume" in df.columns
    assert len(df) == 3


async def test_fetch_passes_dates_to_vnstock(mock_settings, mock_vnstock):
    """PriceCrawler.fetch() passes start_date and end_date to vnstock Quote.history()."""
    crawler = PriceCrawler(delay_seconds=0)
    await crawler.fetch("ACB", start_date="2023-01-01", end_date="2024-12-31")

    # Verify vnstock was called with correct params
    mock_instance = mock_vnstock.return_value
    mock_instance.stock.assert_called_once()
    mock_stock = mock_instance.stock.return_value
    mock_stock.quote.history.assert_called_once_with(
        start="2023-01-01", end="2024-12-31", interval="1D"
    )


async def test_fetch_raises_on_empty_data(mock_settings, mock_vnstock):
    """PriceCrawler.fetch() raises ValueError when vnstock returns empty DataFrame."""
    mock_vnstock.return_value.stock.return_value.quote.history.return_value = pd.DataFrame()
    crawler = PriceCrawler(delay_seconds=0)
    with pytest.raises(ValueError, match="No price data"):
        await crawler.fetch("INVALID")


async def test_fetch_raises_on_none_data(mock_settings, mock_vnstock):
    """PriceCrawler.fetch() raises ValueError when vnstock returns None."""
    mock_vnstock.return_value.stock.return_value.quote.history.return_value = None
    crawler = PriceCrawler(delay_seconds=0)
    with pytest.raises(ValueError, match="No price data"):
        await crawler.fetch("INVALID")


async def test_fetch_batch_skips_failed_symbols(mock_settings, mock_vnstock, sample_ohlcv_df):
    """PriceCrawler inherits BaseCrawler.fetch_batch() — skips failed symbols per D-02."""
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ConnectionError("API timeout")
        return sample_ohlcv_df

    mock_vnstock.return_value.stock.return_value.quote.history.side_effect = side_effect

    crawler = PriceCrawler(delay_seconds=0)
    results, failed = await crawler.fetch_batch(["ACB", "BAD", "VNM"])
    assert "ACB" in results
    assert "VNM" in results
    assert len(failed) == 1
    assert failed[0][0] == "BAD"


async def test_get_backfill_start_date(mock_settings):
    """PriceCrawler.get_backfill_start_date() returns a date ~2 years ago."""
    crawler = PriceCrawler(delay_seconds=0)
    start_date = crawler.get_backfill_start_date()
    # Should be in ISO format and roughly 730 days ago
    from datetime import date, timedelta

    expected = (date.today() - timedelta(days=730)).isoformat()
    assert start_date == expected


async def test_fetch_uses_configured_source(mock_settings, mock_vnstock, sample_ohlcv_df):
    """PriceCrawler uses vnstock_source from settings."""
    mock_settings.vnstock_source = "KBS"
    crawler = PriceCrawler(delay_seconds=0)
    assert crawler.source == "KBS"

    await crawler.fetch("ACB", start_date="2024-01-01", end_date="2024-01-04")
    mock_vnstock.assert_called_with(source="KBS")
