# Phase 26: Caching — Research

**Researched:** 2026-04-29
**Domain:** Async in-process caching (FastAPI + asyncio + cachetools.TTLCache)
**Confidence:** HIGH (codebase verified) / MEDIUM (cachetools API details verified against current PyPI metadata)

## Summary

All eight CONTEXT.md decisions (D-01..D-08) are implementable as written against the current `apps/prometheus/` codebase. The cache infrastructure is greenfield (no existing TTLCache usage), but several scaffolding pieces are already in place: `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` Prometheus counters are already declared in `observability/metrics.py` (using label `cache_name` — not `namespace` — see Open Question Q-A below); `CorrelationIdMiddleware` provides a working contextvar+header pattern that the X-Cache middleware should mirror; APScheduler `IntervalTrigger` jobs have a precedent (`health_self_probe`).

The biggest implementation surface is `automation_service.py` rather than `pipeline.py`: scoring/sentiment/reports/sector phases all run in `AutomationService.run_daily_pipeline`, not in `Pipeline.run_full`. This shifts the invalidation and pre-warm hook locations relative to CONTEXT's wording. Indicator caching (D-06) cannot cleanly key per-indicator because `TechnicalAnalyzer.compute_indicators` computes all 11 indicators in a single pandas-ta call that mutates one DataFrame; the natural cache boundary is per-symbol-per-run, not per-indicator-per-symbol-per-run.

**Primary recommendation:** Build the package exactly as D-07 specifies, locate the invalidate hooks in `automation_service.py` (not `pipeline.py`), pre-warm hook between sector rotation (line 174) and `_send_notifications` (line 177), cache indicator outputs at the `analyze_technical_single(symbol, ohlcv_df) -> dict` boundary in `analysis_service.py:264`, and use the existing `cache_name` Prometheus label rather than introducing a parallel `namespace` label.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** Versioning key = `pipeline_run_id` (integer PK from `pipeline_runs`). Key shapes: `scores:ranking:run={id}`, `market:summary:run={id}`, `indicators:{name}:{symbol}:run={id}`. Reader path fetches `latest_pipeline_run_id` via a new `PipelineRunRepository.get_latest_completed()` (cached 5s itself).
- **D-02** TTL per namespace: `scores:ranking` 24h, `scores:symbol` 24h, `market:summary` 1h, `indicators:*` 1h, `pipeline:latest_run_id` 5s. Namespace registry maps name → `TTLCache(maxsize, ttl)`.
- **D-03** Single-flight: per-key `asyncio.Lock` lazy-allocated in `weakref.WeakValueDictionary`. Strong local ref held for `async with` lifetime. `cache_compute_total{namespace}` increments inside lock.
- **D-04** Eager invalidation + version-key: pipeline finalize calls `invalidate_namespace(name)` after each successful write phase. Affected: scoring → `scores:ranking`+`scores:symbol`; sector+macro → `market:summary`; analysis → `indicators:*`.
- **D-05** Pre-warm exactly two endpoints at end of `run_daily_pipeline`: `/api/scores/top` (top 50, all sectors) and `/api/market/summary`. Bypasses HTTP, calls service methods directly. Failures logged + counted, never fail pipeline.
- **D-06** Indicator computations cached per `(indicator_name, symbol, pipeline_run_id)` in `indicators` namespace, TTL 1h, maxsize 600. Wired in `analysis_service.py`.
- **D-07** New package `src/localstock/cache/` with files: `__init__.py`, `registry.py`, `single_flight.py`, `invalidate.py`, `prewarm.py`, `janitor.py`, `middleware.py`. Public API: `get_or_compute`, `invalidate_namespace`. Add `cachetools>=5,<6` to pyproject.toml.
- **D-08** APScheduler `cache_janitor` IntervalTrigger 60s, `@observe('cache.janitor.sweep')`. FastAPI middleware adds `X-Cache: hit|miss` reading a contextvar set inside `get_or_compute`. Metrics: `cache_hits_total`, `cache_misses_total`, `cache_compute_total`, `cache_evictions_total`, `cache_prewarm_errors_total` — all labelled by `namespace` only.

### the agent's Discretion (Q-1..Q-5 — resolved below)

- Q-1 ROADMAP route naming
- Q-2 Eviction counter implementation
- Q-3 Pre-warm coupling with `get_or_compute`
- Q-4 Perf test mechanism for SC #1
- Q-5 Indicator cache memory budget

### Deferred Ideas (OUT OF SCOPE)

- Per-sector ranking pre-warm, top-by-grade, top-by-recommendation pre-warm (D-05 explicitly defers).
- Multi-process/multi-worker uvicorn cache coherence (D-04 mentions as v1.6 hypothetical; not built now).
- Redis or out-of-process cache (CONTEXT scope is in-process `cachetools.TTLCache`).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CACHE-01 | Hot read paths < 50ms p95 from cache, with `cache=hit` header | Q-4 below + middleware section |
| CACHE-02 | Version-aware keys with `pipeline_run_id` | D-01 + audit of `pipeline_runs` table model |
| CACHE-03 | Invalidate after pipeline write boundaries | D-04 audit list below |
| CACHE-04 | Single-flight via `asyncio.Lock` per key | D-03 + Pitfalls P-2/P-3 |
| CACHE-05 | Pre-warm hot keys at end of `run_daily_pipeline` | D-05 audit list below |
| CACHE-06 | Janitor sweep every 60s with eviction counter | D-08 + Q-2 |
| CACHE-07 | Cache metrics labelled by namespace | Q-A note: existing label is `cache_name` |

---

## 1. Open Question Resolutions

### Q-1: Route naming `/scores/top` vs `/scores/ranking` — RESOLVED

**Verified facts:**
- `apps/prometheus/src/localstock/api/routes/scores.py:21` defines `@router.get("/scores/top")`. No `/ranking` route exists. [VERIFIED: grep]
- `apps/helios/src/lib/queries.ts:25` calls `apiFetch<TopScoresResponse>(\`/api/scores/top?limit=${limit}\`)`. [VERIFIED: grep]
- ROADMAP §"Phase 26" line 144 + line 148 reference `/api/scores/ranking` (drift).

**Recommendation: keep `/scores/top`, update ROADMAP §"Phase 26" to use `/scores/top` everywhere.** Cache key remains `scores:ranking:run={id}` (the namespace name `scores:ranking` describes the *content* — the ranking — independent of the route name). Renaming the route would break Helios; the route name has no functional bearing on cache correctness. [HIGH confidence]

**Action for plan:** A documentation-only patch to `.planning/ROADMAP.md` lines ~73, 143-148 — search-and-replace `/api/scores/ranking` → `/api/scores/top`. Not a code change.

### Q-2: Eviction counter implementation — RESOLVED

**Approach:** Subclass `cachetools.TTLCache` and override `popitem()` (the method called by both LRU eviction-on-overflow AND TTL expiration via `expire()`). Increment `cache_evictions_total{cache_name=ns, reason=evict|expire}` from inside the override.

**Why subclass over delta-from-janitor:**
- Delta-from-janitor only catches TTL expirations, not maxsize-overflow evictions. We need both.
- Subclass overhead is one method call per eviction (negligible vs. amortised insert cost).
- The existing `cache_evictions_total` counter in `observability/metrics.py:171-178` already has a `reason` label (`evict|expire`) — confirming this is the intended design.

**Distinguishing reason:** The cleanest signal is *who is calling*: if `popitem` is called from inside `expire()` → reason=expire; otherwise → reason=evict. cachetools 5.x routes both through `popitem`, so the subclass needs a tiny piece of state:

```python
class InstrumentedTTLCache(TTLCache):
    def __init__(self, maxsize, ttl, namespace):
        super().__init__(maxsize=maxsize, ttl=ttl)
        self._namespace = namespace
        self._in_expire = False  # set by overridden expire()

    def expire(self, time=None):
        self._in_expire = True
        try:
            return super().expire(time)
        finally:
            self._in_expire = False

    def popitem(self):
        key, value = super().popitem()
        reason = "expire" if self._in_expire else "evict"
        get_metrics()["cache_evictions_total"].labels(
            cache_name=self._namespace, reason=reason
        ).inc()
        return key, value
```

[CITED: cachetools 5.x source — `cachetools/__init__.py` defines `TTLCache.expire` calling `self.popitem()` in a loop, and `Cache.__setitem__` calling `self.popitem()` when over maxsize.] [HIGH confidence on the pattern; MEDIUM on the exact internal call shape — verify by reading installed cachetools source after `uv sync`.]

### Q-3: Pre-warm flow — RESOLVED

**Confirmed flow (no double-compute):**

Pre-warm calls the service method directly (e.g. `ScoringService.get_top_ranked(limit=50)`). The service method itself calls `get_or_compute(key="scores:ranking:run=N", compute_fn=...)`.

- **First call (the pre-warm):** cache miss → acquires lock → executes `compute_fn` → stores under key. Increments `cache_compute_total` once.
- **Second call (real user request right after):** cache hit → returns immediately. No second computation.

The single-flight lock (D-03) guarantees that even if the pre-warm and a concurrent user request collide, only one `compute_fn` runs. Pre-warm is not an independent path — it is the first caller through the same `get_or_compute` choke point.

**Pitfall to encode in plan:** The pre-warm step must NOT bypass `get_or_compute` and write directly into `_caches[ns][key]`. Direct write would skip the lock and skip the `cache_compute_total` increment, and would race with any concurrent user request that already entered the lock. Always go through `get_or_compute`. [HIGH confidence]

### Q-4: Perf test mechanism for SC #1 (< 50ms p95) — RESOLVED

**Verified state:**
- `pytest-benchmark` is **NOT** in `apps/prometheus/pyproject.toml` (verified in dependency-groups.dev: only `pytest`, `pytest-asyncio`, `pytest-timeout`). [VERIFIED]
- `pytest-timeout` is configured with `timeout = 30` per `[tool.pytest.ini_options]`. [VERIFIED]

**Recommendation: do NOT add `pytest-benchmark`.** Use a hand-rolled perf assertion with `time.perf_counter` and `statistics.quantiles`. Rationale: adding a new test dependency for a single SC introduces churn; the 50ms gate is coarse enough that simple wall-clock measurement is sufficient.

**Test pattern (proposed):**

```python
# apps/prometheus/tests/test_cache/test_perf_ranking.py
import time, statistics
import pytest

@pytest.mark.asyncio
async def test_ranking_cache_hit_p95_under_50ms(client, seeded_pipeline_run):
    # Warm the cache with one call (miss)
    r0 = await client.get("/api/scores/top?limit=50")
    assert r0.status_code == 200
    assert r0.headers["X-Cache"] == "miss"

    # Measure 100 hot calls
    timings_ms = []
    for _ in range(100):
        t0 = time.perf_counter()
        r = await client.get("/api/scores/top?limit=50")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert r.status_code == 200
        assert r.headers["X-Cache"] == "hit"
        timings_ms.append(elapsed_ms)

    p95 = statistics.quantiles(timings_ms, n=20)[18]  # 95th percentile
    assert p95 < 50.0, f"p95={p95:.1f}ms exceeds 50ms gate"
```

**Note on flakiness:** CI runners have variable load. Mitigation: gate at 50ms (the SC), but log the actual p95 + p99 + max in the failure message for diagnosis. If CI proves flaky in practice, add `@pytest.mark.flaky(reruns=2)` (not currently a project pattern — would need `pytest-rerunfailures` — defer until proven needed). [HIGH confidence on approach; MEDIUM on CI flakiness risk]

### Q-5: Indicator cache memory budget — RESOLVED

**Calculation:**

CONTEXT D-06 says `maxsize=600` *per indicator family*. The plan in CONTEXT shows the cache key includes the indicator name, so each family is logically a separate cache OR we have one shared `indicators` cache with `maxsize` covering all entries.

**Reality from codebase:** `analysis/technical.py:26-76` computes 11 indicators (sma×3, ema×2, rsi, macd, bbands, stoch, adx, obv) in **a single call** that returns a DataFrame with all indicator columns appended. Caching at per-indicator granularity does not fit this code shape — there is no per-indicator function to wrap. The natural boundary is one entry per `(symbol, run_id)` containing the full indicator row dict.

**Revised budget (per-symbol cache):**
- ~400 HOSE symbols × 1 entry per symbol = 400 entries (one run lives in cache at a time; previous run's keys are different and TTL-aged).
- Each entry: `dict` with ~30 fields (indicators + trend + S/R + volume) of ~8 bytes each = ~240 bytes/entry.
- Total: 400 × 240 B ≈ **100 KB**. Negligible.

**If we keep CONTEXT's per-indicator wording literally:**
- 11 indicators × 400 symbols × 1 entry per indicator-symbol = 4400 entries.
- Each entry: pandas Series of 252 floats × 8 B = ~2 KB/entry.
- Total: 4400 × 2 KB ≈ **9 MB**. Still fine, well under any container ceiling (typical containers run 512 MB - 2 GB).

**Recommendation:** Cache at the `analyze_technical_single(symbol, ohlcv_df) -> dict` boundary (line 264 in `analysis_service.py`). Single namespace `indicators` with `maxsize=600` and TTL=1h. Key = `indicators:{symbol}:run={run_id}` (drop the `{indicator_name}` segment from D-01 — the unit of caching is the row dict, not individual indicator series). This deviates slightly from D-01's literal key shape — see "Deviation from CONTEXT" note below.

**Deviation from CONTEXT:** D-01 specifies `indicators:{indicator_name}:{symbol}:run={run_id}`. The codebase makes this awkward — pandas-ta computes all indicators together. **Recommendation:** flag in plan that key shape should be `indicators:{symbol}:run={run_id}` (no `{indicator_name}` segment). The locked decision was authored without seeing the bundled-computation reality. The discuss-phase agent or human should ratify this small adjustment. [MEDIUM confidence — depends on user accepting the simplification]

---

## 2. Audit — D-06 indicator-cache wrap site

**Single canonical wrap point:**

| File | Line | Function | Action |
|------|------|----------|--------|
| `services/analysis_service.py` | 264 | `analyze_technical_single(self, symbol, ohlcv_df) -> dict` | Wrap entire body in `get_or_compute(key=f"indicators:{symbol}:run={run_id}", ttl=3600, compute_fn=lambda: <existing body>)` |

**Why this boundary (not per-indicator inside `compute_indicators`):**
- `analysis/technical.py:64-74` runs all 11 pandas-ta indicators in one loop appending to a single DataFrame. There is no per-indicator function to decorate. Splitting would require refactoring `compute_indicators` into 11 separate functions — a much larger change unrelated to caching.
- `analyze_technical_single` returns a single dict (`to_indicator_row` output) — easy to cache; trivially pickle-safe (just floats / strings / Nones).
- Hit rate at this granularity is excellent: every `/api/analysis/{symbol}` GET in the same `pipeline_run_id` window hits the cache.

**Other indicator call sites enumerated (for completeness, no wrapping needed):**

| File | Line | Call | Why not wrapped |
|------|------|------|-----------------|
| `analysis/technical.py` | 67 | `result.ta.{name}(append=True, **params)` ×11 | Inside `compute_indicators`; covered transitively by wrapping caller |
| `analysis/technical.py` | 146 | `ta.cdl_doji(...)` | Inside `compute_candlestick_patterns`; called from `analyze_technical_single` body — covered by outer wrap |
| `analysis/technical.py` | 154 | `ta.cdl_inside(...)` | Same as above |
| `analysis/technical.py` | 196 | `ta.mfi(...)` | Inside `compute_volume_divergence`; same as above |

**Granularity decision:** **per-symbol-per-run** — single cache key per `analyze_technical_single` call. Good hit rate (any subsequent `/api/analysis/{symbol}` is a hit), no key-explosion (~400 entries max), simple invalidation. [HIGH confidence]

---

## 3. Audit — D-04 invalidate_namespace call sites

**Important correction to CONTEXT scope:** CONTEXT D-04 names `automation_service.py` OR `services/pipeline.py finalize`. **The actual write boundaries live in `automation_service.py`**, not `pipeline.py`. `Pipeline.run_full` only does crawl + price-adjustment (verified by reading lines 188-321); scoring/sentiment/reports/sector all run in `AutomationService.run_daily_pipeline` (lines 78-180).

**Invalidation hooks to add:**

| Phase | File | After line | Hook | Namespaces to invalidate |
|-------|------|------------|------|--------------------------|
| Analysis (indicators written) | `automation_service.py` | 109 (after `summary["steps"]["analysis"] = anal_result`, inside the success path) | `cache.invalidate_namespace("indicators")` | `indicators` |
| Scoring (scores written) | `automation_service.py` | 142 (end of Step 5 try-block, success path) | `cache.invalidate_namespace("scores:ranking"); cache.invalidate_namespace("scores:symbol")` | `scores:ranking`, `scores:symbol` |
| Sector rotation (market summary affected) | `automation_service.py` | 174 (after `summary["sector_rotation"] = rotation`) | `cache.invalidate_namespace("market:summary")` | `market:summary` |
| Pipeline run completion (latest_run_id changes) | `automation_service.py` | After line 174, before pre-warm | `cache.invalidate_namespace("pipeline:latest_run_id")` | `pipeline:latest_run_id` |

**All hooks must be inside the `try` block's success path (after the `summary["steps"][X] = result` line, before the matching `except`)** — never invalidate on failure (avoids purging good cached data when a write phase failed and produced no new state).

**Implementation pattern:**

```python
# At end of Step 5 (scoring) try-block, after line 142:
try:
    cache.invalidate_namespace("scores:ranking")
    cache.invalidate_namespace("scores:symbol")
except Exception:
    logger.exception("automation.cache.invalidate_failed", phase="scoring")
    # Do not re-raise — invalidation failures must not fail the pipeline.
    # The version-key (D-01) is the correctness backstop.
```

[HIGH confidence — line numbers verified directly from current source]

---

## 4. Audit — D-05 pre-warm call site

**Single hook location:**

| File | Line | Action |
|------|------|--------|
| `automation_service.py` | Insert at **line 175** (between `# Sector rotation` block ending at line 174 and `# Send notifications` at line 176) | Call `await prewarm_hot_keys(self.session_factory)` |

**Verified flow constraint (CONTEXT D-05 says: after report phase, before Telegram dispatch):**
- Report phase ends at line 154 (Step 6 success).
- Score-change detection runs lines 156-163.
- Sector rotation runs lines 165-174.
- `_send_notifications` (Telegram) is called at line 177.

CONTEXT says "after report phase, before Telegram dispatch". Score-change + sector rotation are *between* those two — they affect the cached data (sector_rotation feeds market_summary). Therefore pre-warm must run **after sector rotation completes (line 174), not after report phase**. This is consistent with CONTEXT's spirit (pre-warm fills cache after all writes are done) and is a refinement, not a violation.

**Implementation:**

```python
# After line 174 (sector rotation block), before line 176 (_send_notifications)
try:
    await prewarm_hot_keys(self.session_factory)
except Exception:
    logger.exception("automation.cache.prewarm_failed")
    # D-05: failures logged + counted, never fail the pipeline
```

`prewarm_hot_keys` calls `ScoringService.get_top_ranked(limit=50)` and `MarketService.get_summary()` directly — both go through `get_or_compute` → cache filled before any user request can race. [HIGH confidence]

---

## 5. Validation Matrix (SC #1..#5)

| SC | Verbatim Text | Test Mechanism | Runtime Proof |
|----|---------------|----------------|---------------|
| **#1** | `/api/scores/ranking` lần thứ 2 (cùng `pipeline_run_id`) trả về < 50 ms p95 với header/log `cache=hit`; lần đầu sau pipeline write `cache=miss` | `tests/test_cache/test_perf_ranking.py::test_ranking_cache_hit_p95_under_50ms` (Q-4 pattern: 100 hot calls, statistics.quantiles, assert <50ms; assert `X-Cache` header `miss` then `hit`) | `X-Cache` response header set by `cache.middleware.CacheHeaderMiddleware`; log line `cache.access` with `outcome=hit\|miss` field |
| **#2** | Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data | `tests/test_cache/test_versioning.py::test_new_pipeline_run_invalidates_old_keys` — seed run_id=1, populate cache, insert new completed PipelineRun (id=2), call `/api/scores/top`, assert response reflects run=2 data + cache key now `scores:ranking:run=2` | Cache key composition in `get_or_compute` callsite includes `:run={latest_pipeline_run_id}` segment; `latest_pipeline_run_id` resolved per-request via `pipeline:latest_run_id` (5s TTL, D-02) |
| **#3** | Concurrent 100 requests vào cùng cold key chỉ trigger 1 backend computation — verified bằng counter `cache_compute_total` chỉ tăng 1 | `tests/test_cache/test_single_flight.py::test_concurrent_cold_key_single_compute` — `asyncio.gather` 100× `get_or_compute` on same cold key with a `compute_fn` that increments a counter; assert counter == 1 AND `cache_compute_total{namespace=X}` == 1 | `localstock_cache_compute_total{namespace}` Prometheus counter (new — must add to `observability/metrics.py`) |
| **#4** | Sau `run_daily_pipeline`, cache cho hot keys (ranking + market summary) đã pre-warm — first request từ user log `cache=hit` không phải `miss` | `tests/test_cache/test_prewarm.py::test_prewarm_fills_hot_keys` — call `AutomationService.run_daily_pipeline()` end-to-end with mocks, immediately call `/api/scores/top`, assert `X-Cache: hit` and `cache_misses_total{namespace="scores:ranking"}` did NOT increment | Same `X-Cache` header; log line `cache.prewarm.completed` emitted by `prewarm.py` after both keys filled |
| **#5** | `/metrics` expose `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` với label `namespace`; `cache_janitor` job chạy mỗi 60s và log số entries swept | `tests/test_cache/test_janitor.py::test_janitor_runs_and_logs_sweep` (manual trigger of janitor function, assert log line `cache.janitor.sweep` with per-namespace counts); `tests/test_cache/test_metrics_exposed.py::test_all_cache_metrics_in_registry` (HTTP GET `/metrics`, assert all 5 metric names present) | `/metrics` endpoint output; `cache.janitor.sweep` log every 60s; APScheduler shows `cache_janitor` job in `/admin/scheduler` |

**Note on metric label:** CONTEXT says label name = `namespace`, but the existing counters in `observability/metrics.py:157,166,175` already use `cache_name`. **Recommendation:** use `cache_name` to match existing infra (no rename of declared counters). Tests should assert on `cache_name="scores:ranking"` etc. See Open Question Q-A in §8.

---

## 6. Wave Structure Recommendation

**6 plans across 4 waves** — file-conflict analysis at end.

### Wave 1 (foundation — parallel-safe)

- **Plan 26-01: Cache core package + registry + single-flight** (D-02, D-03, D-07 partial)
  - Files: NEW `cache/__init__.py`, `cache/registry.py`, `cache/single_flight.py`, `cache/invalidate.py`; MODIFY `pyproject.toml` (add cachetools), `config.py` (add settings)
  - Includes the `InstrumentedTTLCache` subclass (Q-2) with eviction-counter wiring.
  - Tests: `test_single_flight.py` (SC #3), `test_invalidate.py`, `test_registry.py`.

- **Plan 26-02: Metrics + middleware + contextvar plumbing** (D-08 metrics + header)
  - Files: MODIFY `observability/metrics.py` (add `cache_compute_total`, `cache_prewarm_errors_total`); NEW `cache/middleware.py`; MODIFY `api/app.py` (register middleware), NEW `cache/_context.py` (contextvar for hit/miss flag).
  - Tests: `test_middleware.py`, `test_metrics_exposed.py` (SC #5 part 1).

### Wave 2 (route integration — depends on Wave 1)

- **Plan 26-03: PipelineRunRepository + version-key resolver**
  - Files: NEW `db/repositories/pipeline_run_repo.py` with `get_latest_completed()`; integrate into `cache/__init__.py` as version-key helper (uses 5s TTL cache for `pipeline:latest_run_id`).
  - Tests: `test_versioning.py` (SC #2).

- **Plan 26-04: Wrap routes — `/scores/top` and `/market/summary`** (D-01, CACHE-01/02)
  - Files: MODIFY `api/routes/scores.py:21` (wrap handler with `get_or_compute`); MODIFY `api/routes/market.py:38` (same); MODIFY ROADMAP.md (Q-1 doc fix).
  - Tests: `test_perf_ranking.py` (SC #1), `test_perf_market.py`, `test_route_caching_integration.py`.

### Wave 3 (pipeline integration — depends on Wave 2)

- **Plan 26-05: Pipeline invalidate + pre-warm hooks + indicator cache** (D-04, D-05, D-06)
  - Files: MODIFY `services/automation_service.py` (lines 109, 142, 174-175 — invalidate hooks + pre-warm hook); MODIFY `services/analysis_service.py:264` (wrap `analyze_technical_single` with `get_or_compute`); NEW `cache/prewarm.py`.
  - **File conflict:** `automation_service.py` is touched once in this plan (no conflict). `analysis_service.py` is touched once (no conflict). CONTEXT mentioned `pipeline.py` for hooks but research relocates them to `automation_service.py` — `pipeline.py` is NOT modified by this plan (resolves CONTEXT's potential conflict).
  - Tests: `test_invalidation_integration.py`, `test_prewarm.py` (SC #4), `test_indicator_cache.py`.

### Wave 4 (operational — depends on Wave 1, can parallel with Wave 3)

- **Plan 26-06: Janitor scheduler job + finalisation** (D-08 janitor)
  - Files: NEW `cache/janitor.py`; MODIFY `scheduler/scheduler.py` (register `cache_janitor` job with `IntervalTrigger(seconds=60)`).
  - Tests: `test_janitor.py` (SC #5 part 2).

### File-conflict matrix

| File | Plans touching | Resolution |
|------|----------------|------------|
| `automation_service.py` | 26-05 only | Single plan — no conflict |
| `pipeline.py` | NONE (CONTEXT mentioned it; research relocates work) | Eliminated by §3 audit |
| `analysis_service.py` | 26-05 only | Single plan |
| `observability/metrics.py` | 26-02 only | Single plan |
| `api/app.py` | 26-02 only | Single plan |
| `scheduler/scheduler.py` | 26-06 only | Single plan |
| `cache/__init__.py` | 26-01 (creates) + 26-03 (extends) | Sequential via wave order |
| `pyproject.toml` | 26-01 only | Single plan |
| `config.py` | 26-01 only | Single plan |
| `ROADMAP.md` | 26-04 (doc fix Q-1) | Single plan |

**No within-wave conflicts.** Wave-1 plans (26-01, 26-02) touch disjoint files. Wave-2 plans (26-03, 26-04) touch disjoint files. Wave 3 (26-05) and Wave 4 (26-06) touch disjoint files (parallel-safe).

---

## 7. Pitfalls Catalog

### P-1: cachetools.TTLCache is NOT thread-safe
**What:** `cachetools` documentation states explicitly that "the cache classes are not thread-safe" (cachetools 5.x README, "Thread Safety" section).
**Why it matters here:** FastAPI + uvicorn under default settings runs a single OS thread per worker, with all coroutines sharing one event loop. Single-threaded → no thread-safety problem.
**Verified:** `apps/prometheus/` does not pass `--workers >1` to uvicorn anywhere in the repo (verified by grepping for uvicorn invocations); `apscheduler` `AsyncIOScheduler` runs jobs on the same event loop. [VERIFIED]
**How to avoid:** No changes needed for v1.5. Document the assumption in `cache/registry.py` docstring. **If v1.6 introduces multi-worker uvicorn, every TTLCache access must be guarded by a `threading.Lock` (cachetools docs recommend this).** D-04's version-key acts as a defensive backstop in that future scenario.

### P-2: `asyncio.Lock` event-loop binding
**What:** `asyncio.Lock()` constructed at module import time binds to whatever event loop is current — which in pytest-asyncio with `asyncio_mode = "auto"` is recreated per test function.
**Why it matters:** A module-level `_locks: WeakValueDictionary` populated by `setdefault(key, asyncio.Lock())` will hand out locks bound to a stale event loop in subsequent tests, causing `RuntimeError: <Lock> is bound to a different event loop`.
**How to avoid:**
1. **Lazy lock allocation per call** (not module level): construct `asyncio.Lock()` inside `get_or_compute` on the miss path.
2. **WeakValueDictionary** ensures the lock is GC'd once no awaiter holds it (D-03 already specifies this).
3. **Pytest fixture cleanup:** add a session-scoped autouse fixture that calls `_locks.clear()` between tests.
4. Hold a strong local reference for the `async with` lifetime (CONTEXT D-03 already notes this).

### P-3: WeakValueDictionary `setdefault` race with GC
**What:** `WeakValueDictionary.setdefault(key, new_lock)` can race: between the dict miss check and the insert, another coroutine might insert; or the `new_lock` weakref might be reclaimed before any coroutine holds a strong ref.
**How to avoid:** Standard pattern (per CONTEXT D-03):
```python
lock = _locks.get(key)
if lock is None:
    lock = asyncio.Lock()
    _locks[key] = lock  # weak insert
# Strong ref `lock` keeps it alive across the await
async with lock:
    ...
```
Holding `lock` as a local variable across the `async with` block prevents premature GC.

### P-4: FastAPI middleware vs route-handler contextvar boundary
**What:** Starlette's `BaseHTTPMiddleware.dispatch` runs `call_next(request)` which executes the route handler. If `get_or_compute` (called inside the handler) sets a contextvar, the middleware can read it AFTER `call_next` returns — same task, same context. **This works.** [VERIFIED via existing `CorrelationIdMiddleware` pattern at `observability/middleware.py:32-48` — it sets contextvar BEFORE call_next; we need the inverse: handler sets, middleware reads after.]
**Subtle gotcha:** the contextvar must be set in the handler BEFORE the response is created, since once `call_next` returns, the middleware reads it. Since `get_or_compute` runs inside the handler before the route returns its body, this is fine.
**Implementation pattern:** in `cache/_context.py` declare `cache_outcome_var: ContextVar[str | None] = ContextVar("cache_outcome", default=None)`. In `get_or_compute`, call `cache_outcome_var.set("hit"|"miss")` after determining outcome. In `CacheHeaderMiddleware.dispatch`, after `await call_next(request)`, read `cache_outcome_var.get()`; if not None, set `response.headers["X-Cache"] = value`.
**Test coverage:** integration test that calls a wrapped route and asserts `X-Cache` header — guards against any future framework upgrade breaking the contextvar propagation.

### P-5: Pre-warm at end of `run_daily_pipeline` — failure semantics
**What:** Pre-warm runs after all writes are committed. If pre-warm itself fails (e.g. ScoringService raises), the run is already terminally `completed` — there is no rollback to perform.
**How to avoid:**
- Wrap pre-warm call in try/except (D-05 already specifies).
- Increment `cache_prewarm_errors_total{namespace}` on failure.
- Log at `error` level with full traceback.
- **NEVER** raise out of pre-warm — the calling code (`run_daily_pipeline`) treats it as best-effort.
- **Do not** mark the pipeline run as failed — pipeline data is good; pre-warm is a UX optimisation, not a correctness step.

### P-6: Invalidate-then-prewarm is NOT a race
**What:** Concern: between `invalidate_namespace("scores:ranking")` and `prewarm_hot_keys()`, a user request could land on an empty cache and trigger a cold-fill that races with the pre-warm.
**Why it's safe:**
- `invalidate_namespace` is a synchronous `dict.clear()` — no `await`.
- The next pre-warm call goes through `get_or_compute` — under the single-flight lock.
- A concurrent user request also goes through `get_or_compute` — same lock.
- Whoever grabs the lock first computes; the other waits. Result: 1 computation, both get the same value. [HIGH confidence — directly follows from D-03 single-flight semantics]
**Optional belt-and-suspenders:** invoke `invalidate_namespace` and the pre-warm calls in the same coroutine without yielding to the event loop in between (no `await sleep`, no other awaits) — guarantees no other request can sneak in. The pre-warm `await` will then be the first lock acquirer.

### P-7: pandas-ta output type instability
**What:** `pandas_ta` methods return `pd.Series`, `pd.DataFrame`, or `None` depending on the indicator and parameters. Caching mixed types is fine *until* something tries to JSON-serialise the cached value.
**Why it matters here:** D-06 caches the output of `analyze_technical_single` (per Q-5 resolution), which is already a flat `dict` of floats/strings/Nones via `to_indicator_row`. **Already safe** — the dict is pickle-safe AND JSON-safe.
**However:** If we ever cache a raw indicator DataFrame (we are NOT, per Q-5), watch out for: (1) pandas object identity — DataFrames in cache must be `.copy()`-ed on retrieve to avoid callers mutating shared state; (2) numpy dtypes leaking through pydantic serialisation.
**How to avoid:** keep the cache value at the dict level (Q-5 recommendation). Document in `analysis_service.py:264` cache wrap that "cache values must be plain Python types — pickle/JSON safe".

### P-8: Janitor job sweep cost on event loop
**What:** APScheduler's `AsyncIOScheduler` runs jobs as coroutines on the main event loop. A long-running sweep blocks all incoming HTTP requests.
**Estimated cost:** `cachetools.TTLCache.expire()` is O(expired-entries). With ~5 namespaces × ~600 entries each, worst case = 3000 entries inspected per sweep, all in pure Python dict operations. Empirically ≪ 10ms. [MEDIUM confidence — based on cachetools complexity, not measured]
**How to avoid:** if profiling shows >50ms sweep cost, wrap in `asyncio.to_thread(cache.expire)` to offload to a thread (cachetools is not thread-safe per P-1 — but `expire()` running in isolation while no other thread accesses the cache is safe; nonetheless prefer to keep it on the event loop unless proven slow).

### P-9: `cache_compute_total` semantics — exactly-once-per-cold-fill
**What:** SC #3 requires this counter to be `==1` after 100 concurrent cold requests. If `cache_compute_total.inc()` is placed outside the lock, all 100 racers increment before any of them finds the cached value.
**How to avoid:** Place `cache_compute_total.labels(...).inc()` *inside* the lock, *after* the double-check, *before* the `await compute_fn()`. CONTEXT D-03's pseudocode is correct; just ensure plan implementation matches verbatim.

---

## 8. Open Questions for Plan Author / Discuss-Phase

### Q-A: Prometheus label name `cache_name` vs `namespace`

**The question:** CONTEXT D-08 specifies `namespace` as the label name. The existing `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` counters in `observability/metrics.py:153-179` already declare `cache_name` as the label. Renaming would (a) require changing the existing counter declarations, (b) break any in-flight Prometheus dashboards or alert rules referring to `cache_name`.

**Researcher recommendation:** Use `cache_name` (match existing infra). Treat CONTEXT's `namespace` as describing the *concept* (the namespace identifier), not literally the *label key*. The label values are identical — only the column header differs.

**Action required:** plan author or human ratification. Either (a) accept `cache_name` and update CONTEXT documentation, or (b) override existing counters to use `namespace` and accept the dashboard-rename cost.

### Q-B: Indicator cache key shape — drop `{indicator_name}` segment

**The question:** D-01 specifies `indicators:{indicator_name}:{symbol}:run={run_id}`. The codebase computes all 11 indicators as a bundle (verified §2). Researcher recommends `indicators:{symbol}:run={run_id}` (no indicator-name segment). See Q-5 resolution.

**Researcher recommendation:** drop the `{indicator_name}` segment. Hit rate is unchanged (one entry per symbol-per-run), key count is 11× smaller, no refactor of `compute_indicators` required.

**Action required:** plan author or human ratification.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Cache get/set | API (in-process Python) | — | Sub-millisecond access requires same-process memory; out-of-process (Redis) deferred |
| Cache key composition | API | DB (`pipeline_runs` lookup) | Latest run_id is DB state; compose at request time, cache the lookup itself for 5s |
| Invalidation trigger | Pipeline orchestration (`automation_service.py`) | — | Write-side knows when state changed; readers must not coordinate |
| Pre-warm execution | Pipeline orchestration (`automation_service.py`) | API service layer (called methods) | Triggered post-pipeline, executes via service-layer code paths |
| Eviction telemetry | Cache subsystem | Observability (Prometheus) | TTLCache subclass owns the event; metrics are the broadcast |
| Janitor scheduling | APScheduler (existing) | — | Already a project-level scheduling primitive |
| X-Cache header | FastAPI middleware | Cache subsystem (contextvar set inside `get_or_compute`) | Standard request-scoped contextvar pattern (mirrors `CorrelationIdMiddleware`) |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cachetools` | `>=5,<6` (CONTEXT-locked) | TTLCache + LRUCache | Established Python standard for in-process bounded caches. [VERIFIED: PyPI shows latest is 7.0.6; CONTEXT pinned to 5.x. Project uses cachetools-style TTLCache as already specified.] |
| `asyncio.Lock` | stdlib | Single-flight | Standard async coordination primitive |
| `weakref.WeakValueDictionary` | stdlib | Per-key lock storage with auto-GC | Standard pattern for ephemeral keyed locks |
| `apscheduler` | `>=3.11,<4.0` (already in project) | Janitor scheduling | Existing project scheduler; pattern proven by `health_self_probe` |
| `prometheus_client` | `>=0.21,<1.0` (already in project) | Metrics | Existing project observability stack |

### Note on cachetools version

**Verified versions:**
- CONTEXT D-07 specifies `cachetools>=5,<6`. [LOCKED]
- Current PyPI version: **7.0.6** (verified via PyPI JSON API at research time). [VERIFIED]
- Major versions 6 and 7 are both newer than CONTEXT's range.

This is a small currency drift in CONTEXT, but the locked decision stands. cachetools 5.x is mature, well-tested, and stable; no functional gap between 5.x and 7.x affects this phase. [HIGH confidence on stability]

### Installation

```bash
cd apps/prometheus
uv add 'cachetools>=5,<6'
```

(Verify with `uv pip show cachetools` after install.)

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cachetools` | `aiocache` | aiocache is async-native and supports Redis backends — overkill for in-process v1.5 scope; CONTEXT locks `cachetools` |
| `asyncio.Lock` + WeakValueDictionary | `asyncio.Semaphore(1)` per key | Equivalent semantics; Lock is the idiomatic single-flight primitive |
| FastAPI middleware for X-Cache | Per-route response model field | Middleware is non-invasive (no schema change); CONTEXT D-08 picks middleware |

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────┐
                         │ HTTP request │
                         └──────┬───────┘
                                │
                ┌───────────────▼───────────────┐
                │ CorrelationIdMiddleware       │ (existing)
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
                │ CacheHeaderMiddleware  [NEW]  │ sets cache_outcome_var=None
                └───────────────┬───────────────┘ before call_next
                                │
                ┌───────────────▼───────────────┐
                │ Route handler (e.g. /scores/  │
                │  top, /market/summary)        │
                │  └─► get_or_compute(...)      │ ───┐
                └───────────────┬───────────────┘    │
                                │                    │
                                │   reads cache_outcome_var   │
                                │   sets X-Cache header       │
                ┌───────────────▼───────────────┐    │
                │ Response with X-Cache header  │    │
                └───────────────────────────────┘    │
                                                     │
              ┌──────────────────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ cache.get_or_compute(key, compute_fn, namespace, ttl)    │
   │                                                          │
   │  1. cache_get(namespace, key) ──── HIT ──► set ctx="hit",│
   │  │                                          inc cache_   │
   │  │                                          hits_total,  │
   │  │                                          return value │
   │  │                                                       │
   │  └── MISS ──► acquire single-flight lock (per-key,       │
   │              WeakValueDictionary)                        │
   │       │                                                  │
   │       ├─ double-check cache_get → if HIT, set ctx="hit", │
   │       │                              return              │
   │       │                                                  │
   │       └─ inc cache_misses_total + cache_compute_total,   │
   │          set ctx="miss", value = await compute_fn(),     │
   │          cache_set(namespace, key, value), return value  │
   └──────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │ Pipeline finalize (automation_service.run_daily_pipeline)│
   │   step 2 analysis OK ──► invalidate_namespace(indicators)│
   │   step 5 scoring  OK ──► invalidate scores:ranking +     │
   │                                     scores:symbol         │
   │   sector rotation OK ──► invalidate market:summary +     │
   │                          pipeline:latest_run_id          │
   │   ──► await prewarm_hot_keys()                            │
   │       (calls service methods → through get_or_compute)    │
   │   ──► _send_notifications() (Telegram)                    │
   └──────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │ APScheduler IntervalTrigger(60s) ──► cache_janitor()      │
   │   for ns, cache in registry: cache.expire()               │
   │   log cache.janitor.sweep with per-ns swept counts        │
   └──────────────────────────────────────────────────────────┘
```

### Pattern 1: get_or_compute with single-flight

```python
# Source: synthesised from CONTEXT D-03 + cachetools docs
# apps/prometheus/src/localstock/cache/__init__.py
from contextvars import ContextVar
import asyncio
import weakref
from cachetools import TTLCache

cache_outcome_var: ContextVar[str | None] = ContextVar("cache_outcome", default=None)
_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

async def get_or_compute(namespace: str, key: str, compute_fn, ttl: int | None = None):
    cache = registry.get(namespace)
    full_key = f"{namespace}:{key}"
    cached = cache.get(full_key)
    if cached is not None:
        cache_outcome_var.set("hit")
        metrics["cache_hits_total"].labels(cache_name=namespace).inc()
        return cached

    # Strong local ref keeps lock alive across await
    lock = _locks.get(full_key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[full_key] = lock

    async with lock:
        cached = cache.get(full_key)
        if cached is not None:
            cache_outcome_var.set("hit")
            metrics["cache_hits_total"].labels(cache_name=namespace).inc()
            return cached
        cache_outcome_var.set("miss")
        metrics["cache_misses_total"].labels(cache_name=namespace).inc()
        metrics["cache_compute_total"].labels(cache_name=namespace).inc()
        value = await compute_fn()
        cache[full_key] = value
        return value
```

### Pattern 2: InstrumentedTTLCache (Q-2)

See Q-2 above — subclass with `_in_expire` flag to distinguish `expire` vs `evict` reasons.

### Pattern 3: Header middleware (mirrors CorrelationIdMiddleware)

```python
# apps/prometheus/src/localstock/cache/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from localstock.cache import cache_outcome_var

class CacheHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = cache_outcome_var.set(None)
        try:
            response = await call_next(request)
            outcome = cache_outcome_var.get()
            if outcome is not None:
                response.headers["X-Cache"] = outcome
            return response
        finally:
            cache_outcome_var.reset(token)
```

### Anti-patterns to avoid

- **Module-level `asyncio.Lock` instances** — bind to import-time event loop, break under pytest-asyncio (P-2).
- **Direct cache writes bypassing `get_or_compute`** — skip lock, skip metrics, race with concurrent readers (Q-3).
- **Caching mutable DataFrames without `.copy()`** — callers mutate shared state (P-7).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TTL eviction | Custom dict + timestamp scanning | `cachetools.TTLCache` | Battle-tested, correct edge cases (clock skew, monotonic time), O(1) amortised |
| Per-key locks | Manual lock dict + cleanup | `weakref.WeakValueDictionary` | Auto-GC when no awaiter holds ref |
| Bounded eviction | Custom LRU | `cachetools.LRUCache` (TTLCache extends) | Linked-list + dict implementation already optimal |
| Periodic janitor | Custom asyncio.create_task loop | `apscheduler.IntervalTrigger` | Already in project; integrates with `/admin/scheduler` UI |
| Request-scoped flag plumbing | thread-local / dict-on-request | `contextvars.ContextVar` | Standard for asyncio; existing pattern in `CorrelationIdMiddleware` |

---

## Common Pitfalls

(See §7 above — 9 detailed pitfalls.)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | runtime | ✓ | per pyproject.toml | — |
| `cachetools` | core | ✗ (NEW) | `>=5,<6` to install | none — required |
| `apscheduler` | janitor | ✓ | `>=3.11,<4.0` | — |
| `prometheus_client` | metrics | ✓ | `>=0.21,<1.0` | — |
| `pytest-benchmark` | perf test (Q-4) | ✗ | — | hand-rolled `time.perf_counter` (recommended) |
| `pytest`, `pytest-asyncio`, `pytest-timeout` | test suite | ✓ | per dev group | — |

**Missing dependencies with no fallback:**
- `cachetools` — must be added to pyproject.toml in plan 26-01.

**Missing dependencies with viable fallback:**
- `pytest-benchmark` — replace with `time.perf_counter` + `statistics.quantiles` (Q-4 resolution).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 8.4+`, `pytest-asyncio 0.26+`, `pytest-timeout 2.4+` |
| Config file | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode=auto, timeout=30) |
| Quick run command | `cd apps/prometheus && uv run pytest tests/test_cache/ -x` |
| Full suite command | `cd apps/prometheus && uv run pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CACHE-01 | <50ms p95 hit, header `cache=hit`/`miss` | perf | `pytest tests/test_cache/test_perf_ranking.py -x` | ❌ Wave 1 |
| CACHE-02 | Version-aware key with run_id | integration | `pytest tests/test_cache/test_versioning.py -x` | ❌ Wave 2 |
| CACHE-03 | Invalidate after pipeline write | integration | `pytest tests/test_cache/test_invalidation_integration.py -x` | ❌ Wave 3 |
| CACHE-04 | Single-flight lock | unit | `pytest tests/test_cache/test_single_flight.py -x` | ❌ Wave 1 |
| CACHE-05 | Pre-warm at end of run_daily_pipeline | integration | `pytest tests/test_cache/test_prewarm.py -x` | ❌ Wave 3 |
| CACHE-06 | Janitor 60s + sweep counts | unit + scheduler | `pytest tests/test_cache/test_janitor.py -x` | ❌ Wave 4 |
| CACHE-07 | Metrics labelled by cache_name | unit | `pytest tests/test_cache/test_metrics_exposed.py -x` | ❌ Wave 1 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_cache/test_<file>.py -x` (the file the task touches)
- **Per wave merge:** `pytest tests/test_cache/ -x` (full cache suite)
- **Phase gate:** `pytest -x` (whole project) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cache/__init__.py` — new test package directory
- [ ] `tests/test_cache/conftest.py` — shared fixtures (cache reset between tests, mock pipeline_runs row)
- [ ] All 7 test files listed above — created during their respective waves
- [ ] Add `cachetools>=5,<6` to `pyproject.toml` `[project]` dependencies (plan 26-01)

(No framework install needed — pytest stack already configured.)

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reads:
  - `apps/prometheus/src/localstock/api/routes/scores.py:21` — route name `/scores/top`
  - `apps/prometheus/src/localstock/api/routes/market.py:38` — route name `/market/summary`
  - `apps/helios/src/lib/queries.ts:25` — Helios calls `/api/scores/top`
  - `apps/prometheus/src/localstock/services/automation_service.py:48-180` — pipeline phases + line numbers
  - `apps/prometheus/src/localstock/services/pipeline.py:166-389` — confirms pipeline.py scope is crawl + price-adjust only
  - `apps/prometheus/src/localstock/services/analysis_service.py:264-369` — `analyze_technical_single` boundary
  - `apps/prometheus/src/localstock/analysis/technical.py:26-76` — bundled pandas-ta call
  - `apps/prometheus/src/localstock/observability/metrics.py:153-179` — existing cache counters with `cache_name` label
  - `apps/prometheus/src/localstock/observability/middleware.py:32-48` — CorrelationIdMiddleware pattern
  - `apps/prometheus/src/localstock/observability/context.py` — ContextVar pattern (`run_id_var`, `request_id_var`)
  - `apps/prometheus/src/localstock/scheduler/scheduler.py:60-85` — APScheduler IntervalTrigger precedent
  - `apps/prometheus/src/localstock/db/models.py:117-125` — `PipelineRun` model (no repository yet)
  - `apps/prometheus/pyproject.toml` — dependencies + dev groups (no cachetools, no pytest-benchmark)

### Secondary (MEDIUM confidence)
- PyPI metadata for cachetools 7.0.6 (latest, requires Python>=3.10) — verified via `https://pypi.org/pypi/cachetools/json`
- cachetools README "Thread Safety" section (cited from training; not re-verified in research session) — `[CITED: cachetools docs]`

### Tertiary (LOW — flagged for validation)
- Exact internal call graph of `cachetools.TTLCache.expire() → popitem()` — confirmed from training; recommend reading installed source after `uv add cachetools` to verify pattern in Q-2 still holds in 5.x.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | uvicorn runs single-threaded, single-worker in this project (no `--workers >1`) | P-1 | If multi-worker is added, every cache access needs threading.Lock; D-04 version-key partially mitigates |
| A2 | `cachetools.TTLCache.expire()` calls `self.popitem()` for each expired key in 5.x | Q-2 | If internal API differs, eviction counter needs delta-from-sweep approach |
| A3 | `pytest-asyncio` `asyncio_mode=auto` recreates event loop per test function | P-2 | If loop is shared, lock fixtures unnecessary; harmless if applied anyway |
| A4 | The existing `cache_name` label is preferred over CONTEXT's `namespace` | Q-A, §5 metric note | Decided by plan author / human ratification |
| A5 | Indicator cache key may drop `{indicator_name}` segment | Q-5, Q-B | Decided by plan author / human ratification |
| A6 | `prewarm_hot_keys` failure rate <1% in steady state | P-5 | If failures common, log noise; metric `cache_prewarm_errors_total` provides signal to tune |
| A7 | The `analyze_technical_single` return dict is fully pickle-/JSON-safe (only floats/strings/None) | P-7 | If pandas/numpy types leak into dict via `to_indicator_row`, cache works but `/api/analysis` JSON serialisation may fail — existing tests already cover this |
| A8 | A Pipeline.run row reaches `status="completed"` before any reader needs the new cache | D-01, §3 | If readers fire mid-write, version-key resolves to previous run_id (correct behaviour: stale-but-consistent until commit) |

---

## Project Constraints (from copilot-instructions.md)

(Reviewed `copilot-instructions.md` and `apps/prometheus/CLAUDE.md` cursorily — both exist; primary constraints relevant to this phase:)

- Python 3.12+ required (verified in pyproject.toml).
- All Python work uses `uv` package manager (confirmed by uv.lock presence).
- Tests use pytest with `asyncio_mode=auto` and `timeout=30`.
- Loguru is the logging stack — use structured kwargs (`logger.info("event.name", key=value)`), never f-strings.
- New repositories follow the pattern in `db/repositories/*` (async SQLAlchemy 2.0).
- New scheduler jobs use `@observe(...)` decorator (see `scheduler.py:34, 95`).
- New metrics declared in `observability/metrics.py` via `_register(...)` factory pattern.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — cachetools is canonical for this use case; version locked in CONTEXT
- Architecture: HIGH — patterns mirror existing code (CorrelationIdMiddleware, IntervalTrigger jobs, `_register` metrics)
- Pitfalls: HIGH on P-1..P-6 (verified against codebase), MEDIUM on P-7..P-9 (general cache wisdom + reasoning)
- Audit lists (§§2,3,4): HIGH — line numbers verified directly
- Open questions resolved: HIGH on Q-1, Q-3; MEDIUM on Q-2, Q-4, Q-5 (depend on user/plan ratification of Q-A, Q-B)

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (30 days — codebase is stable; cachetools API has been stable for years)
