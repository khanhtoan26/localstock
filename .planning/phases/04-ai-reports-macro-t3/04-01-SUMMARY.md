---
phase: 04-ai-reports-macro-t3
plan: 01
subsystem: database
tags: [models, repositories, migration, config, phase4-foundation]
dependency_graph:
  requires: [phase-03-scoring]
  provides: [MacroIndicator-model, AnalysisReport-model, MacroRepository, ReportRepository, phase4-config]
  affects: [scoring-weights, composite-score-redistribution]
tech_stack:
  added: []
  patterns: [pg_insert-upsert, subquery-join-latest, repository-pattern]
key_files:
  created:
    - src/localstock/db/repositories/macro_repo.py
    - src/localstock/db/repositories/report_repo.py
    - alembic/versions/add_phase4_macro_report_tables.py
    - src/localstock/macro/__init__.py
    - src/localstock/reports/__init__.py
    - tests/test_macro/__init__.py
    - tests/test_reports/__init__.py
    - tests/test_db/test_models_phase4.py
  modified:
    - src/localstock/db/models.py
    - src/localstock/config.py
    - tests/test_scoring/test_normalizer.py
decisions:
  - "Scoring weights rebalanced to 0.30/0.30/0.20/0.20 — macro dimension now active"
  - "MacroIndicator uses (indicator_type, period) as dedup key for upsert"
  - "AnalysisReport uses (symbol, date, report_type) as dedup key for upsert"
  - "get_all_latest uses subquery+join for per-type latest record retrieval"
metrics:
  duration: 3min
  completed: "2026-04-16T03:59:50Z"
  tasks: 2
  files: 11
---

# Phase 04 Plan 01: DB Foundation for Macro & Reports Summary

MacroIndicator and AnalysisReport ORM models with pg_insert upsert repositories, Alembic migration, updated scoring weights 0.30/0.30/0.20/0.20, and report generation config (top_n=20, max_tokens=4096).

## Tasks Completed

### Task 1: DB models, migration, repositories (TDD)
- **Commit:** `e9df34f` (RED), `1fad774` (GREEN)
- Added `MacroIndicator` model (8 fields: id, indicator_type, value, period, source, trend, recorded_at, fetched_at) with `uq_macro_indicator` constraint on (indicator_type, period)
- Added `AnalysisReport` model (12 fields: id, symbol, date, report_type, content_json, summary, recommendation, t3_prediction, model_used, total_score, grade, generated_at) with `uq_analysis_report` constraint on (symbol, date, report_type)
- Created `MacroRepository` with bulk_upsert (pg_insert + on_conflict_do_update), get_latest_by_type, get_all_latest (subquery+join pattern)
- Created `ReportRepository` with upsert, get_latest, get_by_date, get_by_symbol_and_date
- Created Alembic migration creating `macro_indicators` and `analysis_reports` tables
- Created package init files for `localstock.macro` and `localstock.reports`
- 42 new tests covering model fields, constraints, and repository method signatures

### Task 2: Config updates for Phase 4 activation
- **Commit:** `48ed709`
- Updated scoring weights: technical 0.35→0.30, fundamental 0.35→0.30, sentiment 0.30→0.20, macro 0.0→0.20
- Added `report_top_n: int = 20` and `report_max_tokens: int = 4096`
- Updated existing test_normalizer to match new weight defaults

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scoring_config_from_settings weight assertions**
- **Found during:** Task 2
- **Issue:** Existing test `test_scoring_config_from_settings` asserted old weight defaults (0.35/0.35/0.30/0.0)
- **Fix:** Updated assertions to match new defaults (0.30/0.30/0.20/0.20)
- **Files modified:** tests/test_scoring/test_normalizer.py
- **Commit:** 48ed709

## Verification Results

- ✅ All 189 tests pass (`uv run python -m pytest tests/ --timeout=30`)
- ✅ New Phase 4 model tests pass (42 tests in `test_models_phase4.py`)
- ✅ Config imports cleanly with new defaults
- ✅ Module packages importable: `localstock.macro`, `localstock.reports`
- ✅ Repository classes importable: `MacroRepository`, `ReportRepository`

## Decisions Made

1. **Scoring weights 0.30/0.30/0.20/0.20** — macro dimension now contributes 20% to composite score. Dynamic weight redistribution in compute_composite() handles cases where macro_score is None.
2. **MacroIndicator dedup on (indicator_type, period)** — each indicator type has one value per period, upsert overwrites value/source/trend/fetched_at.
3. **AnalysisReport dedup on (symbol, date, report_type)** — one report per stock per day per type, upsert overwrites content.
4. **Subquery+join for get_all_latest** — efficient per-type latest retrieval using max(recorded_at) grouped by indicator_type.

## Self-Check: PASSED

All 11 files verified present. All 3 commits (e9df34f, 1fad774, 48ed709) found in git log.
