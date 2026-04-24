---
phase: 15-sidebar-float-collapse
plan: "02"
subsystem: helios-ui
tags: [sidebar, floating, icon-rail, overlay-panel, layout, animation]
dependency_graph:
  requires: ["15-01 (useSidebarState hook, Tooltip component)"]
  provides: ["FloatingSidebar component", "Updated AppShell with ml-14 layout"]
  affects: ["app-shell.tsx", "all pages via layout change"]
tech_stack:
  added: []
  patterns: ["CSS transform toggle for slide animation", "Conditional tooltip portal rendering", "Split nav groups with bottom-pinned admin"]
key_files:
  created:
    - apps/helios/src/components/layout/floating-sidebar.tsx
  modified:
    - apps/helios/src/components/layout/app-shell.tsx
  deleted:
    - apps/helios/src/components/layout/sidebar.tsx
decisions:
  - "Admin group pinned to bottom of icon rail with border-t separator (D-04/D-05)"
  - "Auto-collapse sidebar after clicking any nav link in expanded panel"
  - "AI Stock Agent text hardcoded in overlay header (no i18n key exists for tagline)"
metrics:
  duration: "3m 12s"
  completed: "2026-04-24T04:10:28Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
  files_deleted: 1
---

# Phase 15 Plan 02: Floating Sidebar + Layout Restructuring Summary

Floating sidebar with always-visible icon rail (w-14) and slide-in overlay panel (w-60) using 180ms ease-out CSS transform, replacing old fixed w-60 sidebar

## What Was Done

### Task 1: Create FloatingSidebar component (b2d2d29)

Created `floating-sidebar.tsx` (161 lines) with two-part structure:

**Icon Rail (always visible):**
- Fixed `w-14` strip on left side (`z-30`)
- Main nav group (Rankings, Market, Learn) at top with icon buttons
- Admin nav pinned to bottom with `border-t` separator
- Each icon wrapped in Tooltip — tooltips only render portal when `collapsed` is true
- Active state detection via `pathname.startsWith(href)`
- Click toggles sidebar expand/collapse

**Overlay Panel (CSS transform toggle):**
- Fixed `w-60` panel positioned at `left-14` (`z-40`)
- Always in DOM, hidden via `-translate-x-full` / shown via `translate-x-0`
- `transition-transform duration-[180ms] ease-out` for smooth slide animation
- Contains "LocalStock / AI Stock Agent" header + full nav links with labels
- `aria-hidden={collapsed}` for accessibility
- Auto-collapses after clicking any nav link

**Design decisions enforced:**
- D-02: No logo/branding in icon rail
- D-03: No badge indicators
- D-07: No backdrop overlay
- D-08: 180ms ease-out slide animation

### Task 2: Update AppShell and delete old sidebar (fae5d4b)

- Changed import from `Sidebar` to `FloatingSidebar`
- Changed content offset from `ml-60` to `ml-14`
- Deleted old `sidebar.tsx` (44 lines removed)
- Verified no orphan imports remain

## Key Links Verified

| From | To | Via |
|------|-----|-----|
| floating-sidebar.tsx | use-sidebar-state.ts | `import { useSidebarState }` |
| floating-sidebar.tsx | tooltip.tsx | `import { Tooltip, TooltipTrigger, ... }` |
| app-shell.tsx | floating-sidebar.tsx | `import { FloatingSidebar }` |
| app-shell.tsx | layout | `ml-14` class on content wrapper |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `npx tsc --noEmit`: ✅ Exit 0
- FloatingSidebar exported and imported: ✅
- Layout uses ml-14 not ml-60: ✅
- Old sidebar.tsx deleted: ✅
- No orphan imports to sidebar: ✅
- No stubs found: ✅

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | b2d2d29 | feat(15-02): create FloatingSidebar with icon rail and overlay panel |
| 2 | fae5d4b | feat(15-02): update AppShell to use FloatingSidebar, delete old sidebar |
