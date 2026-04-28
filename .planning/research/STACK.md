# Stack Research — v1.5 Performance & Data Quality

**Domain:** Local-first single-user data pipeline (FastAPI + APScheduler + Postgres)
**Researched:** 2026-04-29
**Confidence:** HIGH (versions verified on PyPI 2026-04-29; integration patterns verified against existing codebase)
**Scope:** Stack ADDITIONS/CHANGES for v1.5 only. The v1.0–v1.4 core stack (FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, APScheduler, httpx, pandas, pandas-ta, vnstock 4.x, loguru, tenacity) is already validated and stays.

> **Note on prompt drift**: Orchestrator brief listed `vnstock 3.5.1` and "structlog vs loguru". Actual `pyproject.toml` already pins `vnstock>=4.0.1,<5.0` and `loguru>=0.7,<1.0`. Recommendations below reflect what's in the file, not the brief.

---

## Guiding Constraints (drive every choice below)

1. **Single user, single host.** No multi-worker uvicorn, no horizontal scale. Anything in-process beats anything that needs a sidecar.
2. **Free tier / local only.** Supabase free Postgres, RTX 3060, no managed Redis, no Datadog. Cost of new infra ≈ ∞.
3. **Existing scheduler is APScheduler in-process.** All caches and metrics share that process — no IPC needed.
4. **~400 stocks × 5 dimensions, runs 1×/day + on-demand.** This is a *throughput-modest, latency-tolerant* workload. Don't reach for distributed-system tooling.
5. **Already have loguru + tenacity.** Don't add a second logging library unless the upgrade is decisive.

The TL;DR: **add 4 small libraries, no new runtime services.** Redis, Celery, RabbitMQ, statsd, Great Expectations, OpenTelemetry collectors are all rejected for this milestone — they solve problems we don't have.

---

## Recommended Stack — Additions

### Core Additions

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **cachetools** | `>=7.0,<8.0` (latest 7.0.6) | In-process TTL/LRU cache for hot data (computed indicators, vnstock symbol lists, market summary) | Pure-Python, zero deps, ~1KB API. `TTLCache`/`LRUCache` are exactly what a single-process app needs. Drop-in `@cached` decorator. No serialization, no sidecar. |
| **hishel** | `>=1.2,<2.0` (latest 1.2.1) | RFC 9111 HTTP cache transport for httpx (vnstock + news fetches) | Native httpx integration via `hishel.AsyncCacheTransport` — drops into existing `httpx.AsyncClient`. SQLite or filesystem storage. Respects `Cache-Control`/`ETag`. Zero behavioural change for non-cacheable responses. |
| **diskcache** | `>=5.6,<6.0` (latest 5.6.3) | Persistent SQLite-backed cache for expensive computations that should survive restarts (e.g. financial-statement parses, daily indicator snapshots) | Pure-Python, single-file SQLite, no server. Survives process restart unlike `cachetools`. Used by Pip and Streamlit. Thread- and process-safe. |
| **pandera** | `>=0.31,<1.0` (latest 0.31.1) with `[pandas]` extra | DataFrame schema validation for OHLCV, indicators, fundamentals (data quality gate) | Built specifically for pandas validation. Pydantic v2 native. Schemas as code. Coercion + missing-data checks + custom checks. Lightweight (~3 deps) vs Great Expectations' full framework. Output integrates cleanly with anomaly-detection logic. |
| **prometheus-client** | `>=0.25,<1.0` (latest 0.25.0) | Metrics primitives (Counter / Gauge / Histogram) for pipeline timing, error rates, cache hit ratios | Reference Python client. Pull-model — exposes `/metrics`, no daemon required. Works fine with no scraper attached (just emits to memory). Minimal overhead. |
| **prometheus-fastapi-instrumentator** | `>=7.1,<8.0` (latest 7.1.0) | One-line FastAPI middleware emitting standard HTTP metrics | Wraps `prometheus-client`. Auto-instruments request latency / status / in-flight. Adds `/metrics` route. ~50 lines of integration glue we'd otherwise hand-roll. |

### Supporting Libraries (use only if needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **fakeredis** | `>=2.30,<3.0` | Redis-API stub for tests | Only if (later) we adopt a Redis-shaped abstraction. **Skip for v1.5** — not needed since we're not using Redis. |
| **anyio** | already transitive via FastAPI | `anyio.Semaphore` / task groups for bounded concurrency in pipeline batching | Use `anyio.create_task_group()` + `anyio.Semaphore(N)` for the ~400-stock fan-out instead of `asyncio.gather`. No new dep. |
| **pytest-benchmark** | `>=5.0,<6.0` | Regression-test pipeline phase timings | Add only if/when we want CI guards on pipeline speed. Optional. |
| **psutil** | `>=6.0,<7.0` | Process/host metrics (RSS, CPU, GPU-adjacent) for health dashboard | Add when health dashboard wants memory/CPU panels. Tiny dep. |

### Database Optimization — No Library, Just Patterns

| Approach | Tooling | Why |
|----------|---------|-----|
| **Indexes** | Alembic migrations (existing) | Already in stack. Add `op.create_index(..., postgresql_using='btree')` migrations for `(symbol, date)`, `(date)` on prices, `(symbol, indicator_name, date)` on indicators. No new dep. |
| **Slow query log** | SQLAlchemy `before_cursor_execute` / `after_cursor_execute` events | Hand-rolled middleware logs queries > N ms via loguru. ~30 LOC. No `sqlalchemy-utils` needed. |
| **Query plan inspection** | `EXPLAIN (ANALYZE, BUFFERS)` via psql / Supabase SQL editor | Manual, ad-hoc. No tool needed. |
| **pg_stat_statements** | Supabase enables by default; query via SQL | Free, native, zero install. Surfaces slowest queries in production. |
| **Time-series partitioning** | Postgres declarative partitioning via raw SQL in Alembic | Native PG14+ feature. Partition `prices` and `indicators` by `RANGE(date)` (yearly). Raw SQL in `op.execute(...)`. No partitioning library needed. **Only do this if a table exceeds ~10M rows** — at 400 symbols × 5y × 250 trading days ≈ 500K rows for prices, partitioning is premature. Defer unless evidence shows pain. |
| **Connection pool tuning** | SQLAlchemy `create_async_engine(pool_size, max_overflow, pool_pre_ping)` | Already configurable. Just tune values; no new dep. |

### Logging — Keep Loguru, Don't Add structlog

**Decision: stay on loguru, enable JSON serialization + `logger.contextualize()` for structured fields.**

Loguru already installed. It supports:
- `logger.add(sink, serialize=True)` → newline-delimited JSON output, schema-stable.
- `logger.bind(job_id=...)` and `with logger.contextualize(request_id=...)` → contextual key/value fields propagate through async tasks.
- `logger.opt(record=True)` for record introspection.

**Why not structlog**: structlog is excellent and arguably more idiomatic for pure structured logging, but adopting it means rewriting every existing `logger.info(...)` call (326 backend tests reference loggers indirectly). The marginal gain over `loguru + serialize=True + contextualize` doesn't justify the churn for a single-user app. Revisit only if we ever ship to a real log aggregator that demands structlog conventions (we won't in v1.5).

**What to add (config, not dep):**
```python
# logging_config.py
logger.remove()
logger.add(sys.stderr, level=settings.log_level, serialize=False)  # human-readable in dev
logger.add("logs/app.jsonl", level="INFO", serialize=True, rotation="50 MB", retention=10)  # JSON for tooling
```

### Development Tools — No Changes

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff, mypy, pytest, pytest-asyncio | already in dev deps | No changes |
| `uv add --dev pytest-benchmark` | optional perf regression tests | Add only when we wire perf assertions into CI |

---

## Installation

```bash
# From apps/prometheus/
uv add cachetools hishel diskcache pandera[pandas] prometheus-client prometheus-fastapi-instrumentator

# Optional, when health dashboard needs host metrics
uv add psutil
```

That's the entire v1.5 dependency footprint: **6 small pure-Python packages, zero new services.**

---

## Integration Points with Existing Stack

### FastAPI lifespan
- `prometheus-fastapi-instrumentator` registers in `create_app()` after middleware setup. `/metrics` becomes available immediately.
- diskcache `Cache(directory=...)` instance created in lifespan startup, closed on shutdown. Inject via FastAPI `Depends`.
- `cachetools.TTLCache` lives as module-level singleton (process-local) — no lifespan management.

### APScheduler jobs
- Wrap each scheduled job body with a `Histogram.time()` context manager from `prometheus-client` → emits `localstock_pipeline_duration_seconds{phase=...}` for free.
- Use `with logger.contextualize(job_id=job.id, run_id=uuid4()):` at job entry → every nested log line gets job context. Loguru-native, no new lib.
- Add APScheduler event listeners (`EVENT_JOB_ERROR`, `EVENT_JOB_EXECUTED`) → increment Prometheus counters. ~20 LOC.

### httpx clients (vnstock + news)
- Replace `httpx.AsyncClient()` with `httpx.AsyncClient(transport=hishel.AsyncCacheTransport(httpx.AsyncHTTPTransport(), storage=hishel.AsyncSQLiteStorage(...)))`.
- Storage path under `var/cache/http/`. Respects `Cache-Control` from upstream — vnstock responses without cache headers will pass through unchanged (so no behavioural risk).

### SQLAlchemy
- Register two `event.listens_for` hooks on the engine for `before_cursor_execute` / `after_cursor_execute` → log queries > 250 ms with bind params (sanitized).
- New Alembic revisions per index (one revision per logical change — keeps rollback granular).

### Pandera in pipeline
- Define `OHLCVSchema`, `IndicatorSchema`, `FundamentalsSchema` as `pa.DataFrameSchema` next to the SQLAlchemy models.
- Validate at I/O boundaries: after vnstock fetch (raw → validated), before DB insert (computed → validated). Failed validation → log + quarantine row, don't crash pipeline.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `cachetools` (in-process TTL/LRU) | **Redis** (managed or self-hosted) | Only if we ever run multiple workers/processes that must share cache state. **Single-user APScheduler-in-process app does not.** Adds a sidecar to manage, secure, back up. |
| `cachetools` | `aiocache` (abstraction over memory/Redis/Memcached) | If we genuinely expect to swap backends later. We don't — and `aiocache` adds an indirection layer for a swap that's unlikely to happen. |
| `cachetools` | Python stdlib `functools.lru_cache` / `async-lru` | `lru_cache` has no TTL — wrong tool for indicators that go stale. `async-lru` is fine for trivial coroutine memoization but lacks TTL too. |
| `diskcache` | SQLite directly | We'd reinvent diskcache. It IS SQLite, just wrapped. |
| `hishel` | Hand-rolled httpx response cache | Hand-rolling RFC 9111 (vary headers, revalidation, stale-while-revalidate) is a tarpit. hishel is 1.x stable, maintained by encode (httpx authors' orbit). |
| Loguru + `serialize=True` | `structlog` | If we were starting fresh, structlog. We aren't — loguru is everywhere in the codebase already. Cost > benefit. |
| Loguru + `serialize=True` | stdlib `logging` + `python-json-logger` | More config, less ergonomic. Loguru already does this in one line. |
| `prometheus-client` | `statsd` + statsd daemon | Push model needs a daemon. We have no daemon. Pull model is free here. |
| `prometheus-client` | OpenTelemetry SDK | OTel is the future, but for a single-host single-user app the metrics-only Prom path is 10× simpler. Revisit if we ever export traces to an external backend. |
| `prometheus-client` | Lightweight custom counter dict | Throwing away the standard tooling for ~5 lines of "saved" deps. False economy — we'd rebuild histograms badly. |
| `pandera` | `great_expectations` | GE is a *framework* (config files, expectations stores, data docs HTML, CLI). Massive over-spec for in-line DataFrame checks in a 400-stock pipeline. Slow startup, heavy dep tree, opinionated runtime. |
| `pandera` | Hand-rolled Pydantic models per row | Pydantic validates row-at-a-time — converting a 400×500 DataFrame to Pydantic models is slow and loses pandas semantics (NaN handling, dtype checks, vectorized constraints). Pandera validates the frame, not the rows. |
| Alembic for indexes | `sqlalchemy-utils` | sqlalchemy-utils is a grab-bag (TimezoneType, JSON utilities, etc.) we don't need. Index DDL belongs in migrations regardless. |
| Native PG partitioning | `citus` / `timescaledb` | Both require server extensions. Supabase free tier won't allow arbitrary extensions. Native declarative partitioning is enough at our scale. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Redis** (as new dep) | Adds a sidecar service to install, run, monitor, and secure — for a single-process single-user app. No multi-worker scenario justifies it. | `cachetools` in-process + `diskcache` for persistence |
| **Celery / RQ / Dramatiq** | Distributed task queue when we already have APScheduler in-process and one user. Pure complexity tax. | Existing APScheduler |
| **Great Expectations** | Heavy framework, slow imports, JSON config files, expectation suites, data docs site generation — none of which we need. | `pandera` schemas |
| **statsd / DataDog / New Relic** | Push metrics to external service we don't run, or pay for. | `prometheus-client` `/metrics` endpoint |
| **OpenTelemetry full stack** (tracer + collector + exporter) | Massive for a 1-host app. The collector alone is a service to run. | `prometheus-client` for metrics; loguru JSON for "traces" via correlation IDs. Reconsider if we ever go multi-host. |
| **`logging` stdlib JSONFormatter rewrite** | Means dual-logging-system limbo for months. | Loguru `serialize=True` |
| **`asyncio.gather` for the 400-stock fan-out** | Unbounded concurrency → vnstock rate limits + thrash Postgres pool. | `anyio.Semaphore(N)` + task group; tune N (~10–20). No new dep. |
| **`sqlalchemy-utils`** | Broad utility lib; we'd use < 1% of it. | Inline helpers / Alembic ops |
| **`alembic-utils`** (for views/triggers) | We aren't using DB views/triggers/functions in v1.5 plan. | n/a |
| **`asyncio-pool` / `aiomultiprocess`** | Process pool when the workload is I/O-bound (HTTP + DB). | `anyio` semaphore |
| **TimescaleDB-specific features** | Supabase free won't let us add the extension. | Native PG partitioning if/when needed |

---

## Stack Patterns by Variant

**If pipeline phase is I/O-bound (vnstock fetch, news scrape, Ollama call):**
- Use `anyio.create_task_group()` + `anyio.Semaphore(10–20)` for bounded concurrency.
- Wrap with `tenacity.retry` (already installed) for transient failures.
- Cache responses with `hishel` at httpx layer.

**If pipeline phase is CPU-bound (indicator computation, pattern detection):**
- Stay sync inside the worker; pandas/numpy release the GIL on vectorized ops anyway.
- If a phase becomes a bottleneck, move it to `asyncio.to_thread()` rather than a process pool. Single-user app — we don't need true parallelism.

**If a result is reusable within a single pipeline run** (e.g., sector classification fetched once, used by 50 stocks):
- `cachetools.TTLCache(maxsize=1024, ttl=3600)` module-level.

**If a result is reusable across pipeline runs** (e.g., parsed financial statements, sector mapping):
- `diskcache.Cache("var/cache/diskcache")` with explicit keys.

**If pipeline NaN/missing-data ratio exceeds threshold:**
- Pandera schema with `pa.Check(lambda s: s.isna().mean() < 0.05)` — fails loudly, pipeline quarantines symbol, doesn't poison downstream scoring.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `pandera[pandas] 0.31.1` | `pandas 2.2.x`, `pydantic 2.13.x`, `numpy 2.x` | Pandera 0.30+ explicitly supports Pydantic v2 and pandas 2.1+. Verified against pyproject.toml. |
| `prometheus-fastapi-instrumentator 7.1.0` | `fastapi 0.135.x`, `starlette 0.40+` | 7.x line is current with FastAPI 0.115+. |
| `hishel 1.2.1` | `httpx 0.28.x` | hishel 1.x targets httpx 0.27+. Matches our `httpx>=0.28`. |
| `cachetools 7.0.6` | Python 3.12 | Pure Python, no constraints. Note: 7.x dropped Python 3.8; we're on 3.12 — fine. |
| `diskcache 5.6.3` | Python 3.12, SQLite ≥ 3.7 | Pure Python. Storage dir must not be on a network FS. |
| `prometheus-client 0.25.0` | Python 3.9+ | No FastAPI version coupling. |
| **Existing `loguru 0.7.x`** | Python 3.12, asyncio | `serialize=True` + `contextualize()` are both stable since 0.6. No upgrade needed. |

**Conflict watch:**
- `pandera` pulls `typing_inspect` and `typeguard`. Both are widely used and unlikely to clash.
- `hishel` storage drivers: pick *one* (`AsyncSQLiteStorage` recommended). Don't mix with on-disk filesystem storage in same app.
- `prometheus-client` exposes a global default registry; `prometheus-fastapi-instrumentator` uses it by default. If we ever want to isolate metrics per test, pass `registry=CollectorRegistry()` explicitly.

---

## Fallback / Escape Hatches

| Scenario | Fallback |
|----------|----------|
| We later run multiple uvicorn workers and need shared cache | Add `redis` + `aiocache` adapter. cachetools call sites are decorator-based and trivially swappable. Not v1.5. |
| diskcache corrupts (rare, but SQLite on weird FS) | Delete `var/cache/diskcache/` — pure cache, no source-of-truth data. |
| hishel cache returns stale data during vnstock outage | Force-refresh path: `client.get(url, extensions={"force_cache": False})` per request. Document in runbook. |
| Prometheus scraper not installed | `/metrics` still works as a GET — manual `curl localhost:8000/metrics` for spot checks; health dashboard can read it directly. |
| Pandera validation too strict, blocks pipeline | Schemas support `lazy=True` → collect all errors, log, optionally `coerce` instead of fail. Use `lazy=True` from day one in the pipeline; reserve `lazy=False` for tests. |
| Loguru JSON output too noisy | Add `filter=` callable on the JSON sink to drop debug-level events. No code rewrite. |

---

## Sources

- PyPI metadata fetched 2026-04-29 for: `structlog`, `prometheus-client`, `pandera`, `cachetools`, `aiocache`, `hishel`, `diskcache`, `async-lru`, `redis`, `sqlalchemy-utils`, `prometheus-fastapi-instrumentator`, `starlette-prometheus`, `opentelemetry-api`, `great-expectations` — HIGH confidence on versions.
- `apps/prometheus/pyproject.toml` (read directly) — HIGH confidence on existing pinned versions.
- `apps/prometheus/src/localstock/config.py` (read directly) — confirmed APScheduler-in-process model, no Redis configured, single uvicorn assumption.
- Loguru docs (`serialize`, `contextualize`, `bind`) — features are pre-0.7, stable. HIGH confidence from training + cross-checked against changelog dates.
- Pandera docs — `[pandas]` extra, Pydantic v2 support since 0.20.x. HIGH confidence (verified via PyPI requires_dist).
- hishel project (encode-adjacent author) — HTTP caching transport, RFC 9111. MEDIUM-HIGH (training + PyPI 1.2.1 release confirms maturity).
- prometheus-fastapi-instrumentator README — middleware integration pattern. HIGH confidence (widely used, 7.x stable).
- Postgres declarative partitioning since PG14 — supported on Supabase (PG15+). HIGH confidence.

---
*Stack research for: LocalStock v1.5 Performance & Data Quality additions*
*Researched: 2026-04-29*
