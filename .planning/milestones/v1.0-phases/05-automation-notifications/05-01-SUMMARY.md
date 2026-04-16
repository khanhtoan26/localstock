---
phase: 05-automation-notifications
plan: 01
subsystem: scheduler, db-models, config
tags: [automation, scheduler, db-models, trading-calendar, repositories]
dependency_graph:
  requires: [04-04-PLAN]
  provides: [scheduler-calendar, score-change-alert-model, sector-snapshot-model, notification-log-model, extended-score-repo, sector-repo, notification-repo]
  affects: [05-02-PLAN, 05-03-PLAN]
tech_stack:
  added: [apscheduler-3.11, python-telegram-bot-22.7, holidays-0.94]
  patterns: [merge-migration, trading-calendar, notification-dedup]
key_files:
  created:
    - src/localstock/scheduler/__init__.py
    - src/localstock/scheduler/calendar.py
    - src/localstock/db/repositories/sector_repo.py
    - src/localstock/db/repositories/notification_repo.py
    - alembic/versions/add_phase5_automation_tables.py
    - tests/test_scheduler/__init__.py
    - tests/test_scheduler/test_calendar.py
    - tests/test_phase5/__init__.py
    - tests/test_phase5/test_task1.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/localstock/config.py
    - src/localstock/db/models.py
    - src/localstock/db/repositories/score_repo.py
decisions:
  - "Alembic merge migration merges two heads (823bee92cc2e + a1b2c3d4e5f6) into single b5c6d7e8f901"
  - "holidays.Vietnam used for VN public holiday detection (handles lunar calendar Tết dates)"
  - "NotificationLog uq on (date, notification_type) for daily dedup"
metrics:
  duration: 8min
  completed: 2026-04-16T07:53:00Z
  tasks: 2
  files: 14
---

# Phase 05 Plan 01: Foundation — Dependencies, Models & Trading Calendar Summary

**One-liner:** APScheduler/Telegram/holidays deps installed, 5 config settings, 3 new DB tables (score_change_alerts, sector_snapshots, notification_logs) with merge migration, Vietnamese trading calendar with holiday detection, and 3 new repositories (extended score, sector, notification).

## What Was Done

### Task 1: Install dependencies, extend config, add DB models, create migration
- Added `apscheduler>=3.11,<4.0`, `python-telegram-bot>=22.0,<23.0`, `holidays>=0.94,<1.0` to pyproject.toml
- Extended Settings with 5 new fields: `telegram_bot_token`, `telegram_chat_id`, `scheduler_run_hour` (15), `scheduler_run_minute` (45), `score_change_threshold` (15.0)
- Added 3 ORM models: `ScoreChangeAlert`, `SectorSnapshot`, `NotificationLog` with unique constraints
- Created Alembic merge migration `b5c6d7e8f901` merging two heads (`823bee92cc2e` + `a1b2c3d4e5f6`)
- 8 new tests for config defaults and model tablenames
- Commits: `3f20036` (RED), `6a8b540` (GREEN)

### Task 2: Trading calendar, extended repositories, and tests
- Created `scheduler/calendar.py` with `is_trading_day()` and `get_next_trading_day()` using `holidays.Vietnam`
- Extended `ScoreRepository` with `get_previous_date_scores()` and `get_latest_date()` for SCOR-04 comparison
- Created `SectorSnapshotRepository` with `bulk_upsert`, `get_latest`, `get_by_date`, `get_by_date_range`
- Created `NotificationRepository` with `log_notification` (upsert dedup) and `was_sent_today`
- 10 new calendar tests covering weekdays, weekends, VN holidays (Reunification Day, National Day, New Year)
- Commits: `0175245` (RED), `6fe7ccd` (GREEN)

## Decisions Made

1. **Alembic merge migration** — Two heads existed from Phase 3 FK constraint and Phase 4 macro tables. Merged into single `b5c6d7e8f901` with tuple `down_revision`.
2. **holidays.Vietnam for trading calendar** — Handles lunar calendar dates (Tết shifts yearly), well-maintained package, covers all Vietnamese public holidays.
3. **NotificationLog dedup on (date, notification_type)** — Prevents duplicate notifications per type per day, supports upsert pattern for retry scenarios.

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **Before:** 267 existing tests passing
- **After:** 285 tests passing (267 existing + 8 config/model + 10 calendar)
- **Zero regressions**

## Verification Results

1. ✅ `uv run pytest tests/ -x -q --timeout=30` — 285 passed
2. ✅ `grep -c` models — 3 new models found
3. ✅ `grep` deps — all 3 dependencies in pyproject.toml
4. ✅ `python -c "from localstock.scheduler.calendar import is_trading_day"` — imports clean
5. ✅ `python -c "from localstock.db.repositories.sector_repo import SectorSnapshotRepository"` — imports clean

## Self-Check: PASSED

All 9 created files exist. All 4 commit hashes verified in git log.
