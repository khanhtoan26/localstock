---
phase: 16-table-search-session-bar
plan: "03"
subsystem: ui
tags: [react, nuqs, search, filter, vitest, tdd, i18n, url-state]

# Dependency graph
requires:
  - phase: 16-01
    provides: nuqs installed and NuqsAdapter wired in layout.tsx
  - phase: 16-00
    provides: apps/helios/tests/search-filter.test.ts with 6 failing stubs

provides:
  - apps/helios/src/components/rankings/filter-stocks.ts (pure filterStocks function, unit-tested)
  - apps/helios/src/components/rankings/stock-search-input.tsx (StockSearchInput with nuqs URL state, 150ms debounce, clear button)
  - Search integration in rankings/page.tsx (useQueryState + useMemo filtered + noResults empty state)
  - rankings.search.{placeholder,clear} and rankings.noResults i18n keys in en.json and vi.json

affects:
  - 16-04 (session bar — no search dependency, same phase)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure filter module (filter-stocks.ts) unit-tested in isolation — separation enables vitest without React overhead
    - nuqs useQueryState('q') with local useState for immediate display + 150ms debounce for URL update
    - setQ(null) on clear removes ?q= param entirely (Pitfall 4 from RESEARCH.md)
    - Hooks (useQueryState, useMemo) placed before early-return guards — React hooks cannot be conditional

key-files:
  created:
    - apps/helios/src/components/rankings/filter-stocks.ts
    - apps/helios/src/components/rankings/stock-search-input.tsx
  modified:
    - apps/helios/src/app/rankings/page.tsx
    - apps/helios/messages/en.json
    - apps/helios/messages/vi.json
    - apps/helios/tests/search-filter.test.ts

key-decisions:
  - "setQ(null) for clear: null removes the ?q= param from URL entirely; setQ('') would keep ?q= in URL"
  - "Filter logic in page.tsx (useMemo), not in StockSearchInput — StockSearchInput is a pure URL-state widget; page owns derived data"
  - "useQueryState + useMemo placed before all early-return guards — React hook rules require unconditional hook calls"
  - "Threat T-16-03-01 mitigated: noResults uses t() interpolation via next-intl which escapes interpolated values, never dangerouslySetInnerHTML"

requirements-completed:
  - TBL-03
  - TBL-04

# Metrics
duration: 4min
completed: 2026-04-25
---

# Phase 16 Plan 03: Stock Search Feature Summary

**filterStocks pure function extracted and tested (6 passing), StockSearchInput with nuqs URL persistence + 150ms debounce wired into rankings page, i18n keys added to en.json and vi.json**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-25T01:27:22Z
- **Completed:** 2026-04-25T01:31:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `filter-stocks.ts` exporting `filterStocks`: symbol prefix match (case-insensitive startsWith) + name substring match (null-safe via cast); whitespace-only query returns all stocks unchanged
- Replaced all 6 Wave 0 `expect(true).toBe(false)` stubs in `search-filter.test.ts` with real assertions — all 6 pass (vitest exit 0)
- Created `StockSearchInput`: `useQueryState('q', parseAsString.withDefault('').withOptions({ shallow: true }))`, local `useState(q)` for immediate display, 150ms debounce via `useEffect`, `setQ(null)` on clear/Escape (removes ?q= param per Pitfall 4), `<X>` clear button with `aria-label`, `<Search>` icon, `sr-only` label for accessibility
- Updated `rankings/page.tsx`: added 4 imports (useMemo, useQueryState, StockSearchInput, filterStocks), placed `[q]` hook + `filtered` useMemo before early-return guards, updated happy-path return to render `<StockSearchInput />` between title and table, added noResults empty state when `filtered.length === 0 && q.trim()`
- Added `rankings.noResults` and `rankings.search.{placeholder,clear}` keys to both `messages/en.json` and `messages/vi.json` per UI-SPEC copywriting contract

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract filterStocks and wire tests (TDD RED→GREEN)** - `03f122b` (feat)
2. **Task 2: StockSearchInput component + rankings page integration + i18n keys** - `87a070e` (feat)

## Files Created/Modified

- `apps/helios/src/components/rankings/filter-stocks.ts` — New: pure `filterStocks` export with symbol prefix + name substring match
- `apps/helios/tests/search-filter.test.ts` — Updated: 6 stubs replaced with real assertions (all pass)
- `apps/helios/src/components/rankings/stock-search-input.tsx` — New: `"use client"` component with `useQueryState`, debounce, clear button
- `apps/helios/src/app/rankings/page.tsx` — Modified: added imports, hooks before guards, StockSearchInput + filtered data + noResults state
- `apps/helios/messages/en.json` — Modified: added `rankings.noResults` and `rankings.search.{placeholder,clear}`
- `apps/helios/messages/vi.json` — Modified: added Vietnamese equivalents of same keys

## Decisions Made

- `setQ(null)` vs `setQ("")` for clear: null removes `?q=` param entirely from the URL (Pitfall 4 in RESEARCH.md). `setQ("")` would leave `?q=` in the URL which looks unclean. Both approaches were valid; null was chosen for URL cleanliness.
- Filter logic in `page.tsx`, not in `StockSearchInput`: the component is a pure URL-state widget that reads/writes `?q=`. The filtering itself (useMemo + filterStocks) belongs to the page which owns the data. This matches the anti-pattern note in RESEARCH.md Pitfall 6.
- Hook placement before early returns: React hooks (useQueryState, useMemo) placed at the top of `RankingsPage` before any `if (isLoading)` guard. This is a React requirement — hooks cannot be called conditionally.

## Deviations from Plan

None - plan executed exactly as written.

## Security (Threat Model Compliance)

- **T-16-03-01 mitigated**: `t("noResults", { query: q })` uses next-intl's `t()` interpolation. next-intl escapes interpolated values in JSX context. No `dangerouslySetInnerHTML` or raw string concatenation with user input anywhere.
- **T-16-03-02 accepted**: `?q=` param used only for client-side array filtering. Never used as route path, redirect target, or API parameter.
- **T-16-03-03 accepted**: Search terms appear in URL as intended (D-09 URL persistence requirement).

## Known Stubs

None — `filterStocks` is fully implemented; `StockSearchInput` is fully wired. The `name` field branch `((s as { name?: string | null }).name ?? "").toLowerCase().includes(lower)` is forward-compatible dead code (StockScore has no `name` field yet), but it is not a stub — it is intentional defensive code that will activate when the type is extended.

## Issues Encountered

None — npm install in worktree was required to get vitest available (worktree had no node_modules), resolved by running `npm install` in `apps/helios` within the worktree.

---
*Phase: 16-table-search-session-bar*
*Completed: 2026-04-25*
