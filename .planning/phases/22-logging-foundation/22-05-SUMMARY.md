---
phase: 22-logging-foundation
plan: 05
subsystem: observability
tags: [logging, refactor, structured-events, OBS-01, OBS-06]
requires: [22-01, 22-03, 22-04]
provides:
  - "Zero f-string log calls across apps/prometheus/{src,tests,bin}"
  - "OBS-06 lint gate now green (lint-no-fstring-logs.sh exits 0)"
  - "OBS-01 structured-extras surface — every variable now flows through record.extra (redaction patcher applies)"
affects: [observability, crawlers, repositories, services, ai, analysis, notifications, cli]
tech_stack_added: []
patterns_used:
  - "loguru kwargs form: logger.X('event.name', k=v, ...) — extras serialize as JSON"
  - "logger.exception('event.name') in except blocks — captures stack via loguru exc_info"
  - "Event-name convention: ASCII dot-separated (<area>.<action>(.<status>))"
key_files:
  modified:
    - apps/prometheus/src/localstock/crawlers/base.py
    - apps/prometheus/src/localstock/crawlers/company_crawler.py
    - apps/prometheus/src/localstock/crawlers/event_crawler.py
    - apps/prometheus/src/localstock/crawlers/finance_crawler.py
    - apps/prometheus/src/localstock/crawlers/news_crawler.py
    - apps/prometheus/src/localstock/crawlers/price_crawler.py
    - apps/prometheus/src/localstock/macro/crawler.py
    - apps/prometheus/src/localstock/db/repositories/event_repo.py
    - apps/prometheus/src/localstock/db/repositories/indicator_repo.py
    - apps/prometheus/src/localstock/db/repositories/industry_repo.py
    - apps/prometheus/src/localstock/db/repositories/job_repo.py
    - apps/prometheus/src/localstock/db/repositories/macro_repo.py
    - apps/prometheus/src/localstock/db/repositories/news_repo.py
    - apps/prometheus/src/localstock/db/repositories/price_repo.py
    - apps/prometheus/src/localstock/db/repositories/ratio_repo.py
    - apps/prometheus/src/localstock/db/repositories/report_repo.py
    - apps/prometheus/src/localstock/db/repositories/score_repo.py
    - apps/prometheus/src/localstock/db/repositories/sector_repo.py
    - apps/prometheus/src/localstock/db/repositories/sentiment_repo.py
    - apps/prometheus/src/localstock/db/repositories/stock_repo.py
    - apps/prometheus/src/localstock/services/admin_service.py
    - apps/prometheus/src/localstock/services/analysis_service.py
    - apps/prometheus/src/localstock/services/automation_service.py
    - apps/prometheus/src/localstock/services/news_service.py
    - apps/prometheus/src/localstock/services/report_service.py
    - apps/prometheus/src/localstock/services/score_change_service.py
    - apps/prometheus/src/localstock/services/scoring_service.py
    - apps/prometheus/src/localstock/services/sector_service.py
    - apps/prometheus/src/localstock/ai/client.py
    - apps/prometheus/src/localstock/analysis/technical.py
    - apps/prometheus/src/localstock/notifications/telegram.py
    - apps/prometheus/bin/crawl_all.py
    - apps/prometheus/bin/crawl_single.py
    - apps/prometheus/bin/run_reports.py
decisions:
  - "Used logger.exception(event) inside every except block where the original code interpolated {e} — auto-captures traceback, satisfies OBS-01 redaction surface (the exception object is no longer baked into a flat string)."
  - "Behavior preserved: notif_repo.log_notification(...) calls in automation_service still receive str(e) for DB persistence — the f-string conversion only changed the *log call*, not downstream side effects."
  - "Multi-line f-string log calls (not detected by single-line lint regex) were also migrated for consistency (base.py batch error, ai/client.py sentiment summary, analysis_service.py run summary, news_service.py crawl summary)."
metrics:
  duration_minutes: ~25
  tasks_completed: 3
  files_modified: 34
  commits: 4
  completed_date: 2026-04-28
---

# Phase 22 Plan 05: F-String Log Sweep Summary

Mechanical migration of every `logger.X(f"...")` call across `apps/prometheus/src` and `apps/prometheus/bin` to loguru's structured-kwargs form, unblocking the OBS-06 CI lint gate and ensuring OBS-01 structured-extras carry every variable as a JSON field instead of a flattened message string.

## What Changed

- **34 files** modified across 7 subsystems (crawlers, macro, db/repositories, services, ai, analysis, notifications, bin/ CLI scripts).
- **~95 single-line f-string log calls** plus ~5 multi-line f-string log calls converted.
- **Event-name namespaces** introduced (ASCII, dot-separated, lowercase, grep-able):
  - `crawl.<entity>.<action>` for crawlers
  - `<entity>_repo.<action>(.<status>)` for repositories
  - `<area>.<action>(.<status>)` for services (analysis, scoring, report, sector, news)
  - `automation.step.<status>` for the 6-step pipeline orchestrator
  - `admin.<job_type>.<action>` for the admin worker
  - `ai.client.<sentiment|report>.<phase>` for the Ollama wrapper
  - `analysis.technical.<indicator>_failed` for indicator computation guards
  - `telegram.send.<status>` for notifications
  - `cli.<script>.<action>` for bin/ entrypoints
- **Exception handling upgrade:** every `logger.error(f"...{e}")` inside an `except` block was rewritten to `logger.exception("event.name", ...)` — traceback now flows through loguru's `exc_info` into the redacted JSON sink instead of being string-interpolated into the message.

## Verification

| Check | Command | Result |
|---|---|---|
| OBS-06 lint gate | `bash apps/prometheus/scripts/lint-no-fstring-logs.sh` | exit 0 ("OK: zero f-string log calls.") |
| Test suite | `cd apps/prometheus && uv run pytest tests/ -x` | 462 passed, 1 unrelated deprecation warning |
| `# noqa: log-fstring` count | `grep -rc "noqa: log-fstring" apps/prometheus/{src,bin}` | 0 (well under the ≤5 budget) |
| New files | `git status -s` | none — pure modifications |

## Commits

| Hash | Scope | Files |
|---|---|---|
| `edd21cc` | crawlers + macro | 7 |
| `1def9c7` | db/repositories | 13 |
| `a25d9c5` | services + ai + analysis + notifications | 11 |
| `8d13a67` | bin/ CLI scripts | 3 |

Split-by-module commits preserve revert safety per plan instructions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Scope expansion] Migrated multi-line f-string log calls**
- **Found during:** Tasks 1–2 (file reads)
- **Issue:** The lint regex only catches single-line `logger.X(\s*f"...")`. Several call sites use multi-line implicit string concatenation (e.g., `crawlers/base.py:54`, `services/news_service.py:69`, `services/analysis_service.py:146`, `ai/client.py:178`, `services/report_service.py` summary). These are still f-string log violations per CONTEXT.md D-05 ("Hard-cut day one").
- **Fix:** Converted to structured-kwargs form alongside the single-line calls.
- **Files:** crawlers/base.py, services/news_service.py, services/analysis_service.py, ai/client.py
- **Commits:** edd21cc, a25d9c5

**2. [Rule 1 — Bug avoided] Preserved `str(e)` in `notif_repo.log_notification` payload**
- **Found during:** automation_service.py edits
- **Issue:** Initial conversion changed `except Exception as e: ... await notif_repo.log_notification(today, "daily_digest", "failed", {"error": str(e)})` to `except Exception:` — which would have dropped the error string from the persisted notification record.
- **Fix:** Reverted the `as e` removal in those two notification blocks; only the `logger.error(...)` was replaced with `logger.exception(...)`. The `str(e)` continues to flow into the DB.
- **Files:** services/automation_service.py
- **Commit:** a25d9c5

### Auth Gates

None.

## Stub / Threat Surface Notes

No new stubs introduced. No new network endpoints, auth paths, or trust boundaries — pure call-site refactor. No threat flags.

## Self-Check: PASSED

Verified:
- `apps/prometheus/scripts/lint-no-fstring-logs.sh` → exit 0
- All 4 commits present in `git log`: 8d13a67, a25d9c5, 1def9c7, edd21cc
- All 34 files in `files_modified` exist in tree
- `pytest tests/ -x` → 462 passed
