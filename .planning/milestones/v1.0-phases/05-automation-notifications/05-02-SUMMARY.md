---
phase: 05-automation-notifications
plan: 02
subsystem: services, notifications
tags: [score-change-detection, sector-rotation, telegram, formatters, notifications]
dependency_graph:
  requires: [05-01-PLAN]
  provides: [score-change-service, sector-rotation-service, telegram-notifier, message-formatters]
  affects: [05-03-PLAN]
tech_stack:
  added: []
  patterns: [score-comparison, sector-aggregation, telegram-html-messages, message-splitting]
key_files:
  created:
    - src/localstock/services/score_change_service.py
    - src/localstock/services/sector_service.py
    - src/localstock/notifications/__init__.py
    - src/localstock/notifications/telegram.py
    - src/localstock/notifications/formatters.py
    - tests/test_services/test_score_changes.py
    - tests/test_services/test_sector_rotation.py
    - tests/test_notifications/__init__.py
    - tests/test_notifications/test_telegram.py
    - tests/test_notifications/test_formatters.py
  modified: []
decisions:
  - "detect_score_changes is a standalone async function (not a class) — simple single-purpose contract"
  - "SectorService uses IndustryRepository.get_all_groups + get_symbols_by_group for per-group aggregation"
  - "TelegramNotifier uses HTML parse mode for simpler escaping (no Markdown edge cases)"
  - "Message splitting at 4000 chars (Telegram limit is 4096, 4000 gives safety margin)"
  - "Formatters produce Vietnamese language output with emoji indicators for mobile readability"
metrics:
  duration: 4min
  completed: 2026-04-16T08:01:00Z
  tasks: 2
  files: 10
---

# Phase 05 Plan 02: Score Change Detection, Sector Rotation & Telegram Notifications Summary

**One-liner:** Score change detection (>15pt threshold) comparing consecutive scoring dates, sector rotation tracking with inflow/outflow classification, TelegramNotifier with HTML messages and 4000-char splitting, plus 3 Vietnamese message formatters for digest/alerts/rotation.

## What Was Done

### Task 1: Score change detection service + sector rotation service (TDD)
- Created `score_change_service.py` with `detect_score_changes()` — compares consecutive scoring dates, finds stocks with >15pt absolute change, sets direction up/down
- Created `sector_service.py` with `SectorService` class — `compute_snapshot()` aggregates avg_score per industry group, `get_rotation_summary()` classifies sectors as inflow (>2.0 change) / outflow (<-2.0) / stable
- 4 tests for score change detection: large increase, large decrease, no previous data (Pitfall 5), below-threshold filtering
- 3 tests for sector rotation: aggregation by group, inflow/outflow classification, empty data handling
- Commits: `112577b` (RED), `982a67d` (GREEN)

### Task 2: TelegramNotifier + message formatters (TDD)
- Created `notifications/telegram.py` with `TelegramNotifier` — sends HTML messages via python-telegram-bot Bot, silently skips when unconfigured, splits messages >4000 chars at newline boundaries
- Created `notifications/formatters.py` with 3 formatters:
  - `format_daily_digest()` — top 10 stocks with scores/grades, score changes with arrows, sector rotation summary
  - `format_score_alerts()` — alert message with grade transitions (C→B) and delta values
  - `format_sector_rotation()` — detailed inflow/outflow with avg scores and stock counts
- 7 tests for TelegramNotifier: config checks, send behavior, error handling, message splitting
- 7 tests for formatters: header/date, top stocks, empty handling, score changes, sector rotation, grade transitions, no rotation
- Commits: `02b0235` (RED), `a999a02` (GREEN)

## Decisions Made

1. **detect_score_changes as standalone function** — Single-purpose contract, no state needed, matches session-based pattern used across the project.
2. **HTML parse mode for Telegram** — Simpler escaping than Markdown (no backslash-escaping of `_`, `*`, etc.), supports `<b>`, `<i>` natively.
3. **4000-char message split threshold** — Telegram API limit is 4096 chars; using 4000 as safety margin for emoji multi-byte encoding overhead.
4. **Vietnamese language formatters** — Matches project target audience, emoji indicators (📈📉🏆🔄) for mobile readability.
5. **SectorService aggregation via IndustryRepository** — Reuses existing get_all_groups/get_symbols_by_group, no new queries needed.

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **Before:** 285 existing tests passing
- **After:** 309 tests passing (285 existing + 7 score/sector + 17 notification)
- **Zero regressions**

## Verification Results

1. ✅ `uv run pytest tests/ -x -q --timeout=30` — 309 passed
2. ✅ `python -c "from localstock.services.score_change_service import detect_score_changes"` — imports clean
3. ✅ `python -c "from localstock.services.sector_service import SectorService"` — imports clean
4. ✅ `python -c "from localstock.notifications.telegram import TelegramNotifier"` — imports clean
5. ✅ `python -c "from localstock.notifications.formatters import format_daily_digest, format_score_alerts, format_sector_rotation"` — imports clean

## Self-Check: PASSED

All 10 created files exist. All 4 commit hashes verified in git log.
