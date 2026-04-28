---
phase: 22-logging-foundation
plan: 04
subsystem: observability
tags: [logging, run_id, scheduler, contextvar, OBS-03]
requires: [22-01]
provides:
  - "Pipeline.run_full body bound to run_id contextvar + logger.contextualize"
  - "Scheduler lifespan defensive configure_logging() + logger.complete() shutdown drain"
  - "Structured scheduler.daily.* events with logger.exception on failure"
affects:
  - apps/prometheus/src/localstock/services/pipeline.py
  - apps/prometheus/src/localstock/scheduler/scheduler.py
tech-stack:
  added: []
  patterns:
    - "ContextVar.set(token) in try / reset(token) in finally for asyncio-safe correlation"
    - "logger.contextualize WRAPS existing function body — never replaces it"
    - "logger.exception over logger.error f-string in except blocks"
key-files:
  created: []
  modified:
    - apps/prometheus/src/localstock/services/pipeline.py
    - apps/prometheus/src/localstock/scheduler/scheduler.py
decisions:
  - "Reused PipelineRun.id verbatim per D-03 (str(run.id)) — no separate uuid4 minted"
  - "PipelineRun.id is autoincrement Integer in the schema; expire_on_commit=False on session factory means run.id is populated immediately after commit (no refresh needed)"
metrics:
  duration: ~15 min
  tasks_completed: 2
  files_modified: 2
  completed: 2026-04-28
---

# Phase 22 Plan 04: Pipeline run_id propagation + scheduler defensive wiring — Summary

Bound run_id contextvar onto every loguru record emitted from inside `Pipeline.run_full()` (OBS-03), wired the scheduler lifespan to call `configure_logging()` defensively at startup and `logger.complete()` on shutdown, and converted scheduler/pipeline f-string log calls to structured form.

## What was built

### Task 1 — services/pipeline.py (commit 6576c36)
- Imported `run_id_var` from `localstock.observability.context`.
- After `await self.session.commit()` populates `run.id`, the entire post-commit body of `run_full` was wrapped (verbatim — no business logic deletion or reordering) inside:
  ```python
  run_id = str(run.id)
  token = run_id_var.set(run_id)
  try:
      with logger.contextualize(run_id=run_id, pipeline_run_id=run.id):
          logger.info("pipeline.run.started", run_type=run_type)
          try:
              # >>> EXISTING BODY (Steps 1..8, exception handler) <<<
          finally:
              logger.info("pipeline.run.completed", status=run.status)
      await self.session.commit()
      return run
  finally:
      run_id_var.reset(token)
  ```
- Converted all f-string `logger.*` calls in `pipeline.py` (including `_store_financials`, `_crawl_prices`, `_apply_price_adjustments`, `run_single`) to structured kwargs.
- Replaced `logger.error(f"Pipeline failed: {e}")` and `logger.error(f"Failed to adjust prices ...")` with `logger.exception("pipeline.run.errored")` / `logger.exception("pipeline.adjustment.failed")` — capturing stack via loguru's `exc_info` handling per T-22-08 mitigation.

### Task 2 — scheduler/scheduler.py (commit b1e02f7)
- `daily_job` body replaced verbatim with structured events: `scheduler.daily.start`, `scheduler.daily.result`, `scheduler.daily.failed` (via `logger.exception`).
- `setup_scheduler` configured-log emitted as kwargs (`hour`, `minute`, `tz`).
- `get_lifespan` now imports `configure_logging` and calls it as the FIRST step inside the async context manager (idempotent guard makes this safe — covers CLI / scheduler-only entry points where the FastAPI app's `configure_logging` would not run).
- `logger.complete()` called post-`scheduler.shutdown()` to drain enqueued records before process exit (RESEARCH Open Question 3).
- All three pre-existing f-string log calls in scheduler.py eliminated.

## Verification

- `cd apps/prometheus && uv run pytest tests/test_observability/test_run_id.py -x` → **2 passed** (Wave 0 stub now backed by real wiring).
- `cd apps/prometheus && uv run pytest tests/ -k "pipeline"` → **14 passed** — no regression in pipeline/admin/automation suites.
- `cd apps/prometheus && uv run pytest tests/ -k "scheduler or lifespan"` → **12 passed**.
- `from localstock.api.app import create_app; create_app()` → OK (smoke).
- F-string lint: `! grep -E 'logger\.(...)\(\s*f["\']'` clean for both modified files.
- `grep -q "run_id_var.set"` / `logger.contextualize(run_id=` / `pipeline.run.started` / `pipeline.run.completed` in pipeline.py — all present.
- `grep -q "configure_logging()"` / `logger.complete()` / `scheduler.daily.start` / `scheduler.daily.failed` / `logger.exception` in scheduler.py — all present.
- Body preservation: `git diff 6576c36~1 6576c36 -- apps/prometheus/src/localstock/services/pipeline.py` shows additions (wrapper + structured-event rewrites) plus indentation shifts only; every existing `await crawl/finance/company/event/_apply_price_adjustments` call is preserved.

## Deviations from Plan

None — plan executed as written.

Note on D-03 wording: the plan refers to `pipeline_run.id` as a "UUID" but the actual `PipelineRun.id` column is `Integer` autoincrement. The directive ("reuse PipelineRun.id verbatim, do NOT mint a fresh uuid4") still applies — implementation uses `str(run.id)` of the persisted integer PK. Both `run_id` (string) and `pipeline_run_id` (raw int) are bound into `logger.contextualize` so downstream consumers can use either form.

## Threat Mitigations Applied

- **T-22-08 (Repudiation, scheduler swallowing exceptions):** `daily_job` and pipeline post-commit `except` now use `logger.exception(...)` — full stack trace captured.
- **T-22-09 (run_id Information Disclosure):** accepted; emitting run_id is the intended behavior of OBS-03.
- **T-22-10 (logger.complete DoS on slow shutdown):** accepted; uvicorn graceful shutdown timeout bounds the drain.

## Pre-existing condition observed (not addressed in this plan)

A failing test in `tests/test_observability/test_request_id.py` (sibling Wave 2 plan 22-03 territory) was confirmed to fail BEFORE this plan's edits via `git stash` round-trip. Out of scope per executor SCOPE BOUNDARY rules; flagged for the 22-03 verifier.

## Self-Check: PASSED

- FOUND: apps/prometheus/src/localstock/services/pipeline.py (modified)
- FOUND: apps/prometheus/src/localstock/scheduler/scheduler.py (modified)
- FOUND: commit 6576c36 (`git log --oneline | grep 6576c36`)
- FOUND: commit b1e02f7 (`git log --oneline | grep b1e02f7`)
- FOUND: tests/test_observability/test_run_id.py — 2 passed
