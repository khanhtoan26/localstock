"""Phase 26 / 26-01 — Single-flight + ROADMAP SC #3 verbatim test."""
from __future__ import annotations

import asyncio

import pytest

from localstock.cache import get_or_compute
from localstock.observability.metrics import get_metrics


@pytest.mark.asyncio
async def test_concurrent_cold_key_single_compute():
    """ROADMAP SC #3 — 100 racers, exactly 1 compute_fn invocation."""
    compute_calls = 0

    async def slow_compute():
        nonlocal compute_calls
        compute_calls += 1
        await asyncio.sleep(0.05)
        return {"value": 42}

    m = get_metrics()
    before = m["cache_compute_total"].labels(
        cache_name="scores:ranking"
    )._value.get()

    results = await asyncio.gather(*[
        get_or_compute(
            namespace="scores:ranking",
            key="run=1",
            compute_fn=slow_compute,
        )
        for _ in range(100)
    ])

    after = m["cache_compute_total"].labels(
        cache_name="scores:ranking"
    )._value.get()

    assert compute_calls == 1, f"compute_fn ran {compute_calls}× (expected 1)"
    assert after - before == 1, f"counter delta = {after - before}"
    assert all(r == {"value": 42} for r in results)


@pytest.mark.asyncio
async def test_second_call_is_hit():
    async def compute():
        return "v"

    await get_or_compute("scores:ranking", "k", compute)
    m = get_metrics()
    before_hits = m["cache_hits_total"].labels(
        cache_name="scores:ranking"
    )._value.get()
    v = await get_or_compute("scores:ranking", "k", compute)
    after_hits = m["cache_hits_total"].labels(
        cache_name="scores:ranking"
    )._value.get()
    assert v == "v"
    assert after_hits - before_hits == 1


@pytest.mark.asyncio
async def test_outcome_contextvar_set():
    from localstock.cache import cache_outcome_var

    async def compute():
        return 1

    await get_or_compute("scores:ranking", "ctx", compute)
    # After miss, contextvar was set to "miss" (set inside the lock).
    assert cache_outcome_var.get() == "miss"
    await get_or_compute("scores:ranking", "ctx", compute)
    assert cache_outcome_var.get() == "hit"
