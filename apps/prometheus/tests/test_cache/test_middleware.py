"""Phase 26 / 26-02 / D-08 — CacheHeaderMiddleware contract (P-4).

Verifies:
  * Routes that call ``get_or_compute`` get ``X-Cache: miss`` on cold
    fill and ``X-Cache: hit`` on subsequent calls.
  * Routes that don't touch the cache emit no header.
  * The ContextVar is reset between requests so a non-caching request
    after a caching one does NOT inherit a stale outcome (P-4 boundary).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from localstock.cache import get_or_compute
from localstock.cache.middleware import CacheHeaderMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CacheHeaderMiddleware)

    @app.get("/cached")
    async def cached_endpoint():
        async def compute():
            return {"ok": True}

        return await get_or_compute("scores:ranking", "test", compute)

    @app.get("/uncached")
    async def uncached_endpoint():
        return {"ok": True}

    return app


def test_cached_route_emits_miss_then_hit():
    client = TestClient(_build_app())
    r1 = client.get("/cached")
    assert r1.status_code == 200
    assert r1.headers.get("X-Cache") == "miss"
    r2 = client.get("/cached")
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "hit"


def test_uncached_route_emits_no_header():
    client = TestClient(_build_app())
    r = client.get("/uncached")
    assert r.status_code == 200
    assert "X-Cache" not in r.headers


def test_contextvar_reset_between_requests():
    """P-4 — middleware resets ContextVar so a non-caching request after
    a caching one does not inherit a stale outcome."""
    client = TestClient(_build_app())
    client.get("/cached")
    r = client.get("/uncached")
    assert "X-Cache" not in r.headers
