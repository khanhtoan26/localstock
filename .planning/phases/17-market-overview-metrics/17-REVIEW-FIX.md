---
phase: 17-market-overview-metrics
fixed_at: 2026-04-25T00:00:00Z
review_path: .planning/phases/17-market-overview-metrics/17-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-04-25T00:00:00Z
**Source review:** .planning/phases/17-market-overview-metrics/17-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `total_volume = 0` silently coerced to `None`

**Files modified:** `apps/prometheus/src/localstock/api/routes/market.py`
**Commit:** f6737bf
**Applied fix:** Replaced `aggregate["total_volume"] or None` with `aggregate["total_volume"]` (with a comment noting the repo returns int or None). This eliminates the Python truthiness coercion that incorrectly converted a legitimate zero-volume value into `None`, which would cause the frontend to render "—" instead of "0".

---

### WR-02: Hardcoded English strings bypass i18n in `MarketSummaryCards`

**Files modified:** `apps/helios/messages/en.json`, `apps/helios/messages/vi.json`, `apps/helios/src/components/market/market-summary-cards.tsx`
**Commit:** 9c95f46
**Applied fix:**
- Added `advancesDetail`, `bullish`, and `bearish` keys under `market.summaryLabels` in both `en.json` and `vi.json` with appropriate English and Vietnamese translations.
- Updated `market-summary-cards.tsx` line 102 to use `t("summaryLabels.advancesDetail", { advances, declines })` instead of the hardcoded template literal.
- Updated line 119 to use `t("summaryLabels.bullish")` / `t("summaryLabels.bearish")` instead of hardcoded `"Bullish"` / `"Bearish"`.

---

### WR-03: Silent mismatch between `StockPrice` date and `TechnicalIndicator` date for volume change

**Files modified:** `apps/prometheus/src/localstock/db/repositories/price_repo.py`
**Commit:** c00c975
**Applied fix:** Added a `logger.debug(...)` call immediately after `avg_vol_20d = avg_vol_result.scalar()` that fires when `avg_vol_20d is None`. The log message identifies the affected date and explains the likely cause (analyze step has not yet run). `logger` was already imported from `loguru` at the top of the file — no additional import was needed.

---

_Fixed: 2026-04-25T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
