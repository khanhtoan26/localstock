"""Phase 23 — metric primitive unit tests (T1–T7 from 23-VALIDATION.md)."""
from __future__ import annotations

import importlib

import pytest
from prometheus_client import CollectorRegistry

from localstock.observability.metrics import (
    PIPELINE_STEP_BUCKETS,
    init_metrics,
)

EXPECTED_FAMILIES = {
    "http_requests_total",
    "op_duration_seconds", "op_total",
    "cache_hits_total", "cache_misses_total", "cache_evictions_total",
    "db_query_duration_seconds", "db_query_total", "db_query_slow_total",
    "pipeline_step_duration_seconds", "pipeline_step_total",
    "pipeline_step_inprogress",
    "dq_validation_failures_total", "dq_validation_total",
}

# D-06 budget — labelnames frozen per family (registry name -> labelnames tuple)
EXPECTED_LABELS = {
    "localstock_http_requests_total":               ("method", "status_class"),
    "localstock_op_duration_seconds":               ("domain", "subsystem", "action", "outcome"),
    "localstock_op_total":                          ("domain", "subsystem", "action", "outcome"),
    "localstock_cache_hits_total":                  ("cache_name",),
    "localstock_cache_misses_total":                ("cache_name",),
    "localstock_cache_evictions_total":             ("cache_name", "reason"),
    "localstock_db_query_duration_seconds":         ("query_type", "table_class"),
    "localstock_db_query_total":                    ("query_type", "table_class", "outcome"),
    "localstock_db_query_slow_total":               ("query_type", "table_class"),
    "localstock_pipeline_step_duration_seconds":    ("step", "outcome"),
    "localstock_pipeline_step_total":               ("step", "outcome"),
    "localstock_pipeline_step_inprogress":          ("step",),
    "localstock_dq_validation_failures_total":      ("validator", "severity"),
    "localstock_dq_validation_total":               ("validator", "outcome"),
}


def test_metrics_module_level_import_does_not_raise() -> None:
    """OBS-08 — pure import + reload succeeds (D-04 idempotency)."""
    import localstock.observability.metrics as m
    importlib.reload(m)


def test_init_metrics_returns_all_primitive_families(
    metrics_registry: CollectorRegistry,
) -> None:
    """OBS-08 — every metric family expected by Phase 24 is registered."""
    metrics = init_metrics(metrics_registry)
    missing = EXPECTED_FAMILIES - set(metrics.keys())
    assert not missing, f"Missing metric families: {missing}"


def test_metrics_namespace_prefix(
    metrics_registry: CollectorRegistry,
) -> None:
    """D-01 — every custom metric name starts with 'localstock_'."""
    init_metrics(metrics_registry)
    for collector in list(metrics_registry._collector_to_names.keys()):
        name = getattr(collector, "_name", "")
        assert name.startswith("localstock_"), f"Non-namespaced metric: {name!r}"


def test_pipeline_step_histogram_buckets(
    metrics_registry: CollectorRegistry,
) -> None:
    """D-03 — pipeline_step_duration_seconds uses minute-scale buckets."""
    metrics = init_metrics(metrics_registry)
    hist = metrics["pipeline_step_duration_seconds"]
    bounds = tuple(hist._upper_bounds[:-1])  # last is +Inf
    assert bounds == PIPELINE_STEP_BUCKETS


def test_no_metric_has_symbol_label(
    metrics_registry: CollectorRegistry,
) -> None:
    """OBS-09 — 'symbol' MUST NEVER be a label (high cardinality, use logs)."""
    init_metrics(metrics_registry)
    for collector in list(metrics_registry._collector_to_names.keys()):
        labelnames = tuple(getattr(collector, "_labelnames", ()))
        assert "symbol" not in labelnames, (
            f"Forbidden 'symbol' label found on {collector._name}"
        )


def test_label_schema_matches_budget(
    metrics_registry: CollectorRegistry,
) -> None:
    """OBS-09 / D-06 — label sets per family are frozen at the budgeted shape."""
    init_metrics(metrics_registry)
    for collector in list(metrics_registry._collector_to_names.keys()):
        name = getattr(collector, "_name", "")
        if name not in EXPECTED_LABELS:
            continue  # skip instrumentator defaults if any leak in
        actual = tuple(getattr(collector, "_labelnames", ()))
        assert actual == EXPECTED_LABELS[name], (
            f"{name}: labels {actual} != budget {EXPECTED_LABELS[name]}"
        )


def test_init_metrics_idempotent_on_same_registry(
    metrics_registry: CollectorRegistry,
) -> None:
    """OBS-10 — second init_metrics() call MUST NOT raise; returns same instances."""
    first = init_metrics(metrics_registry)
    second = init_metrics(metrics_registry)
    assert set(first.keys()) == set(second.keys())
    for key in first:
        assert first[key] is second[key], f"{key} re-created instead of reused"
