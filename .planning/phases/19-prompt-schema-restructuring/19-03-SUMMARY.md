---
phase: 19-prompt-schema-restructuring
plan: 03
status: complete
started: 2026-04-28T10:38:00Z
completed: 2026-04-28T10:48:00Z
commits:
  - d877498
---

# Plan 19-03 Summary: Price Validation + Risk Normalization + Service Wiring

## What was built

Added post-generation validation for LLM-produced price levels, risk_rating normalization, and wired Phase 18 signal computation into the report generation pipeline.

## Changes

### apps/prometheus/src/localstock/reports/generator.py
- Added `from loguru import logger` import
- Added `RISK_RATING_MAP` constant (12 entries: EN, VI, cased variants)
- Added `_normalize_risk_rating(report)` — maps Vietnamese/cased variants to canonical lowercase
- Added `_validate_price_levels(report, current_close)` — rejects invalid ordering or ±30% range

### apps/prometheus/src/localstock/services/report_service.py
- Added imports: `compute_sector_momentum`, `TechnicalAnalyzer`, `_validate_price_levels`, `_normalize_risk_rating`, `SectorSnapshotRepository`
- Added `sector_repo` to constructor
- Wired signal computation (candlestick, volume divergence, sector momentum) into both `run_full()` and `generate_for_symbol()`
- Added `signals_data=signals_data` to builder calls
- Added post-generation validation + normalization after LLM report generation

### apps/prometheus/tests/test_reports/test_generator.py
- Added `TestValidatePriceLevels` (7 tests): valid, invalid ordering, ±30% range, non-price preserved, all-None, partial
- Added `TestNormalizeRiskRating` (7 tests): EN passthrough, Vietnamese variants, casing, unknown→None, None→None

### apps/prometheus/tests/test_services/test_report_service.py
- Added `get_prices` and `sector_repo.get_latest` mocks to existing test fixtures

## Deviation

- Used `self.price_repo.get_prices(symbol)[-60:]` instead of plan's `get_history(symbol, limit=60)` since `PriceRepository` doesn't have a `get_history` method
- Used `self.sector_repo.get_latest(group_code)` from `SectorSnapshotRepository` instead of plan's `industry_repo.get_latest_by_group()` since that method doesn't exist
- Moved signal computation block after `stock_info` gathering to avoid referencing undefined variables

## Verification

- ✓ 78 affected tests pass (52 generator + 7 report_service + 5 client + 14 others)
- ✓ Price validation nulls only price fields, preserves non-price fields
- ✓ Risk normalization handles all Vietnamese/English/cased variants
- ✓ Both run_full() and generate_for_symbol() have identical signal+validation wiring
