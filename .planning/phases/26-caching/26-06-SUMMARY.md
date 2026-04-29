---
phase: 26-caching
plan: 06
subsystem: cache
tags: [cache, scheduler, janitor, observability, sc-5]
requires: [26-01, 26-02]
provides:
  - cache.janitor.cache_janitor (async sweep, 60s)
  - InstrumentedTTLCache.expire (Rule-1 fix — emits reason='expire')
affects:
  - apps/prometheus/src/localstock/cache/janitor.py (new)
  - apps/prometheus/src/localstock/cache/__init__.py
  - apps/prometheus/src/localstock/cache/registry.py (Rule 1 fix)
  - apps/prometheus/src/localstock/scheduler/scheduler.py
tech-stack:
  added: [APScheduler IntervalTrigger, @observe('cache.janitor.sweep')]
  patterns: [TTL sweep, eviction-counter delta accounting, per-namespace try/except]
key-files:
  created:
    - apps/prometheus/src/localstock/cache/janitor.py
    - apps/prometheus/tests/test_cache/test_janitor.py
  modified:
    - apps/prometheus/src/localstock/cache/__init__.py
    - apps/prometheus/src/localstock/cache/registry.py
    - apps/prometheus/src/localstock/scheduler/scheduler.py
decisions:
  - "Sweep count derived from cache_evictions_total{reason='expire'} delta — len(TTLCache) itself triggers expire(), so a before/after len() approach reads zero for `before`."
  - "Rule 1 fix in 26-01: TTLCache.expire() uses Cache.__delitem__ internally, NOT popitem. Override expire() to walk the returned (key, value) list and increment cache_evictions_total{reason='expire'} per entry. popitem() retains reason='evict' for LRU overflow, guarded by _in_expire to prevent double-counting."
metrics:
  duration_minutes: 12
  tasks_completed: 1
  tests_added: 4
  files_changed: 5
  completed: "2026-04-29"
---

# Phase 26 Plan 06: cache_janitor APScheduler 60s sweep + SC #5 closure Summary

cache_janitor APScheduler IntervalTrigger(60s) job sweeps every registered InstrumentedTTLCache and logs per-namespace swept counts; latent Rule-1 bug in 26-01 (reason='expire' was never actually emitted because TTLCache.expire bypasses popitem) fixed by overriding expire() at the registry layer. **Closes verbatim ROADMAP Success Criterion #5 — Phase 26 implementation complete.**

## What Shipped

**`localstock.cache.janitor.cache_janitor`** — `async def cache_janitor() -> dict[str, int]` decorated with `@observe('cache.janitor.sweep')`:

- Iterates `_caches` registry (5 namespaces); for each, captures the `cache_evictions_total{cache_name, reason='expire'}` counter value, calls `cache.expire()`, captures the post-value, and stores `swept[ns] = max(0, after - before)`.
- Per-namespace `try/except` so a sweep failure on one namespace does not abort the rest (T-26-06-02).
- Logs `cache.janitor.sweep` at INFO with `swept={ns: count}` + `total=N` (verbatim SC #5 requirement: "log số entries swept").
- P-8: sweep is sub-millisecond in practice; if profiling ever shows >50 ms cost, body wraps in `asyncio.to_thread` (documented).

**Scheduler registration** in `setup_scheduler()` (after DQ-08 quarantine cleanup block):

```python
scheduler.add_job(
    cache_janitor,
    trigger=IntervalTrigger(seconds=settings.cache_janitor_interval_seconds),  # 60
    id="cache_janitor",
    name="Cache TTL sweep (cachetools.expire)",
    replace_existing=True,
    max_instances=1,    # T-26-06-03 — no stacked sweeps
    coalesce=True,
)
```

**`InstrumentedTTLCache.expire` Rule-1 fix** (`registry.py`):

cachetools' `TTLCache.expire()` uses `Cache.__delitem__` internally — it never routes through `popitem`. The 26-01 implementation relied on the popitem hook for both `reason='expire'` and `reason='evict'`, so the `expire` reason was never actually incremented. Fixed by overriding `expire()` to capture its returned `expired = [(k, v), ...]` list and increment the counter once per entry. `popitem()` retains the `reason='evict'` path for LRU overflow during `__setitem__`, guarded by the `_in_expire` flag to prevent double-counting if a future cachetools version routes expirations through popitem.

## Tasks Completed

| Task | Name | Commits | Files |
| --- | --- | --- | --- |
| 1 | RED → GREEN cache_janitor + scheduler registration + 26-01 Rule-1 fix | `45e0ce6` (RED), `81d929e` (GREEN) | janitor.py, registry.py, __init__.py, scheduler.py, test_janitor.py |

## Tests

`tests/test_cache/test_janitor.py` — 4 tests, all GREEN:

1. `test_janitor_sweeps_expired_entries` — insert into `scores:ranking` with TTL=0.1s, sleep 0.15s, call janitor, assert swept count ≥ 1 and cache empty.
2. `test_janitor_returns_dict_for_all_namespaces` — janitor return dict contains all 5 registered namespaces.
3. `test_janitor_emits_expire_eviction_counter` — Q-2 — `cache_evictions_total{cache_name='market:summary', reason='expire'}` increments by ≥1 after TTL expiry + janitor sweep.
4. `test_janitor_registered_in_scheduler` — `setup_scheduler()` returns a scheduler with `cache_janitor` job, 60s IntervalTrigger, max_instances=1, coalesce=True.

Full project: **606 passed** (37 cache + 569 other), 1 pre-existing Phase-24 migration test deselected per plan directive.

`uvx ruff check` clean on all 5 changed files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] reason='expire' eviction counter never emitted (latent bug from 26-01)**

- **Found during:** Task 1, attempting to make `test_janitor_emits_expire_eviction_counter` pass.
- **Issue:** `cachetools.TTLCache.expire()` uses `Cache.__delitem__` directly to remove expired entries — it never calls `popitem`. The 26-01 `InstrumentedTTLCache.popitem` override (with `_in_expire` flag for reason discrimination) therefore never fires during expiration. `cache_evictions_total{reason='expire'}` was permanently zero.
- **Fix:** Override `expire()` in `InstrumentedTTLCache` to capture `expired = super().expire(time)` and increment `cache_evictions_total{cache_name, reason='expire'}` once per returned `(key, value)` pair. `popitem()` retains the `reason='evict'` path for LRU overflow, now wrapped in `if not self._in_expire:` to defensively prevent double-counting if a future cachetools version routes expirations through popitem.
- **Files modified:** `apps/prometheus/src/localstock/cache/registry.py` (InstrumentedTTLCache.expire + popitem).
- **Commit:** `81d929e`.

**2. [Rule 1 - Bug] Sweep count derivation via len() reads zero**

- **Found during:** Task 1, first GREEN attempt.
- **Issue:** Initial `swept = before - after` used `before = len(cache)` / `after = len(cache)`. But `cachetools.TTLCache.__len__` itself calls `expire()` first then returns the post-expiry size — so `before` is always 0 once the TTL has elapsed.
- **Fix:** Derive swept count from the `cache_evictions_total{reason='expire'}` counter delta around the explicit `cache.expire()` call. This now also serves as a verification path that the Rule-1 fix above is actually wired correctly.
- **Files modified:** `apps/prometheus/src/localstock/cache/janitor.py`.
- **Commit:** `81d929e`.

## Auth Gates

None.

## SC #5 Closure

ROADMAP Success Criterion #5 (verbatim): "/metrics expose `cache_hits_total`, `cache_misses_total`, `cache_evictions_total` với label `namespace`; `cache_janitor` job chạy mỗi 60s và log số entries swept."

- **Metrics surface:** verified via `tests/test_cache/test_metrics_exposed.py` (3 tests, from 26-02). All 5 canonical counters (`cache_hits_total`, `cache_misses_total`, `cache_evictions_total`, `cache_compute_total`, `cache_prewarm_errors_total`) present on `/metrics`. Label is `cache_name` (D-08 ratified rename — concept matches the ROADMAP `namespace` text). Eviction counter carries the additional `reason ∈ {expire, evict}` label per Q-2.
- **Janitor job runs every 60s:** verified by `test_janitor_registered_in_scheduler` (asserts `IntervalTrigger.interval.total_seconds() == 60`).
- **Logs swept counts:** verified by inspection of `cache.janitor.sweep` log line during test runs (captures `swept={ns: count}` + `total`).

Phase 26 implementation complete: **6/6 plans, 7/7 requirements, 5/5 SCs ✅.**

## ROADMAP Doc Verification

Per task brief, scanned `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` for any residual `/scores/ranking` references (26-04 converted them to `/scores/top`). **No regression — both files clean.**

Updated:
- `.planning/ROADMAP.md`: Phase 26 milestone checkbox → `[x]`; progress row → `6/6 Complete ✅`; Plans line lists all 6 plans with their requirement closures.
- `.planning/REQUIREMENTS.md`: CACHE-06 + CACHE-07 checkboxes → `[x]`; traceability table `Plan` column filled for CACHE-03 (26-05), CACHE-05 (26-05), CACHE-06 (26-06), CACHE-07 (26-02) — those rows had been left at "TBD/Pending" by predecessors.

## TDD Gate Compliance

- RED gate: `45e0ce6` — `test(26-06): RED tests for cache_janitor APScheduler sweep`
- GREEN gate: `81d929e` — `feat(26-06): cache_janitor APScheduler 60s sweep`
- REFACTOR gate: not required (single coherent implementation; no dead code).

## Self-Check: PASSED

- `apps/prometheus/src/localstock/cache/janitor.py` — FOUND
- `apps/prometheus/tests/test_cache/test_janitor.py` — FOUND
- Commit `45e0ce6` (RED) — FOUND
- Commit `81d929e` (GREEN) — FOUND
- `cache_janitor` job registered in scheduler — verified by passing test
- `cache_evictions_total{reason='expire'}` increments via janitor — verified by passing test
- ROADMAP.md + REQUIREMENTS.md updated for CACHE-06 closure — verified by `git status`
