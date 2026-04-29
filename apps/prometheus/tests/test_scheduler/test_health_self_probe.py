"""Phase 24 / OBS-15 — health_self_probe tests."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import REGISTRY

from localstock.scheduler.health_probe import health_self_probe


def _g(name: str) -> float:
    """Read current gauge sample value from the default REGISTRY (or 0 if unset)."""
    val = REGISTRY.get_sample_value(name)
    return val if val is not None else 0.0


class _FakeAsyncSessionCtx:
    def __init__(self, run):
        self._run = run

    async def __aenter__(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = self._run
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        return session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_self_probe_populates_gauges(monkeypatch):
    """OBS-15 — successful probe sets all 4 gauges to non-default values."""
    # Mock engine.pool with synchronous size()/checkedout() readouts.
    fake_pool = MagicMock()
    fake_pool.size.return_value = 5
    fake_pool.checkedout.return_value = 2
    fake_engine = MagicMock()
    fake_engine.pool = fake_pool
    monkeypatch.setattr(
        "localstock.db.database.get_engine", lambda: fake_engine
    )

    completed = datetime.now(UTC) - timedelta(seconds=42)
    fake_run = MagicMock()
    fake_run.completed_at = completed
    fake_run.symbols_success = 42

    def _factory():
        return _FakeAsyncSessionCtx(fake_run)

    monkeypatch.setattr(
        "localstock.db.database.get_session_factory", lambda: _factory
    )

    await health_self_probe()

    assert _g("localstock_db_pool_size") == 5
    assert _g("localstock_db_pool_checked_out") == 2
    assert _g("localstock_last_pipeline_age_seconds") >= 42
    assert _g("localstock_last_crawl_success_count") == 42


@pytest.mark.asyncio
async def test_self_probe_logs_on_failure(monkeypatch, loguru_caplog):
    """OBS-15 — failure path: probe must not raise; logs WARNING `health_probe_failed`."""
    def _boom():
        raise RuntimeError("pool exploded")

    monkeypatch.setattr(
        "localstock.db.database.get_engine", _boom
    )

    # Must not raise.
    await health_self_probe()

    messages = [r.get("message", "") for r in loguru_caplog.records]
    assert any("health_probe_failed" in m for m in messages), (
        f"Expected 'health_probe_failed' in log messages; got {messages!r}"
    )
