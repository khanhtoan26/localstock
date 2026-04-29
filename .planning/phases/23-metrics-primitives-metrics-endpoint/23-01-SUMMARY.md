---
phase: 23-metrics-primitives-metrics-endpoint
plan: 01
subsystem: observability
status: complete
completed: 2026-04-29
tags: [metrics, prometheus, observability, primitives, tdd]
requirements_closed: [OBS-08, OBS-09, OBS-10]
dependency_graph:
  requires:
    - "Phase 22 observability/__init__.py re-export pattern"
    - "prometheus_client (CollectorRegistry, Counter, Histogram, Gauge)"
  provides:
    - "localstock.observability.metrics.init_metrics() — idempotent registrar"
    - "13 metric primitives across 6 families (HTTP, op_*, cache, db_query, pipeline_step, dq)"
    - "PIPELINE_STEP_BUCKETS / HTTP_LATENCY_BUCKETS / DB_QUERY_BUCKETS / OP_DURATION_BUCKETS constants"
    - "metrics_registry function-scoped pytest fixture"
  affects:
    - "Plan 23-02 will consume init_metrics + Instrumentator deps in FastAPI lifespan"
    - "Phase 24 (.inc/.observe/.set call sites) will import from localstock.observability"
tech_stack:
  added:
    - "prometheus-client>=0.21,<1.0 (resolved 0.25.0)"
    - "prometheus-fastapi-instrumentator>=7.1,<8.0 (resolved 7.1.0)"
  patterns:
    - "Idempotent registry via try/except ValueError + _names_to_collectors fallback (D-04)"
    - "Module-level eager init: _DEFAULT_METRICS = init_metrics() satisfies OBS-08 wording"
    - "Lambda factory wrappers to defer constructor errors (Counter raises at construction)"
key_files:
  created:
    - "apps/prometheus/src/localstock/observability/metrics.py"
    - "apps/prometheus/tests/test_observability/test_metrics.py"
  modified:
    - "apps/prometheus/pyproject.toml (+2 deps)"
    - "apps/prometheus/src/localstock/observability/__init__.py (+init_metrics re-export)"
    - "apps/prometheus/tests/test_observability/conftest.py (+metrics_registry fixture)"
    - "uv.lock (resolver update)"
decisions:
  - "Used anchored regex form for instrumentator excluded_handlers (deferred to 23-02)"
  - "All 13 collectors registered with frozen labelnames per CONTEXT.md D-06 budget"
  - "vnstock 4.0.2 install glitch (missing vnai package files) fixed via uv sync --reinstall-package vnai — transient, unrelated to plan"
metrics:
  duration: "~7 min"
  tasks_completed: 3
  files_touched: 6
  tests_added: 7
  tests_total_after: 469
commit: a1add23
---

# Phase 23 Plan 01: Metrics Primitives & Idempotent Registry Init Summary

13 Prometheus metric primitives registered under `localstock_` namespace via idempotent `init_metrics()` helper, plus 7 unit tests, in 1 atomic commit.

## What Was Done

**Task 1 — Dependencies**
- Added `prometheus-client>=0.21,<1.0` (resolved 0.25.0) and `prometheus-fastapi-instrumentator>=7.1,<8.0` (resolved 7.1.0) to `apps/prometheus/pyproject.toml`, inserted between `tenacity` and `pandas-ta` per plan.
- `uv sync` resolved cleanly. Side-effect: vnstock auto-bumped 4.0.1 → 4.0.2 (within pin range), and one transient install glitch left `vnai-2.4.8` dist-info present without package files; resolved with `uv sync --reinstall-package vnai`. Documented as expected resolver behavior; not a deviation since the pin was already permissive.

**Task 2 — RED (fixture + failing tests)**
- Appended function-scoped `metrics_registry` fixture to `tests/test_observability/conftest.py` (aliased imports to avoid name collision with Phase 22 fixtures).
- Created `tests/test_observability/test_metrics.py` with all 7 tests verbatim per `23-VALIDATION.md`:
  1. `test_metrics_module_level_import_does_not_raise`
  2. `test_init_metrics_returns_all_primitive_families`
  3. `test_metrics_namespace_prefix`
  4. `test_pipeline_step_histogram_buckets`
  5. `test_no_metric_has_symbol_label`
  6. `test_label_schema_matches_budget`
  7. `test_init_metrics_idempotent_on_same_registry`
- Confirmed RED: collection failed with `ModuleNotFoundError: localstock.observability.metrics`.

**Task 3 — GREEN (implementation)**
- Created `observability/metrics.py` (~210 LOC) using the verified code-ready block from `23-RESEARCH.md`. Sections: bucket constants → `init_metrics()` with `_register()` idempotency helper → 6 metric-family blocks (HTTP, op_*, cache, db_query, pipeline_step, dq) → trailing `_DEFAULT_METRICS = init_metrics()` eager init.
- Updated `observability/__init__.py` to re-export `init_metrics`.
- All 7 tests now PASS (`pytest tests/test_observability/test_metrics.py` → 7 passed).

## Verification

| Check | Result |
| --- | --- |
| 7 unit tests pass | ✅ 7 passed in 0.95s |
| Full prometheus app suite | ✅ 469 passed (462 baseline + 7 new) |
| `init_metrics()` returns 13 collectors | ✅ confirmed |
| No `symbol` label anywhere | ✅ `grep '"symbol"' metrics.py` = 0 |
| No `.inc()/.observe()/.set()` in `metrics.py` | ✅ confirmed |
| f-string log lint (Phase 22 OBS-06) | ✅ `OK: zero f-string log calls` |
| D-08 boundary grep on services/crawlers/scheduler/api | ⚠️ 1 hit `run_id_var.set(run_id)` in `services/pipeline.py:69` — this is a `contextvars.ContextVar.set()` from Phase 22, NOT a Prometheus metric `.set()`. False positive on lexical grep. No Phase 24 leakage introduced by this plan. |
| mypy on metrics.py | ⏭️ skipped — `mypy` not installed in venv (it's in `[project.optional-dependencies].dev`, not `[dependency-groups].dev`). Not a blocker; module passes import + runtime tests. |

## Deviations from Plan

**None functional.** Two minor execution notes:

1. **vnstock reinstall (Rule 3 — blocking issue, transient).** After `uv sync` added the new deps, vnstock auto-resolved 4.0.1 → 4.0.2 within the existing pin. The post-install state had a `vnai-2.4.8.dist-info/` directory but no `vnai/` package, breaking `import vnstock`. Recovered with `uv sync --reinstall-package vnai`. Pre-existing pin behavior, not caused by plan changes. Tracked here for transparency.
2. **mypy verification skipped.** Plan optional check; tool not installed in the active uv environment. Type correctness instead validated by passing tests + clean import.

## Acceptance Criteria — Final Status

- ✅ OBS-08 (Module-level primitives) — closed
- ✅ OBS-09 (Cardinality budget, no `symbol` label) — closed
- ✅ OBS-10 (Idempotent registry init) — closed
- ⏳ OBS-07 (endpoint wiring) — deferred to 23-02 per plan

## Self-Check: PASSED

- ✅ FOUND: `apps/prometheus/src/localstock/observability/metrics.py`
- ✅ FOUND: `apps/prometheus/tests/test_observability/test_metrics.py`
- ✅ FOUND: commit `a1add23`
- ✅ All 7 tests passing
- ✅ Full suite 469 passed
