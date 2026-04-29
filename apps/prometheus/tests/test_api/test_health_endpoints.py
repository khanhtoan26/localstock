"""Phase 24 / OBS-14 — health probe integration tests.

Covers the 6 verbatim test names from 24-VALIDATION.md OBS-14 rows:

  1. test_health_live_returns_200
  2. test_health_ready_503_when_db_ping_fails
  3. test_health_ready_200_with_pool_stats
  4. test_health_pipeline_returns_age_seconds
  5. test_health_data_returns_freshness
  6. test_health_legacy_alias_has_deprecation_header

Tests run against ``create_app()`` via FastAPI ``TestClient`` with the
APScheduler lifespan stubbed and ``Depends(get_session)`` overridden to
yield a ``MagicMock`` session (see ``conftest.py`` in this dir). Pool
stats for ``/health/ready`` and ``/health`` come from the ``mock_engine``
fixture, which patches ``localstock.api.routes.health.get_engine`` so
no real DB / pool is required.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import OperationalError


# ---- 1. /health/live --------------------------------------------------------
def test_health_live_returns_200(client) -> None:
    """`/health/live` MUST always return 200 with body {"status": "alive"}.

    Per D-03: liveness probe performs zero I/O, so we deliberately do NOT
    wire ``override_session`` — if the handler accidentally touches the DB
    the test would surface that regression as an unrelated failure.
    """
    r = client.get("/health/live")
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "alive"}


# ---- 2. /health/ready — DB ping fails ---------------------------------------
def test_health_ready_503_when_db_ping_fails(client, override_session, mock_engine) -> None:
    """Readiness 503s when the bounded `SELECT 1` ping raises OperationalError."""
    override_session.execute = AsyncMock(
        side_effect=OperationalError("boom", None, Exception("DB down"))
    )
    r = client.get("/health/ready")
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["db"] == "down"
    assert "error_type" in body


# ---- 3. /health/ready — DB up + pool stats ----------------------------------
def test_health_ready_200_with_pool_stats(client, override_session, mock_engine) -> None:
    """Readiness returns 200 and exposes the 4 expected pool counters."""
    override_session.execute = AsyncMock(return_value=MagicMock())
    r = client.get("/health/ready")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["db"] == "ok"
    assert set(body["pool"].keys()) == {"size", "checked_in", "checked_out", "overflow"}


# ---- 4. /health/pipeline ----------------------------------------------------
def test_health_pipeline_returns_age_seconds(client, override_session) -> None:
    """`/health/pipeline` reports last_run_status + last_pipeline_age_seconds."""
    completed = datetime.now(timezone.utc) - timedelta(hours=1)
    started = completed - timedelta(minutes=5)
    fake_run = MagicMock()
    fake_run.status = "completed"
    fake_run.completed_at = completed
    fake_run.started_at = started

    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_run
    override_session.execute = AsyncMock(return_value=result)

    r = client.get("/health/pipeline")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["last_run_status"] == "completed"
    assert body["last_pipeline_age_seconds"] >= 3600
    assert body["started_at"] is not None
    assert body["completed_at"] is not None


# ---- 5. /health/data --------------------------------------------------------
def test_health_data_returns_freshness(client, override_session) -> None:
    """`/health/data` returns max_price_date + trading_days_lag + stale bool."""
    yesterday = date.today() - timedelta(days=1)
    result = MagicMock()
    result.scalar_one_or_none.return_value = yesterday
    override_session.execute = AsyncMock(return_value=result)

    r = client.get("/health/data")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_price_date"] == yesterday.isoformat()
    assert "trading_days_lag" in body
    assert isinstance(body["stale"], bool)


# ---- 6. /health (legacy alias) ----------------------------------------------
def test_health_legacy_alias_has_deprecation_header(client, override_session, mock_engine) -> None:
    """Legacy `/health` mirrors `/health/ready` body and sets X-Deprecated."""
    override_session.execute = AsyncMock(return_value=MagicMock())
    r = client.get("/health")
    assert r.status_code in (200, 503)
    assert r.headers.get("X-Deprecated") == "use /health/ready instead"
