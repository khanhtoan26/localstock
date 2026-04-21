---
phase: 09-academic-learning-page-glossary-data
plan: 01
subsystem: learn-glossary-data
tags: [glossary, data-module, sidebar-navigation, educational-content]
dependency_graph:
  requires: []
  provides: [glossary-data-module, learn-sidebar-nav, input-component]
  affects: [phase-10-glossary-linking, plan-02-learn-pages]
tech_stack:
  added: []
  patterns: [typed-record-data-module, nfd-diacritic-normalization]
key_files:
  created:
    - apps/helios/src/lib/glossary.ts
    - apps/helios/src/components/ui/input.tsx
  modified:
    - apps/helios/src/components/layout/sidebar.tsx
decisions:
  - "Created Input component manually instead of shadcn CLI due to SSL cert issue (equivalent output)"
  - "Organized glossary entries by category using separate Record objects merged into single export"
metrics:
  duration: 508s
  completed: "2026-04-21T02:23:10Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
requirements:
  - LEARN-01
  - LEARN-02
---

# Phase 09 Plan 01: Glossary Data Module & Sidebar Navigation Summary

Typed glossary data module with 25 Vietnamese educational entries across 3 categories (technical/fundamental/macro), NFD+Đ diacritic-insensitive search normalization, sidebar "Học" nav item, and shadcn Input component for Plan 02 search UI.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create glossary data module with 25 typed entries and helpers | `a60ede6` | `apps/helios/src/lib/glossary.ts` |
| 2 | Add sidebar navigation and install Input component | `6dfc9ad` | `apps/helios/src/components/layout/sidebar.tsx`, `apps/helios/src/components/ui/input.tsx` |

## What Was Built

### Task 1: Glossary Data Module

Created `apps/helios/src/lib/glossary.ts` — single source of truth for all learn pages and Phase 10 glossary linking:

- **Types:** `GlossaryCategory` union type (`"technical" | "fundamental" | "macro"`) and `GlossaryEntry` interface with `id`, `term`, `termEn`, `aliases`, `category`, `shortDef`, `content`, and optional `formula`
- **25 entries total:**
  - **Technical (10):** RSI, MACD, SMA, EMA, Bollinger Bands, OBV, VWAP, Stochastic, ADX, ATR
  - **Fundamental (10):** P/E, P/B, EPS, ROE, ROA, D/E, Revenue Growth, Profit Growth, Market Cap, Current Ratio
  - **Macro (5):** CPI, GDP Growth, Interest Rate, Exchange Rate, Money Supply M2
- **Content quality:** Each entry has 150-400 words of Vietnamese educational text with structured sections (Định nghĩa, Cách tính, Cách đọc/Diễn giải, Ví dụ thực tế, Lưu ý)
- **Helper functions:** `getEntriesByCategory()`, `getAllEntries()`, `normalizeForSearch()`
- **Search normalization:** NFD decomposition + manual `đ/Đ → d` replacement + lowercase — handles Vietnamese diacritics correctly

### Task 2: Sidebar Navigation & Input Component

- Added `{ href: "/learn", label: "Học", icon: BookOpen }` to sidebar `navItems` array
- Created `apps/helios/src/components/ui/input.tsx` — shadcn-compatible Input component (manual creation due to CLI SSL cert issue, identical API)

## Verification Results

All automated checks passed:
- ✅ Total entries: 25 (PASS)
- ✅ Technical: 10 (PASS)
- ✅ Fundamental: 10 (PASS)
- ✅ Macro: 5 (PASS)
- ✅ Diacritic match: "chỉ số" normalizes same as "chi so" (PASS)
- ✅ Đ handling: "Đường" normalizes same as "duong" (PASS)
- ✅ All entries have content >100 chars (PASS)
- ✅ All entries have aliases (PASS)
- ✅ `npm run build` passes clean (no TypeScript errors)
- ✅ Sidebar contains BookOpen, "/learn", "Học" (PASS)
- ✅ Input component file exists (PASS)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] shadcn CLI SSL certificate error**
- **Found during:** Task 2
- **Issue:** `npx shadcn@latest add input` failed with "self-signed certificate in certificate chain" error
- **Fix:** Created Input component manually following shadcn base-nova pattern (identical to CLI output)
- **Files created:** `apps/helios/src/components/ui/input.tsx`
- **Commit:** `6dfc9ad`

## Known Stubs

None — all entries contain full Vietnamese educational content, all helpers are functional.

## Self-Check: PASSED

- ✅ `apps/helios/src/lib/glossary.ts` exists
- ✅ `apps/helios/src/components/ui/input.tsx` exists
- ✅ `apps/helios/src/components/layout/sidebar.tsx` exists
- ✅ `.planning/phases/09-academic-learning-page-glossary-data/09-01-SUMMARY.md` exists
- ✅ Commit `a60ede6` found in git log
- ✅ Commit `6dfc9ad` found in git log
