---
phase: 07-theme-foundation-visual-identity
plan: "02"
subsystem: frontend-theme
tags: [theme, lightweight-charts, chart-colors, react-hooks, applyOptions]
dependency_graph:
  requires:
    - phase: 07-theme-foundation-visual-identity
      provides: [theme-provider, warm-oklch-palette, next-themes integration]
  provides: [theme-aware-charts, chart-color-tokens, useChartTheme-hook]
  affects: [apps/helios/src/lib/chart-colors.ts, apps/helios/src/hooks/use-chart-theme.ts, apps/helios/src/components/charts/price-chart.tsx, apps/helios/src/components/charts/sub-panel.tsx]
tech_stack:
  added: []
  patterns: [split-useEffect for chart theme re-painting, series refs for applyOptions, getChartColors theme factory, useChartTheme bridge hook]
key_files:
  created:
    - apps/helios/src/hooks/use-chart-theme.ts
  modified:
    - apps/helios/src/lib/chart-colors.ts
    - apps/helios/src/components/charts/price-chart.tsx
    - apps/helios/src/components/charts/sub-panel.tsx
    - apps/helios/src/components/theme/theme-provider.tsx
    - apps/helios/src/components/theme/theme-toggle.tsx
key_decisions:
  - "Split-useEffect pattern: chart creation effect excludes chartColors from deps to preserve zoom/scroll; second effect depends only on chartColors and calls applyOptions"
  - "Volume and MACD histogram require setData (not applyOptions) to update per-bar colors — lightweight-charts per-bar color is a data field, not a series option"
  - "RSI price lines (createPriceLine at 70/30 thresholds) cannot be updated via applyOptions — accepted limitation since threshold line colors are semantically stable across themes"
  - "ThemeProvider theme name changed from 'claude' to 'light' — empty string as a DOMTokenList value triggers a DOMException in browsers"
  - "Light volume alpha is 60 (37.5%) vs dark 40 (25%) to compensate for lower contrast on cream background"
patterns_established:
  - "useChartTheme(): bridge hook that translates resolvedTheme (next-themes) to a typed ChartColorSet — reusable for any future chart component"
  - "getChartColors(theme): pure function returning static color set objects — stable references, no re-render risk"
  - "Series refs pattern: store ISeriesApi refs alongside chartRef to enable in-place color updates without chart destruction"
requirements_completed: [THEME-04]
duration: ~25min
completed: "2026-04-17"
---

# Phase 7 Plan 02: Theme-Aware Charts Summary

**ChartColorSet interface + getChartColors(theme) factory + useChartTheme hook + split-effect re-painting in PriceChart and SubPanel — charts update colors instantly on theme toggle without destroying the chart or losing zoom/scroll state.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-17T10:06:50Z
- **Completed:** 2026-04-17T10:11:28Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 6

## Accomplishments

- Refactored `chart-colors.ts` from a single static object to a typed interface + theme factory with separate LIGHT_COLORS (green-700/cream bg, 60-alpha volume) and DARK_COLORS (existing values unchanged)
- Created `useChartTheme()` hook that bridges `resolvedTheme` from next-themes to a `ChartColorSet`, defaulting to light on SSR
- Updated both chart components with the split-effect pattern: creation effect omits `chartColors` from its deps (preserving zoom/scroll), second effect depends only on `chartColors` and calls `chart.applyOptions()` + `series.applyOptions()` + `series.setData()` for histograms
- Fixed a ThemeProvider bug where `value={{ claude: "" }}` caused a browser DOMException on theme toggle — renamed theme to `"light"` throughout

## Task Commits

1. **Task 1: Refactor chart-colors.ts and create useChartTheme hook** - `c492205` (feat)
2. **Task 2: Update PriceChart and SubPanel with live theme re-painting** - `2d6107a` (feat)
3. **Task 2 (deviation fix): Fix ThemeProvider DOMToken error** - `6b6f828` (fix)

Human verification (Task 3 checkpoint): approved — all 5 THEME requirements confirmed visually.

## Files Created/Modified

- `apps/helios/src/hooks/use-chart-theme.ts` — new hook; reads `resolvedTheme` from next-themes, returns `ChartColorSet` via `getChartColors()`
- `apps/helios/src/lib/chart-colors.ts` — refactored; exports `ChartColorSet` interface, `LIGHT_COLORS`, `DARK_COLORS`, `getChartColors(theme)`, and backward-compat `CHART_COLORS` alias
- `apps/helios/src/components/charts/price-chart.tsx` — split effects; series refs for `candleRef` and `volumeRef`; live applyOptions on theme change
- `apps/helios/src/components/charts/sub-panel.tsx` — split effects; `seriesRefs` object for hist/line1/line2; live applyOptions for MACD and RSI on theme change
- `apps/helios/src/components/theme/theme-provider.tsx` — fix: `value={{ light: "", dark: "dark" }}` (renamed from `claude`)
- `apps/helios/src/components/theme/theme-toggle.tsx` — fix: toggle cycles between `"light"` and `"dark"` (renamed from `"claude"`)

## Decisions Made

1. **Split-effect pattern over recreation:** Keeping `chartColors` out of the creation effect's dependency array means the chart is never destroyed on theme toggle. The second effect (deps: `[chartColors, prices]` / `[chartColors, type, indicators]`) calls `chart.applyOptions()` and `series.applyOptions()` to update colors in-place. This is D-11 compliance — zoom and scroll position survive theme switches.

2. **Histogram per-bar colors need `setData`:** Volume bars and MACD histogram bars each carry an individual `color` field in their data objects. lightweight-charts does not expose a series-level option to update these colors after creation. The theme re-paint effect calls `series.setData()` with recomputed color values. This is a framework constraint, not a design choice.

3. **RSI price lines: accepted limitation.** `createPriceLine()` returns an object without a public `applyOptions` API in the lightweight-charts v5 type definitions. The overbought (70) and oversold (30) threshold lines keep their creation-time colors across theme switches. The colors are semantically correct in both themes (red = overbought, green = oversold) — only the specific shade differs.

4. **ThemeProvider theme name `"claude"` → `"light"`:** The original Plan 01 used `value={{ claude: "" }}` to map the warm-light theme to an empty CSS class (no `.claude` selector needed). However, passing an empty string as a DOMTokenList value (`classList.add("")`) is forbidden by the browser spec and throws a `DOMException`. Renaming the theme to `"light"` with `value={{ light: "" }}` is equivalent — it still maps to no class — but does not produce an invalid token.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed empty DOMToken error from ThemeProvider `claude` theme name**
- **Found during:** Task 3 (human-verify checkpoint) — browser console showed DOMException on theme toggle
- **Issue:** `next-themes` calls `document.documentElement.classList.add(value)` where `value` is the mapped string. `value={{ claude: "" }}` maps the "claude" theme to an empty string `""`. Passing `""` to `classList.add()` raises `DOMException: The token provided must not be empty`.
- **Fix:** Changed theme name from `"claude"` to `"light"` in ThemeProvider `value` prop and in ThemeToggle's toggle logic. The mapping `value={{ light: "", dark: "dark" }}` preserves the same behavior (warm-light = no class, dark = `.dark` class) without the invalid token.
- **Files modified:** `apps/helios/src/components/theme/theme-provider.tsx`, `apps/helios/src/components/theme/theme-toggle.tsx`
- **Verification:** Theme toggle worked without console errors; confirmed by human verification checkpoint
- **Committed in:** `6b6f828`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Fix was essential for theme toggle to function at all. No scope creep. The Plan 01 SUMMARY.md records the original `claude` decision — it was superseded by this fix.

## Issues Encountered

None beyond the ThemeProvider DOMToken bug documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 5 THEME requirements (THEME-01 through THEME-05) confirmed visually by human verification
- `useChartTheme()` hook is a stable, reusable primitive — any future chart component can import it
- `CHART_COLORS` backward-compat export remains for any consumer not yet migrated to the hook
- The split-effect pattern is established and should be followed if additional chart components are added in future phases

---
*Phase: 07-theme-foundation-visual-identity*
*Completed: 2026-04-17*
