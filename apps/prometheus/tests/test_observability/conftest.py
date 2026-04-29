"""Loguru capture fixture for Phase 22 observability tests (per CONTEXT.md D-08b)."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from loguru import logger


@pytest.fixture(autouse=True)
def _isolate_app_from_infra(monkeypatch):
    """Decouple create_app() from scheduler + DB for middleware-only tests.

    Rationale (Rule 3 — blocking issue): production lifespan starts an APScheduler
    job and routes like `/health` open async DB sessions. Both reuse module-level
    state bound to the first test's event loop, causing `RuntimeError: Event loop
    is closed` on subsequent tests. These middleware tests don't exercise scheduler
    or DB behavior — they only need a 200 response to flow through the middleware
    stack. Scoped to tests/test_observability/ only.
    """
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(
        "localstock.api.app.get_lifespan", _noop_lifespan, raising=True
    )

    # Replace the session factory so any Depends(get_session) yields a mock that
    # responds to `await session.execute(stmt)` with predictable scalar values.
    class _FakeSessionCtx:
        async def __aenter__(self):
            session = MagicMock()
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.scalar.return_value = 0
            session.execute = AsyncMock(return_value=result)
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def _fake_factory():
        return _FakeSessionCtx()

    monkeypatch.setattr(
        "localstock.db.database.get_session_factory",
        lambda *a, **kw: _fake_factory,
        raising=True,
    )
    yield


@pytest.fixture
def loguru_caplog():
    records: list[dict] = []
    sink_id = logger.add(
        lambda msg: records.append(msg.record),
        level="DEBUG",
        format="{message}",
    )

    class _Capture:
        @property
        def records(self):
            return records

    yield _Capture()
    logger.remove(sink_id)


# === Phase 23 — Prometheus metric registry isolation (D-04) ===
import pytest as _pytest
from prometheus_client import CollectorRegistry as _CollectorRegistry


@_pytest.fixture
def metrics_registry() -> _CollectorRegistry:
    """Function-scoped fresh CollectorRegistry — prevents `Duplicated timeseries`
    between tests (CONTEXT.md D-04, OBS-10).

    Each test that calls ``init_metrics(registry)`` gets an isolated registry;
    no cleanup needed (GC'd at function teardown).
    """
    return _CollectorRegistry()
