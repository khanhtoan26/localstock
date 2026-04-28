---
phase: 19-prompt-schema-restructuring
plan: 01
status: complete
started: 2026-04-28T10:25:00Z
completed: 2026-04-28T10:30:00Z
commits:
  - f06f3c2
---

# Plan 19-01 Summary: Extend StockReport Model + Raise num_ctx

## What was built

Extended `StockReport` Pydantic model from 9 to 15 fields and raised `generate_report()` context window to 8192 tokens.

## Changes

### apps/prometheus/src/localstock/ai/client.py
- Added `from typing import Optional` import
- Added 6 new Optional fields to `StockReport`: `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, `signal_conflicts`
- Updated docstring to reflect 15 fields
- Changed `num_ctx` from 4096 to 8192 in `generate_report()` options
- `classify_sentiment()` unchanged at `num_ctx: 4096`

### apps/prometheus/tests/test_reports/test_generator.py
- Updated `REQUIRED_FIELDS` list with 6 new fields
- Renamed `test_exactly_9_fields` → `test_exactly_15_fields`
- Updated num_ctx assertion from 4096 to 8192
- Added `TestStockReportBackwardCompat` class with 3 tests:
  - `test_old_json_without_new_fields` — 9-field JSON still deserializes
  - `test_new_json_with_all_fields` — 15-field JSON parses correctly
  - `test_partial_new_fields` — partial new fields work

## Verification

- ✓ `StockReport.model_json_schema()` has exactly 15 properties
- ✓ `generate_report()` uses `num_ctx: 8192`
- ✓ `classify_sentiment()` uses `num_ctx: 4096` (unchanged)
- ✓ Old 9-field JSON deserializes without error
- ✓ All 32 tests pass (0 failures)

## Deviations

None — plan executed exactly as specified.
