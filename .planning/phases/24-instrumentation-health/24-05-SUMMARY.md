---
phase: 24-instrumentation-health
plan: 05
subsystem: observability
tags: [observability, scheduler, crawlers, prometheus, telegram, OBS-11, OBS-15, OBS-16]
requires:
  - 24-01 (decorator @observe)
  - 24-04 (split health endpoints — independent)
  - 23-* (init_metrics + _register helper, op_duration_seconds primitive)
provides:
  - localstock_db_pool_size (Gauge)
  - localstock_db_pool_checked_out (Gauge)
  - localstock_last_pipeline_age_seconds (Gauge)
  - localstock_last_crawl_success_count (Gauge)
  - localstock_scheduler_job_errors_total (Counter labels=job_id,error_type)
  - 30s health_self_probe APScheduler job
  - EVENT_JOB_ERROR listener with 15-min dedup + Telegram fire-and-forget
  - "@observe applied to PriceCrawler/FinanceCrawler/CompanyCrawler/EventCrawler.fetch + scheduler.daily_job"
affects:
  - apps/prometheus/src/localstock/observability/metrics.py
  - apps/prometheus/src/localstock/scheduler/scheduler.py
  - apps/prometheus/src/localstock/scheduler/health_probe.py
  - apps/prometheus/src/localstock/scheduler/error_listener.py
  - apps/prometheus/src/localstock/crawlers/{price,finance,company,event}_crawler.py
tech-stack:
  added: []
  patterns:
    - threading.Lock guards in-memory dedup cache (NOT asyncio.Lock — listener may fire from worker thread)
    - asyncio.create_task fire-and-forget with done-callback to suppress task exceptions
    - REGISTRY._names_to_collectors lookup keeps emission code defensive against init order
    - decorator preserves __wrapped__ + iscoroutinefunction for downstream introspection
key-files:
  created:
    - apps/prometheus/src/localstock/scheduler/health_probe.py
    - apps/prometheus/src/localstock/scheduler/error_listener.py
    - apps/prometheus/tests/test_scheduler/conftest.py
    - apps/prometheus/tests/test_scheduler/test_health_self_probe.py
    - apps/prometheus/tests/test_scheduler/test_error_listener.py
    - apps/prometheus/tests/test_observability/test_decorator_integration.py
  modified:
    - apps/prometheus/src/localstock/observability/metrics.py
    - apps/prometheus/src/localstock/scheduler/scheduler.py
    - apps/prometheus/src/localstock/crawlers/price_crawler.py
    - apps/prometheus/src/localstock/crawlers/finance_crawler.py
    - apps/prometheus/src/localstock/crawlers/company_crawler.py
    - apps/prometheus/src/localstock/crawlers/event_crawler.py
    - apps/prometheus/tests/test_observability/test_metrics.py
decisions:
  - "Dedup keyed by (job_id, error_type) — distinct error types not deduped together (D-06)"
  - "threading.Lock chosen over asyncio.Lock — listener may fire from APScheduler worker thread"
  - "Fire-and-forget Telegram via asyncio.create_task + done-callback for exception suppression"
  - "Self-probe writes via REGISTRY._names_to_collectors — symmetric with @observe lookup, no fragile module-global state"
  - "Defensive try/except per .set() call in health_probe — survives NullPool / non-QueuePool engines (Pitfall 6)"
  - "@observe('crawl.<subsystem>.fetch') applied to 4 crawler entry points only — matches CONTEXT D-01 minimal scope; do NOT decorate fetch_batch / BaseCrawler.fetch"
metrics:
  duration_minutes: 25
  completed: 2026-04-29
  tasks_total: 4
  tasks_complete: 4
  tests_added: 9
  test_suite_total: 516
---

# Phase 24 Plan 05: Self-Probe + Scheduler Errors + @observe Rollout — Summary

**One-liner:** Two new APScheduler hooks (30s self-probe Gauge populator + EVENT_JOB_ERROR listener with rate-limited Telegram alerts) + `@observe` applied to four crawler `fetch` entry points and the daily scheduler closure — adds 5 metric primitives, closes OBS-15/OBS-16, and produces ROADMAP SC-1's literal `domain=crawl,subsystem=ohlcv,action=fetch,outcome=success` label combination in `/metrics` after a real crawl.

## What Shipped

### 1. Five New Metric Primitives (`observability/metrics.py`)

Registered via the existing Phase 23 `_register` idempotent helper in the same file (no new metrics module — single-file contract per Phase 23 D-05):

| Name                                          | Kind    | Labels                        | Purpose                                            |
| --------------------------------------------- | ------- | ----------------------------- | -------------------------------------------------- |
| `localstock_db_pool_size`                     | Gauge   | —                             | SQLAlchemy pool capacity                           |
| `localstock_db_pool_checked_out`              | Gauge   | —                             | Pool connections currently in use                  |
| `localstock_last_pipeline_age_seconds`        | Gauge   | —                             | Seconds since last completed PipelineRun           |
| `localstock_last_crawl_success_count`         | Gauge   | —                             | symbols_success of latest PipelineRun              |
| `localstock_scheduler_job_errors_total`       | Counter | `job_id`, `error_type`        | EVENT_JOB_ERROR counter                            |

`tests/test_observability/test_metrics.py` `EXPECTED_FAMILIES` + `EXPECTED_LABELS` extended accordingly. All 4 budget invariants (no `symbol` label, namespace prefix, idempotency, frozen labels) remain green.

### 2. `scheduler/health_probe.py` (NEW, 70 LOC)

`async def health_self_probe()` — registered by `setup_scheduler()` with `IntervalTrigger(seconds=30), max_instances=1, coalesce=True`. Populates the 4 gauges above. Wrapped end-to-end in try/except — never raises. On any failure logs `health_probe_failed` at WARNING with structured kwargs. Uses `REGISTRY._names_to_collectors.get(name)` to look up gauges so production and test code share the same lookup path. Per-`.set()` try/except guards against `NullPool` / non-QueuePool engines (Pitfall 6).

### 3. `scheduler/error_listener.py` (NEW, 130 LOC)

`on_job_error(event)` — registered via `scheduler.add_listener(..., EVENT_JOB_ERROR)`. Pipeline:

1. **Counter:** `localstock_scheduler_job_errors_total{job_id, error_type}.inc()` — always.
2. **Log:** structured ERROR `scheduler_job_failed` with `traceback=` kwarg (no f-string per OBS-06).
3. **Telegram:** rate-limited via `_should_alert((job_id, error_type), now)`. The 15-minute window (`_DEDUP_WINDOW = timedelta(minutes=15)`) is enforced under a module-level `threading.Lock` (NOT `asyncio.Lock` — listener may fire from a worker thread on some APScheduler internals). On allowed alerts, dispatches `_send_telegram(...)` via `asyncio.get_running_loop().create_task(...)` with a done-callback that suppresses task exceptions to avoid `Task exception was never retrieved` warnings. Falls back to `asyncio.run(coro)` if no loop is running. **Distinct `(job_id, error_type)` keys are NOT deduped together.**

### 4. `@observe` Rollout to CONTEXT D-01 Initial Scope

| Site                                 | Decorator                                |
| ------------------------------------ | ---------------------------------------- |
| `PriceCrawler.fetch`                 | `@observe("crawl.ohlcv.fetch")`          |
| `FinanceCrawler.fetch`               | `@observe("crawl.financial.fetch")`      |
| `CompanyCrawler.fetch`               | `@observe("crawl.company.fetch")`        |
| `EventCrawler.fetch`                 | `@observe("crawl.event.fetch")`          |
| `daily_job` closure in `scheduler.py`| `@observe("scheduler.daily.run")`        |

`tests/test_observability/test_decorator_integration.py` adds two assertions:
- All four crawler `fetch` methods retain `__wrapped__` + `iscoroutinefunction` (24-01 D-01 invariant).
- `await PriceCrawler().fetch("VCB")` with a stubbed `vnstock.explorer.kbs.quote.Quote` actually drives the decorator wrapper — sample count for `localstock_op_duration_seconds_count{domain="crawl",subsystem="ohlcv",action="fetch",outcome="success"}` strictly increases. **This closes ROADMAP SC-1 at the literal label level** (previously satisfied only via 24-06's `pipeline.step.crawl` proxy).

## Tests

9 new tests (all passing). Full suite **516 passing** (508 baseline + 8 from this plan; one pre-existing test was retired by a prior plan — 6 unit + 1 integration + 2 wrapping-invariant new assertions account for the +8 swing through the test_metrics changes).

| Test File                                              | Count | Coverage                                                         |
| ------------------------------------------------------ | ----- | ---------------------------------------------------------------- |
| `test_scheduler/test_health_self_probe.py`             | 2     | OBS-15 — gauge population + failure swallow                      |
| `test_scheduler/test_error_listener.py`                | 4     | OBS-16 — counter inc, telegram once, dedup window, key isolation |
| `test_observability/test_decorator_integration.py`     | 2     | OBS-11 + ROADMAP SC-1 — wrapping invariants + literal label fire |
| `test_observability/test_metrics.py` (extended)        | —     | Phase 23 budget tests now cover 5 new primitives                 |

`bash apps/prometheus/scripts/lint-no-fstring-logs.sh` is clean.

## Commits

- **`001f31a`** `test(observability): RED tests for self-probe + scheduler errors (Phase 24-05)` — 6 ImportError-failing tests + test_metrics.py expectation update.
- **`fc448b8`** `feat(observability): self-probe gauges + scheduler error metric + Telegram alert dedup (Phase 24-05)` — metric primitives, `health_probe.py`, `error_listener.py`, scheduler wire-up.
- **`2e68b14`** `feat(crawlers,scheduler): apply @observe to entry points (Phase 24-05)` — 4 crawlers + daily_job decoration + integration test.

## D-08 Boundary — Phase 23 → Phase 24-05 Lift

> Phase 23 introduced D-08: "no `.inc()` / `.observe()` / `.set()` calls in `{services,crawlers,scheduler,api}/` IN PHASE 23". The prohibition was phase-scoped, not permanent — the deferred work landed here.
>
> Phase 24-05 introduces metric-emitting call sites inside the D-08 audit roots at three locations:
>
> | File | Call | Source |
> |---|---|---|
> | `scheduler/error_listener.py` | `scheduler_job_errors_total.labels(...).inc()` | Task 3 (OBS-16) |
> | `scheduler/health_probe.py`   | `db_pool_size.set(...)`, `db_pool_checked_out.set(...)`, `last_pipeline_age_seconds.set(...)`, `last_crawl_success_count.set(...)` | Task 3 (OBS-15) |
> | `scheduler/scheduler.py` (closure `daily_job`), `crawlers/{price,finance,company,event}_crawler.py` (`fetch`) | implicit `localstock_op_duration_seconds.labels(...).observe(...)` via `@observe(...)` decoration | Task 4 (CONTEXT D-01, ROADMAP SC-1) |
>
> These are the **intended Phase 24 implementation** of the Phase 23 D-08 deferred work. The boundary is lifted in this phase by design.
>
> **Lint impact:** zero. `scripts/lint-no-fstring-logs.sh` is regex-based for f-string log calls only and does not match `.inc()` / `.observe()` / `.set()`. No allowlist edit was required. **Manual D-08 grep:** matches WILL appear in `scheduler/error_listener.py`, `scheduler/health_probe.py`, and (via `@observe` indirection) `scheduler/scheduler.py` + `crawlers/{price,finance,company,event}_crawler.py`. **These matches are by design and must not be flagged as violations.**

(Block quoted verbatim from `24-05-PLAN.md` `<d8_audit>` to preserve the audit chain in version-controlled documentation.)

## Deviations from Plan

**None of substance.** Plan executed verbatim. Two minor pragmatic choices, both documented inline in the implementation:

1. **`logger.bind(...).error("scheduler_job_failed", traceback=...)`** instead of the RESEARCH §5 sketch's `error("scheduler_job_failed\n{tb}", tb=...)`. Rationale: keeps the message field a stable structured key (consumers can match on exact `message="scheduler_job_failed"`) and routes the traceback as a serialized extra rather than embedded in the message — better for the JSON sink and avoids any f-string-resembling pattern. Equivalent log payload, zero impact on assertions.
2. **Done-callback `_suppress_task_exception`** added to the fire-and-forget `loop.create_task(coro)` to prevent `Task exception was never retrieved` warnings if `_send_telegram` raises (e.g. transient network error). RESEARCH §5 hinted at the issue but did not provide the callback; this is the standard pattern. No behavior change to dedup or counter.

## Authentication Gates

None encountered.

## Self-Check: PASSED

- All created files exist (verified by tooling).
- All three commits present in git log: `001f31a`, `fc448b8`, `2e68b14`.
- Full suite 516/516 passing; lint clean; decorator integrity check `OK`.
