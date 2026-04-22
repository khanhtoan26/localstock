---
phase: 12-admin-console-ui
plan: "01"
subsystem: frontend-admin-foundation
tags: [admin, types, i18n, tanstack-query, sidebar, toast, shadcn]
dependency_graph:
  requires: []
  provides: [admin-types, admin-query-hooks, admin-i18n, admin-nav, toast-provider, checkbox-component]
  affects: [12-02]
tech_stack:
  added: [sonner]
  patterns: [tanstack-query-mutations-with-invalidation, conditional-refetch-interval]
key_files:
  created:
    - apps/helios/src/components/ui/checkbox.tsx
    - apps/helios/src/components/ui/sonner.tsx
  modified:
    - apps/helios/src/lib/types.ts
    - apps/helios/src/lib/queries.ts
    - apps/helios/src/components/layout/app-shell.tsx
    - apps/helios/src/components/layout/sidebar.tsx
    - apps/helios/messages/en.json
    - apps/helios/messages/vi.json
    - apps/helios/package.json
    - apps/helios/package-lock.json
decisions:
  - Used sonner-based toast (shadcn's default for base-nova style) instead of custom useToast hook
  - Placed Toaster as sibling to content div inside AppShell root
metrics:
  duration: 3m20s
  completed: "2026-04-22T04:54:26Z"
  tasks: 2/2
  files_changed: 10
---

# Phase 12 Plan 01: Admin Console Foundation Summary

**One-liner:** Complete admin data layer with 6 TypeScript types, 9 TanStack Query hooks (including conditional polling), i18n keys for EN/VI, sidebar navigation with Shield icon, and Toaster/Checkbox shadcn components.

## What Was Done

### Task 1: Install shadcn components, add Toaster provider, add admin types, add i18n keys
**Commit:** `a51ff7d`

- Installed shadcn `checkbox` component (base-nova style, uses @base-ui/react)
- Installed shadcn `sonner` toast component (theme-aware via next-themes)
- Added `<Toaster />` to `AppShell` component for app-wide toast notifications
- Added 6 admin TypeScript interfaces to `types.ts`: `TrackedStock`, `TrackedStocksResponse`, `AdminJob`, `AdminJobDetail`, `AdminJobsResponse`, `TriggerResponse`
- Added complete admin i18n keys to `en.json` (nav, tabs, stocks, pipeline, jobs, toast sections)
- Added complete admin i18n keys to `vi.json` with Vietnamese translations

### Task 2: Add TanStack Query hooks and Admin sidebar navigation
**Commit:** `6cee52b`

- Added 9 TanStack Query hooks/mutations to `queries.ts`:
  - **Stock Management:** `useTrackedStocks()`, `useAddStock()`, `useRemoveStock()`
  - **Pipeline Triggers:** `useTriggerAdminCrawl()`, `useTriggerAdminAnalyze()`, `useTriggerAdminScore()`, `useTriggerAdminPipeline()`
  - **Job Monitor:** `useAdminJobs()`, `useAdminJobDetail()`
- All mutations invalidate relevant query caches on success via `useQueryClient`
- `useAdminJobs` implements conditional `refetchInterval` — polls at 3s when jobs are running/pending, stops when all complete
- Added Admin nav item with `Shield` icon to sidebar, linking to `/admin`

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- **Lint:** All modified files pass lint cleanly (pre-existing warnings in unrelated files: price-chart.tsx, sub-panel.tsx, glossary components)
- **Build:** `npm run build` exits 0, TypeScript compilation successful, all pages generated

## Decisions Made

1. **Sonner-based toast:** shadcn base-nova style generates sonner-based Toaster (not custom useToast hook). Uses `next-themes` for automatic theme awareness. Toast calls use `toast()` from `sonner` library.
2. **Toaster placement:** Added as last child of AppShell root div, sibling to sidebar and content area. This ensures toasts appear above all content.

## Self-Check: PASSED

All files verified present. Both commits (a51ff7d, 6cee52b) confirmed in git log.
