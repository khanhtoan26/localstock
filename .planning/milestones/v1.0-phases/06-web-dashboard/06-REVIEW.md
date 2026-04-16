---
phase: 06-web-dashboard
reviewed: 2025-07-18T10:30:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - src/localstock/api/app.py
  - src/localstock/api/routes/dashboard.py
  - src/localstock/api/routes/prices.py
  - web/next.config.ts
  - web/src/app/layout.tsx
  - web/src/app/market/page.tsx
  - web/src/app/page.tsx
  - web/src/app/rankings/page.tsx
  - web/src/app/stock/[symbol]/page.tsx
  - web/src/components/charts/price-chart.tsx
  - web/src/components/charts/sub-panel.tsx
  - web/src/components/charts/timeframe-selector.tsx
  - web/src/components/layout/app-shell.tsx
  - web/src/components/layout/sidebar.tsx
  - web/src/components/market/macro-cards.tsx
  - web/src/components/market/sector-table.tsx
  - web/src/components/rankings/grade-badge.tsx
  - web/src/components/rankings/stock-table.tsx
  - web/src/lib/api.ts
  - web/src/lib/chart-colors.ts
  - web/src/lib/queries.ts
  - web/src/lib/query-provider.tsx
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2025-07-18T10:30:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

The Phase 06 Web Dashboard implementation is solid overall. The codebase is clean, well-structured, and follows established project patterns. Security is handled appropriately — CORS is properly restricted to `localhost:3000`, backend path parameters are validated with regex, and the React frontend uses JSX escaping throughout (no `dangerouslySetInnerHTML` or `innerHTML`). No console.log statements, no debug artifacts, no hardcoded secrets.

Key strengths:
- Chart components correctly handle cleanup (ResizeObserver disconnect + chart.remove)
- QueryProvider properly uses `useState` to prevent QueryClient recreation
- lightweight-charts is correctly dynamic-imported with `ssr: false` to avoid SSR crashes
- All React hooks follow rules of hooks — no conditional hook calls
- Type definitions match backend API response shapes
- Loading/error/empty states are consistently handled across all pages

One warning-level bug found in the Python backend (falsy check treats valid `0.0` as `None`), plus three info-level items.

## Warnings

### WR-01: Falsy check on `avg_score_change` treats zero as None

**File:** `src/localstock/api/routes/dashboard.py:52`
**Issue:** The expression `round(snap.avg_score_change, 1) if snap.avg_score_change else None` uses a truthiness check. In Python, `0.0` is falsy, so a valid zero score change (sector score unchanged) is silently converted to `None` and sent to the frontend as `null` instead of `0.0`. This loses valid data — the frontend cannot distinguish "no change data available" from "score changed by exactly zero."

**Fix:**
```python
# Before (line 52):
"avg_score_change": round(snap.avg_score_change, 1) if snap.avg_score_change else None,

# After:
"avg_score_change": round(snap.avg_score_change, 1) if snap.avg_score_change is not None else None,
```

## Info

### IN-01: Chart full recreation when indicator data loads after price data

**File:** `web/src/components/charts/price-chart.tsx:149`
**Issue:** The `useEffect` dependency array is `[prices, indicators]`. When the price query resolves first (showing candlesticks), then the indicator query resolves (changing `indicators` from `undefined` to data), the entire chart is destroyed and recreated — including the already-rendered candlesticks and volume bars. This causes an unnecessary DOM teardown/rebuild cycle. With lightweight-charts' fast rendering this is likely imperceptible, but the pattern is suboptimal.

**Fix:** Split into two effects — one for the base chart (candlestick + volume) that depends on `[prices]`, and a second that uses `chartRef` to add/update indicator overlay series when `indicators` changes. This avoids recreating the candlestick chart when only indicators need updating.

### IN-02: `SortKey` type includes non-sortable fields

**File:** `web/src/components/rankings/stock-table.tsx:16`
**Issue:** `type SortKey = keyof StockScore` includes all 11 keys of the `StockScore` interface, but only 8 are actual table columns. Keys like `date`, `dimensions_used`, and `weights` (a `Record<string, number> | null`) are included in the type but have no corresponding column. The sort function uses `?? -Infinity` as a null fallback, which would produce incorrect results for object-typed fields like `weights` if they were ever used as a sort key.

**Fix:**
```typescript
// Before:
type SortKey = keyof StockScore;

// After:
type SortKey = "rank" | "symbol" | "total_score" | "grade" | "technical_score" | "fundamental_score" | "sentiment_score" | "macro_score";
```

### IN-03: Potential "null" string display in AI report card

**File:** `web/src/app/stock/[symbol]/page.tsx:127-128`
**Issue:** The expression `reportQuery.data.summary || JSON.stringify(reportQuery.data.content_json, null, 2)` falls through to `JSON.stringify` when `summary` is `null` or empty string. If `content_json` is also `null`, `JSON.stringify(null, null, 2)` returns the literal string `"null"`, which would be displayed to the user as visible text. While unlikely in practice (a report should have at least one populated field), the edge case is unhandled.

**Fix:**
```tsx
// Before:
{reportQuery.data.summary ||
  JSON.stringify(reportQuery.data.content_json, null, 2)}

// After:
{reportQuery.data.summary ||
  (reportQuery.data.content_json
    ? JSON.stringify(reportQuery.data.content_json, null, 2)
    : "Báo cáo không có nội dung.")}
```

---

_Reviewed: 2025-07-18T10:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
