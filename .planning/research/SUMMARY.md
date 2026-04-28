# Project Research Summary — LocalStock v1.5 Performance & Data Quality

**Project:** LocalStock (AI Stock Agent for HOSE)
**Domain:** Single-user, local-first analytics backend — FastAPI + async SQLAlchemy + Supabase Postgres + APScheduler (in-process) + Ollama
**Milestone:** v1.5 — pipeline performance, caching, observability, data quality, DB optimization
**Researched:** 2026-04-29
**Confidence:** HIGH

## Executive Summary

v1.5 is a **reliability and instrumentation milestone** layered on a working v1.4 system. Across all four research files the conclusion converges: this is *not* a distributed-systems problem. It is a single-process FastAPI app with one in-loop APScheduler, ~400 HOSE symbols, one daily mutation cliff at 15:45 VN, and one user. The right shape is **measure first, then optimize**: structured logs + correlation IDs + a pull-based `/metrics` endpoint go in before anyone touches caching or parallelism, because every later phase becomes guesswork without them.

The recommended stack is intentionally tiny — six pure-Python libraries, zero new runtime services. `cachetools` (in-memory TTL) + `diskcache` (persistent SQLite-backed) cover caching without Redis; `hishel` adds RFC 9111 caching to the existing httpx clients; `pandera` validates DataFrames at I/O boundaries; `prometheus-client` + `prometheus-fastapi-instrumentator` expose `/metrics` with no agent. Loguru stays (we already have it) — JSON serialization + `contextualize()` is enough; no `structlog` migration. DB optimization is patterns-only (Alembic indexes, SQLAlchemy event-based slow-query log, pool tuning 3→10) — no new dependency.

The dominant risks are not technological — they are **ordering and discipline risks**. Caching without `pipeline_run_id` in the key serves yesterday's ranks until TTL expires (Pitfall 1). Cache stampede on cold start exhausts the small async pool (Pitfall 2). `asyncio.gather` over 400 sync `pandas-ta` calls is *zero* parallelism but freezes `/health` for 60 s (Pitfall 7). Per-symbol Prometheus labels explode cardinality to 18k+ series (Pitfall 6). Hard data-quality gates on day one abort the entire pipeline (Pitfall 11). Each of these is cheap to avoid if the phase order is right, and expensive to retrofit if it isn't.

## Key Findings

### Recommended Stack

Add **6 pure-Python libraries, zero new services.** Reject Redis, Celery, Great Expectations, OpenTelemetry full stack, statsd — all solve problems we don't have at this scale. Keep loguru, keep APScheduler, keep tenacity.

**Top additions (with version + rationale):**

- **`cachetools >=7.0,<8.0`** — In-process TTL/LRU cache for hot reads (rankings, market summary, indicators per `(symbol,date)`). Pure-Python, zero deps, decorator API. The right answer for single-process. *Caveat:* not async-safe for concurrent writes — wrap with `asyncio.Lock` per ARCHITECTURE.md.
- **`hishel >=1.2,<2.0`** — RFC 9111 HTTP cache transport for the existing httpx clients (vnstock, news fetches). Drops into `AsyncCacheTransport`. SQLite storage. Respects upstream `Cache-Control`; non-cacheable responses pass through unchanged.
- **`pandera[pandas] >=0.31,<1.0`** — DataFrame schema validation for OHLCV / indicators / fundamentals. Pydantic v2 native, vectorized checks (NaN ratio, monotonic dates, value bounds). Far lighter than Great Expectations' framework footprint.
- **`prometheus-client >=0.25,<1.0`** + **`prometheus-fastapi-instrumentator >=7.1,<8.0`** — Pull-model metrics. `/metrics` endpoint, no agent. Auto HTTP request histogram + status counters; module-level Counter/Histogram/Gauge for pipeline phases + cache hits/misses.
- **`diskcache >=5.6,<6.0`** *(optional, persistent tier)* — SQLite-backed cache for results that should survive process restarts (parsed financial statements, daily indicator snapshots). Only adopt where TTL cache loss is genuinely painful.

**Already-installed, no upgrade needed:** loguru (use `serialize=True` + `contextualize()` + `enqueue=True`), tenacity (retries with backoff), httpx, SQLAlchemy 2.0 async, Alembic, anyio (transitive — use its `Semaphore` for bounded fan-out without a new dep).

**DB optimization is patterns, not packages:** `op.create_index(..., postgresql_concurrently=True)` migrations, SQLAlchemy `before_cursor_execute`/`after_cursor_execute` events for slow-query logging, `pool_size 3→10` + `max_overflow 5→10` + `pool_timeout=5`, optional `pg_stat_statements` (Supabase exposes via dashboard).

See [STACK.md](./STACK.md) for installation commands, alternatives considered, and version-compatibility matrix.

### Expected Features

Five concern areas. Each has table stakes, differentiators, and explicit anti-features.

#### Performance (pipeline + DB)

**Table stakes:**
- Per-stock failure isolation — one bad symbol must not fail the whole batch (`gather(..., return_exceptions=True)`)
- Pipeline retries with `tenacity` exponential backoff per crawler call site
- Composite indexes on hot paths: `stock_prices(symbol, date DESC)`, `pipeline_runs(started_at DESC)`, `stock_scores(date, symbol)`
- Connection pool tuning: `pool_size 3→10`, `pool_timeout=5` (fail fast, surface in metrics)

**Differentiators:**
- Concurrent crawl with `asyncio.Semaphore(8)` — 5–10× wall-clock win, gated on retry/backoff landing first
- Repository batch upserts via `INSERT … ON CONFLICT … DO UPDATE`
- Per-stage timing on `PipelineRun` (crawl/analyze/score/report durations)

**Anti-features:** time-series partitioning (premature at 500k rows), BRIN-as-default (btree composite wins at this scale — *flagged disagreement, see Open Questions*), parallel ProcessPoolExecutor (only if profiling proves CPU-bound after concurrent crawl).

#### Caching

**Table stakes:**
- In-process `cachetools.TTLCache` for API response cache (`/api/scores/ranking`, `/api/market/summary`)
- In-process indicator cache keyed by `(symbol, indicator, params, last_ohlcv_date)`
- Cache invalidation on pipeline completion — `cache.invalidate_namespace(...)` in `automation_service.py` after each write phase
- Single-flight wrapper (`asyncio.Lock` per key) to prevent cold-start stampede
- Pre-warm hot keys at end of daily pipeline (don't lazy-fill from first request)

**Differentiators:**
- HTTP-layer cache via `hishel` for upstream vnstock/news fetches
- Persisted indicator results table (`stock_indicators(symbol, date, name, value)`) — replaces in-memory cache long-term, survives restarts
- `diskcache` for results too expensive to recompute on cold start (financial-statement parses)

**Anti-features:** Redis (no second process to share with), multi-level cache (L1+L2+L3), generic ASGI response-cache middleware (no domain semantics, can't invalidate cleanly).

#### Observability

**Table stakes:**
- Structured JSON logging — loguru `serialize=True` + `enqueue=True` + `contextualize()` (no f-string log lines)
- `CorrelationIdMiddleware` setting `request_id` contextvar (propagates to scheduler tasks via contextvar, not `Depends`)
- Pipeline `run_id` propagation — wrap `run_daily_pipeline` in `logger.contextualize(run_id=...)`
- Request log middleware (method, path, status, duration_ms)
- `/health/live`, `/health/ready`, `/health/pipeline`, `/health/data` (split from current single endpoint)
- Slow query logging via SQLAlchemy events (queries > 250–500 ms)

**Differentiators:**
- Prometheus `/metrics` endpoint via `prometheus-fastapi-instrumentator`
- `@observe("domain.subsystem.action")` decorator combining timing + log + Prometheus histogram in one annotation
- `health_self_probe` scheduler job (every 30 s) populating gauges that aren't request-driven (DB pool size, `last_pipeline_age_seconds`, last successful crawl per symbol count)
- Admin observability dashboard page (Helios) — last 30 runs, per-stage durations, failure histogram, slow-query top-10
- APScheduler `EVENT_JOB_ERROR` listener emitting counter + Telegram alert

**Anti-features:** OpenTelemetry full stack (collector + exporter), Sentry (violates data-sovereignty), per-symbol Prometheus labels (cardinality explosion — symbols belong in logs, not metrics), `/metrics` push-gateway (sync, blocks event loop).

#### Data Quality

**Table stakes:**
- Two-tier validation: **Tier 1 (block per-symbol)** = corrupt/unsafe (negative price, future date, NaN ratio > threshold, duplicate PK) → skip that symbol, continue pipeline. **Tier 2 (advisory)** = anomalous (RSI > 99.5, gap > 30 %, missing > 20 % rows) → log + Prometheus gauge, do not block.
- NaN/Infinity sanitizer at JSONB write boundary (`df.replace([±inf], NaN).where(notna(), None)`)
- Stale-data detection endpoint comparing `MAX(date)` to current trading-calendar date
- `PipelineRun.stats` JSONB column (or `PipelineRunStockResult` table) recording `succeeded/failed/skipped` + failed symbol list
- Crawler-level Pydantic validators (reject before persist; repositories stay dumb)

**Differentiators:**
- `DataQualityService` running as a new pipeline step between crawl and score; writes `data_quality_runs` row + emits `dq_missing_ratio` / `dq_anomaly_count` gauges
- Quarantine table for failed rows (never lose data, never silently drop)
- Backfill command (CLI + admin button) targeting flagged symbols
- Crawler `last_crawled_at` per stock (drives stale detection at finer grain)

**Anti-features:** Great Expectations framework, hard-gate enforcement on day one (must shadow first 1–2 weeks per Pitfall 11), validating in repositories (couples persistence to evolving rules).

#### DB Optimization

**Table stakes:**
- Composite btree indexes on hot WHERE-paths (driven by slow-query log, not guessed)
- `CREATE INDEX CONCURRENTLY` via `op.create_index(..., postgresql_concurrently=True)` + `transactional=False` migration — must not lock tables during pipeline
- Pool sizing: `pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True, prepared_statement_cache_size=0` (last one already set — preserve, pgbouncer transaction-mode requires it)
- Bulk upsert via `INSERT … ON CONFLICT … DO UPDATE` in repositories

**Differentiators:**
- `pg_stat_statements` enabled in Supabase dashboard, queried periodically for top-N slow statements
- Direct connection (port 5432) for `EXPLAIN (ANALYZE, BUFFERS)` — pooled connection (6543) returns rewritten plans
- Optional GIN index on `report.content_json` if JSONB-key queries become a pattern

**Anti-features:** time-series partitioning (defer until > 10 M rows; we're at ~500 k), TimescaleDB / Citus extensions (Supabase free tier won't allow), BRIN indexes on stock_prices at current scale (btree composite faster — *flagged disagreement, see Open Questions*).

See [FEATURES.md](./FEATURES.md) for the full prioritization matrix and dependency graph.

### Architecture Approach

Single FastAPI process, single uvicorn worker, single asyncio loop shared between HTTP handlers and APScheduler jobs. v1.5 adds three new packages and modifies four existing ones — no new top-level layers, no new processes.

**New packages:**
1. **`localstock/observability/`** — `logging.py` (loguru JSON sink + contextvar enricher), `middleware.py` (CorrelationId / RequestLogging / PrometheusMetrics), `metrics.py` (registry + module-level Counter/Histogram/Gauge), `tracing.py` (`@observe` decorator).
2. **`localstock/cache/`** — `backend.py` (Protocol + `InMemoryCache` impl + factory), `decorators.py` (`@cached(namespace, key, ttl)`), `keys.py` (centralized key builders + namespaces). Redis adapter exists as opt-in behind the Protocol but is not wired by default.
3. **`localstock/validators/`** — `ohlcv.py`, `financials.py`, `news.py`. Pure functions reusable by both crawlers (Tier 1 reject) and `DataQualityService` (Tier 2 audit).

**New service:** `services/data_quality_service.py` — runs between crawl and score phases, writes `data_quality_runs` audit table.

**New scheduler jobs:** `cache_janitor` (60 s, sweeps expired TTLs explicitly to avoid unbounded growth between accesses), `health_self_probe` (30 s, populates pool/age gauges).

**Five architectural patterns** (see [ARCHITECTURE.md §"Architectural Patterns"](./ARCHITECTURE.md)):
1. Service-layer cache with explicit invalidation (NOT response-middleware cache)
2. Bounded-parallel crawl with single `asyncio.Semaphore`
3. Decorator trio `@observe` — timing + log + metric in one annotation
4. Validator-then-persist (crawler) + audit (service)
5. Pull-based self-observability — no agent, no sidecar

**Placement decisions:** Correlation ID is a contextvar (survives `asyncio.gather`, visible in scheduler jobs). Service-layer caching (NOT response middleware — keys need domain semantics + invalidation). DB query timing uses both repo `@timed_query` decorator (logical names) AND SQLAlchemy engine events (low-level fallback) — they emit to different histograms.

### Critical Pitfalls

1. **Cache key omits "as-of trading date"** — naive TTL caches serve pre-pipeline data for up to TTL after 15:45 mutation. *Fix:* include `(symbol, latest_ohlcv_date, scoring_run_id)` or bump a `pipeline_version` counter at end of `run_daily_pipeline` and embed in every key. Never TTL-cache scoring outputs.
2. **Cache stampede on cold start** — 400 symbols × N panels miss simultaneously, exhausting `pool_size=3`. *Fix:* single-flight wrapper (`asyncio.Lock` keyed by cache key), pre-warm hot keys at end of pipeline, raise pool to 10, `pool_timeout=5`.
3. **`pandas-ta` under `asyncio.gather` is sequential** — `async def` wrapping sync CPU work runs serially on the event loop and blocks `/health` for 60 s. *Fix:* `asyncio.to_thread(...)` for CPU-bound work; vectorize over all 400 symbols in one pandas op rather than 400 parallel calls.
4. **Per-symbol Prometheus labels = 18 k+ series** — `Counter(..., labels=["symbol", "stage", "status"])` blows up scrape size and RAM. *Fix:* never put `symbol` on a metric; symbols go in **logs**. Label budget `stage × status × source ≤ 50 series per metric`. Audit cardinality before deploy.
5. **vnstock concurrent calls trigger soft-ban** — > 8 parallel calls return 429s / HTML error pages; `gather` fail-fast kills 399 healthy symbols. *Fix:* `Semaphore(5–8)` + jitter + `return_exceptions=True` + per-source token-bucket (`aiolimiter`) + circuit breaker on 3 consecutive 429s + response-shape validation before parsing.
6. **NaN/Infinity in JSONB silently breaks API** — pandas-ta returns `NaN` for first N rolling rows; `df.to_dict()` → JSONB → `json.loads` raises `Out of range float values are not JSON compliant` for new symbols only. *Fix:* one sanitizer at boundary (`df.replace([±inf], NaN).where(notna(), None)`); Pydantic outbound validator NaN→None.
7. **Hard data-quality gate aborts pipeline day one** — strict `validate_or_raise` on real free-data sources fails 50/400 symbols, Telegram digest goes silent. *Fix:* shadow mode 1–2 weeks (warn-only, build baseline failure rates), then promote selective rules to blocking. Two-tier: block on corrupt/unsafe, warn on anomalous. Quarantine table — never silently drop.

See [PITFALLS.md](./PITFALLS.md) for 21 pitfalls total + technical-debt patterns + integration gotchas + the "Looks Done But Isn't" checklist.

## Implications for Roadmap

### Recommended Build Order (cross-area dependencies)

The single most important rule: **instrumentation before optimization.** You cannot pick the right indexes, cache keys, or concurrency levels without metrics telling you what's slow. ARCHITECTURE.md, FEATURES.md, and PITFALLS.md all converge on the same ordering.

#### Phase A — Logging Foundation
**Rationale:** Every later phase emits logs you'll want to grep. Smallest possible PR. No upstream dependencies.
**Delivers:** loguru JSON sink (`serialize=True`, `enqueue=True`), `CorrelationIdMiddleware` setting `request_id` contextvar, request log middleware with method/path/status/duration_ms, pipeline `run_id` via `logger.contextualize`, secret redaction patcher for `Settings`.
**Avoids:** Pitfalls 4 (f-string logs defeat structure), 5 (loguru double-init duplicates lines), 16 (sync sink blocks loop), 17 (PII leakage), 20 (un-serializable fields fail batch).
**Lint rule in CI:** `grep -r 'logger\.[a-z]*(f"' src/` returns 0.

#### Phase B — Metrics Primitives + `/metrics` Endpoint
**Rationale:** Depends on A (so failures are debuggable). Declares the registry; no instrumentation yet.
**Delivers:** `prometheus-client` + `prometheus-fastapi-instrumentator` wired in `create_app()`. Module-level metric definitions (`http_*`, `op_*`, `cache_*`, `db_query_*`, `pipeline_step_*`, `dq_*`). `/metrics` mounted via `make_asgi_app()`. Idempotent init pattern (avoid `Duplicated timeseries` in tests).
**Avoids:** Pitfalls 5 (registry double-init), 6 (label cardinality — design label schema *now*, before instrumenting), 14 (sync push blocks loop — pull-model only).

#### Phase C — Instrumentation (HTTP middleware + `@observe` + `@timed_query`)
**Rationale:** Depends on B. After this, scheduler-driven work AND HTTP traffic are visible.
**Delivers:** `PrometheusMetricsMiddleware`, `@observe("domain.subsystem.action")` decorator on service methods + scheduler jobs, `@timed_query` on hot repository methods + SQLAlchemy `before/after_cursor_execute` event listeners for ad-hoc queries, expanded `/health/{live,ready,pipeline,data}` endpoints, `health_self_probe` 30 s job.
**Avoids:** Pitfall 15 (APScheduler swallowed exceptions — add `EVENT_JOB_ERROR` listener emitting counter + Telegram).

#### Phase D — Data Quality (Tier 1 validators + sanitizers + per-stock isolation)
**Rationale:** Depends on C (so DQ runs are observable). Must land **before** parallelism — concurrency amplifies silent corruption. Can land in parallel with E for shadow-mode learning.
**Delivers:** `validators/` package (pandera schemas for OHLCV/indicators/fundamentals + manual sanity checks), NaN/Inf sanitizer at JSONB boundary, `PipelineRun.stats` JSONB column with succeeded/failed/skipped + failed symbol list, per-stock try/except in pipeline (never one symbol fails the batch), stale-data detection endpoint, freshness check in `/health/data`.
**Mode:** Shadow first 1–2 weeks (warn-only, build baseline failure rates) before promoting Tier 2 rules to blocking.
**Avoids:** Pitfalls 10 (NaN→JSONB→broken API), 11 (hard-gate aborts day one).

#### Phase E — Caching (in-process, with version-aware invalidation)
**Rationale:** Depends on C (need cache-hit/miss metrics). Must come before any benchmarking of "is the dashboard fast?"
**Delivers:** `cache/` package — `CacheBackend` Protocol + `InMemoryCache` (cachetools.TTLCache wrapped with `asyncio.Lock`), `@cached(namespace, key, ttl)` decorator, centralized key builders including `pipeline_run_id`/`scoring_run_id`/`latest_ohlcv_date` for content-addressed identity, `cache.invalidate_namespace(...)` calls in pipeline write boundaries, single-flight wrapper, pre-warm hot keys at end of `run_daily_pipeline`, `cache_janitor` 60 s job. Apply to `/api/scores/ranking` + `/api/market/summary` + indicator service first. Optional `hishel` HTTP cache on httpx clients (vnstock/news).
**Avoids:** Pitfalls 1 (TTL-only stale ranks), 2 (cold-start stampede), 3 (`@lru_cache` on async).

#### Phase F — Pipeline Parallelism (concurrent crawl + retries)
**Rationale:** Depends on C (measure the win), D (catch corruption that concurrency amplifies), E (pool tuning context). Bumps `pool_size` 3→10 in same PR.
**Delivers:** Crawler loop refactored to `asyncio.Semaphore(8) + gather(..., return_exceptions=True)` with per-source token-bucket and circuit-breaker. `tenacity` retries with exponential backoff + jitter on every external call. `pandas-ta` (sync, CPU-bound) wrapped in `asyncio.to_thread`. Pool tuning: `pool_size=10, max_overflow=10, pool_timeout=5`. Telegram send moved to fire-and-forget task.
**Avoids:** Pitfalls 7 (`gather` over sync CPU work), 8 (vnstock soft-ban), 9 (pool exhaustion at 15:45).

#### Phase G — DB Optimization (indexes + bulk upserts, driven by metrics)
**Rationale:** Depends on C and F — pick indexes from `db_query_duration_seconds` p95 outliers, not from guesswork. Last because it's the lowest-leverage if everything else is right.
**Delivers:** Composite btree indexes on identified hot paths via `CREATE INDEX CONCURRENTLY` (separate non-transactional Alembic migrations), repository batch upserts via `INSERT … ON CONFLICT … DO UPDATE`, slow-query event-listener tuned thresholds, `pg_stat_statements` enabled in Supabase dashboard, migration runbook ("not during pipeline window").
**Avoids:** Pitfalls 12 (locking migrations during pipeline + partition cutover row loss), 13 (Supabase pgbouncer disables features observability assumes), 19 (index bloat without VACUUM schedule).

#### Phase H — Observability Dashboard + Differentiators (optional v1.5 P2)
**Rationale:** All upstream data exists in Postgres + Prometheus after A–G; this phase is purely UI multiplier.
**Delivers:** `/admin/observability` Helios page — last 30 pipeline runs, per-stage durations, failure histogram, data-freshness panel, slow-query top-10. Backfill command (CLI + admin button). Persisted indicator results table (replaces in-memory cache long-term). Shared-secret `X-Admin-Token` header check (Pitfall 18 — defense in depth for tunneled deployments).
**Defer to v1.6+:** ProcessPoolExecutor for indicator computation (only if profiling shows CPU bound), GIN index on `report.content_json` (only when JSONB-key queries become a pattern), `EXPLAIN ANALYZE` capture as automated tool.

### Phase Ordering Rationale

- **A → B → C is non-negotiable.** Logging before metrics before instrumentation. Each is a foundation for the next.
- **D before F.** Data-quality validators must catch corrupt rows *before* concurrent crawling amplifies the blast radius.
- **E before F.** Cache invalidation hooks must exist before pipeline write boundaries are restructured for parallelism — otherwise stale-cache behavior is the first thing the parallelism PR breaks.
- **G last.** Adding indexes early "for performance" doubles write cost on every pipeline run and bloats Supabase free tier. The only correct trigger for an index is "p95 of this query path exceeded threshold for a week."
- **H is decorative.** Skip if v1.5 timeline is tight; the underlying signals exist after A–G whether or not the page is built.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase E (Caching):** Verify `cachetools.TTLCache` async-safety claim (architecture says "needs external lock for concurrent async access", confidence MEDIUM). Decide cachetools-only vs cachetools+diskcache vs add Redis adapter behind Protocol now. Spike: 50-parallel cold-start request test post-restart.
- **Phase F (Parallelism):** Empirically tune `Semaphore(N)` for vnstock — `8` is a starting estimate, real rate limits are undocumented. Need a controlled measurement run before the cron schedule changes.
- **Phase G (DB):** Verify Supabase free-tier exposure of `pg_stat_statements` (per Pitfall 13 — features behave differently through pgbouncer). Confirm `CREATE INDEX CONCURRENTLY` works through Supabase migration tooling.

**Phases with standard patterns (skip phase-research):**
- **Phase A (Logging):** loguru `serialize=True` + `contextualize` is documented and used in many production FastAPI apps. Implementation is mechanical.
- **Phase B (Metrics primitives):** `prometheus-fastapi-instrumentator` README pattern is the de-facto standard. ~50 lines of integration glue.
- **Phase C (Instrumentation):** Decorator pattern is shown in ARCHITECTURE.md §"Pattern 3" with full code.
- **Phase D Tier 1 validators:** pandera schemas are straightforward; the *policy* (shadow → enforce ramp) needs requirements-level decisions, not technical research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified on PyPI 2026-04-29; integration patterns verified against existing `pyproject.toml` and `db/database.py`. The "no Redis, no Celery" stance is consistent with v1.0 decisions logged in PROJECT.md. |
| Features | HIGH | Production patterns are well-established; scoping to single-user local context is unambiguous. Anti-feature list is opinionated but defensible — each rejection is grounded in single-process / single-user constraints. |
| Architecture | HIGH | Grounded in concrete repo file inspection (api/app.py, scheduler/scheduler.py, db/database.py, services/pipeline.py, services/automation_service.py, api/routes/health.py, config.py). All five architectural patterns cite specific file paths and existing call sites. |
| Pitfalls | HIGH for stack-specific traps; MEDIUM for Supabase-tier-specific items | Verified against codebase for Pitfalls 1–12, 14–17, 19, 21. Supabase-specific Pitfall 13 (pg_stat_statements / LISTEN-NOTIFY / EXPLAIN through pooler) requires runtime verification per tier — flagged for Phase G research. |

**Overall confidence: HIGH.**

### Gaps to Address (Open Questions for Requirements Step)

These are inter-research-file disagreements or unspecified policy choices that the requirements phase must resolve:

1. **BRIN vs btree composite for `stock_prices(symbol, date)` index.** ARCHITECTURE.md §Build-Order step 11 recommends BRIN; FEATURES.md anti-features section and STACK.md both reject BRIN at our 500 k row scale and recommend btree composite. **Resolution direction:** start with btree composite `(symbol, date DESC)` (consensus across two of three docs + matches access pattern); revisit BRIN only if `stock_prices` exceeds ~10 M rows (post-v2 multi-exchange).

2. **Cache backend ambition: cachetools-only vs. Protocol-with-Redis-adapter ready.** ARCHITECTURE.md proposes `CacheBackend` Protocol with optional Redis adapter behind a config flag. FEATURES.md anti-features explicitly rejects Redis. STACK.md rejects Redis and `aiocache` abstraction layer ("we don't expect to swap backends"). **Resolution direction:** ship `InMemoryCache` only; do **not** build Protocol+adapter scaffold until/unless multi-process becomes real. YAGNI applies. Decorator call sites are trivially swappable later (one decorator import).

3. **In-memory indicator cache vs persisted indicator-results table.** FEATURES.md flags this explicitly as "a fork — don't ship both permanently." Recommend: ship TTLCache in Phase E (fast win), promote to persisted table in Phase H or v1.6 once schema stabilizes. Requirements should specify which is the v1.5 target.

4. **Prometheus `/metrics` endpoint priority: P1 (architecture) vs P3 (features).** ARCHITECTURE.md treats it as core; FEATURES.md prioritization matrix puts it at P3 ("LOW user value, no consumer yet"). **Resolution direction:** ship the endpoint in Phase B regardless (cost is ~50 LOC, cardinality discipline is the hard part) but defer Grafana wiring to user demand.

5. **Data quality enforcement ramp policy.** Pitfall 11 mandates shadow mode 1–2 weeks before any blocking rules. Requirements must specify: which rules are Tier 1 (block per-symbol) vs Tier 2 (advisory) on day one, and the explicit promotion criteria (e.g., "Tier 2 rule promotes to Tier 1 when shadow failure rate < 1 % for 14 consecutive days").

6. **Pool sizing under Supabase free-tier limits.** Pitfall 9 recommends `pool_size=10`; current is `pool_size=3`. Need to verify Supabase free-tier connection cap (stated as 60 in pitfall doc but tier limits change) and confirm 10 leaves headroom for Helios + migrations + ad-hoc psql.

7. **Scheduler observability granularity.** Whether to instrument every pipeline phase (`crawl_prices`, `crawl_financials`, `crawl_companies`, `crawl_events`, `compute_indicators`, `score_all`, `generate_top_n`, `send_digest`) or only roll-up phases. Cardinality-safe either way; question is dashboard value vs noise.

## Sources

### Primary (HIGH confidence)
- **Repo inspection** (read directly during research): `apps/prometheus/pyproject.toml`, `src/localstock/api/app.py`, `scheduler/scheduler.py`, `db/database.py`, `services/pipeline.py`, `services/automation_service.py`, `api/routes/health.py`, `config.py` — verified existing pinned versions, lifespan model, pool sizing, single-process scheduler binding.
- **PyPI metadata** fetched 2026-04-29 for: `cachetools`, `hishel`, `diskcache`, `pandera`, `prometheus-client`, `prometheus-fastapi-instrumentator`, `aiocache`, `redis`, `sqlalchemy-utils`, `opentelemetry-api`, `great-expectations`, `structlog`, `async-lru` — version + dependency graphs verified.
- **Official docs:** FastAPI advanced/middleware (lifespan + middleware ordering), APScheduler 3.x AsyncIOScheduler event-loop binding, prometheus-client `make_asgi_app()` exposition, PostgreSQL Indexes / BRIN, pandera `[pandas]` extra + Pydantic-v2 support since 0.20.x.

### Secondary (MEDIUM confidence)
- `cachetools.TTLCache` async-safety: docs note thread-safety but not asyncio-concurrent-write safety — recommend external `asyncio.Lock`. Verify with cold-start stampede spike test.
- `hishel` 1.x maturity: encode-orbit author, used in production but smaller community than `httpx-cache`. Mitigation: hishel storage drivers are pluggable; can swap to filesystem if SQLite storage misbehaves.
- Supabase `pg_stat_statements` exposure on free tier: stated to require dashboard enablement; behavior through pgbouncer transaction-mode known to differ from self-hosted Postgres. Verify per-tier at planning time.

### Tertiary (LOW confidence — needs runtime validation)
- vnstock concurrent-call rate-limit threshold: undocumented upstream; "8 is a safe starting point" is inference from anecdotal community reports + pitfall research. Empirical tuning needed in Phase F.
- Optimal `Semaphore` value for Ollama: stated as `1` for single model copy in PITFALLS — verify if multi-model or multi-instance configuration changes this.

---
*Research completed: 2026-04-29*
*Ready for roadmap: yes*
*Inputs: STACK.md (231 lines), FEATURES.md (223 lines), ARCHITECTURE.md (498 lines), PITFALLS.md (529 lines)*
