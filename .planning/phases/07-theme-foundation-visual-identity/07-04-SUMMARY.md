---
phase: 07-theme-foundation-visual-identity
plan: "04"
subsystem: ui
tags: [react, nextjs, tabs, collapsible, side-by-side-layout, stock-page]

requires:
  - phase: 07-theme-foundation-visual-identity
    provides: shadcn Tabs/Collapsible components, AIReportPanel, ScoreBreakdown, @tailwindcss/typography, react-markdown

provides:
  - StockDataPanel component with tabbed desktop and accordion mobile layout
  - Side-by-side stock detail page (AI report left 65%, data panel right 35%)
  - Score overview in page header (KT/CB/TT/VM compact display)
  - localStorage tab preference persistence

affects: [stock-detail, charts, scoring, ai-reports]

tech-stack:
  added: []
  patterns: [side-by-side-responsive-layout, localStorage-tab-persistence, dynamic-import-in-subcomponent]

key-files:
  created:
    - apps/helios/src/components/stock/stock-data-panel.tsx
  modified:
    - apps/helios/src/app/stock/[symbol]/page.tsx

key-decisions:
  - "D-13: Side-by-side layout — AI Report LEFT (65%), Chart/Data RIGHT (35%), no drawer"
  - "D-14: Right panel sticky (md:sticky md:top-6 md:self-start)"
  - "D-15: Score overview compact in header (KT/CB/TT/VM abbreviations)"
  - "D-20: Right panel tabs: Biểu đồ | Chỉ số | Điểm số"
  - "D-21: Tab persisted in localStorage key stock-data-tab, fallback chart"
  - "D-26: Mobile tabs → collapsible accordion sections below 768px"

patterns-established:
  - "Side-by-side responsive: flex-col md:flex-row with percentage widths"
  - "Sticky panel: md:sticky md:top-6 md:self-start for keeping right panel visible"
  - "localStorage persistence: read in useEffect (SSR-safe), validate against allowed set"
  - "Desktop/mobile split rendering: hidden md:block / block md:hidden"
---

# Plan 07-04 Summary

Stock detail page side-by-side redesign with StockDataPanel — AI report as primary left content, tabbed chart/indicators/score on sticky right panel, responsive accordion on mobile.

## What Was Done

### Task 1: StockDataPanel Component
Created `apps/helios/src/components/stock/stock-data-panel.tsx`:
- Desktop: `Tabs` with 3 panels — Biểu đồ (chart+timeframe selector), Chỉ số (MACD+RSI sub-panels), Điểm số (ScoreBreakdown)
- Mobile: 3 `Collapsible` accordion sections replacing tabs below md breakpoint
- `localStorage` tab persistence with validation against allowed values
- Dynamic imports for PriceChart and SubPanel (ssr: false) moved here from page
- Internal state for `days` (timeframe) and `activeTab`

### Task 2: Stock Detail Page Rewrite
Rewrote `apps/helios/src/app/stock/[symbol]/page.tsx`:
- Side-by-side layout: `flex-col md:flex-row gap-6`
- Left panel (65%): `AIReportPanel` with markdown rendering
- Right panel (35%): `StockDataPanel` with sticky positioning
- Header: symbol + GradeBadge + total score + 4 compact dimension scores (KT, CB, TT, VM)
- Removed: `useState`, `dynamic`, `useStockPrices`, `useStockIndicators`, `Card` imports — all moved to StockDataPanel

## Deviations from Plan

None — followed plan as specified.

## Issues Encountered
- base-ui Tabs API uses `onValueChange(value, eventDetails)` (not just value) — handled with generic handler accepting `unknown`

## Verification
- ✅ `npm run build` passes with no TypeScript errors
- ✅ `flex-col md:flex-row` layout in page.tsx
- ✅ `md:sticky` right panel
- ✅ `stock-data-tab` localStorage key in StockDataPanel
- ✅ `AIReportPanel` imported in page
- ✅ No `useStockPrices`, `Card`, or `useState` in page (moved to panel)

## Next Phase Readiness
- Stock page redesign complete, pending human visual verification (Task 3)
- Phase 7 execution complete pending code review and verification gates

---
*Phase: 07-theme-foundation-visual-identity*
*Plan: 04*
*Committed: f61dae7*
