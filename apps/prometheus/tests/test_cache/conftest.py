"""Cache-test isolation (P-2 mitigation).

Autouse fixture clears the per-key lock map and every namespace cache
between tests so single-flight tests cannot bleed locks/values into
each other.

26-04 extension: also reset the singleton ``_engine`` / ``_session_factory``
in ``localstock.db.database`` between tests. Route handlers go through
``get_session_factory()`` (a process-singleton) whose pool is bound to
the event loop on which it was first created. ``pytest-asyncio`` (auto
mode, function-scoped loop) hands each test a fresh loop, so reusing
the cached engine across tests yields ``RuntimeError: Event loop is
closed`` from asyncpg's connection-cancel hooks. Resetting the
singleton forces each test to construct a fresh engine on its own
loop.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from localstock.cache import registry as cache_registry
from localstock.cache import single_flight as sf


@pytest.fixture(autouse=True)
def _reset_cache_state():
    # Pre-test: clear locks and all namespace caches
    if hasattr(sf, "_locks"):
        sf._locks.clear()
    for cache in getattr(cache_registry, "_caches", {}).values():
        cache.clear()
    yield
    # Post-test: clear AGAIN so cache state from this test cannot leak
    # into tests in OTHER test directories (which don't share this
    # autouse fixture). Critical after 26-04 wired /scores/top and
    # /market/summary into the cache: a populated cache from a perf
    # test would change the routing decisions of pre-existing
    # `test_market_route` mock-based tests (run order: test_cache →
    # test_market_route).
    if hasattr(sf, "_locks"):
        sf._locks.clear()
    for cache in getattr(cache_registry, "_caches", {}).values():
        cache.clear()


@pytest_asyncio.fixture(autouse=True)
async def _reset_db_singletons():
    """Dispose + null-out the singleton engine before AND after each test.

    Pre-test reset: prior tests may have left the singleton bound to a
    closed loop; nulling it forces ``get_engine()`` to build fresh.

    Post-test dispose: returns the engine's connections cleanly so the
    next test's loop doesn't inherit zombie connections.
    """
    from localstock.db import database as dbmod

    if dbmod._engine is not None:
        try:
            await dbmod._engine.dispose()
        except Exception:
            pass
        dbmod._engine = None
        dbmod._session_factory = None

    yield

    if dbmod._engine is not None:
        try:
            await dbmod._engine.dispose()
        except Exception:
            pass
        dbmod._engine = None
        dbmod._session_factory = None
    # Drain any pending tasks asyncpg created during dispose.
    await asyncio.sleep(0)
