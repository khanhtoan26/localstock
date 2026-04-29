---
phase: 25-data-quality
plan: 03
subsystem: dq, scheduler
tags: [DQ-08, quarantine, retention, apscheduler]
status: Complete
type: tdd
wave: 1
depends_on: [25-01]
requirements: [DQ-08]
dependency_graph:
  requires:
    - 25-01 quarantine_rows table (Alembic 25a0b1c2d3e4)
    - 25-02 sanitize_jsonb (cross-cutting belt + suspenders)
    - Phase 24 @observe decorator
  provides:
    - QuarantineRepository.insert(*, source, symbol, payload, reason, rule, tier)
    - QuarantineRepository.cleanup_older_than(*, days=30) -> int
    - APScheduler job id "dq_quarantine_cleanup" (CronTrigger hour=3 minute=15 Asia/Ho_Chi_Minh)
  affects:
    - apps/prometheus/src/localstock/dq/quarantine_repo.py
    - apps/prometheus/src/localstock/scheduler/scheduler.py
tech_stack:
  added: []
  patterns:
    - "Async repo over `text()` SQL on `quarantine_rows`; caller commits."
    - "APScheduler CronTrigger with explicit Asia/Ho_Chi_Minh tz + max_instances=1 + coalesce=True (Pitfall F)."
    - "`@observe('dq.quarantine.cleanup')` instrumentation on the cron entry point."
key_files:
  created: []
  modified:
    - apps/prometheus/src/localstock/dq/quarantine_repo.py
    - apps/prometheus/src/localstock/scheduler/scheduler.py
    - apps/prometheus/tests/test_scheduler/test_quarantine_cleanup.py
decisions:
  - "Cleanup uses `datetime.now(UTC) - timedelta(days)` cutoff bound parameter rather than SQL `now() - interval` so the boundary is testable with frozen-time fixtures and not subject to server-clock drift."
  - "Cron registered AFTER existing daily_pipeline / admin_job / health_self_probe / error_listener blocks in setup_scheduler() so it inherits the same `replace_existing=True` idempotency and EVENT_JOB_ERROR listener."
  - "Test asserts `job.trigger.timezone` (attribute) instead of `'Asia/Ho_Chi_Minh' in str(job.trigger)` because CronTrigger.__str__ omits timezone — the original RED scaffold assertion was structurally wrong."
metrics:
  duration: "~12 minutes"
  completed_date: "2026-04-29"
  tasks_completed: 2
  files_modified: 3
  red_to_green_tests: 4
---

# Phase 25 Plan 03: QuarantineRepository + 30-day Retention Cron Summary

QuarantineRepository.insert/cleanup_older_than implemented over `quarantine_rows`; APScheduler `dq_quarantine_cleanup` cron registered at 03:15 Asia/Ho_Chi_Minh with `@observe`-instrumented body — closes the operational half of CONTEXT D-02 (DQ-08).

## What Shipped

- **`QuarantineRepository.insert`** (apps/prometheus/src/localstock/dq/quarantine_repo.py): persists `(source, symbol, payload, reason, rule, tier)` to `quarantine_rows` via parameterized `INSERT … VALUES (… CAST(:payload AS JSONB) …)`. Payload runs through `sanitize_jsonb` first — belt-and-suspenders cross-check with DQ-04 so any caller forgetting to pre-sanitize still produces clean JSONB. Caller commits.
- **`QuarantineRepository.cleanup_older_than(days=30)`**: deletes rows whose `quarantined_at` is older than `now(UTC) - timedelta(days)` and returns affected rowcount. Default 30 days per CONTEXT D-02. Logs `dq.quarantine.cleanup` with `deleted` and `days` extras.
- **`_quarantine_cleanup_job`** in `setup_scheduler()`: opens its own AsyncSession via `get_session_factory()`, calls the repo, commits. Decorated with `@observe('dq.quarantine.cleanup')` so the Phase 24 outcome counter / latency histogram pick it up.
- **Cron registration**: `add_job(id="dq_quarantine_cleanup", trigger=CronTrigger(hour=3, minute=15, timezone="Asia/Ho_Chi_Minh"), max_instances=1, coalesce=True, replace_existing=True)`. Pitfall F: 03:15 is far away from the 15:46 daily pipeline window, so retention cannot collide with crawl/score.
- **Test fix**: `test_quarantine_cleanup_job_registered` rewritten to assert against `job.trigger.timezone`, hour/minute fields, and the max_instances/coalesce flags — replaces the original `'Asia/Ho_Chi_Minh' in str(job.trigger)` assertion that could never have passed (CronTrigger.__str__ omits tz).

## RED → GREEN

| Test | Path | Before | After |
|---|---|---|---|
| test_insert_persists_row | tests/test_dq/test_quarantine_repo.py | RED (NotImplementedError) | GREEN |
| test_cleanup_30d_deletes_old_rows | tests/test_dq/test_quarantine_repo.py | RED (NotImplementedError) | GREEN |
| test_insert_sanitizes_nan_in_payload | tests/test_dq/test_quarantine_repo.py | RED (NotImplementedError) | GREEN |
| test_quarantine_cleanup_job_registered | tests/test_scheduler/test_quarantine_cleanup.py | RED (job missing) | GREEN |

Verification command:

```bash
cd apps/prometheus && uv run pytest tests/test_dq/test_quarantine_repo.py tests/test_scheduler/test_quarantine_cleanup.py -q
# 4 passed in 12.91s
```

## Commits

| Task | Hash | Message |
|---|---|---|
| 1 | 27fdf3f | feat(25-03): QuarantineRepository.insert + cleanup_older_than (DQ-08) |
| 2 | d2a9708 | feat(25-03): register dq_quarantine_cleanup APScheduler cron (DQ-08) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Test assertion `'Asia/Ho_Chi_Minh' in str(job.trigger)` could never pass**

- **Found during:** Task 2 verification.
- **Issue:** `CronTrigger.__str__` returns `"cron[hour='3', minute='15']"` — it omits the timezone. The original 25-01 RED scaffold's only assertion was therefore unsatisfiable even by a correctly-registered job.
- **Fix:** Rewrote the test to use the structured assertion suggested by the plan's Task 2 action block — `isinstance(job.trigger, CronTrigger)`, `str(job.trigger.timezone) == "Asia/Ho_Chi_Minh"`, hour/minute via `job.trigger.fields`, and the `max_instances` / `coalesce` flags.
- **Files modified:** apps/prometheus/tests/test_scheduler/test_quarantine_cleanup.py.
- **Commit:** d2a9708.

**2. [Rule 2 — Adopted plan-suggested assertion shape]** The plan's Task 2 already specified the richer set of assertions (fields + max_instances + coalesce); 25-01's RED scaffold had only the single insufficient line. Bringing the test to the plan-specified shape doubled as fixing Rule 1 above.

## Authentication Gates

None — no external systems touched.

## Notes / Cross-Plan Context

- **25-02 already landed in master** (commits `ca1fcdb`, `c7df127`) by the time this plan executed, so `sanitize_jsonb` was real and Test 3 went GREEN immediately. The original prompt described 25-02 as parallel; in practice it had merged first. Either ordering would have worked — the per-test outcomes only depend on `sanitize_jsonb` being non-stub.
- **No production caller** of `QuarantineRepository` is wired yet — that integration lands in 25-05 (DQ-01 reject-to-quarantine). The repo and cron are fully usable but quarantine_rows will remain empty until 25-05 ships.
- **Replay path** (manual SQL only) remains explicitly out of scope per CONTEXT D-02.

## Deferred Issues

- **Quarantine repo tests intermittently report 2 ERRORS in the *full* suite** while passing cleanly when run alone or in `tests/test_dq/`. Net suite delta is still positive (538→540 passes, 20→17 failures). Root cause is the per-test engine creation/disposal in the 25-01-authored fixture interacting with another test's event-loop scope downstream, not the implementation in this plan. Logging here for the verifier; a fixture refactor would be a separate plan.
- 17 unrelated FAILED tests are pre-existing 25-01 RED scaffolds for downstream plans (test_ohlcv_schema → 25-05, test_tier2_dispatch → 25-07, test_pipeline_isolation → 25-06, test_pipeline_stats → 25-04, test_health_data_freshness → 25-08, plus the long-standing test_migration_24_pipeline_durations downgrade test). None are caused by 25-03.

## Threat Model Alignment

| Threat | Disposition | Realized mitigation |
|---|---|---|
| T-25-03-01 unbounded quarantine_rows growth | mitigate | `cleanup_older_than(days=30)` + 03:15 cron |
| T-25-03-02 NaN/Inf in payload | mitigate | `sanitize_jsonb(payload)` at insert entry |
| T-25-03-03 collision with 15:46 pipeline | mitigate | hour=3 minute=15 + max_instances=1 + coalesce=True |
| T-25-03-04 third-party data disclosure | accept | unchanged — HOSE market data only |

No new threat surface introduced (`threat_flag: none`).

## Self-Check: PASSED

- ✅ apps/prometheus/src/localstock/dq/quarantine_repo.py — found
- ✅ apps/prometheus/src/localstock/scheduler/scheduler.py — found
- ✅ apps/prometheus/tests/test_scheduler/test_quarantine_cleanup.py — found
- ✅ commit 27fdf3f — found in `git log`
- ✅ commit d2a9708 — found in `git log`
- ✅ targeted suite: 4 passed in 12.91s
- ✅ ruff: All checks passed!
