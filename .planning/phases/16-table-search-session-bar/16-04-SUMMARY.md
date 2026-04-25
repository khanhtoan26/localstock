---
phase: 16-table-search-session-bar
plan: "04"
subsystem: frontend/layout
tags: [react, hose, market-session, vitest, ssr-guard, i18n, progress-bar]
dependency_graph:
  requires:
    - phase: 16-00
      provides: apps/helios/tests/hose-session.test.ts with 12 failing stubs
  provides:
    - apps/helios/src/components/layout/hose-session.ts (pure HOSE timezone + phase logic)
    - apps/helios/src/components/layout/market-session-bar.tsx (client component with SSR guard)
  affects:
    - apps/helios/src/components/layout/app-shell.tsx (header now shows MarketSessionBar)
    - apps/helios/messages/en.json (sessionBar i18n keys added)
    - apps/helios/messages/vi.json (sessionBar i18n keys added)
tech_stack:
  added: []
  patterns:
    - Pure function extraction to hose-session.ts for unit testability (no React deps)
    - SSR hydration guard via useSyncExternalStore (same pattern as theme-toggle.tsx)
    - Intl.DateTimeFormat.formatToParts for IANA timezone extraction (avoids Pitfall 5)
    - setInterval 60s refresh with clearInterval cleanup in useEffect
    - hidden sm:flex for mobile-hidden header component
key_files:
  created:
    - apps/helios/src/components/layout/hose-session.ts
    - apps/helios/src/components/layout/market-session-bar.tsx
  modified:
    - apps/helios/src/components/layout/app-shell.tsx
    - apps/helios/messages/en.json
    - apps/helios/messages/vi.json
    - apps/helios/tests/hose-session.test.ts
decisions:
  - "Extracted HOSE logic to hose-session.ts separate from the React component so all phase boundary logic is unit-testable without DOM/React overhead"
  - "Used Intl.DateTimeFormat.formatToParts for timezone extraction instead of raw UTC offset arithmetic — handles DST edge cases and Pitfall 5 (midnight UTC = 07:00 VN)"
  - "14 tests written (12 required + 2 bonus midpoint pct assertions) — all pass"
  - "MarketSessionBar renders hidden placeholder div during SSR to avoid hydration mismatch from Date.now() difference between server and client"
metrics:
  duration: "176 seconds"
  completed_date: "2026-04-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
---

# Phase 16 Plan 04: HOSE Market Session Bar Summary

**One-liner:** Pure `hose-session.ts` module with `Intl.DateTimeFormat` timezone extraction feeds a `MarketSessionBar` client component using `useSyncExternalStore` SSR guard and 60s `setInterval` refresh, integrated into the app-shell header center section.

## What Was Built

### Task 1: hose-session.ts — Pure HOSE Phase Logic Module

File: `apps/helios/src/components/layout/hose-session.ts`

Exports:
- `getVNTimeParts(now: Date): VNTimeParts` — extracts `{ h, m, dow }` in Vietnam time (UTC+7) using `Intl.DateTimeFormat.formatToParts`. Avoids Pitfall 5 (raw UTC offset arithmetic fails at midnight boundaries).
- `getCurrentHosePhase(now: Date): HosePhaseResult` — returns `{ isOpen, phase, pct, countdown }` for the current HOSE session based on Vietnam time. Phase boundaries: Pre-market 08:30–09:00, ATO 09:00–09:15, Morning 09:15–11:30, Lunch 11:30–13:00, Afternoon 13:00–14:30, ATC 14:30–14:45, Closed otherwise.
- `HOSE_PHASES` — exported constant array of phase boundary definitions.

Includes `// TODO: Add Vietnamese public holiday awareness (Tết, 30/4, 2/9, etc.) in future` comment as required by CONTEXT.md deferred items.

### Task 2: MarketSessionBar Component + App-Shell Integration

File: `apps/helios/src/components/layout/market-session-bar.tsx`

- `"use client"` directive with `useSyncExternalStore`-based `useMounted` SSR guard (identical pattern to `theme-toggle.tsx`)
- `useState<Date>` initialized to `new Date()`, updated every 60s via `setInterval` cleanup in `useEffect`
- Active state: phase label (`w-20 text-right font-medium text-foreground`) + `ProgressTrack`/`ProgressIndicator` (`w-24 h-1`) + countdown (`w-16`)
- Closed state: `● Closed · Opens in Xh Ym` centered text
- Hidden on `< sm` breakpoint via `hidden sm:flex`
- i18n via `useTranslations("sessionBar")` — `left` and `opensIn` with `{time}` interpolation

File: `apps/helios/src/components/layout/app-shell.tsx`

- Added `import { MarketSessionBar } from "./market-session-bar"`
- Inserted `<MarketSessionBar />` between the left logo block and right controls in the `<header>` — the component's own `flex-1 hidden sm:flex items-center justify-center` handles centering

Files: `messages/en.json` and `messages/vi.json`

- Added `"sessionBar"` top-level key with `preMarket`, `ato`, `morning`, `lunch`, `afternoon`, `atc`, `closed`, `left`, `opensIn` sub-keys
- `left`: `"{time} left"` (EN) / `"còn {time}"` (VI)
- `opensIn`: `"Opens in {time}"` (EN) / `"Mở cửa sau {time}"` (VI)

### Test Results

Wave 0 stubs replaced with 14 real assertions — all pass:

```
Test Files  1 passed (1)
Tests       14 passed (14)
Duration    231ms
```

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 048ee28 | feat(16-04): extract HOSE session logic to hose-session.ts with 14 passing tests |
| 2 | e154c42 | feat(16-04): create MarketSessionBar component and wire into app-shell header |

## Deviations from Plan

**1. [Rule 2 - Enhancement] 14 tests written instead of 12**
- **Found during:** Task 1
- **Reason:** Added 2 bonus midpoint pct assertions (`pct === 50` at midpoint of Pre-market and Afternoon phases) to increase coverage confidence beyond the minimum 12 required stubs
- **Impact:** All 14 pass; no regressions in other test files

None — plan executed as written. The only deviation is the additional 2 tests.

## Known Stubs

None — all functionality is fully implemented with real data sources (system clock via `Date.now()`).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes were introduced. The SSR hydration threat (T-16-04-01) was mitigated via the `useMounted` pattern as specified.

## Self-Check: PASSED

Files verified:
- FOUND: apps/helios/src/components/layout/hose-session.ts
- FOUND: apps/helios/src/components/layout/market-session-bar.tsx
- FOUND: apps/helios/src/components/layout/app-shell.tsx (contains MarketSessionBar)
- FOUND: apps/helios/messages/en.json (contains sessionBar)
- FOUND: apps/helios/messages/vi.json (contains sessionBar)
- FOUND: apps/helios/tests/hose-session.test.ts (14 real assertions, all passing)

Commits verified:
- FOUND: 048ee28 (feat: extract HOSE session logic)
- FOUND: e154c42 (feat: create MarketSessionBar + wire into app-shell)
