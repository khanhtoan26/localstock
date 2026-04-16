---
phase: 04-ai-reports-macro-t3
plan: 04
subsystem: integration
tags: [report-service, api-endpoints, macro-api, integration, phase4-complete]
dependency_graph:
  requires: [04-02, 04-03]
  provides: [ReportService, reports-api, macro-api, full-pipeline-integration]
  affects: [api-app, scoring-service]
tech_stack:
  added: []
  patterns: [session-based-orchestrator, asyncio-lock, pydantic-input-validation, recommendation-mapping]
key_files:
  created:
    - src/localstock/services/report_service.py
    - src/localstock/api/routes/reports.py
    - src/localstock/api/routes/macro.py
    - tests/test_services/test_report_service.py
  modified:
    - src/localstock/api/app.py
    - src/localstock/db/repositories/stock_repo.py
    - src/localstock/db/repositories/price_repo.py
decisions:
  - "RECOMMENDATION_MAP translates Vietnamese LLM output to DB enum (Mua→buy, Bán→sell, etc.)"
  - "ReportService follows session-based service pattern from ScoringService"
  - "Macro context fetched once per run_full() call (shared across all stocks)"
  - "MacroInput Pydantic model with regex-constrained indicator_type (T-04-09)"
  - "asyncio.Lock prevents concurrent report generation (T-04-10)"
  - "Added StockRepository.get_by_symbol() and PriceRepository.get_latest() for data access"
metrics:
  duration: 4min
  completed: "2026-04-16T04:21:42Z"
  tasks: 2
  files: 7
---

# Phase 04 Plan 04: Report Service & API Integration Summary

ReportService orchestrator wiring scores→macro→T+3→LLM→DB pipeline, report API (GET/POST) with concurrency lock, macro API with Pydantic-validated manual entry and VCB exchange rate fetch, all registered in FastAPI app (24 routes total).

## Tasks Completed

### Task 1: ReportService orchestrator (TDD)
- **Commit:** `ed05e93` (RED), `8868dc2` (GREEN)
- Created `ReportService` with session-based pattern matching ScoringService
- `run_full(top_n)`: health check → get top scores → get macro context once → per-stock data gathering (indicator, ratio, sentiment, stock info, price) → T+3 prediction → prompt building → LLM report generation → DB storage
- `RECOMMENDATION_MAP`: translates Vietnamese recommendations ("Mua mạnh"→"strong_buy", etc.)
- Per-stock error isolation via try/except — one failure doesn't stop pipeline
- Ollama health check gate prevents hanging when LLM unavailable
- `get_reports(limit)`: retrieves latest reports as flat dicts
- `get_report(symbol)`: retrieves full report with content_json + metadata
- Added `StockRepository.get_by_symbol()` for stock info lookup (Rule 3)
- Added `PriceRepository.get_latest()` for close price retrieval (Rule 3)
- 7 tests covering init, happy path, Ollama down, error isolation, get_reports, get_report, not found

### Task 2: API routes for reports and macro data
- **Commit:** `00400ee`
- Created `src/localstock/api/routes/reports.py`:
  - `GET /api/reports/top` — latest reports list with limit query param
  - `GET /api/reports/{symbol}` — specific stock report or 404
  - `POST /api/reports/run` — triggers generation with asyncio.Lock (T-04-10)
- Created `src/localstock/api/routes/macro.py`:
  - `GET /api/macro/latest` — current macro indicators
  - `POST /api/macro` — manual entry with MacroInput Pydantic validation (T-04-09)
  - `POST /api/macro/fetch-exchange-rate` — VCB exchange rate fetch + store
- Updated `src/localstock/api/app.py` with reports_router and macro_router
- 24 total routes registered in FastAPI app

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added StockRepository.get_by_symbol()**
- **Found during:** Task 1
- **Issue:** StockRepository lacked get_by_symbol() method needed by ReportService for stock info lookup
- **Fix:** Added simple select query method returning Stock | None
- **Files modified:** src/localstock/db/repositories/stock_repo.py
- **Commit:** 8868dc2

**2. [Rule 3 - Blocking] Added PriceRepository.get_latest()**
- **Found during:** Task 1
- **Issue:** PriceRepository lacked get_latest() method needed by ReportService for close price
- **Fix:** Added query method returning most recent StockPrice by date desc
- **Files modified:** src/localstock/db/repositories/price_repo.py
- **Commit:** 8868dc2

## Verification Results

- ✅ Report service tests pass: 7 tests in `tests/test_services/test_report_service.py` (0.54s)
- ✅ Full test suite green: 267 tests pass (1.65s)
- ✅ All routes importable: `from localstock.api.app import app`
- ✅ Routes verified: /api/reports/top, /api/reports/{symbol}, /api/reports/run, /api/macro/latest, /api/macro, /api/macro/fetch-exchange-rate
- ✅ 24 total routes registered in FastAPI app

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-04-09 | MacroInput Pydantic model with regex pattern constraining indicator_type to 4 valid values |
| T-04-10 | asyncio.Lock prevents concurrent report generation; top_n capped at 50 |

## Decisions Made

1. **RECOMMENDATION_MAP** — translates Vietnamese LLM output to DB-friendly enum values: "Mua mạnh"→"strong_buy", "Mua"→"buy", "Nắm giữ"→"hold", "Bán"→"sell", "Bán mạnh"→"strong_sell". Defaults to "hold" for unknown values.
2. **Macro context fetched once per run_full()** — macro conditions are market-wide, not per-stock, avoiding redundant DB queries.
3. **Session-based service pattern** — ReportService.__init__(session) creates all repo instances, following ScoringService convention.
4. **Trend computed from previous value on manual entry** — POST /api/macro compares new value with latest existing to determine rising/falling/stable trend.
5. **Report concurrency lock** — asyncio.Lock on POST /api/reports/run returns 409 if already running, prevents resource exhaustion.

## Self-Check: PASSED
