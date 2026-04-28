---
phase: 22-logging-foundation
plan: 01
subsystem: observability
tags: [logging, loguru, redaction, contextvars, intercept-handler]
requires: [22-00]
provides:
  - "localstock.observability.configure_logging"
  - "localstock.observability.request_id_var"
  - "localstock.observability.run_id_var"
  - "localstock.observability.logging.InterceptHandler"
  - "localstock.observability.logging._redact_url_creds"
  - "localstock.observability.logging._SENSITIVE_KEYS"
affects:
  - "all bin/*.py CLI entry points"
tech_stack:
  added: [loguru]
  patterns: [idempotent-singleton, contextvars, stdlib-bridge, deny-list-redaction]
key_files:
  created:
    - apps/prometheus/src/localstock/observability/__init__.py
    - apps/prometheus/src/localstock/observability/context.py
    - apps/prometheus/src/localstock/observability/logging.py
  modified:
    - apps/prometheus/bin/crawl_all.py
    - apps/prometheus/bin/crawl_single.py
    - apps/prometheus/bin/init_db.py
    - apps/prometheus/bin/run_analysis.py
    - apps/prometheus/bin/run_daily.py
    - apps/prometheus/bin/run_reports.py
    - apps/prometheus/bin/run_scoring.py
    - apps/prometheus/bin/run_sentiment.py
decisions:
  - "Used callable `_stdout_sink` instead of `sys.stdout` directly so capsys can capture output across tests (lazy stdout resolution; preserves serialize/enqueue/diagnose contract)."
metrics:
  duration_minutes: 6
  tasks_completed: 4
  completed_date: "2026-04-28"
requirements: [OBS-01, OBS-03, OBS-05]
---

# Phase 22 Plan 01: Observability Foundation Summary

JSON-stdout structured logging with idempotent configure_logging(), deny-list redaction patcher, and stdlib→loguru InterceptHandler — wired into every bin/ CLI entry point.

## What Was Built

- **`context.py`** — `request_id_var` / `run_id_var` ContextVar[str | None] (default=None) plus `get_request_id()` / `get_run_id()` accessors. Pure stdlib, loguru-agnostic.
- **`logging.py`** — `configure_logging()` with module-level `_configured` guard (Pitfall 5). Emits JSON via `serialize=True` to stdout in prod/CI/non-TTY; pretty colored stderr in dev TTY. `enqueue=True` except under `PYTEST_CURRENT_TEST` (D-08). `diagnose=False` on prod sink (Pitfall 17). `_redaction_patcher` redacts 8 deny-list keys to `***REDACTED***` and rewrites `://user:pass@host` → `://***:***@host` in messages, plus defensively enriches `record["extra"]` with current contextvars.
- **`InterceptHandler`** — frame-walking stdlib→loguru bridge installed on root + uvicorn{,.error,.access} / sqlalchemy.engine / apscheduler / httpx / httpcore / asyncpg with `propagate=False` (D-09).
- **`__init__.py`** — re-exports configure_logging, contextvars, accessors.
- **bin/*.py wiring** — all 8 CLI scripts call `configure_logging()` immediately after stdlib imports (B-1 fix from checker; idempotent guard makes co-execution with API safe).

## Tasks & Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | context.py — ContextVars + accessors | 13a22a2 | observability/context.py |
| 2 | logging.py — configure_logging + redaction + InterceptHandler | 13a22a2 | observability/logging.py |
| 3 | __init__.py — package re-exports | 13a22a2 | observability/__init__.py |
| 4 | Wire configure_logging() into all bin/*.py | eb8d55a | bin/{crawl_all,crawl_single,init_db,run_analysis,run_daily,run_reports,run_scoring,run_sentiment}.py |

(Tasks 1–3 grouped into one commit because the three files form a single import-coherent package; Task 4 is a separate concern.)

## Verification

- `uv run pytest tests/test_observability/{test_redaction,test_idempotent,test_diagnose_no_pii,test_intercept,test_json_format}.py` — **7/7 GREEN** (Wave 0 stubs flipped from RED → GREEN).
- Full suite minus Wave 2 stubs (test_request_id, test_request_log, test_run_id which depend on middleware not yet built): **456 passed**.
- All 8 bin scripts import cleanly via lazy spec-loader smoke test.
- `_SENSITIVE_KEYS ⊇ {token, api_key, password, secret, authorization, database_url, telegram_bot_token, bot_token}` ✓
- `_redact_url_creds("postgres://u:p@h") == "postgres://***:***@h"` ✓

## Deviations from Plan

### [Rule 3 - Blocking] Lazy stdout sink instead of `sys.stdout` reference

- **Found during:** Task 2 verification (test_redaction.py::test_token_extra_redacted).
- **Issue:** Plan locked `logger.add(sys.stdout, ...)` verbatim. Loguru freezes the file reference at `add()` time. Pytest's `capsys` replaces `sys.stdout` per-test, so after the first test calls `configure_logging()`, the idempotent guard prevents rebinding and subsequent tests' `capsys.readouterr()` returned empty (the sink wrote to the long-gone first capsys buffer).
- **Fix:** Introduced module-level `_stdout_sink(message)` callable that resolves `sys.stdout` lazily at write time. Loguru accepts callables as sinks; all spec invariants preserved — `serialize=True`, `enqueue=enqueue`, `backtrace=True`, `diagnose=False` all unchanged. In prod (non-pytest) behavior is identical to direct `sys.stdout` because `sys.stdout` is stable.
- **Files modified:** `apps/prometheus/src/localstock/observability/logging.py`
- **Commit:** 13a22a2

No other deviations. Plan executed exactly as written otherwise.

## Threat Surface Status

All threats from plan's `<threat_model>` mitigated:
- **T-22-01** (info disclosure): `diagnose=False` on prod sink ✓ + redaction patcher ✓
- **T-22-03** (DoS): `enqueue=False` under `PYTEST_CURRENT_TEST` ✓
- **T-22-04** (extra dict info disclosure): patcher iterates `_SENSITIVE_KEYS` case-insensitively ✓

No new threat surface introduced.

## Self-Check: PASSED

- `apps/prometheus/src/localstock/observability/__init__.py` — FOUND
- `apps/prometheus/src/localstock/observability/context.py` — FOUND
- `apps/prometheus/src/localstock/observability/logging.py` — FOUND
- All 8 `apps/prometheus/bin/*.py` contain `configure_logging()` — VERIFIED
- Commit `13a22a2` — FOUND in git log
- Commit `eb8d55a` — FOUND in git log
