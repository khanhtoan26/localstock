# Feature Research

**Domain:** Single-user local-first data pipeline backend (FastAPI + Postgres + APScheduler) — v1.5 Performance & Data Quality
**Researched:** 2026-04-28
**Confidence:** HIGH (well-established production patterns; scope filtered to single-user local context)

## Scoping Premise

Three facts gate every recommendation below:

1. **Single user, single host.** No multi-tenant, no horizontal scaling, no SLO contract.
2. **Daily batch cadence.** Pipeline runs ~once/day after 15:30 close; ~400 HOSE stocks. Latency budgets are minutes, not milliseconds.
3. **Existing stack is uvicorn + APScheduler in one process + Postgres (Supabase free tier) + Ollama on same host.** No Redis, no message broker, no metrics backend deployed.

Anything that assumes "distributed system", "high QPS", or "many engineers on-call" is anti-feature territory.

---

## Feature Landscape

### Table Stakes (must-have for production-quality reliability)

| Feature | Why Expected | Complexity | Notes / Dependencies |
|---|---|---|---|
| **Structured JSON logging via loguru sinks** | Already using loguru; without JSON output, grep is the only debug tool. Production debugging table stakes. | LOW | Add `serialize=True` sink to file with rotation. Existing `logger.info(...)` calls work as-is. Dep: loguru (in stack). |
| **Request ID / correlation ID middleware** | Cross-cutting trace from API request → service → DB query → log line. Single field (`request_id`) is enough; full OpenTelemetry is overkill. | LOW | FastAPI middleware that sets `contextvars.ContextVar`, loguru patcher includes it in every record. Dep: FastAPI app factory in `api/`. |
| **Pipeline run trace ID** | Same idea for scheduled jobs — every log line during a `PipelineRun` should carry its `run_id`. Today logs are anonymous. | LOW | Wrap `AutomationService.run_daily_pipeline` in `logger.contextualize(run_id=...)`. Dep: `PipelineRun` model exists. |
| **`/health` deep check (DB + Ollama + last run age)** | Current `/health` only counts rows. "Healthy" should mean "DB reachable, Ollama responding, last pipeline ran within 24h". | LOW | Extend existing `routes/health.py`. Add `/health/live` (process up) vs `/health/ready` (deps OK). Dep: `routes/health.py`, Ollama client. |
| **Stale-data detection / freshness endpoint** | "Why is the dashboard wrong?" → because crawl failed 3 days ago and nobody noticed. Surface `max(price.date)` per stock and flag staleness. | LOW | New `/health/data-freshness` endpoint or extend existing. Compare `MAX(date)` to today minus weekends/holidays (existing `hose-session.ts` logic on backend). Dep: `StockPrice`, calendar logic. |
| **Slow query logging** | Postgres has `log_min_duration_statement`; SQLAlchemy has `engine.echo` + event listeners. Without it, Supabase free-tier slowdowns are invisible. | LOW | SQLAlchemy `before_cursor_execute` / `after_cursor_execute` events → log queries > 500ms with bound params. Dep: `db/database.py`. |
| **Pipeline retries with exponential backoff (per-stock)** | `vnstock` rate-limits and times out. One bad stock should not fail the whole batch; retry 3× with backoff. | LOW–MED | `tenacity` library on crawler call sites. Per-stock try/except already partially exists; formalize. Dep: `crawlers/`. |
| **Per-stock failure isolation + summary** | A `PipelineRun` should record `succeeded: 387, failed: 13, skipped: 0` and the failed symbols, not just `status='completed'`. | LOW | Extend `PipelineRun` with `stats` JSONB column or new `PipelineRunStockResult` table. Dep: `db/models.py` + Alembic migration. |
| **Missing OHLCV / NaN ratio detection on ingest** | Validate after crawl: `(NaN_count / row_count) > threshold` → flag, do not score. Today garbage flows downstream into indicators. | MED | Validation step between crawl and analyze in `AutomationService`. Reject stocks with > N% missing in trailing window. Dep: `analysis/`, `crawlers/`. |
| **Anomaly detection on prices (sanity bounds)** | `close = 0`, price jump > 30% (excluding splits), volume = 0 on a trading day. Cheap rules catch source-data corruption. | LOW–MED | Validation function on `StockPrice` rows post-crawl. Log + skip + flag. Dep: `analysis/` or new `validation/` module. |
| **Indexes on hot query paths** | `stock_prices(symbol, date DESC)`, `pipeline_runs(started_at DESC)`, `stock_scores(date, symbol)`. Single-column scans on 400 stocks × 2 years OHLCV = ~200k rows is fine; wrong indexes still cause sequential scans on dashboard load. | LOW | Audit current indexes (Alembic migrations) → add composite indexes via new migration. Dep: Alembic, model relationships. |
| **In-memory caching for computed indicators (request scope)** | `RSI(VNM, 14)` is recomputed on every dashboard load. Cache by `(symbol, indicator, params, as_of_date)` for the request lifetime — no Redis needed. | LOW–MED | `functools.lru_cache` won't work (async + DB inputs); use `cachetools.TTLCache` keyed by `(symbol, date)` at service layer. Dep: `analysis/`, `scoring/`. |
| **API response cache for read-heavy GETs (TTL-based)** | `GET /api/scores`, `/api/market/summary`, `/api/sectors` — content changes once/day. Serve from in-process TTL cache (5–30 min) instead of hitting DB on every dashboard refresh. | LOW | `fastapi-cache2` with `InMemoryBackend` OR plain `cachetools` decorator. Existing frontend already uses `staleTime` (v1.3 decision). Dep: `api/routes/`. |
| **Cache invalidation on pipeline completion** | When daily pipeline finishes, flush API + indicator caches. Otherwise dashboard shows stale data until TTL expires. | LOW | `AutomationService.run_daily_pipeline` calls `cache.clear()` on success. Single-process makes this trivial — anti-pattern only at scale. Dep: cache module + automation service. |
| **Request log middleware (method, path, status, duration_ms)** | One log line per request with timing. Cornerstone for "is the dashboard slow because API or frontend?" | LOW | FastAPI middleware. Combines with request ID from above. Dep: API app factory. |

### Differentiators (meaningfully improves debug/perf, worth doing)

| Feature | Value Proposition | Complexity | Notes / Dependencies |
|---|---|---|---|
| **Concurrent crawl with bounded `asyncio.Semaphore`** | Sequential crawl of 400 stocks @ ~1s each = ~7 min. With concurrency 8–16, can drop to ~1 min. Respects vnstock rate limits via semaphore. | MED | Refactor crawler loop in `AutomationService` to `asyncio.gather` with `Semaphore(N)`. Tune N empirically. Dep: `crawlers/`, `automation_service.py`. **Risk:** vnstock rate-limit; need backoff already covered above. |
| **Parallel indicator computation (process pool for CPU-bound)** | pandas-ta over 400 stocks × 11 indicators is CPU-bound. `concurrent.futures.ProcessPoolExecutor` distributes across cores. RTX 3060 host likely has 6+ cores. | MED | Per-stock indicator calc is embarrassingly parallel. Pickle-safe inputs (DataFrame). Dep: `analysis/indicators.py`. **Watch:** Postgres connection pool not shared across processes — compute first, write back in main process. |
| **Pipeline metrics in DB (durations per stage)** | Extend `PipelineRun` with `crawl_duration_ms`, `analyze_duration_ms`, `score_duration_ms`, `report_duration_ms`. Trend chart on admin console answers "why is pipeline slow tonight?". | LOW | Schema change + timing wraps in `AutomationService`. Dep: `PipelineRun` model, admin UI. |
| **Health/observability dashboard page (admin)** | Single page: last 30 pipeline runs (status + per-stage durations), data freshness per stock, crawl failure histogram, slow-query top-10. Exists in DB after table-stakes work — UI is the multiplier. | MED | New `/admin/observability` Next.js page consuming new `/api/admin/observability/*` endpoints. Dep: admin console (v1.2 infra exists). |
| **Backfill command for missing OHLCV** | When data quality detection flags a stock, expose `localstock backfill --symbol VNM --from 2026-01-01`. CLI + admin button. | MED | Reuse crawler with date range. Idempotent upsert on `(symbol, date)`. Dep: `crawlers/`, admin API. |
| **Postgres `EXPLAIN ANALYZE` capture for slow queries** | Slow query logging logs the SQL; capturing the plan once is what actually tells you "missing index". Run `EXPLAIN (ANALYZE, BUFFERS)` and store with the slow log entry. | MED | One-off tool, not on hot path. Run manually from admin or scheduled weekly. Dep: `db/database.py` + admin route. |
| **Prometheus-format `/metrics` endpoint (single-instance)** | If user later wants to point Grafana at it, the data is there. `prometheus-client` library, in-process registry, exposes counters (pipeline_runs_total, http_requests_total) and histograms (request_duration). | MED | `prometheus-fastapi-instrumentator` package. Optional consumer; cost is one route + small RAM. Dep: FastAPI app factory. **Caveat:** marginal value with 1 user — keep behind feature flag. |
| **GIN index on `report.content_json`** | If admin queries reports by JSONB key (e.g. "all reports flagging risk_rating=high"), a GIN index makes JSONB containment fast. Otherwise sequential scan. | LOW | Single Alembic migration. Only worth it if such queries exist or are planned. Dep: `Report` model, JSONB column. |
| **Indicator result table (cache as data, not memory)** | Persist computed indicators in `stock_indicators(symbol, date, name, value)` after pipeline run. Dashboard reads directly. Avoids recomputing on every API call AND survives process restart. | MED | New table + Alembic migration + write step in pipeline + read path in `analysis_service`. Dep: analysis layer. **Trade-off:** more I/O at write time, much faster reads. Probably the right answer over in-memory cache once schema lands. |
| **Crawler "last successful fetch" per stock** | `stocks.last_crawled_at` column. Drives "stale stock" detection and prioritized re-crawl ordering. | LOW | Schema + update in crawler. Dep: `Stock` model. |

### Anti-Features (overkill for single-user local app)

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Distributed tracing (OpenTelemetry + Jaeger/Tempo)** | "Production observability checklist" articles list it. | One process, no inter-service hops. Setup cost (collector, backend, sampler config) >> debug value. | Request ID + structured logs cover 100% of single-process tracing needs. |
| **Redis as caching layer** | Standard answer to "add caching". | Adds a service to install, monitor, and persist. Single-process FastAPI can hold an in-memory dict that does the same job. | `cachetools.TTLCache` in-process. Was already a v1.0 decision: "APScheduler instead of Celery/Redis". Stay consistent. |
| **Message broker (RabbitMQ / Kafka) + Dead-Letter Queue** | "Pipeline reliability" pattern from microservices. | Daily batch on one host has no queue. Failure mode is "scheduler logs an error" or "row in `pipeline_runs` with status=failed". | Persist failed-stock list in `PipelineRunStockResult`; manual or scheduled retry job re-reads it. That IS the DLQ for this scale. |
| **Time-series partitioning (Postgres declarative partitioning) on `stock_prices`** | "OHLCV is time-series, partition by month/year." | 400 stocks × 252 trading days/yr × ~5 years = ~500k rows. Postgres handles 10M rows on a single B-tree without complaint. Partitioning adds maintenance overhead (creating new partitions, constraint exclusion gotchas, ATTACH PARTITION) for zero query benefit at this scale. | Composite index `(symbol, date DESC)`. Revisit partitioning at >50M rows. |
| **BRIN indexes for OHLCV** | "BRIN is great for time-ordered data." | BRIN wins on huge sequentially-inserted tables (>10M rows) where range scans dominate. At 500k rows, B-tree is faster and smaller relative to the gain. Most queries are `WHERE symbol = ? AND date >= ?` — point-style on symbol, range on date — exactly the B-tree composite case. | Composite B-tree on `(symbol, date)` — already an industry standard for this access pattern. |
| **Full Prometheus + Grafana + Alertmanager stack** | "If you're not graphing it, it's not real." | Three more services to install, configure, secure on a single-user host. Most metrics only matter when you're staring at the dashboard manually anyway. | Optional `/metrics` endpoint (differentiator above) + admin observability page reading from Postgres. |
| **Sentry / external error tracking** | Standard error tracking. | Sends data off-machine — violates project's "data sovereignty / fully local / free" posture. | loguru file sink with rotation + admin error log viewer. |
| **APScheduler with persistent job store (PostgresJobStore / SQLAlchemyJobStore)** | "Persist jobs across restarts." | One cron job (daily pipeline) and one interval job (admin worker). Both are re-registered at startup from code. Persistence buys nothing here. | Keep `MemoryJobStore` (default). Document re-register-on-startup as the contract. |
| **Per-endpoint rate limiting** | Standard API hardening. | Single user on localhost. Rate limit of self by self is theater. | Skip. CORS already restricts origins (v1.0 decision). |
| **Background task queue for AI report generation (Celery/RQ/Arq)** | "Long-running tasks should be off the request thread." | Already off the request thread — admin job worker polls DB and runs in scheduler. That pattern (DB-as-queue) is fine for 1–10 jobs/day. | Keep current admin_job_worker pattern; just add backoff + retry counts to existing `AdminJob` table. |
| **Read replica / connection pool tuning for read scaling** | "Scale reads." | One user. The "read load" is one browser tab on a Next.js dashboard. Default `asyncpg` pool sizing is fine. | Index correctly; cache responses; done. |
| **Multi-level cache (L1 memory + L2 Redis + L3 CDN)** | Standard at scale. | All three of: no second process to share L2, no edge to put L3, latency already dominated by Ollama generation not data fetch. | Single in-process TTL cache. |

---

## Feature Dependencies

```
[Request ID middleware]
    └──enables──> [Structured JSON logging with correlation]
    └──enables──> [Request log middleware (timing)]
                       └──enables──> [Slow query logging value increases]

[Pipeline run trace ID]
    └──enables──> [Per-stage durations on PipelineRun]
                       └──enables──> [Health/observability dashboard]

[PipelineRunStockResult table]
    └──enables──> [Per-stock failure isolation + summary]
    └──enables──> [Backfill command targeting failed stocks]
    └──enables──> [Retry-failed-stocks job (DLQ-equivalent)]

[Indicator result table]
    └──replaces──> [In-memory indicator cache] (better long-term answer)
    └──requires──> [Cache invalidation on pipeline completion]

[Anomaly detection on prices]
    └──requires──> [Per-stock failure isolation] (so flagged stocks don't fail run)
    └──enables──> [Stale-data / quality dashboard]

[Composite indexes (symbol, date)]
    └──prerequisite for──> [Slow query logging being actionable]
    └──conflicts with──> [Time-series partitioning] (anti-feature; keep B-tree)

[Concurrent crawl with Semaphore]
    └──requires──> [Pipeline retries with exponential backoff] (concurrency amplifies rate-limit risk)
    └──requires──> [Per-stock failure isolation]

[Cache invalidation on pipeline completion]
    └──requires──> [API response cache] AND [Indicator cache or table]
```

### Dependency Notes

- **Request ID is the foundation.** Every observability feature gets ~10× more useful when log lines are correlatable. Land it first.
- **Per-stock failure isolation unlocks half the data-quality work.** Once one stock can fail without nuking the run, anomaly detection, backfill, and retry-failed all become small features instead of risky ones.
- **Indicator cache vs. indicator table is a fork.** TTLCache is faster to ship; persisted table is the better long-term answer because it survives restarts and removes recomputation entirely. Recommend: ship TTLCache in early phase, then migrate to table once schema stabilizes. Don't ship both permanently.
- **Indexes before slow-query logging is wrong order.** Add slow-query logging first, *let it tell you* which queries need indexes, then add. Otherwise you index by guesswork.
- **Concurrent crawl is gated on retry/backoff.** Without retry, concurrency just makes rate-limit failures hit faster.

---

## MVP Definition

### Launch With (v1.5 P1 — table stakes)

- [ ] **Request ID + pipeline run ID propagation** — foundation for all observability
- [ ] **Structured JSON logging (loguru serialize sink)** — debuggable production logs
- [ ] **Request log middleware (method/path/status/duration)** — answer "is API slow?"
- [ ] **Slow query logging via SQLAlchemy events** — answer "is DB slow?"
- [ ] **`/health` deep check (DB + Ollama + freshness)** — single endpoint says "system is OK or not"
- [ ] **Stale-data detection endpoint** — surface "crawl hasn't run in 3 days" without manual SQL
- [ ] **Per-stock failure isolation + `PipelineRun.stats` JSONB** — bad stocks don't fail the batch
- [ ] **Pipeline retries with `tenacity` (exp backoff, 3 tries)** — vnstock flakiness handled
- [ ] **Missing-OHLCV / NaN-ratio validation gate** — garbage doesn't reach scoring
- [ ] **Price anomaly detection (zero/jump/zero-volume rules)** — source corruption caught
- [ ] **Composite indexes on hot paths** — `(symbol, date)`, `pipeline_runs(started_at)`, etc.
- [ ] **In-process API response cache (TTL) + invalidation on pipeline complete** — dashboard responsive
- [ ] **In-process indicator cache (TTL)** — short-term win before persisted table

### Add After Validation (v1.5 P2 — differentiators)

- [ ] **Concurrent crawl with `asyncio.Semaphore`** — once retry/backoff proven solid
- [ ] **Per-stage timing on `PipelineRun`** — feeds dashboard
- [ ] **Admin observability dashboard page** — pulls together all metrics
- [ ] **Backfill command (CLI + admin button)** — when missing-data flags accumulate
- [ ] **Persisted indicator result table** — replaces in-memory cache long-term
- [ ] **Crawler `last_crawled_at` per stock** — feeds stale detection at finer grain

### Future Consideration (v2+)

- [ ] **Parallel indicator computation via ProcessPoolExecutor** — only if v1.5 timings show CPU bound after concurrent crawl lands
- [ ] **Prometheus `/metrics` endpoint** — only if user actually wants to wire Grafana
- [ ] **GIN index on `report.content_json`** — only if JSONB queries become a pattern
- [ ] **`EXPLAIN ANALYZE` capture for top slow queries** — useful but manual one-offs suffice initially

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| Request ID + run ID propagation | HIGH (unlocks all debugging) | LOW | P1 |
| Structured JSON logging | HIGH | LOW | P1 |
| `/health` deep check | HIGH | LOW | P1 |
| Stale-data detection | HIGH | LOW | P1 |
| Per-stock failure isolation | HIGH | LOW | P1 |
| Pipeline retries (tenacity) | HIGH | LOW | P1 |
| Slow query logging | HIGH | LOW | P1 |
| Composite indexes (hot paths) | HIGH | LOW | P1 |
| Missing-OHLCV / NaN validation | HIGH | MEDIUM | P1 |
| Price anomaly detection | MEDIUM–HIGH | LOW | P1 |
| API response cache (TTL) | HIGH | LOW | P1 |
| Cache invalidation on pipeline complete | HIGH | LOW | P1 |
| Indicator cache (in-memory, TTL) | MEDIUM | LOW–MEDIUM | P1 |
| Request log middleware | HIGH | LOW | P1 |
| Concurrent crawl with semaphore | HIGH (5–7× faster) | MEDIUM | P2 |
| Per-stage durations on PipelineRun | MEDIUM | LOW | P2 |
| Admin observability dashboard | HIGH | MEDIUM | P2 |
| Backfill command | MEDIUM | MEDIUM | P2 |
| Persisted indicator table | MEDIUM | MEDIUM | P2 |
| Crawler `last_crawled_at` | MEDIUM | LOW | P2 |
| Parallel indicator computation | LOW–MEDIUM (only if CPU bound) | MEDIUM | P3 |
| Prometheus `/metrics` endpoint | LOW (no consumer yet) | MEDIUM | P3 |
| GIN index on JSONB | LOW (no query pattern yet) | LOW | P3 |
| EXPLAIN ANALYZE capture | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.5 — table stakes for production-quality reliability
- P2: Should have, ship in later phase of v1.5 once P1 is stable
- P3: Nice to have, defer to v1.6+ unless cheap

---

## Industry Pattern Cross-Reference

| Pattern | Industry Default (microservices) | Our Approach (single-user local) | Why Different |
|---|---|---|---|
| Distributed tracing | OpenTelemetry + Jaeger | Request ID in loguru context | One process — full tracing has no spans to connect |
| Cache layer | Redis | `cachetools.TTLCache` in-process | One process can share dict; Redis is service overhead |
| DLQ | RabbitMQ DLQ / Kafka topic | `PipelineRunStockResult` table with `status='failed'` | Postgres IS the queue at this scale |
| Metrics | Prometheus exporter | Postgres rows + admin dashboard | Optional `/metrics` for opt-in users |
| Time-series storage | TimescaleDB / partitioned tables | Plain Postgres with composite B-tree | 500k rows — partitioning is premature |
| Slow query analysis | pg_stat_statements + Datadog | SQLAlchemy event listener + log file | Free, in-stack, sufficient |
| Error tracking | Sentry | loguru rotating file sink | Data sovereignty constraint |
| Job queue | Celery + Redis broker | APScheduler + DB-polling worker | v1.0 explicit decision — preserved |

---

## Sources

- Project context: `.planning/PROJECT.md` (v1.5 milestone goals, v1.0 decision to use APScheduler not Celery)
- Codebase: `apps/prometheus/src/localstock/api/routes/health.py`, `scheduler/scheduler.py`, `db/models.py`
- FastAPI middleware patterns: official FastAPI docs (middleware, lifespan)
- loguru `serialize=True` JSON output: loguru official docs
- SQLAlchemy `before_cursor_execute` event for slow query logging: SQLAlchemy 2.x docs
- tenacity for retry/backoff: official tenacity docs
- APScheduler `MemoryJobStore` vs persistent stores: APScheduler 3.x docs
- Postgres index strategy for OHLCV (B-tree composite over BRIN at <10M rows): Postgres docs + general DB community consensus
- Anti-feature framing for distributed tracing/Redis/partitioning at single-host scale: ecosystem consensus that infrastructure cost must match scale (HIGH confidence based on widely-published patterns; MEDIUM confidence on exact thresholds — they're judgment calls)

---
*Feature research for: LocalStock v1.5 Performance & Data Quality*
*Researched: 2026-04-28*
