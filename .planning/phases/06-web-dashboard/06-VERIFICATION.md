---
phase: 06-web-dashboard
verified: 2026-04-16T22:30:00Z
status: human_needed
score: 7/7
overrides_applied: 0
human_verification:
  - test: "Dark theme visual check — background #020817 applied, text readable on dark"
    expected: "All pages show deep navy background with white/gray text, no unreadable elements"
    why_human: "CSS variable application cannot be verified visually via grep — needs browser render"
  - test: "Rankings table sorting — click column headers to sort asc/desc"
    expected: "Each column sorts correctly, arrow indicator (↑/↓) shows on active column, default sort is total_score desc"
    why_human: "Client-side sorting behavior requires interactive browser testing"
  - test: "Stock detail charts render correctly — candlestick + volume + overlays"
    expected: "Candlestick chart at 400px height, volume bars in bottom 20%, SMA/EMA/BB lines visible, MACD/RSI sub-panels at 152px"
    why_human: "Canvas rendering by lightweight-charts cannot be verified programmatically"
  - test: "Timeframe selector changes chart data range"
    expected: "Clicking 1T/3T/6T/1N/2N buttons updates chart with corresponding data range (30/90/180/365/730 days)"
    why_human: "Requires running dev server with backend data to verify end-to-end data flow"
  - test: "Market overview macro cards display real data"
    expected: "4 macro cards show Lãi Suất SBV, Tỷ Giá USD/VND, CPI, GDP with numeric values from backend"
    why_human: "Requires running backend with populated DB to verify data display"
---

# Phase 06: Web Dashboard Verification Report

**Phase Goal:** Visual web interface for browsing stock rankings, viewing charts with technical indicators, and reading AI analysis reports
**Verified:** 2026-04-16T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard displays a ranked stock table sortable by composite score with key metrics visible | ✓ VERIFIED | `rankings/page.tsx` uses `useTopScores(50)`, `StockTable` has 8 columns (#, Mã CK, Điểm, Hạng, Kỹ Thuật, Cơ Bản, Tin Tức, Vĩ Mô) with client-side sorting via `useState` and `handleSort()`. Row click navigates to `/stock/{symbol}` via `router.push`. |
| 2 | Stock detail page shows interactive price chart with technical indicators and the full AI analysis report | ✓ VERIFIED | `stock/[symbol]/page.tsx` uses `useStockPrices`, `useStockIndicators`, `useStockScore`, `useStockReport`. `PriceChart` renders candlestick+volume+SMA/EMA/BB overlays (400px). `SubPanel` renders MACD+RSI (152px each). AI report card with `ScrollArea` and `whitespace-pre-wrap`. No `dangerouslySetInnerHTML`. |
| 3 | Dashboard includes a market overview section with macro analysis summary and sector performance | ✓ VERIFIED | `market/page.tsx` uses `useMacroLatest()` and `useSectorsLatest()`. `MacroCards` shows 2×2 grid (Lãi Suất SBV, Tỷ Giá USD/VND, CPI, GDP). `SectorTable` has 4 columns (Ngành, Điểm TB, Số Mã, Hạng) with `scoreToGrade` + `GradeBadge`. |
| 4 | FastAPI backend accepts requests from http://localhost:3000 (CORS) | ✓ VERIFIED | `app.py` line 31-32: `CORSMiddleware` with `allow_origins=["http://localhost:3000"]` — restricted, not wildcard `*`. |
| 5 | 3 new API endpoints exist and are registered | ✓ VERIFIED | `prices.py`: GET `/api/prices/{symbol}`, GET `/api/prices/{symbol}/indicators`. `dashboard.py`: GET `/api/sectors/latest`. All registered in `app.py` lines 44-45. 8/8 tests pass. |
| 6 | lightweight-charts v5 API used correctly (addSeries pattern) | ✓ VERIFIED | `price-chart.tsx` uses `chart.addSeries(CandlestickSeries, {...})` — correct v5 API. No deprecated `addCandlestickSeries`. Same pattern in `sub-panel.tsx`. Proper `chart.remove()` cleanup in useEffect returns. |
| 7 | Dark theme with fixed sidebar and Vietnamese navigation | ✓ VERIFIED | `layout.tsx`: `<html lang="vi" className="dark">`. `globals.css` `.dark` section: `--background: hsl(222.2 84% 4.9%)` (#020817). Sidebar: fixed 240px (`w-60`), nav items "Xếp Hạng" and "Thị Trường". Root `/` redirects to `/rankings`. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/localstock/api/app.py` | CORS middleware + router registrations | ✓ VERIFIED | CORSMiddleware for localhost:3000, prices_router + dashboard_router included |
| `src/localstock/api/routes/prices.py` | OHLCV + indicator endpoints | ✓ VERIFIED | 2 endpoints with Path regex `^[A-Z0-9]+$`, Query ge=30 le=730, dependency injection |
| `src/localstock/api/routes/dashboard.py` | Sectors endpoint | ✓ VERIFIED | GET /api/sectors/latest with outerjoin IndustryGroup for Vietnamese names |
| `tests/test_api_dashboard.py` | Tests for new endpoints | ✓ VERIFIED | 8 tests across 4 classes — all passing |
| `web/package.json` | Next.js project with dependencies | ✓ VERIFIED | Next.js 16.2.4, React 19, lightweight-charts 5.1.0, @tanstack/react-query 5, recharts |
| `web/src/app/layout.tsx` | Root layout with dark theme + sidebar | ✓ VERIFIED | lang="vi", className="dark", AppShell + QueryProvider wrapping |
| `web/src/components/layout/sidebar.tsx` | Fixed left navigation sidebar | ✓ VERIFIED | 240px fixed, LocalStock logo, Xếp Hạng + Thị Trường nav with active state |
| `web/src/components/layout/app-shell.tsx` | Layout wrapper | ✓ VERIFIED | Sidebar + main `ml-60 p-6` |
| `web/src/lib/api.ts` | Typed fetch wrapper | ✓ VERIFIED | `apiFetch<T>()` generic with NEXT_PUBLIC_API_URL env var |
| `web/src/lib/types.ts` | TypeScript interfaces | ✓ VERIFIED | 14 interfaces matching all API response shapes |
| `web/src/lib/queries.ts` | react-query hooks | ✓ VERIFIED | 10 hooks including useTopScores, useStockPrices, useStockIndicators, useMacroLatest, useSectorsLatest |
| `web/src/lib/chart-colors.ts` | Chart color constants | ✓ VERIFIED | 17 colors matching UI-SPEC exactly |
| `web/src/lib/utils.ts` | Formatters + grade colors | ✓ VERIFIED | formatScore, formatVND, formatPercent, formatVolume, gradeColors map |
| `web/src/components/rankings/grade-badge.tsx` | Color-coded grade badge | ✓ VERIFIED | A=green, B=blue, C=yellow, D=orange, F=red — matches UI-SPEC |
| `web/src/components/rankings/stock-table.tsx` | DataTable with 8 columns | ✓ VERIFIED | Client-side sort, row click navigation, correct column headers |
| `web/src/components/market/macro-cards.tsx` | 2×2 macro indicator cards | ✓ VERIFIED | 4 ordered cards, Intl.NumberFormat for exchange rate, skeleton loading |
| `web/src/components/market/sector-table.tsx` | Sector performance table | ✓ VERIFIED | 4 columns, scoreToGrade function, GradeBadge integration |
| `web/src/components/charts/price-chart.tsx` | Candlestick + volume + overlays | ✓ VERIFIED | v5 addSeries API, ResizeObserver, chart.remove() cleanup, 400px height |
| `web/src/components/charts/sub-panel.tsx` | MACD/RSI sub-panels | ✓ VERIFIED | MACD: histogram+line+signal. RSI: line + createPriceLine at 70/30. 152px height |
| `web/src/components/charts/timeframe-selector.tsx` | Timeframe button group | ✓ VERIFIED | 5 options (1T/3T/6T/1N/2N), default 1N (365 days), variant toggle |
| `web/src/app/rankings/page.tsx` | Rankings page | ✓ VERIFIED | useTopScores(50), loading/error/empty/success states |
| `web/src/app/market/page.tsx` | Market overview page | ✓ VERIFIED | Independent macro/sectors sections, separate error handling |
| `web/src/app/stock/[symbol]/page.tsx` | Stock detail page | ✓ VERIFIED | Dynamic imports with ssr:false, 4 hooks at top-level (no conditional hooks), chart+report+scores |
| `web/src/app/page.tsx` | Root redirect | ✓ VERIFIED | `redirect("/rankings")` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api.ts` | `http://localhost:8000` | `NEXT_PUBLIC_API_URL` env var | ✓ WIRED | Line 1: `process.env.NEXT_PUBLIC_API_URL \|\| "http://localhost:8000"` |
| `queries.ts` | `api.ts` | `import apiFetch` | ✓ WIRED | Line 3: `import { apiFetch } from "./api"` — 10 hooks call apiFetch |
| `layout.tsx` | `app-shell.tsx` | `import AppShell` | ✓ WIRED | Line 2: `import { AppShell }` — wraps children in render |
| `rankings/page.tsx` | `/api/scores/top` | `useTopScores` | ✓ WIRED | Line 9: `useTopScores(50)` — data feeds `StockTable` |
| `market/page.tsx` | `/api/macro/latest` | `useMacroLatest` | ✓ WIRED | Line 10: `useMacroLatest()` — feeds `MacroCards` |
| `market/page.tsx` | `/api/sectors/latest` | `useSectorsLatest` | ✓ WIRED | Line 11: `useSectorsLatest()` — feeds `SectorTable` |
| `stock-table.tsx` | `/stock/{symbol}` | `router.push` | ✓ WIRED | Line 79: `router.push(\`/stock/${stock.symbol}\`)` |
| `price-chart.tsx` | `lightweight-charts` | `createChart + addSeries(CandlestickSeries)` | ✓ WIRED | Lines 25, 41: `createChart()`, `chart.addSeries(CandlestickSeries, {...})` |
| `stock/[symbol]/page.tsx` | `/api/prices/{symbol}` | `useStockPrices` | ✓ WIRED | Line 43: `useStockPrices(symbol, days)` |
| `stock/[symbol]/page.tsx` | `/api/reports/{symbol}` | `useStockReport` | ✓ WIRED | Line 46: `useStockReport(symbol)` |
| `stock/[symbol]/page.tsx` | `/api/prices/{symbol}/indicators` | `useStockIndicators` | ✓ WIRED | Line 44: `useStockIndicators(symbol, days)` |
| `prices.py` | `PriceRepository` | Dependency injection | ✓ WIRED | Line 31: `PriceRepository(session)` |
| `prices.py` | `IndicatorRepository` | Dependency injection | ✓ WIRED | Line 63: `IndicatorRepository(session)` |
| `dashboard.py` | `SectorSnapshotRepository` | Direct SQLAlchemy query | ✓ WIRED | Lines 27-37: uses SectorSnapshot + IndustryGroup models directly |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `rankings/page.tsx` | `data` (StockScore[]) | `useTopScores(50)` → `/api/scores/top` | Yes — calls PriceRepository via backend | ✓ FLOWING |
| `market/page.tsx` | `macro.data` | `useMacroLatest()` → `/api/macro/latest` | Yes — queries macro_indicators table | ✓ FLOWING |
| `market/page.tsx` | `sectors.data` | `useSectorsLatest()` → `/api/sectors/latest` | Yes — queries sector_snapshots joined with industry_groups | ✓ FLOWING |
| `stock/[symbol]/page.tsx` | `priceQuery.data` | `useStockPrices()` → `/api/prices/{symbol}` | Yes — PriceRepository.get_prices() queries stock_prices | ✓ FLOWING |
| `stock/[symbol]/page.tsx` | `indicatorQuery.data` | `useStockIndicators()` → `/api/prices/{symbol}/indicators` | Yes — IndicatorRepository.get_by_date_range() queries technical_indicators | ✓ FLOWING |
| `stock/[symbol]/page.tsx` | `reportQuery.data` | `useStockReport()` → `/api/reports/{symbol}` | Yes — queries reports table | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests pass | `pytest tests/test_api_dashboard.py -x -v` | 8 passed in 1.95s | ✓ PASS |
| All 326 tests pass (no regressions) | `pytest tests/ -x --tb=no -q` | 326 passed in 3.18s | ✓ PASS |
| Next.js build succeeds | `cd web && npx next build` | Compiled successfully, all routes generated | ✓ PASS |
| No deprecated LWC v4 API | `grep addCandlestickSeries` | 0 matches | ✓ PASS |
| No dangerouslySetInnerHTML (XSS) | `grep dangerouslySetInnerHTML` | 0 matches | ✓ PASS |
| No conditional hooks | Hooks at top-level in stock detail | All 6 hooks called unconditionally at lines 39-46 | ✓ PASS |
| Chart cleanup (no memory leaks) | `grep chart.remove + resizeObserver.disconnect` | Both cleanup in useEffect return in price-chart.tsx AND sub-panel.tsx | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| DASH-01 | 06-02, 06-03 | Web dashboard hiển thị bảng xếp hạng cổ phiếu theo điểm tổng hợp | ✓ SATISFIED | Rankings page with sortable 8-column DataTable, GradeBadge, row navigation |
| DASH-02 | 06-01, 06-04 | Dashboard cho phép xem chi tiết từng mã: biểu đồ giá, chỉ báo kỹ thuật, báo cáo AI | ✓ SATISFIED | Stock detail with candlestick chart, SMA/EMA/BB overlays, MACD/RSI panels, AI report card, score breakdown |
| DASH-03 | 06-01, 06-03 | Dashboard hiển thị tổng quan thị trường và phân tích vĩ mô | ✓ SATISFIED | Market page with 2×2 macro cards + sector performance table with GradeBadge |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TODOs, FIXMEs, placeholders, console.logs, empty returns, or stubs found | — | — |

**No anti-patterns detected.** All page placeholders from Plan 02 were properly replaced by Plans 03 and 04.

### Human Verification Required

### 1. Dark Theme Visual Rendering

**Test:** Open http://localhost:3000/rankings in a browser
**Expected:** Deep navy background (#020817), white/gray text readable, sidebar darker card surface
**Why human:** CSS variable application through oklch/HSL mapping requires visual browser check

### 2. Rankings Table Sorting

**Test:** Click column headers on the rankings page
**Expected:** Each column sorts asc/desc on click, arrow indicator (↑/↓) shows, default sort total_score desc
**Why human:** Client-side sorting logic requires interactive testing with real data

### 3. Candlestick Chart Rendering

**Test:** Navigate to /stock/VNM (or any symbol with data)
**Expected:** Candlestick chart at 400px, green/red candles, volume bars bottom 20%, SMA blue line, EMA purple line, BB gray dashed lines, MACD panel below (152px), RSI panel below (152px) with 70/30 dashed lines
**Why human:** Canvas rendering by lightweight-charts cannot be verified via grep

### 4. Timeframe Selector Data Refresh

**Test:** On stock detail page, click 1T, 3T, 6T, 1N, 2N buttons
**Expected:** Chart re-renders with different data range, active button filled, inactive outlined
**Why human:** Requires running backend with populated database

### 5. Market Overview Macro Cards

**Test:** Navigate to /market page
**Expected:** 4 cards showing Lãi Suất SBV (%), Tỷ Giá USD/VND (dot-formatted number), CPI (%), GDP (%) with real values
**Why human:** Requires running backend with macro data to verify end-to-end data display

### Gaps Summary

**No gaps found.** All 7 observable truths verified. All 3 requirements (DASH-01, DASH-02, DASH-03) satisfied. All 24 artifacts exist, are substantive, and are wired. All 14 key links verified. All data flows trace to real database queries. 326 backend tests pass. Next.js build succeeds with all routes generated.

The codebase demonstrates a thorough, production-quality implementation:
- **Backend:** CORS properly restricted to localhost:3000, symbol regex validation, query param bounds for DoS prevention
- **Frontend:** v5 lightweight-charts API, no deprecated patterns, proper chart cleanup, no XSS vectors, hooks rules followed
- **Architecture:** Clean data flow: react-query hooks → apiFetch → FastAPI → SQLAlchemy repositories → PostgreSQL

Status is `human_needed` because 5 items require visual/interactive browser testing that cannot be verified programmatically.

---

_Verified: 2026-04-16T22:30:00Z_
_Verifier: the agent (gsd-verifier)_
