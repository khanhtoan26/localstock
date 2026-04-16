---
phase: 05-automation-notifications
plan: 03
subsystem: automation, scheduler, api
tags: [automation-service, apscheduler, api-endpoints, fastapi-lifespan, pipeline-orchestration]
dependency_graph:
  requires: [05-01-PLAN, 05-02-PLAN]
  provides: [automation-service, scheduler-integration, automation-api-endpoints, fastapi-lifespan]
  affects: []
tech_stack:
  added: []
  patterns: [pipeline-orchestration, asyncio-lock-concurrency, cron-trigger, fastapi-lifespan]
key_files:
  created:
    - src/localstock/services/automation_service.py
    - src/localstock/scheduler/scheduler.py
    - src/localstock/api/routes/automation.py
    - tests/test_services/test_automation_service.py
  modified:
    - src/localstock/api/app.py
decisions:
  - "AutomationService uses get_session_factory() for per-step sessions — each pipeline step gets its own session lifecycle"
  - "asyncio.Lock at module level prevents concurrent pipeline runs, API returns 409 when locked"
  - "APScheduler initialized inside FastAPI lifespan, not at import time (Pitfall 3 prevention)"
  - "On-demand runs force=True to skip trading day check — user intent overrides schedule"
  - "Symbol path parameter validated with regex ^[A-Z0-9]+$ and max_length=10 (T-05-09 mitigation)"
metrics:
  duration: 5min
  completed: 2026-04-16T08:11:00Z
  tasks: 2
  files: 5
---

# Phase 05 Plan 03: AutomationService, Scheduler & API Endpoints Summary

**One-liner:** Full pipeline orchestrator (crawl→analyze→news→sentiment→score→report→detect changes→sector rotation→notify) with APScheduler at 15:45 VN time, on-demand API triggers, and FastAPI lifespan integration.

## What Was Done

### Task 1: AutomationService — full pipeline orchestrator with notifications (TDD)
- Created `automation_service.py` with `AutomationService` class — runs 6-step pipeline, detects score changes (SCOR-04), computes sector rotation (SCOR-05), sends Telegram digest and alerts (NOTI-01, NOTI-02)
- Trading day check skips pipeline on weekends/holidays (unless force=True for on-demand)
- Concurrent run prevention via module-level `asyncio.Lock` — returns status="skipped" + reason="already_running"
- Notification dedup via `NotificationRepository.was_sent_today()` before sending (Pitfall 2)
- Each pipeline step has try/except — failures logged but don't crash pipeline (graceful degradation)
- On-demand `run_on_demand(symbol=None)` for full or single-symbol analysis
- 9 tests: non-trading day skip, all 6 steps execution, score change detection, sector rotation, notification skip when unconfigured, summary dict structure, step failure handling, single symbol, on-demand full
- Commits: `6102f50` (RED), `3084494` (GREEN)

### Task 2: Scheduler integration + API endpoints + FastAPI lifespan
- Created `scheduler/scheduler.py` with `AsyncIOScheduler` + `CronTrigger` at configured hour/minute, mon-fri, Asia/Ho_Chi_Minh timezone
- `setup_scheduler()` adds daily pipeline job with `misfire_grace_time=3600` (1hr grace window)
- `get_lifespan()` async context manager starts/stops scheduler with FastAPI lifecycle
- Created `api/routes/automation.py` with 3 endpoints:
  - `POST /api/automation/run` — trigger full pipeline on demand (force=True)
  - `POST /api/automation/run/{symbol}` — single stock analysis with regex validation
  - `GET /api/automation/status` — scheduler state, pipeline lock state, scheduled jobs
- Updated `app.py` — added automation_router (7 total routers) and lifespan=get_lifespan
- Commit: `f4721bc`

## Decisions Made

1. **Per-step session lifecycle** — Each pipeline step gets its own `async with session_factory()` context to prevent session state bleed between long-running operations.
2. **Module-level asyncio.Lock** — Single `_pipeline_lock` prevents concurrent pipeline runs from both scheduler and API triggers. API returns HTTP 409 when locked.
3. **Scheduler in lifespan, not import time** — `setup_scheduler()` called inside `get_lifespan()` to avoid scheduler initialization during test imports (Pitfall 3).
4. **Force flag for on-demand** — On-demand runs skip trading day check because user intent implies they want results regardless of calendar.
5. **Symbol regex validation** — `^[A-Z0-9]+$` with max_length=10 on path parameter prevents injection (T-05-09).

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **Before:** 309 existing tests passing
- **After:** 318 tests passing (309 existing + 9 automation service)
- **Zero regressions**

## Verification Results

1. ✅ `uv run pytest tests/ -x -q --timeout=30` — 318 passed
2. ✅ `python -c "from localstock.api.app import app; ..."` — shows /api/automation/* routes (27 total routes)
3. ✅ `python -c "from localstock.scheduler.scheduler import scheduler; ..."` — AsyncIOScheduler type confirmed
4. ✅ `python -c "from localstock.services.automation_service import AutomationService"` — imports clean
5. ✅ `grep -c "include_router" src/localstock/api/app.py` — returns 7 (all routers)

## Self-Check: PASSED

All 4 created files exist. All 3 commit hashes verified in git log.
