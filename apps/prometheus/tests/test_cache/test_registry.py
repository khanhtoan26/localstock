"""Phase 26 / 26-01 — Registry contract tests (D-02 TTL table)."""
from __future__ import annotations


def test_all_namespaces_registered():
    from localstock.cache.registry import REGISTERED_NAMESPACES, get_cache

    for ns in (
        "scores:ranking", "scores:symbol", "market:summary",
        "indicators", "pipeline:latest_run_id",
    ):
        assert ns in REGISTERED_NAMESPACES
        cache = get_cache(ns)
        assert cache is not None


def test_ttl_values_match_d02():
    from localstock.cache.registry import _caches

    # InstrumentedTTLCache exposes .ttl
    assert _caches["scores:ranking"].ttl == 86400
    assert _caches["market:summary"].ttl == 3600
    assert _caches["indicators"].ttl == 3600
    assert _caches["pipeline:latest_run_id"].ttl == 5


def test_eviction_counter_on_overflow():
    """Q-2 — popitem-on-overflow increments cache_evictions_total{reason='evict'}."""
    from localstock.cache.registry import InstrumentedTTLCache
    from localstock.observability.metrics import get_metrics

    cache = InstrumentedTTLCache(maxsize=2, ttl=3600, namespace="test:evict")
    m = get_metrics()
    before = m["cache_evictions_total"].labels(
        cache_name="test:evict", reason="evict"
    )._value.get()
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3  # overflow → evicts "a"
    after = m["cache_evictions_total"].labels(
        cache_name="test:evict", reason="evict"
    )._value.get()
    assert after - before >= 1
