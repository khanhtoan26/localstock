"""Tests for FinanceCrawler and FinancialRepository with mocked vnstock."""

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
def mock_kbs_finance(sample_balance_sheet, sample_income_statement, sample_cash_flow):
    """Mock KBS Finance to return financial data."""
    with patch("localstock.crawlers.finance_crawler.importlib") as mock_importlib:
        mock_module = MagicMock()
        mock_fin_instance = MagicMock()
        mock_fin_instance.balance_sheet.return_value = sample_balance_sheet
        mock_fin_instance.income_statement.return_value = sample_income_statement
        mock_fin_instance.cash_flow.return_value = sample_cash_flow
        mock_module.Finance.return_value = mock_fin_instance
        mock_importlib.import_module.return_value = mock_module
        yield mock_importlib


@pytest.fixture
def mock_kbs_fails_vci_works(sample_balance_sheet, sample_income_statement, sample_cash_flow):
    """Mock where KBS fails but VCI works."""
    with patch("localstock.crawlers.finance_crawler.importlib") as mock_importlib:
        kbs_module = MagicMock()
        kbs_fin = MagicMock()
        kbs_fin.balance_sheet.side_effect = ConnectionError("KBS down")
        kbs_fin.income_statement.side_effect = ConnectionError("KBS down")
        kbs_fin.cash_flow.side_effect = ConnectionError("KBS down")
        kbs_module.Finance.return_value = kbs_fin

        vci_module = MagicMock()
        vci_fin = MagicMock()
        vci_fin.balance_sheet.return_value = sample_balance_sheet
        vci_fin.income_statement.return_value = sample_income_statement
        vci_fin.cash_flow.return_value = sample_cash_flow
        vci_module.Finance.return_value = vci_fin

        def import_side_effect(path):
            if "kbs" in path:
                return kbs_module
            return vci_module

        mock_importlib.import_module.side_effect = import_side_effect
        yield mock_importlib


@pytest.fixture
def mock_all_fail():
    """Mock where all sources fail."""
    with patch("localstock.crawlers.finance_crawler.importlib") as mock_importlib:
        mock_module = MagicMock()
        mock_fin = MagicMock()
        mock_fin.balance_sheet.side_effect = ConnectionError("API down")
        mock_fin.income_statement.side_effect = ConnectionError("API down")
        mock_fin.cash_flow.side_effect = ConnectionError("API down")
        mock_module.Finance.return_value = mock_fin
        mock_importlib.import_module.return_value = mock_module
        yield mock_importlib


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


async def test_fetch_returns_all_report_types(mock_kbs_finance):
    """FinanceCrawler.fetch() returns dict with all 3 report types."""
    crawler = FinanceCrawler(delay_seconds=0)
    result = await crawler.fetch("ACB")
    assert isinstance(result, dict)
    assert "balance_sheet" in result
    assert "income_statement" in result
    assert "cash_flow" in result
    assert isinstance(result["balance_sheet"], pd.DataFrame)
    assert not result["balance_sheet"].empty


async def test_fetch_tries_kbs_first(mock_kbs_finance):
    """FinanceCrawler tries KBS source first."""
    crawler = FinanceCrawler(delay_seconds=0)
    await crawler.fetch("ACB")
    first_call = mock_kbs_finance.import_module.call_args_list[0]
    assert "kbs" in first_call.args[0]


async def test_fetch_falls_back_to_vci(mock_kbs_fails_vci_works):
    """FinanceCrawler falls back to VCI when KBS fails."""
    crawler = FinanceCrawler(delay_seconds=0)
    result = await crawler.fetch("ACB")
    assert "balance_sheet" in result
    assert not result["balance_sheet"].empty
    assert mock_kbs_fails_vci_works.import_module.call_count >= 2


async def test_fetch_returns_empty_when_all_sources_fail(mock_all_fail):
    """FinanceCrawler returns empty dict when all sources fail."""
    crawler = FinanceCrawler(delay_seconds=0)
    result = await crawler.fetch("INVALID")
    assert result == {}


async def test_fetch_quarterly_and_annual(mock_kbs_finance):
    """FinanceCrawler can fetch both quarterly and annual data."""
    crawler = FinanceCrawler(delay_seconds=0)

    result_q = await crawler.fetch("ACB", period="quarter")
    assert "balance_sheet" in result_q

    result_a = await crawler.fetch("ACB", period="year")
    assert "balance_sheet" in result_a


# ── Repository tests ────────────────────────────────────────────────


def test_financial_repo_import():
    """FinancialRepository can be imported."""
    from localstock.db.repositories.financial_repo import FinancialRepository

    assert FinancialRepository is not None
