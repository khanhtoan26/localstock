"""Phase 25 / DQ-07 — /health/data data_freshness extension (RED until 25-08).

These tests exercise the proposed shape of the `data_freshness` block on
the /health/data response. 25-08 lands the route extension + sessions_behind
calculation against the trading calendar.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_data_freshness_shape() -> None:
    """/health/data response includes data_freshness block with 5 keys."""
    from localstock.api.routes.health import health_data

    sess = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = date.today()
    sess.execute.return_value = result
    body = await health_data(session=sess)
    assert "data_freshness" in body
    df = body["data_freshness"]
    assert set(df.keys()) >= {
        "last_trading_day",
        "max_data_date",
        "sessions_behind",
        "status",
        "threshold_sessions",
    }


@pytest.mark.asyncio
async def test_stale_status_when_lag_exceeds_threshold() -> None:
    from localstock.api.routes.health import health_data

    sess = AsyncMock()
    old = date.today() - timedelta(days=5)
    result = MagicMock()
    result.scalar_one_or_none.return_value = old
    sess.execute.return_value = result
    body = await health_data(session=sess)
    assert body["data_freshness"]["status"] == "stale"


@pytest.mark.asyncio
async def test_threshold_override(monkeypatch) -> None:
    from localstock.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("DQ_STALE_THRESHOLD_SESSIONS", "10")
    from localstock.api.routes.health import health_data

    sess = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = date.today() - timedelta(days=2)
    sess.execute.return_value = result
    body = await health_data(session=sess)
    assert body["data_freshness"]["status"] == "fresh"


@pytest.mark.asyncio
async def test_sc5_health_data_response_shape() -> None:
    """ROADMAP Success Criterion #5 verbatim — /health/data response shape.

    Asserts the dual contract:
      1. Phase 24 back-compat (D-05): top-level keys ``max_price_date``,
         ``trading_days_lag``, ``stale`` MUST remain present.
      2. DQ-07: ``data_freshness`` block exposes the 5 documented keys
         and ``status`` is one of {fresh, stale, unknown}.
    """
    from localstock.api.routes.health import health_data

    sess = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = date.today()
    sess.execute.return_value = result
    body = await health_data(session=sess)

    # Phase 24 contract preserved verbatim (CONTEXT D-05).
    for k in ("max_price_date", "trading_days_lag", "stale"):
        assert k in body, f"Phase 24 contract broken: missing {k}"

    # DQ-07 / SC #5 — new freshness block.
    assert "data_freshness" in body
    df = body["data_freshness"]
    for k in (
        "last_trading_day",
        "max_data_date",
        "sessions_behind",
        "status",
        "threshold_sessions",
    ):
        assert k in df, f"DQ-07 missing key: {k}"
    assert df["status"] in ("fresh", "stale", "unknown")
    assert isinstance(df["threshold_sessions"], int)
