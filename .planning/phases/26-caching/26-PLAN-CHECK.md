---
phase: 26-caching
artifact: PLAN-CHECK
verdict: NEEDS REVISION
blockers: 3
warnings: 2
checked: 2026-04-29
---

# Phase 26 — Plan Verification

## Verdict: NEEDS REVISION

Three blockers must be addressed before execution. Two warnings should be
fixed in the same revision pass. All other dimensions (SC coverage,
requirement coverage, decision compliance, pitfall coverage, RED test
count, threat-model traceability) are clean.

---

## Headline Coverage (CLEAN ✅)

### SC #1..#5 — exactly one closing plan with verbatim citation

| SC | Closing Plan | Closing Test | Verbatim Quote in must_haves.truths? |
|----|--------------|--------------|--------------------------------------|
| #1 | 26-04 | `test_perf_ranking::test_ranking_cache_hit_p95_under_50ms` | ✅ verbatim |
| #2 | 26-03 | `test_versioning::test_new_pipeline_run_invalidates_old_keys` | ✅ verbatim |
| #3 | 26-01 | `test_single_flight::test_concurrent_cold_key_single_compute` | ✅ verbatim |
| #4 | 26-05 | `test_prewarm::test_prewarm_fills_ranking_and_market_summary` | ✅ verbatim |
| #5 | 26-06 | `test_janitor::*` (+ supporting `test_metrics_exposed` from 26-02) | ✅ verbatim |

### CACHE-01..07 — exactly one plan marks each Done

| Req | Plan | OK |
|-----|------|----|
| CACHE-01 | 26-04 | ✅ |
| CACHE-02 | 26-03 | ✅ |
| CACHE-03 | 26-05 | ✅ |
| CACHE-04 | 26-01 | ✅ |
| CACHE-05 | 26-05 | ✅ |
| CACHE-06 | 26-06 | ✅ |
| CACHE-07 | 26-02 | ✅ |

### D-01..D-08 — honored (with two ratifications carried verbatim)

- D-01 ✅ pipeline_run_id key shape; reader composes via `resolve_latest_run_id`
- D-02 ✅ TTL table verbatim in 26-01 registry
- D-03 ✅ WeakValueDictionary + `asyncio.Lock`; P-2/P-3 mitigations encoded
- D-04 ✅ 4 invalidate hooks at automation_service.py:109/142/174 (RESEARCH §3 lines)
- D-05 ✅ pre-warm via `get_or_compute` (Q-3 — no direct cache writes)
- D-06 ✅ key shape `indicators:{symbol}:run={run_id}` (Q-B ratification 2026-04-29)
- D-07 ✅ `src/localstock/cache/` package layout
- D-08 ✅ `cache_name` label (ratification 2026-04-29) carried in 26-02

### Pitfall coverage P-1..P-9

All 9 pitfalls from RESEARCH §7 appear in the relevant plan's `<notes>`:
P-1/2/3/9 (26-01), P-4 (26-02), P-2 (26-03), P-2/7 (26-04), P-5/6/7 (26-05), P-8 (26-06).
✅

### RED test count

26-01 ≥7, 26-02 = 6, 26-03 = 5, 26-04 = 4, 26-05 = 10, 26-06 = 4. **Total ≈ 36 tests** (≥ 20 expected). ✅

### Threat-model traceability

Each plan ships its own threat table; threats trace to D-* mitigations
(e.g. T-26-01-02 → D-03; T-26-04-01 → D-01 + D-04; T-26-05-03 → P-6 +
D-03; T-26-06-03 → APScheduler max_instances=1). ✅

### Wave DAG / file-conflict matrix

RESEARCH §6 claims zero within-wave conflicts. **One within-wave conflict
detected** (Blocker #1 below). All other wave/file pairings are disjoint.

---

## Blockers

### B1 — `cache_compute_total` straddles 26-01 + 26-02 (within-wave file conflict)

**Severity:** BLOCKER (within-wave conflict on `observability/metrics.py`).

**What the plans say:**

- **26-01 Task 2 Section E** instructs the executor to add an idempotency-guarded `cache_compute_total` declaration to `apps/prometheus/src/localstock/observability/metrics.py`. Quote: *"Open `observability/metrics.py`, find the cache counter block at line 153–179, append (idempotent — guard with `if "cache_compute_total" not in metrics`)"*.
- **26-01 frontmatter `files_modified` does NOT list `observability/metrics.py`.** The plan modifies a file it does not declare.
- **26-02 frontmatter** lists `observability/metrics.py` and Task 1 instructs *"If 26-01 Task 2 already inserted a stub `cache_compute_total` via the no-overwrite guard, REPLACE that stub with the canonical declaration"*.
- Both plans are Wave 1 (`wave: 1`, `depends_on: []` for both).

**Why this fails the file-conflict matrix:** RESEARCH §6 explicitly claims `observability/metrics.py` is touched by *26-02 only*. The plans deviate from research. Two parallel-eligible plans editing the same file in the same wave can produce non-deterministic merge order; the "shim + later replace" pattern only works under strict sequencing.

**Recommended fix (option A — cleanest):**
Move the canonical `cache_compute_total` declaration entirely into **26-01**:
1. Add `apps/prometheus/src/localstock/observability/metrics.py` to 26-01 `files_modified`.
2. Drop Section E's idempotency guard; add the canonical declaration alongside the existing cache counters (mirroring the `_register(Counter, ...)` pattern at metrics.py:153–179).
3. Strip the "REPLACE that stub" language from 26-02 Task 1 — 26-02 only adds `cache_prewarm_errors_total`.
4. Update RESEARCH §6 file-conflict matrix to show metrics.py touched by both 26-01 and 26-02 with disjoint regions, OR reorder plans so 26-02 inherits a Wave-2 dependency on 26-01.

**Alternative (option B):**
Sequentialize via `depends_on`: change 26-02 to `depends_on: [26-01]` (becomes Wave 2). Loses parallelism but keeps the shim/replace dance.

### B2 — Test fixtures `db_session` and `async_client` do not exist project-wide

**Severity:** BLOCKER (Wave 0 gap; tests will error at collection time).

**What the plans assume:**

- 26-03 `test_pipeline_run_repo.py` and `test_versioning.py` use `db_session`.
- 26-04 `test_perf_ranking.py`, `test_perf_market.py`, and `test_route_caching_integration.py` use `async_client` AND `db_session`.
- 26-05 `test_prewarm.py` uses `db_session`.

**What actually exists** (verified by inspection):

| Location | Defines |
|----------|---------|
| `apps/prometheus/tests/conftest.py` | `_configure_test_logging`, `sample_ohlcv_df`, `sample_company_overview`, `sample_corporate_events`, `sample_financial_data`. **No `db_session`. No `async_client`.** |
| `apps/prometheus/tests/test_api/conftest.py` | `app`, `client` (sync `TestClient`), `mock_session`, `override_session`, `mock_engine`. **No `db_session`. No `async_client`.** |
| `apps/prometheus/tests/test_dq/test_quarantine_repo.py:33` | A *file-local* `db_session` fixture (Postgres-backed, gated by `requires_pg`) — not visible outside that module. |
| `apps/prometheus/tests/test_db/test_migration_24_pipeline_durations.py` | Marker `requires_pg` exists but no shared fixture. |

**Impact:** Every test that lists `db_session` or `async_client` as a parameter will raise `fixture '<name>' not found` at collection. Both perf tests, the SC #2 test, and the SC #4 test would fail before assertion.

**Recommended fix:**
Add an explicit Wave 0 task (either inside 26-01 or as a new pre-Wave-1 plan) to create shared async fixtures. Two options:

A. Promote the `test_dq/test_quarantine_repo.py:33` `db_session` fixture into `apps/prometheus/tests/conftest.py` (session-scoped per test, async-yield, transactional rollback, gated by `requires_pg`). Then add an `async_client` fixture using `httpx.AsyncClient(app=create_app(), base_url="http://test")` paired with the test_api isolation pattern.

B. Add the fixtures to `apps/prometheus/tests/test_cache/conftest.py` (currently only resets `_locks`). Localizes the dependency to the cache test package.

Either way, this must land BEFORE 26-03/04/05 and must be reflected in `26-VALIDATION.md` Wave 0 section (which currently lists only `__init__.py` + `conftest.py`-with-locks-cleanup).

### B3 — 26-06 test imports `build_scheduler`; actual factory is `setup_scheduler`

**Severity:** BLOCKER (test will fail at import).

**What the plan says:** `test_janitor.py::test_janitor_registered_in_scheduler` imports
```python
from localstock.scheduler.scheduler import build_scheduler  # adjust import to actual factory name
sched = build_scheduler()
```
followed by an executor NOTE: *"the executor must read `scheduler.py` to find the actual factory function name (likely `build_scheduler` or `create_scheduler` or `setup_scheduler`); adjust the import accordingly."*

**What actually exists** (verified by `grep -nE "^def .*scheduler"`):
```
apps/prometheus/src/localstock/scheduler/scheduler.py:23:def setup_scheduler() -> AsyncIOScheduler:
```

**Impact:** As written, the test module raises `ImportError` at collection. The executor NOTE relies on the executor remembering to fix the import — but verify-on-collection is a Nyquist signal we should not pre-corrupt.

**Recommended fix:** Replace `build_scheduler` with `setup_scheduler` directly in the plan's test code listing. Remove the speculative NOTE — the planner has the verified name from the codebase. (Bonus: plan should also note that `setup_scheduler()` may already wire the cache_janitor job after Task 1 of 26-06, so the test asserts post-registration state — this matches the intent.)

---

## Warnings

### W1 — `routes/market.py` refactor in 26-05 not declared in frontmatter

**Severity:** WARNING (not a within-wave conflict because 26-04 / Wave 2 finishes before 26-05 / Wave 3, but still a frontmatter-truth mismatch and a layering smell).

**What the plan says:** 26-05 Task 2 declares: *"NOTE for executor: if `localstock.api.routes.market` does not expose `build_market_summary`, refactor the existing route handler to extract its `_compute` body into a module-level `async def build_market_summary(session: AsyncSession) -> MarketSummaryResponse:` helper and have the route call it."*

**Verified state:** `apps/prometheus/src/localstock/api/routes/market.py` currently exposes only `async def get_market_summary(...)` at line 39. There is no `build_market_summary` helper. So 26-05 Task 2 *will* trigger the refactor branch.

**But:** `routes/market.py` is NOT in 26-05's `files_modified` frontmatter.

**Recommended fix (option A — preferred):**
Move the refactor into **26-04**, which already modifies `routes/market.py` to wrap with `get_or_compute`. While doing the wrap, extract the underlying compute into a module-level `build_market_summary(session)` helper. The route handler then becomes a thin `get_or_compute` wrapper around the helper. 26-05 Task 2 then simply imports `build_market_summary` — no refactor branch, no frontmatter delta, clean separation of "data builder" from "cache wrapping".

**Recommended fix (option B):**
Add `apps/prometheus/src/localstock/api/routes/market.py` to 26-05's `files_modified`. Less clean — keeps a layering inversion where pre-warm refactors a route module — but acceptable.

### W2 — Indicator cache `run_id` resolution: hoisting should be mandatory, not optional

**Severity:** WARNING (correctness OK; perf hygiene).

**What the plan says (26-05 Task 3 Section C):**
> *"Update the caller at line ~452. … resolve at each call; if perf-relevant the executor may hoist it"*
>
> ```python
> run_id = await resolve_latest_run_id(get_session_factory())
> row = await self.cached_analyze_technical_single(symbol, ohlcv_df, run_id)
> ```

**Why this is a problem:** The caller is a per-symbol loop iterating over ~400 HOSE symbols. As written, the line above is **inside** the loop — resolving `run_id` 400× per analysis run. Each call:
- Acquires a `WeakValueDictionary` lock for `pipeline:latest_run_id:current`,
- Hits the 5s TTL cache (so 399 of 400 are cache hits, ~microseconds each),
- BUT still pays the asyncio lock acquire/release cycle and a contextvar set/reset.

It will not violate correctness, but adds non-trivial overhead per analysis run and, more importantly, masks a design seam: the caller knows it is processing one pipeline run, so `run_id` is a loop invariant.

**Recommended fix:** Change the plan from "may hoist" to "MUST hoist". The caller resolves `run_id` ONCE before entering the per-symbol loop and passes it as a parameter:

```python
run_id = await resolve_latest_run_id(get_session_factory())
for symbol, ohlcv_df in symbols:
    row = await self.cached_analyze_technical_single(symbol, ohlcv_df, run_id)
    ...
```

Document the constraint in the wrapper's docstring: "Caller MUST hoist `run_id` resolution out of any per-symbol loop — `run_id` is invariant for the duration of a single analysis pass."

---

## Other Observations (informational, no action required)

- **Wave parallelism:** 26-04 (Wave 2) `depends_on: [26-01, 26-02, 26-03]` — but 26-03 is also Wave 2. This makes 26-03 and 26-04 effectively sequential within Wave 2, not parallel. Acceptable per gsd convention (wave = max(deps)+1, both reach Wave 2 because their deps are Wave 1), but document it: 26-04 cannot start until 26-03 completes. The dependency graph in 26-VALIDATION.md should make this explicit ("Wave 2: 26-03 then 26-04, sequential").

- **`test_resolve_uses_5s_cache`** in 26-03 relies on the 5s TTL not expiring between two adjacent calls. Test runtime is well under 5s, so it works in practice. No change needed; just noting that the assertion is a subtle TTL race if the host is heavily loaded.

- **Test `test_prewarm_failure_increments_counter_and_does_not_raise`** uses an `@asynccontextmanager` whose body raises before yielding. Python may emit a `RuntimeWarning` about the generator never yielding. Functionally correct (the `async with` enters and immediately raises, which is what the test wants), but consider a cleaner stub like an object whose `__aenter__` raises.

- **D-08 cardinality bound** is asserted explicitly by `test_cardinality_bounded` in 26-02. Excellent.

- **Pre-warm direct-write hazard (Q-3 / RESEARCH §7 P-6)** is addressed: the plan body comments explicitly say "Pre-warm goes through the SAME `get_or_compute` choke point". ✅

- **Per-namespace `try/except` around invalidate calls** is consistent across all 4 hooks. ✅

---

## Dimension Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Requirement Coverage | ✅ | 7/7 CACHE-* requirements covered, exactly once each |
| Task Completeness | ✅ | All tasks have files/action/verify/done |
| Dependency Correctness | ⚠️ | Within-wave file conflict (B1); otherwise clean |
| Key Links Planned | ✅ | All artifacts wired (D-01 composer → resolve_latest_run_id; ContextVar→middleware; popitem→eviction counter) |
| Scope Sanity | ✅ | 6 plans, 1–3 tasks each, file counts reasonable |
| must_haves Derivation | ✅ | User-observable truths verbatim from SCs |
| Context Compliance | ✅ | All D-01..D-08 + ratifications honored |
| Architectural Tier | ✅ | Hooks placed per RESEARCH responsibility map |
| Cross-Plan Data Contracts | ⚠️ | metrics.py shared between 26-01 and 26-02 (B1) |
| copilot-instructions.md | ✅ | uv, pytest, loguru, repository pattern, @observe — all honored |
| Research Resolution | ✅ | Q-1..Q-5 resolved; Q-A/Q-B ratified |
| Pattern Compliance | ✅ | InstrumentedTTLCache, CacheHeaderMiddleware, IntervalTrigger jobs all mirror existing patterns |
| Nyquist | ⚠️ | Test fixtures missing (B2) makes ≥4 RED tests un-collectible |

---

## Required Revisions (in priority order)

1. **Fix B1** — Move canonical `cache_compute_total` declaration into 26-01; update 26-01 `files_modified` to include `observability/metrics.py`; strip "REPLACE shim" language from 26-02. Update RESEARCH §6 file-conflict matrix.
2. **Fix B2** — Add Wave 0 task (in 26-01 Task 1 or new pre-Wave plan) creating shared `db_session` and `async_client` fixtures. Update 26-VALIDATION.md Wave 0 section.
3. **Fix B3** — Replace `build_scheduler` with `setup_scheduler` in 26-06 test code listing; remove speculative NOTE.
4. **Address W1** — Move `build_market_summary` extraction into 26-04 (preferred) or add `routes/market.py` to 26-05 frontmatter.
5. **Address W2** — Make `run_id` hoisting mandatory in 26-05 Task 3; resolve once before per-symbol loop, pass into wrapper.

After revision, re-run plan-checker. No re-research expected — all fixes are local to the plans.

---

**Approval status:** NEEDS REVISION
