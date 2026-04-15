---
phase: 01-foundation-data-pipeline
plan: 04
subsystem: data-pipeline
tags: [vnstock, corporate-events, price-adjustment, fastapi, pipeline-orchestrator]

# Dependency graph
requires:
  - phase: 01-02
    provides: "PriceCrawler, StockRepository, PriceRepository"
  - phase: 01-03
    provides: "FinanceCrawler, CompanyCrawler, FinancialRepository"
provides:
  - "EventCrawler for corporate event fetching"
  - "EventRepository with upsert and processed tracking"
  - "PriceAdjuster with backward adjustment for splits and dividends"
  - "Pipeline orchestrator for full crawl sequence"
  - "FastAPI app with /health endpoint"
affects: [02-technical-analysis, 05-automation-scheduling]

# Tech tracking
tech-stack:
  added: [fastapi]
  patterns: [backward-price-adjustment, pipeline-orchestrator, event-type-mapping]

key-files:
  created:
    - src/localstock/crawlers/event_crawler.py
    - src/localstock/db/repositories/event_repo.py
    - src/localstock/services/price_adjuster.py
    - src/localstock/services/pipeline.py
    - src/localstock/api/app.py
    - src/localstock/api/routes/__init__.py
    - src/localstock/api/routes/health.py
    - tests/test_services/test_price_adjuster.py
    - tests/test_services/test_pipeline.py
  modified: []

key-decisions:
  - "Backward price adjustment: divide prices by ratio before ex_date, multiply volumes by ratio"
  - "EventCrawler returns empty DataFrame (not error) when no events — most stocks have few events"
  - "Only split and stock_dividend event types trigger price adjustment; cash_dividend and others are marked processed without adjustment"
  - "Pipeline uses datetime.now(UTC) consistently over deprecated utcnow()"

patterns-established:
  - "Backward adjustment: price_adj = price / ratio for all OHLC columns before ex_date"
  - "Pipeline orchestrator: listings → prices → financials → company → events → adjust"
  - "FastAPI app factory: create_app() returns configured FastAPI instance"

requirements-completed: [DATA-05]

# Metrics
duration: 4min
completed: 2026-04-15
---

# Phase 01 Plan 04: Events, Price Adjustment & Pipeline Summary

**Corporate event crawler, backward price adjustment for splits/dividends (DATA-05), pipeline orchestrator wiring all crawlers, and FastAPI health endpoint**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-15T03:39:06Z
- **Completed:** 2026-04-15T03:43:26Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- EventCrawler fetches corporate events via vnstock Company.events() with event type mapping (split, stock_dividend, cash_dividend, rights_issue, bonus_share)
- Price adjuster applies backward adjustment for splits and stock dividends — prices divided by ratio, volumes multiplied by ratio before ex_date (DATA-05)
- Pipeline orchestrator runs full sequence: listings → prices → financials → company → events → price adjustment
- FastAPI app with /health endpoint returning pipeline status and data counts
- Full test suite: 53 tests pass (12 price adjuster + 5 pipeline + existing tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Event crawler, event repository, and price adjustment service (TDD)**
   - `305548e` (test) — TDD RED: failing tests for price adjuster and event parsing
   - `de7442e` (feat) — TDD GREEN: implement event crawler, event repo, price adjuster
2. **Task 2: Pipeline orchestrator, health check, and integration tests** - `1624ae2` (feat)

## Files Created/Modified
- `src/localstock/crawlers/event_crawler.py` — Corporate event crawler using vnstock Company.events()
- `src/localstock/db/repositories/event_repo.py` — CRUD for corporate_events table with upsert and processed tracking
- `src/localstock/services/price_adjuster.py` — Backward price adjustment for corporate actions (DATA-05)
- `src/localstock/services/pipeline.py` — Pipeline orchestrator for full crawl sequence
- `src/localstock/api/app.py` — FastAPI application setup
- `src/localstock/api/routes/__init__.py` — API routes package
- `src/localstock/api/routes/health.py` — Health check endpoint
- `tests/test_services/test_price_adjuster.py` — 12 tests for price adjuster and event parsing
- `tests/test_services/test_pipeline.py` — 5 tests for pipeline orchestrator

## Decisions Made
- Backward price adjustment formula: `price_adj = price * (1/ratio)` for all OHLC columns before ex_date; `volume_adj = volume * ratio` — standard financial data adjustment methodology
- EventCrawler returns empty DataFrame (not ValueError) when no events — most stocks have few or no corporate events, and that's normal
- Only split and stock_dividend event types trigger price adjustment per T-01-11 (unknown types stored but not applied)
- Pipeline uses `datetime.now(UTC)` consistently over deprecated `utcnow()` per Python 3.12+ best practice

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pytest.approx with pandas Series comparison**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Plan's test assertions used `all(series == pytest.approx(scalar))` which doesn't work — pandas `==` with `pytest.approx` returns a Series of `False`
- **Fix:** Changed to `series.tolist() == pytest.approx([expected] * n)` which properly compares lists
- **Files modified:** tests/test_services/test_price_adjuster.py
- **Verification:** All 12 tests pass
- **Committed in:** 305548e (test commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in test assertions)
**Impact on plan:** Necessary for correct test assertions. No scope creep.

## Issues Encountered
None — all implementations followed plan specifications.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 01 (foundation-data-pipeline) is now complete with all 4 plans executed
- Data pipeline: stock listings, OHLCV prices, financial statements, company profiles, corporate events, and price adjustment all implemented
- Full test suite: 53 tests passing across all crawlers, repositories, and services
- FastAPI app configured and ready for uvicorn deployment
- Ready for Phase 02 (technical analysis) — all price data will be properly adjusted for corporate actions

## Self-Check: PASSED

All 10 files verified present. All 3 commits verified in git log.

---
*Phase: 01-foundation-data-pipeline*
*Completed: 2026-04-15*
