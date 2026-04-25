---
phase: 17-market-overview-metrics
plan: "02"
subsystem: frontend
tags: [nextjs, tanstack-query, typescript, i18n, market-cards]

# Dependency graph
requires:
  - "17-01: GET /api/market/summary backend endpoint"
provides:
  - "MarketSummaryResponse and VnindexData TypeScript interfaces in types.ts"
  - "useMarketSummary TanStack Query hook (queryKey: [market, summary], staleTime 30min)"
  - "MarketSummaryCards component — 4-card grid with skeleton, change %, trend arrows"
  - "Market Overview page with MarketSummaryCards section FIRST before MacroCards"
  - "English and Vietnamese i18n keys for market summary section"
affects:
  - "apps/helios/src/app/market/page.tsx — market page layout updated"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TanStack Query hook with staleTime: 30 * 60 * 1000 — matches daily-crawl data rhythm (D-10)"
    - "next-intl ICU message format with {date} parameter in asOf key"
    - "Inline ChangeRow sub-component for green/red trend arrows (D-05)"
    - "Intl.NumberFormat vi-VN locale for VN-Index value display"

key-files:
  created:
    - apps/helios/src/components/market/market-summary-cards.tsx
  modified:
    - apps/helios/src/lib/types.ts
    - apps/helios/src/lib/queries.ts
    - apps/helios/src/app/market/page.tsx
    - apps/helios/messages/en.json
    - apps/helios/messages/vi.json

key-decisions:
  - "MarketSummaryCards section placed before MacroCards section in market/page.tsx (D-08)"
  - "staleTime set to 30 * 60 * 1000 (30 minutes) to match daily crawl data rhythm (D-10)"
  - "VnindexData and MarketSummaryResponse inserted after SectorsLatestResponse in types.ts to maintain logical grouping"
  - "useMarketSummary inserted after useSectorsLatest, before useTriggerPipeline in queries.ts"

# Metrics
duration: 4min
completed: 2026-04-25
---

# Phase 17 Plan 02: Frontend Market Summary Cards Summary

**4-card Market Summary section with TanStack Query hook, TypeScript types, skeleton loading, change indicators, and i18n — wired to GET /api/market/summary backend from Wave 1**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-25
- **Completed:** 2026-04-25
- **Tasks:** 2
- **Files modified:** 5 (1 created, 5 modified)

## Accomplishments

- Added `VnindexData` and `MarketSummaryResponse` TypeScript interfaces to `types.ts` (inserted after `SectorsLatestResponse`)
- Added `useMarketSummary()` TanStack Query hook to `queries.ts` with `queryKey: ["market", "summary"]` and `staleTime: 30 * 60 * 1000` (D-10)
- Created `market-summary-cards.tsx` component with 4 cards: VN-Index, Total Volume, Advances/Declines, Market Breadth
- Each card shows label + primary value + `ChangeRow` sub-component (green ↑ / red ↓ per D-05)
- Skeleton loading state renders 4 skeleton cards with 3-row skeleton each (D-11)
- Updated `market/page.tsx` to place Market Summary section FIRST before MacroCards (D-08)
- Inline "as of [date]" label renders when `summary.data?.as_of` is present (D-04)
- Added all required i18n keys to both `en.json` and `vi.json`: `summaryTitle`, `summaryError`, `asOf` (with `{date}` ICU param), `summaryLabels.{vnindex,totalVolume,advances,breadth}`
- `npm run build` exits 0 — no TypeScript or compilation errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TypeScript types and useMarketSummary hook** — `3a0ef2e`
2. **Task 2: Create MarketSummaryCards component, update market page, add i18n keys** — `87183c9`

## Files Created/Modified

- `apps/helios/src/components/market/market-summary-cards.tsx` — New component with 4 cards, skeleton, change indicators
- `apps/helios/src/lib/types.ts` — Added `VnindexData` and `MarketSummaryResponse` interfaces
- `apps/helios/src/lib/queries.ts` — Added `MarketSummaryResponse` import and `useMarketSummary()` hook
- `apps/helios/src/app/market/page.tsx` — Added `useMarketSummary`, `MarketSummaryCards`, market summary section first
- `apps/helios/messages/en.json` — Added `summaryTitle`, `summaryError`, `asOf`, `summaryLabels.*`
- `apps/helios/messages/vi.json` — Added Vietnamese equivalents of all summary keys

## Decisions Made

- Market Summary section placed before Macro Indicators section in `market/page.tsx` per D-08 (market summary is primary)
- `staleTime: 30 * 60 * 1000` (30 minutes) for `useMarketSummary` per D-10 — daily crawl data does not update intraday
- `VnindexData` and `MarketSummaryResponse` inserted after `SectorsLatestResponse` in types.ts to maintain logical grouping of market-related types
- `useMarketSummary` inserted after `useSectorsLatest`, before `useTriggerPipeline` in queries.ts to maintain grouped market hooks

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 4 cards are wired to real `useMarketSummary` hook data. The `—` fallback values display when backend returns null fields, which is the intended behavior for empty-DB state.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model. All data rendered is aggregate market data (no PII). The `{date}` ICU parameter in `asOf` receives a backend-supplied ISO date string, not user input — no XSS risk.

## Self-Check: PASSED

- `apps/helios/src/components/market/market-summary-cards.tsx` — FOUND
- `apps/helios/src/lib/types.ts` — FOUND (modified)
- `apps/helios/src/lib/queries.ts` — FOUND (modified)
- `apps/helios/src/app/market/page.tsx` — FOUND (modified)
- `apps/helios/messages/en.json` — FOUND (modified)
- `apps/helios/messages/vi.json` — FOUND (modified)
- Task 1 commit `3a0ef2e` — FOUND
- Task 2 commit `87183c9` — FOUND
- `npm run build` — exits 0, no TypeScript errors
