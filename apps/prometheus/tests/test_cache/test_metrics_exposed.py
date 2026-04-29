"""Phase 26 / 26-02 / D-08 — verify cache counter surface on /metrics.

Closes ROADMAP SC #5: `/metrics` exposes the five canonical cache counters
with bounded cardinality (label set = `cache_name` only, except evictions
which carries an additional `reason` label per Q-2).
"""
from __future__ import annotations

import pytest
from prometheus_client import REGISTRY


REQUIRED = {
    "localstock_cache_hits_total",
    "localstock_cache_misses_total",
    "localstock_cache_evictions_total",
    "localstock_cache_compute_total",
    "localstock_cache_prewarm_errors_total",
}


def test_all_cache_metrics_registered():
    names = {m.name for m in REGISTRY.collect()}
    # prometheus_client strips the _total suffix from .name; allow either form
    present = names | {f"{n}_total" for n in names}
    missing = REQUIRED - present
    assert not missing, f"missing counters: {missing}"


def test_label_is_cache_name_not_namespace():
    from localstock.observability.metrics import get_metrics

    m = get_metrics()
    # Must accept cache_name kwarg
    m["cache_compute_total"].labels(cache_name="scores:ranking").inc(0)
    # Must NOT accept namespace kwarg (would raise)
    with pytest.raises((ValueError, KeyError)):
        m["cache_compute_total"].labels(namespace="scores:ranking").inc(0)


def test_cardinality_bounded():
    """Per D-08: only `cache_name` label, no per-key labels."""
    from localstock.observability.metrics import get_metrics

    m = get_metrics()
    for n in (
        "cache_hits_total",
        "cache_misses_total",
        "cache_compute_total",
        "cache_prewarm_errors_total",
    ):
        counter = m[n]
        assert counter._labelnames == ("cache_name",), (
            f"{n} has unexpected labels: {counter._labelnames}"
        )
    # cache_evictions_total has the extra `reason` label per Q-2
    assert m["cache_evictions_total"]._labelnames == ("cache_name", "reason")
