---
phase: 01-foundation-data-pipeline
plan: 01
subsystem: database
tags: [python, uv, sqlalchemy, asyncpg, alembic, pydantic, supabase, vnstock]

# Dependency graph
requires: []
provides:
  - Python project scaffold with all Phase 1 dependencies
  - 5 SQLAlchemy ORM models (stocks, stock_prices, corporate_events, financial_statements, pipeline_runs)
  - Async database engine and session factory for Supabase PostgreSQL
  - Alembic async migration infrastructure
  - Abstract BaseCrawler with error-tolerant batch processing
  - Pytest test infrastructure with vnstock-format fixtures
affects: [01-02, 01-03, 01-04, 02-foundation]

# Tech tracking
tech-stack:
  added: [uv, fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, asyncpg, alembic, vnstock, pandas, httpx, loguru, tenacity, pytest, pytest-asyncio, pytest-timeout, ruff, mypy]
  patterns: [pydantic-settings env loading with lru_cache, async sqlalchemy engine factory, abstract base crawler with error-tolerant batch]

key-files:
  created:
    - pyproject.toml
    - src/localstock/__init__.py
    - src/localstock/config.py
    - src/localstock/db/database.py
    - src/localstock/db/models.py
    - src/localstock/crawlers/base.py
    - alembic.ini
    - alembic/env.py
    - tests/conftest.py
    - .env.example
    - .gitignore
    - README.md
  modified: []

key-decisions:
  - "Used BigInteger for StockPrice.volume column — volumes can exceed 2B (Integer max)"
  - "Added pytest-timeout dev dependency — required for timeout=30 config in pyproject.toml"

patterns-established:
  - "Config pattern: Pydantic BaseSettings with lru_cache singleton via get_settings()"
  - "DB pattern: create_async_engine factory + async_sessionmaker, expire_on_commit=False"
  - "Crawler pattern: BaseCrawler ABC with fetch() + fetch_batch() error-tolerant loop"
  - "Model pattern: DeclarativeBase with Mapped[type] + mapped_column(), UniqueConstraint in __table_args__"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05]

# Metrics
duration: 7min
completed: 2026-04-15
---

# Phase 01 Plan 01: Project Scaffold Summary

**Python project with uv, 5 SQLAlchemy ORM models for HOSE stock data, async Supabase PostgreSQL engine, Alembic migrations, and error-tolerant BaseCrawler**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-15T03:16:25Z
- **Completed:** 2026-04-15T03:23:23Z
- **Tasks:** 2
- **Files modified:** 22

## Accomplishments
- Python project initialized with uv, 13 runtime dependencies and 5 dev dependencies all installed and locked
- 5 SQLAlchemy ORM models defined with correct types, constraints (unique, index), and BigInteger for volume
- Async database engine and session factory configured for Supabase PostgreSQL via asyncpg
- Alembic configured for async migrations with model metadata auto-detection
- Abstract BaseCrawler implements D-02 error-tolerant batch processing (skip failed, continue, log)
- Pytest infrastructure with shared fixtures matching vnstock output formats

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project scaffold with uv, dependencies, config, and directory structure** - `f80ad95` (feat)
2. **Task 2: Create SQLAlchemy models, database engine, Alembic migrations, base crawler, and test infrastructure** - `6fb0355` (feat)

## Files Created/Modified
- `pyproject.toml` - Project config with all Phase 1 dependencies
- `src/localstock/__init__.py` - Package init with version
- `src/localstock/config.py` - Pydantic Settings loading from .env
- `src/localstock/db/database.py` - Async SQLAlchemy engine and session factory
- `src/localstock/db/models.py` - 5 ORM models: Stock, StockPrice, CorporateEvent, FinancialStatement, PipelineRun
- `src/localstock/crawlers/base.py` - Abstract BaseCrawler with error-tolerant fetch_batch
- `alembic.ini` - Alembic configuration pointing to alembic/ directory
- `alembic/env.py` - Async Alembic env reading DATABASE_URL_MIGRATION from Settings
- `alembic/script.py.mako` - Standard Alembic migration template
- `tests/conftest.py` - Shared pytest fixtures (OHLCV, company overview, corporate events, financial data)
- `.env.example` - Template with Supabase connection string and crawl settings
- `.gitignore` - Python project ignores including .env
- `README.md` - Project description and setup instructions

## Decisions Made
- Used BigInteger for StockPrice.volume column — Vietnamese stock volumes can exceed 2 billion (Integer max ~2.1B)
- Added pytest-timeout as dev dependency — plan specified `timeout=30` in pytest config but pytest-timeout wasn't in the dependency list

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing pytest-timeout dependency**
- **Found during:** Task 2 (test infrastructure verification)
- **Issue:** `pyproject.toml` specified `timeout = 30` in `[tool.pytest.ini_options]` but `pytest-timeout` package was not in dev dependencies, causing `pytest: error: unrecognized arguments: --timeout=30`
- **Fix:** Added `"pytest-timeout>=2.0,<3.0"` to `[project.optional-dependencies] dev` and re-ran `uv sync`
- **Files modified:** `pyproject.toml`, `uv.lock`
- **Verification:** `uv run pytest tests/ -x --timeout=30` exits 0
- **Committed in:** `6fb0355` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for test infrastructure to work. No scope creep.

## Issues Encountered
None — both tasks executed smoothly after the pytest-timeout fix.

## User Setup Required

**External services require manual configuration.** The plan references Supabase PostgreSQL setup:
- Copy `.env.example` to `.env`
- Create a Supabase project (supabase.com → New Project → region ap-southeast-1)
- Set `DATABASE_URL` from Supabase Dashboard → Settings → Database → Connection string (port 6543)
- Set `DATABASE_URL_MIGRATION` same as above but port 5432

## Next Phase Readiness
- Project scaffold complete — all subsequent plans can import from `localstock.*`
- ORM models ready for Alembic migration generation (Plan 01-02 will need Supabase credentials)
- BaseCrawler ready for concrete crawler implementations (Plan 01-02: stock listing, Plan 01-03: price crawler)
- Test fixtures ready for crawler and service tests

## Self-Check: PASSED

All 15 files verified as existing. Both task commits (f80ad95, 6fb0355) found in git log.

---
*Phase: 01-foundation-data-pipeline*
*Completed: 2026-04-15*
