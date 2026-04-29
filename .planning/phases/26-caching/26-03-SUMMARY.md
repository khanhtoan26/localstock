---
phase: 26-caching
plan: 03
subsystem: cache + db
status: Complete
tags: [cache, versioning, pipeline_run_id, sc-2, cache-02, d-01, d-02]
requirements: [CACHE-02]
dependency_graph:
  requires:
    - 26-01 (cache.get_or_compute, invalidate_namespace, registry namespace `pipeline:latest_run_id`)
    - Wave-0 fixture `db_session` (project-wide, lifted in 26-01)
  provides:
    - `localstock.cache.resolve_latest_run_id(session_factory)` → 5s-cached `pipeline_run_id`
    - `localstock.db.repositories.pipeline_run_repo.PipelineRunRepository.get_latest_completed()`
  affects:
    - 26-04 (route handlers compose `run={id}` keys via the new resolver)
    - 26-05 (pipeline finalize hook MUST `invalidate_namespace('pipeline:latest_run_id')` to advance version key < 5s)
tech_stack:
  added: []
  patterns:
    - Async-SQLAlchemy 2.0 read-only repo (mirrors `news_repo.py`)
    - Cached version-key resolver wrapping repo call in `get_or_compute`
    - Local import of `get_or_compute` inside `resolve_latest_run_id` to side-step circular load
key_files:
  created:
    - apps/prometheus/src/localstock/db/repositories/pipeline_run_repo.py
    - apps/prometheus/src/localstock/cache/version.py
    - apps/prometheus/tests/test_db/test_pipeline_run_repo.py
    - apps/prometheus/tests/test_cache/test_versioning.py
  modified:
    - apps/prometheus/src/localstock/cache/__init__.py (re-export `resolve_latest_run_id`)
decisions:
  - "Local import of `get_or_compute` inside `version.resolve_latest_run_id` body (vs. module-top) so `__init__.py` can re-export the helper without circular import. `cache/__init__.py` imports `version` AFTER `get_or_compute` is defined."
  - "RED tests `_purge` `pipeline_runs` at the start so the assertions hold against any pre-existing fixture data; relies on transactional rollback at fixture teardown for full isolation."
  - "Versioning test simulates 26-05's pipeline finalize by calling `invalidate_namespace('pipeline:latest_run_id')` + `invalidate_namespace('scores:ranking')` directly — the contract 26-05 must honour."
metrics:
  duration_minutes: ~25
  tasks: 2
  files_created: 4
  files_modified: 1
  tests_added: 5
  tests_passing: 18 (cache + new repo tests; full suite 583 passed, 2 fail out-of-scope — see Deferred Issues)
completed_date: 2026-04-29
---

# Phase 26 Plan 03: PipelineRunRepository + version-key resolver Summary

**TDD versioned cache key for scoring outputs — `pipeline_run_id` lookup with 5s TTL closes ROADMAP SC #2 verbatim.**

## Objective Recap

Implement the per-request lookup of the current `pipeline_run_id` (D-01) used by every cache-key composer, backed by:

1. New `PipelineRunRepository.get_latest_completed()` reading the most-recent `status='completed'` row.
2. New `cache.version.resolve_latest_run_id(session_factory)` wrapping that repo call in `get_or_compute(namespace='pipeline:latest_run_id', key='current', ...)` so back-to-back composers share a 5s-TTL cached lookup (D-02).

Closes verbatim ROADMAP Success Criterion #2:

> "Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data, không cần đợi TTL."

## What Shipped

### Task 1 — `PipelineRunRepository.get_latest_completed()` (CACHE-02 DB layer)

- **Repo** (`db/repositories/pipeline_run_repo.py`, 41 LOC): async-SQLAlchemy 2.0, `select(PipelineRun.id).where(status='completed').order_by(completed_at.desc()).limit(1)` → `int | None`. Filters `running`/`failed` rows (T-26-03-02 mitigation: a running run_id would yield empty downstream data).
- **RED tests** (`tests/test_db/test_pipeline_run_repo.py`):
  - `test_returns_none_when_no_completed_runs`
  - `test_returns_latest_completed_id` — seeds older + newer + running, asserts newer.id returned
  - `test_ignores_failed_and_running_runs`
- **Commits:** `4c1646a` (RED) → `54ff416` (GREEN). 3/3 pass.

### Task 2 — `cache.version.resolve_latest_run_id` + SC #2 closure

- **Helper** (`cache/version.py`, ~40 LOC): zero-arg async-CM session factory pattern (matches `AutomationService.session_factory`); wraps repo call in `get_or_compute('pipeline:latest_run_id', 'current', _fetch)`. Module docstring documents the invalidation contract 26-05 must honour (T-26-03-01 mitigation).
- **Public surface** (`cache/__init__.py`): `__all__` extended with `resolve_latest_run_id`; import placed AFTER `get_or_compute` is defined to avoid circular load (decision documented in code comment).
- **RED tests** (`tests/test_cache/test_versioning.py`):
  - `test_new_pipeline_run_invalidates_old_keys` — verbatim SC #2 closure: seeds run1 (id=N1), populates `scores:ranking:limit=50:run=N1`, inserts run2 (id=N2), invalidates both namespaces (simulating 26-05 finalize hook), asserts `resolve_latest_run_id` returns N2 and the new key composes/fills cleanly. Old `run=N1` key is unreachable by composers — old key never serves stale data.
  - `test_resolve_uses_5s_cache_namespace` — back-to-back calls within TTL produce 1 miss + 1 hit on `pipeline:latest_run_id` namespace counters (D-02 verified).
- **Commits:** `05a697d` (RED) → `937565b` (GREEN). 2/2 pass.

## Verification

```bash
cd apps/prometheus
uv run pytest tests/test_cache/ tests/test_db/test_pipeline_run_repo.py -q
# 18 passed in 15.07s

uvx ruff check src/localstock/cache/ src/localstock/db/repositories/pipeline_run_repo.py \
               tests/test_cache/test_versioning.py tests/test_db/test_pipeline_run_repo.py
# All checks passed!

uv run pytest -q
# 583 passed, 2 failed (both out-of-scope — see Deferred Issues)
```

## ROADMAP SC #2 Closure (verbatim)

> "Cache key cho scoring outputs include `pipeline_run_id` — verified bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data, không cần đợi TTL."

`tests/test_cache/test_versioning.py::test_new_pipeline_run_invalidates_old_keys`:

1. Seeds `PipelineRun(id=N1, status='completed')`; resolver returns `N1`.
2. Populates `scores:ranking:limit=50:run=N1` with `{"snapshot": "from_run_1"}`.
3. Inserts `PipelineRun(id=N2, status='completed')` (no commit yet — flush only).
4. Calls `invalidate_namespace('pipeline:latest_run_id')` + `invalidate_namespace('scores:ranking')` — exactly what the 26-05 finalize hook will do.
5. Resolver immediately returns `N2` (no 5s TTL wait).
6. New composer key `scores:ranking:limit=50:run=N2` is a miss-then-fill; old `run=N1` key is unreachable because composers only ever address the current `run_id`.

**Status: ✅ closed.**

## Threat Model Status

| Threat ID | Disposition | Verification |
|-----------|-------------|--------------|
| T-26-03-01 (5s TTL delays new-run visibility) | Mitigated | Test exercises invalidate hook the 26-05 finalize will install |
| T-26-03-02 (running run_id leaks into key) | Mitigated | `where(status='completed')` enforced in repo + tested by `test_ignores_failed_and_running_runs` |
| T-26-03-03 (DB hammering) | Mitigated | 5s TTL cache verified by `test_resolve_uses_5s_cache_namespace` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between `cache/__init__.py` and `cache/version.py`**
- **Found during:** Task 2 GREEN
- **Issue:** Plan suggested `from localstock.cache import get_or_compute` at top of `cache/version.py`, but `cache/__init__.py` re-exports `resolve_latest_run_id` from `cache.version` — top-level import would cycle on first load.
- **Fix:** Moved `from localstock.cache import get_or_compute` inside the `resolve_latest_run_id` function body (lazy import); `cache/__init__.py` imports `resolve_latest_run_id` AFTER `get_or_compute` is defined. Documented in code comments at both sites.
- **Files modified:** `cache/version.py`, `cache/__init__.py`
- **Commit:** `937565b`

**2. [Rule 1 - Bug] Plan-style RED test for `test_returns_latest_completed_id` would have failed against pre-existing fixture rows**
- **Found during:** Task 1 RED
- **Issue:** Plan's test snippet adds 3 rows and asserts `latest == newer.id`, but if other tests had created completed PipelineRun rows earlier in the same DB, the assertion could pick up a stranger row.
- **Fix:** Added `_purge` helper that `DELETE FROM pipeline_runs` at start of each test (rolled back at fixture teardown). All 3 tests gated by this. Same pattern applied to versioning tests.
- **Files modified:** `tests/test_db/test_pipeline_run_repo.py`, `tests/test_cache/test_versioning.py`
- **Commit:** `4c1646a` (RED already shipped with `_purge`)

**3. [Rule 1 - Test contract] Plan's `test_resolve_uses_5s_cache` referenced `before_misses` but never used it**
- **Found during:** Task 2 RED authoring
- **Issue:** Cosmetic — the snapshot was unused, would trigger ruff F841.
- **Fix:** Used both deltas (`hits` and `misses`) so the test asserts the full miss+hit pair, which is the actual D-02 contract.
- **Commit:** `05a697d`

### Path correction

Prompt header listed `apps/prometheus/src/localstock/db/pipeline_run_repo.py`, but plan frontmatter and `<files>` block authoritatively specified `db/repositories/pipeline_run_repo.py` (matching the existing `repositories/` layout). Followed the plan frontmatter.

## Deferred Issues

Logged to `.planning/phases/26-caching/deferred-items.md`:

1. **`tests/test_market_route.py::TestMarketSummaryResponse::test_endpoint_calls_repo`** fails in full-suite run only; passes in isolation. Caused by 26-04 wrapping `/market/summary` with `get_or_compute` — cached results from earlier tests bypass the mock this test installs. **Owner: 26-04** (cache-isolation fixture for route tests). NOT caused by 26-03.
2. **`tests/test_db/test_migration_24_pipeline_durations.py::test_migration_downgrade_removes_columns`** — pre-existing Phase-24 failure documented as ignored by the prompt.

## Commits

- `4c1646a` test(26-03): RED — PipelineRunRepository.get_latest_completed (CACHE-02)
- `54ff416` feat(26-03): GREEN — PipelineRunRepository.get_latest_completed (CACHE-02)
- `05a697d` test(26-03): RED — versioning closure for SC #2
- `937565b` feat(26-03): GREEN — cache.version.resolve_latest_run_id (D-01, SC #2)

All commits include the required `Co-authored-by: Copilot` trailer.

## TDD Gate Compliance

- ✅ Task 1: RED (`4c1646a`, ImportError) → GREEN (`54ff416`, 3/3 pass). No refactor needed.
- ✅ Task 2: RED (`05a697d`, ImportError) → GREEN (`937565b`, 2/2 pass). No refactor needed.

## Self-Check: PASSED

**Files (all created/modified files exist):**
- ✅ `apps/prometheus/src/localstock/db/repositories/pipeline_run_repo.py`
- ✅ `apps/prometheus/src/localstock/cache/version.py`
- ✅ `apps/prometheus/src/localstock/cache/__init__.py` (re-export added)
- ✅ `apps/prometheus/tests/test_db/test_pipeline_run_repo.py`
- ✅ `apps/prometheus/tests/test_cache/test_versioning.py`

**Commits (all exist in `git log`):**
- ✅ `4c1646a` (RED — repo)
- ✅ `54ff416` (GREEN — repo)
- ✅ `05a697d` (RED — versioning)
- ✅ `937565b` (GREEN — versioning + helper)

**Acceptance:**
- ✅ ROADMAP SC #2 verbatim closure verified by `test_new_pipeline_run_invalidates_old_keys`
- ✅ 5s TTL on `pipeline:latest_run_id` verified by `test_resolve_uses_5s_cache_namespace`
- ✅ `resolve_latest_run_id` exported from `localstock.cache.__all__`
- ✅ ruff clean on all touched files
- ✅ 18/18 cache + new repo tests pass; full suite 583 passed (2 out-of-scope failures documented in deferred-items.md)
