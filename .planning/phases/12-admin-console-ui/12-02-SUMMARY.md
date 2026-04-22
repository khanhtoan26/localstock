---
phase: 12-admin-console-ui
plan: "02"
subsystem: frontend-admin-components
tags: [admin, tabs, stock-table, pipeline-control, job-monitor, status-badge]
dependency_graph:
  requires: [12-01]
  provides: [admin-page, stock-table-component, pipeline-control-component, job-monitor-component, status-badge-component]
  affects: []
tech_stack:
  added: []
  patterns: [controlled-tabs, checkbox-selection-with-useMemo-sync, expandable-table-rows, mutation-error-handling-409]
key_files:
  created:
    - apps/helios/src/components/admin/status-badge.tsx
    - apps/helios/src/components/admin/stock-table.tsx
    - apps/helios/src/components/admin/pipeline-control.tsx
    - apps/helios/src/components/admin/job-monitor.tsx
    - apps/helios/src/app/admin/page.tsx
  modified: []
decisions:
  - Used useState toggle for job detail expansion instead of Collapsible to avoid invalid DOM nesting in table
  - Used color-mix() CSS function for StatusBadge custom token colors with opacity
  - Wrapped stocks array in useMemo to fix react-hooks/exhaustive-deps lint warning
metrics:
  duration: 3m56s
  completed: "2026-04-22T05:01:52Z"
  tasks: 3/3
  files_changed: 5
---

# Phase 12 Plan 02: Admin Console UI Components Summary

**One-liner:** Complete admin console with 3-tab page (/admin), stock management table with add/remove, pipeline trigger controls with checkbox selection, and job monitor with expandable detail rows and status badges.

## What Was Done

### Task 1: Create status-badge.tsx and stock-table.tsx
**Commit:** `9da72ff`

- Created `StatusBadge` component rendering 4 job statuses with semantic colors:
  - `completed` → green via `--stock-up` CSS token
  - `failed` → red via Badge `variant="destructive"`
  - `running` → amber via `--stock-warning` CSS token
  - `pending` → muted via Badge `variant="secondary"`
- Created `StockTable` component with:
  - Inline add form (Input + Button) with `<form>` for Enter key support
  - Symbol validation: `toUpperCase()` + regex `^[A-Z0-9]+$`
  - Remove button per row with ghost variant
  - Loading state (8 Skeleton rows), error state (ErrorState), empty state (EmptyState)
  - Toast feedback via sonner for add/remove/error operations

### Task 2: Create pipeline-control.tsx and job-monitor.tsx
**Commit:** `dd979bd`

- Created `PipelineControl` component with:
  - `useTrackedStocks()` for stock list (TanStack Query deduplicates with StockTable)
  - Checkbox selection with `useState<Set<string>>` and `useMemo` sync (prevents stale state)
  - Header checkbox with checked/indeterminate states
  - 4 action buttons: Crawl, Analyze (disabled when 0 selected), Score, Run Full Pipeline (always enabled)
  - Spinner animation on pending mutations
  - 409 conflict error handling with `operationLocked` toast
  - `onOperationTriggered` callback for tab switching on success
- Created `JobMonitor` component with:
  - `useAdminJobs()` with automatic 3s polling when active jobs exist
  - `StatusBadge` for each job row
  - `formatDuration` helper (seconds → "Xs" or "Xm Ys")
  - Expandable rows via `useState` toggle (chose over Collapsible for valid table DOM)
  - `JobDetailPanel` sub-component fetching `useAdminJobDetail(jobId)` on expand
  - Result JSON display with `JSON.stringify(detail.result, null, 2)`
  - Error display in destructive-colored `<pre>` block

### Task 3: Create admin/page.tsx
**Commit:** `098b005`

- Created `/admin` page with 3-tab layout using controlled `Tabs` component
- Tabs: Stocks, Pipeline, Jobs with `variant="line"` styling
- Controlled state via `useState("stocks")` with `value`/`onValueChange`
- PipelineControl receives `onOperationTriggered={() => setActiveTab("jobs")}` for auto-switching
- Page title "Admin Console" via i18n `t("title")`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrapped stocks array in useMemo**
- **Found during:** Task 2
- **Issue:** `react-hooks/exhaustive-deps` lint warning — `stocks` variable created new array reference each render, causing `validSelected` useMemo to recompute unnecessarily
- **Fix:** Wrapped `const stocks = useMemo(() => data?.stocks ?? [], [data?.stocks])` 
- **Files modified:** pipeline-control.tsx
- **Commit:** dd979bd

**2. [Rule 3 - Blocking] Used useState toggle instead of Collapsible for job detail rows**
- **Found during:** Task 2
- **Issue:** @base-ui/react Collapsible wraps content in `<div>` panel which creates invalid HTML inside `<tbody>` (no `<div>` allowed between `<tr>` elements)
- **Fix:** Used simple `useState<number | null>` toggle with conditional `<TableRow>` rendering instead of Collapsible component
- **Files modified:** job-monitor.tsx
- **Commit:** dd979bd

**3. [Rule 3 - Blocking] Adapted CSS token usage for StatusBadge**
- **Found during:** Task 1
- **Issue:** Plan specified `hsl(var(--stock-up))` but CSS variables store full color values (`hsl(...)` or `#hex`), not HSL channels — wrapping in `hsl()` would produce invalid `hsl(hsl(...))`
- **Fix:** Used `color-mix(in srgb, var(--stock-up) 10%, transparent)` for backgrounds and `var(--stock-up)` directly for text color
- **Files modified:** status-badge.tsx
- **Commit:** 9da72ff

## Verification Results

- **Lint:** All admin files pass lint cleanly (pre-existing warnings in unrelated files only)
- **Build:** `npm run build` exits 0 — TypeScript compiles, all pages generated including `/admin`
- **Route:** `/admin` appears in build output route list

## Decisions Made

1. **useState over Collapsible for job rows:** @base-ui/react Collapsible renders wrapper `<div>` panels that break valid `<table>` DOM structure. Simple conditional rendering is cleaner.
2. **color-mix() for status colors:** CSS variables contain full color values, so `color-mix(in srgb, ...)` provides cross-theme opacity control.
3. **useMemo for stocks array:** Prevents stale reference issues in dependent useMemo for selection sync.

## Self-Check: PASSED

All 5 files verified present. All 3 commits (9da72ff, dd979bd, 098b005) confirmed in git log.
