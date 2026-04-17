"""Shared pytest fixtures for LocalStock tests."""

from datetime import date

import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv_df():
    """Sample OHLCV DataFrame matching vnstock Quote.history() output format."""
    return pd.DataFrame(
        {
            "time": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
            "open": [25000.0, 25500.0, 25200.0],
            "high": [25800.0, 25700.0, 25600.0],
            "low": [24800.0, 25100.0, 25000.0],
            "close": [25500.0, 25200.0, 25400.0],
            "volume": [1000000, 1200000, 900000],
        }
    )


@pytest.fixture
def sample_company_overview():
    """Sample company overview matching vnstock Company.overview() output."""
    return pd.DataFrame(
        {
            "symbol": ["ACB"],
            "company_name": ["Ngan hang TMCP A Chau"],
            "exchange": ["HOSE"],
            "icb_name3": ["Ngan hang"],
            "icb_name4": ["Ngan hang thuong mai"],
            "issue_share": [3_880_000_000.0],
            "charter_capital": [38_800.0],
        }
    )


@pytest.fixture
def sample_corporate_events():
    """Sample corporate events matching vnstock Company.events() output."""
    return pd.DataFrame(
        {
            "event_title": ["Chia co phieu thuong 10%"],
            "exright_date": ["2024-06-15"],
            "record_date": ["2024-06-14"],
            "event_list_code": ["stock_dividend"],
            "ratio": [1.1],
            "value": [0.0],
            "public_date": ["2024-05-20"],
        }
    )


@pytest.fixture
def sample_financial_data():
    """Sample financial statement data matching vnstock Finance output."""
    return {
        "balance_sheet": pd.DataFrame(
            {
                "ticker": ["ACB"],
                "year": [2024],
                "quarter": [3],
                "total_assets": [700000.0],
                "total_liabilities": [640000.0],
                "equity": [60000.0],
            }
        ),
        "income_statement": pd.DataFrame(
            {
                "ticker": ["ACB"],
                "year": [2024],
                "quarter": [3],
                "revenue": [15000.0],
                "net_income": [4500.0],
            }
        ),
    }
