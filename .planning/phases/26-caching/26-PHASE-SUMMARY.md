# Phase 26 — Caching: Closure Summary

**Status:** ✅ COMPLETE — 6/6 plans, 7/7 requirements, 5/5 ROADMAP Success Criteria.
**Milestone:** v1.6 Performance Caching.
**Closed:** 2026-04-29.

## Plans

| Plan | Wave | Requirements Closed | SC Closed | One-liner |
| --- | --- | --- | --- | --- |
| 26-01 | W1 | CACHE-04 | #3 | Cache core (`get_or_compute`), single-flight `asyncio.Lock` per key, `InstrumentedTTLCache` registry, canonical `cache_compute_total`, Wave-0 fixtures |
| 26-02 | W2 | CACHE-07 | (#5 surface) | Telemetry middleware (`X-Cache: hit/miss` header via ContextVar), `/metrics` exposes 5 canonical cache counters with `cache_name` label |
| 26-03 | W2 | CACHE-02 | #2 | `resolve_latest_run_id(session_factory)` version-key helper; cache keys include `pipeline_run_id` so writes never see stale data without TTL elapse |
| 26-04 | W3 | CACHE-01 | #1 | `/scores/top` + `/market/summary` wrapped in `get_or_compute`; `build_market_summary(session)` extracted for prewarm reuse; `CacheHeaderMiddleware` wiring fix-forward |
| 26-05 | W3 | CACHE-03, CACHE-05 | #4 | 4 eager-invalidate hooks in `automation_service.py` after each pipeline write phase; `prewarm_hot_keys` at end of pipeline; `cached_analyze_technical_single` indicator wrapper with mandatory `run_id` hoist |
| 26-06 | W4 | CACHE-06 | #5 | `cache_janitor` APScheduler `IntervalTrigger(60s)` sweep; `InstrumentedTTLCache.expire` Rule-1 fix (`reason='expire'` was never emitted because TTLCache uses `Cache.__delitem__`, not popitem) |

## ROADMAP Success Criteria — Verbatim Closure

| # | Criterion (Vietnamese verbatim) | Closed by | Verification |
| --- | --- | --- | --- |
| 1 | `/api/scores/top` lần 2 (cùng `pipeline_run_id`) trả về < 50 ms p95 với `cache=hit` | 26-04 | `test_ranking_cache_hit_p95_under_50ms`: **p95 = 2.36 ms** (21× under gate); `/market/summary` p95 = 2.01 ms (25× under gate) |
| 2 | Cache key cho scoring outputs include `pipeline_run_id` — ghi pipeline mới → key cũ không trả stale | 26-03 | `test_versioning.py` asserts new run_id ⇒ new key ⇒ cache miss without TTL wait |
| 3 | 100 concurrent cold requests → 1 backend computation (single-flight) — `cache_compute_total` chỉ tăng 1 | 26-01 | `test_single_flight.py` — 100 concurrent calls, compute counter increments once |
| 4 | Sau `run_daily_pipeline`, hot keys pre-warmed — first user request `cache=hit` không phải `miss` | 26-05 | `test_prewarm.py` — pipeline finalize calls `prewarm_hot_keys`; subsequent get_or_compute is a hit. Indicator cache hit reduction: **99.7%** (107.53 ms → 0.29 ms over 50 symbols) |
| 5 | `/metrics` expose `cache_hits/misses/evictions_total` với label `namespace`; `cache_janitor` chạy mỗi 60s + log số entries swept | 26-02 (metrics) + 26-06 (janitor) | `test_metrics_exposed.py` (5 counters present, label `cache_name` per D-08); `test_janitor.py` (60s IntervalTrigger + sweep count logging + reason='expire' counter increments) |

## Requirements — All Done

- [x] CACHE-01 — TTLCache for `/scores/top` + `/market/summary` + indicator computations (26-04, 26-05)
- [x] CACHE-02 — Cache keys include `pipeline_run_id` (26-03)
- [x] CACHE-03 — `cache.invalidate_namespace(...)` from `automation_service.py` after write phases (26-05)
- [x] CACHE-04 — Single-flight `asyncio.Lock` per key (26-01)
- [x] CACHE-05 — Pre-warm hot keys at end of `run_daily_pipeline` (26-05)
- [x] CACHE-06 — `cache_janitor` 60s sweep (26-06)
- [x] CACHE-07 — Cache hit/miss/eviction counters on `/metrics` (26-02)

## Key Performance Metrics

| Surface | Before (W3 baseline) | After (cached) | Improvement |
| --- | --- | --- | --- |
| `/api/scores/top` p95 | uncached / DB-bound | **2.36 ms** | 21× under 50 ms SC #1 gate |
| `/api/market/summary` p95 | uncached / DB-bound | **2.01 ms** | 25× under 50 ms gate |
| `/api/market/summary` p50 | — | 1.47 ms | — |
| Indicator compute fanout (50 symbols) | 107.53 ms cold | 0.29 ms warm | **99.7% reduction** (SC #4 gate ">50% drop" easily cleared) |
| `cache_janitor` sweep cost | — | sub-millisecond | <50 ms P-8 budget by 50× headroom |

## Architectural Decisions Locked In

- **D-02:** Per-namespace TTLs (`scores:ranking` 24h, `scores:symbol` 24h, `market:summary` 1h, `indicators` 12h, `pipeline:latest_run_id` 30s); janitor interval 60s.
- **D-03:** Single-flight via `asyncio.Lock` allocated per `f"{namespace}:{key}"` inside the coroutine (P-2 — current loop).
- **D-04:** Eager invalidate (not TTL-only) on every write phase boundary in `automation_service.py`. Each invalidate wrapped in its own `try/except` so cache failures never abort the pipeline.
- **D-05:** Pre-warm runs at end of `run_daily_pipeline`, before notifications, routed through `get_or_compute` (Q-3 — same single-flight choke-point as routes; no double-compute).
- **D-06:** Indicator cache wrapper keyed by `indicators:{symbol}:run={run_id}` — bundled call (no per-indicator-name segment per Q-B).
- **D-07:** Namespace registry is a process-singleton dict; thread-safety relies on FastAPI/uvicorn/asyncio single-thread audit (P-1 caveat documented).
- **D-08:** Metric label is `cache_name` (renamed from initial `namespace` design — bounded cardinality enforced; only `cache_evictions_total` carries an additional `reason ∈ {expire, evict}` label per Q-2).
- **W2 caller contract (26-05):** `cached_analyze_technical_single(symbol, ohlcv_df, run_id)` requires `run_id`; pipeline callers MUST hoist `resolve_latest_run_id(...)` ONCE before per-symbol loops, with fallback to `None` on resolution failure (cache bypass parity with route-level `T-26-04-04`).
- **Rule-1 fix (26-06):** `InstrumentedTTLCache.expire` overridden — emits `reason='expire'` from the returned expired-pairs list (TTLCache uses `Cache.__delitem__` internally, not popitem).

## Files Touched (across all 6 plans)

**New modules** (apps/prometheus/src/localstock/):
- `cache/__init__.py`, `cache/_context.py`, `cache/registry.py`, `cache/single_flight.py`, `cache/invalidate.py`, `cache/version.py`, `cache/prewarm.py`, `cache/janitor.py`, `cache/middleware.py`

**Modified:**
- `routes/scores.py`, `routes/market.py`, `services/automation_service.py`, `services/analysis_service.py`, `scheduler/scheduler.py`, `api/app.py`, `observability/metrics.py`, `config.py`

**Test surface** (apps/prometheus/tests/test_cache/): 12 test files, 37 tests, all passing.

## Test Suite Health at Closure

- Cache suite: **37 / 37** passing.
- Full project: **606 passing** (1 pre-existing Phase-24 migration `downgrade_removes_columns` test deselected — out of scope per Phase 26 directive, tracked separately).
- `uvx ruff check` clean across all Phase 26 deliverables.

## Threat Model Coverage

All identified threats from per-plan threat models have explicit code-level mitigations or audit-documented assumptions:

- T-26-01-* (lock leak, cache poison): address-keyed `_locks` dict, `_in_expire` flag, registry validation.
- T-26-04-04 (empty-shape poison via missing `run_id`): both routes bypass cache when `run_id is None`; same guard in pipeline callers.
- T-26-06-01..03 (event-loop block, partial-sweep failure, unbounded growth): per-namespace try/except, `max_instances=1 + coalesce=True`, sub-millisecond sweep.

## Follow-Ups (Not Blocking)

- TODO(27+): If `run_in_executor` writers ever start mutating cache state (currently audited against), wrap each `InstrumentedTTLCache` with `asyncio.Lock` (P-1).
- TODO(future): Migrate `routes/scores.py` + `routes/market.py` from local `resolve_latest_run_id` shim to canonical `localstock.cache.resolve_latest_run_id` once the engine event-loop pollution under pytest-asyncio is reconciled (26-04 W3 note).

---

**Phase 26 closes v1.6 Performance Caching milestone scope. Next:** Phase 27 (Pipeline Performance) — depends on Phase 26 invalidation hooks (research §"F depends on E").
