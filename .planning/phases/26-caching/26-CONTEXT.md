---
phase: 26
name: Caching
milestone: v1.5
status: context-locked
created: 2026-04-29
mode: auto-accept (user accepted all recommendations 2026-04-29)
requirements: [CACHE-01, CACHE-02, CACHE-03, CACHE-04, CACHE-05, CACHE-06, CACHE-07]
---

# Phase 26 — Caching: Context & Locked Decisions

## Goal (verbatim from ROADMAP)

Hot read-paths (`/api/scores/ranking`, `/api/market/summary`, indicator computations) trả về < 50 ms p95 từ cache, invalidate đúng lúc pipeline ghi xong, không stampede khi cache cold — phải có invalidation hooks trước Phase 27.

## Success Criteria (verbatim from ROADMAP)

1. `/api/scores/ranking` lần thứ 2 (cùng `pipeline_run_id`) trả về < 50 ms p95 với header/log `cache=hit`; lần đầu sau pipeline write `cache=miss`
2. Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data, không cần đợi TTL
3. Concurrent 100 requests vào cùng cold key chỉ trigger 1 backend computation (single-flight via `asyncio.Lock`) — verified bằng counter `cache_compute_total` chỉ tăng 1
4. Sau `run_daily_pipeline`, cache cho hot keys (ranking + market summary) đã pre-warm — first request từ user log `cache=hit` không phải `miss`
5. `/metrics` expose `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` với label `namespace`; `cache_janitor` job chạy mỗi 60s và log số entries swept

## Locked Decisions

### D-01 — Versioning Key: `pipeline_run_id`
**LOCKED**: Use `pipeline_run_id` (the integer PK from `pipeline_runs` table) as the version component in cache keys for scoring/ranking outputs.

- Rationale: deterministic, monotonic, atomic with the write boundary; ROADMAP allows "pipeline_run_id OR latest_ohlcv_date" — pick the former for SC #2 testability.
- Cache key shape: `scores:ranking:run={pipeline_run_id}` for ranking, `market:summary:run={pipeline_run_id}` for market summary.
- For indicators: `indicators:{indicator_name}:{symbol}:run={pipeline_run_id}` (D-06).
- Reader access path: every cached read fetches `latest_pipeline_run_id` from `PipelineRunRepository.get_latest_completed()` (cached for 5s itself to avoid hot-loop DB hits) and composes the key.
- Pipeline writers do NOT mint keys — they bump the version by completing a new run. Readers always include the latest run_id.

### D-02 — TTL Strategy: Per-Namespace
**LOCKED**: Each cache namespace declares its own TTL; version key is the primary correctness mechanism, TTL is secondary memory-safety.

| Namespace | TTL | Rationale |
|---|---|---|
| `scores:ranking` | 24 h | One pipeline run per day; old run_ids age out by next day |
| `scores:symbol` | 24 h | Per-symbol latest score |
| `market:summary` | 1 h | Macro/sector aggregates change less than per-symbol |
| `indicators:*` | 1 h | Pandas-ta outputs; bounded by run_id, TTL is pure memory cap |
| `pipeline:latest_run_id` | 5 s | Lookup of latest completed run; brief cache to avoid stampede on cache_get |

Implementation: namespace registry maps name → `TTLCache(maxsize, ttl)`. Maxsize per namespace also configurable.

### D-03 — Single-Flight: Per-Key `asyncio.Lock` via WeakValueDictionary
**LOCKED**: Single-flight implemented as a per-key `asyncio.Lock` lazy-allocated in a `weakref.WeakValueDictionary` keyed by full cache key. When the last awaiter releases the lock, GC reclaims it.

- Pattern (CACHE-04):
  ```python
  async def get_or_compute(key, compute_fn, namespace, ttl):
      cached = _caches[namespace].get(key)
      if cached is not None:
          metrics.cache_hits_total.labels(namespace=namespace).inc()
          return cached
      lock = _locks.setdefault(key, asyncio.Lock())  # WeakValueDictionary
      async with lock:
          # double-check after lock acquired
          cached = _caches[namespace].get(key)
          if cached is not None:
              metrics.cache_hits_total.labels(namespace=namespace).inc()
              return cached
          metrics.cache_misses_total.labels(namespace=namespace).inc()
          metrics.cache_compute_total.labels(namespace=namespace).inc()
          value = await compute_fn()
          _caches[namespace][key] = value
          return value
  ```
- Pitfall: `setdefault` on a WeakValueDictionary can be racy with GC. Mitigation: hold a strong local ref to `lock` for the lifetime of the `async with`. Standard pattern, well-tested in production caches.
- Counter `cache_compute_total{namespace}` is the SC #3 verification gate — must increment exactly once per (key, cold-fill) regardless of concurrency.

### D-04 — Invalidation: Eager Purge + Version Bump (Belt + Suspenders)
**LOCKED**: After each pipeline write phase that produces cacheable outputs, `automation_service.py` (or `services/pipeline.py` finalize) calls `cache.invalidate_namespace(name)` for each affected namespace. Version key in subsequent reads is independent backup.

- Affected namespaces (called from pipeline finalize, AFTER successful write):
  - `scores:ranking`, `scores:symbol` — invalidated after scoring phase
  - `market:summary` — invalidated after sector + macro phase
  - `indicators:*` — invalidated after indicator computation phase (or skipped if pre-warmed in same run)
- `invalidate_namespace(name)` purges the entire namespace dict (`_caches[name].clear()`).
- Version key + eager purge is intentional defense-in-depth: in single-process deployment they're redundant, but if v1.6 introduces multi-worker uvicorn the version key keeps cross-worker cache safe even if one worker missed the invalidation signal.

### D-05 — Pre-Warm: Minimal Hot-Path Coverage
**LOCKED**: Pre-warm exactly two endpoints at end of `run_daily_pipeline`:
1. `/api/scores/top` (default params — top 50, all sectors)
2. `/api/market/summary`

Pre-warm step calls each endpoint's underlying service method (NOT the HTTP handler — bypass middleware) and stores under the canonical cache key. Indicator caches are pre-warmed implicitly during the analyze phase (D-06).

- Future expansion (deferred): per-sector ranking, top-by-grade, top-by-recommendation.
- Trigger point: `Pipeline.run_full` step after `report` phase, before Telegram dispatch.
- Failure mode: pre-warm errors are logged + counted but DO NOT fail the pipeline (try/except with `cache_prewarm_errors_total{namespace}` counter).

### D-06 — Indicator Computation Cache: Per-Symbol Bundle (RATIFIED 2026-04-29)
**LOCKED**: Pandas-ta indicator computations cached per `(symbol, pipeline_run_id)` at the `analyze_technical_single` function boundary in `analysis_service.py`.

- Cache key: `indicators:{symbol}:run={run_id}`
- **Key simplification (research Q-B ratified)**: drop the `{indicator_name}` segment. Rationale: pandas-ta computes all 11 indicators in one bundled call (`analyze_technical_single`); per-indicator keys would fragment cache and force redundant computation. Per-symbol-per-run is the natural boundary.
- TTL 1 h, maxsize ~600 (~400 symbols × 1.5 buffer).
- Wired at `analysis_service.py:264` (verified in research §2).
- Major CPU win: pandas-ta runs ~50-100ms per symbol bundle; cache hit returns in microseconds.
- Pre-warm: implicit — when analysis phase populates indicators for all 400 symbols, the cache is hot for any subsequent `/api/analysis/{symbol}` reads in the same run.
- Memory budget (research Q-5): worst case ~9 MB total for full 400-symbol coverage; well under any reasonable container ceiling.

### D-07 — Cache Module: `src/localstock/cache/` Package
**LOCKED**: New top-level package `src/localstock/cache/` mirroring the `dq/` pattern from Phase 25.

```
src/localstock/cache/
  __init__.py        # public API: get_or_compute, invalidate_namespace
  registry.py        # namespace → TTLCache mapping; declares TTLs/maxsizes per D-02
  single_flight.py   # WeakValueDictionary lock manager (D-03 pattern)
  invalidate.py      # invalidate_namespace + helper for pipeline finalize hooks
  prewarm.py         # pre-warm orchestrator called from Pipeline.run_full (D-05)
  janitor.py         # APScheduler job (D-08)
  middleware.py      # FastAPI middleware that reads namespace+key from request, adds X-Cache: hit|miss header (SC #1)
```

- Public surface kept narrow: routes import only `get_or_compute` + `invalidate_namespace`.
- Settings additions: `CACHE_RANKING_TTL_SECONDS=86400`, `CACHE_MARKET_TTL_SECONDS=3600`, `CACHE_INDICATORS_TTL_SECONDS=3600`, `CACHE_INDICATORS_MAXSIZE=600`, `CACHE_JANITOR_INTERVAL_SECONDS=60`.
- All settings have sensible defaults; env override only.

### D-08 — Janitor + Telemetry
**LOCKED**:
- **Janitor**: APScheduler `cache_janitor` job, IntervalTrigger 60 s (per CACHE-06). Sweeps each namespace's TTLCache by calling `cache.expire()` (cachetools native; pops expired keys eagerly, returning swept count). Logs `cache.janitor.sweep` with per-namespace counts. Job decorated `@observe('cache.janitor.sweep')`.
- **Header**: FastAPI middleware adds `X-Cache: hit | miss` to responses for the cached routes (SC #1). Middleware reads a request-context flag set by `get_or_compute` (contextvars, similar to Phase 22 correlation_id pattern). NOT every route — only the ones that called into the cache.
- **Metrics** (CACHE-07, SC #5) — label is `cache_name` (RATIFIED 2026-04-29 to match existing `observability/metrics.py` scaffolding from prior phases; was `namespace` in original CONTEXT):
  - `cache_hits_total{cache_name}` — incremented on cache hit (already declared in metrics.py)
  - `cache_misses_total{cache_name}` — incremented on cache miss (already declared)
  - `cache_evictions_total{cache_name}` — incremented on eviction (already declared); subclass `TTLCache.popitem` to attribute reason='expire'|'evict' (research Q-2)
  - `cache_compute_total{cache_name}` — NEW; incremented inside the lock (SC #3 gate)
  - `cache_prewarm_errors_total{cache_name}` — NEW; incremented on pre-warm failure (D-05)
- **Cardinality**: only `cache_name` label; never include the actual cache key (would explode cardinality on `indicators:*`). Total label combinations: ~5 cache_names × 5 metrics = 25 series.

### Hook Location Correction (RATIFIED 2026-04-29)

CONTEXT originally referenced `services/pipeline.py` for D-04 (invalidate) and D-05 (pre-warm) hooks. **Research §3+§4 verified the actual home is `services/automation_service.py`** — scoring/sentiment/reports/sector phases all run inside `AutomationService.run_daily_pipeline`, not `Pipeline.run_full`. Plans should target `automation_service.py` lines 109/142/174 (invalidate after each write phase) and line 175 (pre-warm between sector rotation and `_send_notifications`).

## Affected Files (preliminary scope — research will expand)

**New files** (D-07):
- `apps/prometheus/src/localstock/cache/__init__.py`
- `apps/prometheus/src/localstock/cache/registry.py`
- `apps/prometheus/src/localstock/cache/single_flight.py`
- `apps/prometheus/src/localstock/cache/invalidate.py`
- `apps/prometheus/src/localstock/cache/prewarm.py`
- `apps/prometheus/src/localstock/cache/janitor.py`
- `apps/prometheus/src/localstock/cache/middleware.py`
- `apps/prometheus/tests/test_cache/...`

**Modified files** (preliminary):
- `apps/prometheus/src/localstock/api/routes/scores.py` — wrap `/scores/top` with `get_or_compute`
- `apps/prometheus/src/localstock/api/routes/market.py` — wrap `/market/summary` with `get_or_compute`
- `apps/prometheus/src/localstock/services/analysis_service.py` — wrap indicator computations (D-06)
- `apps/prometheus/src/localstock/services/pipeline.py` — pre-warm hook + invalidate hooks (D-04, D-05)
- `apps/prometheus/src/localstock/scheduler/scheduler.py` — register janitor job (D-08)
- `apps/prometheus/src/localstock/api/app.py` — register cache middleware (D-08)
- `apps/prometheus/src/localstock/observability/metrics.py` — declare cache counters
- `apps/prometheus/src/localstock/config.py` — add cache settings
- `pyproject.toml` — add `cachetools>=5,<6` dependency

## Open Questions (deferred to research)

1. **Q-1 ROADMAP naming drift**: ROADMAP references `/api/scores/ranking` but actual endpoint is `/api/scores/top`. Researcher to confirm whether to (a) keep `/scores/top` and update ROADMAP, or (b) introduce `/scores/ranking` as alias. **Recommendation**: (a) — update ROADMAP, keep `top`.
2. **Q-2 Eviction counter source**: `cachetools.TTLCache` does not natively emit eviction events. Options: subclass + override `popitem`, or compute delta from janitor sweep. Researcher to pick lowest-friction approach.
3. **Q-3 Pre-warm coupling**: Pre-warm calls service methods directly. If service methods themselves use `get_or_compute`, the pre-warm becomes a no-op (cache is filled by the service call, not by pre-warm itself). Researcher to confirm flow + ensure pre-warm doesn't spawn its own concurrent computation.
4. **Q-4 Test strategy for SC #1 < 50ms p95**: Property test or perf benchmark? `pytest-benchmark` already a dep? Researcher to scope the perf test approach.
5. **Q-5 Indicator cache memory budget**: 600 entries per indicator × ~10 indicators = 6000 entries. Each `pd.Series` of 252 daily bars × 8 bytes = ~2 KB. Total ~12 MB. Researcher to validate against expected memory ceiling.

## Threats & Mitigations (preliminary)

- **T-26-01 Stampede**: Cold-start of hot key when 100 concurrent requests land. Mitigation: D-03 single-flight; SC #3 verifies.
- **T-26-02 Stale read**: Pipeline writes new scores but reader still sees old cache. Mitigation: D-01 version key + D-04 eager invalidation.
- **T-26-03 Memory unbounded growth**: Indicator cache leaks across runs if eviction fails. Mitigation: D-02 TTL + D-08 janitor 60s + maxsize.
- **T-26-04 Lock leak**: WeakValueDictionary lock leaks if a coroutine holds strong ref forever. Mitigation: standard `async with` pattern releases ref at scope exit.
- **T-26-05 Pre-warm race**: Pre-warm runs concurrent with first user request. Mitigation: D-03 lock makes pre-warm + first request collapse to single computation.
- **T-26-06 Janitor blocks event loop**: Sweep over many namespaces could be slow. Mitigation: each namespace `.expire()` is O(expired-keys); total runtime expected sub-millisecond. If problematic, run in `asyncio.to_thread`.

## Next Step

Run `/gsd-plan-phase 26` (with `--research` flag if needed) to produce RESEARCH.md + per-plan PLAN.md files.
