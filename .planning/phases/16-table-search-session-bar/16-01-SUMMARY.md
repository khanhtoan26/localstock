---
phase: 16-table-search-session-bar
plan: "01"
subsystem: ui
tags: [nuqs, react, next.js, url-state, provider]

# Dependency graph
requires:
  - phase: 16-00
    provides: nuqs integration design and NuqsAdapter placement decision
provides:
  - nuqs 2.x installed in apps/helios/package.json
  - NuqsAdapter provider wrapping AppShell in layout.tsx
  - useQueryState can be called without runtime errors in any component
affects:
  - 16-02 (rankings search — uses useQueryState for q param)
  - 16-03 (admin search — uses useQueryState for q param)
  - 16-04 (sort persistence — may use nuqs for sort state)

# Tech tracking
tech-stack:
  added:
    - nuqs@^2.8.9 (URL search-param state management for Next.js App Router)
  patterns:
    - NuqsAdapter wraps AppShell inside QueryProvider — all components in the app subtree can use useQueryState
    - Provider order: NextIntlClientProvider > ThemeProvider > QueryProvider > NuqsAdapter > AppShell

key-files:
  created: []
  modified:
    - apps/helios/package.json
    - apps/helios/package-lock.json
    - apps/helios/src/app/layout.tsx

key-decisions:
  - "nuqs placed inside QueryProvider (not outside) — nuqs is a URL-state adapter, not a React Query peer"
  - "NuqsAdapter takes no props — children-only, no configuration required for basic URL state"

patterns-established:
  - "Pattern: NuqsAdapter as innermost provider before app content (wraps AppShell directly)"

requirements-completed:
  - TBL-04

# Metrics
duration: 2min
completed: 2026-04-24
---

# Phase 16 Plan 01: nuqs Installation and NuqsAdapter Provider Summary

**nuqs 2.x installed and NuqsAdapter wired in layout.tsx, enabling URL-synchronized search state via useQueryState across all app components**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-24T14:47:50Z
- **Completed:** 2026-04-24T14:49:47Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Installed nuqs@^2.8.9 from npm (latest stable 2.x, compatible with Next.js 16.2.4)
- Added `import { NuqsAdapter } from "nuqs/adapters/next/app"` to layout.tsx
- Wrapped `<AppShell>` with `<NuqsAdapter>` inside `<QueryProvider>`, maintaining all existing provider nesting order
- All Wave 2 components using `useQueryState` will now run without the "NuqsAdapterMissing" runtime error (Pitfall 1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install nuqs and wire NuqsAdapter in layout.tsx** - `f84ecef` (feat)

**Plan metadata:** (committed with SUMMARY)

## Files Created/Modified

- `apps/helios/package.json` - Added nuqs@^2.8.9 to dependencies
- `apps/helios/package-lock.json` - Updated lock file after npm install
- `apps/helios/src/app/layout.tsx` - Added NuqsAdapter import and JSX wrapper around AppShell

## Decisions Made

- NuqsAdapter placed inside QueryProvider (not a peer) — nuqs manages URL state, not server-data fetching state; placement inside QueryProvider is correct per nuqs App Router docs
- No props needed on NuqsAdapter — default configuration handles all use cases for this project

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — npm install completed cleanly, edits matched the plan specification exactly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- nuqs foundation complete: Wave 2 plans (16-02, 16-03) can now use `useQueryState` without runtime errors
- layout.tsx provider stack is stable — no further provider changes needed for Phase 16
- No blockers for Wave 2 execution

---
*Phase: 16-table-search-session-bar*
*Completed: 2026-04-24*
