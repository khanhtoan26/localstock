---
phase: 25-data-quality
plan: 02
subsystem: dq
tags: [DQ-04, SC-2, sanitizer, jsonb, repo-hardening]
status: complete
completed: 2026-04-29
wave: 1
depends_on: [25-01]
requirements: [DQ-04]
provides:
  - localstock.dq.sanitizer.sanitize_jsonb (canonical NaN/Inf scrubber)
  - JSONB write-boundary hardening across 5 repos
requires:
  - Wave 0 stub + RED tests (25-01)
  - localstock.dq package
affects:
  - apps/prometheus/src/localstock/db/repositories/{financial,report,score,notification,job}_repo.py
  - apps/prometheus/src/localstock/services/pipeline.py (replaces inlined _clean_nan)
tech_stack:
  added: []
  patterns:
    - "Write-boundary sanitizer (RESEARCH Pattern 3)"
    - "Single source of truth replacing duplicated inline helper"
key_files:
  created:
    - apps/prometheus/src/localstock/dq/sanitizer.py (full impl, replaces stub)
  modified:
    - apps/prometheus/src/localstock/db/repositories/financial_repo.py
    - apps/prometheus/src/localstock/db/repositories/report_repo.py
    - apps/prometheus/src/localstock/db/repositories/score_repo.py
    - apps/prometheus/src/localstock/db/repositories/notification_repo.py
    - apps/prometheus/src/localstock/db/repositories/job_repo.py
    - apps/prometheus/src/localstock/services/pipeline.py
    - apps/prometheus/tests/test_dq/test_sanitizer.py
decisions:
  - "Per wave coordination, scheduler/scheduler.py:156 errors-dict NOT wrapped (owned by 25-03 in same wave) — covered when 25-03 lands; static dict has no NaN/Inf risk anyway."
  - "Sanitizer treats numpy.float64 via isinstance(value, float) (np.float64 subclasses float) — no numpy import needed in production path."
  - "bool short-circuited before numeric branch so False stays False (would otherwise round-trip through float())."
  - "Tuples are normalized to lists (JSON has no tuple)."
metrics:
  duration_minutes: 12
  tasks_completed: 3
  files_modified: 8
  commits: 2
---

# Phase 25 Plan 02: JSONB Write-Boundary Sanitizer (DQ-04) Summary

**One-liner:** `sanitize_jsonb` recursive NaN/±Inf scrubber wired at every JSONB-bound repo write — closes ROADMAP Success Criterion #2 verbatim.

## What Shipped

- **`localstock.dq.sanitizer.sanitize_jsonb(value) -> Any`** — recursive walker over `dict`/`list`/`tuple`; replaces `float('nan'/'inf'/'-inf')` (incl. `numpy.float64`) with `None`; idempotent on clean input; preserves int/bool/str/Decimal as-is. ~45 LOC.
- **5 repositories wired** — `sanitize_jsonb` is the first executable line of every JSONB-bound write method:
  - `FinancialRepository.upsert_statement(data=…)`
  - `ReportRepository.upsert(row)` — wraps full row dict so `content_json` and any nested float traps are scrubbed.
  - `ScoreRepository.bulk_upsert(rows)` — covers `weights_json`.
  - `NotificationRepository.log_notification(details=…)`
  - `JobRepository.create_job(params=…)` and `update_status(result=…)`
- **`services/pipeline.py` cleanup** — deleted the inline `_clean_nan` helper (12 LOC), replaced two call-sites with `sanitize_jsonb(...)`. Single source of truth restored.
- **`PipelineRun.errors` defensive wraps** — wrapped the four error-dict construction sites at lines 213, 222, 233, 249 (RESEARCH Audit List).
- **Integration test (`@requires_pg`)** — writes `content_json` containing `float('inf')`, `float('nan')`, `-float('inf')`, plus nested list+dict; SELECTs `content_json::text`; asserts neither `'NaN'` nor `'Infinity'` appear, and `'null'` does. Verifies SC #2 end-to-end against real Postgres.

## RED → GREEN

| Test | Status before | Status after |
|------|---------------|--------------|
| `test_nan_to_none` | RED (NotImplementedError) | GREEN |
| `test_inf_and_neg_inf_to_none` | RED | GREEN |
| `test_recursive_sanitize` | RED | GREEN |
| `test_numpy_scalars_handled` | RED | GREEN |
| `test_idempotent_on_clean_input` | RED | GREEN |
| `test_report_repo_sanitizes_inf` (integration) | SKIPPED | GREEN (Postgres-backed, end-to-end SC #2 proof) |

Full suite: **537 passed, 1 pre-existing failure** (`test_migration_downgrade_removes_columns` — Phase 24 Alembic state, unrelated; verified failing on baseline `master` via `git stash` test).

## Files & Commits

| Commit | Title |
|--------|-------|
| `ca1fcdb` | `feat(25-02): implement sanitize_jsonb (DQ-04 unit tests GREEN)` |
| `c7df127` | `feat(25-02): wire sanitize_jsonb into JSONB repos + integration test (DQ-04, SC #2)` |

## Deviations from Plan

**1. [Rule 3 - Wave coordination] Skipped scheduler/scheduler.py:156 errors-dict wrap**
- **Found during:** Task 2
- **Issue:** User prompt explicitly forbids editing `scheduler/scheduler.py` because Wave 1 plan 25-03 (running in parallel) owns that file. Confirmed via `git stash` revealing 25-03's uncommitted changes to `scheduler/scheduler.py` + `dq/quarantine_repo.py` + `test_quarantine_cleanup.py`.
- **Resolution:** Skipped that single wrap. The dict at line 156 is a static literal (`{"error": "abandoned", "reason": "..."}`) with no float content — no NaN/Inf risk. Documented for 25-03 to optionally wrap when they merge their changes; or for a follow-up plan to add (low priority).
- **Files affected:** none (scheduler.py left untouched by this plan).

**2. [Rule 2 - Robustness] Sanitizer handles `int` explicitly**
- **Issue:** Plan recipe drafted in PLAN body did `try: float(value)` for every non-float — would convert clean `int` values via float round-trip unnecessarily.
- **Resolution:** Added `isinstance(value, int)` short-circuit so int stays typed. Also short-circuit `bool` (subclass of int) before either numeric branch so `False` doesn't lose typing. Pure micro-correctness; tests still GREEN.

## Threat Surface

Threat model T-25-02-01..03 mitigations all satisfied:
- LLM-produced `content_json` (T-01) → `report_repo.upsert` calls `sanitize_jsonb(row)` first.
- "Infinity" string leaking through API JSON parse (T-02) → fixed at write boundary; reads are now safe.
- Crawler DataFrame NaN (T-03) → `financial_repo.upsert_statement` wraps `data` first.

## Self-Check: PASSED

- `apps/prometheus/src/localstock/dq/sanitizer.py` — exists, contains `def sanitize_jsonb`, full impl (no `NotImplementedError`).
- 5 repos all `grep -l sanitize_jsonb` match (verified by automated check in plan).
- `_clean_nan` removed from `services/pipeline.py` (verified `grep -c _clean_nan` returns 0).
- Commits `ca1fcdb` and `c7df127` present in `git log`.
- 6/6 tests pass in `tests/test_dq/test_sanitizer.py` (5 unit + 1 integration).
- ROADMAP SC #2 closed end-to-end against live Postgres.
