"""Tests for CompanyCrawler with mocked vnstock."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from localstock.crawlers.company_crawler import CompanyCrawler


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    """Mock get_settings to avoid needing .env file."""
    with patch("localstock.crawlers.company_crawler.get_settings") as mock:
        settings = MagicMock()
        settings.crawl_delay_seconds = 0.0
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_vnstock_company(mock_settings, sample_company_overview):
    """Mock vnstock to return company overview data."""
    with patch("localstock.crawlers.company_crawler.Vnstock") as mock_cls:
        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.company.overview.return_value = sample_company_overview
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance
        yield mock_cls


# ── Fetch tests ──────────────────────────────────────────────────────


async def test_fetch_company_overview(mock_vnstock_company):
    """CompanyCrawler.fetch() returns DataFrame with company overview data."""
    crawler = CompanyCrawler(delay_seconds=0)
    df = await crawler.fetch("ACB")
    assert not df.empty
    assert "symbol" in df.columns


async def test_fetch_uses_vci_source(mock_vnstock_company):
    """CompanyCrawler uses VCI source by default (richer company data)."""
    crawler = CompanyCrawler(delay_seconds=0)
    await crawler.fetch("ACB")
    # Verify Vnstock was called with VCI source
    mock_vnstock_company.assert_called_with(source="VCI")


async def test_fetch_raises_on_empty(mock_settings):
    """CompanyCrawler.fetch() raises ValueError on empty response."""
    with patch("localstock.crawlers.company_crawler.Vnstock") as mock_cls:
        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.company.overview.return_value = pd.DataFrame()
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance

        crawler = CompanyCrawler(delay_seconds=0)
        with pytest.raises(ValueError, match="No company data"):
            await crawler.fetch("INVALID")


async def test_fetch_raises_on_none(mock_settings):
    """CompanyCrawler.fetch() raises ValueError when vnstock returns None."""
    with patch("localstock.crawlers.company_crawler.Vnstock") as mock_cls:
        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.company.overview.return_value = None
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance

        crawler = CompanyCrawler(delay_seconds=0)
        with pytest.raises(ValueError, match="No company data"):
            await crawler.fetch("INVALID")


# ── overview_to_stock_dict tests ─────────────────────────────────────


def test_overview_to_stock_dict(mock_settings, sample_company_overview):
    """overview_to_stock_dict() maps vnstock columns to Stock model columns."""
    crawler = CompanyCrawler(delay_seconds=0)
    result = crawler.overview_to_stock_dict(sample_company_overview)
    assert result["symbol"] == "ACB"
    assert result["name"] == "Ngan hang TMCP A Chau"
    assert result["exchange"] == "HOSE"
    assert result["industry_icb3"] == "Ngan hang"
    assert result["industry_icb4"] == "Ngan hang thuong mai"
    assert result["issue_shares"] == 3_880_000_000.0
    assert result["charter_capital"] == 38_800.0


def test_overview_to_stock_dict_with_short_name(mock_settings):
    """overview_to_stock_dict() falls back to short_name when company_name absent."""
    df = pd.DataFrame(
        {
            "symbol": ["VNM"],
            "short_name": ["Vinamilk"],
            "exchange": ["HOSE"],
            "icb_name3": ["Thuc pham"],
            "icb_name4": ["Sua"],
            "issue_share": [2_000_000_000.0],
            "charter_capital": [20_000.0],
        }
    )
    crawler = CompanyCrawler(delay_seconds=0)
    result = crawler.overview_to_stock_dict(df)
    assert result["name"] == "Vinamilk"


def test_overview_to_stock_dict_handles_none_values(mock_settings):
    """overview_to_stock_dict() handles None/NaN values gracefully."""
    df = pd.DataFrame(
        {
            "symbol": ["TEST"],
            "company_name": ["Test Corp"],
            "exchange": ["HOSE"],
            "icb_name3": [None],
            "icb_name4": [None],
            "issue_share": [None],
            "charter_capital": [None],
        }
    )
    crawler = CompanyCrawler(delay_seconds=0)
    result = crawler.overview_to_stock_dict(df)
    assert result["symbol"] == "TEST"
    assert result["industry_icb3"] is None
    assert result["issue_shares"] is None
    assert result["charter_capital"] is None


# ── Batch crawling tests ────────────────────────────────────────────


async def test_fetch_batch_skips_failed(mock_settings, sample_company_overview):
    """CompanyCrawler inherits BaseCrawler.fetch_batch() — skips failed symbols per D-02."""
    with patch("localstock.crawlers.company_crawler.Vnstock") as mock_cls:
        call_count = 0

        def overview_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConnectionError("timeout")
            return sample_company_overview

        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.company.overview.side_effect = overview_side_effect
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance

        crawler = CompanyCrawler(delay_seconds=0)
        results, failed = await crawler.fetch_batch(["ACB", "BAD", "VNM"])
        assert "ACB" in results
        assert len(failed) == 1
        assert failed[0][0] == "BAD"
