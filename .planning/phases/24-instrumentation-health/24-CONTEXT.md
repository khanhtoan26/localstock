# Phase 24 — Instrumentation & Health — CONTEXT

**Phase**: 24
**Goal** (from ROADMAP.md): Service methods, scheduler jobs, DB queries, và HTTP layer đều emit metrics + structured timing log; health endpoints tách thành 4 probe rõ ràng cho ops; scheduler errors không còn bị nuốt.
**Depends on**: Phase 23 (Metrics) — `@observe` decorator dùng `op_*` primitives, `@timed_query` dùng `db_query_*` primitives.
**Requirements**: OBS-11, OBS-12, OBS-13, OBS-14, OBS-15, OBS-16, OBS-17
**Discussion mode**: `--auto` (recommendations locked by agent, user delegated all 10 gray areas)

---

## Locked Decisions

### D-01: `@observe` decorator — sync+async dual API

**Decision**: Single `observe(name: str, *, log: bool = True)` factory với automatic sync/async detection via `inspect.iscoroutinefunction`. Returns appropriately-typed decorator.

```python
def observe(name: str, *, log: bool = True):
    """Time + log + emit Prometheus histogram for a function call.

    name = "domain.subsystem.action" (e.g., "crawl.ohlcv.fetch")
    Splits on first 2 dots → labels (domain, subsystem, action).
    Outcome label = "success" | "fail" (any exception → "fail" + re-raise).
    Logs op_complete (success) or op_failed (exception) at INFO with duration_ms.
    """
```

- **Histogram**: `localstock_op_duration_seconds{domain, subsystem, action, outcome}` (already declared in Phase 23 metrics.py)
- **Log fields**: `event=op_complete|op_failed`, `op_name=name`, `duration_ms=elapsed*1000`, `outcome=success|fail`, `error_type=type(exc).__name__` (only on fail)
- **Exception handling**: catch → mark outcome=fail → emit metric/log → **re-raise** (never swallow)
- **Naming convention**: enforce `domain.subsystem.action` (3 dot-separated tokens) via runtime validation in decorator factory; raise `ValueError` at import time if malformed
- **Files using it (initial scope)**: scheduler jobs (`scheduler/scheduler.py` job functions), pipeline step methods (`services/pipeline.py:run_full` step calls), key crawler entry points (`crawlers/*.py` top-level fetch functions). NOT every internal helper — focus on operations that take >100ms or cross I/O boundary.

**Rationale**: One decorator covers 80% of code; auto-detect avoids `@observe_async` vs `@observe_sync` confusion.

---

### D-02: Slow query threshold — env-configurable, default 250ms

**Decision**: Threshold via `Settings.slow_query_threshold_ms: int = 250` (Pydantic env: `SLOW_QUERY_THRESHOLD_MS`).

- Single global value (no per-query override in v1.5 — defer if needed in v1.6)
- Validation: must be > 0, capped at 10000 (sanity)
- Test fixture `monkeypatch.setenv("SLOW_QUERY_THRESHOLD_MS", "50")` for slow-query test (paired with `pg_sleep(0.1)`)

**Rationale**: 250ms is roadmap-locked; env override needed for tests + future ops tuning. Per-query override creates label cardinality issue.

---

### D-03: Health endpoints — 4 probes + `/health` as deprecated alias

**Decision**: Split `apps/prometheus/src/localstock/api/routes/health.py` into 4 endpoints under `/health/*`, keep `/health` as alias to `/health/ready` with deprecation header.

| Endpoint | Purpose | Returns | Status codes |
|---|---|---|---|
| `GET /health/live` | liveness — process up, no I/O | `{"status": "alive"}` | always 200 (unless app crashed) |
| `GET /health/ready` | readiness — DB pool reachable | `{"status": "ready", "db": "ok", "pool": {...}}` | 200 OK / 503 if DB ping fails or pool exhausted |
| `GET /health/pipeline` | pipeline freshness | `{"last_run_status", "last_pipeline_age_seconds", "started_at"}` | 200 always (informational) |
| `GET /health/data` | data freshness | `{"max_price_date", "trading_days_lag", "stale": bool}` | 200 always (informational; `stale=true` if lag > 1 trading day) |
| `GET /health` | DEPRECATED alias → identical body to `/health/ready` + header `X-Deprecated: use /health/ready` | mirror | mirror |

- `/health/ready` "DB unhealthy" detection: `await session.execute(text("SELECT 1"))` with 2s timeout via `asyncio.wait_for`. Pool stats from `engine.pool.size()`, `pool.checkedin()`, `pool.checkedout()`, `pool.overflow()`.
- `/health/data` trading-calendar: use `vnstock.trading_dates()` if available, else simple business-day check (Mon-Fri, exclude common Vietnamese holidays via small static list maintained by team — defer full calendar to backlog).
- `/health/data` lag computed as `(today - max(stock_prices.date)).business_days` — flag stale if > 1.
- All 4 probes are **read-only** (no DB writes).

**Rationale**: Splits per OBS-14. Keeping `/health` alias avoids breaking existing dashboards/scripts during migration window. Deprecation header signals removal in v1.7.

---

### D-04: `@timed_query` + SQLAlchemy events — both layers, async-only scope

**Decision**: Two complementary mechanisms:

1. **SQLAlchemy event listener** on the global async engine — `before_cursor_execute` + `after_cursor_execute` capture per-statement duration. Emits `localstock_db_query_duration_seconds{query_type, table_class}` histogram + `slow_query` log if >threshold.
   - `query_type` extracted from first SQL keyword (SELECT/INSERT/UPDATE/DELETE/OTHER)
   - `table_class` simple heuristic: "hot" if statement matches `stock_prices|stock_scores|pipeline_runs`, else "cold"
   - Registered ONCE in `db/database.py` after engine creation
2. **`@timed_query(name: str)` decorator** for service-level repository methods that wrap multiple statements (e.g., bulk upserts) — provides higher-level granularity. Optional, used only where event-level granularity is too low.
   - Implementation reuses `observe(f"db.query.{name}")` semantics

**Scope**:
- Async engine ONLY (project has no sync engine)
- Alembic migrations: SKIP — events would fire during DDL and pollute metrics. Conditional skip via `if context.get("compiled_cache") is None: return` heuristic OR (cleaner) only attach listener to runtime engine, not Alembic's.

**Rationale**: Event listener gives universal coverage for free; decorator gives semantic naming for hot paths. Async-only matches codebase reality.

---

### D-05: `health_self_probe` job — 30s interval, gauges in metrics.py

**Decision**: New APScheduler job `health_self_probe` runs every 30s (cron `*/30 * * * * *` style — APScheduler uses IntervalTrigger here). Populates 3 `Gauge` metrics:

- `localstock_db_pool_size` — current pool size (engine.pool.size())
- `localstock_db_pool_checked_out` — connections in use
- `localstock_last_pipeline_age_seconds` — time since last completed pipeline run
- `localstock_last_crawl_success_count` — last `PipelineRun.symbols_success`

**Where defined**: extend `observability/metrics.py` (per D-05 of Phase 23: single file). Add `# === Self-probe gauges ===` section.

**Where wired**: `scheduler/scheduler.py` `setup_scheduler()` adds the job AFTER pipeline jobs.

**Failure handling**: probe wraps body in try/except, logs `health_probe_failed` on error, continues silently (does NOT crash scheduler).

**Rationale**: 30s is fine-grained enough for ops dashboards without pool pressure. Co-locating gauges with other primitives keeps single source of truth.

---

### D-06: Scheduler error → counter + Telegram alert

**Decision**: Register `EVENT_JOB_ERROR` listener on APScheduler. Listener:

1. Increment `localstock_scheduler_job_errors_total{job_id, error_type}`
2. Send Telegram alert via existing `notifications/telegram.py` client — but with **rate limiting + dedup**:
   - **Rate limit**: max 1 alert per `(job_id, error_type)` per 15 minutes (in-memory `dict[tuple, datetime]` cache)
   - **Dedup**: identical `(job_id, error_type)` within window → counter still increments, alert suppressed
   - **Message format**: `🚨 Scheduler job failed\nJob: {job_id}\nError: {error_type}: {exception}\nTraceback: <code block, 500 chars max>`
   - Send **fire-and-forget** via `asyncio.create_task(...)` — listener doesn't block
3. Always log `scheduler_job_failed` at ERROR with full traceback

**Note**: `localstock_scheduler_job_errors_total` is a NEW metric (not in Phase 23's primitive list). Add to `metrics.py` under `# === Scheduler ===` new section.

**Rationale**: Counter for monitoring; Telegram for human attention. Rate limit prevents notification storms when same job fails on every retry. In-memory dedup is fine because scheduler errors are rare.

---

### D-07: PipelineRun migration — 4 nullable `*_duration_ms` columns

**Decision**: Alembic migration adds 4 `Integer` (NULL allowed) columns to `pipeline_runs` table:

```python
op.add_column("pipeline_runs", sa.Column("crawl_duration_ms", sa.Integer(), nullable=True))
op.add_column("pipeline_runs", sa.Column("analyze_duration_ms", sa.Integer(), nullable=True))
op.add_column("pipeline_runs", sa.Column("score_duration_ms", sa.Integer(), nullable=True))
op.add_column("pipeline_runs", sa.Column("report_duration_ms", sa.Integer(), nullable=True))
```

- Nullable=True for backward compat (old rows have NULL)
- No index needed (columns used for analysis, not WHERE clauses)
- Migration uses standard Alembic transactional DDL (no `CREATE INDEX CONCURRENTLY` needed)
- ORM `db/models.py` PipelineRun adds `Mapped[int | None]` columns

**Rationale**: Per OBS-17 verbatim. NULL-allowed avoids backfill requirement.

---

### D-08: Step timing capture — context manager wrapping each step

**Decision**: Add `_step_timer(step_name: str)` async context manager in `services/pipeline.py` that:
- Records `t_start = time.perf_counter()` on enter
- On exit (success or exception): `duration_ms = int((time.perf_counter() - t_start) * 1000)`; sets `setattr(run, f"{step_name}_duration_ms", duration_ms)`
- Wraps each of the 4 steps in `run_full()`: crawl/analyze/score/report

```python
async with self._step_timer("crawl"):
    await self._run_crawl_step(run)
```

- Doubles as `@observe("pipeline.step.crawl")` source — context manager calls `op_duration_seconds.labels(...).observe(elapsed)` internally
- On exception: still records duration before re-raising (so `*_duration_ms` reflects actual time spent before failure)

**Rationale**: Context manager is cleaner than 4× try/finally blocks. Captures duration even on partial failure.

---

### D-09: Test strategy — pg_sleep + fault injection + mock Telegram

**Decision**: Per requirement test approach:

| Requirement | Test approach |
|---|---|
| OBS-11 (`@observe`) | Unit test decorator: sync + async functions, success + exception paths; verify metric label set + log emitted |
| OBS-12 (`@timed_query` + events) | Integration test: spin up real async engine on test DB, execute `SELECT pg_sleep(0.05)`, assert histogram observed + `query_type=SELECT, table_class=cold` labels |
| OBS-13 (slow query) | Integration test: monkeypatch `SLOW_QUERY_THRESHOLD_MS=50`, run `SELECT pg_sleep(0.1)`, assert `slow_query` log + `db_query_slow_total` counter > 0 |
| OBS-14 (health endpoints) | Integration test for each of 4 probes via TestClient: live=200, ready=200 with DB up, pipeline returns last_pipeline_age, data returns max_date. Plus negative test: kill DB pool → ready=503 |
| OBS-15 (self-probe) | Unit test: invoke `health_self_probe()` directly, assert gauges populated |
| OBS-16 (scheduler error) | Unit test: register fault-injected job that raises, trigger via `scheduler.scheduler._run_job`, assert counter incremented + mocked Telegram client called once. Second trigger within 15min → counter increments, telegram NOT called |
| OBS-17 (PipelineRun timing) | Integration test: invoke `Pipeline.run_full()` with mocked steps, assert PipelineRun row has all 4 `*_duration_ms` populated |

**Test infrastructure**: Use existing `conftest.py` patterns from Phase 22/23. Add `mock_telegram_client` fixture. Use existing `metrics_registry` fixture for isolation.

**Rationale**: Fault injection beats trying to crash real jobs. `pg_sleep` is the standard slow-query test pattern.

---

### D-10: Plan splitting — 6 plans across 4 waves

**Decision**: Splitting strategy (planner has discretion to refine):

| Plan | Wave | Description | Depends on |
|---|---|---|---|
| 24-01 | 1 | `@observe` decorator + unit tests (no integration) | — |
| 24-02 | 1 | Alembic migration: 4 PipelineRun columns + ORM update | — |
| 24-03 | 2 | DB query timing (event listener + `@timed_query` decorator + slow query log) | 24-01 (`observe` semantics reused) |
| 24-04 | 2 | Health endpoints split (4 probes + `/health` alias) + integration tests | — |
| 24-05 | 3 | `health_self_probe` job + scheduler error listener + Telegram dedup | 24-01, 24-04 |
| 24-06 | 3 | Pipeline step timing wiring (context manager + apply to crawl/analyze/score/report) + integration test | 24-01, 24-02 |

**Wave 1 (parallel)**: 24-01 + 24-02 (no overlap, foundational)
**Wave 2 (parallel)**: 24-03 + 24-04 (no overlap)
**Wave 3 (parallel)**: 24-05 + 24-06 (no overlap, both depend on Wave 1+2)

**Estimated total**: ~700-900 LOC, 25-30 new tests.

**Rationale**: Maximizes parallelism while respecting dep chain. 6 plans is upper bound — planner may merge if scope is smaller than estimate.

---

## Requirements traceability

| Req ID | Description | Locked decision |
|---|---|---|
| OBS-11 | `@observe` decorator on services + scheduler | D-01 |
| OBS-12 | `@timed_query` + SQLAlchemy events for DB | D-04 |
| OBS-13 | Slow query log >250ms | D-02, D-04 |
| OBS-14 | Health endpoints split into 4 probes | D-03 |
| OBS-15 | `health_self_probe` job populates gauges | D-05 |
| OBS-16 | APScheduler error listener + Telegram alert | D-06 |
| OBS-17 | PipelineRun per-stage `*_duration_ms` columns | D-07, D-08 |

---

## Success Criteria (from ROADMAP)

1. `@observe("crawl.ohlcv.fetch")` shows in `/metrics` as `localstock_op_duration_seconds{...}` + emits `op_complete` log with `duration_ms` → covered by D-01 + Phase 23 primitives
2. Query >250ms emits `slow_query` log + `db_query_slow_total` counter — verified with `pg_sleep(0.3)` → covered by D-02, D-04
3. `/health/live` 200 always; `/health/ready` 503 if DB unhealthy; `/health/pipeline` returns age; `/health/data` returns freshness → covered by D-03
4. Scheduler job error → `scheduler_job_errors_total{job_id}` increments + Telegram alert (verified with fault-injected job) → covered by D-06
5. PipelineRun row has `crawl/analyze/score/report_duration_ms` populated → covered by D-07, D-08

---

## Out of scope (deferred)

- Per-query slow-query threshold override (D-02 noted) — backlog if needed in v1.6
- Full Vietnamese trading calendar (D-03) — minimal static list; defer full to backlog
- Removing deprecated `/health` alias (D-03) — defer to v1.7
- `@timed_query` for sync/Alembic context (D-04) — out of scope
- New metric primitives beyond Phase 23's 13 — only ADD `scheduler_job_errors_total` + 4 self-probe gauges + `db_query_slow_total` counter; no other new families

---

## Notes for downstream agents

- **Researcher**: Focus on (1) APScheduler `EVENT_JOB_ERROR` listener API + how to capture exception details from event object; (2) SQLAlchemy 2.0 async `event.listen(engine.sync_engine, "before_cursor_execute", ...)` pattern (note: events fire on sync engine even for async); (3) `inspect.iscoroutinefunction` + `functools.wraps` patterns for dual-mode decorator; (4) `asyncio.wait_for` timeout pattern for DB ping in `/health/ready`. Confirm versions: existing `apscheduler`, `sqlalchemy[asyncio]`, `python-telegram-bot`.
- **Planner**: 6 plans recommended (D-10). Each PLAN.md must declare its tests up-front (TDD-eligible: 24-01, 24-03, 24-04, 24-05). Migration plan 24-02 must include both `upgrade()` and `downgrade()` heads.
- **Plan-checker**: Specifically verify: (a) D-01 decorator handles BOTH sync and async; (b) D-04 listener attached to engine, not Alembic; (c) D-06 rate-limit logic has dedicated unit test; (d) D-07 migration is reversible; (e) D-08 context manager records duration even on exception; (f) Phase 23's `op_duration_seconds` IS the metric used by `@observe` (no duplicate creation).
