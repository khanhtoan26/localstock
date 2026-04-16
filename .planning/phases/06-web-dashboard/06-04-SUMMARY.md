---
phase: 06-web-dashboard
plan: 04
subsystem: web-charts
tags: [stock-detail, candlestick, lightweight-charts, macd, rsi, timeframe, ai-report]
dependency_graph:
  requires:
    - "06-01: CORS middleware + dashboard API endpoints (prices, indicators)"
    - "06-02: Next.js scaffold with shared libs, types, hooks, chart-colors"
  provides:
    - "PriceChart component: candlestick + volume + SMA/EMA/BB overlays (400px)"
    - "SubPanel component: MACD or RSI sub-chart (152px)"
    - "TimeframeSelector component: 1T/3T/6T/1N/2N button group"
    - "Stock detail page at /stock/[symbol] with charts, AI report, score breakdown"
  affects:
    - web/src/app/stock/[symbol]/page.tsx
tech_stack:
  added: []
  patterns:
    - "lightweight-charts v5 API: addSeries(CandlestickSeries) pattern"
    - "Dynamic import with ssr: false for browser-only chart libs"
    - "ResizeObserver for responsive chart width"
    - "createPriceLine for RSI 70/30 reference lines"
key_files:
  created:
    - web/src/components/charts/price-chart.tsx
    - web/src/components/charts/sub-panel.tsx
    - web/src/components/charts/timeframe-selector.tsx
  modified:
    - web/src/app/stock/[symbol]/page.tsx
decisions:
  - "Dynamic import with ssr: false for PriceChart and SubPanel — prevents window is not defined crash (Pitfall 1)"
  - "Report rendered as React text node with whitespace-pre-wrap — no dangerouslySetInnerHTML (T-06-09 XSS mitigation)"
  - "Volume histogram overlaid on main chart with priceScaleId: volume and scaleMargins top: 0.8"
  - "BB bands rendered with lineStyle: 2 (dashed) to distinguish from price action"
metrics:
  duration: "3min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 06 Plan 04: Stock Detail Page with Charts Summary

**One-liner:** Stock detail page at /stock/[symbol] with candlestick+volume chart (400px), SMA/EMA/BB overlays, MACD+RSI sub-panels (152px each), timeframe selector (1T-2N, default 1N), AI report card with XSS-safe rendering, and 2×2 score breakdown grid — all using lightweight-charts v5 API with dynamic imports.

## What Was Done

### Task 1: Chart components — PriceChart, SubPanel, TimeframeSelector
**Commit:** `be77a72`

1. **`web/src/components/charts/price-chart.tsx`** — Main chart component:
   - Candlestick series with green/red up/down colors from CHART_COLORS
   - Volume histogram overlay on same chart (bottom 20% via `scaleMargins: { top: 0.8, bottom: 0 }`)
   - Indicator overlays: SMA 20 (blue #3b82f6), EMA 12 (purple #a855f7), BB upper/lower (gray dashed)
   - Uses `createChart()` with 400px height, dark background, crosshair mode 0
   - ResizeObserver for responsive width on container resize
   - Proper cleanup: `resizeObserver.disconnect()` + `chart.remove()` in useEffect return

2. **`web/src/components/charts/sub-panel.tsx`** — MACD/RSI sub-panel:
   - MACD mode: histogram (green/red), MACD line (blue), signal line (orange)
   - RSI mode: RSI line (purple) with `createPriceLine` at 70 (red dashed) and 30 (green dashed)
   - Default height: 152px (multiple of 4 per UI-SPEC)
   - Label: "MACD (12, 26, 9)" or "RSI (14)" above chart

3. **`web/src/components/charts/timeframe-selector.tsx`** — Button group:
   - 5 timeframe options: 1T (30d), 3T (90d), 6T (180d), 1N (365d), 2N (730d)
   - Active button: `variant="default"` (filled), inactive: `variant="outline"`

### Task 2: Stock detail page assembly
**Commit:** `e20ca88`

Replaced placeholder `web/src/app/stock/[symbol]/page.tsx` with full implementation:

1. **Header bar:** Symbol in 28px semibold + GradeBadge + formatted total score + "← Quay lại" back link to /rankings
2. **Price chart section:** Loading → Skeleton(400px), Error → ErrorState, Empty → EmptyState, Success → PriceChart with indicator overlays
3. **Timeframe selector:** `useState(365)` for default 1N, onChange updates `days` state which re-fetches data
4. **Sub-panels:** MACD + RSI panels rendered when indicator data available
5. **AI Report card:** "Báo Cáo AI" heading, ScrollArea for long text, `whitespace-pre-wrap` rendering (no XSS). Falls back to JSON.stringify(content_json) if summary is null
6. **Score breakdown card:** "Phân Tích Điểm" heading, 2×2 grid showing Kỹ Thuật, Cơ Bản, Tin Tức, Vĩ Mô scores
7. **Dynamic imports:** PriceChart and SubPanel loaded with `dynamic(() => import(...), { ssr: false })` to prevent SSR crash

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation | Implemented |
|-----------|------------|-------------|
| T-06-09 | Report text rendered as React text node with `whitespace-pre-wrap` — NO `dangerouslySetInnerHTML` | ✅ |
| T-06-10 | Symbol param `.toUpperCase()` on frontend, backend validates with regex | ✅ |
| T-06-11 | Max 730 days data accepted — lightweight-charts handles efficiently | ✅ |

## Verification Results

```
npx tsc --noEmit — ✓ No TypeScript errors
npm run build — ✓ Compiled successfully
grep "ssr: false" page.tsx — 3 matches (PriceChart, SubPanel, loading fallback)
grep "dangerouslySetInnerHTML" page.tsx — 0 matches (XSS safe)
grep hooks page.tsx — all 4 hooks present (useStockPrices, useStockIndicators, useStockScore, useStockReport)
Route /stock/[symbol] — ✓ Generated as dynamic (ƒ)
```

## Self-Check: PASSED

- [x] `web/src/components/charts/price-chart.tsx` exists
- [x] `web/src/components/charts/sub-panel.tsx` exists
- [x] `web/src/components/charts/timeframe-selector.tsx` exists
- [x] `web/src/app/stock/[symbol]/page.tsx` updated (not placeholder)
- [x] Commit `be77a72` exists
- [x] Commit `e20ca88` exists
- [x] `npm run build` succeeds
