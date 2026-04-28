# Pitfalls Research

**Domain:** Adding caching, observability, data-quality, parallelism, and DB optimization to an EXISTING async-FastAPI + SQLAlchemy(asyncpg) + Supabase Postgres + APScheduler + Ollama app (LocalStock v1.5)
**Researched:** 2026-04-28
**Confidence:** HIGH for stack-specific traps (verified against codebase + library docs); MEDIUM for Supabase-specific items (behavior varies by tier).

> **Codebase facts grounding this research** (verified by inspection):
> - `apps/prometheus/src/localstock/db/database.py`: single async engine, `pool_size=3, max_overflow=5, pool_recycle=300`, `prepared_statement_cache_size=0` (Supabase pgbouncer transaction-mode workaround).
> - Supabase Postgres reached via pgbouncer (transaction pooling) — implies several Postgres features behave differently (no session-scoped state, no `LISTEN/NOTIFY`, prepared statements disabled).
> - `scheduler/scheduler.py`: single-process `AsyncIOScheduler` started in FastAPI lifespan, `daily_pipeline` cron + `process_pending_jobs` interval poller (every 5s).
> - Pipeline stages: vnstock crawl → pandas-ta indicators → scoring → Ollama LLM reports → Telegram. ~400 HOSE symbols.
> - Logging: `loguru` (free-form `logger.info(f"...")` strings — not yet structured/JSON).
> - 326+ pytest tests; FastAPI lifespan + tests share the singleton engine/scheduler globals.

These constraints make several "generic" perf tutorials actively wrong here; pitfalls below are framed against THIS stack.

---

## Critical Pitfalls

### Pitfall 1 — Cache key omitting "as-of trading date", serving yesterday's data after the 15:45 pipeline run

**What goes wrong:**
A naive `@cache(ttl=3600)` on `/api/stocks/{symbol}` or computed indicators returns pre-pipeline data for up to TTL after the daily crawl finishes. Users see "rank changed yesterday" because the cache, not the DB, is authoritative. Worse: Telegram digest at 15:50 uses cached top-N from 15:00.

**Why it happens:**
- TTL is set to "long enough to be useful" without considering the daily mutation cliff at 15:45.
- Cache key includes `symbol` but not `trading_date` / `pipeline_run_id`.
- Developers forget that LocalStock has *exactly one* mutation event per weekday; eventual consistency that's fine for SaaS is wrong here.

**How to avoid:**
- Key by **content-addressed identity**: include `(symbol, latest_ohlcv_date, scoring_run_id)` in cache key. Stale data becomes a cache *miss*, not a wrong hit.
- Bump a single `pipeline_version` Redis key (or in-memory counter) at the *end* of `AutomationService.run_daily_pipeline`; include it in every cache key. Old keys age out naturally.
- Never cache *scoring* outputs by TTL alone — bind to `scoring_run.id`.
- For OHLCV data which is immutable per (symbol, date), TTL can be long (24h+); for derived/ranked data, TTL is irrelevant — use version key.

**Warning signs:**
- Telegram digest disagrees with dashboard for ~1h after pipeline finishes.
- Manual `/admin/score` re-run doesn't change UI without browser refresh.
- Tests passing in isolation but flaky when reordered (cache leaking between tests).

**Phase to address:** Caching phase. Scheduler phase must add the `pipeline_version` bump as the *last* step of `run_daily_pipeline`.

---

### Pitfall 2 — Cache stampede on cold start: 400 symbols × N panel components hit DB simultaneously

**What goes wrong:**
After a process restart (or Redis flush), the dashboard's first page load fans out to dozens of endpoints. Each endpoint computes ranks/indicators independently, all observing a cache miss in the same millisecond. With `pool_size=3, max_overflow=5`, the 9th concurrent query waits, the 10th times out, and FastAPI returns 500s during what should be the *fastest* moment.

**Why it happens:**
- Async + small pool + many parallel route handlers.
- Naive `if cache.get(): ...; else: compute_and_set()` has no single-flight protection.
- Pgbouncer transaction mode hides the pool exhaustion — connections look "available" upstream but SQLAlchemy's local pool is still 3.

**How to avoid:**
- Use a **single-flight / request-coalescing** wrapper (`asyncio.Lock` keyed by cache key, or `aiocache` with `lock=True`).
- For the daily pipeline, **pre-warm** the hot keys at the end of the run (write to cache directly from the pipeline, not lazily from first request).
- Prefer one `/api/dashboard/summary` aggregate endpoint over 8 fan-out endpoints. The frontend already only renders one screen — match the API to the screen.
- Increase `pool_size` cautiously: Supabase free tier has hard connection limits. Going from 3→10 with one app process is safe; going to 50 is not.

**Warning signs:**
- p99 latency spike + `QueuePool limit ... overflow ... reached` warnings in logs after restart.
- `pg_stat_activity` shows `idle in transaction` rows during dashboard load.
- "First load is always slow, refresh is fast" — classic stampede tell.

**Phase to address:** Caching phase (single-flight + pre-warm). Pipeline parallelism phase must size pool consciously.

---

### Pitfall 3 — Cache backend choice: `cachetools` / `functools.lru_cache` is not async-safe and not multi-process-safe

**What goes wrong:**
A developer reaches for `@lru_cache` because "it's stdlib." It works in dev. Then APScheduler's daily job mutates DB state but the FastAPI request handler still has the function-scoped cache. Or worse: `lru_cache` is applied to an `async def` and returns the same coroutine object — second await raises `RuntimeError: cannot reuse already awaited coroutine`.

**Why it happens:**
- `functools.lru_cache` doesn't understand coroutines.
- In-process dict caches don't see writes from other workers / from APScheduler running in the same process but different task contexts.
- Pickle-based caches choke on `pandas.DataFrame` with `Timestamp` indices or numpy `NaN`.

**How to avoid:**
- For async: use `aiocache` (memory or redis backend) or hand-rolled `dict + asyncio.Lock`. Never `@lru_cache` on `async def`.
- Decide *now* whether to add Redis or stay in-memory. Single-process + APScheduler-in-app = in-memory is fine, BUT cache must be invalidated by the pipeline writer in the same process.
- For DataFrame caching: convert to Arrow/Parquet bytes (`df.to_parquet()`) before caching, not pickle. Smaller, faster, NaN-safe.
- Never cache mutable objects — always cache the *bytes* / immutable tuple form.

**Warning signs:**
- `RuntimeError: cannot reuse already awaited coroutine`.
- Memory growth on long-running process despite TTL (lru_cache has no TTL).
- DataFrame cache hits return objects with `dtype: object` instead of `float64` (pickle round-trip lost dtypes).

**Phase to address:** Caching phase — make backend decision (in-memory vs Redis) explicitly, document in DECISIONS.

---

### Pitfall 4 — `loguru` `logger.info(f"...")` everywhere defeats structured logging migration

**What goes wrong:**
Existing code is full of `logger.info(f"Processed {symbol} score={score}")`. When you switch to JSON sink for observability, you get a single `message` field with the f-string already interpolated. Dashboards can't filter by `symbol` or aggregate by `score`. You end up regex-parsing your own logs.

**Why it happens:**
- f-strings are the path of least resistance; loguru accepts them; no linter complains.
- "We'll add structure later" — but later requires touching every log line.

**How to avoid:**
- Replace `f"..."` patterns with `logger.bind(symbol=symbol).info("score computed", score=score)` or loguru's `logger.info("score computed", symbol=symbol, score=score)` (kwargs become extra fields with JSON serializer).
- Configure loguru sink with `serialize=True` + custom serializer that reads from `record["extra"]`.
- Add an AST-based lint rule (or simple `grep`) in CI that flags `logger\.(info|warning|error)\(f"`.
- Standardize event names: `pipeline.stage.started`, `crawl.symbol.failed`, `scoring.run.completed` — searchable, dashboardable.

**Warning signs:**
- Dashboard query "show all failures for symbol VNM today" requires regex.
- Log volume grows linearly with debug detail because every line is a unique string (no aggregation possible).

**Phase to address:** Logging phase — first task is adopting `extra=` / `bind()` convention; lint rule prevents regression.

---

### Pitfall 5 — Loguru double-init in FastAPI lifespan + tests, producing duplicated log lines

**What goes wrong:**
A new `setup_logging()` is called from `lifespan()`. Pytest fixtures import the app multiple times; `logger.add(sink)` runs each time. By test 50 every log line is emitted 50 times, masking real errors and making CI 10x slower from log I/O.

**Why it happens:**
- Loguru's `logger` is a module-level singleton; `logger.add()` is *additive*, not idempotent.
- FastAPI lifespan + test client + fixture reuse triggers multiple inits.
- Same trap exists for prometheus `Counter` / `Histogram` — re-registering in same registry raises `Duplicated timeseries`.

**How to avoid:**
- `logger.remove()` before any `logger.add(...)` in `setup_logging()`.
- Wrap setup in a `_configured` flag or module-scoped pytest fixture (`@pytest.fixture(scope="session")`).
- For prometheus: use `CollectorRegistry()` per-app, or guard `try: REGISTRY.register(c) except ValueError: pass`.

**Warning signs:**
- "tests are noisy now" — each line printed 2-5x.
- `prometheus_client.exposition.ValueError: Duplicated timeseries in CollectorRegistry`.
- Memory grows in test suite (handlers accumulating).

**Phase to address:** Logging phase + Metrics phase — both need idempotent init pattern.

---

### Pitfall 6 — Prometheus high-cardinality labels: `symbol` ∈ 400 values × `stage` × `status` blows up scrape size

**What goes wrong:**
`Counter("crawl_total", ["symbol", "stage", "status", "source"])` with 400 symbols × 5 stages × 3 statuses × 3 sources = 18,000 series. Each scrape is multi-MB. Memory of `prometheus_client` grows because metrics never expire. After a week of symbol churn (delisted/added), it's 50k series.

**Why it happens:**
- Per-symbol observability is intuitive — "I want to know which symbols fail."
- Prometheus encourages labels; nothing warns you about cardinality limits.

**How to avoid:**
- **Never** put `symbol` on a metric. Put it in **logs** (queryable via Loki/Grafana logs) or a dedicated `failures` table.
- Label budget: `stage` (5), `status` (3), `source` (3) ≤ 50 series per metric. Stop there.
- For per-symbol failure detection use a `Gauge("last_crawl_failures_count")` updated per pipeline run, plus structured logs with `symbol` field.
- Audit cardinality before deploy: `len(metric._metrics)` should be < 100 per metric.

**Warning signs:**
- `/metrics` endpoint > 1MB or scrape duration > 1s.
- `prometheus_client` process RSS growth correlated with pipeline runs.
- Grafana queries time out on `sum by (symbol) (...)`.

**Phase to address:** Metrics phase — design label schema *before* instrumenting.

---

### Pitfall 7 — `pandas-ta` (and `pandas` itself) under `asyncio.gather` blocks the event loop, defeating parallelism

**What goes wrong:**
Pipeline does `await asyncio.gather(*[compute_indicators(s) for s in symbols])` thinking it's parallel. Each `compute_indicators` is `async def` but calls `df.ta.rsi()` (sync, CPU-bound, holds GIL). All 400 tasks run *serially* on the event loop. Worse, no other request handler can respond during the 60s computation — `/api/health` times out.

**Why it happens:**
- `async def` is treated as "magic parallelism."
- pandas-ta is sync C/Python; GIL prevents true threading parallelism for pure-Python parts but releases for numpy ops.
- Developers don't profile until it's slow — and it's slow because it was *never* parallel.

**How to avoid:**
- CPU-bound work goes to `asyncio.to_thread(...)` or `loop.run_in_executor(ProcessPoolExecutor, ...)`. For pandas-ta which uses numpy heavily, `to_thread` (releases GIL during numpy) usually suffices.
- Even better for 400-symbol CPU work: do it in *one* vectorized pandas op over all symbols at once, not 400 parallel calls.
- For the LLM stage (Ollama): true async I/O — `gather` works correctly there. Don't conflate the two.
- Add a guard: warn if any coroutine takes > 100ms wall time without an `await` (use `asyncio.get_event_loop().slow_callback_duration = 0.1`).

**Warning signs:**
- `gather(...)` with `return_exceptions=False` doesn't speed up — total time = sum, not max.
- Health check fails *only during pipeline runs*.
- `asyncio` warns: `Executing <Task ...> took 12.5 seconds`.

**Phase to address:** Pipeline parallelism phase — must distinguish I/O-bound (asyncio.gather) from CPU-bound (to_thread / vectorize).

---

### Pitfall 8 — vnstock concurrent calls without rate-limit/backoff get the source IP soft-banned

**What goes wrong:**
Pipeline parallelism fans out 50 concurrent `vnstock` calls to speed up crawl. Within minutes, vnstock returns 429s, empty DataFrames, or HTML error pages. pandas tries to parse HTML, raises `ValueError`, and *one bad symbol fails the whole gather*. Next day the source IP is rate-limited for hours.

**Why it happens:**
- vnstock wraps free public sources (VCI, TCBS, etc.) which have undocumented limits.
- "More parallelism = faster" is intuitive but wrong for shared free APIs.
- `asyncio.gather` defaults to fail-fast; one symbol's HTML response taking down 399 others is a known footgun.

**How to avoid:**
- Cap concurrency with `asyncio.Semaphore(5)` (or 8) and add jitter (`await asyncio.sleep(random.uniform(0.5, 1.5))`).
- Use `asyncio.gather(..., return_exceptions=True)` and reduce results, never let one symbol crash the batch.
- Add a per-source rate-limiter (token bucket via `aiolimiter`).
- Add a circuit breaker: if 3 consecutive 429s, sleep 60s then retry; if still failing, abort the source and continue with others.
- Validate response shape *before* parsing — if it's HTML or empty, log and skip.

**Warning signs:**
- Crawl success rate drops from 99% → 60% suddenly.
- Logs: `JSONDecodeError`, `<!DOCTYPE html>` in response.
- vnstock returns same data for different symbols (cached error page).

**Phase to address:** Pipeline parallelism phase + Data quality phase (response-shape validation gate).

---

### Pitfall 9 — Connection pool exhaustion when scheduler job runs concurrently with API requests

**What goes wrong:**
Pool is `pool_size=3, max_overflow=5` (verified in code). Daily pipeline holds ~5 connections during the heavy DB phase. A concurrent admin click on `/admin/jobs` fans out to 4 endpoints, each opens a session. The 9th connection blocks; FastAPI request hangs for `pool_timeout` (default 30s); user sees spinner; clicks again, now there are 12 pending.

**Why it happens:**
- Pool was sized for "single user, light load" without considering concurrent pipeline + UI.
- `process_pending_jobs` runs every 5s — its session is short but it competes.
- Supabase pgbouncer doesn't help because the pool that exhausts is *SQLAlchemy's local pool*, not the Postgres connection count.

**How to avoid:**
- Raise `pool_size` to 10, `max_overflow` to 10 — still well within Supabase free-tier (60 connections).
- Set `pool_timeout=5` not 30 — fail fast, surface the problem in metrics, don't hide it as latency.
- Make sessions **short**: open inside the unit of work, close immediately. Audit any `async with session:` that wraps slow LLM/HTTP calls — those should fetch data, close session, then call LLM, then reopen.
- Use a separate engine for the pipeline (`pool_size=5`) vs API (`pool_size=10`) if they truly contend.

**Warning signs:**
- `TimeoutError: QueuePool limit of size 3 overflow 5 reached`.
- API p99 latency spikes specifically at 15:45-16:15.
- `pg_stat_activity` shows few active connections but FastAPI is slow (proves pool, not DB, is bottleneck).

**Phase to address:** Pipeline parallelism phase — re-tune pool. DB optimization phase verifies via `pg_stat_activity`.

---

### Pitfall 10 — NaN / Infinity propagation into JSONB columns silently breaks API (and `json.loads`)

**What goes wrong:**
pandas-ta produces `NaN` for the first N rows of any rolling indicator. A "store full indicator dict in JSONB" path serializes via `df.to_dict()` → `{"rsi": nan}`. asyncpg sends it. Postgres stores it. Reading back, FastAPI's `json.loads` raises `ValueError: Out of range float values are not JSON compliant: nan` — only on the days when a stock has insufficient history. Some users see broken pages randomly.

**Why it happens:**
- Python's `json` accepts `float('nan')` on serialize (with `allow_nan=True` default) but the spec says NaN isn't valid JSON. Some drivers, some downstream parsers (JS `JSON.parse`) reject it.
- New stocks (or recently delisted with backfill) have <14 days of data → all RSI values NaN → entire row poisoned.
- Tests use stocks with full history; the bug only manifests in production.

**How to avoid:**
- Write a single sanitizer: `df.replace([np.inf, -np.inf], np.nan).where(df.notna(), None)` before any `to_dict()`.
- Pydantic validator on outbound models converts NaN → None. Add at the boundary, not in every endpoint.
- Reject inserts with NaN at the data-quality validator (decide: fail, or coerce to NULL — but be consistent).
- Frontend: never use `JSON.parse` on raw — Next.js fetch already does it; ensure Pydantic emits clean JSON.

**Warning signs:**
- Sentry/logs: `Out of range float values are not JSON compliant`.
- Dashboard "broken page" only for newly-added symbols.
- DB query `WHERE content_json::text LIKE '%NaN%'` returns rows.

**Phase to address:** Data quality phase — sanitizer is a hard validation gate, not advisory.

---

### Pitfall 11 — Data-quality validation as a hard gate breaks the *existing* pipeline on day one

**What goes wrong:**
Adding `if not validator.passes(df): raise ValidationError` causes the daily pipeline to abort on the first symbol that fails (and 50 of 400 will fail something — it's a free public source). Telegram digest doesn't send. User wakes up to silence.

**Why it happens:**
- "Data quality" is framed as enforcement, not observation.
- Existing pipeline tolerates messy data; new validation is stricter than reality.

**How to avoid:**
- **Two-tier validation:**
  - Tier 1 (block): "data is corrupt or unsafe" (negative price, future date, duplicate PK). Skip *that symbol*, continue pipeline.
  - Tier 2 (warn): "data looks anomalous" (RSI > 99.5, gap > 30%, missing > 20% rows). Log + metric, *do not block*.
- **Shadow mode first:** for 1-2 weeks, validators only emit warnings/metrics. Establish baseline failure rates. Only then promote selective rules to blocking.
- Per-symbol failure isolation: `try/except` around each symbol with structured failure logging. Pipeline always completes for the 350+ healthy ones.
- Quarantine table for failed rows — never lose data, never silently drop.

**Warning signs:**
- First night with validation enabled: pipeline aborts at 15:46.
- Telegram digest contains 5 stocks instead of 20 (silent partial failure).
- `validation_failures` metric shows 30%+ rate — that's not bad data, that's bad rules.

**Phase to address:** Data quality phase — explicit shadow → enforce ramp.

---

### Pitfall 12 — Adding indexes during a running pipeline locks tables; partition cutover loses rows

**What goes wrong:**
A migration adds `CREATE INDEX ON ohlcv_daily (symbol, date)` (no `CONCURRENTLY`). It runs at 15:46 while the pipeline is mid-write. Migration takes `ACCESS EXCLUSIVE` lock; pipeline `INSERT`s queue; APScheduler job hits its `misfire_grace_time=3600`; eventually a deadlock or the pipeline dies. Worse with partitioning: a naive cutover from non-partitioned → partitioned forgets to backfill the new partitions, "missing" 6 months of OHLCV until someone notices charts go blank pre-2026.

**Why it happens:**
- Alembic generates `CREATE INDEX` (not `CONCURRENTLY`) by default.
- DBAs forget that `CREATE INDEX CONCURRENTLY` cannot run inside a transaction (Alembic wraps migrations in tx by default).
- Partition cutover is a multi-step dance (create new table, copy, swap, drop) — easy to miss copy step.

**How to avoid:**
- For `CREATE INDEX`: use `op.create_index(..., postgresql_concurrently=True)` AND mark the migration `transactional = False` (Alembic) / split into separate migration.
- Schedule schema changes for the *single safe window*: weekday morning before market open, OR weekends (HOSE closed). Add a pre-migration check: `if scheduler.get_job('daily_pipeline').next_run_time within 1h: refuse`.
- For partitioning: use `pg_partman` extension if Supabase exposes it, OR write idempotent backfill script with `INSERT ... SELECT ... ON CONFLICT DO NOTHING` and verify row counts pre/post.
- Always keep old non-partitioned table as `_legacy` for 1 milestone before dropping.
- Test migrations against a Supabase branch / local docker first — never directly on prod.

**Warning signs:**
- `pipeline_duration_seconds` metric spike on migration day.
- Alembic log: `LOCK TABLE ohlcv_daily IN ACCESS EXCLUSIVE MODE`.
- Pre/post row counts disagree after partition cutover.

**Phase to address:** DB optimization phase — migration runbook + maintenance window contract.

---

### Pitfall 13 — Supabase + pgbouncer transaction-mode disables features observability assumes

**What goes wrong:**
`pg_stat_statements` requires `shared_preload_libraries` access — not available on Supabase free tier in the way self-hosted Postgres has it (Supabase exposes a managed view but with quirks). `LISTEN/NOTIFY` doesn't work through transaction-pooled pgbouncer. Prepared statements are disabled (already worked around in code: `prepared_statement_cache_size=0`). Server-side cursors don't persist across statements. Some `EXPLAIN (ANALYZE, BUFFERS)` plans look "wrong" because pgbouncer rewrites.

**Why it happens:**
- Tutorials assume self-hosted Postgres.
- Supabase docs are scattered across "free vs pro" features.

**How to avoid:**
- Verify upfront which observability features Supabase exposes: `pg_stat_statements` is available on Supabase but requires enabling in dashboard (Database → Extensions). Check tier limits.
- Run query analysis using **direct connection** (port 5432) not pooler (port 6543) for `EXPLAIN`. The codebase already has `database_url_migration` pattern — reuse for analysis.
- Don't design pipeline coordination around `LISTEN/NOTIFY`. Stick with APScheduler + DB polling (already used by `process_pending_jobs`).
- Document in PITFALLS / DECISIONS that any "use Postgres feature X" idea must be verified against Supabase first.

**Warning signs:**
- `pg_stat_statements` view returns empty / permission denied.
- Random `prepared statement does not exist` errors (means cache wasn't fully disabled somewhere).
- `EXPLAIN ANALYZE` plan differs between local-dev and prod for "no reason."

**Phase to address:** DB optimization phase — verify Supabase capabilities *before* planning queries around them.

---

## Moderate Pitfalls

### Pitfall 14 — Metrics flush via blocking HTTP push in event loop

`prometheus_client.push_to_gateway` is **synchronous**. Calling it from FastAPI shutdown / from a route blocks the loop for the duration of the push (could be 100ms+ on slow link). Solution: prefer pull model (`/metrics` endpoint via `make_asgi_app()`); if push is needed, run via `asyncio.to_thread`. Phase: Metrics.

### Pitfall 15 — APScheduler job's exception swallowed; no metric or alert fires

If `daily_job` raises, the current code catches and `logger.error`s — but APScheduler also has its own listener system. Without `scheduler.add_listener(EVENT_JOB_ERROR, handler)`, errors don't increment a metric. Add a listener that increments `pipeline_failures_total{job_id=...}` and emits a Telegram alert. Phase: Metrics + Logging.

### Pitfall 16 — Loguru's queue-based async sink is required to avoid blocking under load

Default loguru sinks write **synchronously**. Under request load, each `logger.info` blocks the event loop on disk I/O. Use `logger.add(sink, enqueue=True)` to offload to a worker thread. Phase: Logging.

### Pitfall 17 — PII / secret leakage: API keys, Telegram bot token, DB URL in logs

`Settings` includes `telegram_bot_token`, `vnstock_api_key`, `database_url`. Anyone doing `logger.debug(settings)` or `logger.exception` on a Pydantic ValidationError that includes config dumps the secrets. Add a loguru `patch` that redacts known sensitive keys; pydantic `SecretStr` for all secret fields. Phase: Logging.

### Pitfall 18 — Dashboard auth: "it's local-only so no auth needed" until you `tailscale serve` it

LocalStock binds to localhost. Once a user shares it via Tailscale or ngrok for "checking from phone," the unauthenticated `/admin/*` and `/metrics` are exposed. Add a single shared-secret header check (env var) — trivial to add, prevents drive-by. Phase: Observability infra (when adding Grafana/Prometheus endpoints).

### Pitfall 19 — Index bloat from frequent UPSERTs without `VACUUM` schedule

Daily upserts on `ohlcv_daily` (or scoring tables) create dead tuples. Supabase autovacuum runs but tuning is restricted. After 6 months, indexes can be 2-3x size needed. Add a monthly `REINDEX CONCURRENTLY` job (off-hours) or accept the bloat for v1.5 and document. Phase: DB optimization.

### Pitfall 20 — JSON log parser failures (one bad log = lost batch)

When you ship logs to a JSON parser (Vector / Promtail / Grafana Loki), one log line with an un-serializable field (datetime, Decimal, custom class) can fail the entire batch. Use a robust serializer: `json.dumps(record, default=str)`. Add a unit test that round-trips realistic log records. Phase: Logging.

### Pitfall 21 — Test fixtures share singleton engine; one slow test poisons the pool

`get_engine()` returns a module-global. In pytest, if any test forgets to close a session (or holds it via a fixture without scope cleanup), the singleton pool stays exhausted across tests. Use `pytest-asyncio` with `loop_scope="function"` and override `get_engine` in conftest to use a NullPool for tests. Phase: covers Caching/Metrics/Logging — anything adding singletons.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| In-memory cache (dict) instead of Redis | No new infra, ship caching this week | Lost on restart, no cross-process invalidation, can't scale to 2 workers | Acceptable for v1.5 single-process; document upgrade path |
| TTL-only cache (no version key) | Simple, "good enough" | Stale data after pipeline; user trust erodes when ranks lag | Never for ranking/scoring; fine for static dictionary data |
| Skip `CREATE INDEX CONCURRENTLY` because table is small | Migration runs in 1s | First time pipeline + migration overlap, table locks, pipeline aborts | Only on truly cold tables (dim tables, < 10k rows) |
| Per-symbol metrics labels | Easy "per-symbol" dashboards | Cardinality explosion, prometheus OOM | Never — use logs+exemplars, or a `failure` table |
| `validate_or_raise()` on day 1 | "Strict from start" feels rigorous | Pipeline aborts; data loss; trust loss | Never as default; always shadow → ramp |
| `logger.info(f"...")` everywhere | Familiar, no cognitive load | Unstructured logs, can't aggregate, painful migration | OK for local dev; lint-rejected in CI |
| `pool_size=3` (current) | "Single user" sizing | Pipeline + UI contention; pool exhaustion | Was fine for v1.0-v1.4; v1.5 must raise |
| Skip `pool_timeout` tuning (default 30s) | Defaults | 30s spinners hide real problems | Set to 5s and surface as metric |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| **asyncpg + Supabase pgbouncer** | Leaving prepared-statement cache enabled | Set `prepared_statement_cache_size=0, statement_cache_size=0` (already done — preserve!) |
| **SQLAlchemy + asyncio.gather** | One session shared across gathered coroutines | One session per coroutine; sessions are NOT concurrency-safe |
| **APScheduler + FastAPI lifespan** | Starting scheduler at import time | Start in `lifespan()` only; tests use TestClient which triggers lifespan once |
| **APScheduler + tests** | `scheduler.start()` in conftest causes tests to fire jobs | Use `scheduler.start(paused=True)` or replace with mock in tests |
| **Ollama + httpx async client** | Reusing client without timeout, hangs forever | `httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=ollama_timeout))` |
| **Ollama + concurrent requests** | Calling `gather` over 20 LLM requests | Ollama serves one request per model copy; semaphore=1 unless multi-instance |
| **vnstock + asyncio** | vnstock is **sync**; awaiting it directly does nothing parallel | Wrap with `asyncio.to_thread(vnstock.fn, args)`; cap with semaphore |
| **prometheus_client + multiprocess** | One registry across uvicorn workers | Use `multiprocess.MultiProcessCollector` with `PROMETHEUS_MULTIPROC_DIR` (or stick to 1 worker — current arch) |
| **pandas-ta + numpy 2.x** | Latest pandas-ta expects numpy<2 in places | Pin numpy/pandas/pandas-ta versions together; verify in CI |
| **Loguru + structlog/stdlib logging** | Mixing both creates duplicate handlers | Pick one (loguru is already chosen); use `InterceptHandler` to route stdlib `logging` into loguru |
| **Alembic + async engine** | Running migrations against asyncpg URL | Use sync URL (`postgresql+psycopg://`) for migrations — already factored as `database_url_migration` |
| **JSONB + Pydantic** | Pydantic emitting `NaN`/`Infinity` floats into JSONB | Sanitize at boundary; use `model_config = {'json_encoders': {float: lambda v: None if math.isnan(v) else v}}` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| Sync CPU work in async handler | Health check fails during pipeline | `asyncio.to_thread` for pandas-ta; vectorize over symbols | Always — but unnoticed until 400 symbols |
| Cache stampede on cold start | First load 10x slower; pool timeouts | Single-flight + pre-warm at end of pipeline | After every restart / Redis flush |
| N+1 in repository (per-symbol fetch) | Pipeline ~400× DB round-trips | `selectinload` / batch IN-list; one query per stage | At ~50 symbols becomes noticeable |
| Pool too small + concurrent scheduler | `QueuePool limit reached` at 15:45 | `pool_size=10`, `pool_timeout=5` | Daily, predictably |
| Per-symbol `/api/...` fan-out | Dashboard load = 50+ requests | Aggregate `/api/dashboard/summary` | Always — gets worse with more components |
| Unbounded prometheus labels | `/metrics` >1MB; scrape timeouts | Label budget; never `symbol` label | After ~weeks of accumulation |
| `logger.add(sink)` without `enqueue=True` | p99 latency tracks log volume | `enqueue=True` makes logging async | Under request burst |
| Reading entire OHLCV history per request | Memory + DB time grow with history age | Use `LIMIT` + cursor; cache per (symbol,date) | After 2+ years of history |
| Re-computing indicators every request | CPU pegged on dashboard load | Cache indicators with `(symbol, last_ohlcv_date)` key; invalidate on pipeline | After ~10 concurrent users (or one user clicking fast) |
| Telegram blocking pipeline | Pipeline waits 30s on Telegram timeout | Send notifications in fire-and-forget task; don't block scoring | When Telegram has incidents |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Logging full `Settings` object on startup | Telegram token + Supabase URL in logs | Use `pydantic.SecretStr`; redact in custom loguru formatter |
| `/metrics` exposed without auth | Reveals symbol counts, pipeline timing — minor info leak; can DoS via scrape | Bind to localhost OR require shared-secret header |
| `/admin/*` endpoints unauthenticated "because local" | Once tunneled (ngrok/tailscale), instant takeover | Single shared-secret header (`X-Admin-Token`) — 10 lines of code |
| SQL constructed via f-string for "trusted" symbol input | symbol comes from user input via admin add-stock | Parametrize all SQL; SQLAlchemy ORM avoids by default — audit any `text()` |
| Storing Ollama prompt verbatim in logs | Prompts may include user-added notes / private context | Hash prompts; log hash + length, not body |
| Telegram bot token in `.env` committed | Git history leak | `.env` in `.gitignore`; verify with `git log -p .env` |
| `ssl_verify=False` for "behind proxy" left on in prod | MITM possible | Default true; environment-specific override; audit on each deploy |

---

## "Looks Done But Isn't" Checklist

- [ ] **Caching:** TTL set but no `pipeline_version` key — verify cache key includes `scoring_run_id` or invalidates on pipeline end.
- [ ] **Caching:** Single-flight tested under concurrent cold start (run 50 parallel requests post-restart).
- [ ] **Logging:** JSON sink configured but f-string log lines remain — `grep -r 'logger\.[a-z]*(f"' src/` returns 0.
- [ ] **Logging:** `loguru` `enqueue=True` set on file/network sinks (verify via `logger._core.handlers`).
- [ ] **Metrics:** `/metrics` size < 100KB AND scrape duration < 200ms; cardinality audit script in CI.
- [ ] **Metrics:** Test for `Duplicated timeseries` regression (run app→tests→app sequence).
- [ ] **Pipeline parallelism:** Concurrency cap (semaphore) verified via metric `crawl_concurrent_inflight ≤ N`.
- [ ] **Pipeline parallelism:** `gather(..., return_exceptions=True)` everywhere; no single symbol can fail batch.
- [ ] **Pipeline parallelism:** CPU-bound code wrapped in `to_thread`; event-loop lag metric < 50ms.
- [ ] **Data quality:** Validators run in shadow mode for ≥1 week; baseline failure rate documented.
- [ ] **Data quality:** NaN/Inf sanitizer at JSONB boundary tested with new-stock fixture (< 14 days history).
- [ ] **DB:** All v1.5 migrations use `CREATE INDEX CONCURRENTLY` AND run in maintenance window.
- [ ] **DB:** `pg_stat_statements` verified enabled on Supabase before claiming query analysis is "ready."
- [ ] **DB:** Pool config raised; `pool_timeout=5`; metric `db_pool_in_use` exists.
- [ ] **Scheduler:** `EVENT_JOB_ERROR` listener attached; pipeline failures emit metric + Telegram alert.
- [ ] **Tests:** Singleton state (engine, scheduler, prometheus registry, loguru handlers) reset between tests.
- [ ] **Secrets:** `pydantic.SecretStr` on all secret fields; redaction tested by logging Settings on purpose.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Stale cache after pipeline | LOW | Add `pipeline_version` bump; flush cache; redeploy |
| Cache stampede | LOW | Add semaphore/single-flight; restart |
| Pool exhaustion | LOW | Raise `pool_size`; restart; add metric for next time |
| Prometheus cardinality blowup | MEDIUM | Drop offending metric (delete, don't relabel); restart prom-client; redesign labels |
| Loguru double-init duplicate logs | LOW | Add `logger.remove()` to setup; restart |
| NaN in JSONB | MEDIUM | One-time SQL: `UPDATE ... SET content_json = jsonb_strip_nans(content_json)`; deploy sanitizer; backfill |
| Validation breaking pipeline | LOW | Flip feature flag to shadow mode; analyze rules; re-enable selectively |
| vnstock soft-ban | HIGH (waiting) | Stop pipeline immediately; wait 24h; reduce concurrency to 2; resume; document new ceiling |
| Index lock during pipeline | MEDIUM | `pg_cancel_backend()` the migration; rerun with `CONCURRENTLY` in maintenance window; replay missed pipeline |
| Partition cutover lost rows | HIGH | Restore from Supabase backup; replay backfill from sources (vnstock has historical) |
| Secrets in logs | HIGH (rotation) | Rotate Telegram token + DB password + vnstock key; audit log shipping destinations; add `SecretStr` |
| Ollama hang blocks pipeline | LOW | Add httpx timeout; restart Ollama; pipeline picks up next day |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| 1 — Stale cache after writes | Caching (+ Scheduler hook) | Integration test: write → cache invalidated within same process |
| 2 — Cache stampede | Caching | Load test: 50 concurrent cold requests succeed |
| 3 — Async-unsafe cache backend | Caching | Lint: no `@lru_cache` on `async def`; cache backend documented |
| 4 — f-string log spam | Logging | CI lint rule rejecting `logger\.\w+\(f"` |
| 5 — Loguru/Prometheus double-init | Logging + Metrics | Test runs full app→test→app cycle without "Duplicated" errors |
| 6 — High-cardinality labels | Metrics | CI: `/metrics` size + series count assertions |
| 7 — pandas-ta blocking event loop | Pipeline parallelism | Metric `event_loop_lag_seconds` < 0.05 during pipeline |
| 8 — vnstock rate-limit | Pipeline parallelism | Semaphore in code; circuit-breaker metric exists |
| 9 — Pool exhaustion | Pipeline parallelism (+ DB) | Metric `db_pool_wait_seconds` p99 < 0.1 |
| 10 — NaN in JSONB | Data quality | Unit test: < 14-day-history symbol round-trips through API |
| 11 — Validation breaking pipeline | Data quality | Feature flag `validation_mode=shadow|enforce`; flag tested |
| 12 — Index lock / partition cutover | DB optimization | Migration runbook checked into repo; rehearsed on Supabase branch |
| 13 — Supabase pgbouncer caveats | DB optimization | DECISIONS.md entry; `pg_stat_statements` extension verified |
| 14 — Blocking metrics push | Metrics | Pull model (ASGI app) preferred; if push, `to_thread` |
| 15 — Scheduler swallows errors | Metrics + Logging | EVENT_JOB_ERROR listener test |
| 16 — Synchronous loguru sink | Logging | `enqueue=True` audit |
| 17 — PII/secret leakage | Logging | `SecretStr` audit; redaction unit test |
| 18 — Dashboard auth | Observability infra | Header check + test |
| 19 — Index bloat | DB optimization | Monthly REINDEX job (or accept + document) |
| 20 — JSON parser failures | Logging | Round-trip serializer test |
| 21 — Test pool poisoning | Cross-cutting (test infra) | conftest uses NullPool override |

---

## Sources

- LocalStock codebase inspection: `apps/prometheus/src/localstock/{db/database.py, scheduler/scheduler.py, config.py}` (HIGH).
- SQLAlchemy 2.x docs — async pool / `pool_timeout` / `selectinload` semantics (HIGH, official).
- asyncpg + pgbouncer transaction-mode known-issue thread (MagicStack/asyncpg #339, #819) — verified via training data + matches existing `prepared_statement_cache_size=0` workaround in code (MEDIUM-HIGH).
- Supabase docs — connection pooling modes, `pg_stat_statements` extension availability (MEDIUM; tier-dependent).
- APScheduler docs — `AsyncIOScheduler`, listener events, `misfire_grace_time` (HIGH, official).
- prometheus_client (Python) — cardinality guidance, `multiprocess` mode, registry duplication (HIGH).
- loguru docs — `enqueue=True`, `logger.remove()`, `bind()`/extra fields (HIGH).
- pandas-ta GitHub issues — numpy compatibility, GIL behavior of rolling functions (MEDIUM).
- vnstock README + community issues — soft-rate-limit reports on free sources (MEDIUM, anecdotal).
- Personal pattern library: cache versioning via run-id, shadow→enforce validation rollout, two-tier validators (HIGH for the *patterns*, applied to this stack here).

---
*Pitfalls research for: LocalStock v1.5 Performance & Data Quality (existing async-FastAPI + asyncpg + Supabase + APScheduler stack)*
*Researched: 2026-04-28*
