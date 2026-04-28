# Architecture Research — v1.5 Performance & Data Quality

**Domain:** Single-process FastAPI + APScheduler analytics backend (LocalStock / Prometheus)
**Researched:** 2026-04-29
**Confidence:** HIGH (grounded in concrete repo layout + verified library docs)

## Scope

How do **caching, observability, data-quality, and performance/DB optimization** integrate into the existing layered architecture (`api → services → repositories → db`) **without** introducing distributed infrastructure (no Celery, no Redis-as-required, no separate metrics agent)?

The hard constraint: **single Python process**, single user, local-first. APScheduler runs *inside* the FastAPI lifespan in the same event loop that serves HTTP requests. This is the architectural pivot — every new component below either (a) cooperates with that loop or (b) runs as a sidecar pull endpoint that an external tool scrapes.

## Standard Architecture (target end-state for v1.5)

```
                                    ┌──────────────────────────────────────┐
                                    │   Helios (Next.js, :3000)            │
                                    │   admin console + dashboard          │
                                    └──────────────┬───────────────────────┘
                                                   │ HTTP
┌──────────────────────────────────────────────────┴───────────────────────┐
│  Prometheus app (uvicorn, single process, single event loop, :8000)      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ ASGI Middleware Stack (executed top-down per request)              │  │
│  │  1. CORSMiddleware                            (existing)           │  │
│  │  2. CorrelationIdMiddleware  *NEW*  → contextvar request_id        │  │
│  │  3. RequestLoggingMiddleware *NEW*  → structured access log        │  │
│  │  4. PrometheusMetricsMiddleware *NEW* → http_* counters/histograms │  │
│  └─────────────────────────┬──────────────────────────────────────────┘  │
│                            │                                             │
│  ┌─────────────────────────▼──────────────────────────────────────────┐  │
│  │ API Layer (api/routes/*.py)                                        │  │
│  │  health, analysis, scores, reports, market, admin, …               │  │
│  │  + /metrics             *NEW* (prometheus_client.ASGIApp)          │  │
│  │  + /health/{live,ready,pipeline,data}  *EXPANDED*                  │  │
│  │  Depends(get_session), Depends(get_cache)  *NEW*                   │  │
│  └─────────────────────────┬──────────────────────────────────────────┘  │
│                            │                                             │
│  ┌─────────────────────────▼──────────────────────────────────────────┐  │
│  │ Service Layer (services/*.py) — business logic                     │  │
│  │  AnalysisService, ScoringService, ReportService, …                 │  │
│  │  ── wrapped by @cached(...) on hot read paths       *NEW*          │  │
│  │  ── timed by @observe("service.x.y") decorator      *NEW*          │  │
│  │  ── emits cache.invalidate(prefix) at write points  *NEW*          │  │
│  └────┬─────────────────────────────────────────────────┬─────────────┘  │
│       │                                                 │                │
│  ┌────▼──────────────────────┐    ┌─────────────────────▼────────────┐   │
│  │ Repository Layer          │    │ Quality / Validation Layer  *NEW*│   │
│  │ db/repositories/*         │    │ validators/ohlcv.py              │   │
│  │ + @timed_query decorator  │    │ validators/financials.py         │   │
│  │   *NEW* → db_query_*      │    │ DataQualityService               │   │
│  └────┬──────────────────────┘    │ → writes data_quality_runs table │   │
│       │                           └──────────────────────────────────┘   │
│  ┌────▼──────────────────────────────────────────────────────────────┐   │
│  │ Async SQLAlchemy engine (singleton) — pool_size 3→10 *MODIFIED*   │   │
│  │ pool_pre_ping, statement cache disabled (Supabase pgbouncer)      │   │
│  └────┬──────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│  ┌────▼─────────┐   ┌────────────────────────────────┐                   │
│  │ PostgreSQL   │   │ APScheduler (AsyncIOScheduler) │                   │
│  │ (Supabase)   │   │ same loop as ASGI              │                   │
│  │ + new        │   │  • daily_pipeline (15:45 VN)   │                   │
│  │   indexes    │   │  • admin_job_worker (5s)       │                   │
│  │   *NEW*      │   │  • cache_janitor *NEW* (60s)   │                   │
│  └──────────────┘   │  • health_self_probe *NEW*(30s)│                   │
│                     └─────────────┬──────────────────┘                   │
│                                   │                                      │
│  ┌────────────────────────────────▼─────────────────────────────────┐    │
│  │ Cache Backend  *NEW*   (Protocol: get/set/delete/invalidate)     │    │
│  │  Default:  cachetools.TTLCache wrapped in async lock             │    │
│  │  Optional: Redis adapter (aiocache) — toggled by settings only   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ Observability Module  *NEW*  (localstock/observability/)         │    │
│  │  logging.py  → loguru JSON sink + correlation_id contextvar      │    │
│  │  metrics.py  → prometheus_client Counter/Histogram/Gauge defs    │    │
│  │  tracing.py  → @observe decorator (timer + log + metric in one)  │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘

External (optional, pull-based):
   Prometheus scraper / Grafana → GET /metrics
   curl health checks            → GET /health/live, /health/ready
```

### Component Responsibilities

| Component | Responsibility | New / Modified | File(s) |
|-----------|----------------|----------------|---------|
| `CorrelationIdMiddleware` | Generate/propagate `X-Request-ID`, store in `contextvars.ContextVar` | NEW | `localstock/observability/middleware.py` |
| `RequestLoggingMiddleware` | Structured access log with request_id, status, duration_ms | NEW | same |
| `PrometheusMetricsMiddleware` | Increment `http_requests_total`, observe `http_request_duration_seconds` | NEW | same |
| `observability/logging.py` | Configure loguru JSON sink, register contextvar enricher | NEW | `localstock/observability/logging.py` |
| `observability/metrics.py` | Declare module-level Counter/Histogram/Gauge instances; expose registry | NEW | `localstock/observability/metrics.py` |
| `observability/tracing.py` | `@observe(name)` decorator combining timing + log + histogram | NEW | `localstock/observability/tracing.py` |
| `cache/backend.py` | `CacheBackend` Protocol + `InMemoryCache` impl + factory `get_cache()` | NEW | `localstock/cache/backend.py` |
| `cache/decorators.py` | `@cached(key, ttl, namespace)` for service methods | NEW | `localstock/cache/decorators.py` |
| `cache/keys.py` | Centralized key builders (`scores_ranking_v1`, `indicators:{symbol}:{date}`) | NEW | `localstock/cache/keys.py` |
| `validators/` | Pydantic models / functional checks for OHLCV, financials, news | NEW | `localstock/validators/` |
| `services/data_quality_service.py` | Run validators across latest crawl, write `data_quality_runs` row | NEW | `localstock/services/data_quality_service.py` |
| `db/repositories/quality_repo.py` | Persist quality run summaries + per-symbol issues | NEW | `localstock/db/repositories/quality_repo.py` |
| `services/pipeline.py` | Replace sequential symbol loops with `asyncio.gather` + `Semaphore`; emit per-step `pipeline_step_duration_seconds` histogram | MODIFIED | `localstock/services/pipeline.py` |
| `services/automation_service.py` | Wrap each phase with `@observe`; invalidate cache namespaces after write phases; trigger DataQualityService between crawl and score | MODIFIED | `localstock/services/automation_service.py` |
| `db/database.py` | Bump `pool_size` 3→10, `max_overflow` 5→10; expose `pool_status()` for /health/ready | MODIFIED | `localstock/db/database.py` |
| `db/repositories/*` | Add `@timed_query("repo.price.upsert")` decorator on hot methods; bulk insert via `INSERT … ON CONFLICT … DO UPDATE` | MODIFIED | repos with `upsert_*` methods |
| `api/routes/health.py` | Split into `/health/live`, `/health/ready`, `/health/pipeline`, `/health/data` | MODIFIED | `localstock/api/routes/health.py` |
| `api/routes/metrics.py` | Mount `prometheus_client.make_asgi_app()` at `/metrics` | NEW | `localstock/api/routes/metrics.py` |
| `scheduler/scheduler.py` | Add `cache_janitor` (TTL sweep) + `health_self_probe` jobs | MODIFIED | `localstock/scheduler/scheduler.py` |
| Alembic migrations | Indexes (BRIN on `(symbol, date)` for `stock_prices`; partial indexes), `data_quality_runs` table | NEW | `apps/prometheus/migrations/versions/` |

## Where Each Concern Hooks In (justified placement)

This is the heart of the research. For each cross-cutting concern, three placements were considered: **ASGI middleware**, **FastAPI `Depends`**, **service-layer decorator**. Choice depends on (1) what knows the cache key / metric label, (2) whether scheduler invocations bypass HTTP, (3) testability.

| Concern | Placement | Why not the alternatives |
|---------|-----------|--------------------------|
| **Correlation ID** | ASGI middleware (sets contextvar) + loguru patcher reads contextvar | `Depends` can't propagate to background tasks / scheduler jobs. Contextvar is the only mechanism that survives `asyncio.gather` and is visible in repository code without threading it through every call. |
| **HTTP request metrics** | ASGI middleware | Cleanest place to capture method/path/status uniformly. `Depends` runs *after* routing so it can't time pre-routing work. |
| **Service-method timing** | `@observe` decorator on service methods | Middleware sees only HTTP; scheduler-driven calls (daily pipeline) bypass HTTP entirely. Decorator works for both code paths. |
| **DB query timing** | Repository decorator `@timed_query` *and* SQLAlchemy `before_cursor_execute`/`after_cursor_execute` events | Repository decorator gives logical names (`repo.price.upsert_ohlcv`); engine events give a low-level fallback for ad-hoc queries. Use both — they emit to different histograms. |
| **HTTP response cache** (e.g., `/api/scores/ranking`) | Service-layer `@cached` (NOT response middleware) | A response-level cache key would need to encode every query param + auth state. Service-layer cache keys are explicit, invalidatable, and shared between HTTP and scheduler call sites (the pipeline pre-warms them). |
| **Computed-indicator cache** | Service layer (`AnalysisService.get_indicators`) | Indicators are derived data with a clear `(symbol, date)` key — perfect cache key. Repository layer too low (cache misses semantic meaning); middleware impossible (param-driven). |
| **Cache invalidation** | Explicit calls inside services at write boundaries + namespace TTL fallback | Event-bus invalidation is overkill for single-process. Direct calls (`cache.invalidate_namespace("scores")`) at the end of the scoring step in `pipeline.py` are simple and grep-able. TTL ensures correctness even if invalidation is forgotten. |
| **Data quality validation** | Pipeline step (between crawl and score) + per-record Pydantic validators in crawlers | Doing validation inside repositories couples persistence to business rules. Doing it only as a separate post-hoc job risks scoring on bad data. The split: hard schema/null checks in crawler (fail fast), statistical/anomaly checks as a pipeline step that flags but doesn't block. |
| **Scheduler-job metrics** | `@observe("scheduler.job.daily_pipeline")` wrapping the job function in `setup_scheduler()` | APScheduler has internal events but they're not async-aware enough; wrapping the job is uniform with service-method timing. |
| **Pool / connection metrics** | Gauge polled by `health_self_probe` scheduler job (every 30s) | Engine events fire too often; polling a gauge is cheap and matches Prometheus pull model. |

## Recommended Project Structure (additions only; existing layout preserved)

```
apps/prometheus/src/localstock/
├── api/
│   ├── app.py                      # MODIFIED: register new middlewares + /metrics route
│   └── routes/
│       ├── health.py               # MODIFIED: split into live/ready/pipeline/data
│       └── metrics.py              # NEW: mounts prometheus_client ASGI app
├── observability/                  # NEW package
│   ├── __init__.py
│   ├── logging.py                  # loguru JSON sink + contextvar enricher
│   ├── middleware.py               # CorrelationId, RequestLogging, PrometheusMetrics
│   ├── metrics.py                  # registry + module-level metric definitions
│   └── tracing.py                  # @observe decorator
├── cache/                          # NEW package
│   ├── __init__.py
│   ├── backend.py                  # Protocol + InMemoryCache + (optional) RedisCache
│   ├── decorators.py               # @cached(...)
│   └── keys.py                     # KeyBuilder, namespaces
├── validators/                     # NEW package
│   ├── __init__.py
│   ├── ohlcv.py                    # null/duplicate/monotonic-date/spike checks
│   ├── financials.py               # ratio sanity (PE>0, ROE in [-1,1], etc.)
│   └── news.py                     # url/date/encoding/dedup
├── services/
│   ├── pipeline.py                 # MODIFIED: parallelism, instrumentation
│   ├── automation_service.py       # MODIFIED: invalidation, DQ step, observe
│   └── data_quality_service.py     # NEW
├── db/
│   ├── database.py                 # MODIFIED: pool tuning, pool_status()
│   └── repositories/
│       ├── quality_repo.py         # NEW
│       └── *_repo.py               # MODIFIED: @timed_query decorators, bulk upserts
├── scheduler/
│   └── scheduler.py                # MODIFIED: + cache_janitor + health_self_probe
└── config.py                       # MODIFIED: cache_backend, redis_url, log_format,
                                    #           dq_enabled, pool_size override
```

### Structure Rationale

- **`observability/` as its own package** rather than scattered helpers: keeps logging/metrics/tracing concerns together, makes test mocking trivial (one import path), and matches the convention found in production FastAPI codebases (e.g., the `prometheus-fastapi-instrumentator` README example layout).
- **`cache/` separate from `observability/`**: caching is functional behavior with semantics (invalidation rules), not pure cross-cutting telemetry. Merging them would tangle correctness with measurement.
- **`validators/` separate from `crawlers/`**: same data may be validated in two contexts — at ingest time (crawler) and at audit time (`DataQualityService`). Shared module avoids duplication.
- **`services/data_quality_service.py` lives with other services** rather than at the top level: it *is* a service (orchestrates validators + repo writes), and the pipeline can import it like any other.

## Architectural Patterns

### Pattern 1: Service-Layer Cache with Explicit Invalidation

**What:** Hot read paths in services are wrapped in `@cached`; pipeline write phases call `cache.invalidate_namespace(...)` after committing. TTL acts as a safety net.

**When to use:** Any computation that (a) is read >5× per write, (b) has a stable key derivable from arguments, (c) tolerates seconds-to-minutes staleness. Examples: `/api/scores/ranking`, `/api/market/summary`, computed technical indicators per `(symbol, date)`.

**Trade-offs:** + Single, grep-able invalidation site per namespace; + works for both HTTP and scheduler call paths; + degrades gracefully if cache fails (just slower). − Forgetting to invalidate causes staleness until TTL expires (mitigated by short TTLs on volatile data).

**Example:**
```python
# localstock/services/scoring_service.py
from localstock.cache.decorators import cached
from localstock.cache.keys import RANKINGS_NS

class ScoringService:
    @cached(namespace=RANKINGS_NS, key="ranking:top:{top_n}", ttl=300)
    async def get_top_ranked(self, top_n: int = 50) -> list[ScoreRow]:
        return await self.score_repo.fetch_top(top_n)

# localstock/services/pipeline.py — after Step 5 (scoring) commits:
from localstock.cache.backend import get_cache
from localstock.cache.keys import RANKINGS_NS
await get_cache().invalidate_namespace(RANKINGS_NS)
```

### Pattern 2: Bounded-Parallel Crawl with Single Semaphore

**What:** Replace `for symbol in symbols: await crawl(symbol)` loops with `asyncio.gather` gated by a single `asyncio.Semaphore(N)`. N tuned per upstream (vnstock ≈ 6–8; news ≈ 4 to be polite).

**When to use:** Any pipeline step that fans out per-symbol over ~400 symbols where the bottleneck is upstream I/O latency, not local CPU.

**Trade-offs:** + 5–10× wall-clock speedup typical; + back-pressure built in. − Harder to reason about partial failures (mitigated by `return_exceptions=True` + per-symbol error logging); − can blow out DB pool if commits happen inside the gathered coroutines (mitigated by collecting results then committing serially, or using `pool_size ≥ N`).

**Example:**
```python
# localstock/services/pipeline.py
import asyncio

async def _crawl_prices(self, symbols: list[str]):
    sem = asyncio.Semaphore(self.settings.crawl_concurrency)  # default 8

    async def one(sym: str):
        async with sem:
            return sym, await self.price_crawler.fetch_one(sym)

    results = await asyncio.gather(*(one(s) for s in symbols), return_exceptions=True)
    ok, failed = {}, []
    for r in results:
        if isinstance(r, Exception):
            failed.append(str(r))
        else:
            sym, df = r
            ok[sym] = df
    # commit serially to avoid pool starvation
    for sym, df in ok.items():
        await self.price_repo.upsert_prices(sym, df)
    return ok, failed
```

### Pattern 3: Decorator Trio (`@observe`) — Timing + Log + Metric

**What:** A single decorator that, when applied to an async function, (1) starts a `loguru.contextualize` block with the function name and arguments, (2) records duration into a Prometheus `Histogram` keyed by the operation name, (3) increments a counter on success/failure.

**When to use:** Service methods, scheduler jobs, pipeline phases. Not on hot inner loops (overhead).

**Trade-offs:** + One annotation, three observability outputs aligned by name; + zero call-site noise. − Hides control flow slightly; − naming discipline required (use `domain.subsystem.action`).

**Example:**
```python
# localstock/observability/tracing.py
from functools import wraps
from time import perf_counter
from loguru import logger
from localstock.observability.metrics import op_duration, op_total

def observe(name: str):
    def deco(fn):
        @wraps(fn)
        async def wrapper(*a, **kw):
            t0 = perf_counter()
            with logger.contextualize(op=name):
                try:
                    out = await fn(*a, **kw)
                    op_total.labels(op=name, outcome="ok").inc()
                    return out
                except Exception:
                    op_total.labels(op=name, outcome="error").inc()
                    raise
                finally:
                    op_duration.labels(op=name).observe(perf_counter() - t0)
        return wrapper
    return deco
```

### Pattern 4: Validator-Then-Persist (Crawler) + Audit (Service)

**What:** Two-tier data quality. Tier 1 (synchronous, blocking): Pydantic + manual checks inside crawlers reject malformed rows before they reach the DB. Tier 2 (asynchronous, advisory): `DataQualityService` runs after each pipeline phase, computes per-symbol completeness/anomaly metrics, writes a `data_quality_runs` row, and emits Prometheus gauges (`dq_missing_ratio`, `dq_anomaly_count`).

**When to use:** Always for ingested external data; tier-2 is the basis for the health dashboard's "data freshness" panel.

**Trade-offs:** + Bad data never poisons scoring; + tier-2 gives historical visibility into data drift. − Two code paths for "validation"; mitigated by sharing validator functions across both tiers.

### Pattern 5: Pull-Based Self-Observability (no agent)

**What:** Process exposes `/metrics` (Prometheus exposition format) and `/health/{live,ready,pipeline,data}`. External Prometheus / Grafana / curl pulls. Internal scheduler job (`health_self_probe`, every 30 s) populates gauges that aren't naturally request-driven (DB pool size, last pipeline age, last successful crawl per symbol count).

**When to use:** Single-process apps where adding a sidecar agent (statsd, OpenTelemetry collector) is disproportionate to the value.

**Trade-offs:** + Zero new processes; + works fine for a personal-tool scale. − Restart loses counters (acceptable for daily-cycle workload); − no distributed tracing (acceptable — there's nothing to trace across).

## Data Flow

### HTTP Request Flow (with v1.5 layers)

```
client → uvicorn
     → CORSMiddleware
     → CorrelationIdMiddleware    [sets contextvar request_id]
     → RequestLoggingMiddleware   [logs entry]
     → PrometheusMetricsMiddleware [starts timer]
     → router → handler
            → Depends(get_session) → AsyncSession from pool
            → service.method()  ── @observe(...) starts timer
                  → cache.get(key)  HIT → return cached value
                                    MISS → repo.query()
                                          → @timed_query records db_query_duration
                                          → SQLAlchemy → asyncpg → Postgres
                                    ←   cache.set(key, value, ttl)
                  ── @observe(...) records duration + outcome
            ← handler returns response
     ← PrometheusMetricsMiddleware [observes http_request_duration]
     ← RequestLoggingMiddleware    [logs exit with status + duration]
client ← uvicorn
```

### Scheduled Pipeline Flow (with v1.5 layers)

```
APScheduler tick (15:45 VN, weekday)
     → daily_job() (in same event loop as HTTP)
        → @observe("scheduler.job.daily_pipeline")
        → AutomationService.run_daily_pipeline()
            ├─ Pipeline.run_full()                [@observe("pipeline.run_full")]
            │    ├─ stock_listings                [@observe("pipeline.step.listings")]
            │    ├─ crawl_prices PARALLEL N=8     [@observe("pipeline.step.prices")]
            │    │    └─ per-symbol: validators/ohlcv → repo.upsert (timed)
            │    ├─ crawl_financials PARALLEL     [@observe("pipeline.step.financials")]
            │    ├─ crawl_companies PARALLEL      [@observe("pipeline.step.companies")]
            │    └─ crawl_events                  [@observe("pipeline.step.events")]
            ├─ DataQualityService.run()  *NEW STEP*
            │    → compute completeness, anomalies → write data_quality_runs row
            │    → set gauges: dq_missing_ratio{stage="prices"}, dq_anomaly_count{...}
            ├─ AnalysisService.compute_indicators (parallel, semaphore-bounded)
            ├─ ScoringService.score_all
            │    → on commit: cache.invalidate_namespace("rankings")
            │    → on commit: cache.invalidate_namespace("market_summary")
            ├─ ReportService.generate_top_n
            └─ Notifier.send_digest
        → @observe records pipeline duration
        → PipelineRun row updated (existing behavior)
        → health_self_probe gauge `last_pipeline_age_seconds` reset to 0
```

### Cache Read/Write/Invalidate

```
READ:   service.get_X(args)
        → key = build_key("X", args)
        → cache.get(key)
            HIT  → record cache_hits_total{ns} → return
            MISS → record cache_misses_total{ns}
                 → value = repo.query(args)
                 → cache.set(key, value, ttl)
                 → return value

WRITE:  pipeline.step_X commits to DB
        → cache.invalidate_namespace(ns_for_X)
        → record cache_invalidations_total{ns}

JANITOR (scheduler, 60s):
        → InMemoryCache.sweep_expired() (cachetools handles lazily; explicit sweep
          avoids unbounded growth between accesses)
```

### State Management (server-side)

```
Process-local in-memory state (lost on restart, by design):
   • cachetools.TTLCache instance         (cache.backend)
   • prometheus_client default REGISTRY   (observability.metrics)
   • request_id contextvar                (observability.logging)
   • _pipeline_lock asyncio.Lock          (existing)

Persisted state (Postgres):
   • All domain tables (existing)
   • PipelineRun (existing)
   • data_quality_runs                    *NEW*
   • (optional) cache_warmup_keys table for cache pre-warming on boot
```

## Build Order (dependency-respecting)

Each step is independently shippable and unblocks specific later work. Numbers map to suggested phase ordering.

1. **Structured logging + correlation ID** — no upstream deps. Configures loguru JSON sink, adds `CorrelationIdMiddleware`. *Unblocks:* every later step gets useful logs from day one. Smallest PR.
2. **Metrics primitives + `/metrics` endpoint** — depends on #1 (so failures are debuggable). Adds `prometheus_client`, declares core metrics (`http_*`, `op_*`, `cache_*`, `db_query_*`, `pipeline_step_*`, `dq_*`), mounts `/metrics`. No instrumentation yet — just the registry.
3. **HTTP middleware instrumentation** — depends on #2. Adds `PrometheusMetricsMiddleware` + `RequestLoggingMiddleware`. After this, `/metrics` is meaningful for HTTP traffic.
4. **`@observe` decorator + repository `@timed_query`** — depends on #2. Apply selectively to pipeline phases and hottest repo methods (price upsert, score upsert). Now scheduler-driven work is also visible.
5. **Expanded `/health/*` endpoints + `health_self_probe` job** — depends on #4 (uses gauges populated by instrumentation). This is when you get a real "is the system OK?" signal.
6. **Cache backend + `@cached` decorator (in-memory only)** — depends on #4 (needs metrics for hit/miss). No invalidation logic yet — just TTL. Apply to 1–2 hot read endpoints first (rankings, market summary).
7. **Cache invalidation hooks at pipeline boundaries** — depends on #6. Add `invalidate_namespace` calls in `pipeline.py` and `automation_service.py`. Now caches can be more aggressive (longer TTLs).
8. **Validators + `DataQualityService` + `data_quality_runs` table** — depends on #4 (so DQ runs are observable). Run as new pipeline step between crawl and score. Tier-1 crawler validators can land in same PR or earlier.
9. **Crawler parallelism (semaphore + `asyncio.gather`)** — depends on #4 to *measure* the win, and on #8 so bad data from parallel races is caught. Bump `pool_size` 3→10 in same PR.
10. **Repository batching (`INSERT … ON CONFLICT`, bulk upserts)** — depends on #4 to spot the slow queries. Targets identified by `db_query_duration_seconds` p95.
11. **DB indexes (Alembic migration)** — depends on #4 + #10 (you need traffic profile to pick indexes). Start with BRIN on `stock_prices(symbol, date)` (cheap, large table); add partial indexes for hot WHERE clauses surfaced by query timing.
12. **Optional: Redis backend behind `CacheBackend` Protocol** — only if memory pressure or process-restart cache loss becomes painful. Single config flag flip; no other code changes.

**Critical dependency rules:**
- Logging (#1) before anything that emits logs you'll want to grep.
- Metrics primitives (#2) before any instrumentation (#3, #4).
- HTTP middleware (#3) and decorator instrumentation (#4) before health dashboard (#5) — the dashboard reads what they emit.
- Cache backend (#6) before invalidation (#7) — obvious.
- Instrumentation (#4) before performance work (#9, #10, #11) — *measure first*; otherwise you're guessing what to optimize.
- Data quality (#8) before/with parallelism (#9) — parallel crawling can amplify silent corruption; DQ catches it.

## Scaling Considerations

The scaling axis here is **#stocks tracked × pipeline frequency**, not concurrent users (single-user app).

| Scale | Pipeline target | Architecture adjustments |
|-------|-----------------|--------------------------|
| ~400 HOSE stocks, 1×/day (today) | <15 min wall-clock | In-memory cache, semaphore=8, BRIN indexes — sufficient |
| ~1500 stocks (HOSE+HNX+UPCOM, future v2) | <30 min | Bump semaphore to 12, switch indicators to NumPy-vectorized batch, add `stock_prices` partition by year |
| Intraday refresh (every 30 min during market) | <5 min per cycle | Move heavy AI report generation off the hot path (queue locally — still single process, asyncio queue), Redis cache for cross-cycle sharing if multi-process worker added |
| Multi-process (uvicorn `--workers > 1`) | n/a | **Avoid until necessary.** Would require: Redis cache (in-memory no longer shared), `prometheus-client` multiprocess mode (`PROMETHEUS_MULTIPROC_DIR`), APScheduler with external job store (PostgreSQLJobStore) or a dedicated worker process |

### Scaling Priorities (what breaks first, in order)

1. **Crawl wall-clock time** — sequential per-symbol loop. Fix: Pattern 2 (semaphore + gather). *This is the #1 win for v1.5.*
2. **DB write throughput during pipeline** — many round-trips per symbol. Fix: bulk `INSERT … ON CONFLICT` in repositories.
3. **Read latency on `/api/scores/ranking` and similar** — recomputed/scanned each request. Fix: service-layer cache (Pattern 1).
4. **JSONB query cost on `financial_statements.content_json` / `stock_reports.content_json`** — full-table scans. Fix: GIN index on the queried JSON paths, or extract hot fields into typed columns.
5. **Time-series queries on `stock_prices`** — already keyed by (symbol, date) but no time-range index optimization. Fix: BRIN index on `date`, composite btree on `(symbol, date DESC)` for "latest N rows per symbol".

## Anti-Patterns

### Anti-Pattern 1: Response-Level HTTP Cache Middleware

**What people do:** Drop in a generic ASGI cache middleware that hashes URL+headers and stores responses.
**Why it's wrong:** Cache key has no domain semantics, can't be invalidated when the daily pipeline updates scores, and becomes stale silently. Also misses scheduler-driven warm-up opportunities.
**Do this instead:** Cache at the service method (Pattern 1). HTTP handlers stay thin; cache is shared between API and scheduler call paths; invalidation is one explicit call per write boundary.

### Anti-Pattern 2: Scattered `time.time()` Logging Instead of Metrics

**What people do:** Sprinkle `t0 = time.time(); …; logger.info(f"took {time.time()-t0}s")` through services.
**Why it's wrong:** Logs aren't aggregable into percentiles, can't drive alerts, and pollute output. Also lost on log rotation.
**Do this instead:** `@observe` decorator (Pattern 3). One annotation gives histogram (p50/p95/p99 derivable), counter, and a contextualized log line — all at once.

### Anti-Pattern 3: Redis-by-Default for "Future-Proofing"

**What people do:** Add Redis to the stack "in case we need it later," requiring users to run a second service.
**Why it's wrong:** Violates local-first/single-process constraint. Single-user app gets nothing from Redis until #workers > 1, which itself isn't planned. Adds an operational failure mode.
**Do this instead:** `CacheBackend` Protocol with `InMemoryCache` default. Redis adapter exists in code but is opt-in via config. Zero infrastructure cost today, two-line flip if needed tomorrow.

### Anti-Pattern 4: Validating in Repositories

**What people do:** Put data quality checks in `PriceRepository.upsert_prices` because "that's where data lands."
**Why it's wrong:** Couples persistence to evolving business rules; hard to test validation without DB; can't differentiate "reject row" vs "flag for audit."
**Do this instead:** Pattern 4 — synchronous Pydantic/manual validators in *crawlers* (reject before persist), plus advisory `DataQualityService` that runs as a pipeline step and writes audit rows. Repositories stay dumb.

### Anti-Pattern 5: Indexing Everything in One Big Migration

**What people do:** Generate a migration with indexes on every column "for performance."
**Why it's wrong:** Doubles write cost on the pipeline (every insert maintains every index), bloats DB on Supabase free tier, and most indexes are never used.
**Do this instead:** Drive index creation from `db_query_duration_seconds` p95 outliers (instrumentation step #4). Add one index, measure, repeat. Prefer BRIN over btree for monotonic time-series columns.

### Anti-Pattern 6: APScheduler Background Tasks That Block the Event Loop

**What people do:** Add a CPU-heavy job to APScheduler (e.g., bulk indicator computation in pure Python loops).
**Why it's wrong:** APScheduler runs in the same event loop as FastAPI HTTP handlers — a long sync section freezes the API.
**Do this instead:** For CPU-bound work in a scheduled job, dispatch to `asyncio.to_thread(...)` (or `loop.run_in_executor`) and `await` it. For very heavy computation (rare in v1.5), reach for `ProcessPoolExecutor` — but note the data shipping cost.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Postgres (Supabase) | Async SQLAlchemy + asyncpg, single pool singleton | Disable statement cache (already done — pgbouncer transaction mode requires it). Bump pool when increasing crawler concurrency. |
| Prometheus / Grafana (optional, external) | Pull from `/metrics` exposition endpoint | No agent inside process; user runs Prometheus container or `node_exporter`-style scrape if desired. |
| vnstock upstream | HTTP via `httpx` inside crawlers | Bound concurrency at semaphore=8 (verify rate limit empirically — flag for runtime tuning). |
| Ollama (local) | HTTP via `ollama` SDK | Single-flight per symbol report (already enforced). Adding cache only at *prompt-input* level is risky — outputs are non-deterministic; do NOT cache LLM responses unless a deterministic-prompt mode is established. |
| Telegram | python-telegram-bot HTTP | Unchanged. Wrap send in `@observe("notif.telegram.send")`. |

### Internal Boundaries

| Boundary | Communication | v1.5 considerations |
|----------|---------------|---------------------|
| API ↔ Service | function call within same loop | New `Depends(get_cache)` for routes that want to invalidate cache directly |
| Service ↔ Repository | function call, AsyncSession passed via constructor | Repos gain `@timed_query`; signatures unchanged |
| Service ↔ Cache | `await cache.get/set/invalidate_namespace` via `get_cache()` factory | New boundary; cache is process-singleton |
| Service ↔ Validators | pure function call (no IO) | Validators take dataframes/dicts, return `(clean, issues)` tuples |
| Pipeline ↔ DataQualityService | direct call (new pipeline step) | DQ writes its own row; doesn't mutate domain tables |
| Scheduler ↔ Service | direct call inside lifespan-bound loop | Wrap job functions in `@observe`; never block the loop |
| HTTP middleware ↔ Service | contextvar (request_id) | Logger reads contextvar automatically; no parameter threading |

## Sources

- Existing repo files (verified by reading): `apps/prometheus/src/localstock/api/app.py`, `scheduler/scheduler.py`, `db/database.py`, `services/pipeline.py`, `services/automation_service.py`, `api/routes/health.py`, `config.py`, `pyproject.toml` — confidence HIGH.
- FastAPI lifespan + middleware ordering semantics — official FastAPI advanced/middleware docs (training data, cross-checked against repo's existing usage) — confidence HIGH.
- APScheduler `AsyncIOScheduler` event-loop binding requirements — APScheduler 3.x docs — confidence HIGH (consistent with current `scheduler/scheduler.py` pattern).
- `prometheus-client` Python library exposition pattern + `make_asgi_app()` — official `prometheus/client_python` README — confidence HIGH.
- `cachetools.TTLCache` thread-safety considerations (needs external lock for concurrent async access) — cachetools docs — confidence MEDIUM (verify with a small test before relying on lock-free use).
- Postgres BRIN index suitability for monotonic timestamp/date columns on large tables — PostgreSQL official docs (Indexes / BRIN) — confidence HIGH.
- pgbouncer transaction-mode + asyncpg `statement_cache_size=0` requirement — already encoded in `db/database.py`; confirms Supabase pooler behavior — confidence HIGH.
- Loguru `contextualize` + contextvars interaction for ASGI — loguru docs + community patterns — confidence MEDIUM (needs verification that the loguru patcher reads the contextvar across `asyncio.gather` boundaries — flag for runtime check).

---
*Architecture research for: LocalStock v1.5 Performance & Data Quality milestone*
*Researched: 2026-04-29*
