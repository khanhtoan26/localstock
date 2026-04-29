---
phase: 26-caching
plan: 05
subsystem: cache / pipeline integration
tags: [cache, automation, prewarm, invalidation, indicators, SC-4]
status: Complete
completed: 2026-04-29
requirements: [CACHE-03, CACHE-05]
depends_on: [26-01, 26-02, 26-03, 26-04]

dependency_graph:
  requires:
    - "cache.get_or_compute / invalidate_namespace (26-01)"
    - "cache_prewarm_errors_total Counter (26-02)"
    - "cache.resolve_latest_run_id(session_factory) (26-03)"
    - "build_market_summary(session) helper in routes/market.py (26-04)"
    - "/scores/top + /market/summary route caching (26-04)"
  provides:
    - "automation_service.py — 4 invalidate hooks (D-04)"
    - "automation_service.py — prewarm hook between sector-rotation and notifications (D-05)"
    - "cache.prewarm_hot_keys(session_factory, ranking_limit=50)"
    - "AnalysisService.cached_analyze_technical_single(symbol, ohlcv_df, run_id) — D-06 indicator cache"
  affects:
    - "All consumers of /scores/top and /market/summary — first user request post-pipeline now logs X-Cache: hit"
    - "AnalysisService run_full / run_single — second pass within same run_id is ~99% faster on indicator math"

tech-stack:
  added: []
  patterns:
    - "eager invalidation at the success path of each pipeline write phase"
    - "version-keyed pre-warm (run_id) routed through get_or_compute to inherit single-flight"
    - "loop-invariant resolution hoist (W2) — run_id resolved ONCE, passed down 400× into per-symbol wrapper"

key-files:
  created:
    - apps/prometheus/src/localstock/cache/prewarm.py
    - apps/prometheus/tests/test_cache/test_invalidation_integration.py
    - apps/prometheus/tests/test_cache/test_prewarm.py
    - apps/prometheus/tests/test_cache/test_indicator_cache.py
  modified:
    - apps/prometheus/src/localstock/cache/__init__.py
    - apps/prometheus/src/localstock/services/automation_service.py
    - apps/prometheus/src/localstock/services/analysis_service.py
    - apps/prometheus/tests/test_services/test_pipeline_isolation.py

decisions:
  - "Combined Tasks 1+2 into a single feat commit since both touch automation_service.py at adjacent lines (hooks + prewarm). Task 3 is a separate feat commit. RED tests are in their own dedicated commit (TDD gate)."
  - "Indicator cache speedup test uses a 50-symbol fanout (not 400) to keep wall-clock under 200ms while still demonstrating the >50% drop required by SC #4. Production HOSE has ~400 symbols; the cache hit cost is O(1) per symbol so the speedup ratio scales linearly."
  - "run_full and run_single both hoist run_id via cache.resolve_latest_run_id(get_session_factory()). On any resolution failure (e.g. fresh DB with no completed runs in test environment) the hoist degrades to run_id=None and the wrapper bypasses the cache — parity with the route-level bypass shipped in 26-04."

metrics:
  duration_minutes: 25
  tasks_completed: 3
  files_changed: 7
---

# Phase 26 Plan 05: Pipeline Invalidate + Prewarm + Indicator Cache Summary

**One-liner:** Wires 4 eager-invalidate hooks + a `prewarm_hot_keys` call into `run_daily_pipeline`, and adds an async indicator-cache wrapper at `analyze_technical_single` keyed by `(symbol, run_id)` — closing ROADMAP SC #4 verbatim and operationalising SC #2 invalidation.

## What Was Built

### 1. Invalidate hooks (CACHE-03 / D-04) — `automation_service.py`

Four eager-invalidate blocks, each living inside the success path of its phase's `try` block, each wrapped in its own `try/except` so an invalidation failure is logged + counted but never aborts the pipeline:

| Phase | Namespace(s) purged |
|---|---|
| analysis success | `indicators` |
| scoring success | `scores:ranking`, `scores:symbol` |
| sector-rotation done | `market:summary`, `pipeline:latest_run_id` |

Purging `pipeline:latest_run_id` is what makes the version-key bump *operational* — without it, a freshly-completed run would only become visible to readers after the 5s TTL expired (T-26-03-01).

### 2. Pre-warm hook (CACHE-05 / D-05) — `cache/prewarm.py` + `automation_service.py`

New module `cache/prewarm.py` exposes:

```python
async def prewarm_hot_keys(session_factory, *, ranking_limit: int = 50) -> None
```

- Resolves `run_id` via `cache.resolve_latest_run_id` (5s TTL).
- Pre-warms `scores:ranking` via `ScoringService(session).get_top_stocks(50)`.
- Pre-warms `market:summary` via `build_market_summary(session)` (the helper extracted by 26-04 in `routes/market.py` — no SQL duplication).
- Both calls are routed through `get_or_compute`, so a concurrent first-user request hitting the same key collapses into the same single-flight compute (Q-3 / P-6 — no double-compute).
- Failures bump `cache_prewarm_errors_total{cache_name=...}` and log `automation.cache.prewarm_failed`; **never** re-raise (P-5).
- `run_id is None` short-circuits with a `cache.prewarm.skipped` warning.

The hook is invoked from `run_daily_pipeline` between the sector-rotation block and `_send_notifications`, again wrapped in its own `try/except` belt-and-suspenders.

### 3. Indicator cache (CACHE-03 / D-06) — `analysis_service.py`

New async wrapper:

```python
async def cached_analyze_technical_single(
    self, symbol: str, ohlcv_df: pd.DataFrame, run_id: int | None,
) -> dict
```

- Cache key: `indicators:{symbol}:run={run_id}` — D-06 ratified, **no** `{indicator_name}` segment (Q-B: pandas-ta computes all 11 indicators in one bundled call).
- Namespace: `indicators` (TTL 1h via registry, D-02).
- `run_id is None` → bypass (parity with 26-04 route bypass for `T-26-04-04`).

**W2 caller contract (mandatory):** `run_id` is a **required** positional/keyword argument with **no default** (enforced by `test_indicator_wrapper_requires_run_id_param` via `inspect.signature`). The caller MUST hoist `run_id = await resolve_latest_run_id(get_session_factory())` ONCE before any per-symbol loop. Resolving inside the loop would pay a 400× lock-acquire / contextvar-set cost across HOSE.

Caller updates:
- `run_full()` — hoists `run_id` before the per-symbol loop (with a fallback to `None` on resolution failure).
- `run_single()` — same hoist for consistency (single-symbol path also benefits).
- `_run_technical(symbol, run_id=None)` — accepts and forwards `run_id`.

## Tests

| File | Tests | Status |
|---|---|---|
| `test_invalidation_integration.py` | 6 | ✓ all pass |
| `test_prewarm.py` | 3 (1 `requires_pg`) | ✓ all pass |
| `test_indicator_cache.py` | 5 | ✓ all pass |

**RED → GREEN cycle:**
1. Commit `e11e0f1` — `test(26-05)`: 14 new tests, 10 failing red, 4 passing (invalidate-namespace smoke).
2. Commit `6cafc4c` — `feat(26-05)`: pipeline hooks + prewarm. RED tests for Tasks 1+2 turn green.
3. Commit `d3deb19` — `feat(26-05)`: indicator cache wrapper + caller hoist. RED tests for Task 3 turn green.

**Indicator cache timing (SC #4 closure):**

| Pass | 50 symbols × 2ms compute | Ratio |
|---|---|---|
| 1st (all miss) | 107.53ms | 100% baseline |
| 2nd (all hit, same run_id) | 0.29ms | **0.3%** (>99.7% reduction) |

Comfortably exceeds the SC #4 ">50% drop" threshold. Production HOSE has ~400 symbols and indicator math is ~50–100ms per call — the same O(1) cache-hit cost applies, so the speedup scales.

## Verification

```bash
$ cd apps/prometheus && uv run pytest tests/test_cache/ -q
33 passed in 43.39s

$ uv run pytest -q --ignore=tests/test_db
544 passed, 8 warnings in 75.25s
```

## Deviations from Plan

### Combined commits (organisational, not behavioural)

The plan implies one commit per task. Tasks 1 and 2 both modify `automation_service.py` at adjacent lines (4 invalidate hooks + 1 prewarm hook + 2 imports). Splitting them by hunk would make `git log --follow` noisy with no review benefit. They are bundled into commit `6cafc4c`. Task 3 (analysis_service.py + caller hoist) is a clean separate commit `d3deb19`.

### Auto-fixed Issues

**1. [Rule 1 — Test signature drift] `test_pipeline_isolation::test_analyze_step_isolation` mock signature**

- **Found during:** Task 3 GREEN run (full test suite)
- **Issue:** Pre-existing test mocks `_run_technical` with signature `(symbol)`. Task 3's W2 hoist widened the production signature to `_run_technical(symbol, run_id=None)`, and the kwarg-style call from `run_full` raised `TypeError: got an unexpected keyword argument 'run_id'` inside the mock.
- **Fix:** Widened the test's `_tech` mock signature to `(symbol: str, run_id: int | None = None) -> None`. No production behaviour change.
- **Files modified:** `apps/prometheus/tests/test_services/test_pipeline_isolation.py` (1 line)
- **Commit:** `d3deb19`

### Pre-existing Issues (Out of Scope — logged to `deferred-items.md`)

3 `ruff F401` unused-import warnings in `automation_service.py` and `analysis_service.py` predate Phase 26 (introduced in commit `a25d9c5`, "refactor(22-05)"). Not introduced by 26-05; logged to `.planning/phases/26-caching/deferred-items.md` for a future cleanup pass.

### Authentication Gates

None.

### Architectural Changes

None — the plan was executed as designed.

## SC #4 Closure Statement

ROADMAP Success Criterion #4 verbatim:

> "Sau `run_daily_pipeline`, cache cho hot keys (ranking + market summary) đã pre-warm — first request từ user log `cache=hit` không phải `miss`."

**Status: closed.** End of `run_daily_pipeline` invalidates the version-key namespace + the two read-side namespaces, then immediately calls `prewarm_hot_keys` which routes both compute paths through `get_or_compute`. The single-flight lock on `(namespace, key)` guarantees that any user request landing during the prewarm window collapses into the same compute, never a duplicate. After prewarm completes, both hot keys are populated; the next read-path request returns from the cache and `CacheHeaderMiddleware` (26-02) emits `X-Cache: hit`.

The verbatim SC #4 test `test_prewarm_fills_ranking_and_market_summary` (gated `requires_pg`) asserts `len(_caches["scores:ranking"]) >= 1` and `len(_caches["market:summary"]) >= 1` after `await prewarm_hot_keys(factory, ranking_limit=50)`.

## TDD Gate Compliance

- ✅ RED commit (`test(26-05)`): `e11e0f1`
- ✅ GREEN commits (`feat(26-05)`): `6cafc4c`, `d3deb19`
- No REFACTOR commit needed — wrapper + prewarm shipped clean on first GREEN.

## Threat Flags

None — no new attack surface introduced. All changes are server-internal cache reads/writes routed through pre-existing concentrators (`get_or_compute`, `invalidate_namespace`).

## Self-Check: PASSED

- ✅ `apps/prometheus/src/localstock/cache/prewarm.py` exists (123 lines).
- ✅ `apps/prometheus/src/localstock/services/automation_service.py` contains `invalidate_namespace("indicators")`, `invalidate_namespace("scores:ranking")`, `invalidate_namespace("market:summary")`, `invalidate_namespace("pipeline:latest_run_id")`, `await prewarm_hot_keys(self.session_factory)`.
- ✅ `apps/prometheus/src/localstock/services/analysis_service.py` contains `async def cached_analyze_technical_single` with `run_id` parameter (no default).
- ✅ Commits `e11e0f1`, `6cafc4c`, `d3deb19` present in `git log`.
- ✅ All 33 `tests/test_cache/` tests pass.
- ✅ Full suite (excl. test_db migrations) — 544 passed.
- ✅ Indicator cache speedup empirically measured at 99.7% reduction (107.53ms → 0.29ms).
