---
phase: 17-market-overview-metrics
plan: "01"
subsystem: backend
tags: [fastapi, sqlalchemy, pydantic, market-api, tdd-green]

# Dependency graph
requires:
  - "17-00: test_market_route.py RED state stubs"
provides:
  - "GET /api/market/summary FastAPI endpoint returning MarketSummaryResponse"
  - "PriceRepository.get_market_aggregate() advances/declines/volume aggregation"
  - "market_router registered in create_app()"
affects:
  - "17-02-frontend-market-cards (consumes GET /api/market/summary)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLAlchemy self-join via StockPrice.__table__.alias() for prev/today price comparison"
    - "MAX(date)-derived trading day — never date.today()"
    - "Structured nulls on empty DB — endpoint never raises 500"

key-files:
  created:
    - apps/prometheus/src/localstock/api/routes/market.py
  modified:
    - apps/prometheus/src/localstock/db/repositories/price_repo.py
    - apps/prometheus/src/localstock/api/app.py

key-decisions:
  - "VNINDEX excluded from advances/declines by symbol != 'VNINDEX' (not by exchange field) — safe regardless of how VNINDEX is seeded"
  - "Self-join uses StockPrice.__table__.alias() — SQLAlchemy Core table alias approach for cross-row comparison within same table"
  - "total_volume returns None (not 0) when aggregate has no data — frontend can distinguish 'no data' from 'zero volume'"

# Metrics
duration: 15min
completed: 2026-04-25
---

# Phase 17 Plan 01: Backend Market API Summary

**GET /api/market/summary FastAPI endpoint with advances/declines/volume aggregation — turns Wave 0 RED tests to GREEN (8/8 pass)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-25
- **Completed:** 2026-04-25
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Added `PriceRepository.get_market_aggregate()` method that computes advances/declines/flat/volume for the most recent trading day using a SQLAlchemy self-join on `stock_prices`
- Created `apps/prometheus/src/localstock/api/routes/market.py` with `VnindexData`, `MarketSummaryResponse` Pydantic models and `GET /api/market/summary` endpoint
- Registered `market_router` in `create_app()` in `app.py`
- All 8 `test_market_route.py` tests pass (GREEN state achieved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_market_aggregate() to PriceRepository** — `b3a9537`
2. **Task 2: Create market.py router and register in app.py** — `6c3d113`

## Files Created/Modified

- `apps/prometheus/src/localstock/api/routes/market.py` — New router with VnindexData, MarketSummaryResponse Pydantic models and GET /api/market/summary endpoint
- `apps/prometheus/src/localstock/db/repositories/price_repo.py` — Added `get_market_aggregate()` method, added `TechnicalIndicator` import, updated `case` import
- `apps/prometheus/src/localstock/api/app.py` — Added `market_router` import and `include_router(market_router, tags=["market"])` call

## Decisions Made

- VNINDEX excluded from advances/declines by `symbol != 'VNINDEX'` comparison (not by `exchange='INDEX'` field) — this is safe regardless of what `exchange` value is set on the VNINDEX stocks record and matches the plan's explicit guidance
- SQLAlchemy self-join via `StockPrice.__table__.alias()` for comparing today's vs previous day's close prices — this is the correct Core-level table alias pattern for cross-row comparison on the same table
- `total_volume` returns `None` when aggregate produces 0 (no data) rather than `0` — allows frontend to distinguish "no data" from "zero volume trading day"
- Removed unused `Stock` import from `price_repo.py` (plan included it but `get_market_aggregate()` doesn't use the `Stock` model directly)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Cleanup] Removed unused `Stock` import from price_repo.py**
- **Found during:** Task 1 implementation
- **Issue:** The plan specified importing `Stock` along with `StockPrice` and `TechnicalIndicator`, but the `get_market_aggregate()` implementation excludes VNINDEX by `StockPrice.symbol != "VNINDEX"` — not by joining against the `Stock` table. The `Stock` model is not referenced anywhere in the method.
- **Fix:** Removed `Stock` from the import line to keep the import clean.
- **Files modified:** `apps/prometheus/src/localstock/db/repositories/price_repo.py`
- **Commit:** `b3a9537`

**2. [Rule 3 - Fix] Moved SQLAlchemy imports to module level in market.py**
- **Found during:** Task 2 implementation
- **Issue:** The plan placed `from sqlalchemy import select` and `from localstock.db.models import StockPrice` inside the `if latest_vnindex is not None:` block. While valid Python, inline imports inside conditional branches are a style anti-pattern and ruff may flag them.
- **Fix:** Moved both imports to the module-level import block at the top of `market.py`.
- **Files modified:** `apps/prometheus/src/localstock/api/routes/market.py`
- **Commit:** `6c3d113`

## Known Stubs

None — all data paths are wired to real repository methods. The endpoint correctly returns structured nulls when DB has no price data.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model. The endpoint is a read-only aggregate query with no user-supplied parameters (no injection surface beyond what SQLAlchemy ORM parameterization already handles).

## Self-Check: PASSED

- `apps/prometheus/src/localstock/api/routes/market.py` — FOUND
- `apps/prometheus/src/localstock/db/repositories/price_repo.py` — FOUND (modified)
- `apps/prometheus/src/localstock/api/app.py` — FOUND (modified)
- Task 1 commit `b3a9537` — FOUND
- Task 2 commit `6c3d113` — FOUND
- 8/8 tests GREEN
