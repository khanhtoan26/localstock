"""Tests for StockRepository upsert and query logic."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.repositories.stock_repo import StockRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    # Mock execute to return a result proxy
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock
    return session


@pytest.fixture
def stock_repo(mock_session):
    """Create a StockRepository with a mocked session."""
    return StockRepository(mock_session)


@pytest.fixture
def sample_listings_df():
    """Sample DataFrame matching vnstock Listing.all_symbols() output."""
    return pd.DataFrame(
        {
            "symbol": ["ACB", "VNM", "FPT"],
            "organ_name": ["Ngan hang TMCP A Chau", "Vinamilk", "FPT Corp"],
            "exchange": ["HOSE", "HOSE", "HNX"],
            "icb_name3": ["Ngan hang", "Thuc pham", "Cong nghe"],
            "icb_name4": ["Ngan hang TM", "Sua", "Phan mem"],
            "issue_share": [3_880_000_000.0, 2_090_000_000.0, 1_500_000_000.0],
            "charter_capital": [38_800.0, 20_900.0, 15_000.0],
        }
    )


async def test_upsert_stocks_inserts_new_stocks(stock_repo, mock_session, sample_listings_df):
    """StockRepository.upsert_stocks() inserts new stocks into empty table."""
    count = await stock_repo.upsert_stocks(sample_listings_df)
    assert count == 3
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_upsert_stocks_updates_existing_without_duplicates(
    stock_repo, mock_session, sample_listings_df
):
    """StockRepository.upsert_stocks() updates existing stock without creating duplicate."""
    # First call
    await stock_repo.upsert_stocks(sample_listings_df)
    # Reset mock
    mock_session.execute.reset_mock()
    mock_session.commit.reset_mock()

    # Second call with updated issue_shares
    updated_df = sample_listings_df.copy()
    updated_df.loc[0, "issue_share"] = 4_000_000_000.0
    count = await stock_repo.upsert_stocks(updated_df)
    assert count == 3
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_get_all_hose_symbols_returns_only_hose(stock_repo, mock_session):
    """StockRepository.get_all_hose_symbols() returns only symbols where exchange='HOSE'."""
    # Mock the result to return HOSE symbols
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = ["ACB", "VNM"]
    mock_session.execute.return_value = result_mock

    symbols = await stock_repo.get_all_hose_symbols()
    assert symbols == ["ACB", "VNM"]
    mock_session.execute.assert_called_once()
