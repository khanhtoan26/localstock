---
phase: 16-table-search-session-bar
plan: "02"
subsystem: ui
tags: [react, sort, vitest, lucide-react, table, tdd]

# Dependency graph
requires:
  - phase: 16-00
    provides: apps/helios/tests/sort-comparator.test.ts with 8 failing stubs defining the sort contract
  - phase: 16-01
    provides: nuqs installed and NuqsAdapter wired in layout.tsx
provides:
  - apps/helios/src/components/rankings/sort-comparator.ts (pure sort logic, unit-testable)
  - Fixed stock-table.tsx: numeric sort with tiebreaker, grade semantic sort, recommendation guard, ChevronUp/Down icons
affects:
  - 16-03 (search filter — StockTable now receives pre-filtered data correctly)
  - 16-04 (session bar — no direct dependency, but same wave)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Extract pure sort logic to dedicated module for unit testability (sort-comparator.ts pattern)
    - Grade semantic sort with direction inversion: GRADE_RANK map where desc puts rank 1 (A+) first
    - Conditional cursor-pointer via cn() on TableHead: non-sortable columns exclude cursor-pointer

key-files:
  created:
    - apps/helios/src/components/rankings/sort-comparator.ts
  modified:
    - apps/helios/src/components/rankings/stock-table.tsx
    - apps/helios/tests/sort-comparator.test.ts

key-decisions:
  - "Extracted sort logic to sort-comparator.ts: stock-table.tsx imports sortStocks instead of inline comparator, enabling unit testing without rendering"
  - "Grade sort direction inversion documented with inline comment (Pitfall 2): when sortDir=desc, comparator sorts ascending on GRADE_RANK so rank 1 (A+) floats to top"
  - "Recommendation column guard in handleSort returns early before any state update; TableHead loses cursor-pointer but onClick still present (no-op)"

patterns-established:
  - "Pattern: Pure comparator module (sort-comparator.ts) imported by component — separation enables vitest unit testing without DOM/React overhead"
  - "Pattern: cn() with conditional class for non-sortable column: cn(col.width, 'select-none text-xs', col.key !== 'recommendation' && 'cursor-pointer')"

requirements-completed:
  - TBL-01
  - TBL-02

# Metrics
duration: 2min
completed: 2026-04-25
---

# Phase 16 Plan 02: Sort Comparator Extraction and Stock Table Fix Summary

**Pure sortStocks comparator extracted to sort-comparator.ts with grade semantic sort (A+ first in desc), numeric tiebreaker, recommendation guard, and ChevronUp/Down icons replacing text indicators**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-25T01:22:52Z
- **Completed:** 2026-04-25T01:24:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `sort-comparator.ts` exporting `sortStocks`, `GRADE_RANK`, `SortKey`, `SortDir` — pure function with no React dependencies, fully unit-testable
- Fixed three sort bugs: (1) `return 0` replaced with `a.symbol.localeCompare(b.symbol)` tiebreaker, (2) grade sorted semantically via `GRADE_RANK` map with direction inversion, (3) recommendation returns original order unchanged
- Replaced 8 Wave 0 `expect(true).toBe(false)` stubs with real assertions — all 8 pass (vitest exit 0)
- Updated `stock-table.tsx`: imports `sortStocks` from `sort-comparator.ts`, `ChevronUp`/`ChevronDown` from lucide-react replace `↑`/`↓` text, recommendation column loses `cursor-pointer` via `cn()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract sort comparator to sort-comparator.ts** - `4bc82b3` (feat)
2. **Task 2: Update stock-table.tsx with icons, grade sort, and recommendation guard** - `00b2fe4` (feat)

**Plan metadata:** (committed with SUMMARY)

## Files Created/Modified

- `apps/helios/src/components/rankings/sort-comparator.ts` — New pure module: `sortStocks`, `GRADE_RANK`, `SortKey`, `SortDir` exports
- `apps/helios/src/components/rankings/stock-table.tsx` — Updated: imports sortStocks + SortKey/SortDir from sort-comparator.ts, ChevronUp/ChevronDown from lucide-react, cn() for conditional cursor-pointer, recommendation guard in handleSort
- `apps/helios/tests/sort-comparator.test.ts` — Wave 0 stubs replaced with 8 real assertions (all passing)

## Decisions Made

- `SortKey` and `SortDir` types moved to `sort-comparator.ts` and re-exported — `stock-table.tsx` removes local type aliases and imports from the module instead. This keeps the type source of truth co-located with the sort logic.
- `cn` explicitly imported from `@/lib/utils` alongside `formatScore` (same import line) — already exported from utils.ts, no new dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TBL-01 (numeric sort with tiebreaker) and TBL-02 (sort direction icons) requirements are complete
- `sort-comparator.ts` is a stable import target for any future sort-related tests
- `stock-table.tsx` is ready to receive `filtered` data from the parent page (16-03 search plan)
- No blockers for remaining Wave 1 plans (16-03, 16-04)

---
*Phase: 16-table-search-session-bar*
*Completed: 2026-04-25*

## Self-Check: PASSED

Files verified:
- FOUND: apps/helios/src/components/rankings/sort-comparator.ts
- FOUND: apps/helios/src/components/rankings/stock-table.tsx
- FOUND: apps/helios/tests/sort-comparator.test.ts
- FOUND: .planning/phases/16-table-search-session-bar/16-02-SUMMARY.md

Commits verified:
- FOUND: 4bc82b3 (feat: extract sortStocks to sort-comparator.ts)
- FOUND: 00b2fe4 (feat: update stock-table.tsx with icons, grade sort, recommendation guard)
