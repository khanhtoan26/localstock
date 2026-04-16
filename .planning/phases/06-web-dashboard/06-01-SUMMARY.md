---
phase: 06-web-dashboard
plan: 01
subsystem: api
tags: [cors, prices, indicators, sectors, dashboard-api]
dependency_graph:
  requires: []
  provides:
    - "GET /api/prices/{symbol} — OHLCV time-series endpoint"
    - "GET /api/prices/{symbol}/indicators — technical indicator time-series endpoint"
    - "GET /api/sectors/latest — sector snapshots with Vietnamese names"
    - "CORSMiddleware configured for http://localhost:3000"
  affects:
    - src/localstock/api/app.py
tech_stack:
  added: []
  patterns:
    - "CORSMiddleware with restricted origins (not wildcard)"
    - "Path parameter regex validation for symbol injection prevention"
    - "Query parameter bounds (ge/le) for DoS prevention"
key_files:
  created:
    - src/localstock/api/routes/prices.py
    - src/localstock/api/routes/dashboard.py
    - tests/test_api_dashboard.py
  modified:
    - src/localstock/api/app.py
decisions:
  - "CORS restricted to http://localhost:3000 only (T-06-03 threat mitigation)"
  - "Symbol path params validated with ^[A-Z0-9]+$ regex (T-06-01/T-06-02)"
  - "Days query param constrained ge=30, le=730 (T-06-04 DoS prevention)"
  - "Sectors endpoint uses outerjoin with IndustryGroup for Vietnamese names"
metrics:
  duration: "2min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
  tests_added: 8
  tests_total_passing: 326
---

# Phase 06 Plan 01: Dashboard Backend API Endpoints Summary

**One-liner:** CORS middleware + 3 new API endpoints (OHLCV prices, indicator time-series, sector snapshots) for web dashboard with regex symbol validation and query param bounds.

## What Was Done

### Task 1: CORS middleware + new price/indicator/sector API endpoints
**Commit:** `1d8256c`

Created 2 new route files and modified app.py:

1. **`src/localstock/api/routes/prices.py`** — 2 endpoints:
   - `GET /api/prices/{symbol}?days=365` — OHLCV price history for candlestick charts. Returns `{symbol, count, prices: [{time, open, high, low, close, volume}]}`. Symbol validated with `^[A-Z0-9]+$` regex. Days constrained 30-730.
   - `GET /api/prices/{symbol}/indicators?days=365` — Technical indicator time-series for chart overlays. Returns `{symbol, count, indicators: [{time, sma_20, sma_50, sma_200, ema_12, ema_26, rsi_14, macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower}]}`.

2. **`src/localstock/api/routes/dashboard.py`** — 1 endpoint:
   - `GET /api/sectors/latest` — Latest sector snapshots with Vietnamese group names. Finds max date, joins with IndustryGroup for `group_name_vi`, returns `{date, count, sectors: [{group_code, group_name_vi, avg_score, stock_count, avg_score_change}]}`.

3. **`src/localstock/api/app.py`** — Added:
   - `CORSMiddleware` with `allow_origins=["http://localhost:3000"]` (restricted, not wildcard)
   - `prices_router` and `dashboard_router` registrations

### Task 2: Backend tests for new dashboard endpoints
**Commit:** `8d0cdf6`

Created `tests/test_api_dashboard.py` with 8 tests across 4 test classes:
- `TestCorsMiddleware` — verifies CORSMiddleware present in app.user_middleware
- `TestPricesRouter` — verifies route paths and endpoint function callability
- `TestDashboardRouter` — verifies sectors route and endpoint function
- `TestAppRouteRegistration` — verifies all 3 new routes registered in create_app()

All 8 tests pass. Full suite: 326 tests passing, no regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation | Implemented |
|-----------|------------|-------------|
| T-06-01 | Symbol regex `^[A-Z0-9]+$` on `/api/prices/{symbol}` | ✅ |
| T-06-02 | Same regex on `/api/prices/{symbol}/indicators` | ✅ |
| T-06-03 | CORS `allow_origins=["http://localhost:3000"]` (not `*`) | ✅ |
| T-06-04 | `days` param `Query(ge=30, le=730)` | ✅ |

## Verification Results

```
tests/test_api_dashboard.py — 8 passed in 1.42s
tests/ (full suite) — 326 passed in 2.23s
```

## Self-Check: PASSED

- [x] `src/localstock/api/routes/prices.py` exists
- [x] `src/localstock/api/routes/dashboard.py` exists
- [x] `tests/test_api_dashboard.py` exists
- [x] Commit `1d8256c` exists
- [x] Commit `8d0cdf6` exists
