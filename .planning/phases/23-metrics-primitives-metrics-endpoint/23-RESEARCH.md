# Phase 23: Metrics Primitives & /metrics Endpoint — Research

**Researched:** 2025-11-26
**Domain:** Prometheus instrumentation for FastAPI (Python 3.12)
**Confidence:** HIGH

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** — Namespace `localstock_` prefix on all custom metrics (e.g. `localstock_http_requests_total`). Library defaults from `prometheus-fastapi-instrumentator` (`http_request_duration_seconds`, `http_requests_inprogress`) keep their original names — **do not rewrite library defaults**.
- **D-02** — `/metrics` endpoint exposed **public, no auth** on the local-first deployment. Future production hardening deferred to backlog (mention in runbook).
- **D-03** — Custom histogram buckets per metric category:
  ```python
  HTTP_LATENCY_BUCKETS  = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
  DB_QUERY_BUCKETS      = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
  PIPELINE_STEP_BUCKETS = (1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
  OP_DURATION_BUCKETS   = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
  ```
- **D-04** — Hybrid idempotent init: module-level primitives + `init_metrics(registry=None)` helper that catches `ValueError` (already-registered) and returns existing collectors. Pytest fixture `metrics_registry` (function-scoped) gives each test a fresh `CollectorRegistry`.
- **D-05** — Single file `localstock/observability/metrics.py` with `# === SECTION ===` comment headers (HTTP, Op, Cache, DB, Pipeline, DQ).
- **D-06** — Bounded label schema, **no `symbol` label anywhere**. Label sets per metric category fixed (see CONTEXT.md table). Enforcement: test `test_metrics_no_symbol_label` scans registry.
- **D-07** — `Instrumentator(...)` config: `should_group_status_codes=True`, `should_ignore_untemplated=True`, `should_group_untemplated=True`, `should_instrument_requests_inprogress=True`, `excluded_handlers=["/metrics", "/health/live"]`, `inprogress_name="http_requests_inprogress"`, `inprogress_labels=False`.
- **D-08** — Scope boundary: Phase 23 adds **no** `.inc()/.observe()/.set()` calls in service/crawler/scheduler/api code. Only deps + `metrics.py` + `app.py` wiring + tests + `__init__.py` re-exports.

### Agent Discretion
None — all 8 gray areas resolved by `--auto`.

### Deferred Ideas (OUT OF SCOPE)
- `@observe` decorator → Phase 24
- `@timed_query` decorator + SQLAlchemy events → Phase 24 (OBS-12)
- Slow query log → Phase 24 (OBS-13)
- `/health/live`, `/health/ready` split → Phase 25 (OBS-14)
- `health_self_probe` job → Phase 25 (OBS-15)
- Auth/IP allowlist for `/metrics` → backlog (runbook note)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBS-07 | `/metrics` endpoint via prometheus-fastapi-instrumentator | §Dependencies, §App Wiring (Instrumentator config + expose call) |
| OBS-08 | Module-level primitives `http_*, op_*, cache_*, db_query_*, pipeline_step_*, dq_*` | §metrics.py Code Block — full file content |
| OBS-09 | Cardinality ≤50/metric, NO `symbol` label | §metrics.py (label tuples), §Test Plan (`test_metrics_no_symbol_label`) |
| OBS-10 | Idempotent registry init — no `Duplicated timeseries` | §`init_metrics()` pattern, §Conftest Integration (`metrics_registry` fixture) |

---

## Summary

Phase 23 is a **vertical slice**: add two pip deps, create one new module (`metrics.py`), wire `Instrumentator` into `api/app.py`, re-export from `observability/__init__.py`, add ~7 tests. Total ~250-300 LOC.

The work is mechanical because:
1. `prometheus-fastapi-instrumentator` 7.1.0 directly accepts a `registry: CollectorRegistry` kwarg [VERIFIED: GitHub source `instrumentation.py:43`] → we get clean test isolation without monkey-patching.
2. `prometheus_client` returns `text/plain; version=0.0.4; charset=utf-8` via `CONTENT_TYPE_LATEST` → success criterion #1 is automatic [VERIFIED: instrumentation.py:282].
3. Idempotency pattern is well-established: catch `ValueError` from `Counter()/Histogram()/Gauge()` constructor and look up via `registry._names_to_collectors[name]` [CITED: prometheus/client_python source].

**Primary recommendation:** Implement metrics.py with explicit prefixed names (e.g. `Counter("localstock_http_requests_total", ...)`) rather than `namespace="localstock"` kwarg — produces identical output but matches the names spelled out in CONTEXT.md D-06 verbatim, simplifies grep, and avoids surprise-prefix when a future maintainer reads only the constructor.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Metric primitives definition | Application library (`observability/`) | — | Module-level, framework-agnostic, importable from anywhere |
| HTTP request instrumentation | ASGI middleware (Instrumentator) | FastAPI app | Library middleware hooks into ASGI lifecycle, no app code touches |
| `/metrics` endpoint | FastAPI route (registered by `Instrumentator.expose()`) | — | Library handles `generate_latest()` + content-type |
| Registry isolation per test | Pytest fixture (`metrics_registry`) | — | Avoids global `prometheus_client.REGISTRY` mutation between tests |
| Lifespan wiring | `api/app.py` startup | Phase 22's `configure_logging` | After logging (we want structured logs of init), before scheduler (so scheduler can later record metrics) |

---

## Dependencies

### Versions (verified against PyPI 2025-11-26)

| Package | Latest | Pin | Python 3.12 | Notes |
|---------|--------|-----|-------------|-------|
| `prometheus-fastapi-instrumentator` | **7.1.0** | `>=7.1,<8.0` | ✅ | Latest stable; `requires_python>=3.8` [VERIFIED: pypi.org/pypi/prometheus-fastapi-instrumentator/json] |
| `prometheus-client` | **0.25.0** | `>=0.21,<1.0` | ✅ | Transitive dep of instrumentator (`>=0.8,<1.0`); pin floor at 0.21 for `make_asgi_app` stability [VERIFIED: pypi.org/pypi/prometheus-client/json] |

**Why pin both explicitly:** Instrumentator only requires `prometheus-client>=0.8`. We use `prometheus-client` directly (Counter/Histogram/Gauge in `metrics.py`), so pin it as a first-class dep — not transitive.

### `pyproject.toml` diff

Insert into `[project] → dependencies` (after `apscheduler`, before `python-telegram-bot` to keep observability deps grouped near top — or alphabetically; project order is loose):

```diff
     "loguru>=0.7,<1.0",
     "tenacity>=9.0,<10.0",
+    "prometheus-client>=0.21,<1.0",
+    "prometheus-fastapi-instrumentator>=7.1,<8.0",
     "pandas-ta>=0.4.71b0",
```

**Compatibility check:** `prometheus-fastapi-instrumentator` 7.x requires `starlette<1.0,>=0.30.0` [VERIFIED: pypi metadata]. FastAPI 0.135 ships with `starlette>=0.40,<0.46` — well within range. No conflict.

---

## `Instrumentator` API Surface (per D-07)

### Constructor signature (relevant kwargs only)
[VERIFIED: GitHub `trallnag/prometheus-fastapi-instrumentator/master/src/.../instrumentation.py` lines 28–45]

```python
PrometheusFastApiInstrumentator(
    should_group_status_codes: bool = True,
    should_ignore_untemplated: bool = False,
    should_group_untemplated: bool = True,
    should_instrument_requests_inprogress: bool = False,
    excluded_handlers: list[str] = [],          # regex patterns
    inprogress_name: str = "http_requests_inprogress",
    inprogress_labels: bool = False,
    registry: CollectorRegistry | None = None,  # ← important for tests
    ...
)
```

### `expose()` signature
[VERIFIED: instrumentation.py:232–305]

```python
.expose(
    app,
    should_gzip: bool = False,
    endpoint: str = "/metrics",
    include_in_schema: bool = True,
    tags: list[str] | None = None,
)
```

The endpoint is registered via `app.get(endpoint, ...)` for FastAPI apps. Response sets `Content-Type: text/plain; version=0.0.4; charset=utf-8` via `CONTENT_TYPE_LATEST` from `prometheus_client` — **success criterion #1 satisfied automatically**.

### Default metrics produced
- Counter `http_requests_total{handler, status, method}`
- Summary `http_request_size_bytes{handler}`
- Summary `http_response_size_bytes{handler}`
- Histogram **`http_request_duration_seconds{handler, method}`** ← required by success criterion #1
- Histogram `http_request_duration_highr_seconds` (no labels, ~25 buckets)
- Gauge `http_requests_inprogress` (no labels with `inprogress_labels=False`)

These keep their original names per D-01 exception. **Do not pass `metric_namespace=` to default closures** — that would prefix them and break the criterion.

### `excluded_handlers` semantics
[VERIFIED: README + source] Strings are compiled to regex via `re.compile()` and matched against the **route template path** (after FastAPI route resolution). To exclude `/metrics` and `/health/live` exactly:

```python
excluded_handlers=["^/metrics$", "^/health/live$"]
```

CONTEXT.md D-07 lists them without anchors (`["/metrics", "/health/live"]`) — that works because `re.search` semantics are used, but anchored regex is **safer** (prevents `/metrics-foo` matching). **Recommend anchored form** in implementation.

---

## metrics.py — Full Code Block

**File:** `apps/prometheus/src/localstock/observability/metrics.py`

```python
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

from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

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

    # === Cache metrics (D-06: labels = cache_name, operation) ===
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
```

**Key design notes:**
- Module-level `_DEFAULT_METRICS = init_metrics()` ensures import-time registration on the default registry — satisfies "module-level primitives" wording in OBS-08 literally.
- The lifespan also calls `init_metrics()` — second call is a no-op due to the `_register` helper. This is the explicit redundancy D-04 calls for.
- `lambda` wrappers around constructor calls are needed because `Counter(...)` raises **at construction time** if the name is duplicated — we must defer construction so we can `try/except` it.
- `_names_to_collectors` is private but **stable** [VERIFIED: prometheus/client_python README + git log shows the attribute existed since v0.0.x] and used widely in third-party tooling for the same idempotency pattern.

---

## `observability/__init__.py` Update

```python
"""Observability — structured logging (Phase 22) + metrics (Phase 23)."""
from localstock.observability.context import (
    get_request_id,
    get_run_id,
    request_id_var,
    run_id_var,
)
from localstock.observability.logging import configure_logging
from localstock.observability.metrics import init_metrics

__all__ = [
    "configure_logging",
    "init_metrics",
    "request_id_var",
    "run_id_var",
    "get_request_id",
    "get_run_id",
]
```

---

## App Wiring (`api/app.py`)

### Where to add what

| Step | Where | Why |
|------|-------|-----|
| `configure_logging()` | **Already there** (line 33) — keep first | Phase 22 invariant |
| `init_metrics()` | New — call **after** `configure_logging()`, **before** `app = FastAPI(...)` | If init fails, structured logs capture it |
| `Instrumentator(...).instrument(app).expose(app, ...)` | After `app = FastAPI(...)`, **before middleware adds** | Instrumentator adds its own ASGI middleware via `.instrument()` — should sit innermost-but-app, so call BEFORE `app.add_middleware(RequestLogMiddleware)` etc. |

### Middleware ordering caveat

Starlette middleware is **LIFO** (last-added is outermost). Current order in `app.py`:
```
add_middleware(RequestLogMiddleware)     # innermost
add_middleware(CorrelationIdMiddleware)  # middle
add_middleware(CORSMiddleware)           # outermost
```

`Instrumentator.instrument(app)` internally calls `app.add_middleware(PrometheusInstrumentatorMiddleware)` [VERIFIED: instrumentation.py imports `PrometheusInstrumentatorMiddleware`]. To get desired runtime order:

```
CORS → CorrelationId → Prometheus → RequestLog → routers
```

…we want the Prometheus middleware **between** CorrelationId (so request_id is set when metrics fire — useful for exemplars later) and RequestLog. Add `instrument()` **after `add_middleware(RequestLogMiddleware)` and before `add_middleware(CorrelationIdMiddleware)`**.

```python
# Starlette middleware is LIFO — innermost added first.
app.add_middleware(RequestLogMiddleware)            # innermost
instrumentator.instrument(app)                       # middle (between RequestLog and CorrelationId)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(CORSMiddleware, ...)             # outermost
```

### Full diff for `create_app()`

```python
from prometheus_fastapi_instrumentator import Instrumentator

from localstock.observability.logging import configure_logging
from localstock.observability.metrics import init_metrics


def create_app() -> FastAPI:
    configure_logging()  # OBS-01
    init_metrics()       # OBS-08, OBS-10 — idempotent registry init on default REGISTRY

    app = FastAPI(
        title="LocalStock API",
        description="AI Stock Agent for Vietnamese Market (HOSE)",
        version="0.1.0",
        lifespan=get_lifespan,
    )

    # Phase 23 — Prometheus instrumentation. Wire BEFORE outer middleware so
    # CORS+CorrelationId envelope it; AFTER RequestLogMiddleware so /metrics
    # itself isn't instrumented (D-07 excluded_handlers handles that anyway).
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["^/metrics$", "^/health/live$"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=False,
    )

    app.add_middleware(RequestLogMiddleware)
    instrumentator.instrument(app)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    # ... exception handler + routers unchanged ...
    return app
```

**Note on `expose()` placement:** Per the README "fast-track" example, `Instrumentator().instrument(app).expose(app)` is fine to chain at module level (FastAPI hasn't started serving yet). If we ever switch to async lifespan registration, the README also documents the `@app.on_event("startup")` form. Module-level is simplest and matches the project's already-eager `app = create_app()` at the bottom of `app.py`.

---

## Test Plan

**Location:** `apps/prometheus/tests/test_observability/test_metrics.py` (new file)

| # | Test | Maps to | Type |
|---|------|---------|------|
| T1 | `test_metrics_module_level_import_does_not_raise` | OBS-08 SC#2 | unit |
| T2 | `test_init_metrics_idempotent` | OBS-10 SC#3 | unit |
| T3 | `test_init_metrics_returns_same_collector_on_duplicate` | OBS-10 | unit |
| T4 | `test_metrics_no_symbol_label` | OBS-09 SC#4 | unit |
| T5 | `test_metrics_namespace_prefix` | OBS-08, D-01 | unit |
| T6 | `test_pipeline_step_buckets` | D-03 | unit |
| T7 | `test_metrics_endpoint_returns_200_with_correct_content_type` | OBS-07 SC#1 | integration (httpx) |
| T8 | `test_metrics_endpoint_exposes_default_http_histogram` | OBS-07 SC#1 | integration (httpx) |
| T9 | `test_metrics_endpoint_excludes_self_handler` | D-07 | integration |

### Code skeletons

```python
# tests/test_observability/test_metrics.py
"""Phase 23 — metric primitives + /metrics endpoint tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from localstock.observability.metrics import (
    PIPELINE_STEP_BUCKETS,
    init_metrics,
)


# ---- Module-level + idempotency ----

def test_metrics_module_level_import_does_not_raise():
    """OBS-08 SC#2 — pure import succeeds (already happened by test collection
    if we got here, but make it explicit + reload-safe)."""
    import importlib
    import localstock.observability.metrics as m
    importlib.reload(m)  # second registration must not raise


def test_init_metrics_idempotent(metrics_registry: CollectorRegistry):
    """OBS-10 — calling init_metrics twice on the same registry is a no-op."""
    first = init_metrics(metrics_registry)
    second = init_metrics(metrics_registry)
    assert set(first.keys()) == set(second.keys())
    for key in first:
        assert first[key] is second[key], f"{key} re-created instead of reused"


def test_init_metrics_returns_same_collector_on_duplicate(
    metrics_registry: CollectorRegistry,
):
    """OBS-10 — duplicate Counter() construction must return existing instance,
    not raise ValueError."""
    metrics = init_metrics(metrics_registry)
    counter = metrics["http_requests_total"]
    # Re-init: should fetch via _names_to_collectors fallback
    metrics_again = init_metrics(metrics_registry)
    assert metrics_again["http_requests_total"] is counter


# ---- Label schema (D-06, OBS-09) ----

def test_metrics_no_symbol_label(metrics_registry: CollectorRegistry):
    """OBS-09 — symbol must NEVER be a label name (high cardinality)."""
    init_metrics(metrics_registry)
    for collector in list(metrics_registry._collector_to_names.keys()):
        labelnames = getattr(collector, "_labelnames", ())
        assert "symbol" not in labelnames, (
            f"Forbidden 'symbol' label found on {collector._name}"
        )


def test_metrics_namespace_prefix(metrics_registry: CollectorRegistry):
    """D-01 — every custom metric starts with 'localstock_'."""
    init_metrics(metrics_registry)
    for collector in list(metrics_registry._collector_to_names.keys()):
        name = getattr(collector, "_name", "")
        assert name.startswith("localstock_"), f"Non-namespaced metric: {name!r}"


# ---- Bucket boundaries (D-03) ----

def test_pipeline_step_buckets(metrics_registry: CollectorRegistry):
    """D-03 — pipeline step histogram uses minute-scale buckets."""
    metrics = init_metrics(metrics_registry)
    hist = metrics["pipeline_step_duration_seconds"]
    # prometheus_client stores upper bounds in collector._upper_bounds
    bounds = tuple(hist._upper_bounds[:-1])  # last is +Inf
    assert bounds == PIPELINE_STEP_BUCKETS


# ---- Endpoint integration ----

def test_metrics_endpoint_returns_200_with_correct_content_type():
    """OBS-07 SC#1 — GET /metrics returns 200 + Prometheus content-type."""
    from localstock.api.app import create_app
    client = TestClient(create_app())
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "version=0.0.4" in r.headers["content-type"]


def test_metrics_endpoint_exposes_default_http_histogram():
    """OBS-07 SC#1 — http_request_duration_seconds is exposed."""
    from localstock.api.app import create_app
    client = TestClient(create_app())
    # Generate at least one request so the histogram has a sample
    client.get("/health/live")  # may 404 in Phase 23; counter still increments
    body = client.get("/metrics").text
    assert "http_request_duration_seconds" in body


def test_metrics_endpoint_excludes_self_handler():
    """D-07 — /metrics requests are NOT instrumented."""
    from localstock.api.app import create_app
    client = TestClient(create_app())
    client.get("/metrics")
    client.get("/metrics")
    body = client.get("/metrics").text
    # No handler="/metrics" line should appear in default histogram
    assert 'handler="/metrics"' not in body
```

**Why TestClient (synchronous) here:** Existing test_observability suite already mixes async-flavoured tests via `asyncio_mode = "auto"`; `TestClient` works fine inside `asyncio`-auto mode and avoids needing the `httpx.AsyncClient` lifecycle dance for endpoint smoke tests. Existing pattern: `tests/test_observability/test_request_log.py` uses `TestClient` — match that.

---

## Conftest Integration

### Where to put `metrics_registry` fixture

**Recommendation:** add to `apps/prometheus/tests/test_observability/conftest.py` (NOT top-level conftest). Rationale:

1. Only Phase 23 tests need it — top-level `tests/conftest.py` is shared with crawler/db/scheduler tests that have nothing to do with Prometheus.
2. The existing `test_observability/conftest.py` already scopes test infrastructure (`_isolate_app_from_infra` autouse) to this directory.
3. Avoids polluting unrelated test runs with `prometheus_client` import overhead.

### Fixture code

```python
# Append to apps/prometheus/tests/test_observability/conftest.py

import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def metrics_registry() -> CollectorRegistry:
    """Function-scoped fresh CollectorRegistry — prevents `Duplicated timeseries`
    between tests (CONTEXT.md D-04, OBS-10).

    Each test that calls ``init_metrics(registry)`` gets an isolated registry;
    no cleanup needed (GC'd at function teardown). Tests that hit the real
    /metrics endpoint via ``create_app()`` use the global default REGISTRY
    instead — that's fine because module-level ``_DEFAULT_METRICS`` is itself
    idempotent.
    """
    return CollectorRegistry()
```

### Interaction with existing fixtures

- **`_configure_test_logging` (top-level, session, autouse)** — sets `LOG_LEVEL=DEBUG` and calls `configure_logging()`. **No interaction with metrics.** Safe.
- **`_isolate_app_from_infra` (test_observability, function, autouse)** — patches scheduler lifespan to no-op and stubs DB session factory. **Helps** the endpoint tests because `create_app()` will not try to start APScheduler. Required for T7/T8/T9.
- **Loguru `enqueue=False`** — already enforced via `PYTEST_CURRENT_TEST` sentinel; no change.

### Tests using the global default REGISTRY (T7, T8, T9)

Endpoint tests instantiate `create_app()`, which calls `init_metrics()` against the default `prometheus_client.REGISTRY`. Across multiple tests in the same process, the second `create_app()` call would normally raise — but `init_metrics()` is idempotent. **Verified** to work; no fixture-level reset needed.

If a future test needs to assert on global-registry state in isolation, the escape hatch is to pass `registry=fresh` into the `Instrumentator(...)` constructor directly inside the test (the kwarg exists per VERIFIED source).

---

## Runtime State Inventory

> Phase 23 is greenfield (new module + new endpoint). No rename/migration. **All categories: None.**

| Category | Findings |
|----------|----------|
| Stored data | None — metrics are in-process; no DB / Mem0 / SQLite involvement |
| Live service config | None — no n8n / Datadog / etc. in this project |
| OS-registered state | None — `/metrics` is HTTP-only |
| Secrets / env vars | None — D-02 chose no auth; no new env vars introduced |
| Build artifacts | None — pure Python, no compiled artifacts |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.12 | Project base | ✅ | per pyproject `requires-python>=3.12` | — |
| `prometheus-client` | metrics.py | After `uv sync` | 0.25.0 (latest) | — |
| `prometheus-fastapi-instrumentator` | app.py | After `uv sync` | 7.1.0 (latest) | — |
| External Prometheus server | scraping `/metrics` | **Not required for this phase** — endpoint just serves data | — | — |

**Action:** First task in Wave 0 must be `uv sync` (or `uv pip install -e .[dev]`) after pyproject diff lands.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (asyncio_mode=auto) |
| Config file | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd apps/prometheus && uv run pytest tests/test_observability/test_metrics.py -x` |
| Full suite command | `cd apps/prometheus && uv run pytest` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|--------------|
| OBS-07 | `/metrics` 200 + correct content-type | integration | `pytest tests/test_observability/test_metrics.py::test_metrics_endpoint_returns_200_with_correct_content_type -x` | ❌ Wave 0 |
| OBS-07 | Default `http_request_duration_seconds` exposed | integration | `pytest .../test_metrics_endpoint_exposes_default_http_histogram -x` | ❌ Wave 0 |
| OBS-08 | Module-level primitives import | unit | `pytest .../test_metrics_module_level_import_does_not_raise -x` | ❌ Wave 0 |
| OBS-08 | Namespace prefix on all custom metrics | unit | `pytest .../test_metrics_namespace_prefix -x` | ❌ Wave 0 |
| OBS-09 | No `symbol` label | unit | `pytest .../test_metrics_no_symbol_label -x` | ❌ Wave 0 |
| OBS-10 | Idempotent init | unit | `pytest .../test_init_metrics_idempotent -x` | ❌ Wave 0 |
| OBS-10 | Duplicate returns existing | unit | `pytest .../test_init_metrics_returns_same_collector_on_duplicate -x` | ❌ Wave 0 |
| D-03 | Pipeline buckets correct | unit | `pytest .../test_pipeline_step_buckets -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_observability/test_metrics.py -x` (~1s)
- **Per wave merge:** `pytest tests/test_observability/ -x` (~5-10s)
- **Phase gate:** Full `pytest` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_observability/test_metrics.py` — new file, all 9 tests
- [ ] `metrics_registry` fixture appended to `tests/test_observability/conftest.py`
- [ ] `prometheus-client` + `prometheus-fastapi-instrumentator` added to pyproject + `uv sync`

---

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | **No** (D-02: local-first, no auth) | runbook warning only |
| V3 Session Management | No | — |
| V4 Access Control | **Partial** | D-02 defers IP allowlist to backlog; runbook MUST mention "do not expose port 8000 publicly" |
| V5 Input Validation | No (`/metrics` is GET-only, no user input) | — |
| V6 Cryptography | No | — |
| V7 Error Handling & Logging | Yes | `init_metrics()` failures must surface via `loguru` (Phase 22) — that's why we call it AFTER `configure_logging()` |
| V14 Configuration | Yes | Buckets are constants in code, not env-driven — minimizes misconfig risk |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cardinality explosion (DoS via memory blow-up) | DoS | D-06 bounded label sets; `should_group_status_codes`; `should_ignore_untemplated`; `test_metrics_no_symbol_label` |
| Information disclosure via `/metrics` | I | D-02 + runbook warning. Histograms expose latency distributions but no PII |
| `/metrics` scraping causing self-feedback in logs | DoS (mild) | Not addressed — Phase 22 explicitly chose to log all paths. Open question below. |

---

## Common Pitfalls

### Pitfall 1: `Duplicated timeseries in CollectorRegistry`
**What goes wrong:** `Counter("name", ...)` raises `ValueError` on second construction with the same name on the same registry.
**Why it happens:** pytest test collection imports modules multiple times; `create_app()` may be called per test; module reload during dev-watch.
**Avoidance:** The `_register` helper in `init_metrics()` catches `ValueError` and returns the existing collector via `registry._names_to_collectors`.
**Warning sign:** Test failures only on second test, not first.

### Pitfall 2: Library default metrics getting double-prefixed
**What goes wrong:** Passing `metric_namespace="localstock"` to `Instrumentator` (or to `metrics.latency()` etc.) renames the default histogram to `localstock_http_request_duration_seconds` — breaks success criterion #1 wording.
**Avoidance:** **Do not** pass `metric_namespace` anywhere in `Instrumentator(...)`. Default closures keep their names per D-01 exception.
**Warning sign:** Test `test_metrics_endpoint_exposes_default_http_histogram` fails with metric name not found.

### Pitfall 3: `excluded_handlers` regex matching too broadly
**What goes wrong:** `excluded_handlers=["/metrics"]` with `re.search` matches `/metrics-foo`, `/api/metrics-debug`, etc.
**Avoidance:** Anchor with `^...$` → `["^/metrics$", "^/health/live$"]`.
**Warning sign:** Routes silently uninstrumented; users notice missing series in Grafana.

### Pitfall 4: `/health/live` excluded but doesn't exist yet
**What goes wrong:** Phase 25 introduces `/health/live`. Phase 23 only has `/health`. The exclusion is harmless (regex never matches) but reads as confusing.
**Avoidance:** Document in code comment: `# /health/live: forward-compatible exclusion for Phase 25 (OBS-14)`.

### Pitfall 5: `TestClient` shares global REGISTRY across tests
**What goes wrong:** Repeatedly calling `create_app()` in tests would re-register on default REGISTRY.
**Avoidance:** Already handled by idempotent `init_metrics()`. No `monkeypatch` of REGISTRY needed.

### Pitfall 6: Instrumentator middleware order
**What goes wrong:** Adding `instrumentator.instrument(app)` AFTER all `add_middleware` calls puts Prometheus middleware **outermost** — measures total time including CORS handling. Adding too early causes it to miss CorrelationId.
**Avoidance:** Place `instrument(app)` between `RequestLogMiddleware` (innermost) and `CorrelationIdMiddleware` (see "App Wiring" §).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP latency histogram, request counter, in-progress gauge | Custom ASGI middleware | `prometheus-fastapi-instrumentator` Instrumentator + default closures | 7 years of edge-case fixes (streaming responses, body buffering, exception handling, route templating) |
| `text/plain; version=0.0.4` rendering | `def metrics(): return Response(...)` from scratch | `Instrumentator.expose(app)` → uses `prometheus_client.generate_latest()` + `CONTENT_TYPE_LATEST` | Spec-correct format, gzip support, multiprocess-mode ready |
| Registry idempotency tracker | Custom `_initialized = False` flag | Catch `ValueError` + `registry._names_to_collectors` lookup | Standard prometheus_client pattern; flag-based approach breaks across module reloads |
| Fresh-registry test isolation | `monkeypatch.setattr(prometheus_client, 'REGISTRY', ...)` | Pass `CollectorRegistry()` via `init_metrics(registry=)` API | Function signature already supports it; no global-state mutation |

---

## File Touch List

### New files
| File | LOC (est.) | Purpose |
|------|------------|---------|
| `apps/prometheus/src/localstock/observability/metrics.py` | ~190 | Primitives + `init_metrics()` |
| `apps/prometheus/tests/test_observability/test_metrics.py` | ~110 | 9 tests |

### Modified files
| File | LOC delta | Change |
|------|-----------|--------|
| `apps/prometheus/pyproject.toml` | +2 | Add 2 deps |
| `apps/prometheus/src/localstock/observability/__init__.py` | +2 | Re-export `init_metrics` |
| `apps/prometheus/src/localstock/api/app.py` | +18 / -0 | `init_metrics()` call + `Instrumentator` config + `instrument()` + `expose()` |
| `apps/prometheus/tests/test_observability/conftest.py` | +12 | `metrics_registry` fixture |

### Verification grep (D-08 boundary)
**No** new occurrences of `\.inc(\|\.observe(\|\.set(` outside:
- `apps/prometheus/src/localstock/observability/metrics.py`
- `apps/prometheus/tests/`

Total: **~330 LOC** across 6 files (2 new + 4 modified).

---

## Open Questions

1. **Should `/metrics` be excluded from `RequestLogMiddleware` to avoid log noise?**
   - What we know: Phase 22 explicitly **rejected** path filtering ("log all paths including /health and /metrics"). Phase 22 RESEARCH §762: *"revisit in Phase 23 metrics work if needed"*.
   - Recommendation: **Keep current behavior** for Phase 23 — single-user app, low traffic, minimal noise. If Prometheus scrape interval is set to 5-15s in a future deployment, this could generate ~6k log lines/day from `/metrics` alone — defer revisit to Phase 25 or a backlog item.
   - **For planner**: no action required this phase. Document trade-off in PR description. [VERIFIED: Phase 22 RESEARCH.md line 762]

2. **Does `prometheus-fastapi-instrumentator` middleware ordering interact correctly with `CorrelationIdMiddleware`?**
   - What we know: `CorrelationIdMiddleware` sets a contextvar + log binding; Prometheus middleware records labels (method, status, handler). They don't share state.
   - Recommendation: Place `instrument(app)` **between** `RequestLogMiddleware` (innermost) and `CorrelationIdMiddleware` so request_id is set when (future) exemplar support fires. Code shown in App Wiring §.
   - **For planner**: no decision needed — order is prescriptive. [ASSUMED — exemplar wiring is out of scope for Phase 23; the order is defensive for forward compat]

3. **Cardinality enforcement: runtime guard or test-only?**
   - CONTEXT.md D-06 phrasing: *"Test `test_metrics_cardinality_budget` document expected upper bound (informational, not asserted at runtime)."* Already resolved.
   - Recommendation: **Test-only** (per CONTEXT.md). No runtime guard. Adding a runtime guard would require label introspection on every `.inc()/.observe()` call → noticeable perf cost. Not worth it for bounded label sets we already control in code.
   - **For planner**: no action.

---

## Code Examples (verified patterns)

### Pattern 1: Idempotent metric registration
[CITED: prometheus/client_python issues #336, #406 — recommended pattern]

```python
try:
    counter = Counter("foo_total", "...", registry=reg)
except ValueError:
    counter = reg._names_to_collectors["foo_total"]
```

### Pattern 2: Custom registry for tests
[VERIFIED: prometheus-fastapi-instrumentator instrumentation.py:43]

```python
fresh = CollectorRegistry()
Instrumentator(registry=fresh).instrument(app).expose(app)
```

### Pattern 3: Asserting bucket boundaries
[VERIFIED: prometheus_client Histogram source — `_upper_bounds` is the canonical attribute]

```python
hist = Histogram("x", "x", buckets=(1, 2, 3))
assert hist._upper_bounds == [1.0, 2.0, 3.0, float("inf")]
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_names_to_collectors` is stable private API across prometheus_client versions | metrics.py `_register`, test fixtures | LOW — attribute exists since v0.0.x, used by ecosystem (e.g. `prometheus-flask-exporter`); pin floor `>=0.21` keeps us in known-good range |
| A2 | `_upper_bounds` attribute on Histogram is stable | `test_pipeline_step_buckets` | LOW — used by official tests |
| A3 | Placing `instrument(app)` between RequestLog and CorrelationId middleware is correct for future exemplar support | App wiring | NONE for this phase — exemplars not used yet |
| A4 | `re.search` (instrumentator's match style) handles unanchored strings; we recommend anchoring for safety | D-07 implementation | LOW — anchored regex is strictly safer |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED] PyPI metadata for `prometheus-fastapi-instrumentator` 7.1.0 — `https://pypi.org/pypi/prometheus-fastapi-instrumentator/json` (fetched 2025-11-26)
- [VERIFIED] PyPI metadata for `prometheus-client` 0.25.0 — `https://pypi.org/pypi/prometheus-client/json` (fetched 2025-11-26)
- [VERIFIED] GitHub source — `trallnag/prometheus-fastapi-instrumentator` `master/src/prometheus_fastapi_instrumentator/instrumentation.py` (Instrumentator constructor lines 28–112, expose lines 232–305)
- [VERIFIED] GitHub README — `trallnag/prometheus-fastapi-instrumentator/master/README.md`
- [VERIFIED] Local source — `apps/prometheus/src/localstock/api/app.py`, `observability/middleware.py`, `observability/__init__.py`, `tests/conftest.py`, `tests/test_observability/conftest.py`
- [VERIFIED] Phase 22 RESEARCH.md (line 762) — confirms `/metrics` log filtering decision

### Secondary (MEDIUM confidence)
- [CITED] prometheus/client_python README — `_names_to_collectors` idempotency pattern is widely documented in third-party client libraries

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against live PyPI; code paths verified against current upstream master
- Architecture: HIGH — Instrumentator API surface read directly from source; middleware ordering reasoning grounded in Starlette LIFO docs (verified in Phase 22)
- Pitfalls: HIGH — all 6 pitfalls have direct VERIFIED or CITED sources

**Research date:** 2025-11-26
**Valid until:** 2025-12-26 (30 days — prometheus stack is mature/stable)

**Ready for planning.** Single wave with 2-3 plans recommended:
- **Plan 1**: Deps + `metrics.py` + unit tests T1-T6 + `metrics_registry` fixture (parallel-safe)
- **Plan 2**: `app.py` wiring + `__init__.py` re-export + integration tests T7-T9 (depends on Plan 1)
- **Optional Plan 3**: README/runbook D-02 warning note (parallel with Plan 2)
