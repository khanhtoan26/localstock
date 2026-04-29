"""Phase 24 — test_api package conftest.

Isolates ``create_app()`` from APScheduler lifespan + real DB session so that
HTTP-level tests can run without external infrastructure. Mirrors the
``_isolate_app_from_infra`` pattern already used by ``tests/test_observability``
(Phase 22+23) but scoped to ``tests/test_api/`` and provides explicit
``client``, ``override_session``, and ``mock_engine`` fixtures for
dependency-injection-style tests.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    """FastAPI app instance with the APScheduler lifespan stubbed out."""

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    monkeypatch.setattr(
        "localstock.api.app.get_lifespan", _noop_lifespan, raising=True
    )
    from localstock.api.app import create_app

    return create_app()


@pytest.fixture
def client(app):
    """``TestClient`` bound to the isolated app."""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """A ``MagicMock`` session whose ``.execute`` is awaitable."""
    s = MagicMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def override_session(app, mock_session):
    """Override ``Depends(get_session)`` to yield ``mock_session``.

    Yields the underlying mock so tests can configure return / side_effect
    on ``mock_session.execute`` per scenario.
    """
    from localstock.db.database import get_session

    async def _override():
        yield mock_session

    app.dependency_overrides[get_session] = _override
    try:
        yield mock_session
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_engine(monkeypatch):
    """Patch ``localstock.api.routes.health.get_engine`` to return a mock.

    ``raising=False`` is intentional: during the RED phase the health module
    has not yet imported ``get_engine`` and the attribute does not exist.
    Once the GREEN rewrite lands, the patch becomes effective.
    """
    pool = MagicMock()
    pool.size.return_value = 3
    pool.checkedin.return_value = 1
    pool.checkedout.return_value = 0
    pool.overflow.return_value = 0
    engine = MagicMock()
    engine.pool = pool
    monkeypatch.setattr(
        "localstock.api.routes.health.get_engine",
        lambda: engine,
        raising=False,
    )
    return engine
