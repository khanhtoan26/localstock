---
phase: 01-foundation-data-pipeline
plan: 03
subsystem: crawlers/financial
tags: [vnstock, financial-statements, company-profiles, crawlers, repository, tdd]
dependency_graph:
  requires:
    - 01-01 (SQLAlchemy models: FinancialStatement, Stock)
    - 01-01 (BaseCrawler abstract class)
  provides:
    - FinanceCrawler for balance_sheet, income_statement, cash_flow
    - CompanyCrawler for company overview (ICB, shares, capital)
    - FinancialRepository for financial_statements upsert
  affects:
    - Phase 2 fundamental analysis (P/E, ROE, D/E ratios require financial data)
    - Phase 2 industry comparison (ICB classification from company profiles)
tech_stack:
  added: []
  patterns:
    - KBS-first source fallback for financial data stability
    - Unit normalization at ingestion (billion_vnd) to prevent downstream errors
    - overview_to_stock_dict mapping pattern for vnstock → model conversion
key_files:
  created:
    - src/localstock/crawlers/finance_crawler.py
    - src/localstock/crawlers/company_crawler.py
    - src/localstock/db/repositories/financial_repo.py
    - tests/test_crawlers/test_finance_crawler.py
    - tests/test_crawlers/test_company_crawler.py
  modified: []
decisions:
  - KBS source first for financials (more stable per research issue #218), VCI as fallback
  - VCI source for company profiles (richer data via GraphQL endpoint)
  - Unit normalization to billion_vnd at ingestion time (prevents Pitfall 4)
metrics:
  duration: 3min
  completed: 2026-04-15T03:36:03Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 20
  test_pass: 20
---

# Phase 01 Plan 03: Financial & Company Crawlers Summary

**One-liner:** KBS-first finance crawler (balance sheet + income statement + cash flow) and VCI company profile crawler with billion_vnd normalization and upsert repository.

## What Was Built

### Task 1: Financial Statement Crawler & Repository

**FinanceCrawler** (`src/localstock/crawlers/finance_crawler.py`):
- Extends `BaseCrawler` to fetch all 3 report types (balance_sheet, income_statement, cash_flow) via vnstock Finance API
- Source fallback: KBS first (more stable per research issue #218), then VCI
- `normalize_unit()` static method converts dong/million_vnd/billion_vnd to billion_vnd at ingestion time (prevents Pitfall 4 unit mismatch)
- Synchronous vnstock calls wrapped in `run_in_executor` for async compatibility

**FinancialRepository** (`src/localstock/db/repositories/financial_repo.py`):
- `upsert_statement()` — single financial statement upsert with `ON CONFLICT DO UPDATE` on `uq_financial_stmt` constraint
- `upsert_batch()` — batch upsert for multiple statements per symbol
- `get_latest_period()` — returns most recent (year, period) for incremental crawl support
- Uses `datetime.now(UTC)` for timezone-aware timestamps (Python 3.12+ convention)

**Tests** (12 tests):
- 6 unit normalization tests covering all unit aliases
- 4 async crawling tests (KBS-first, VCI fallback, all-fail error, quarterly/annual)
- 1 repo import test
- 1 fetch returns all report types test

### Task 2: Company Profile Crawler

**CompanyCrawler** (`src/localstock/crawlers/company_crawler.py`):
- Extends `BaseCrawler` to fetch company overview data via vnstock `Company.overview()`
- Uses VCI source (richer data with ICB classification, shareholders, events)
- `overview_to_stock_dict()` maps vnstock columns to Stock model: icb_name3 → industry_icb3, issue_share → issue_shares, etc.
- Handles None/NaN values and short_name → company_name fallback gracefully
- Inherits error-tolerant batch processing from BaseCrawler (D-02)

**Tests** (8 tests):
- Fetch overview, VCI source verification, empty/None error handling
- overview_to_stock_dict with full data, short_name fallback, None values
- Batch crawling skip-on-failure

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| KBS source first for financials | More stable for financial data per research (issue #218) |
| VCI source for company profiles | Richer company data (GraphQL endpoint with ICB classification) |
| billion_vnd normalization at ingestion | Prevents Pitfall 4 — downstream analysis always works with consistent units |
| datetime.now(UTC) over utcnow() | Python 3.12+ convention for timezone-aware timestamps (consistent with Plan 01-02) |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | `a3c0fee` | Failing tests for finance crawler and financial repository |
| 1 (GREEN) | `e0e7460` | Implement finance crawler and financial repository |
| 2 (RED) | `14f90df` | Failing tests for company profile crawler |
| 2 (GREEN) | `74c69a1` | Implement company profile crawler with VCI source |

## Test Results

```
36 passed in 0.92s (full suite)
20 new tests added by this plan
```

## Self-Check: PASSED

All 5 created files verified on disk. All 4 commit hashes verified in git log.
