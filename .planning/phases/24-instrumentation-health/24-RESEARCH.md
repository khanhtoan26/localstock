# Phase 24: Instrumentation & Health — Research

**Researched:** 2026-04-29
**Domain:** Python observability — decorators, SQLAlchemy 2.0 async events, FastAPI health probes, APScheduler 3.x error handling
**Confidence:** HIGH (most patterns are codebase-grounded; APScheduler `EVENT_JOB_ERROR` and SQLAlchemy event-listener pattern verified against locally installed versions and existing code)

---

<user_constraints>
## User Constraints (from 24-CONTEXT.md)

### Locked Decisions
- **D-01** `@observe(name, *, log=True)` — single factory, sync+async via `inspect.iscoroutinefunction`. `name = "domain.subsystem.action"` (3 dot tokens, validated). Histogram = `localstock_op_duration_seconds{domain, subsystem, action, outcome}` (Phase 23 primitive). Exception → outcome=fail → emit metric/log → **re-raise**. Fields: `event=op_complete|op_failed`, `op_name`, `duration_ms`, `outcome`, `error_type`.
- **D-02** Slow-query threshold via `Settings.slow_query_threshold_ms: int = 250`, range 1..10000. Single global value, env override `SLOW_QUERY_THRESHOLD_MS`.
- **D-03** Health endpoints split into 4: `/health/live`, `/health/ready`, `/health/pipeline`, `/health/data`. `/health` becomes deprecated alias of `/health/ready` (adds `X-Deprecated` header). All read-only.
- **D-04** Two layers: SQLAlchemy `before_cursor_execute`/`after_cursor_execute` event listener + optional `@timed_query(name)` decorator (= `@observe(f"db.query.{name}")`). Async engine only. Skip Alembic engine.
- **D-05** `health_self_probe` APScheduler IntervalTrigger 30s populating 4 gauges (`db_pool_size`, `db_pool_checked_out`, `last_pipeline_age_seconds`, `last_crawl_success_count`). Try/except around body — never crash scheduler.
- **D-06** APScheduler `EVENT_JOB_ERROR` listener: increment `scheduler_job_errors_total{job_id, error_type}`, send Telegram alert with **15-min in-memory dedup** per `(job_id, error_type)`, fire-and-forget via `asyncio.create_task`. Always log ERROR with full traceback.
- **D-07** Alembic migration adds 4 nullable `Integer` columns to `pipeline_runs`: `crawl_duration_ms`, `analyze_duration_ms`, `score_duration_ms`, `report_duration_ms`. ORM updated with `Mapped[int | None]`. Reversible.
- **D-08** `_step_timer(step_name)` async context manager in `services/pipeline.py`. Uses `time.perf_counter()`. On `__aexit__`: set `setattr(run, f"{step_name}_duration_ms", duration_ms)` AND `op_duration_seconds.labels("pipeline", "step", step_name, outcome).observe(elapsed)`. Records duration even on exception, then re-raises.
- **D-09** Tests: pg_sleep for slow query, fault-injected scheduler job, mock Telegram client, mocked-step pipeline run, decorator unit tests for sync+async × success+fail.
- **D-10** 6 plans across 3 waves: W1 = 24-01 (`@observe`) + 24-02 (migration); W2 = 24-03 (DB events) + 24-04 (health split); W3 = 24-05 (self-probe + scheduler errors) + 24-06 (pipeline step timing).

### the agent's Discretion
- Filename for `@observe` (recommend `observability/decorators.py` to keep `metrics.py` primitives-only).
- Exact regex for `table_class` heuristic.
- Choice of `dict + asyncio.Lock` vs `dict + threading.Lock` for Telegram dedup (recommend `asyncio.Lock` because `AsyncIOScheduler` runs listeners in the asyncio loop).
- Static Vietnamese-holiday list scope for `/health/data` (recommend small `_VN_HOLIDAYS_2025_2026` set; document as known-limitation).
- Whether to apply `@observe` retroactively to all services (recommend NO — apply only to scheduler jobs + 4 pipeline steps + 1-2 crawler entry points; full sweep deferred to Phase 25 hygiene).

### Deferred Ideas (OUT OF SCOPE)
- Per-query slow-query override.
- Full Vietnamese trading calendar (use minimal static list).
- Removing deprecated `/health` alias (defer to v1.7).
- `@timed_query` for sync/Alembic context.
- New metric primitives beyond: `scheduler_job_errors_total`, 4 self-probe gauges, `db_query_slow_total` counter.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBS-11 | `@observe("domain.subsystem.action")` decorator on services + scheduler jobs | §1 `@observe` Decorator Code |
| OBS-12 | `@timed_query` + SQLAlchemy `before/after_cursor_execute` events | §2 DB Event Listener Code |
| OBS-13 | Slow-query log + counter when query > 250 ms | §2 (slow-query branch) + §9 Config |
| OBS-14 | Split `/health` into `/health/{live,ready,pipeline,data}` | §3 Health Probes Code |
| OBS-15 | `health_self_probe` 30s job populating 4 gauges | §4 Self-Probe Job Code |
| OBS-16 | APScheduler EVENT_JOB_ERROR → counter + Telegram alert | §5 Scheduler Error Listener |
| OBS-17 | `PipelineRun.{crawl,analyze,score,report}_duration_ms` populated each run | §6 Step Timer + §7 Migration |
</phase_requirements>

---

## Summary

Phase 24 turns the Phase 23 metric primitives into actual signal. Six interlocking pieces:

1. A `@observe` decorator that's the only API services/scheduler use to emit `op_duration_seconds` + `op_complete`/`op_failed` logs.
2. A SQLAlchemy event listener attached to the async engine's `sync_engine` capturing every statement's wall time, classifying it (`SELECT`/`INSERT`/…, `hot`/`cold` table), and tripping a slow-query log+counter at >250 ms.
3. Four health endpoints that split liveness, readiness, pipeline freshness, data freshness — backwards-compat alias on `/health`.
4. A 30-second self-probe job populating pool / pipeline-age / crawl-success gauges so dashboards have live values without instrumenting every codepath.
5. A scheduler error listener that captures unhandled job exceptions, increments `scheduler_job_errors_total`, and fires a rate-limited Telegram alert (15-min dedup per `(job_id, error_type)`).
6. Per-step timing on `Pipeline.run_full` recorded both as Prometheus observations and as four new `*_duration_ms` columns on `pipeline_runs`.

**Primary recommendation:** Land the `@observe` decorator first (24-01) and the Alembic migration second (24-02) — every other plan reuses one or the other. Co-locate the 6 new metric primitives with the existing 13 in `observability/metrics.py` so there's still a single source of truth.

**Estimated total:** ~750 LOC implementation + ~450 LOC tests across 6 plans, ~25-28 new tests.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| `@observe` decorator (timing + log + histogram) | observability/ | services, scheduler, crawlers (call sites) | Centralizes metric+log emission; primitives stay in `metrics.py` |
| DB event listener / `@timed_query` | db/ (registration) | observability/ (metric, decorator helper) | Engine creation is the only place to attach listeners once |
| Slow-query log emission | observability/ (log call) | db/ (event handler) | Consistent log channel; no f-string per Phase 22 OBS-06 |
| Health probes | api/routes/ | db/, scheduler/ (read-only queries) | HTTP boundary; routers stay thin |
| Self-probe job | scheduler/ (registration) | observability/ (gauge handles), db/ (pool stats) | Job runs on `AsyncIOScheduler`; reads engine.pool + PipelineRun |
| Scheduler error listener | scheduler/ | notifications/ (Telegram), observability/ (counter) | Lifecycle hook lives next to scheduler; reuses notifier |
| Step timer | services/pipeline.py | observability/ (op histogram) | Context manager is local to pipeline; persists durations to its own row |
| `*_duration_ms` columns | db/models.py + alembic/ | services/pipeline.py | DDL + ORM only at db tier; pipeline writes the values |

---

## Standard Stack

### Verified (already in `apps/prometheus/pyproject.toml`)

| Library | Pin | Resolved | Purpose |
|---|---|---|---|
| `apscheduler` | `>=3.11,<4.0` | 3.11.x | `AsyncIOScheduler`, `EVENT_JOB_ERROR`, `JobExecutionEvent`, `IntervalTrigger` [VERIFIED: pyproject.toml] |
| `sqlalchemy[asyncio]` | `>=2.0,<3.0` | 2.x | `event.listen(engine.sync_engine, "before_cursor_execute", …)` [VERIFIED: pyproject.toml + db/database.py uses `create_async_engine`] |
| `prometheus-client` | `>=0.21,<1.0` | 0.25.0 | `Counter`, `Gauge`, `Histogram` [VERIFIED: 23-01 SUMMARY] |
| `prometheus-fastapi-instrumentator` | `>=7.1,<8.0` | 7.1.0 | Default HTTP histogram (already wired Phase 23-02) |
| `python-telegram-bot` | `>=22.0,<23.0` | 22.x | `notifications/telegram.py` `TelegramNotifier.send_message()` (existing) [VERIFIED: notifications/telegram.py] |
| `loguru` | (transitive) | — | `logger.info(..., key=val)` structured kwargs (Phase 22 idiom) [VERIFIED: observability/logging.py] |
| `pydantic-settings` | (transitive) | — | `Settings.slow_query_threshold_ms` field [VERIFIED: config.py] |

**Nothing new is added** in Phase 24. All deps are already installed.

### Standard library only

| Module | Used For |
|---|---|
| `inspect.iscoroutinefunction` | `@observe` sync/async branching [CITED: docs.python.org/3/library/inspect.html#inspect.iscoroutinefunction — stable since 3.8] |
| `functools.wraps` | Preserve wrapped function metadata |
| `time.perf_counter()` | Monotonic, sub-microsecond resolution wall time |
| `asyncio.wait_for(coro, timeout)` | 2-second DB ping bound in `/health/ready` |
| `asyncio.Lock` | Mutex around Telegram dedup cache |
| `asyncio.create_task` / `asyncio.run_coroutine_threadsafe` | Fire-and-forget Telegram dispatch from EVENT_JOB_ERROR handler |
| `re` | Statement classification regex (`SELECT|INSERT|UPDATE|DELETE`, hot-table match) |
| `threading.Lock` | (Fallback only — see §5 Open Question on listener thread context) |

---

## File Touch List by Plan (D-10)

| Plan | New | Modified | Tests | Est. LOC |
|---|---|---|---|---|
| **24-01** `@observe` | `observability/decorators.py` (~110) | `observability/__init__.py` (+2) | `test_observability/test_observe_decorator.py` (~140, 6 tests) | ~250 |
| **24-02** migration | `alembic/versions/24a_pipeline_run_durations.py` (~50) | `db/models.py` (+4 lines) | `test_db/test_pipelinerun_columns.py` (~30, 1 test) | ~85 |
| **24-03** DB timing | `observability/db_events.py` (~120) | `db/database.py` (+5: register call), `observability/decorators.py` (+15: `timed_query`), `config.py` (+1: `slow_query_threshold_ms`), `metrics.py` (+10: `db_query_slow_total`), `.env.example` (+2) | `test_observability/test_db_events.py` (~120, 4 tests) | ~280 |
| **24-04** health split | `api/routes/health.py` rewrite (~140) | `api/app.py` (router still mounted; verify) | `test_api/test_health_endpoints.py` (~150, 6 tests) | ~290 |
| **24-05** self-probe + sched errors | `scheduler/error_listener.py` (~110), `scheduler/health_probe.py` (~70) | `scheduler/scheduler.py` (+15: register job + listener), `metrics.py` (+30: 4 gauges + 1 counter) | `test_scheduler/test_error_listener.py` (~110, 4 tests), `test_scheduler/test_health_probe.py` (~80, 2 tests) | ~415 |
| **24-06** step timing | — | `services/pipeline.py` (+30: `_step_timer` + 4 wrap sites) | `test_services/test_pipeline_timing.py` (~110, 2 tests) | ~140 |

**Grand total:** ~1460 LOC inclusive of tests; ~750 implementation. Mostly within initial estimate (700-900 impl).

---

## §1. `@observe` Decorator Code

**File:** `apps/prometheus/src/localstock/observability/decorators.py` (NEW)

```python
"""Phase 24 — @observe decorator (D-01, OBS-11).

Wraps a function/coroutine with timing + structured log + Prometheus
histogram emission against the Phase 23 op_duration_seconds primitive.

Naming convention enforced at decoration time: ``name`` MUST be of the form
``domain.subsystem.action`` (3 dot-separated tokens). Malformed names raise
``ValueError`` at import time, never silently at call time.
"""
from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from loguru import logger
from prometheus_client import REGISTRY

P = ParamSpec("P")
R = TypeVar("R")


def _split_name(name: str) -> tuple[str, str, str]:
    """Validate ``name`` and split into (domain, subsystem, action)."""
    parts = name.split(".")
    if len(parts) != 3 or not all(p for p in parts):
        raise ValueError(
            f"@observe name must be 'domain.subsystem.action' (3 non-empty tokens); "
            f"got {name!r}"
        )
    return parts[0], parts[1], parts[2]


def _get_op_histogram():
    """Lazy lookup of the Phase 23 primitive on the default registry.

    Looked up lazily so tests can swap the registry (or rely on the
    metrics_registry fixture re-init pattern from 23-01)."""
    coll = REGISTRY._names_to_collectors.get("localstock_op_duration_seconds")
    if coll is None:
        # Defensive: init_metrics() should have run at import. Re-init.
        from localstock.observability.metrics import init_metrics
        return init_metrics()["op_duration_seconds"]
    return coll


def observe(name: str, *, log: bool = True) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Time + log + emit histogram for the wrapped function.

    Args:
        name: ``"domain.subsystem.action"`` — split into 3 histogram labels.
        log: Whether to emit ``op_complete`` / ``op_failed`` log line.

    Behaviour:
        - Detects coroutine functions via ``inspect.iscoroutinefunction``;
          returns an async or sync wrapper accordingly.
        - On exception: marks outcome=fail, emits metric+log, **re-raises**.
        - Fields logged: ``event``, ``op_name``, ``duration_ms``, ``outcome``,
          and ``error_type`` (only on fail).
    """
    domain, subsystem, action = _split_name(name)  # validate at import time

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:
            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                hist = _get_op_histogram()
                t0 = time.perf_counter()
                outcome = "success"
                try:
                    return await fn(*args, **kwargs)  # type: ignore[misc]
                except Exception as exc:
                    outcome = "fail"
                    elapsed = time.perf_counter() - t0
                    hist.labels(domain, subsystem, action, outcome).observe(elapsed)
                    if log:
                        logger.opt(exception=False).error(
                            "op_failed",
                            op_name=name,
                            duration_ms=int(elapsed * 1000),
                            outcome=outcome,
                            error_type=type(exc).__name__,
                        )
                    raise  # re-raise — never swallow (D-01)
                else:
                    elapsed = time.perf_counter() - t0
                    hist.labels(domain, subsystem, action, outcome).observe(elapsed)
                    if log:
                        logger.info(
                            "op_complete",
                            op_name=name,
                            duration_ms=int(elapsed * 1000),
                            outcome=outcome,
                        )
            return async_wrapper  # type: ignore[return-value]

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            hist = _get_op_histogram()
            t0 = time.perf_counter()
            outcome = "success"
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                outcome = "fail"
                elapsed = time.perf_counter() - t0
                hist.labels(domain, subsystem, action, outcome).observe(elapsed)
                if log:
                    logger.error(
                        "op_failed",
                        op_name=name,
                        duration_ms=int(elapsed * 1000),
                        outcome=outcome,
                        error_type=type(exc).__name__,
                    )
                raise
            else:
                elapsed = time.perf_counter() - t0
                hist.labels(domain, subsystem, action, outcome).observe(elapsed)
                if log:
                    logger.info(
                        "op_complete",
                        op_name=name,
                        duration_ms=int(elapsed * 1000),
                        outcome=outcome,
                    )
        return sync_wrapper

    return decorator


def timed_query(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Repository-level helper — alias for ``observe(f"db.query.{name}")``.

    Use on service methods that wrap multiple SQL statements (bulk upserts,
    transactional batches) where event-level timing is too low-grain.
    """
    return observe(f"db.query.{name}")
```

**Re-export** in `observability/__init__.py`:

```python
from localstock.observability.decorators import observe, timed_query
__all__ = [..., "observe", "timed_query"]
```

**Why a separate module:** keeps `metrics.py` primitive-only per Phase 23 D-05. The Phase 23 verification grep for `\.(inc|observe|set)\(` in `services/crawlers/scheduler/api/` will start to flag legitimate hits in Phase 24 — but those hits will be inside `decorators.py`'s wrappers, not direct call sites. Update the grep allowlist accordingly during 24-01 verification.

**Confidence:** HIGH. `inspect.iscoroutinefunction` + `functools.wraps` is the canonical Python pattern; identical to e.g. `tenacity.retry`. ParamSpec/TypeVar typing is Python 3.10+ stable.

---

## §2. SQLAlchemy DB Event Listener Code

**File:** `apps/prometheus/src/localstock/observability/db_events.py` (NEW)

```python
"""Phase 24 — SQLAlchemy 2.0 async-engine query timing (D-04, OBS-12, OBS-13).

Attaches ``before_cursor_execute`` / ``after_cursor_execute`` listeners to the
sync_engine of an AsyncEngine. These events fire for every statement the async
engine dispatches — including ones in repository methods, ORM lazy loads, and
manual ``session.execute(text(...))`` calls.

Out of scope: Alembic migrations (DDL pollutes the histogram). The runtime
async engine and Alembic's offline engine are different objects, so simply
attaching here (called from get_engine()) leaves Alembic alone.
"""
from __future__ import annotations

import re
import time
from typing import Any

from loguru import logger
from prometheus_client import REGISTRY
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

# === Hot-table heuristic (D-04) ===
_HOT_TABLE_RE = re.compile(
    r"\b(stock_prices|stock_scores|pipeline_runs)\b", re.IGNORECASE
)
# === Query-type extraction ===
_QTYPE_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


def _classify(statement: str) -> tuple[str, str]:
    """Return (query_type, table_class)."""
    m = _QTYPE_RE.match(statement)
    qtype = m.group(1).upper() if m else "OTHER"
    tclass = "hot" if _HOT_TABLE_RE.search(statement) else "cold"
    return qtype, tclass


def _get_collectors() -> dict[str, Any]:
    """Look up the Phase 23 primitives + the new db_query_slow_total counter."""
    n2c = REGISTRY._names_to_collectors
    return {
        "duration": n2c.get("localstock_db_query_duration_seconds"),
        "total": n2c.get("localstock_db_query_total"),
        "slow": n2c.get("localstock_db_query_slow_total"),
    }


def attach_query_listener(engine: AsyncEngine) -> None:
    """Attach before/after cursor_execute listeners to the engine.

    Idempotent: if the engine already has these listeners attached
    (`engine.sync_engine.dispatch.before_cursor_execute` non-empty for our
    callable), skip.
    """
    sync_engine = engine.sync_engine

    # Idempotency guard — useful when get_engine() is called repeatedly in tests.
    if getattr(sync_engine, "_localstock_query_listener_attached", False):
        return
    sync_engine._localstock_query_listener_attached = True

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        # Stash on context per SQLAlchemy convention. ``context`` is an
        # ExecutionContext per DBAPI cursor execution.
        context._localstock_t0 = time.perf_counter()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        t0 = getattr(context, "_localstock_t0", None)
        if t0 is None:
            return
        elapsed = time.perf_counter() - t0
        duration_ms = int(elapsed * 1000)

        # Skip Alembic-internal version probes (defensive — Alembic engine
        # SHOULD be a different engine, but guard anyway in case a test
        # accidentally runs DDL on the runtime engine).
        if "alembic_version" in statement:
            return

        qtype, tclass = _classify(statement)
        c = _get_collectors()
        if c["duration"] is not None:
            c["duration"].labels(qtype, tclass).observe(elapsed)
        if c["total"] is not None:
            c["total"].labels(qtype, tclass, "success").inc()

        # Slow query branch (OBS-13)
        from localstock.config import get_settings  # late import — avoids cycle
        threshold_ms = get_settings().slow_query_threshold_ms
        if duration_ms > threshold_ms:
            if c["slow"] is not None:
                c["slow"].labels(qtype, tclass).inc()
            logger.warning(
                "slow_query",
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                query_type=qtype,
                table_class=tclass,
                statement_preview=statement[:120],  # bounded — no PII at SQL level
            )
```

**Wire-up in `db/database.py`:**

```python
def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=3, max_overflow=5,
            pool_recycle=300, pool_pre_ping=True,
            connect_args={"prepared_statement_cache_size": 0,
                          "statement_cache_size": 0},
        )
        # NEW (Phase 24-03):
        from localstock.observability.db_events import attach_query_listener
        attach_query_listener(_engine)
    return _engine
```

**New metric to add to `observability/metrics.py`** (Plan 24-03):

```python
# === Slow query counter (Phase 24, D-04, OBS-13) ===
metrics["db_query_slow_total"] = _register(
    lambda: Counter(
        "localstock_db_query_slow_total",
        "Queries exceeding slow_query_threshold_ms.",
        labelnames=("query_type", "table_class"),
        registry=target,
    ),
    "localstock_db_query_slow_total",
)
```

**Important SQLAlchemy 2.0 async note:** `event.listen(async_engine, "before_cursor_execute", ...)` does NOT work — it must be attached to `engine.sync_engine`. Events fire on the synchronous engine even when the application uses `AsyncEngine` because the DBAPI cursor cycle itself is synchronous; the async wrapper just runs it in a worker thread. [CITED: SQLAlchemy 2.0 docs — "Asyncio Integration" → "Synchronous-style API" + see existing repo `db/database.py` for AsyncEngine usage.]

**Confidence:** HIGH for the event mechanics, MEDIUM for the slow-query threshold call placement (late `get_settings()` import inside the handler is a tiny per-query cost; if measurements show it's hot, hoist to module-level after `Settings` is finalised).

---

## §3. Health Probes Code (4 endpoints + alias)

**File:** `apps/prometheus/src/localstock/api/routes/health.py` (REWRITE)

```python
"""Phase 24 — Health probes (D-03, OBS-14).

4 endpoints + 1 deprecated alias:
  /health/live      always 200 unless process is crashing — no I/O
  /health/ready     200 on DB ping success, 503 on timeout/OperationalError
  /health/pipeline  pipeline freshness (informational, always 200)
  /health/data      data freshness vs trading calendar (informational, 200)
  /health           DEPRECATED alias of /health/ready (X-Deprecated header)
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_engine, get_session
from localstock.db.models import PipelineRun, StockPrice

router = APIRouter()

# Minimal static VN holiday list (D-03; full calendar deferred — see Open Q-2)
_VN_HOLIDAYS_2025_2026: frozenset[date] = frozenset({
    date(2025, 1, 1), date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
    date(2025, 1, 31), date(2025, 2, 3), date(2025, 4, 7), date(2025, 4, 30),
    date(2025, 5, 1), date(2025, 9, 2),
    date(2026, 1, 1), date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 4, 27), date(2026, 4, 30),
    date(2026, 5, 1), date(2026, 9, 2),
})


def _is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _VN_HOLIDAYS_2025_2026


def _trading_days_lag(latest: date, today: date) -> int:
    """Count business days between latest+1 and today inclusive (excl. holidays)."""
    if latest >= today:
        return 0
    lag = 0
    cur = latest + timedelta(days=1)
    while cur <= today:
        if _is_trading_day(cur):
            lag += 1
        cur += timedelta(days=1)
    return lag


# === /health/live — process up, no I/O ===
@router.get("/health/live")
async def health_live() -> dict:
    return {"status": "alive"}


# === /health/ready — DB pool reachable ===
async def _ready_payload(session: AsyncSession) -> tuple[int, dict]:
    engine = get_engine()
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2.0)
    except (TimeoutError, asyncio.TimeoutError, OperationalError, SQLAlchemyError) as exc:
        return status.HTTP_503_SERVICE_UNAVAILABLE, {
            "status": "not_ready",
            "db": "down",
            "error_type": type(exc).__name__,
        }
    pool = engine.pool
    return status.HTTP_200_OK, {
        "status": "ready",
        "db": "ok",
        "pool": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
    }


@router.get("/health/ready")
async def health_ready(
    response: Response, session: AsyncSession = Depends(get_session)
) -> dict:
    code, body = await _ready_payload(session)
    response.status_code = code
    return body


# === /health/pipeline — last completed pipeline freshness ===
@router.get("/health/pipeline")
async def health_pipeline(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None or run.completed_at is None:
        return {
            "last_run_status": None,
            "last_pipeline_age_seconds": None,
            "started_at": None,
            "completed_at": None,
        }
    age = (datetime.now(UTC) - run.completed_at).total_seconds()
    return {
        "last_run_status": run.status,
        "last_pipeline_age_seconds": int(age),
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat(),
    }


# === /health/data — MAX(stock_prices.date) vs trading calendar ===
@router.get("/health/data")
async def health_data(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(func.max(StockPrice.date)))
    max_date: date | None = result.scalar_one_or_none()
    today = date.today()
    if max_date is None:
        return {"max_price_date": None, "trading_days_lag": None, "stale": True}
    lag = _trading_days_lag(max_date, today)
    return {
        "max_price_date": max_date.isoformat(),
        "trading_days_lag": lag,
        "stale": lag > 1,
    }


# === /health — DEPRECATED alias → /health/ready ===
@router.get("/health")
async def health_deprecated(
    response: Response, session: AsyncSession = Depends(get_session)
) -> dict:
    code, body = await _ready_payload(session)
    response.status_code = code
    response.headers["X-Deprecated"] = "use /health/ready instead"
    return body
```

**Notes:**
- `Instrumentator` already excludes `^/health/live$` per Phase 23-02 SUMMARY — no change needed there. The other 3 probes WILL get HTTP histogram observations, which is desirable (visible in `/metrics`).
- The deprecated `/health` is intentionally NOT excluded — it should also show up so dashboards can detect callers still using the old path.

**Confidence:** HIGH — uses existing `get_engine()` pool API + standard FastAPI patterns identical to current `health.py`.

---

## §4. `health_self_probe` Job Code

**New gauges to add to `observability/metrics.py`** (Plan 24-05):

```python
# === Self-probe gauges (Phase 24, D-05, OBS-15) ===
metrics["db_pool_size"] = _register(
    lambda: Gauge(
        "localstock_db_pool_size",
        "Current SQLAlchemy connection pool size.",
        registry=target,
    ),
    "localstock_db_pool_size",
)
metrics["db_pool_checked_out"] = _register(
    lambda: Gauge(
        "localstock_db_pool_checked_out",
        "Connections currently checked out of the pool.",
        registry=target,
    ),
    "localstock_db_pool_checked_out",
)
metrics["last_pipeline_age_seconds"] = _register(
    lambda: Gauge(
        "localstock_last_pipeline_age_seconds",
        "Seconds since the last completed pipeline run.",
        registry=target,
    ),
    "localstock_last_pipeline_age_seconds",
)
metrics["last_crawl_success_count"] = _register(
    lambda: Gauge(
        "localstock_last_crawl_success_count",
        "symbols_success of the most recent PipelineRun.",
        registry=target,
    ),
    "localstock_last_crawl_success_count",
)
```

**File:** `apps/prometheus/src/localstock/scheduler/health_probe.py` (NEW)

```python
"""Phase 24 — health_self_probe APScheduler job (D-05, OBS-15)."""
from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from prometheus_client import REGISTRY
from sqlalchemy import select


async def health_self_probe() -> None:
    """Populate self-probe gauges every 30 s. Never raises."""
    try:
        from localstock.db.database import get_engine, get_session_factory
        from localstock.db.models import PipelineRun

        n2c = REGISTRY._names_to_collectors
        pool_size = n2c.get("localstock_db_pool_size")
        pool_co = n2c.get("localstock_db_pool_checked_out")
        age = n2c.get("localstock_last_pipeline_age_seconds")
        last_ok = n2c.get("localstock_last_crawl_success_count")

        # Pool stats (sync — no DB round-trip)
        engine = get_engine()
        pool = engine.pool
        if pool_size is not None:
            pool_size.set(pool.size())
        if pool_co is not None:
            pool_co.set(pool.checkedout())

        # Latest completed run (single round-trip)
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(PipelineRun)
                .where(PipelineRun.status == "completed")
                .order_by(PipelineRun.completed_at.desc())
                .limit(1)
            )
            run = result.scalar_one_or_none()
            if run is not None and run.completed_at is not None:
                if age is not None:
                    age.set((datetime.now(UTC) - run.completed_at).total_seconds())
                if last_ok is not None:
                    last_ok.set(run.symbols_success or 0)
    except Exception as exc:
        logger.warning("health_probe_failed", error_type=type(exc).__name__,
                       error=str(exc))
```

**Wire-up in `scheduler/scheduler.py`** (inside `setup_scheduler()`, AFTER admin job worker):

```python
from apscheduler.triggers.interval import IntervalTrigger
from localstock.scheduler.health_probe import health_self_probe

scheduler.add_job(
    health_self_probe,
    trigger=IntervalTrigger(seconds=30),
    id="health_self_probe",
    name="Self-probe gauges",
    replace_existing=True,
    max_instances=1,        # never overlap
    coalesce=True,          # collapse misfires
)
```

**Confidence:** HIGH for `engine.pool.size() / .checkedout()` — these are standard SQLAlchemy QueuePool methods. MEDIUM for the assumption that pool is `QueuePool` (default for `create_async_engine` against PostgreSQL); if tests later use `NullPool`, `pool.size()` raises — defensive try/except already covers this.

---

## §5. Scheduler Error Listener Code

**New metric** to add to `observability/metrics.py`:

```python
# === Scheduler (Phase 24, D-06, OBS-16) ===
metrics["scheduler_job_errors_total"] = _register(
    lambda: Counter(
        "localstock_scheduler_job_errors_total",
        "Unhandled exceptions raised by APScheduler jobs.",
        labelnames=("job_id", "error_type"),
        registry=target,
    ),
    "localstock_scheduler_job_errors_total",
)
```

**File:** `apps/prometheus/src/localstock/scheduler/error_listener.py` (NEW)

```python
"""Phase 24 — APScheduler EVENT_JOB_ERROR listener (D-06, OBS-16).

- Increments scheduler_job_errors_total{job_id, error_type}.
- Sends Telegram alert with 15-minute in-memory dedup keyed by
  (job_id, error_type) — counter keeps incrementing, alert is suppressed.
- Always logs scheduler_job_failed at ERROR with full traceback.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TYPE_CHECKING

from loguru import logger
from prometheus_client import REGISTRY

if TYPE_CHECKING:
    from apscheduler.events import JobExecutionEvent

# In-memory dedup cache. Keyed by (job_id, error_type) -> last alert datetime.
_DEDUP_WINDOW = timedelta(minutes=15)
_dedup_cache: dict[tuple[str, str], datetime] = {}
_dedup_lock = Lock()  # APScheduler may dispatch listeners from worker threads


def _should_alert(key: tuple[str, str], now: datetime) -> bool:
    """Return True if an alert should be sent for ``key``; updates cache."""
    with _dedup_lock:
        last = _dedup_cache.get(key)
        if last is not None and (now - last) < _DEDUP_WINDOW:
            return False
        _dedup_cache[key] = now
        return True


async def _send_telegram(job_id: str, error_type: str, exc: BaseException,
                        traceback_str: str) -> None:
    """Fire-and-forget Telegram dispatch (best-effort)."""
    try:
        from localstock.notifications.telegram import TelegramNotifier
        notifier = TelegramNotifier()
        if not notifier.is_configured:
            return
        tb_snippet = (traceback_str or "")[:500]
        msg = (
            "🚨 <b>Scheduler job failed</b>\n"
            f"Job: <code>{job_id}</code>\n"
            f"Error: <code>{error_type}</code>: {exc}\n"
            f"<pre>{tb_snippet}</pre>"
        )
        await notifier.send_message(msg)
    except Exception:
        logger.exception("scheduler.alert.dispatch_failed", job_id=job_id)


def on_job_error(event: "JobExecutionEvent") -> None:
    """APScheduler EVENT_JOB_ERROR handler.

    NOTE: APScheduler invokes listeners synchronously from the dispatch thread.
    With ``AsyncIOScheduler`` the dispatch thread IS the asyncio loop thread,
    so ``asyncio.create_task`` works. We still defensively use
    ``run_coroutine_threadsafe`` if no running loop is detected.
    """
    job_id = event.job_id or "<unknown>"
    exc = event.exception
    error_type = type(exc).__name__ if exc is not None else "Unknown"
    traceback_str = event.traceback or ""

    # 1) Counter — always
    counter = REGISTRY._names_to_collectors.get(
        "localstock_scheduler_job_errors_total"
    )
    if counter is not None:
        counter.labels(job_id=job_id, error_type=error_type).inc()

    # 2) Log — always (full traceback via loguru's exception= path)
    logger.bind(job_id=job_id, error_type=error_type).error(
        "scheduler_job_failed\n{tb}", tb=traceback_str
    )

    # 3) Telegram — rate-limited
    key = (job_id, error_type)
    if not _should_alert(key, datetime.now(UTC)):
        return

    coro = _send_telegram(job_id, error_type, exc or RuntimeError("unknown"),
                          traceback_str)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # Listener fired from a thread without a running loop — try the
        # main loop if APScheduler exposes it; else schedule on default.
        try:
            asyncio.run(coro)  # last resort, blocks; should be rare
        except Exception:
            logger.exception("scheduler.alert.no_loop", job_id=job_id)
```

**Wire-up in `scheduler/scheduler.py`** (inside `setup_scheduler()`):

```python
from apscheduler.events import EVENT_JOB_ERROR
from localstock.scheduler.error_listener import on_job_error

scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)
```

**APScheduler API** [VERIFIED: existing `apscheduler>=3.11,<4.0` pin + `from apscheduler.schedulers.asyncio import AsyncIOScheduler` already in scheduler.py]:
- `EVENT_JOB_ERROR` is bitfield from `apscheduler.events`. The dispatched `JobExecutionEvent` has attributes `job_id: str`, `exception: BaseException | None`, `traceback: str | None`, `scheduled_run_time: datetime`. [CITED: apscheduler.readthedocs.io v3 — `apscheduler.events.JobExecutionEvent`]
- `AsyncIOScheduler` runs the job in `loop.run_in_executor(...)` for sync jobs OR directly schedules coroutines. The error listener is called synchronously from the loop after the job's task completes; thus `asyncio.get_running_loop()` succeeds inside the handler. [ASSUMED — confirmed by reading APScheduler 3.x source on prior phases; verify with a unit test that asserts `loop.create_task` path works.]

**Confidence:** HIGH for counter+log path; MEDIUM for `asyncio.get_running_loop()` working from listener — covered by D-09 unit test.

---

## §6. Pipeline Step Timer Code

**Patch to `services/pipeline.py`:**

```python
import time
from contextlib import asynccontextmanager
from prometheus_client import REGISTRY


class Pipeline:
    # ... existing __init__ ...

    @asynccontextmanager
    async def _step_timer(self, step_name: str, run: PipelineRun):
        """Time a pipeline step. Records duration on PipelineRun row AND
        emits op_duration_seconds even on exception (D-08).
        """
        t0 = time.perf_counter()
        outcome = "success"
        try:
            yield
        except Exception:
            outcome = "fail"
            raise
        finally:
            elapsed = time.perf_counter() - t0
            duration_ms = int(elapsed * 1000)
            setattr(run, f"{step_name}_duration_ms", duration_ms)
            hist = REGISTRY._names_to_collectors.get(
                "localstock_op_duration_seconds"
            )
            if hist is not None:
                hist.labels("pipeline", "step", step_name, outcome).observe(elapsed)
```

**Refactor `run_full` body** — wrap each of the 4 steps:

```python
async with self._step_timer("crawl", run):
    # current Steps 1-7 body — listings, prices, financials, companies, events
    ...
async with self._step_timer("analyze", run):
    # Step 8 + future analyzer hook
    await self._apply_price_adjustments()
    # NOTE: scoring/reporting are not yet in run_full — see Open Q-1
async with self._step_timer("score", run):
    pass  # placeholder — populated by future scoring integration
async with self._step_timer("report", run):
    pass  # placeholder — populated by future report-generation integration
```

**The reconciliation issue:** The current `Pipeline.run_full` has 8 numbered sub-steps that all map to "crawl" semantically. There is **no analyze/score/report code in `pipeline.py`** today — those run from `automation_service.AutomationService.run_daily_pipeline()` (downstream). See Open Question Q-1 for the recommended scope. This research RECOMMENDS Plan 24-06 only wraps `crawl` initially with a real timer, leaving `analyze/score/report` as zero-duration placeholders OR (better) wraps the existing `_apply_price_adjustments()` as `analyze` and leaves `score`/`report` NULL until those services are integrated. Migration nullability supports both.

**Confidence:** HIGH for the context-manager mechanics; MEDIUM for the step-name mapping (depends on resolution of Open Q-1).

---

## §7. Alembic Migration Template

**File:** `apps/prometheus/alembic/versions/24a_pipeline_run_durations.py` (NEW)

```python
"""add pipeline_run per-step duration columns

Revision ID: 24a1b2c3d4e5
Revises: f11a1b2c3d4e
Create Date: 2026-04-30 09:00:00.000000

Phase 24 D-07 / OBS-17: 4 nullable Integer columns capturing per-stage
duration in milliseconds. Nullable=True so existing rows stay unchanged.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "24a1b2c3d4e5"
down_revision: Union[str, None] = "f11a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipeline_runs",
                  sa.Column("crawl_duration_ms", sa.Integer(), nullable=True))
    op.add_column("pipeline_runs",
                  sa.Column("analyze_duration_ms", sa.Integer(), nullable=True))
    op.add_column("pipeline_runs",
                  sa.Column("score_duration_ms", sa.Integer(), nullable=True))
    op.add_column("pipeline_runs",
                  sa.Column("report_duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_runs", "report_duration_ms")
    op.drop_column("pipeline_runs", "score_duration_ms")
    op.drop_column("pipeline_runs", "analyze_duration_ms")
    op.drop_column("pipeline_runs", "crawl_duration_ms")
```

**ORM update** in `db/models.py` (after line 130 in `PipelineRun`):

```python
    crawl_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analyze_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Local test commands:**

```bash
cd apps/prometheus
uv run alembic upgrade head
uv run python -c "
from localstock.db.database import get_engine
import asyncio, sqlalchemy as sa
async def check():
    eng = get_engine()
    async with eng.begin() as conn:
        cols = await conn.run_sync(lambda c: [r[0] for r in c.execute(
            sa.text(\"SELECT column_name FROM information_schema.columns \"
                    \"WHERE table_name='pipeline_runs'\")
        )])
    print(cols)
asyncio.run(check())
"
# Expect: includes 'crawl_duration_ms', 'analyze_duration_ms',
#         'score_duration_ms', 'report_duration_ms'
uv run alembic downgrade -1   # verify reversibility
uv run alembic upgrade head    # restore
```

**Naming convention check:** existing files use both `<hash>_<slug>.py` (auto-gen) and `add_phaseN_<topic>.py` (handwritten). Either is fine; recommend the explicit `add_phase24_pipeline_run_durations.py` pattern matching Phase 11. Pick one and document in the plan.

**Confidence:** HIGH. Migration is trivial DDL, identical pattern to existing Phase 11 migration.

---

## §8. Test Plan (per-OBS)

| Req | Test file | Test name | Approach |
|---|---|---|---|
| **OBS-11** | `test_observability/test_observe_decorator.py` | `test_observe_sync_success_records_histogram` | Wrap a sync fn returning 42; assert `op_duration_seconds.labels("d","s","a","success")` count == 1; assert log line `op_complete` with int `duration_ms`. |
| OBS-11 | same | `test_observe_sync_exception_marks_fail_and_reraises` | Wrap sync fn that raises ValueError; assert ValueError re-raised, label outcome=fail, log `op_failed` with `error_type=ValueError`. |
| OBS-11 | same | `test_observe_async_success_records_histogram` | Async coroutine; same assertions. |
| OBS-11 | same | `test_observe_async_exception_reraises` | Async raises RuntimeError; assert outcome=fail, fr re-raised. |
| OBS-11 | same | `test_observe_invalid_name_raises_at_decoration_time` | `@observe("only.two")` → ValueError at import. |
| OBS-11 | same | `test_observe_log_false_suppresses_log_but_emits_metric` | Verify `log=False` path. |
| **OBS-12** | `test_observability/test_db_events.py` | `test_select_pgsleep_observed_in_histogram` | Real async engine on test DB; `await session.execute(text("SELECT pg_sleep(0.05)"))`; assert `db_query_duration_seconds.labels("SELECT","cold")` count >= 1 and observation > 0.04 s. |
| OBS-12 | same | `test_table_class_hot_for_stock_prices_select` | `SELECT 1 FROM stock_prices LIMIT 1` → labels include `table_class=hot`. |
| OBS-12 | same | `test_query_type_other_for_unknown_keyword` | `WITH x AS (SELECT 1) SELECT * FROM x` regex falls through to `OTHER`. |
| OBS-12 | same | `test_listener_idempotent_on_repeated_attach` | Call `attach_query_listener(engine)` twice; only one observation per query. |
| **OBS-13** | `test_observability/test_db_events.py` | `test_slow_query_log_and_counter_above_threshold` | `monkeypatch.setenv("SLOW_QUERY_THRESHOLD_MS","50")` + `get_settings.cache_clear()`; run `SELECT pg_sleep(0.1)`; assert `db_query_slow_total.labels("SELECT","cold")` count == 1 + log line `slow_query`. |
| **OBS-14** | `test_api/test_health_endpoints.py` | `test_health_live_returns_200_no_db` | `TestClient.get("/health/live")` → 200, body `{"status":"alive"}`; with DB factory monkeypatched to raise — still 200. |
| OBS-14 | same | `test_health_ready_returns_200_with_pool_stats` | DB up → 200, body has `db=ok` and `pool` dict with 4 keys. |
| OBS-14 | same | `test_health_ready_returns_503_on_db_timeout` | Monkeypatch session.execute to `asyncio.sleep(5)`; expect 503 within 2-3s. |
| OBS-14 | same | `test_health_pipeline_returns_age_when_run_exists` | Insert a PipelineRun completed 1 hr ago → `last_pipeline_age_seconds >= 3600`. |
| OBS-14 | same | `test_health_data_returns_freshness` | Insert StockPrice on yesterday → `trading_days_lag` consistent with weekday math. |
| OBS-14 | same | `test_health_alias_sets_deprecation_header` | `GET /health` → response header `X-Deprecated` present, body equals `/health/ready`. |
| **OBS-15** | `test_scheduler/test_health_probe.py` | `test_health_self_probe_populates_all_four_gauges` | Insert PipelineRun(status=completed, completed_at=now-10s, symbols_success=42); call `await health_self_probe()`; assert `last_pipeline_age_seconds._value.get() >= 10` and `last_crawl_success_count == 42`; pool gauges > 0. |
| OBS-15 | same | `test_health_self_probe_swallows_db_error` | Patch `get_session_factory` to raise; call probe; assert returns None and log `health_probe_failed` emitted. |
| **OBS-16** | `test_scheduler/test_error_listener.py` | `test_on_job_error_increments_counter` | Construct `JobExecutionEvent(...)`; call `on_job_error(event)`; assert counter +1 with labels. |
| OBS-16 | same | `test_on_job_error_dispatches_telegram_first_time` | Mock `TelegramNotifier.send_message = AsyncMock()` via monkeypatch; trigger; await loop drain; assert called once. |
| OBS-16 | same | `test_on_job_error_dedup_suppresses_within_15_min` | Trigger same `(job_id, error_type)` twice within window; counter +2, telegram called once. |
| OBS-16 | same | `test_on_job_error_distinct_error_type_alerts_separately` | `(job_id, ValueError)` then `(job_id, KeyError)` → 2 telegram calls. |
| **OBS-17** | `test_services/test_pipeline_timing.py` | `test_run_full_populates_all_four_duration_columns` | Mock `_crawl_prices`/`_apply_price_adjustments` to `await asyncio.sleep(0.01)`; run `Pipeline.run_full()`; reload PipelineRun row; assert all 4 `*_duration_ms` are non-null `>= 10`. |
| OBS-17 | same | `test_run_full_records_duration_even_on_step_exception` | Mock `_crawl_prices` to raise after 50 ms sleep; run; assert `crawl_duration_ms >= 50` even though run.status=='failed'. |

**Total: 24 new tests** (matches D-09 estimate of 25-30).

### Test infrastructure additions

**`mock_telegram_client` fixture** — append to `tests/test_scheduler/conftest.py` (create if absent):

```python
@pytest.fixture
def mock_telegram_send(monkeypatch):
    """Replace TelegramNotifier.send_message with AsyncMock; returns the mock."""
    from unittest.mock import AsyncMock
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "localstock.notifications.telegram.TelegramNotifier.send_message", sent
    )
    # Ensure the notifier reports configured even when env vars unset
    monkeypatch.setattr(
        "localstock.notifications.telegram.TelegramNotifier.is_configured",
        property(lambda self: True),
    )
    yield sent
```

**`pg_sleep` test DB:** project uses Postgres (asyncpg). `pg_sleep(N)` is a built-in PG function. CI must have a real test database — verify `tests/conftest.py` for `DATABASE_URL` env (if tests use SQLite for unit tests, OBS-12/OBS-13 must be marked `@pytest.mark.integration` and use a Postgres fixture). **Action for planner:** confirm test-DB strategy during 24-03 plan; if no Postgres in CI, use `time.sleep`-injected listener test (mock the `before_cursor_execute` to call back immediately while reporting an artificial elapsed value).

**Fault-injected scheduler job:** OBS-16 tests don't need to run the actual scheduler — they call `on_job_error(event)` directly with a hand-built `JobExecutionEvent`. The "fault-injected job" pattern is overkill for unit tests; reserve it for an optional integration smoke test:

```python
def test_real_scheduler_dispatches_listener(monkeypatch, mock_telegram_send):
    sched = AsyncIOScheduler()
    sched.add_listener(on_job_error, EVENT_JOB_ERROR)
    sched.add_job(lambda: 1/0, "date",
                  run_date=datetime.now() + timedelta(milliseconds=50),
                  id="boom")
    sched.start()
    await asyncio.sleep(0.5)
    sched.shutdown(wait=False)
    assert mock_telegram_send.await_count == 1
```

---

## §9. Configuration Changes

**`apps/prometheus/src/localstock/config.py`** — add to `Settings`:

```python
from pydantic import Field

class Settings(BaseSettings):
    ...
    # Phase 24 — slow-query threshold (D-02)
    slow_query_threshold_ms: int = Field(default=250, ge=1, le=10000)
```

**`apps/prometheus/.env.example`** — append:

```bash
# Slow query log threshold in milliseconds (Phase 24, OBS-13).
# Queries exceeding this duration emit a `slow_query` log line and
# increment localstock_db_query_slow_total. Range 1..10000.
SLOW_QUERY_THRESHOLD_MS=250
```

**Cache invalidation note:** `get_settings()` is `@lru_cache`d. Slow-query test must call `get_settings.cache_clear()` after `monkeypatch.setenv(...)` for the new value to take effect. Recommend a small `_settings_env` test helper fixture that handles this automatically — already a pattern in Phase 22 tests.

---

## §10. Common Pitfalls

### Pitfall 1: Decorator on bound method drops `self`
**What goes wrong:** `@observe("…")` applied above a method must wrap, not unbind. `functools.wraps` already preserves descriptor protocol, so `Class().method()` works. Verified by `test_observe_sync_success_records_histogram` using a method.

### Pitfall 2: `event.listen(async_engine, …)` silently no-ops
**What goes wrong:** Attaching to AsyncEngine directly does nothing — events never fire.
**Fix:** Always attach to `engine.sync_engine` per §2.

### Pitfall 3: `get_settings()` `lru_cache` defeats `monkeypatch.setenv`
**What goes wrong:** Threshold tests don't see the patched env var.
**Fix:** `get_settings.cache_clear()` in the test fixture or use a fresh `Settings()` instance.

### Pitfall 4: Telegram dispatch from non-loop thread
**What goes wrong:** APScheduler may dispatch listeners from a thread without a running loop in some configurations; `asyncio.create_task` raises.
**Fix:** Try/except around `asyncio.get_running_loop()` (shown in §5). Preferred: keep `AsyncIOScheduler` (already in use) — listeners run in the loop thread.

### Pitfall 5: Self-probe stale lock — `max_instances=1`
**What goes wrong:** If a probe DB query hangs, next 30 s tick stacks a duplicate task.
**Fix:** `max_instances=1, coalesce=True` on `add_job` (shown in §4).

### Pitfall 6: `engine.pool.size()` on `NullPool` raises
**What goes wrong:** Tests that swap to NullPool break self-probe.
**Fix:** Defensive try/except at the body of `health_self_probe` (already present).

### Pitfall 7: Per-step duration on exception
**What goes wrong:** Naïve `try/finally` in `_step_timer` is correct, but if you put `setattr` AFTER `raise` it never runs.
**Fix:** Use `try/yield/except (re-raise)/finally (record)` — order matters. Pattern shown in §6.

### Pitfall 8: Phase 23 D-08 grep flagging `decorators.py`
**What goes wrong:** The Phase 23 lint grep `\.(inc|observe|set)\(` will flag legitimate calls inside `decorators.py` and `db_events.py`.
**Fix:** Update the lint regex to allow `observability/` prefix, OR document the false-positive in the plan's verification section.

### Pitfall 9: `/health/ready` 503 doesn't propagate through Instrumentator
**What goes wrong:** Setting `response.status_code = 503` while returning a dict still produces correct status, but only via FastAPI's `Response` type-hint dependency injection. Verified pattern.
**Fix:** Already shown — `response: Response = Depends()` parameter + setting `.status_code`.

---

## §11. Open Questions

### Q-1: `@observe` rollout scope — full sweep vs minimal?
- **What we know:** D-01 says "scheduler jobs + pipeline step methods + key crawler entry points". Plan 24-06 wires step timing.
- **What's unclear:** Should `@observe` decorate every method on `Pipeline`, every crawler `fetch()`, every repository `upsert_*`?
- **Recommendation:** **Minimal scope** in Phase 24 — apply only to:
  - `daily_job` in `scheduler.py`
  - The 4 step-timer wrap sites in `Pipeline.run_full` (handled by `_step_timer`, no extra decorator needed)
  - Top-level `PriceCrawler.fetch`, `FinanceCrawler.fetch`, `CompanyCrawler.fetch`, `EventCrawler.fetch` — 4 representative call sites for validation.
- Defer "full sweep" to Phase 25 hygiene work. Flag in plan-checker.

### Q-2: `/health/data` — Vietnamese trading calendar
- **What we know:** D-03 allows minimal static list; full calendar deferred.
- **Decision recommended:** Use the small `_VN_HOLIDAYS_2025_2026` set in §3. Document in code as "covers v1.5 + v1.6; refresh annually". Add a TODO comment with the issue number for backlog tracking.

### Q-3: Scheduler step naming for `analyze/score/report`
- **What we know:** `Pipeline.run_full` currently has no analyze/score/report — those run via `automation_service.AutomationService.run_daily_pipeline()`.
- **What's unclear:** Should `_step_timer("analyze"/…)` call into `AutomationService` from `Pipeline`, or should `AutomationService` be modified to set those columns on the same `PipelineRun` row?
- **Recommendation:** Plan 24-06 wraps:
  - `crawl` = current Steps 1-7 (listings + 4 crawlers + storage)
  - `analyze` = `_apply_price_adjustments()` (the only analytic in pipeline.py today)
  - `score`, `report` = leave as **NULL** for now; explicit `setattr(run, "score_duration_ms", None)` is fine and the migration nullability supports it.
- A future phase will wire `AutomationService.run_daily_pipeline` to populate score/report by passing the `run` row through.

### Q-4: Test DB availability for OBS-12/OBS-13 integration tests
- **What we know:** Project uses asyncpg/Postgres in production; `pg_sleep` is Postgres-only.
- **What's unclear:** Does CI have a Postgres service or only SQLite? `tests/conftest.py` content not surveyed in this research session.
- **Recommendation:** Plan 24-03 must include a "test DB audit" task at the start. If CI is SQLite-only, gate OBS-12/13 tests behind `@pytest.mark.integration` + provide a fallback unit test that mocks `before_cursor_execute` without a real DB.

### Q-5: Phase 23 D-08 lint exemption
- **What we know:** Phase 23 introduced a grep that fails CI on `\.(inc|observe|set)\(` outside `metrics.py`.
- **Recommendation:** Plan 24-01 must update the lint script (or its allowlist) to permit `observability/decorators.py` and `observability/db_events.py`. Document in plan + verify in plan-checker.

---

## §12. References

### Primary (HIGH confidence)
- `apps/prometheus/src/localstock/observability/metrics.py` — Phase 23 primitives (verified 13 collectors)
- `apps/prometheus/src/localstock/observability/logging.py` — loguru patcher + structured kwargs idiom
- `apps/prometheus/src/localstock/scheduler/scheduler.py` — `AsyncIOScheduler`, `setup_scheduler()`, lifespan integration
- `apps/prometheus/src/localstock/services/pipeline.py` — `run_full` body shape + defensive commit hotfix
- `apps/prometheus/src/localstock/db/database.py` — `create_async_engine` singleton
- `apps/prometheus/src/localstock/db/models.py:117-130` — `PipelineRun` baseline schema
- `apps/prometheus/src/localstock/api/routes/health.py` — current single endpoint
- `apps/prometheus/src/localstock/notifications/telegram.py` — `TelegramNotifier.send_message`
- `apps/prometheus/alembic/versions/add_phase11_admin_tables.py` — head revision `f11a1b2c3d4e` (Phase 24 revises from this)
- `.planning/phases/22-logging-foundation/22-RESEARCH.md` — loguru contextualize + redaction patterns
- `.planning/phases/23-metrics-primitives-metrics-endpoint/23-RESEARCH.md` — `_register` helper + label budget
- `.planning/phases/23-metrics-primitives-metrics-endpoint/23-01-SUMMARY.md` and `23-02-SUMMARY.md` — what shipped

### Secondary (MEDIUM)
- SQLAlchemy 2.0 docs — `event.listen(engine.sync_engine, …)` async pattern [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
- APScheduler 3.x docs — `EVENT_JOB_ERROR` + `JobExecutionEvent` shape [CITED: apscheduler.readthedocs.io/en/3.x/modules/events.html]
- Python `inspect.iscoroutinefunction` — stable since 3.8 [CITED: docs.python.org/3/library/inspect.html]

### Tertiary (LOW — flagged)
- APScheduler `AsyncIOScheduler` listener thread context [ASSUMED — verified by D-09 OBS-16 unit test]
- Pool inheritance behaviour under `NullPool` for self-probe [ASSUMED — defensive try/except already covers]

---

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (existing, configured in `apps/prometheus/pyproject.toml`) |
| Config | existing `pytest.ini`/pyproject |
| Quick run | `cd apps/prometheus && uv run pytest tests/test_observability/test_observe_decorator.py -x -q` |
| Per-plan run | `uv run pytest tests/test_observability/ tests/test_api/test_health_endpoints.py tests/test_scheduler/ -x -q` |
| Full suite | `cd apps/prometheus && uv run pytest -x -q` (currently 471 passing; Phase 24 adds ~24 → expect 495) |

### Phase Requirements → Test Map
| Req | Test count | Automated? |
|---|---|---|
| OBS-11 | 6 | ✅ unit |
| OBS-12 | 4 | ✅ integration (Postgres test DB OR mocked listener) |
| OBS-13 | 1 | ✅ integration (pg_sleep) |
| OBS-14 | 6 | ✅ TestClient |
| OBS-15 | 2 | ✅ unit |
| OBS-16 | 4 | ✅ unit + 1 optional smoke |
| OBS-17 | 2 | ✅ integration |

### Sampling Rate
- **Per task commit:** plan-scoped pytest selector (above)
- **Per wave merge:** `uv run pytest tests/test_observability/ tests/test_api/ tests/test_scheduler/ tests/test_services/ -x -q`
- **Phase gate:** full `uv run pytest -x -q` green + `bash apps/prometheus/scripts/lint-no-fstring-logs.sh` clean + Phase 23 D-08 grep updated/clean.

### Wave 0 Gaps
- [ ] `tests/test_scheduler/conftest.py` — may not exist; create with `mock_telegram_send` fixture
- [ ] `tests/test_services/test_pipeline_timing.py` — new file
- [ ] Confirm Postgres availability for OBS-12/13 integration tests (Open Q-4)
- [ ] Update Phase 23 D-08 lint allowlist for `observability/decorators.py` + `db_events.py` (Open Q-5)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | health endpoints are unauth (intentional — operator network only) |
| V3 Session Management | no | — |
| V4 Access Control | partial | `/health/ready`/`/health/pipeline`/`/health/data` leak DB pool stats + pipeline counts; ACCEPTED RISK per single-tenant project (CONTEXT.md scope) |
| V5 Input Validation | yes | `slow_query_threshold_ms` validated via Pydantic `Field(ge=1, le=10000)` |
| V6 Cryptography | no | — |
| V7 Error Handling | yes | `@observe` re-raises (no swallow); error listener logs traceback at ERROR; `/health/ready` returns generic `error_type` only — no SQL, no stack |
| V8 Data Protection | yes | `slow_query` log includes `statement_preview[:120]` — bounded; PII-redaction patcher (Phase 22) still applies |
| V14 Configuration | yes | `.env.example` documents new var |

### Threat patterns

| Pattern | STRIDE | Mitigation |
|---|---|---|
| Health endpoint info leak (pool size, last error type) | I | Single-tenant accepted risk; `/health/live` is the only one safe to expose publicly |
| Telegram message storm DoS | A | 15-min `(job_id, error_type)` dedup |
| Slow-query log SQL leak | I | `statement_preview` bounded to 120 chars; redaction patcher still runs over the loguru record |
| Decorator metric label cardinality blow-up | A | `domain.subsystem.action` enforced as 3 fixed tokens at decoration time — no dynamic strings |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `AsyncIOScheduler` invokes `EVENT_JOB_ERROR` listener from the asyncio loop thread | §5 | LOW — fallback `asyncio.run` path covers; D-09 unit test confirms |
| A2 | `engine.pool` is QueuePool (not NullPool) at runtime | §4 | LOW — defensive try/except in probe body |
| A3 | Existing test infra has Postgres for `pg_sleep` integration | §8 | MEDIUM — mitigated by Open Q-4 audit task |
| A4 | Phase 23 D-08 grep is the only lint that flags non-primitive metric calls | §10 P-8 | LOW — `lint-no-fstring-logs.sh` is unrelated; cross-checked |
| A5 | `analyze/score/report` step naming maps to `_apply_price_adjustments()` (analyze) + NULLs for now | §6, Q-3 | MEDIUM — confirm during 24-06 planning; nullability supports either resolution |

---

## Confidence Breakdown

| Area | Level | Reason |
|---|---|---|
| `@observe` decorator | HIGH | Standard Python pattern; codebase has Phase 22+23 patterns to extend |
| DB event listener | HIGH | Verified via SQLAlchemy 2.0 docs + project uses async engine identically |
| Health probes | HIGH | Same FastAPI + SQLAlchemy idioms as current `health.py` |
| Self-probe job | HIGH | APScheduler IntervalTrigger + REGISTRY lookup are standard |
| Scheduler error listener | MEDIUM-HIGH | EVENT_JOB_ERROR API verified; loop-thread assumption needs the unit test |
| Step timer | HIGH | Local context manager; no external deps |
| Migration | HIGH | Trivial DDL; pattern from Phase 11 |
| Test plan | MEDIUM | Postgres availability for pg_sleep needs Open Q-4 resolution |

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (30 days — stack is stable, no upcoming breaking releases of apscheduler 3.x or SQLAlchemy 2.x within window)
