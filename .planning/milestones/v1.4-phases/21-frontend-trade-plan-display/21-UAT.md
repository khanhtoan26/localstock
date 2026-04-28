---
status: complete
phase: 21-frontend-trade-plan-display
source: 21-01-SUMMARY.md, 21-02-SUMMARY.md, 21-VERIFICATION.md
started: 2026-04-28T06:35:00Z
updated: 2026-04-28T07:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Trade Plan card layout and VND formatting
expected: Open /stock/VNM — Trade Plan card with "Kế Hoạch Giao Dịch" title, entry zone/stop-loss/target in VND format, % variance from current close
result: issue
reported: "entry_price, stop_loss on the ui website is rounded and not match the api return. API returns 60.5, 59.7, 60.9 but UI shows 61, 60, 61"
severity: major
fix: Removed Math.round() from formatVND, added maximumFractionDigits: 1. Commit 2ae9484

### 2. Risk badge color and tooltip
expected: Risk badge pill shows correct color (red=Cao, yellow=Trung bình, green=Thấp). Hover shows tooltip with report reasoning text.
result: issue
reported: "risk_rating is null in content_json — LLM not generating it"
severity: major
fix: Strengthened LLM prompt to require risk_rating (LUÔN LUÔN trả về). Commit 8a6b18b. Requires re-generating reports to take effect.

### 3. Signal conflict conditional rendering
expected: For a stock with signal_conflicts in report — amber alert box with ⚠️ icon appears. For a stock without signal_conflicts — no alert box shown.
result: pass

### 4. Graceful degradation for pre-v1.4 reports
expected: Stock with pre-v1.4 report (no trade plan fields) — Trade Plan section completely absent, no empty card or placeholder
result: pass

### 5. Skeleton loading state
expected: While report data is loading, Trade Plan section shows skeleton placeholder (not blank space)
result: pass

### 6. Unit tests pass
expected: All 11 unit tests pass (extractTradePlan null handling, valid extraction, partial data, type narrowing, getRiskColors mapping)
result: pass

## Summary

total: 6
passed: 4
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

