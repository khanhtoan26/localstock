"""Tests for pipeline orchestrator.

Tests use mocks for all crawlers and repositories — no live API or DB.
Verifies:
- Pipeline.__init__() creates all crawler and repository instances
- Pipeline.run_single() calls all 4 crawlers for a single symbol
- Pipeline._crawl_prices() uses incremental strategy (checks get_latest_date)
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from localstock.services.pipeline import Pipeline


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession with commit and add methods."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_pipeline_init(mock_session):
    """Pipeline.__init__() creates all crawler and repository instances."""
    pipeline = Pipeline(mock_session)
    assert pipeline.stock_repo is not None
    assert pipeline.price_repo is not None
    assert pipeline.financial_repo is not None
    assert pipeline.event_repo is not None
    assert pipeline.price_crawler is not None
    assert pipeline.finance_crawler is not None
    assert pipeline.company_crawler is not None
    assert pipeline.event_crawler is not None


@pytest.mark.asyncio
async def test_run_single_calls_all_crawlers(mock_session):
    """run_single() calls all 4 crawlers for a single symbol."""
    pipeline = Pipeline(mock_session)

    # Mock all crawlers
    pipeline.price_crawler.fetch = AsyncMock(
        return_value=pd.DataFrame(
            {
                "time": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [105.0],
                "low": [95.0],
                "close": [102.0],
                "volume": [1_000_000],
            }
        )
    )
    pipeline.finance_crawler.fetch = AsyncMock(
        return_value={"balance_sheet": pd.DataFrame()}
    )
    pipeline.company_crawler.fetch = AsyncMock(
        return_value=pd.DataFrame({"symbol": ["ACB"]})
    )
    pipeline.event_crawler.fetch = AsyncMock(return_value=pd.DataFrame())
    pipeline.price_repo.upsert_prices = AsyncMock(return_value=1)

    result = await pipeline.run_single("ACB")

    assert result["symbol"] == "ACB"
    assert result["status"] in ("completed", "partial")
    pipeline.price_crawler.fetch.assert_called_once()
    pipeline.finance_crawler.fetch.assert_called_once()
    pipeline.company_crawler.fetch.assert_called_once()
    pipeline.event_crawler.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_crawl_prices_incremental_strategy(mock_session):
    """_crawl_prices() uses get_latest_date for incremental crawling."""
    pipeline = Pipeline(mock_session)

    # Mock price_repo to return a latest date
    latest = date(2024, 6, 10)
    pipeline.price_repo.get_latest_date = AsyncMock(return_value=latest)
    pipeline.price_crawler.fetch = AsyncMock(
        return_value=pd.DataFrame(
            {
                "time": [date(2024, 6, 11)],
                "open": [100.0],
                "high": [105.0],
                "low": [95.0],
                "close": [102.0],
                "volume": [1_000_000],
            }
        )
    )
    pipeline.price_repo.upsert_prices = AsyncMock(return_value=1)

    results, failed = await pipeline._crawl_prices(["ACB"])

    # Should have called get_latest_date
    pipeline.price_repo.get_latest_date.assert_called_once_with("ACB")
    # Should fetch starting from day after latest date
    expected_start = (latest + timedelta(days=1)).isoformat()
    call_kwargs = pipeline.price_crawler.fetch.call_args
    assert call_kwargs[1]["start_date"] == expected_start
    assert len(failed) == 0


@pytest.mark.asyncio
async def test_crawl_prices_backfill_when_no_data(mock_session):
    """_crawl_prices() uses 730-day backfill when no existing data."""
    pipeline = Pipeline(mock_session)

    # No existing data
    pipeline.price_repo.get_latest_date = AsyncMock(return_value=None)
    pipeline.price_crawler.fetch = AsyncMock(
        return_value=pd.DataFrame(
            {
                "time": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [105.0],
                "low": [95.0],
                "close": [102.0],
                "volume": [1_000_000],
            }
        )
    )
    pipeline.price_repo.upsert_prices = AsyncMock(return_value=1)

    results, failed = await pipeline._crawl_prices(["VNM"])

    call_kwargs = pipeline.price_crawler.fetch.call_args
    expected_start = (date.today() - timedelta(days=730)).isoformat()
    assert call_kwargs[1]["start_date"] == expected_start


@pytest.mark.asyncio
async def test_run_single_handles_crawler_failures(mock_session):
    """run_single() continues when individual crawlers fail (D-02)."""
    pipeline = Pipeline(mock_session)

    # Price succeeds, others fail
    pipeline.price_crawler.fetch = AsyncMock(
        return_value=pd.DataFrame(
            {
                "time": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [105.0],
                "low": [95.0],
                "close": [102.0],
                "volume": [1_000_000],
            }
        )
    )
    pipeline.price_repo.upsert_prices = AsyncMock(return_value=1)
    pipeline.finance_crawler.fetch = AsyncMock(
        side_effect=ValueError("API error")
    )
    pipeline.company_crawler.fetch = AsyncMock(
        side_effect=ConnectionError("timeout")
    )
    pipeline.event_crawler.fetch = AsyncMock(
        side_effect=RuntimeError("source down")
    )

    result = await pipeline.run_single("ACB")

    assert result["status"] == "partial"
    assert len(result["errors"]) == 3
    assert result["prices"] == 1
