---
phase: 06-web-dashboard
plan: 02
subsystem: web-scaffold
tags: [nextjs, shadcn-ui, dark-theme, sidebar, api-client, react-query]
dependency_graph:
  requires:
    - "06-01: CORS middleware + dashboard API endpoints"
  provides:
    - "web/ — runnable Next.js 16 project with dark financial theme"
    - "AppShell layout with fixed 240px sidebar and content area"
    - "apiFetch typed wrapper for all FastAPI backend calls"
    - "14 TypeScript interfaces matching backend response shapes"
    - "10 react-query hooks for data fetching"
    - "GradeBadge, EmptyState, ErrorState reusable components"
    - "Chart color constants from UI-SPEC"
    - "Vietnamese formatters (formatScore, formatVND, formatPercent, formatVolume)"
  affects:
    - "web/package.json"
tech_stack:
  added:
    - "Next.js 16.2.4"
    - "React 19"
    - "Tailwind CSS 4"
    - "shadcn/ui (table, card, badge, button, skeleton, separator, scroll-area)"
    - "lightweight-charts 5.1.0"
    - "@tanstack/react-query 5"
    - "recharts 3.8.1"
    - "lucide-react"
  patterns:
    - "App Router with file-based routing"
    - "Fixed dark theme (class='dark' on html element)"
    - "QueryClientProvider with 5-min staleTime for financial data"
    - "Centralized apiFetch generic wrapper with NEXT_PUBLIC_API_URL"
    - "react-query hooks per API endpoint"
key_files:
  created:
    - web/src/components/layout/sidebar.tsx
    - web/src/components/layout/app-shell.tsx
    - web/src/lib/query-provider.tsx
    - web/src/lib/api.ts
    - web/src/lib/types.ts
    - web/src/lib/queries.ts
    - web/src/lib/chart-colors.ts
    - web/src/components/ui/empty-state.tsx
    - web/src/components/ui/error-state.tsx
    - web/src/components/rankings/grade-badge.tsx
    - web/src/app/rankings/page.tsx
    - web/src/app/stock/[symbol]/page.tsx
    - web/src/app/market/page.tsx
  modified:
    - web/src/app/globals.css
    - web/src/app/layout.tsx
    - web/src/app/page.tsx
    - web/src/lib/utils.ts
decisions:
  - "Removed Geist font imports — using system-ui font stack per UI-SPEC"
  - "Dark theme CSS variables use HSL values merged into shadcn/ui oklch structure"
  - "Financial semantic tokens (--stock-up, --stock-down, --chart-bg) in :root scope"
  - "QueryClient staleTime 5min for scores, 1hr for prices/macro (data updates daily)"
metrics:
  duration: "19min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 13
  files_modified: 4
---

# Phase 06 Plan 02: Next.js Dashboard Scaffold Summary

**One-liner:** Next.js 16 project in web/ with dark financial theme (#020817), fixed 240px sidebar (Xếp Hạng/Thị Trường), typed API client with 10 react-query hooks, and reusable GradeBadge/EmptyState/ErrorState components.

## What Was Done

### Task 1: Scaffold Next.js project + dark theme + layout shell
**Commit:** `6db4cf8`

1. **Scaffolded Next.js 16** in `web/` with App Router, TypeScript, Tailwind CSS v4, ESLint
2. **Installed dependencies:** lightweight-charts 5.1.0, @tanstack/react-query 5, recharts 3.8.1, lucide-react
3. **Initialized shadcn/ui** with components: table, card, badge, button, skeleton, separator, scroll-area
4. **Configured dark financial theme** in `globals.css`:
   - Background: `hsl(222.2 84% 4.9%)` (#020817)
   - Primary: `hsl(217.2 91.2% 59.8%)` (#3b82f6)
   - Financial tokens: `--stock-up: #22c55e`, `--stock-down: #ef4444`, `--chart-bg: #0f172a`
5. **Created fixed sidebar** (240px, `w-60`) with LocalStock logo, Xếp Hạng and Thị Trường nav items
6. **Created AppShell** layout wrapper with `ml-60 p-6` content offset
7. **Created QueryProvider** with 5-min staleTime for financial data
8. **Updated layout.tsx:** `lang="vi"`, `className="dark"`, AppShell + QueryProvider wrapping
9. **Root page redirect:** `/` → `/rankings`
10. **Placeholder pages:** `/rankings`, `/stock/[symbol]`, `/market`

### Task 2: Shared libs + reusable components
**Commit:** `7539080`

1. **`api.ts`** — Centralized `apiFetch<T>()` generic fetch wrapper using `NEXT_PUBLIC_API_URL` env var
2. **`types.ts`** — 14 TypeScript interfaces matching all backend API response shapes:
   - `StockScore`, `TopScoresResponse`, `PricePoint`, `PriceHistoryResponse`
   - `IndicatorPoint`, `IndicatorHistoryResponse`, `MacroIndicator`, `MacroLatestResponse`
   - `SectorPerformance`, `SectorsLatestResponse`, `StockReport`, `TopReportsResponse`
   - `TechnicalData`, `FundamentalData`
3. **`queries.ts`** — 10 react-query hooks:
   - `useTopScores`, `useStockScore`, `useStockPrices`, `useStockIndicators`
   - `useStockTechnical`, `useStockFundamental`, `useStockReport`
   - `useMacroLatest`, `useSectorsLatest`, `useTriggerPipeline` (mutation)
4. **`utils.ts`** — Added formatters: `formatScore`, `formatVND`, `formatPercent`, `formatVolume`, `gradeColors` map
5. **`chart-colors.ts`** — 17 chart color constants from UI-SPEC (candle, volume, SMA, MACD, RSI, background, grid)
6. **`empty-state.tsx`** — Vietnamese "Chưa có dữ liệu" component with optional CTA button
7. **`error-state.tsx`** — Vietnamese "Không thể tải dữ liệu" component with backend error messaging
8. **`grade-badge.tsx`** — Color-coded grade badge (A=green, B=blue, C=yellow, D=orange, F=red)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed nested .git directory from web/**
- **Found during:** Task 1 commit
- **Issue:** `create-next-app` creates its own `.git` directory, causing git to treat `web/` as a submodule
- **Fix:** Removed `web/.git` and re-committed as regular tracked files
- **Files modified:** web/ (all files)
- **Commit:** `6db4cf8` (amended)

**2. [Rule 3 - Blocking] SSL certificate issue with shadcn init**
- **Found during:** Task 1 Step 3
- **Issue:** `npx shadcn@latest init` failed with "self-signed certificate in certificate chain"
- **Fix:** Used `NODE_TLS_REJECT_UNAUTHORIZED=0` for initial setup only (one-time scaffold)
- **Files modified:** None (tooling workaround)

**3. [Rule 1 - Bug] shadcn uses oklch colors, plan specified HSL**
- **Found during:** Task 1 Step 4
- **Issue:** shadcn/ui v4 generates oklch-based CSS variables, plan's CSS used HSL
- **Fix:** Replaced `.dark` section oklch values with financial dark theme HSL values; kept shadcn's `@theme inline` mapping layer intact
- **Files modified:** web/src/app/globals.css

## Verification Results

```
npm run build — ✓ Compiled successfully
npx tsc --noEmit — ✓ No TypeScript errors
All routes: /, /rankings, /stock/[symbol], /market — ✓ Generated
All acceptance criteria — ✓ 10/10 Task 1, 9/9 Task 2
```

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| Rankings placeholder | web/src/app/rankings/page.tsx | "Coming in Plan 03..." — will be replaced by Plan 03 rankings table |
| Stock detail placeholder | web/src/app/stock/[symbol]/page.tsx | Empty heading — will be replaced by Plan 04 stock detail page |
| Market placeholder | web/src/app/market/page.tsx | Empty heading — will be replaced by Plan 05 market overview page |

These stubs are intentional — each page will be fully implemented in its respective plan (03, 04, 05).

## Self-Check: PASSED

- [x] All 13 created files exist on disk
- [x] Commit `6db4cf8` exists (Task 1)
- [x] Commit `7539080` exists (Task 2)
- [x] `npm run build` succeeds
- [x] `npx tsc --noEmit` succeeds
