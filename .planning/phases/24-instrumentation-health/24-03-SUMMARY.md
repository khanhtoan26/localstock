---
phase: 24-instrumentation-health
plan: 03
subsystem: observability
tags: [sqlalchemy, event-listener, slow-query, OBS-12, OBS-13, TDD, prometheus, loguru]
status: complete
requirements_closed: [OBS-12, OBS-13]
dependency_graph:
  requires:
    - "Phase 23 metric primitives (db_query_duration_seconds, db_query_total)"
    - "Phase 24-01 (@observe + @timed_query — verified via existing test_decorators.py::test_timed_query_emits_op_metric)"
  provides:
    - "attach_query_listener(AsyncEngine) — idempotent, attached to sync_engine"
    - "_classify(stmt) -> (query_type, table_class)"
    - "localstock_db_query_slow_total{query_type, table_class} Counter"
    - "Settings.slow_query_threshold_ms (env: SLOW_QUERY_THRESHOLD_MS, default 250, range 1..10000)"
  affects:
    - "24-05 (call sites — slow query budget visible per query family)"
    - "24-06 (pipeline DB-step timings inherit listener observations)"
    - "Future Grafana dashboards — db_query_slow_total panel"
tech_stack:
  added: []
  patterns:
    - "AsyncEngine.sync_engine event hook (Pitfall 2 — direct AsyncEngine attach silently no-ops)"
    - "Idempotency sentinel (_localstock_query_listener_attached) on sync_engine"
    - "Late get_settings() import inside listener body — avoids config<->db cycle"
    - "REGISTRY._names_to_collectors dict lookup in listener — graceful when init_metrics() hasn't run on default registry"
    - "pydantic Field(default=250, ge=1, le=10000) for bounded numeric env"
    - "structured-kwargs loguru WARNING (no f-strings — passes lint-no-fstring-logs.sh)"
key_files:
  created:
    - apps/prometheus/src/localstock/observability/db_events.py
    - apps/prometheus/tests/test_observability/test_db_events.py
  modified:
    - apps/prometheus/src/localstock/observability/metrics.py
    - apps/prometheus/src/localstock/db/database.py
    - apps/prometheus/src/localstock/config.py
    - apps/prometheus/tests/test_observability/test_metrics.py
    - .env.example
decisions:
  - "Listener attached to engine.sync_engine, NOT AsyncEngine (RESEARCH §2 + Pitfall 2). Direct AsyncEngine attach silently no-ops because the DBAPI cursor cycle runs synchronously in a worker thread."
  - "Idempotent via sentinel attribute on sync_engine — repeated get_engine() in tests stays at one handler pair."
  - "Alembic skip implemented via 'alembic_version' substring check inside _after listener (defensive — Alembic engine is normally a different object, but test fixtures may share)."
  - "Slow-query branch reads threshold via late get_settings() import inside the handler — avoids a circular config<->db import at module-load time. Per-query lru_cache hit is negligible vs DB latency."
  - "Counter db_query_slow_total registered via the same _register helper as Phase 23 primitives, keeping single-file primitives invariant (D-05). EXPECTED_FAMILIES + EXPECTED_LABELS in test_metrics.py updated in lockstep."
  - "Settings.slow_query_threshold_ms uses pydantic Field(ge=1, le=10000) — fail-fast on SLOW_QUERY_THRESHOLD_MS=0 verified."
  - "Phase 24 LIFTS the D-08 boundary for observability/db_events.py (planner note). Audit roots {services, crawlers, scheduler, api}/ remain clean — verified by grep."
metrics:
  duration_minutes: ~20
  tasks: 3
  tests_added: 6                # functions
  test_cases_executed: 16       # 7+5 parametrize + 4 integration
  files_created: 2
  files_modified: 5
  completed: 2026-04-29
---

# Phase 24 Plan 03: DB Query Timing — SQLAlchemy Event Listener + Slow Query Log Summary

SQLAlchemy `before/after_cursor_execute` listeners attached to the AsyncEngine's `sync_engine` capture every query's duration into `localstock_db_query_duration_seconds{query_type, table_class}`, increment `localstock_db_query_total{...,outcome="success"}`, and emit a structured `slow_query` loguru WARNING + `localstock_db_query_slow_total` counter for any statement exceeding the new `Settings.slow_query_threshold_ms` (default 250 ms, env `SLOW_QUERY_THRESHOLD_MS`).

## What shipped

| Component | File | Notes |
|---|---|---|
| Event listener | `observability/db_events.py` (NEW, 117 LOC) | `attach_query_listener(engine)` + `_classify(stmt)` + `_get_collectors()`; idempotent; Alembic-skipped; slow-query branch |
| Counter primitive | `observability/metrics.py` | `db_query_slow_total` Counter via `_register` helper, slotted next to `db_query_total` |
| Wire-up | `db/database.py` | `attach_query_listener(_engine)` after `create_async_engine(...)` (late import) |
| Config | `config.py` | `slow_query_threshold_ms: int = Field(default=250, ge=1, le=10000)` |
| Env doc | `.env.example` (repo root) | `SLOW_QUERY_THRESHOLD_MS=250` block |
| Test | `tests/test_observability/test_db_events.py` (NEW, 250 LOC) | 6 test functions, 16 cases (parametrize) |
| Test budget | `test_metrics.py` | EXPECTED_FAMILIES + EXPECTED_LABELS updated for `db_query_slow_total` |

## Test results

- 12 unit cases pass: `test_query_type_classification` (7) + `test_table_class_classification` (5)
- 4 integration cases pass against the dev Supabase Postgres (~10.7 s):
  - `test_query_duration_observed_for_select` — histogram count increments for `SELECT 1`
  - `test_alembic_statements_skipped` — `SELECT 'alembic_version' AS marker` does NOT increment the histogram
  - `test_slow_query_emits_log_and_counter` — `pg_sleep(0.1)` with `SLOW_QUERY_THRESHOLD_MS=50` emits `slow_query` log + counter
  - `test_fast_query_does_not_trigger_slow_log` — `SELECT 1` with threshold=10000 emits no slow log
- Phase 23 `test_metrics.py` still green (7 passed) after EXPECTED_FAMILIES/LABELS update
- Full non-pg suite: **492 passed** in 22.4 s
- Full suite incl. requires_pg: **496 passed** (492 + 4 pg)
- `lint-no-fstring-logs.sh`: clean
- D-08 boundary grep on `services|crawlers|scheduler|api`: clean (single hit was a pre-existing `contextvar.set()`, not a metric)

## Atomic commits

| Phase | Hash | Message |
|---|---|---|
| RED | `f3a214a` | test(observability): RED tests for DB query event listener (Phase 24-03) |
| GREEN | `74856e2` | feat(observability): SQLAlchemy DB query timing + slow query log + counter (Phase 24-03) |
| INTEGRATION | `c0e1273` | test(observability): pg_sleep integration verified for slow_query (Phase 24-03) |

## Deviations from Plan

### [Rule 3 — Blocking] `apps/prometheus/.env.example` does not exist

- **Found during:** Task 2 Step E
- **Issue:** Plan instructed to append to `apps/prometheus/.env.example`. That file does not exist in the repo; the canonical example file lives at the repo root (`./.env.example`).
- **Fix:** Appended the `SLOW_QUERY_THRESHOLD_MS` block to the repo-root `.env.example` instead. This is consistent with how all existing env vars are documented for prod operators.
- **Files modified:** `.env.example` (repo root)
- **Commit:** `74856e2`

### [Rule 3 — Blocking] `_has_pg()` must consult Settings, not just os.environ

- **Found during:** Task 3 first run
- **Issue:** Initial gate `_has_pg()` only read `os.environ.get("DATABASE_URL")`. pytest does not auto-load `.env` into `os.environ`, so the gate skipped all 4 integration tests despite a Postgres URL being configured. Pydantic-settings reads `.env` directly into `Settings()` only.
- **Fix:** `_has_pg()` now falls back to `get_settings().database_url` when `os.environ` lacks the variable. With the fallback, all 4 `requires_pg` tests run and pass.
- **Files modified:** `tests/test_observability/test_db_events.py`
- **Commit:** `c0e1273`

### Notes on planner expectations

- The plan's Task 1 Step A says "register `requires_pg` marker if missing in pyproject.toml". The marker was already registered (pre-existing from Phase 24-04). Verified — no change needed; no `PytestUnknownMarkWarning` emitted.
- The plan's Task 3 acceptance allows skip-with-clear-reason when no Postgres available. Local dev had Postgres → all 4 pass; documented above.

## Threat Flags

None. The new file `observability/db_events.py` is an internal instrumentation surface — no network, no auth, no schema. The slow-query log truncates `statement_preview=statement[:120]` per ASVS V8 to bound any accidental data exposure in WARNING logs (no PII expected at the SQL-statement level — caller-supplied params are NOT logged).

## Acceptance closed

- **OBS-12** ✅ — listener captures duration with `(query_type, table_class)`; classification verified for SELECT/INSERT/UPDATE/DELETE/OTHER; hot-table heuristic verified for `stock_prices|stock_scores|pipeline_runs`; Alembic skip verified.
- **OBS-13** ✅ — slow-query log + `db_query_slow_total` counter for queries exceeding `slow_query_threshold_ms`; sub-threshold queries verified to NOT emit. Threshold env var validated (range 1..10000).

## Self-Check: PASSED

- File `apps/prometheus/src/localstock/observability/db_events.py` — FOUND
- File `apps/prometheus/tests/test_observability/test_db_events.py` — FOUND
- Commit `f3a214a` — FOUND
- Commit `74856e2` — FOUND
- Commit `c0e1273` — FOUND
