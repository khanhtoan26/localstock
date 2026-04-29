---
phase: 23-metrics-primitives-metrics-endpoint
plan: 02
subsystem: observability
tags: [observability, metrics, fastapi, prometheus, OBS-07]
status: complete
requires:
  - 23-01 (init_metrics + observability/metrics module)
  - prometheus-fastapi-instrumentator>=7.1.0
  - prometheus-client>=0.25.0
provides:
  - "GET /metrics endpoint (text/plain Prometheus exposition format)"
  - "Default HTTP histogram http_request_duration_seconds + Counter http_requests_total"
  - "create_app() that is idempotent across calls (test-safe)"
affects:
  - apps/prometheus/src/localstock/api/app.py (M)
  - apps/prometheus/tests/test_observability/test_metrics_endpoint.py (NEW)
tech-stack:
  added: []
  patterns:
    - "Idempotent collector cleanup before Instrumentator construction (defensive registry hygiene)"
    - "Anchored regex exclusion (^/metrics$, ^/health/live$) for self-instrumentation pitfall"
    - "Middleware LIFO ordering: CORS → CorrelationId → Prometheus → RequestLog → routers"
key-files:
  created:
    - apps/prometheus/tests/test_observability/test_metrics_endpoint.py
  modified:
    - apps/prometheus/src/localstock/api/app.py
decisions:
  - "Relax content-type assertion from version=0.0.4 to version=* — prometheus-client 0.25.0 emits version=1.0.0 (OpenMetrics-aligned)"
  - "Add 6-collector unregister loop before Instrumentator() to make create_app() idempotent across calls"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-29"
  tasks_completed: 2
  tests_added: 2
  tests_total_passing: 471
commit_hashes:
  - c1f797a (atomic feat commit)
requirements_closed: [OBS-07]
---

# Phase 23 Plan 02: /metrics Endpoint Wiring + Integration Tests Summary

**One-liner:** Wired prometheus-fastapi-instrumentator into FastAPI's middleware stack with bounded config (D-07), exposed `/metrics` (excluded from OpenAPI), added Nyquist-contract integration tests, and made `create_app()` idempotent across calls via a defensive 6-collector unregister loop.

## What Was Built

1. **`apps/prometheus/src/localstock/api/app.py` (M, +93/-1 LOC):**
   - Added imports for `Instrumentator`, `init_metrics`, and `prometheus_client.REGISTRY`.
   - `init_metrics()` is called immediately after `configure_logging()` so any registry-init failure surfaces as a structured log line (OBS-01 + OBS-08 ordering).
   - `Instrumentator(...)` constructed with the exact kwargs from CONTEXT D-07: `should_group_status_codes=True`, `should_ignore_untemplated=True`, `should_group_untemplated=True`, `should_instrument_requests_inprogress=True`, `excluded_handlers=["^/metrics$", "^/health/live$"]`, `inprogress_name="http_requests_inprogress"`, `inprogress_labels=False`. **No `metric_namespace`** (per Pitfall 2).
   - Middleware add order rewritten so runtime stack (LIFO) is: CORS (outer) → CorrelationId → Prometheus → RequestLog (inner) → routers. `instrumentator.instrument(app)` sits between `RequestLogMiddleware` and `CorrelationIdMiddleware` so request_id is set when metrics fire (forward-compat for exemplars).
   - `instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)` — `/metrics` is hidden from OpenAPI.
   - **Idempotency guard:** before constructing the new `Instrumentator`, the 6 default collectors that `prometheus-fastapi-instrumentator` registers (`http_requests_total`, `http_requests_inprogress`, `http_request_duration_seconds`, `http_request_duration_highr_seconds`, `http_request_size_bytes`, `http_response_size_bytes`) are unregistered if present. This makes `create_app()` safe to call multiple times in the same process (e.g. integration tests). It is a no-op on the first call (production path).

2. **`apps/prometheus/tests/test_observability/test_metrics_endpoint.py` (NEW, 50 LOC, 2 tests):**
   - `test_metrics_endpoint_returns_200_with_correct_content_type` — `GET /metrics` returns 200 with content-type starting with `text/plain` and containing `version=` and `charset=utf-8`.
   - `test_metrics_endpoint_exposes_default_http_histogram` — after issuing a request to `/health/`, the body of `/metrics` contains the substring `http_request_duration_seconds`.
   - Both tests use `TestClient(create_app())`, sharing the global `prometheus_client.REGISTRY`. Safe because of the new idempotency guard + 23-01's idempotent `init_metrics`.
   - Relies on the autouse `_isolate_app_from_infra` fixture in `tests/test_observability/conftest.py` (unchanged per plan).

## Verification

```text
$ uv run pytest -x -q
471 passed, 1 warning in 2.95s     # was 469 (Phase 23-01) → +2 from this plan

$ bash apps/prometheus/scripts/lint-no-fstring-logs.sh
OK: zero f-string log calls.

$ grep -RnE '\.(inc|observe|set)\(' src/localstock/{services,crawlers,scheduler,api}/
src/localstock/services/pipeline.py:69:        token = run_id_var.set(run_id)   # ContextVar.set, NOT prom .set()
# api/, crawlers/, scheduler/ — clean.

$ uv run python -c "
from fastapi.testclient import TestClient
from localstock.api.app import create_app
c = TestClient(create_app())
c.get('/health/')
r = c.get('/metrics')
assert r.status_code == 200
assert 'http_request_duration_seconds' in r.text
assert r.headers['content-type'].startswith('text/plain')
print('OK')
"
OK
```

OpenAPI schema does NOT contain `/metrics` (verified via `app.openapi()['paths']`).

## Acceptance Criteria — Status

| Criterion (from PLAN) | Status |
|---|---|
| `from prometheus_fastapi_instrumentator import Instrumentator` | ✅ |
| `from localstock.observability.metrics import init_metrics` | ✅ |
| `init_metrics()` called once in create_app() | ✅ |
| `instrumentator.instrument(app)` called once | ✅ |
| `endpoint="/metrics"` + `include_in_schema=False` | ✅ |
| Anchored regex `^/metrics$` in excluded_handlers | ✅ |
| No `metric_namespace=` (Pitfall 2 guard) | ✅ |
| Phase 22 middleware tests still pass | ✅ |
| D-08 cross-cut: no `.inc/.observe/.set` in services/crawlers/scheduler/api (excluding `ContextVar.set`) | ✅ |
| Both integration tests pass | ✅ |
| Full prometheus app suite passes (`pytest -x`) | ✅ (471 passed) |

## Deviations from Plan

### 1. [Rule 1 — Bug] Relaxed Content-Type version assertion (library reality)

**Found during:** Task 2 verification — first test run.

**Issue:** Plan + must_haves required `Content-Type` to contain `version=0.0.4`. Reality: `prometheus-client==0.25.0` emits `text/plain; version=1.0.0; charset=utf-8` (the OpenMetrics-aligned bump introduced in prometheus-client 0.20+).

**Fix:** Test asserts `text/plain` prefix, contains `version=` (any value), and contains `charset=utf-8`. The semantic contract — "Prometheus text exposition format that Prometheus servers can scrape" — is preserved; only the version label is unpinned. Documented as a comment in the test docstring.

**Files modified:** `apps/prometheus/tests/test_observability/test_metrics_endpoint.py:18-32` (assertion + docstring).

**Commit:** c1f797a (atomic).

### 2. [Rule 1 / Rule 3 — Bug + Blocker] Added 6-collector idempotency guard

**Found during:** Task 2 verification — second test failed with `Duplicated timeseries in CollectorRegistry: {'http_requests_inprogress'}` and then `http_request_duration_seconds` was missing from the body even after the cleanup was widened.

**Issue:** Plan must_have explicitly required: *"Calling create_app() multiple times in the same test session does NOT raise Duplicated timeseries (relies on 23-01's idempotent init_metrics)."* But 23-01's `init_metrics` only covers project-owned metrics — it does NOT cover the metrics that `prometheus-fastapi-instrumentator` itself registers (`http_requests_inprogress` in `Instrumentator.__init__`, plus the 5 default metrics from `metrics.default()` registered when the middleware is constructed).

The library's `metrics.default()` wraps all 5 default metric registrations in a single try/except: if ANY of them raises `Duplicated timeseries`, the whole function returns `None` — meaning the middleware ends up with `self.instrumentations = []` and observes nothing. So calling `create_app()` twice produced a `/metrics` endpoint with no `http_request_duration_seconds` at all.

**Fix:** Before constructing `Instrumentator`, unregister all 6 collectors that the library registers if they're already present in the default REGISTRY:

```python
for _name in (
    "http_requests_inprogress",
    "http_requests_total",
    "http_request_duration_seconds",
    "http_request_duration_highr_seconds",
    "http_request_size_bytes",
    "http_response_size_bytes",
):
    _existing = _PROM_REGISTRY._names_to_collectors.get(_name)
    if _existing is not None:
        _PROM_REGISTRY.unregister(_existing)
```

This is a no-op on the first call (production path: `create_app()` runs once at import), and makes subsequent calls idempotent (test path). Justification: the must_have explicitly requires this idempotency, and the alternative (modifying conftest) was forbidden by the plan.

**Files modified:** `apps/prometheus/src/localstock/api/app.py:48-66` (cleanup loop + comment block).

**Commit:** c1f797a (atomic).

## Threat Flags

None. This plan adds an HTTP endpoint (`/metrics`) but the threat model already accounts for it (CONTEXT D-02 — no auth on /metrics is an accepted risk for v1.5; runbook in 23-03 documents reverse-proxy hardening for production deployment).

## Known Stubs

None.

## Self-Check: PASSED

- ✅ FOUND: `apps/prometheus/src/localstock/api/app.py` (modified)
- ✅ FOUND: `apps/prometheus/tests/test_observability/test_metrics_endpoint.py` (new)
- ✅ FOUND: commit `c1f797a` in git log
- ✅ Full suite: 471 passing (was 469; +2 from this plan)
- ✅ Lint guard: passing (zero f-string log calls)
- ✅ D-08 boundary: clean (only false positive is `ContextVar.set` in pipeline.py, pre-existing)
