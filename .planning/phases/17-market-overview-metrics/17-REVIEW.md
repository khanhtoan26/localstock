---
phase: 17-market-overview-metrics
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - apps/helios/messages/en.json
  - apps/helios/messages/vi.json
  - apps/helios/src/app/market/page.tsx
  - apps/helios/src/components/market/market-summary-cards.tsx
  - apps/helios/src/lib/queries.ts
  - apps/helios/src/lib/types.ts
  - apps/prometheus/src/localstock/api/app.py
  - apps/prometheus/src/localstock/api/routes/market.py
  - apps/prometheus/src/localstock/db/repositories/price_repo.py
  - apps/prometheus/tests/test_market_route.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-04-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 17 adds a `/api/market/summary` backend endpoint and a `MarketSummaryCards` frontend component to the Market Overview page. The implementation is generally clean and well-structured. The backend query logic is sound, all 8 tests pass, and i18n keys are correctly wired in both locales.

Three warnings were identified: a silent zero-to-null coercion that could misrepresent a real zero-volume day, hardcoded English strings bypassing i18n in the frontend component, and a date-alignment silent failure between the volume and avg_volume queries. Two info items flag a magic constant and a redundant guard.

---

## Warnings

### WR-01: `total_volume = 0` silently coerced to `None` in market route

**File:** `apps/prometheus/src/localstock/api/routes/market.py:82`

**Issue:** The expression `aggregate["total_volume"] or None` uses Python's truthiness coercion. When `total_volume` is `0` (a legitimate value on a market holiday or early in a fresh install), it is silently coerced to `None`. The frontend then renders `"—"` instead of `"0"`, which is misleading. The repository already returns `0` as an integer (via `COALESCE(..., 0)` and `int()` cast), so this coercion is unnecessary.

**Fix:**
```python
# Before
total_volume: int | None = aggregate["total_volume"] or None

# After — only coerce when the repo explicitly signals absence (None), not zero
total_volume: int | None = aggregate["total_volume"]  # repo returns int or None
```
If the intent is to distinguish "no data" from "zero volume," the repository should return `None` for the no-data case instead of `0` (update the early-return branch in `get_market_aggregate` to return `"total_volume": None`), and drop the `or None` coercion here.

---

### WR-02: Hardcoded English strings bypass i18n in `MarketSummaryCards`

**File:** `apps/helios/src/components/market/market-summary-cards.tsx:102` and `119`

**Issue:** Two user-visible strings are hardcoded in English and will not translate:
- Line 102: `{advances} up · {declines} down` (the sub-label under the Advances/Declines card)
- Line 119: `{breadth >= 50 ? "Bullish" : "Bearish"}` (the breadth direction label)

Both `en.json` and `vi.json` include `market.summaryLabels` and `market.summaryError`, but no keys for these inline labels. Vietnamese users will see raw English.

**Fix:** Add translation keys to both message files and use `t()`:

```json
// en.json — market.summaryLabels additions
"advancesDetail": "{advances} up · {declines} down",
"bullish": "Bullish",
"bearish": "Bearish"

// vi.json — market.summaryLabels additions
"advancesDetail": "{advances} tăng · {declines} giảm",
"bullish": "Tăng trưởng",
"bearish": "Giảm sút"
```

```tsx
// market-summary-cards.tsx line 102
{t("summaryLabels.advancesDetail", { advances, declines })}

// market-summary-cards.tsx line 119
{breadth >= 50 ? t("summaryLabels.bullish") : t("summaryLabels.bearish")}
```

---

### WR-03: Silent mismatch between `StockPrice` date and `TechnicalIndicator` date for volume change

**File:** `apps/prometheus/src/localstock/db/repositories/price_repo.py:215-221`

**Issue:** `get_market_aggregate` derives `latest_date` from `MAX(StockPrice.date)` (lines 183–203), then queries `TechnicalIndicator.date == latest_date` (line 216) to get `avg_volume_20`. If the crawl pipeline ran today (prices written) but the analyze step has not yet run (indicators not yet updated), `avg_vol_20d` will be `None` and `total_volume_change_pct` silently returns `None`. This is not a crash, but the volume change card shows `"—"` on the freshest trading day every time the crawl completes — which could be hours before analyze finishes. The issue is invisible to the operator.

This is a design trade-off rather than a hard bug, but the silent degradation should be logged so the condition is detectable:

**Fix:**
```python
avg_vol_20d = avg_vol_result.scalar()

# Add after line 221:
if avg_vol_20d is None:
    logger.debug(
        f"No avg_volume_20 found for TechnicalIndicator on {latest_date}; "
        "analyze step may not have run yet — total_volume_change_pct will be None"
    )
```

---

## Info

### IN-01: Magic constant `30 * 60 * 1000` in `useMarketSummary` stale time

**File:** `apps/helios/src/lib/queries.ts:104`

**Issue:** The stale time is computed inline as `30 * 60 * 1000` with a comment. The other queries in the same file use similar inline expressions (`5 * 60 * 1000`, `60 * 60 * 1000`). A named constant would make the intent more scannable and the value reusable.

**Fix:**
```typescript
// At the top of queries.ts (or a shared constants file):
const MIN_MS = 60 * 1000;

// Then:
staleTime: 30 * MIN_MS, // D-10: 30 minutes — daily crawl data rhythm
```

---

### IN-02: Redundant truthiness guard on `prev_vnindex.close` before `!= 0` check

**File:** `apps/prometheus/src/localstock/api/routes/market.py:69`

**Issue:** The condition `if prev_vnindex.close and prev_vnindex.close != 0` checks truthiness first and then explicitly checks for zero. Since `0.0` is already falsy in Python, `prev_vnindex.close != 0` is sufficient. The double check is not wrong, but it implies the author was uncertain — and it would silently suppress a legitimate `close = 0` case (which would be anomalous for VN-Index but is already guarded by the first clause).

**Fix:**
```python
# Before
if prev_vnindex is not None and prev_vnindex.close and prev_vnindex.close != 0:

# After — explicit and readable
if prev_vnindex is not None and prev_vnindex.close is not None and prev_vnindex.close != 0:
```
Using `is not None` is the idiomatic guard for nullable model fields and avoids accidental falsy suppression if the value were ever `0.0`.

---

_Reviewed: 2026-04-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
