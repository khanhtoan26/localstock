---
phase: 24-instrumentation-health
plan: 02
subsystem: db / observability
tags: [alembic, migration, pipeline-run, OBS-17, schema]
requires:
  - alembic head f11a1b2c3d4e (Phase 11 admin tables)
provides:
  - pipeline_runs.crawl_duration_ms (Integer, nullable)
  - pipeline_runs.analyze_duration_ms (Integer, nullable)
  - pipeline_runs.score_duration_ms (Integer, nullable)
  - pipeline_runs.report_duration_ms (Integer, nullable)
  - PipelineRun ORM Mapped[int | None] for the 4 columns
  - alembic head 24a1b2c3d4e5
affects:
  - apps/prometheus/src/localstock/db/models.py (PipelineRun)
  - apps/prometheus alembic upgrade chain
tech-stack:
  added: []
  patterns:
    - "per-call async engine in tests to survive pytest-asyncio per-function event loops"
key-files:
  created:
    - apps/prometheus/alembic/versions/24a1b2c3d4e5_pipeline_run_durations.py
    - apps/prometheus/tests/test_db/test_migration_24_pipeline_durations.py
  modified:
    - apps/prometheus/src/localstock/db/models.py
    - apps/prometheus/pyproject.toml
decisions:
  - "Migration uses nullable=True with no server_default per D-07 (existing rows stay NULL until 24-06 populates values)"
  - "No index on the duration columns (D-07 explicit)"
  - "requires_pg pytest marker registered for migration round-trip tests; tests build per-call async engines instead of reusing the module-cached singleton (which gets bound to a closed event loop across test functions)"
metrics:
  duration_minutes: 8
  tasks_completed: 2
  files_created: 2
  files_modified: 2
  completed_date: "2026-04-29"
commit: 316edf3
revision: 24a1b2c3d4e5
down_revision: f11a1b2c3d4e
---

# Phase 24 Plan 02: Alembic Migration for PipelineRun *_duration_ms Columns Summary

**One-liner:** Reversible Alembic migration `24a1b2c3d4e5` adds 4 nullable
`*_duration_ms` Integer columns to `pipeline_runs` and matching
`Mapped[int | None]` ORM fields, closing the schema half of OBS-17.

## What Was Built

- **Migration file** `apps/prometheus/alembic/versions/24a1b2c3d4e5_pipeline_run_durations.py`
  - `revision = "24a1b2c3d4e5"`, `down_revision = "f11a1b2c3d4e"`
  - `upgrade()`: `op.add_column` × 4 (`crawl_`, `analyze_`, `score_`, `report_duration_ms`),
    each `sa.Integer()`, `nullable=True`
  - `downgrade()`: `op.drop_column` × 4 in reverse order
- **ORM update** `apps/prometheus/src/localstock/db/models.py`
  - PipelineRun gains 4 `Mapped[int | None] = mapped_column(Integer, nullable=True)` columns
    in the same order as the migration, placed after `errors` and before `TechnicalIndicator`.
- **Round-trip tests** `apps/prometheus/tests/test_db/test_migration_24_pipeline_durations.py`
  - 2 tests, both marked `@pytest.mark.requires_pg` + `@pytest.mark.asyncio`
  - `test_migration_upgrade_adds_columns`: ensures DB at head, asserts EXPECTED ⊆ columns
  - `test_migration_downgrade_removes_columns`: subprocess `alembic downgrade -1`,
    asserts EXPECTED disjoint from columns, then upgrade head + reassert
  - Helper `_columns()` builds a per-call `create_async_engine` and disposes it,
    avoiding the module-cached engine getting bound to a closed event loop.
- **pyproject.toml**: registered `requires_pg` pytest marker.

## Verification (executed)

| Check | Command | Result |
|---|---|---|
| Pre-flight head | `uv run alembic heads` | `f11a1b2c3d4e (head)` ✅ |
| New head | `uv run alembic heads` (post-file) | `24a1b2c3d4e5 (head)` ✅ |
| Forward migration | `uv run alembic upgrade head` | exit 0 ✅ |
| Column presence (information_schema) | inline asyncpg query | 4 columns confirmed ✅ |
| Reversibility | `alembic downgrade -1 && upgrade head` | clean ✅ |
| ORM hasattr check | inline python | ORM OK ✅ |
| Migration tests | `pytest tests/test_db/test_migration_24_pipeline_durations.py -x -q` | 2 passed in 19.21s ✅ |
| test_db regression | `pytest tests/test_db/ -x -q` | 53 passed in 19.50s ✅ |
| Full suite (excl. 24-01 RED) | `pytest -q --ignore=tests/test_observability/test_decorators.py` | 473 passed ✅ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test-helper engine reuse across event loops**
- **Found during:** Task 2 first pytest run.
- **Issue:** `localstock.db.database.get_engine()` caches one async engine at
  module scope. When pytest-asyncio creates a fresh function-scoped event
  loop per test, the second test in the file failed with
  `RuntimeError: Event loop is closed` while asyncpg tried to clean up the
  cached connection bound to the prior (now closed) loop.
- **Fix:** Replaced `get_engine()` in the test helper with a per-call
  `create_async_engine(...)` plus `await eng.dispose()` in `finally`. Reuses
  the same DB URL via `get_settings()` and the same `connect_args` as the
  app (`prepared_statement_cache_size=0`, `statement_cache_size=0`).
- **Files modified:** `tests/test_db/test_migration_24_pipeline_durations.py`
- **Commit:** `316edf3` (single atomic commit)

**2. [Rule 3 - Blocking] subprocess `cwd="apps/prometheus"` was relative**
- **Found during:** writing the test file from the planner template.
- **Issue:** Planner template used `cwd="apps/prometheus"` for the subprocess
  alembic call, which resolves relative to the pytest invocation dir.
  Running pytest from `apps/prometheus/` would expand to a non-existent
  nested path and fail.
- **Fix:** Resolved `APP_ROOT = Path(__file__).resolve().parents[2]` and use
  it for both `cwd` calls. Works regardless of pytest invocation directory.
- **Files modified:** `tests/test_db/test_migration_24_pipeline_durations.py`
- **Commit:** `316edf3`

### Out-of-Scope Discoveries

- `tests/test_observability/test_decorators.py::test_observe_sync_success`
  fails: histogram count delta is 0, expected 1. This is the Phase **24-01**
  RED test (commit `d0d4b66`, "test(observability): RED tests for @observe
  decorator (Phase 24-01)") and is intentionally failing until 24-01 GREEN
  lands. Not caused by 24-02 changes — confirmed by isolating the suite
  (`pytest -q --ignore=tests/test_observability/test_decorators.py` →
  473 passed). Not fixed; belongs to 24-01.

## Authentication Gates

None. Live Supabase Postgres connection was already configured via
`localstock.config.get_settings()` and worked end-to-end.

## Self-Check: PASSED

- `apps/prometheus/alembic/versions/24a1b2c3d4e5_pipeline_run_durations.py` — FOUND
- `apps/prometheus/tests/test_db/test_migration_24_pipeline_durations.py` — FOUND
- `apps/prometheus/src/localstock/db/models.py` PipelineRun has 4 new mapped columns — FOUND (`hasattr` check passed)
- Commit `316edf3` — FOUND in `git log`
- Alembic head `24a1b2c3d4e5` — FOUND
