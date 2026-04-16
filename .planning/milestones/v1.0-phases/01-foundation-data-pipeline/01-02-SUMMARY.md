---
phase: 01-foundation-data-pipeline
plan: 02
subsystem: database, crawlers
tags: [vnstock, sqlalchemy, postgresql, upsert, ohlcv, async, price-crawler]

requires:
  - phase: 01-01
    provides: "SQLAlchemy models (Stock, StockPrice), async database engine, BaseCrawler, test fixtures"
provides:
  - "StockRepository with upsert for stock listings and HOSE symbol queries"
  - "PriceRepository with OHLCV upsert (ON CONFLICT) and latest-date query for incremental crawl"
  - "PriceCrawler extending BaseCrawler — fetches OHLCV via vnstock v3.5.1 Quote.history()"
affects: [01-03, 01-04, 02-technical-analysis]

tech-stack:
  added: [vnstock (runtime usage in crawler)]
  patterns: [PostgreSQL INSERT ON CONFLICT DO UPDATE for idempotent upserts, run_in_executor for sync-to-async bridge, repository pattern for DB access]

key-files:
  created:
    - src/localstock/crawlers/price_crawler.py
    - src/localstock/db/repositories/stock_repo.py
    - src/localstock/db/repositories/price_repo.py
    - tests/test_crawlers/test_price_crawler.py
    - tests/test_db/test_price_repo.py
    - tests/test_db/test_stock_repo.py
  modified: []

key-decisions:
  - "datetime.now(UTC) instead of deprecated datetime.utcnow() for timezone-aware timestamps"
  - "Validate DataFrame columns before upsert with clear error messages (T-01-04 threat mitigation)"
  - "Log anomalies (negative prices, zero volume) as warnings but allow storage — don't reject data"

patterns-established:
  - "Repository pattern: class with AsyncSession dependency, pg_insert().on_conflict_do_update() for idempotent writes"
  - "Sync-to-async bridge: asyncio.get_event_loop().run_in_executor(None, sync_fn) for vnstock calls"
  - "Column mapping: vnstock DataFrame column names → ORM model column names (organ_name→name, time→date)"

requirements-completed: [DATA-01, DATA-02]

duration: 3min
completed: 2026-04-15
---

# Phase 01 Plan 02: Price Crawler & Repositories Summary

**OHLCV price crawler via vnstock v3.5.1 with PostgreSQL upsert repositories for idempotent stock listing and price data storage**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-15T03:26:15Z
- **Completed:** 2026-04-15T03:29:45Z
- **Tasks:** 2
- **Files created:** 6

## Accomplishments

- StockRepository with PostgreSQL INSERT ON CONFLICT upsert for stock listings, HOSE symbol filtering, and vnstock listing fetch
- PriceRepository with OHLCV upsert on (symbol, date) constraint, latest-date query for incremental crawling, and DataFrame validation
- PriceCrawler extending BaseCrawler — wraps synchronous vnstock in run_in_executor, 2-year backfill default, configurable VCI/KBS source
- 16 unit tests all passing with mocked async sessions and mocked vnstock (zero live API calls)

## Task Commits

Each task was committed atomically:

1. **Task 1: Stock & price repositories** — TDD
   - `75f3388` (test: failing tests for stock and price repositories)
   - `9005a45` (feat: implement stock and price repositories with upsert semantics)

2. **Task 2: Price crawler** — TDD
   - `a08a36b` (test: failing tests for price crawler)
   - `981fc80` (feat: implement price crawler with vnstock v3.5.1)

## Files Created/Modified

- `src/localstock/db/repositories/stock_repo.py` — StockRepository: upsert_stocks, get_all_hose_symbols, fetch_and_store_listings
- `src/localstock/db/repositories/price_repo.py` — PriceRepository: upsert_prices (ON CONFLICT), get_latest_date, get_prices
- `src/localstock/crawlers/price_crawler.py` — PriceCrawler: async OHLCV fetch via vnstock, 2yr backfill, VCI/KBS source config
- `tests/test_db/test_stock_repo.py` — 3 tests for StockRepository upsert and query
- `tests/test_db/test_price_repo.py` — 6 tests for PriceRepository upsert, validation, latest-date
- `tests/test_crawlers/test_price_crawler.py` — 7 tests for PriceCrawler with mocked vnstock

## Decisions Made

- Used `datetime.now(UTC)` instead of deprecated `datetime.utcnow()` — Python 3.12+ best practice
- DataFrame column validation before upsert with descriptive ValueError (T-01-04 threat mitigation)
- Anomaly logging (negative prices, zero volume) as warnings without rejecting data — real market data can have zero-volume days

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deprecated datetime.utcnow() usage**
- **Found during:** Task 1 (StockRepository implementation)
- **Issue:** `datetime.utcnow()` is deprecated in Python 3.12+ and scheduled for removal
- **Fix:** Replaced with `datetime.now(UTC)` using `from datetime import UTC`
- **Files modified:** `src/localstock/db/repositories/stock_repo.py`
- **Verification:** All tests pass with zero deprecation warnings
- **Committed in:** `9005a45` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor fix for Python 3.12 compatibility. No scope creep.

## Issues Encountered

None — plan executed cleanly.

## User Setup Required

None - no external service configuration required for development. vnstock Community tier registration (noted in plan's user_setup) increases rate limits for production crawling but is not required for tests.

## Next Phase Readiness

- Price crawler ready for integration with pipeline orchestrator (Plan 01-03)
- Repositories ready for financial statement and corporate event data (Plan 01-04)
- Incremental crawl support via get_latest_date() ready for daily scheduler

## Self-Check: PASSED

- All 7 files exist
- All 4 commits verified in git history
- 16/16 tests passing

---
*Phase: 01-foundation-data-pipeline*
*Completed: 2026-04-15*
