"""Phase 23 — Prometheus metric primitives for LocalStock.

All custom metrics use the ``localstock_`` namespace prefix (CONTEXT.md D-01).
Library defaults from prometheus-fastapi-instrumentator (``http_request_duration_seconds``,
``http_requests_inprogress``) are NOT redefined here — they are produced by the
Instrumentator middleware and keep their original names per D-01 exception.

Idempotent: ``init_metrics(registry)`` may be called multiple times on the same
registry without raising ``ValueError: Duplicated timeseries...`` (D-04, OBS-10).

CRITICAL (D-06, OBS-09): NO metric in this module declares a ``symbol`` label.
High-cardinality identifiers (ticker symbols) belong in structured logs only.
"""
from __future__ import annotations

import weakref
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# Phase 25 / DQ-02 — track every registry that ``init_metrics`` has been
# called against so that downstream dispatchers (``evaluate_tier2``) can
# increment the matching collector on each one. Test fixtures pass a
# fresh ``CollectorRegistry`` and read back via ``reg.get_sample_value``,
# so the dispatcher must find the collector on that very registry — the
# global ``REGISTRY`` is not enough. WeakSet so test registries are
# collected once their fixtures go out of scope.
_TRACKED_REGISTRIES: "weakref.WeakSet[CollectorRegistry]" = weakref.WeakSet()


def iter_tracked_collectors(name: str):
    """Yield each distinct collector registered under ``name`` across all
    registries seen by ``init_metrics`` (Phase 25 / DQ-02).

    Deduped by ``id()`` — calling ``init_metrics`` twice on the same
    registry will not double-increment.
    """
    seen: set[int] = set()
    for reg in list(_TRACKED_REGISTRIES):
        coll = reg._names_to_collectors.get(name)
        if coll is not None and id(coll) not in seen:
            seen.add(id(coll))
            yield coll
    # Always also check the global default REGISTRY (production path).
    try:
        from prometheus_client import REGISTRY as _GLOBAL

        coll = _GLOBAL._names_to_collectors.get(name)
        if coll is not None and id(coll) not in seen:
            yield coll
    except Exception:  # noqa: BLE001
        return

# === Bucket constants (CONTEXT.md D-03) ===

HTTP_LATENCY_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10,
)
DB_QUERY_BUCKETS: tuple[float, ...] = (
    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5,
)
PIPELINE_STEP_BUCKETS: tuple[float, ...] = (
    1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600,
)
OP_DURATION_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10,
)


def init_metrics(registry: CollectorRegistry | None = None) -> dict[str, Any]:
    """Register all LocalStock metric primitives on ``registry``.

    Idempotent: safe to call multiple times. If a collector with the same name
    already exists in ``registry``, the existing instance is returned instead
    of raising ``ValueError`` (CONTEXT.md D-04, OBS-10).

    Args:
        registry: Target registry. ``None`` -> default ``prometheus_client.REGISTRY``.
            Tests should pass a fresh ``CollectorRegistry()`` to avoid leakage.

    Returns:
        Dict mapping metric short-name -> collector instance. Keys are stable
        across calls so callers can do ``init_metrics(reg)["http_requests_total"]``.
    """
    target = registry  # None means prometheus_client default REGISTRY
    if target is None:
        # NOTE: prometheus_client treats ``registry=None`` as "do not register"
        # (its default kwarg is ``REGISTRY``, not ``None``). Without this fix,
        # ``init_metrics()`` creates orphan collectors detached from the default
        # registry — invisible to ``/metrics`` and to the @observe decorator
        # lookup. Resolve to the actual default REGISTRY so production callers
        # get registered metrics. (Phase 24-01 Rule-3 fix; Phase 23 latent bug.)
        target = _get_default_registry()

    # Phase 25 / DQ-02 — register the resolved registry for downstream
    # multi-registry dispatch (see ``iter_tracked_collectors``).
    try:
        _TRACKED_REGISTRIES.add(target)
    except TypeError:
        pass  # Some registry impls may not be weak-referenceable; skip.

    def _register(factory, name: str):
        """Create-or-fetch helper. Catches duplicate-name ValueError."""
        try:
            return factory()
        except ValueError:
            # Already registered — fetch existing collector.
            # ``_names_to_collectors`` is private but stable since prometheus_client 0.8.
            reg = target if target is not None else _get_default_registry()
            existing = reg._names_to_collectors.get(name)
            if existing is None:
                raise  # Different ValueError; re-raise.
            return existing

    metrics: dict[str, Any] = {}

    # === HTTP metrics (D-06: labels = method, status_class) ===
    # NOTE: ``http_request_duration_seconds`` and ``http_requests_inprogress``
    # are produced by prometheus-fastapi-instrumentator — NOT defined here (D-01).
    metrics["http_requests_total"] = _register(
        lambda: Counter(
            "localstock_http_requests_total",
            "Total HTTP requests handled by LocalStock API.",
            labelnames=("method", "status_class"),
            registry=target,
        ),
        "localstock_http_requests_total",
    )

    # === Operation metrics (op_*) — generic instrumentation surface for Phase 24 ===
    # D-06: labels = domain, subsystem, action, outcome
    metrics["op_duration_seconds"] = _register(
        lambda: Histogram(
            "localstock_op_duration_seconds",
            "Duration of business operations decorated with @observe.",
            labelnames=("domain", "subsystem", "action", "outcome"),
            buckets=OP_DURATION_BUCKETS,
            registry=target,
        ),
        "localstock_op_duration_seconds",
    )
    metrics["op_total"] = _register(
        lambda: Counter(
            "localstock_op_total",
            "Total business operations executed.",
            labelnames=("domain", "subsystem", "action", "outcome"),
            registry=target,
        ),
        "localstock_op_total",
    )

    # === Cache metrics ===
    metrics["cache_hits_total"] = _register(
        lambda: Counter(
            "localstock_cache_hits_total",
            "Total cache hits.",
            labelnames=("cache_name",),
            registry=target,
        ),
        "localstock_cache_hits_total",
    )
    metrics["cache_misses_total"] = _register(
        lambda: Counter(
            "localstock_cache_misses_total",
            "Total cache misses.",
            labelnames=("cache_name",),
            registry=target,
        ),
        "localstock_cache_misses_total",
    )
    metrics["cache_evictions_total"] = _register(
        lambda: Counter(
            "localstock_cache_evictions_total",
            "Total cache evictions / expirations.",
            labelnames=("cache_name", "reason"),  # reason ∈ evict|expire
            registry=target,
        ),
        "localstock_cache_evictions_total",
    )
    # Phase 26 / 26-01 (B1: 26-01 owns this declaration; 26-02 will add
    # cache_prewarm_errors_total separately in a disjoint region of this
    # block so Wave-1 parallel execution is merge-safe).
    metrics["cache_compute_total"] = _register(
        lambda: Counter(
            "localstock_cache_compute_total",
            "Cache cold-fill computations (single-flight gate; SC #3).",
            labelnames=("cache_name",),
            registry=target,
        ),
        "localstock_cache_compute_total",
    )

    # === DB query metrics (D-06: labels = query_type, table_class) ===
    metrics["db_query_duration_seconds"] = _register(
        lambda: Histogram(
            "localstock_db_query_duration_seconds",
            "SQLAlchemy query execution duration.",
            labelnames=("query_type", "table_class"),
            buckets=DB_QUERY_BUCKETS,
            registry=target,
        ),
        "localstock_db_query_duration_seconds",
    )
    metrics["db_query_total"] = _register(
        lambda: Counter(
            "localstock_db_query_total",
            "Total SQLAlchemy queries executed.",
            labelnames=("query_type", "table_class", "outcome"),
            registry=target,
        ),
        "localstock_db_query_total",
    )

    # === Slow query counter (Phase 24, D-04, OBS-13) ===
    metrics["db_query_slow_total"] = _register(
        lambda: Counter(
            "localstock_db_query_slow_total",
            "Queries exceeding slow_query_threshold_ms.",
            labelnames=("query_type", "table_class"),
            registry=target,
        ),
        "localstock_db_query_slow_total",
    )

    # === Pipeline step metrics (D-06: labels = step, outcome) ===
    metrics["pipeline_step_duration_seconds"] = _register(
        lambda: Histogram(
            "localstock_pipeline_step_duration_seconds",
            "Duration of crawler / analyzer / scoring / report pipeline steps.",
            labelnames=("step", "outcome"),
            buckets=PIPELINE_STEP_BUCKETS,
            registry=target,
        ),
        "localstock_pipeline_step_duration_seconds",
    )
    metrics["pipeline_step_total"] = _register(
        lambda: Counter(
            "localstock_pipeline_step_total",
            "Total pipeline step executions.",
            labelnames=("step", "outcome"),
            registry=target,
        ),
        "localstock_pipeline_step_total",
    )
    metrics["pipeline_step_inprogress"] = _register(
        lambda: Gauge(
            "localstock_pipeline_step_inprogress",
            "Pipeline steps currently executing.",
            labelnames=("step",),
            registry=target,
        ),
        "localstock_pipeline_step_inprogress",
    )

    # === Data Quality metrics (D-06: labels = validator, severity) ===
    metrics["dq_validation_failures_total"] = _register(
        lambda: Counter(
            "localstock_dq_validation_failures_total",
            "Total data-quality validation failures.",
            labelnames=("validator", "severity"),  # severity ∈ block|warn
            registry=target,
        ),
        "localstock_dq_validation_failures_total",
    )
    metrics["dq_validation_total"] = _register(
        lambda: Counter(
            "localstock_dq_validation_total",
            "Total data-quality validations performed.",
            labelnames=("validator", "outcome"),  # outcome ∈ pass|fail
            registry=target,
        ),
        "localstock_dq_validation_total",
    )

    # === Phase 25 / DQ-02 — Tier 2 violation counter (D-06) ===
    # NOTE: distinct from dq_validation_failures_total above.
    # That tracks Tier 1 schema-validate-stage outcomes (validator, severity).
    # THIS tracks per-rule violations with shadow/strict tier label so the
    # 14-day shadow → strict promotion is visible in the same series.
    # NEVER add a `symbol` label (Phase 23 D-06 / OBS-09 hard rule).
    metrics["dq_violations_total"] = _register(
        lambda: Counter(
            "localstock_dq_violations_total",
            "Total DQ rule violations (Tier 1 strict + Tier 2 shadow/enforce).",
            labelnames=("rule", "tier"),  # tier ∈ advisory|strict
            registry=target,
        ),
        "localstock_dq_violations_total",
    )

    # === Phase 24-05 — Self-probe gauges (D-05, OBS-15) ===
    metrics["db_pool_size"] = _register(
        lambda: Gauge(
            "localstock_db_pool_size",
            "Current SQLAlchemy connection pool size.",
            registry=target,
        ),
        "localstock_db_pool_size",
    )
    metrics["db_pool_checked_out"] = _register(
        lambda: Gauge(
            "localstock_db_pool_checked_out",
            "Connections currently checked out of the pool.",
            registry=target,
        ),
        "localstock_db_pool_checked_out",
    )
    metrics["last_pipeline_age_seconds"] = _register(
        lambda: Gauge(
            "localstock_last_pipeline_age_seconds",
            "Seconds since the last completed pipeline run.",
            registry=target,
        ),
        "localstock_last_pipeline_age_seconds",
    )
    metrics["last_crawl_success_count"] = _register(
        lambda: Gauge(
            "localstock_last_crawl_success_count",
            "symbols_success of the most recent PipelineRun.",
            registry=target,
        ),
        "localstock_last_crawl_success_count",
    )

    # === Phase 24-05 — Scheduler errors (D-06, OBS-16) ===
    metrics["scheduler_job_errors_total"] = _register(
        lambda: Counter(
            "localstock_scheduler_job_errors_total",
            "Unhandled exceptions raised by APScheduler jobs.",
            labelnames=("job_id", "error_type"),
            registry=target,
        ),
        "localstock_scheduler_job_errors_total",
    )

    return metrics


def _get_default_registry() -> CollectorRegistry:
    """Return the prometheus_client default REGISTRY (lazy import to keep
    module-level import cheap and to make patching easier in tests)."""
    from prometheus_client import REGISTRY
    return REGISTRY


# Module-level eager init against default REGISTRY.
# Production: ``init_metrics()`` is also called explicitly from the FastAPI
# lifespan after ``configure_logging()`` so structured logs capture any failure.
# The double-call is intentional and idempotent (D-04).
_DEFAULT_METRICS = init_metrics()


def get_metrics() -> dict[str, Any]:
    """Return the module-level default metrics dict.

    Phase 26 / 26-01 — accessor for ``localstock.cache`` and tests so
    callers don't import the private ``_DEFAULT_METRICS`` name. Always
    returns the same dict; idempotent re-init via ``init_metrics`` keeps
    collectors stable.
    """
    return _DEFAULT_METRICS
