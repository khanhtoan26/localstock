---
phase: 14-visual-foundation
plan: "01"
subsystem: helios-ui-theme
tags: [css-variables, typography, color-palette, neutral-theme, source-sans-3]
dependency_graph:
  requires: []
  provides: [neutral-css-palette, source-sans-3-font, monochromatic-charts]
  affects: [all-components-using-text-primary, all-components-using-bg-primary, chart-indicators, grade-badges, score-breakdown]
tech_stack:
  added: [Source Sans 3 (Google Font via next/font)]
  patterns: [CSS variable neutral palette, font variable chain next/font → @theme inline → font-sans]
key_files:
  created: []
  modified:
    - apps/helios/src/app/layout.tsx
    - apps/helios/src/app/globals.css
    - apps/helios/src/lib/chart-colors.ts
    - apps/helios/src/lib/utils.ts
    - apps/helios/src/components/stock/score-breakdown.tsx
decisions:
  - "Used Source Sans 3 variable font (200-900 weight range) — single file, all weights available"
  - "Near-black primary hsl(60 2% 15%) for light mode — matches Claude Desktop warm neutral aesthetic"
  - "Warm light gray primary hsl(48 10% 90%) for dark mode — high contrast on dark background"
  - "Stone-600 (#57534e) for chart indicators — neutral warm gray visible on cream background"
  - "Stone-500 Tailwind classes for grade B and technical score — natural neutral intermediate"
metrics:
  duration: 3m 4s
  completed: "2026-04-24T01:09:10Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 5
---

# Phase 14 Plan 01: Neutral Palette + Source Sans 3 Typography Summary

**One-liner:** Replace blue primary palette with Claude Desktop-inspired warm neutral tones (near-black/warm gray) and load Source Sans 3 with Vietnamese subset via next/font/google.

## Tasks Completed

### Task 1: Source Sans 3 font loading + neutral CSS variable palette ✅
**Commit:** `0d9996d`
**Files:** `layout.tsx`, `globals.css`

- Added `Source_Sans_3` import from `next/font/google` with `subsets: ['latin', 'vietnamese']`, `display: 'swap'`, `variable: '--font-sans'`
- Applied `sourceSans.variable` to `<html>` className for CSS variable chain propagation
- Replaced all 10 blue `hsl(210 70.9% 51.6%)` CSS variable values in `:root` and `.dark` blocks:
  - `:root --primary` → `hsl(60 2% 15%)` (warm near-black)
  - `:root --ring` → `hsl(60 3% 40%)` (medium warm gray)
  - `:root --chart-2` → `hsl(60 2% 35%)` (warm gray)
  - `:root --sidebar-primary` → `hsl(60 2% 15%)` (match primary)
  - `:root --sidebar-ring` → `hsl(60 3% 40%)` (match ring)
  - `.dark --primary` → `hsl(48 10% 90%)` (warm light gray)
  - `.dark --primary-foreground` → `hsl(60 2.7% 14.5%)` (dark bg as text)
  - `.dark --ring` → `hsl(48 5% 55%)` (warm gray for dark)
  - `.dark --sidebar-primary` → `hsl(48 10% 90%)` (match primary)
  - `.dark --sidebar-ring` → `hsl(48 5% 55%)` (match ring)
- Removed hardcoded `font-family: system-ui, -apple-system, sans-serif` from body rule
- Preserved all background, foreground, card, secondary, muted, accent, destructive, border, input tokens unchanged (per D-02)
- Preserved all financial tokens (`--stock-up/down/warning`, `--chart-bg/grid/text`) unchanged (per D-09)
- Preserved `@theme inline` block entirely unchanged

### Task 2: Hardcoded blue cleanup in chart-colors, grades, and score breakdown ✅
**Commit:** `1f45777`
**Files:** `chart-colors.ts`, `utils.ts`, `score-breakdown.tsx`

- `chart-colors.ts` LIGHT_COLORS: `sma20` and `macdLine` → `"#57534e"` (stone-600)
- `chart-colors.ts` DARK_COLORS: `sma20` and `macdLine` → `"#a8a29e"` (stone-400)
- `utils.ts` gradeColors B: `bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30` → `bg-stone-500/20 text-stone-700 dark:text-stone-400 border-stone-500/30`
- `score-breakdown.tsx` technical_score color: `bg-blue-500` → `bg-stone-500`
- All other chart colors (candleUp/Down, ema12, bbBands, macdSignal, etc.) unchanged
- All other grade colors (A, C, D, F) unchanged
- All other dimension colors (emerald, amber, violet) unchanged

### Task 3: Visual verification checkpoint ⏳
**Status:** Awaiting human verification — not yet executed

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| Zero `hsl(210 70.9% 51.6%)` in globals.css | ✅ PASS |
| Zero `#2563eb` / `#3b82f6` in chart-colors.ts | ✅ PASS |
| Zero `bg-blue-500` / `text-blue-` / `border-blue-` in utils.ts + score-breakdown.tsx | ✅ PASS |
| `Source_Sans_3` import in layout.tsx | ✅ PASS |
| No `system-ui` in globals.css | ✅ PASS |
| Neutral primary `hsl(60 2% 15%)` present | ✅ PASS |
| Dark neutral primary `hsl(48 10% 90%)` present | ✅ PASS |
| `npm run build` succeeds | ✅ PASS |

## Known Stubs

None — all values are final production values, no placeholders.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. Font loading uses `next/font/google` which self-hosts at build time (no runtime Google requests).

## Self-Check: PASSED

All 5 modified files exist, SUMMARY.md created, both task commits (0d9996d, 1f45777) verified in git log.
