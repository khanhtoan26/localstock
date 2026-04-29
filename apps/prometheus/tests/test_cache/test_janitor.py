"""Phase 26 / CACHE-06 — cache_janitor APScheduler 60s sweep (SC #5)."""
from __future__ import annotations

import time

import pytest


@pytest.mark.asyncio
async def test_janitor_sweeps_expired_entries():
    """Insert into a tiny-TTL cache, wait for expiry, run janitor."""
    from localstock.cache import get_or_compute
    from localstock.cache.janitor import cache_janitor
    from localstock.cache.registry import InstrumentedTTLCache, _caches

    original = _caches.get("scores:ranking")
    _caches["scores:ranking"] = InstrumentedTTLCache(
        maxsize=10, ttl=0.1, namespace="scores:ranking",
    )
    try:
        async def c():
            return 1

        await get_or_compute("scores:ranking", "x", c)
        assert len(_caches["scores:ranking"]) == 1

        time.sleep(0.15)

        swept = await cache_janitor()
        assert swept.get("scores:ranking", 0) >= 1
        assert len(_caches["scores:ranking"]) == 0
    finally:
        if original is not None:
            _caches["scores:ranking"] = original


@pytest.mark.asyncio
async def test_janitor_returns_dict_for_all_namespaces():
    from localstock.cache.janitor import cache_janitor

    result = await cache_janitor()
    assert isinstance(result, dict)
    for ns in (
        "scores:ranking",
        "scores:symbol",
        "market:summary",
        "indicators",
        "pipeline:latest_run_id",
    ):
        assert ns in result, f"namespace {ns} not swept"


@pytest.mark.asyncio
async def test_janitor_emits_expire_eviction_counter():
    """Q-2 — popitem during expire() bumps reason='expire'."""
    from localstock.cache import get_or_compute
    from localstock.cache.janitor import cache_janitor
    from localstock.cache.registry import InstrumentedTTLCache, _caches
    from localstock.observability.metrics import get_metrics

    original = _caches.get("market:summary")
    _caches["market:summary"] = InstrumentedTTLCache(
        maxsize=10, ttl=0.1, namespace="market:summary",
    )
    try:
        async def c():
            return 1

        await get_or_compute("market:summary", "y", c)

        m = get_metrics()
        before = (
            m["cache_evictions_total"]
            .labels(cache_name="market:summary", reason="expire")
            ._value.get()
        )

        time.sleep(0.15)
        await cache_janitor()

        after = (
            m["cache_evictions_total"]
            .labels(cache_name="market:summary", reason="expire")
            ._value.get()
        )
        assert after - before >= 1, (
            "TTL expiration did not increment reason='expire' counter"
        )
    finally:
        if original is not None:
            _caches["market:summary"] = original


def test_janitor_registered_in_scheduler():
    """The scheduler registers cache_janitor with 60s IntervalTrigger."""
    from localstock.scheduler.scheduler import setup_scheduler

    sched = setup_scheduler()
    try:
        job = sched.get_job("cache_janitor")
        assert job is not None, "cache_janitor job not registered"
        assert job.trigger.interval.total_seconds() == 60
        assert job.max_instances == 1
        assert job.coalesce is True
    finally:
        # Remove job so other tests don't see leftover registration
        try:
            sched.remove_job("cache_janitor")
        except Exception:
            pass
