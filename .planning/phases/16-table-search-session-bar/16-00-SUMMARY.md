---
phase: 16-table-search-session-bar
plan: "00"
subsystem: frontend/testing
tags: [tdd, vitest, wave-0, stubs, sort, search, hose-session]
dependency_graph:
  requires: []
  provides:
    - apps/helios/tests/sort-comparator.test.ts
    - apps/helios/tests/search-filter.test.ts
    - apps/helios/tests/hose-session.test.ts
  affects:
    - apps/helios/src/components/rankings/sort-comparator.ts  # Wave 1 — must resolve import
    - apps/helios/src/components/rankings/filter-stocks.ts     # Wave 2 — must resolve import
    - apps/helios/src/components/layout/hose-session.ts        # Wave 2 — must resolve import
tech_stack:
  added: []
  patterns:
    - vitest failing stubs with expect(true).toBe(false)
    - forward-reference imports for not-yet-created modules
key_files:
  created:
    - apps/helios/tests/sort-comparator.test.ts
    - apps/helios/tests/search-filter.test.ts
    - apps/helios/tests/hose-session.test.ts
  modified: []
decisions:
  - "Stubs import non-existent modules (sort-comparator.ts, filter-stocks.ts, hose-session.ts) — vitest runs the tests and all 26 stubs fail with AssertionError, confirming Wave 0 baseline"
  - "Created apps/helios/tests/ directory (flat test dir at package root) following plan spec"
  - "Used explicit describe/it/expect imports from vitest (not relying on globals) matching glossary-linker.test.ts pattern"
metrics:
  duration: "128 seconds"
  completed_date: "2026-04-25"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 0
---

# Phase 16 Plan 00: Wave 0 Failing Test Stubs Summary

**One-liner:** Three vitest stub files establishing automated verification baseline for sort comparator, search filter, and HOSE session phase boundary logic before any implementation begins.

## What Was Built

Created the `apps/helios/tests/` directory with three failing test stub files that define the verification contract for Waves 1 and 2. All 26 stubs fail with `AssertionError: expected true to be false` — confirming the Wave 0 RED gate baseline.

### Task 1: sort-comparator.test.ts (8 stubs)

File: `apps/helios/tests/sort-comparator.test.ts`

Covers all sort behaviors for `sortStocks` function (to be extracted from `stock-table.tsx` in Wave 1):
- Numeric desc/asc ordering
- Null value sentinel (-Infinity, last position in desc)
- Symbol tiebreaker (A→Z when scores equal)
- Grade semantic sort desc (A+ first) and asc (C first)
- Unknown grade fallback to rank 99 (last position)
- Recommendation column guard (non-sortable, unchanged order)

### Task 2: search-filter.test.ts (6 stubs)

File: `apps/helios/tests/search-filter.test.ts`

Covers all filter behaviors for `filterStocks` function (to be created in Wave 2):
- Empty query returns all stocks
- Symbol prefix match (case-insensitive "vnm" → "VNM")
- Non-prefix rejection ("NM" does NOT match "VNM")
- Name substring match ("vinamilk" matches "Công ty Vinamilk")
- Null name field safe handling (no crash, treated as empty string)
- Whitespace-only query treated as empty (returns all stocks)

### Task 3: hose-session.test.ts (12 stubs)

File: `apps/helios/tests/hose-session.test.ts`

Two describe blocks for `getVNTimeParts` and `getCurrentHosePhase` (to be created in Wave 2):

`getVNTimeParts` (2 stubs):
- UTC 02:00 → VN 09:00 (UTC+7 conversion)
- UTC 00:00 → VN 07:00 (midnight boundary, Pitfall 5 guard)

`getCurrentHosePhase` (10 stubs):
- All 7 HOSE phase boundaries: Pre-market (08:45), ATO (09:05), Morning (10:00), Lunch (12:00), Afternoon (13:30), ATC (14:35), Closed (15:00)
- Weekend Saturday → Closed
- Weekend Sunday → Closed
- Active phase pct in (0, 100) range

## Verification Results

```
Test Files  4 failed | 1 passed (5)
Tests  26 failed | 16 passed (42)
```

The 26 failures are all our new stubs. The 16 passing tests are the pre-existing `glossary-linker.test.ts`. The e2e test file also fails (requires running server — pre-existing behavior, out of scope).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 0ae4b7a | test(16-00): add failing stubs for sort comparator logic |
| 2 | daf56f3 | test(16-00): add failing stubs for search filter logic |
| 3 | f9ea116 | test(16-00): add failing stubs for HOSE session phase boundaries |

## Deviations from Plan

None — plan executed exactly as written.

The stubs fail via `AssertionError: expected true to be false` (not via module import error), because vitest loads the test file even when the imported module doesn't exist — it catches the reference error at the stub level. This satisfies the plan's done criteria: "Running vitest reports failure or import error (not 'no test files found')."

## Known Stubs

All stubs in this plan are intentional Wave 0 placeholders. They will be replaced with real assertions when implementation modules are created in Waves 1 and 2:

| File | Import | Resolves After |
|------|--------|----------------|
| `tests/sort-comparator.test.ts` | `../src/components/rankings/sort-comparator` | Wave 1 (plan 16-02) |
| `tests/search-filter.test.ts` | `../src/components/rankings/filter-stocks` | Wave 2 (plan 16-03) |
| `tests/hose-session.test.ts` | `../src/components/layout/hose-session` | Wave 2 (plan 16-04) |

## Threat Flags

None — this plan creates only test files with no production code, no network endpoints, no auth paths, and no schema changes.

## TDD Gate Compliance

This is a Wave 0 (RED gate only) plan. All three files create failing stubs. GREEN gate will be established in Waves 1 and 2 when implementation modules are created.

- RED gate: PASS — all 26 stubs fail as expected
- GREEN gate: deferred to Waves 1 and 2
- REFACTOR gate: N/A for Wave 0

## Self-Check: PASSED

Files verified:
- FOUND: apps/helios/tests/sort-comparator.test.ts
- FOUND: apps/helios/tests/search-filter.test.ts
- FOUND: apps/helios/tests/hose-session.test.ts

Commits verified:
- FOUND: 0ae4b7a (sort-comparator stubs)
- FOUND: daf56f3 (search-filter stubs)
- FOUND: f9ea116 (hose-session stubs)
