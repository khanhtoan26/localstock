---
phase: 06-web-dashboard
plan: 03
subsystem: web-pages
tags: [rankings, market, datatable, macro-cards, sector-table, react-query]
dependency_graph:
  requires:
    - "06-01: CORS middleware + dashboard API endpoints"
    - "06-02: Next.js scaffold with shared libs, types, hooks, reusable components"
  provides:
    - "Rankings page with sortable 8-column DataTable consuming /api/scores/top"
    - "Market Overview page with 2x2 macro indicator cards from /api/macro/latest"
    - "Market Overview page with sector performance table from /api/sectors/latest"
    - "StockTable reusable component with client-side sorting and row click navigation"
    - "MacroCards reusable component with loading skeleton support"
    - "SectorTable reusable component with GradeBadge integration"
  affects:
    - web/src/app/rankings/page.tsx
    - web/src/app/market/page.tsx
tech_stack:
  added: []
  patterns:
    - "Client-side sorting with useState for sortKey/sortDir toggle"
    - "Independent loading/empty/error state handling per data section"
    - "Indicator type lookup map for ordered macro card rendering"
    - "scoreToGrade conversion function for sector average scores"
key_files:
  created:
    - web/src/components/rankings/stock-table.tsx
    - web/src/components/market/macro-cards.tsx
    - web/src/components/market/sector-table.tsx
  modified:
    - web/src/app/rankings/page.tsx
    - web/src/app/market/page.tsx
decisions:
  - "Client-side sorting in StockTable via useState — no server-side sort needed for ~400 stocks"
  - "scoreToGrade thresholds in SectorTable (80/60/40/20) match backend scoring/__init__.py"
  - "MacroCards ordered types hardcoded as interest_rate, exchange_rate_usd_vnd, cpi, gdp"
  - "Independent error handling per section on Market page — macro and sectors fail independently"
metrics:
  duration: "2min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 06 Plan 03: Rankings & Market Overview Pages Summary

**One-liner:** Rankings page with sortable 8-column DataTable (score/grade/sub-scores) and Market Overview page with 2×2 macro indicator cards (SBV rate, USD/VND, CPI, GDP) + sector performance table with GradeBadge, all consuming live backend API via react-query hooks.

## What Was Done

### Task 1: StockTable DataTable + Rankings page (DASH-01)
**Commit:** `a43212b`

1. **`web/src/components/rankings/stock-table.tsx`** — DataTable with 8 columns:
   - Columns: # (rank), Mã CK (symbol link), Điểm (total_score), Hạng (grade badge), Kỹ Thuật, Cơ Bản, Tin Tức, Vĩ Mô
   - Client-side sorting: click column header to toggle asc/desc, default sort `total_score` descending
   - Sort indicator arrows (↑/↓) displayed on active sort column
   - Row click navigates to `/stock/{symbol}` via Next.js router
   - Row hover: `bg-muted/50` highlight with `cursor-pointer`
   - Symbol column: `text-primary font-medium hover:underline`
   - Score columns: `font-mono text-sm` with `formatScore()` for 1-decimal display, em dash for null
   - Grade column: `GradeBadge` component for color-coded A/B/C/D/F display

2. **`web/src/app/rankings/page.tsx`** — Full implementation replacing placeholder:
   - Uses `useTopScores(50)` hook to fetch top 50 ranked stocks
   - Loading state: 8 `Skeleton` rows with `h-10 w-full` shimmer
   - Empty state: `EmptyState` with "Chạy Pipeline" CTA button triggering `useTriggerPipeline` mutation
   - Error state: `ErrorState` with default backend connection error message
   - Success state: `StockTable` with `data.stocks` array

### Task 2: MacroCards + SectorTable + Market Overview page (DASH-03)
**Commit:** `279cffe`

1. **`web/src/components/market/macro-cards.tsx`** — 2×2 grid of macro indicator cards:
   - 4 cards ordered: Lãi Suất SBV, Tỷ Giá USD/VND, CPI, GDP
   - Exchange rate formatted with `Intl.NumberFormat("vi-VN")` (dot separators)
   - Other indicators formatted with `toFixed(1)%`
   - Loading state: skeleton cards matching layout
   - Missing indicators show em dash (—)
   - Card design: `border border-border`, label in `text-xs text-muted-foreground`, value in `text-xl font-semibold font-mono`

2. **`web/src/components/market/sector-table.tsx`** — Sector performance ranking table:
   - 4 columns: Ngành (Vietnamese name), Điểm TB (avg score), Số Mã (stock count), Hạng (grade badge)
   - `scoreToGrade` function converts avg_score to A/B/C/D/F using same thresholds as backend
   - Uses `GradeBadge` component and `formatScore` utility

3. **`web/src/app/market/page.tsx`** — Full implementation replacing placeholder:
   - Uses `useMacroLatest()` and `useSectorsLatest()` hooks
   - Two independent sections with separate state handling:
     - Macro section: error → `ErrorState`, loading → skeleton cards, success → `MacroCards`
     - Sector section: loading → skeleton rows, error → `ErrorState`, empty → `EmptyState`, success → `SectorTable`
   - Section headers: "Chỉ Số Vĩ Mô" and "Hiệu Suất Ngành"

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```
npx tsc --noEmit — ✓ No TypeScript errors
npm run build — ✓ Compiled successfully
All routes generated: /, /_not-found, /market, /rankings, /stock/[symbol]
grep "Xếp Hạng Cổ Phiếu" rankings/page.tsx — ✓ Found
grep "Tổng Quan Thị Trường" market/page.tsx — ✓ Found
grep "useTopScores" rankings/page.tsx — ✓ Found
grep "useMacroLatest" market/page.tsx — ✓ Found
```

## Self-Check: PASSED

- [x] `web/src/components/rankings/stock-table.tsx` exists
- [x] `web/src/components/market/macro-cards.tsx` exists
- [x] `web/src/components/market/sector-table.tsx` exists
- [x] `web/src/app/rankings/page.tsx` updated (not placeholder)
- [x] `web/src/app/market/page.tsx` updated (not placeholder)
- [x] Commit `a43212b` exists
- [x] Commit `279cffe` exists
- [x] `npm run build` succeeds
