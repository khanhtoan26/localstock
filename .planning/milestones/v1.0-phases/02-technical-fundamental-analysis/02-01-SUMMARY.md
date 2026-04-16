---
phase: 02-technical-fundamental-analysis
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgresql, pandas-ta, analysis-models, repositories]

# Dependency graph
requires:
  - phase: 01-data-pipeline-and-storage
    provides: Base ORM models (Stock, StockPrice, FinancialStatement), repository pattern, Alembic async migration setup
provides:
  - TechnicalIndicator model with 28 indicator columns for daily technical analysis storage
  - FinancialRatio model with 23 ratio/value columns for fundamental analysis storage
  - IndustryGroup, StockIndustryMapping, IndustryAverage models for VN industry comparison
  - IndicatorRepository with bulk_upsert and query methods
  - RatioRepository with upsert and query methods
  - IndustryRepository with groups, mappings, and averages CRUD
  - pandas-ta as runtime dependency for indicator computation
affects: [02-02-technical-indicator-computation, 02-03-fundamental-ratio-extraction, 02-04-industry-comparison, 03-scoring-engine]

# Tech tracking
tech-stack:
  added: [pandas-ta (runtime), numpy (runtime)]
  patterns: [analysis model pattern with computed_at timestamps, composite unique constraints for upsert]

key-files:
  created:
    - src/localstock/db/repositories/indicator_repo.py
    - src/localstock/db/repositories/ratio_repo.py
    - src/localstock/db/repositories/industry_repo.py
    - src/localstock/analysis/__init__.py
    - tests/test_analysis/__init__.py
    - alembic/versions/2cd114a9d495_add_analysis_tables.py
  modified:
    - src/localstock/db/models.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "pandas-ta moved from dev to main deps — required at runtime for indicator computation"
  - "numpy added as explicit main dep — needed by pandas-ta and analysis computations"
  - "All analysis models use DateTime(timezone=True) for computed_at — lesson from Phase 1 UAT"

patterns-established:
  - "Analysis model pattern: id + symbol + date/period + indicator columns + computed_at timestamp"
  - "Composite unique constraints for upsert: (symbol, date) for indicators, (symbol, year, period) for ratios"
  - "Repository bulk_upsert with dynamic update_cols excluding primary key fields"

requirements-completed: [TECH-01, TECH-02, TECH-03, TECH-04, FUND-01, FUND-02, FUND-03]

# Metrics
duration: 4min
completed: 2026-04-15
---

# Phase 02 Plan 01: Analysis Database Foundation Summary

**5 SQLAlchemy analysis models, 3 repositories with pg_insert upsert, Alembic migration creating 5 tables for technical/fundamental analysis storage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-15T07:56:52Z
- **Completed:** 2026-04-15T08:00:58Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Added 5 new ORM models (TechnicalIndicator, FinancialRatio, IndustryGroup, StockIndustryMapping, IndustryAverage) extending Phase 1 schema
- Created 3 repository classes following Phase 1 pg_insert upsert pattern with AsyncSession
- Generated and applied Alembic migration creating 5 new tables with proper indexes and constraints
- Moved pandas-ta from dev to main dependencies; added numpy as explicit runtime dep

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 5 analysis SQLAlchemy models + update dependencies** - `816595c` (feat)
2. **Task 2: Create indicator, ratio, and industry repositories** - `5013b10` (feat)
3. **Task 3: Generate Alembic migration and push schema** - `5ecba46` (feat)

## Files Created/Modified
- `src/localstock/db/models.py` - Added TechnicalIndicator, FinancialRatio, IndustryGroup, StockIndustryMapping, IndustryAverage models with Text import
- `src/localstock/db/repositories/indicator_repo.py` - IndicatorRepository with bulk_upsert, get_latest, get_by_date_range, get_symbols_with_indicators, count_by_symbol
- `src/localstock/db/repositories/ratio_repo.py` - RatioRepository with upsert_ratio, bulk_upsert, get_latest, get_by_period, get_all_for_symbol
- `src/localstock/db/repositories/industry_repo.py` - IndustryRepository with upsert_groups, get_all_groups, upsert_mappings, get_symbols_by_group, get_group_for_symbol, upsert_averages, get_averages
- `src/localstock/analysis/__init__.py` - Analysis module package init
- `tests/test_analysis/__init__.py` - Test analysis package init
- `alembic/versions/2cd114a9d495_add_analysis_tables.py` - Migration creating 5 analysis tables
- `pyproject.toml` - pandas-ta moved to main deps, numpy added, pandas-ta removed from dev group
- `uv.lock` - Updated lockfile reflecting dependency changes

## Decisions Made
- pandas-ta moved from dev to main dependencies — it's required at runtime for indicator computation, not just testing
- numpy added as explicit main dependency — needed by pandas-ta and future analysis computations
- All timestamp columns use DateTime(timezone=True) — following Phase 1 UAT lesson for timezone-aware timestamps

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Alembic migration applied automatically.

## Next Phase Readiness
- All 5 analysis tables exist in PostgreSQL, ready for Plans 02-04 to write computed data
- 3 repositories provide complete CRUD interface for all analysis tables
- pandas-ta available as runtime dependency for technical indicator computation in Plan 02
- Analysis module package created for upcoming computation logic

---
*Phase: 02-technical-fundamental-analysis*
*Completed: 2026-04-15*
