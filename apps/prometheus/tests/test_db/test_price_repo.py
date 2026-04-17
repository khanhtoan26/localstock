"""Tests for PriceRepository upsert and query logic."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.repositories.price_repo import PriceRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar.return_value = None
    session.execute.return_value = result_mock
    return session


@pytest.fixture
def price_repo(mock_session):
    """Create a PriceRepository with a mocked session."""
    return PriceRepository(mock_session)


async def test_upsert_prices_inserts_new_rows(price_repo, mock_session, sample_ohlcv_df):
    """PriceRepository.upsert_prices() inserts new OHLCV rows."""
    count = await price_repo.upsert_prices("ACB", sample_ohlcv_df)
    assert count == 3
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_upsert_prices_handles_duplicate_symbol_date(price_repo, mock_session, sample_ohlcv_df):
    """PriceRepository.upsert_prices() on duplicate (symbol, date) updates values."""
    # First upsert
    await price_repo.upsert_prices("ACB", sample_ohlcv_df)
    mock_session.execute.reset_mock()
    mock_session.commit.reset_mock()

    # Second upsert with same dates — should NOT raise
    updated_df = sample_ohlcv_df.copy()
    updated_df.loc[0, "close"] = 26000.0
    count = await price_repo.upsert_prices("ACB", updated_df)
    assert count == 3
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_get_latest_date_returns_none_for_unknown_symbol(price_repo, mock_session):
    """PriceRepository.get_latest_date() returns None for unknown symbol."""
    result_mock = MagicMock()
    result_mock.scalar.return_value = None
    mock_session.execute.return_value = result_mock

    result = await price_repo.get_latest_date("UNKNOWN")
    assert result is None


async def test_get_latest_date_returns_date(price_repo, mock_session):
    """PriceRepository.get_latest_date() returns the most recent date for a symbol."""
    result_mock = MagicMock()
    result_mock.scalar.return_value = date(2024, 1, 4)
    mock_session.execute.return_value = result_mock

    result = await price_repo.get_latest_date("ACB")
    assert result == date(2024, 1, 4)


async def test_upsert_prices_validates_dataframe_columns(price_repo, mock_session):
    """PriceRepository.upsert_prices() raises on invalid DataFrame columns."""
    bad_df = pd.DataFrame({"wrong_col": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing required columns"):
        await price_repo.upsert_prices("ACB", bad_df)


async def test_upsert_prices_rejects_empty_dataframe(price_repo, mock_session):
    """PriceRepository.upsert_prices() returns 0 for empty DataFrame."""
    empty_df = pd.DataFrame()
    count = await price_repo.upsert_prices("ACB", empty_df)
    assert count == 0
