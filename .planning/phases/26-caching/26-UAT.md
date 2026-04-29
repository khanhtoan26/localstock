---
status: complete
phase: 26-caching
source:
  - 26-01-SUMMARY.md
  - 26-02-SUMMARY.md
  - 26-03-SUMMARY.md
  - 26-04-SUMMARY.md
  - 26-05-SUMMARY.md
  - 26-06-SUMMARY.md
  - 26-PHASE-SUMMARY.md
started: 2026-04-29T10:13:00Z
updated: 2026-04-29T10:16:00Z
mode: auto-verified-live
---

## Verdict

**8/8 tests PASS · 5/5 ROADMAP Success Criteria ✅**

All UAT checks executed live against the running backend (`localhost:8000`) plus the
project test suite. No manual test friction — every observable was verifiable by curl,
SQL, or unit-test gate.

## Tests

### 1. Cache hit/miss path on `/api/scores/top` — SC #1

**Expected:** 1st call returns `X-Cache: miss`; 2nd+ call returns `X-Cache: hit` for
the same `pipeline_run_id`.

**Observed (live):**
```
1st: HTTP/1.1 200 OK · x-cache: miss
2nd: HTTP/1.1 200 OK · x-cache: hit
3rd: HTTP/1.1 200 OK · x-cache: hit
```

**Result:** ✅ PASS. Required pre-condition: a row exists in `pipeline_runs` with
`status='completed'`. Per T-26-04-04 mitigation, route safely bypasses cache (returns
miss) when `latest_run_id` is `None` — verified by inserting test run id=188.

### 2. Cache hit/miss path on `/api/market/summary` — SC #1

**Expected:** Same miss → hit pattern.

**Observed:**
```
1st: x-cache: miss
2nd: x-cache: hit
```

**Result:** ✅ PASS.

### 3. p95 latency on cached `/api/scores/top` — SC #1 perf gate (<50ms)

**Expected:** p95 of 50 sequential calls (warm cache) under the 50 ms gate.

**Observed (50 live calls via stdlib `time.perf_counter`):**
```
p50 = 1.76 ms · p95 = 2.26 ms · min = 1.35 ms · max = 23.62 ms
```

**Result:** ✅ PASS — **22× under gate**, matches the in-suite gate
`test_ranking_cache_hit_p95_under_50ms` (p95 = 2.36 ms there).

### 4. Versioning closure (new run_id ⇒ old key dead) — SC #2

**Expected:** Cache key includes `pipeline_run_id`. Inserting a newer completed run
makes prior keys unreachable without TTL elapse.

**Observed:** Verified by `tests/test_cache/test_versioning.py::test_new_pipeline_run_invalidates_old_keys` (GREEN). Live re-check: pre-existing run_id ≤ 14 (failed) → inserted id=188 (completed) → first `/scores/top` was `miss` (key changed to `scores:ranking:run=188`).

**Result:** ✅ PASS.

### 5. Single-flight (100 concurrent cold callers ⇒ 1 backend compute) — SC #3

**Expected:** Single backend compute under contention (`cache_compute_total{cache_name=...}` increments by exactly 1 across 100 concurrent callers).

**Observed:** `tests/test_cache/test_single_flight.py` GREEN. 37/37 cache tests pass.

**Result:** ✅ PASS.

### 6. Pre-warm + indicator caching after `run_daily_pipeline` — SC #4

**Expected:** After pipeline finalize, hot keys are pre-populated; first user request
is `hit`. Indicator computations re-served from cache on 2nd run with **>50% drop**
in compute time.

**Observed:** `tests/test_cache/test_prewarm.py` + `test_indicator_cache.py` GREEN. Indicator fanout (50 symbols) timing in 26-05-SUMMARY:
```
1st pass (cold): 107.53 ms
2nd pass (warm):   0.29 ms   → 99.7 % reduction
```

**Result:** ✅ PASS — 50× margin over the >50% gate.

### 7. `/metrics` exposes 5 cache counters — SC #5 (observability)

**Expected:** `cache_hits_total`, `cache_misses_total`, `cache_compute_total`, `cache_evictions_total{reason}`, `cache_prewarm_errors_total` all carry `cache_name` label (D-08).

**Observed (live `/metrics`):**
```
localstock_cache_hits_total        ← present (incremented)
localstock_cache_misses_total      ← present (incremented)
localstock_cache_compute_total     ← present (incremented)
localstock_cache_evictions_total{cache_name=*, reason="expire"}  ← all 5 namespaces
localstock_cache_prewarm_errors_total  ← declared (only emits after a prewarm fault — by design)
```

All canonical metric names use the `cache_name` label (not `namespace`) per D-08
ratification.

**Result:** ✅ PASS.

### 8. `cache_janitor` scheduled at 60s — SC #5 (sweep)

**Expected:** APScheduler has a job named `cache_janitor` with `IntervalTrigger(60s)`.

**Observed (`setup_scheduler().get_jobs()`):**
```
daily_pipeline           cron[mon-fri 15:45]
admin_job_worker         interval[5s]
health_self_probe        interval[30s]
dq_quarantine_cleanup    cron[03:15]
cache_janitor            interval[60s]   ← present ✓
```

**Result:** ✅ PASS.

## ROADMAP Success Criteria Closure

| # | Criterion | Closed by | UAT Test | Verdict |
| --- | --- | --- | --- | --- |
| 1 | `/api/scores/top` p95 hit < 50 ms | 26-04 | T1+T2+T3 | ✅ p95 = 2.26 ms (22× under) |
| 2 | Cache key includes `pipeline_run_id`; new run kills stale | 26-03 | T4 | ✅ |
| 3 | 100 concurrent cold ⇒ 1 backend compute (single-flight) | 26-01 | T5 | ✅ |
| 4 | Pre-warm + indicator hits after `run_daily_pipeline` | 26-05 | T6 | ✅ 99.7% drop |
| 5 | `/metrics` exposes 5 cache counters; `cache_janitor` 60s sweep | 26-02 + 26-06 | T7+T8 | ✅ |

## Test Suite Health at UAT Time

- **Cache suite:** 37 / 37 passing.
- **Full project:** 606 passing (1 pre-existing Phase-24 migration test deselected — out of scope).
- **`uvx ruff check`:** clean across Phase 26 deliverables.

## Notes

- One small operational observation surfaced during UAT: with no `status='completed'`
  pipeline runs in the DB, both routes safely bypass the cache (return `x-cache: miss`
  on every call). This is the documented T-26-04-04 mitigation — defensive, not a bug.
  Behavior switches to the spec the moment any completed pipeline_run row exists.
- All RESEARCH pitfalls P-1..P-9 mitigated; documented in 26-PHASE-SUMMARY.md.
- No gaps. No follow-up `--gaps-only` execute pass needed.
