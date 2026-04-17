"""Tests for FinanceCrawler and FinancialRepository with mocked vnstock."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from localstock.crawlers.finance_crawler import FinanceCrawler


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_balance_sheet():
    """Sample balance sheet DataFrame matching vnstock Finance output."""
    return pd.DataFrame(
        {
            "ticker": ["ACB", "ACB"],
            "year": [2024, 2024],
            "quarter": [3, 2],
            "total_assets": [700000.0, 680000.0],
            "total_liabilities": [640000.0, 620000.0],
            "equity": [60000.0, 60000.0],
        }
    )


@pytest.fixture
def sample_income_statement():
    """Sample income statement DataFrame matching vnstock Finance output."""
    return pd.DataFrame(
        {
            "ticker": ["ACB", "ACB"],
            "year": [2024, 2024],
            "quarter": [3, 2],
            "revenue": [15000.0, 14000.0],
            "net_income": [4500.0, 4200.0],
        }
    )


@pytest.fixture
def sample_cash_flow():
    """Sample cash flow DataFrame matching vnstock Finance output."""
    return pd.DataFrame(
        {
            "ticker": ["ACB", "ACB"],
            "year": [2024, 2024],
            "quarter": [3, 2],
            "operating_cash_flow": [8000.0, 7500.0],
            "investing_cash_flow": [-3000.0, -2800.0],
            "financing_cash_flow": [-2000.0, -1500.0],
        }
    )


@pytest.fixture
def mock_vnstock_finance(sample_balance_sheet, sample_income_statement, sample_cash_flow):
    """Mock vnstock to return financial data from KBS source."""
    with patch("localstock.crawlers.finance_crawler.Vnstock") as mock_cls:
        mock_instance = MagicMock()
        mock_stock = MagicMock()
        mock_stock.finance.balance_sheet.return_value = sample_balance_sheet
        mock_stock.finance.income_statement.return_value = sample_income_statement
        mock_stock.finance.cash_flow.return_value = sample_cash_flow
        mock_instance.stock.return_value = mock_stock
        mock_cls.return_value = mock_instance
        yield mock_cls


@pytest.fixture
def mock_vnstock_finance_kbs_fails(sample_balance_sheet, sample_income_statement, sample_cash_flow):
    """Mock vnstock where KBS fails but VCI works."""
    with patch("localstock.crawlers.finance_crawler.Vnstock") as mock_cls:
        call_count = 0

        def stock_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            source = kwargs.get("source", args[0] if args else "VCI")
            mock_stock = MagicMock()
            # KBS (first call) raises, VCI (second call) returns data
            if source == "KBS":
                mock_stock.finance.balance_sheet.side_effect = ConnectionError("KBS down")
                mock_stock.finance.income_statement.side_effect = ConnectionError("KBS down")
                mock_stock.finance.cash_flow.side_effect = ConnectionError("KBS down")
            else:
                mock_stock.finance.balance_sheet.return_value = sample_balance_sheet
                mock_stock.finance.income_statement.return_value = sample_income_statement
                mock_stock.finance.cash_flow.return_value = sample_cash_flow
            return mock_stock

        # We need to track which source was used at Vnstock() level
        def vnstock_init_side_effect(*args, **kwargs):
            source = kwargs.get("source", "VCI")
            mock_instance = MagicMock()
            mock_stock = MagicMock()
            if source == "KBS":
                mock_stock.finance.balance_sheet.side_effect = ConnectionError("KBS down")
            else:
                mock_stock.finance.balance_sheet.return_value = sample_balance_sheet
                mock_stock.finance.income_statement.return_value = sample_income_statement
                mock_stock.finance.cash_flow.return_value = sample_cash_flow
            mock_instance.stock.return_value = mock_stock
            return mock_instance

        mock_cls.side_effect = vnstock_init_side_effect
        yield mock_cls


@pytest.fixture
def mock_vnstock_all_fail():
    """Mock vnstock where all sources fail."""
    with patch("localstock.crawlers.finance_crawler.Vnstock") as mock_cls:

        def vnstock_init_side_effect(*args, **kwargs):
            mock_instance = MagicMock()
            mock_stock = MagicMock()
            mock_stock.finance.balance_sheet.side_effect = ConnectionError("API down")
            mock_instance.stock.return_value = mock_stock
            return mock_instance

        mock_cls.side_effect = vnstock_init_side_effect
        yield mock_cls


# ── Unit normalization tests ─────────────────────────────────────────


def test_normalize_unit_billion_vnd():
    """billion_vnd values pass through unchanged."""
    assert FinanceCrawler.normalize_unit(15000.0, "billion_vnd") == 15000.0


def test_normalize_unit_billion_alias():
    """'ty' alias maps to billion_vnd."""
    assert FinanceCrawler.normalize_unit(15000.0, "ty") == 15000.0


def test_normalize_unit_million_to_billion():
    """million_vnd values divided by 1,000 to get billion."""
    assert FinanceCrawler.normalize_unit(15_000_000.0, "million_vnd") == 15000.0


def test_normalize_unit_million_alias():
    """'trieu' alias maps to million_vnd."""
    assert FinanceCrawler.normalize_unit(15_000_000.0, "trieu") == 15000.0


def test_normalize_unit_dong_to_billion():
    """VND (dong) values divided by 1e9 to get billion."""
    result = FinanceCrawler.normalize_unit(15_000_000_000_000.0, "dong")
    assert abs(result - 15000.0) < 0.01


def test_normalize_unit_vnd_alias():
    """'vnd' alias maps same as 'dong'."""
    result = FinanceCrawler.normalize_unit(15_000_000_000_000.0, "vnd")
    assert abs(result - 15000.0) < 0.01


# ── Crawling tests ──────────────────────────────────────────────────


async def test_fetch_returns_all_report_types(mock_vnstock_finance):
    """FinanceCrawler.fetch() returns dict with all 3 report types."""
    crawler = FinanceCrawler(delay_seconds=0)
    result = await crawler.fetch("ACB")
    assert isinstance(result, dict)
    assert "balance_sheet" in result
    assert "income_statement" in result
    assert "cash_flow" in result
    # Each should be a DataFrame
    assert isinstance(result["balance_sheet"], pd.DataFrame)
    assert not result["balance_sheet"].empty


async def test_fetch_tries_kbs_first(mock_vnstock_finance):
    """FinanceCrawler tries KBS source first (per research recommendation)."""
    crawler = FinanceCrawler(delay_seconds=0)
    await crawler.fetch("ACB")
    # First call should be with KBS source
    first_call = mock_vnstock_finance.call_args_list[0]
    assert first_call.kwargs.get("source") == "KBS" or (
        first_call.args and first_call.args[0] == "KBS"
    )


async def test_fetch_falls_back_to_vci(mock_vnstock_finance_kbs_fails):
    """FinanceCrawler falls back to VCI when KBS fails."""
    crawler = FinanceCrawler(delay_seconds=0)
    result = await crawler.fetch("ACB")
    assert "balance_sheet" in result
    assert not result["balance_sheet"].empty
    # Verify both sources were tried (KBS failed, VCI succeeded)
    assert mock_vnstock_finance_kbs_fails.call_count >= 2


async def test_fetch_raises_when_all_sources_fail(mock_vnstock_all_fail):
    """FinanceCrawler raises ValueError when all sources fail."""
    crawler = FinanceCrawler(delay_seconds=0)
    with pytest.raises(ValueError, match="All sources failed"):
        await crawler.fetch("INVALID")


async def test_fetch_quarterly_and_annual(mock_vnstock_finance):
    """FinanceCrawler can fetch both quarterly and annual data."""
    crawler = FinanceCrawler(delay_seconds=0)

    # Quarterly (default)
    result_q = await crawler.fetch("ACB", period="quarter")
    assert "balance_sheet" in result_q

    # Annual
    result_a = await crawler.fetch("ACB", period="year")
    assert "balance_sheet" in result_a


# ── Repository tests ────────────────────────────────────────────────


def test_financial_repo_import():
    """FinancialRepository can be imported."""
    from localstock.db.repositories.financial_repo import FinancialRepository

    assert FinancialRepository is not None
