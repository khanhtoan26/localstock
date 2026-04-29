"""Shared pytest fixtures for LocalStock tests."""

import os

# D-08: enqueue=False guard — sentinel must be set BEFORE configure_logging() is imported,
# so any module-level loguru configuration sees pytest mode and avoids background threads
# that can hang teardown (Phase 22 CONTEXT.md D-08).
os.environ.setdefault("PYTEST_CURRENT_TEST", "init")

from datetime import date

import httpx
import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture(scope="session", autouse=True)
def _configure_test_logging():
    """Force LOG_LEVEL=DEBUG and enqueue=False under pytest (CONTEXT.md D-08).

    The ImportError fallback is intentional: during Wave 0 (test scaffolds) the
    `localstock.observability` package may not yet exist. The existing test suite
    must continue to collect and run while later waves land the implementation.
    """
    os.environ["LOG_LEVEL"] = "DEBUG"
    try:
        from localstock.observability.logging import configure_logging

        configure_logging()
    except ImportError:
        # Wave 0 ran before Wave 1 — observability package not yet created.
        # Allowed: tests for non-observability suites still work.
        pass
    yield
    logger.complete()


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


# === Phase 26 / Wave-0 — project-wide async DB + HTTP fixtures (B2 fix) ===
# Lifted from tests/test_dq/test_quarantine_repo.py:22-50 so plans
# 26-03/04/05 (cache versioning, perf benchmarks, prewarm integration) can
# discover the same fixture names. Gated by `pytest.mark.requires_pg` at
# the consumer test level — tests skip cleanly if PG is unavailable.


@pytest_asyncio.fixture
async def db_session():
    """Project-wide async DB session, transactional rollback for isolation.

    Yields an `AsyncSession` bound to a fresh `create_async_engine`. The
    final `rollback()` discards any uncommitted state. Tests that call
    `session.commit()` to materialise rows MUST clean up their own
    test-data afterwards (this fixture is a session, not a sandbox).
    """
    from localstock.config import get_settings

    settings = get_settings()
    eng = create_async_engine(
        settings.database_url,
        connect_args={
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        },
    )
    sessionmaker = async_sessionmaker(eng, expire_on_commit=False)
    session = sessionmaker()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        await eng.dispose()


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client bound to the FastAPI app via ASGI transport.

    Used by Phase 26 perf + integration tests
    (test_perf_ranking, test_perf_market, test_route_caching_integration).
    """
    from localstock.api.app import create_app  # late import — app
    # construction touches DI / Instrumentator side-effects.

    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
