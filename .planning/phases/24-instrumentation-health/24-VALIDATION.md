# Phase 24 — VALIDATION (Nyquist contract)

Mapping each requirement to its observable test (Nyquist principle: every requirement has a test that would fail if the requirement is violated).

| Req ID | Requirement | Test file → test name | Type | Notes |
|---|---|---|---|---|
| **OBS-11** | `@observe` decorator: timing + log + Prometheus histogram | `tests/test_observability/test_decorators.py::test_observe_sync_success` | unit | Sync function returns value; histogram observed with `outcome="success"`; log `op_complete` emitted with `duration_ms` |
| **OBS-11** | (continued) | `test_decorators.py::test_observe_async_success` | unit | Async function awaited; histogram observed with `outcome="success"` |
| **OBS-11** | (continued) — exception path | `test_decorators.py::test_observe_sync_reraises_with_fail_outcome` | unit | Function raises → outcome=`fail`, `error_type` log field populated, exception re-raised |
| **OBS-11** | (continued) — exception path async | `test_decorators.py::test_observe_async_reraises_with_fail_outcome` | unit | Same as above for async |
| **OBS-11** | (continued) — naming validation | `test_decorators.py::test_observe_rejects_malformed_name` | unit | `@observe("foo")` (no dots) raises `ValueError` at import time |
| **OBS-11** | (continued) — call-site integration (ROADMAP SC-1 literal label) | `tests/test_observability/test_decorator_integration.py::test_crawl_fetch_emits_op_metric` | integration | After `await PriceCrawler().fetch(...)` (network stubbed), `localstock_op_duration_seconds_count{domain="crawl",subsystem="ohlcv",action="fetch",outcome="success"}` increases by ≥ 1 — proves `@observe` fires at the decorated call site (added by 24-05 Task 4 in revision; closes plan-check B-1) |
| **OBS-12** | SQLAlchemy event listener captures query duration | `tests/test_observability/test_db_events.py::test_query_duration_observed_for_select` | integration | Real async session executes `SELECT 1`; histogram `db_query_duration_seconds{query_type="SELECT", table_class="cold"}` observed |
| **OBS-12** | (continued) — INSERT/UPDATE/DELETE classification | `test_db_events.py::test_query_type_classification` | unit | Helper extracts SELECT/INSERT/UPDATE/DELETE/OTHER correctly |
| **OBS-12** | (continued) — table_class hot/cold | `test_db_events.py::test_table_class_classification` | unit | Hot tables (stock_prices, stock_scores, pipeline_runs) labeled `hot`; others `cold` |
| **OBS-12** | (continued) — Alembic skip | `test_db_events.py::test_alembic_statements_skipped` | unit | `alembic_version` queries do NOT increment metric |
| **OBS-12** | `@timed_query` decorator wraps repository methods | `test_decorators.py::test_timed_query_emits_op_metric` | unit | `@timed_query("upsert_prices")` wraps async fn; observes via `op_duration_seconds{domain="db"}` |
| **OBS-13** | Slow query log >threshold + counter | `test_db_events.py::test_slow_query_emits_log_and_counter` | integration | `monkeypatch.setenv("SLOW_QUERY_THRESHOLD_MS", "50")`; execute `SELECT pg_sleep(0.1)`; assert `slow_query` log line + `db_query_slow_total` counter > 0 |
| **OBS-13** | (continued) — fast queries do NOT trigger | `test_db_events.py::test_fast_query_does_not_trigger_slow_log` | integration | Sub-threshold query → no `slow_query` log, counter unchanged |
| **OBS-14** | `/health/live` always 200 | `tests/test_api/test_health_endpoints.py::test_health_live_returns_200` | integration | TestClient GET /health/live → 200 + `{"status": "alive"}` |
| **OBS-14** | `/health/ready` 503 if DB unhealthy | `test_health_endpoints.py::test_health_ready_503_when_db_ping_fails` | integration | Mock `session.execute` to raise `OperationalError`; assert 503 |
| **OBS-14** | `/health/ready` 200 with pool stats | `test_health_endpoints.py::test_health_ready_200_with_pool_stats` | integration | Healthy DB → 200, body contains `pool` dict with size/checkedin/checkedout/overflow |
| **OBS-14** | `/health/pipeline` returns last_pipeline_age | `test_health_endpoints.py::test_health_pipeline_returns_age_seconds` | integration | Insert PipelineRun row; assert `last_pipeline_age_seconds` present + numeric |
| **OBS-14** | `/health/data` returns max date + lag | `test_health_endpoints.py::test_health_data_returns_freshness` | integration | Insert StockPrice rows; assert `max_price_date` + `trading_days_lag` + `stale` boolean |
| **OBS-14** | `/health` deprecated alias | `test_health_endpoints.py::test_health_legacy_alias_has_deprecation_header` | integration | GET /health → 200 + header `X-Deprecated` set |
| **OBS-15** | `health_self_probe` populates 4 gauges | `tests/test_scheduler/test_health_self_probe.py::test_self_probe_populates_gauges` | unit | Invoke `health_self_probe()` directly with mocked engine + DB; assert all 4 gauges have non-default values |
| **OBS-15** | (continued) — failure handled gracefully | `test_health_self_probe.py::test_self_probe_logs_on_failure` | unit | DB query raises → log `health_probe_failed`, no exception propagates |
| **OBS-16** | Scheduler error → counter increments | `tests/test_scheduler/test_error_listener.py::test_job_error_increments_counter` | unit | Construct `JobExecutionEvent` with exception; invoke `_on_job_error`; assert `scheduler_job_errors_total{job_id, error_type}` incremented |
| **OBS-16** | Scheduler error → Telegram alert sent | `test_error_listener.py::test_job_error_sends_telegram_alert` | unit | First failure → mock Telegram client `send_alert` called once with formatted message |
| **OBS-16** | Rate-limit dedup within 15min | `test_error_listener.py::test_job_error_dedup_within_window` | unit | Trigger same `(job_id, error_type)` twice within 1 minute → counter increments TWICE, Telegram called ONCE |
| **OBS-16** | Different errors NOT deduped | `test_error_listener.py::test_different_error_types_not_deduped` | unit | Same job_id, different error_type → both Telegram alerts sent |
| **OBS-17** | PipelineRun has 4 `*_duration_ms` columns populated | `tests/test_services/test_pipeline_step_timing.py::test_pipeline_run_persists_step_durations` | integration | Run `Pipeline.run_full` with mocked steps that sleep briefly; assert PipelineRun row has crawl/analyze/score/report `_duration_ms` non-null + numeric |
| **OBS-17** | Step timer records duration even on exception | `test_pipeline_step_timing.py::test_step_timer_records_duration_on_exception` | unit | `async with _step_timer("crawl"): raise RuntimeError(...)` → `crawl_duration_ms` set on run, then exception re-raised |
| **OBS-17** | Migration applies/reverts cleanly | `tests/test_db/test_migration_24_pipeline_durations.py::test_migration_upgrade_adds_columns` | integration | Run migration, inspect schema, assert 4 columns exist as Integer NULL |
| **OBS-17** | (continued) — downgrade reverts | `test_migration_24_pipeline_durations.py::test_migration_downgrade_removes_columns` | integration | Downgrade, assert columns gone |

---

## Coverage table — Success Criteria → Test

| Roadmap Success Criterion | Tests covering it |
|---|---|
| 1. `@observe("crawl.ohlcv.fetch")` shows in /metrics + log with `duration_ms` | `test_observe_sync_success`, `test_observe_async_success`, **`test_crawl_fetch_emits_op_metric`** (integration: real `PriceCrawler.fetch` call produces literal `domain=crawl,subsystem=ohlcv,action=fetch` label per 24-05 Task 4) |
| 2. Slow query >250ms emits `slow_query` log + `db_query_slow_total` counter | `test_slow_query_emits_log_and_counter`, `test_fast_query_does_not_trigger_slow_log` |
| 3. `/health/live` 200 / `/health/ready` 503 if DB unhealthy / pipeline+data return freshness | `test_health_live_returns_200`, `test_health_ready_503_when_db_ping_fails`, `test_health_ready_200_with_pool_stats`, `test_health_pipeline_returns_age_seconds`, `test_health_data_returns_freshness` |
| 4. Scheduler job error → counter + Telegram alert | `test_job_error_increments_counter`, `test_job_error_sends_telegram_alert`, `test_job_error_dedup_within_window` |
| 5. PipelineRun has crawl/analyze/score/report `_duration_ms` populated | `test_pipeline_run_persists_step_durations`, `test_step_timer_records_duration_on_exception`, `test_migration_upgrade_adds_columns` |

---

## Sampling adequacy (Nyquist)

- 7 requirements × ≥2 tests each (most have 3-4) = **27 distinct tests** (well above 2× sampling)
- Mix of unit (decorators, listeners, classifiers) + integration (DB, HTTP, migrations)
- Negative tests included: malformed name rejection, fast-query non-trigger, DB unhealthy → 503, dedup window
- Failure-mode tests included: exception in `@observe` re-raised; step timer records on exception; self-probe DB failure logged not crashed

---

## Test infrastructure additions

- `mock_telegram_client` fixture (function-scoped, `monkeypatch.setattr` on telegram module)
- `metrics_registry` fixture from Phase 23 (already exists) — reused
- `pg_sleep` integration tests need real Postgres (per Open Q-4 in 24-RESEARCH.md) — planner must verify test DB availability and add `@pytest.mark.requires_pg` skip marker if not
- Migration tests use Alembic API: `alembic_runner.migrate_up_to(revision)` / `migrate_down_one()`

---

## Out of scope

- Per-query slow-query threshold override (CONTEXT D-02) — backlog
- Full Vietnamese trading calendar (CONTEXT D-03) — minimal static set, documented limitation
- `/health` alias removal — defer to v1.7
- `@observe` retroactive sweep across ALL service methods (Open Q-1) — minimal scope only this phase
- New metric primitive families beyond what CONTEXT lists — only ADD: `scheduler_job_errors_total` (Counter), `db_query_slow_total` (Counter), 4 self-probe gauges
