---
status: complete
phase: 06-web-dashboard
source: [06-VERIFICATION.md]
started: 2025-07-19T00:00:00Z
updated: 2025-07-19T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Dark theme visual — CSS rendering needs browser check

expected: Background #020817 applied globally, all text readable on dark theme
result: pass

### 2. Table sorting — Client-side sorting interactive test

expected: Click column headers on Rankings page → data sorts correctly by score/grade/volume
result: pass

### 3. Candlestick charts — Canvas rendering by lightweight-charts

expected: Stock detail page shows candlestick chart with volume, SMA/EMA/BB overlays visible
result: pass

### 4. Timeframe selector — Data refresh via API calls

expected: Clicking 1T/3T/6T/1N/2N buttons reloads chart with correct date range
result: pass

### 5. Macro cards — End-to-end data display with backend data

expected: Market page shows macro indicator cards with data from /api/macro/latest
result: skipped
reason: Chưa có macro data trong DB (chưa chạy macro crawler)

## Summary

total: 5
passed: 4
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps
