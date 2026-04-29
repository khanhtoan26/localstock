---
phase: 24-instrumentation-health
plan: 01
subsystem: observability
tags: [decorator, OBS-11, TDD, sync, async, prometheus, loguru]
status: complete
requirements_closed: [OBS-11]
dependency_graph:
  requires: [Phase 23 metrics primitives (op_duration_seconds), Phase 22 loguru structured-kwargs idiom]
  provides: ["@observe(name, *, log=True)", "@timed_query(name)"]
  affects: [24-03 (timed_query alias re-uses @observe), 24-05 (call sites on daily_job + crawlers), 24-06 (pipeline _step_timer reuses op_duration_seconds semantics)]
tech_stack:
  added: []
  patterns:
    - "inspect.iscoroutinefunction → sync vs async wrapper at decoration time"
    - "functools.wraps to preserve coroutine identity"
    - "Bare re-raise (raise) on exception to preserve __traceback__"
    - "Lazy histogram lookup via REGISTRY._names_to_collectors with init_metrics() fallback"
key_files:
  created:
    - apps/prometheus/src/localstock/observability/decorators.py
    - apps/prometheus/tests/test_observability/test_decorators.py
  modified:
    - apps/prometheus/src/localstock/observability/__init__.py
    - apps/prometheus/src/localstock/observability/metrics.py
decisions:
  - "Place decorator in observability/decorators.py — keeps metrics.py primitive-only (Phase 23 D-05) and keeps the new module OUTSIDE the Phase 23 D-08 audit roots {services,crawlers,scheduler,api}/."
  - "Validate name at decoration time — malformed @observe('foo') fails fast at import, never silently at call time."
  - "Bare re-raise on exception path (never `raise exc`) preserves traceback chain — matches CONTEXT D-01 invariant."
  - "Resolve init_metrics(registry=None) to actual default REGISTRY (Rule-3 fix) — prometheus_client treats None as 'do not register', which left _DEFAULT_METRICS detached from default REGISTRY in Phase 23. Discovered while wiring decorator's lazy lookup."
metrics:
  duration_minutes: ~25
  tasks: 2
  tests_added: 7
  test_cases_executed: 13   # parametrize expands rejects_malformed_name to 7 cases
  files_created: 2
  files_modified: 2
  completed: 2026-04-29
---

# Phase 24 Plan 01: @observe Decorator Definition Summary

**One-liner:** Sync+async dual `@observe(name, *, log=True)` decorator + `@timed_query(name)` alias emitting `localstock_op_duration_seconds{domain,subsystem,action,outcome}` histogram and `op_complete`/`op_failed` structured loguru events; closes OBS-11 definition.

## What was built

- **`observability/decorators.py`** (170 LOC):
  - `_split_name()` validates `domain.subsystem.action` (3 non-empty tokens) at decoration time, raises `ValueError`.
  - `_get_op_histogram()` lazy lookup against default REGISTRY, falls back to `init_metrics()`.
  - `observe(name, *, log=True)` factory returns either a sync or async wrapper based on `inspect.iscoroutinefunction(fn)`.
  - On exception: records histogram with `outcome=fail`, emits `op_failed` log (kwargs only — Phase 22 OBS-06), bare `raise` re-raises original exception preserving traceback.
  - On success: records histogram with `outcome=success`, emits `op_complete` log when `log=True`.
  - `timed_query(name)` returns `observe(f"db.query.{name}")` for repository-level helpers (consumed by 24-03).
- **`observability/__init__.py`** re-exports `observe` and `timed_query`; `__all__` extended.
- **`tests/test_observability/test_decorators.py`** (163 LOC, 7 test functions, 13 cases via parametrize): sync+async × success+fail, naming validation (7 malformed names), `timed_query` alias, `log=False` suppression.

## Commits

| Stage  | Hash      | Message                                                                |
| ------ | --------- | ---------------------------------------------------------------------- |
| RED    | `d0d4b66` | test(observability): RED tests for @observe decorator (Phase 24-01)    |
| GREEN  | `1605197` | feat(observability): @observe decorator with sync+async dual mode (Phase 24-01) |

(Note: an unrelated `316edf3 feat(24-02): …` commit landed between RED and GREEN — produced by a separate process/hook with pre-staged 24-02 work; not part of plan 24-01 deliverables.)

## Verification

```
$ cd apps/prometheus && uv run pytest -x -q
486 passed, 1 warning in 23.60s          # 471 prior + 15 new
$ uv run pytest tests/test_observability/test_decorators.py -q
13 passed in 0.91s
$ bash apps/prometheus/scripts/lint-no-fstring-logs.sh
OK: zero f-string log calls.
$ uv run python -c "from localstock.observability import observe, timed_query; print('OK')"
OK
```

D-08 grep across `{services,crawlers,scheduler,api}/`: only pre-existing `run_id_var.set(run_id)` in `services/pipeline.py:69` (ContextVar — not a metric op; baseline is unchanged from Phase 23). Decorator definition lives in `observability/decorators.py`, outside the audit roots, so D-08 stays clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] init_metrics(registry=None) produced orphan collectors detached from default REGISTRY**

- **Found during:** Task 2 GREEN (decorator lookup returned None and fallback init returned a fresh detached histogram, so test counts never incremented).
- **Issue:** `metrics.py:init_metrics(registry=None)` set `target = registry  # = None`, then passed `registry=None` to `Counter(...)`/`Histogram(...)`. `prometheus_client` constructors treat `registry=None` as "do not auto-register" (their default kwarg is `REGISTRY`, not `None`). Result: production callers (`_DEFAULT_METRICS = init_metrics()` at module import, plus the FastAPI lifespan call) created collectors that were never registered on the default `REGISTRY` — invisible to `/metrics` scrape and to `REGISTRY._names_to_collectors` lookups.
- **Fix:** When `registry is None`, resolve `target` to `_get_default_registry()` so constructors register normally. Idempotent path is unchanged because the existing `_register` helper still catches `Duplicated timeseries` ValueError.
- **Files modified:** `apps/prometheus/src/localstock/observability/metrics.py`
- **Commit:** `1605197` (folded into GREEN — single atomic feat commit)
- **Scope justification:** This is a pre-existing Phase 23 latent bug. Without the fix, `@observe` cannot find the `op_duration_seconds` histogram on the default REGISTRY in production, defeating OBS-11's purpose. Fix is one line, surgical, and tests for Phase 23 metrics already use the `metrics_registry` fixture so they exercised the registered path and never caught this. No Phase 23 test broke after the fix (full 486-test suite green).

### Architectural deviations

None.

## Threat Flags

None — decorator emits an existing Phase 23 histogram with the existing label set; no new network surface, no new auth path, no schema changes.

## Known Stubs

None.

## TDD Gate Compliance

- RED commit `d0d4b66` (test only, fails with ModuleNotFoundError) ✓
- GREEN commit `1605197` (impl + tests pass) ✓
- REFACTOR: not needed — decorator code matches RESEARCH §1 verbatim with adjustments only for the `_get_op_histogram` fallback edge.

## Downstream Notes

- **24-05 Task 4** will apply `@observe` to `daily_job` and 4 crawler `.fetch()` methods (CONTEXT D-01 initial scope). This plan deliberately does NOT apply the decorator anywhere — call sites are 24-05's deliverable.
- **24-03** will define `db_events.py` SQLAlchemy listener and may co-document `@timed_query` usage on bulk-upsert services; the alias is already exported from `localstock.observability` and ready to import.
- **24-06** pipeline `_step_timer` async context manager will reuse the `op_duration_seconds` label semantics (`pipeline.step.{step_name}`) — same metric, different recording surface.

## Self-Check: PASSED

Verified files exist on disk:
- `apps/prometheus/src/localstock/observability/decorators.py` ✓
- `apps/prometheus/tests/test_observability/test_decorators.py` ✓
- `apps/prometheus/src/localstock/observability/__init__.py` (re-exports added) ✓
- `apps/prometheus/src/localstock/observability/metrics.py` (Rule-3 fix) ✓

Verified commits exist (`git log --oneline`):
- `d0d4b66` RED ✓
- `1605197` GREEN ✓
