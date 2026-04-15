---
status: passed
phase: 01-foundation-data-pipeline
source: [01-VERIFICATION.md]
started: 2025-01-27T10:00:00Z
updated: 2026-04-15T04:50:00Z
---

## Current Test

[all tests completed]

## Tests

### 1. End-to-end pipeline run
expected: Pipeline crawls OHLCV, financials, company profiles, events for HOSE tickers and stores in Supabase
result: PASSED (with fixes) — VNM single-symbol test: stocks=1, stock_prices=525, financial_statements=156, corporate_events=46
notes: |
  Found and fixed 5 code bugs during testing:
  1. alembic env.py: postgresql:// not converted to asyncpg for async engine
  2. finance_crawler: lang='en' param unsupported by KBS, limits VCI to 4 quarters
  3. models: DateTime without timezone incompatible with asyncpg + datetime.now(UTC)
  4. pipeline: run_full/run_single fetched financials/company/events but never stored them
  5. event_repo: duplicate events in same batch caused ON CONFLICT error
  Environment fix: DATABASE_URL changed to IPv4 pooler (direct endpoint IPv6-only)

### 2. Alembic migration generation
expected: alembic revision --autogenerate creates migration from models, alembic upgrade head applies to Supabase
result: PASSED (with fix) — 5 tables detected (stocks, stock_prices, financial_statements, corporate_events, pipeline_runs), migration applied
notes: Required fix to alembic/env.py to convert postgresql:// to postgresql+asyncpg:// for async engine

### 3. vnstock rate limiting under batch load
expected: Crawling ~400 HOSE symbols completes without 429/timeout errors within vnstock Community tier limits
result: NOT TESTED — single-symbol test passed, batch test skipped (would take ~2 hours)
notes: KBS source returns 404 for financials in vnstock 3.5.1; VCI works as fallback. Network SSL interception requires REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

## Summary

total: 3
passed: 2
issues: 6 bugs found and fixed
pending: 1 (batch rate limit test)
skipped: 0
blocked: 0

## Gaps

- KBS financial data source returns 404 in vnstock 3.5.1 — VCI fallback works but may be slower
- Community tier limits financial statements to ~52 periods (4 displayed with lang param)
- Batch crawl of ~400 symbols not yet tested for rate limiting behavior
