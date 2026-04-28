---
phase: 19-prompt-schema-restructuring
plan: 02
status: complete
started: 2026-04-28T10:30:00Z
completed: 2026-04-28T10:38:00Z
commits:
  - 501d99d
---

# Plan 19-02 Summary: Prompt Template Restructuring + Signal Formatters

## What was built

Added signal formatting functions, extended ReportDataBuilder with 10 new template keys, and restructured prompts with signal injection section.

## Changes

### apps/prometheus/src/localstock/reports/generator.py
- Added `_format_candlestick()` — formats candlestick pattern dict to comma-separated names
- Added `_format_volume_divergence()` — formats MFI divergence to "bullish (MFI=72.3)"
- Added `_format_sector_momentum()` — formats sector flow to "mild_inflow (+0.5, nhóm BKS)"
- Extended `ReportDataBuilder.build()` with `signals_data` parameter (default None)
- Added 10 new keys: 7 S/R anchors + 3 Phase 18 signals

### apps/prometheus/src/localstock/ai/prompts.py
- Added system rules 9-10: numeric VND format, risk_rating canonical values
- Added `🔔 TÍN HIỆU BỔ SUNG` section with S/R, candlestick, volume, sector placeholders

### apps/prometheus/tests/test_reports/test_generator.py
- Added `TestFormatSignals` class (11 tests)
- Added builder backward compat test (no signals_data → N/A)
- Updated `_make_sample_data()` with 10 new keys
- Updated char limit 3000 → 4000
- Added `🔔` assertion to section markers test

## Verification

- ✓ All 38 tests pass
- ✓ Formatters handle None → "N/A", empty patterns → "không phát hiện"
- ✓ Builder backward compatible (signals_data optional)

## Deviations

None.
