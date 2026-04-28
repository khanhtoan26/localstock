---
status: complete
phase: 19-prompt-schema-restructuring
source: 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md
started: 2026-04-28T10:55:00Z
updated: 2026-04-28T10:59:00Z
---

## Current Test

[testing complete]

## Tests

### 1. StockReport 15-field schema
expected: StockReport model has exactly 15 properties and old 9-field JSON backward compatible
result: pass

### 2. num_ctx raised to 8192
expected: generate_report() uses num_ctx=8192, classify_sentiment() stays at 4096
result: pass

### 3. Signal formatters produce correct output
expected: _format_candlestick, _format_volume_divergence, _format_sector_momentum handle normal + edge cases (None→"N/A", empty→"không phát hiện")
result: pass

### 4. Prompt template has signal section
expected: REPORT_USER_TEMPLATE contains 🔔 TÍN HIỆU BỔ SUNG section with S/R, candlestick, volume, sector placeholders
result: pass

### 5. System prompt rules 9-10
expected: REPORT_SYSTEM_PROMPT contains rule 9 (numeric VND format) and rule 10 (risk_rating values)
result: pass

### 6. Price validation logic
expected: _validate_price_levels nulls entry_price/stop_loss/target_price when ordering is invalid or prices are ±30% from current close
result: pass

### 7. Risk normalization logic
expected: _normalize_risk_rating maps Vietnamese variants (Cao, Trung bình, Thấp) and English variants to canonical lowercase
result: pass
note: Found bug — capitalized Vietnamese variants (Cao, Trung bình, Thấp) were missing from RISK_RATING_MAP. Fixed in b32b7c9.

### 8. Service wiring — signals flow to builder
expected: Both run_full() and generate_for_symbol() compute signals and pass signals_data to builder
result: pass

### 9. All Phase 19 tests pass
expected: All 59 tests in test_generator.py and test_report_service.py pass
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
