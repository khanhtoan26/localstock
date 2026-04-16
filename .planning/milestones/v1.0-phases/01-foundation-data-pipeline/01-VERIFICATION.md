---
phase: 01-foundation-data-pipeline
verified: 2026-04-15T04:00:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Run full pipeline against Supabase PostgreSQL"
    expected: "Pipeline completes, stock_prices table contains OHLCV rows for ~400 HOSE tickers with ≥2 years of history"
    why_human: "Requires live Supabase database connection and vnstock API access — cannot verify data flow end-to-end without external services"
  - test: "Generate Alembic migration and apply to Supabase"
    expected: "alembic revision --autogenerate creates migration with all 5 tables; alembic upgrade head applies without errors"
    why_human: "Requires live database connection to verify DDL generation and application"
  - test: "Verify vnstock rate limiting behavior under batch crawl"
    expected: "Crawling ~400 symbols completes within reasonable time (< 2 hours) with configured delays, no rate limit errors"
    why_human: "Depends on vnstock API server behavior and network conditions — cannot simulate in tests"
---

# Phase 01: Foundation & Data Pipeline — Verification Report

**Phase Goal:** Reliable data ingestion and storage for all HOSE stocks — the foundation everything else depends on
**Verified:** 2026-04-15T04:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent crawls daily OHLCV data for ~400 HOSE tickers and stores it in the database | ✓ VERIFIED | `PriceCrawler` uses `vnstock Quote.history()` (line 58 of price_crawler.py); `StockRepository.fetch_and_store_listings()` filters HOSE exchange (line 102 of stock_repo.py); `PriceRepository.upsert_prices()` with ON CONFLICT DO UPDATE (line 86 of price_repo.py); `Pipeline.run_full()` orchestrates listing→prices→financials→company→events→adjust (pipeline.py lines 50-129) |
| 2 | Database contains ≥2 years of historical price/volume data per ticker | ✓ VERIFIED | `PriceCrawler.get_backfill_start_date()` returns `date.today() - timedelta(days=730)` (line 76 of price_crawler.py); `Pipeline._crawl_prices()` uses 730-day backfill for new symbols (line 151 of pipeline.py); test `test_crawl_prices_backfill_when_no_data` passes |
| 3 | Quarterly and annual financial statements (income statement, balance sheet, cash flow) are stored for each company | ✓ VERIFIED | `FinanceCrawler.REPORT_TYPES = ["balance_sheet", "income_statement", "cash_flow"]` (line 32 of finance_crawler.py); fetches via `fin.balance_sheet()`, `fin.income_statement()`, `fin.cash_flow()` (lines 95-97); `FinancialRepository.upsert_statement()` stores with ON CONFLICT (line 57 of financial_repo.py); `FinancialStatement` model has `period` (Q1-Q4/annual), `report_type`, `data` JSON column |
| 4 | Company profiles (industry sector, market cap, shares outstanding) are queryable from the database | ✓ VERIFIED | `CompanyCrawler` fetches via `stock.company.overview()` (line 60 of company_crawler.py); `overview_to_stock_dict()` maps `icb_name3→industry_icb3`, `issue_share→issue_shares`, `charter_capital` (lines 71-114); `Stock` model has `industry_icb3`, `industry_icb4`, `issue_shares`, `charter_capital` columns |
| 5 | Historical price data is correctly adjusted for corporate actions (stock splits, stock dividends) — no false signals from unadjusted prices | ✓ VERIFIED | `adjust_prices_for_event()` divides OHLC by ratio before ex_date, multiplies volume by ratio (lines 40-42 of price_adjuster.py); `Pipeline._apply_price_adjustments()` processes unprocessed events filtered to `{"split", "stock_dividend"}` types (lines 171-233 of pipeline.py); 12 dedicated price adjuster tests all pass including `test_adjust_for_2_to_1_split`, `test_adjust_for_10pct_stock_dividend`, `test_adjust_all_ohlc_columns` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Project config with Phase 1 deps | ✓ VERIFIED | 919 bytes, contains vnstock==3.5.1, sqlalchemy, asyncpg, alembic, fastapi, pytest |
| `src/localstock/config.py` | Pydantic Settings from .env | ✓ VERIFIED | `class Settings(BaseSettings)` with `database_url`, `vnstock_source`, `crawl_delay_seconds`; `@lru_cache get_settings()` |
| `src/localstock/db/models.py` | 5 ORM models | ✓ VERIFIED | Stock, StockPrice (BigInteger volume), CorporateEvent, FinancialStatement (JSON data), PipelineRun — all with constraints |
| `src/localstock/db/database.py` | Async engine + session factory | ✓ VERIFIED | `create_async_engine`, `async_sessionmaker`, `get_session()` async generator |
| `src/localstock/crawlers/base.py` | Abstract BaseCrawler | ✓ VERIFIED | ABC with `fetch()` + `fetch_batch()` error-tolerant loop (skips failed, logs, continues) |
| `src/localstock/crawlers/price_crawler.py` | OHLCV crawler via vnstock | ✓ VERIFIED | `class PriceCrawler(BaseCrawler)`, `quote.history()`, `run_in_executor`, 2yr backfill |
| `src/localstock/crawlers/finance_crawler.py` | Financial statement crawler | ✓ VERIFIED | KBS-first + VCI fallback, 3 report types, `normalize_unit()` to billion_vnd |
| `src/localstock/crawlers/company_crawler.py` | Company profile crawler | ✓ VERIFIED | VCI source, `overview_to_stock_dict()` mapping, None/NaN handling |
| `src/localstock/crawlers/event_crawler.py` | Corporate event crawler | ✓ VERIFIED | `Company.events()`, event type mapping, returns empty DataFrame (not error) for no events |
| `src/localstock/db/repositories/stock_repo.py` | Stock listing CRUD | ✓ VERIFIED | `pg_insert().on_conflict_do_update()`, `get_all_hose_symbols()`, `fetch_and_store_listings()` |
| `src/localstock/db/repositories/price_repo.py` | Price data CRUD | ✓ VERIFIED | OHLCV upsert on `uq_stock_price`, `get_latest_date()` for incremental, column validation |
| `src/localstock/db/repositories/financial_repo.py` | Financial statement CRUD | ✓ VERIFIED | Upsert on `uq_financial_stmt`, `get_latest_period()` for incremental |
| `src/localstock/db/repositories/event_repo.py` | Corporate event CRUD | ✓ VERIFIED | Upsert on `uq_corporate_event`, `get_unprocessed_events()`, `mark_processed()` |
| `src/localstock/services/price_adjuster.py` | Backward price adjustment | ✓ VERIFIED | `adjust_prices_for_event()` backward adjustment + `compute_adjustment_factor()` |
| `src/localstock/services/pipeline.py` | Pipeline orchestrator | ✓ VERIFIED | Full sequence: listings→prices→financials→company→events→adjust, PipelineRun tracking |
| `src/localstock/api/app.py` | FastAPI application | ✓ VERIFIED | `create_app()` factory, `app = create_app()`, health router included |
| `src/localstock/api/routes/health.py` | Health endpoint | ✓ VERIFIED | `/health` returns stocks count, prices count, latest PipelineRun status |
| `alembic/env.py` | Async Alembic migration env | ✓ VERIFIED | Imports `Base.metadata`, `get_settings()`, async `run_migrations_online()` |
| `tests/conftest.py` | Shared test fixtures | ✓ VERIFIED | 4 fixtures: `sample_ohlcv_df`, `sample_company_overview`, `sample_corporate_events`, `sample_financial_data` |
| `tests/test_crawlers/test_price_crawler.py` | Price crawler tests | ✓ VERIFIED | 7 tests, all passing |
| `tests/test_db/test_price_repo.py` | Price repo tests | ✓ VERIFIED | 6 tests, all passing |
| `tests/test_db/test_stock_repo.py` | Stock repo tests | ✓ VERIFIED | 3 tests, all passing |
| `tests/test_crawlers/test_finance_crawler.py` | Finance crawler tests | ✓ VERIFIED | 12 tests (6 normalization + 4 crawling + 2 misc), all passing |
| `tests/test_crawlers/test_company_crawler.py` | Company crawler tests | ✓ VERIFIED | 8 tests, all passing |
| `tests/test_services/test_price_adjuster.py` | Price adjuster tests | ✓ VERIFIED | 12 tests (7 adjuster + 5 event parsing), all passing |
| `tests/test_services/test_pipeline.py` | Pipeline tests | ✓ VERIFIED | 5 tests, all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config.py` | `.env` | `pydantic-settings BaseSettings` | ✓ WIRED | `class Settings(BaseSettings)` with `env_file: ".env"` |
| `database.py` | `config.py` | `get_settings().database_url` | ✓ WIRED | Import at line 11, used at line 16 |
| `alembic/env.py` | `models.py` | `Base.metadata` import | ✓ WIRED | `target_metadata = Base.metadata` at line 21 |
| `price_crawler.py` | `vnstock` | `Quote.history()` | ✓ WIRED | `stock.quote.history(start=start, end=end, interval="1D")` at line 58 |
| `price_repo.py` | `models.py` | `StockPrice` import | ✓ WIRED | `from localstock.db.models import StockPrice` at line 11 |
| `stock_repo.py` | `vnstock` | `Listing.all_symbols()` | ✓ WIRED | `listing.all_symbols()` at line 99, HOSE filter at line 102 |
| `finance_crawler.py` | `vnstock` | `Finance.balance_sheet/income_statement/cash_flow` | ✓ WIRED | Lines 95-97 call all 3 report methods |
| `company_crawler.py` | `vnstock` | `Company.overview()` | ✓ WIRED | `stock.company.overview()` at line 60 |
| `financial_repo.py` | `models.py` | `FinancialStatement` import | ✓ WIRED | `from localstock.db.models import FinancialStatement` at line 10 |
| `pipeline.py` | `crawlers/*` | All 4 crawlers imported + instantiated | ✓ WIRED | Lines 20-23 import, lines 45-48 instantiate, lines 68-104 run |
| `pipeline.py` | `price_adjuster.py` | `adjust_prices_for_event` | ✓ WIRED | Import at line 29, called at line 207 |
| `health.py` | `models.py` | `PipelineRun` query | ✓ WIRED | `select(PipelineRun)` at line 27, returns status/counts |
| `app.py` | `health.py` | `router` include | ✓ WIRED | `app.include_router(health_router)` at line 19 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `price_crawler.py` | `df` (OHLCV) | `vnstock Quote.history()` via `run_in_executor` | Yes — calls live vnstock API | ✓ FLOWING |
| `stock_repo.py` | `all_symbols_df` | `vnstock Listing.all_symbols()` | Yes — calls live vnstock API | ✓ FLOWING |
| `finance_crawler.py` | `results` (3 report types) | `vnstock Finance.balance_sheet/income_statement/cash_flow` | Yes — calls live vnstock API | ✓ FLOWING |
| `company_crawler.py` | `df` (overview) | `vnstock Company.overview()` | Yes — calls live vnstock API | ✓ FLOWING |
| `event_crawler.py` | `df` (events) | `vnstock Company.events()` | Yes — calls live vnstock API | ✓ FLOWING |
| `health.py` | `stock_count`, `price_count`, `run` | DB queries (`select count`, `select PipelineRun`) | Yes — real DB queries | ✓ FLOWING |
| `pipeline.py` | orchestration | Chains all crawlers → repos → adjustments | Yes — wires real crawlers to real repos | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All modules importable | `uv run python -c "from localstock.services.pipeline import Pipeline"` (and 14 other imports) | All 15 imports succeed | ✓ PASS |
| Test suite passes | `uv run pytest tests/ -x --timeout=30` | 53 passed in 1.00s | ✓ PASS |
| Test collection complete | `uv run pytest --collect-only` | 53 tests collected | ✓ PASS |
| FastAPI routes registered | `uv run python -c "from localstock.api.app import app; print([r.path for r in app.routes])"` | `['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/health']` | ✓ PASS |
| 2yr backfill date correct | `uv run python -c "from localstock.crawlers.price_crawler import PriceCrawler; p=PriceCrawler(); print(p.get_backfill_start_date())"` | Returns date ~730 days ago | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATA-01 | 01-01, 01-02 | Agent crawl OHLCV daily for ~400 HOSE tickers | ✓ SATISFIED | PriceCrawler + StockRepository.fetch_and_store_listings(HOSE filter) + PriceRepository.upsert_prices |
| DATA-02 | 01-01, 01-02 | Store ≥2 years historical data | ✓ SATISFIED | PriceCrawler.get_backfill_start_date() returns 730 days ago; Pipeline uses this for new symbols |
| DATA-03 | 01-03 | Financial statements (quarterly/annual, 3 report types) | ✓ SATISFIED | FinanceCrawler with 3 report types + FinancialRepository upsert + FinancialStatement model |
| DATA-04 | 01-03 | Company info (industry, market cap, shares outstanding) | ✓ SATISFIED | CompanyCrawler + Stock model with industry_icb3/icb4, issue_shares, charter_capital |
| DATA-05 | 01-04 | Price adjustment for corporate actions | ✓ SATISFIED | EventCrawler + PriceAdjuster backward adjustment + Pipeline._apply_price_adjustments |

No orphaned requirements — all 5 DATA requirements mapped to Phase 1 in REQUIREMENTS.md traceability table are accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO/FIXME/PLACEHOLDER comments, no stub implementations, no empty returns to user-facing functions, no hardcoded empty data. Zero anti-patterns detected across all 17 source files.

### Human Verification Required

### 1. End-to-End Pipeline Run Against Live Database

**Test:** Configure `.env` with Supabase credentials, run `alembic upgrade head`, then execute `Pipeline.run_full("backfill")` via a script
**Expected:** Pipeline completes; `stocks` table has ~400 HOSE rows; `stock_prices` has OHLCV rows spanning ≥2 years per ticker; `financial_statements` has balance sheet, income statement, cash flow entries; `corporate_events` has events with processed flags
**Why human:** Requires live Supabase PostgreSQL connection and vnstock API access — external services unavailable in test environment

### 2. Alembic Migration Generation and Application

**Test:** Run `alembic revision --autogenerate -m "init"` then `alembic upgrade head`
**Expected:** Migration script creates all 5 tables (stocks, stock_prices, corporate_events, financial_statements, pipeline_runs) with correct columns, constraints, and indexes
**Why human:** Requires live database connection to generate and apply DDL

### 3. vnstock Rate Limiting Under Batch Load

**Test:** Run full pipeline for all ~400 HOSE symbols with `crawl_delay_seconds=1.0`
**Expected:** Batch crawl completes without rate limit errors; total execution time reasonable (<2 hours)
**Why human:** Depends on vnstock API server behavior, network conditions, and Community tier rate limits

### Gaps Summary

No gaps found. All 5 roadmap success criteria are verified through code analysis, import validation, and 53 passing unit tests. The codebase implements:

- **Complete data pipeline:** stock listings, OHLCV prices, financial statements, company profiles, corporate events
- **Idempotent storage:** PostgreSQL INSERT ON CONFLICT DO UPDATE for all repositories
- **Error-tolerant crawling:** BaseCrawler.fetch_batch() skips failed symbols and continues (D-02)
- **Backward price adjustment:** Splits and stock dividends correctly adjust historical OHLC/volume
- **Pipeline orchestration:** Full sequence with PipelineRun tracking
- **API foundation:** FastAPI with /health endpoint

Automated verification is complete. Three items require human verification involving external services (Supabase DB, vnstock API).

---

_Verified: 2026-04-15T04:00:00Z_
_Verifier: the agent (gsd-verifier)_
