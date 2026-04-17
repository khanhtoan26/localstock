---
phase: 07-theme-foundation-visual-identity
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - apps/helios/src/app/globals.css
  - apps/helios/src/app/layout.tsx
  - apps/helios/src/components/charts/price-chart.tsx
  - apps/helios/src/components/charts/sub-panel.tsx
  - apps/helios/src/components/layout/app-shell.tsx
  - apps/helios/src/components/theme/theme-provider.tsx
  - apps/helios/src/components/theme/theme-toggle.tsx
  - apps/helios/src/components/ui/error-state.tsx
  - apps/helios/src/hooks/use-chart-theme.ts
  - apps/helios/src/lib/chart-colors.ts
  - apps/helios/src/lib/utils.ts
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This phase delivers theme foundation (light/dark), chart color system, and layout shell for the Helios frontend. The implementation is well-structured overall: the two-effect split in the chart components (creation vs. re-theming) is a sound pattern that preserves zoom/scroll state on theme toggle. The color token system in `globals.css` and `chart-colors.ts` is correctly separated by theme.

Four warnings and four info items were found. The most impactful warning is a **ResizeObserver memory leak** in both chart components — the observer captures a stale closure over `containerRef.current` and can fire after the chart is destroyed. A second meaningful warning is an **SSR hydration flash** in `ThemeToggle` caused by rendering theme-dependent icons before `resolvedTheme` is resolved on the client. The remaining issues are a fixed-pixel sidebar offset that breaks responsive layout, and a mismatch between the light `chart-bg` CSS token and the `LIGHT_COLORS.chartBg` JavaScript constant.

---

## Warnings

### WR-01: ResizeObserver may fire after chart is removed (memory leak / stale closure)

**File:** `apps/helios/src/components/charts/price-chart.tsx:145-150`
**Also:** `apps/helios/src/components/charts/sub-panel.tsx:128-133`

**Issue:** The `ResizeObserver` callback captures `containerRef.current` via closure and calls `chart.applyOptions(...)` on the local `chart` variable. The cleanup function calls `resizeObserver.disconnect()` and `chart.remove()`, but `disconnect()` does not guarantee that an already-queued callback will not fire. If the resize callback executes after `chart.remove()` has been called, `chart.applyOptions(...)` will throw because lightweight-charts throws on method calls to a removed chart instance.

```tsx
// Current (price-chart.tsx ~145)
const resizeObserver = new ResizeObserver(() => {
  if (containerRef.current) {
    chart.applyOptions({ width: containerRef.current.clientWidth }); // chart may be removed
  }
});

// Fix: guard with a destroyed flag
let destroyed = false;
const resizeObserver = new ResizeObserver(() => {
  if (!destroyed && containerRef.current) {
    chart.applyOptions({ width: containerRef.current.clientWidth });
  }
});

return () => {
  destroyed = true;
  resizeObserver.disconnect();
  chart.remove();
  chartRef.current = null;
  candleRef.current = null;
  volumeRef.current = null;
};
```

Apply the same `destroyed` guard in `sub-panel.tsx`.

---

### WR-02: ThemeToggle renders with incorrect icon on initial client paint (hydration mismatch)

**File:** `apps/helios/src/components/theme/theme-toggle.tsx:11-25`

**Issue:** `resolvedTheme` from `next-themes` is `undefined` during the first client render (before the theme is read from localStorage). The toggle falls through to the `else` branch and renders `<Moon />` unconditionally on both server and first client paint. On the second render after hydration, it switches to the correct icon. This creates a visible flash, and if React's hydration detects the mismatch it will log a warning.

```tsx
// Current
{resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}

// Fix: suppress rendering until theme is known
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    // Render placeholder with the same dimensions to avoid layout shift
    return <Button variant="ghost" size="icon" aria-label="Theme toggle" disabled><Moon className="h-4 w-4 opacity-0" /></Button>;
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label={resolvedTheme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
```

---

### WR-03: Hardcoded `ml-60` sidebar offset breaks layout if sidebar width ever changes

**File:** `apps/helios/src/components/layout/app-shell.tsx:8`

**Issue:** The main content area uses `ml-60` (240px) which is a hardcoded magic number matching the sidebar's assumed width. If the sidebar width changes, this margin must be updated in two places. More critically, there is no responsive handling — on narrow screens the content is pushed 240px right with no breakpoint, making the layout unusable on tablets/mobile without an explicit breakpoint override.

```tsx
// Current
<div className="ml-60">

// Fix: use a CSS variable or a shared constant to keep sidebar width DRY,
// and add a responsive breakpoint so mobile works:
<div className="ml-0 md:ml-60">
// Then ensure the sidebar is hidden on mobile (w-0 or display:none below md).
```

---

### WR-04: Light theme `chart-bg` CSS token does not match `LIGHT_COLORS.chartBg` JS constant

**File:** `apps/helios/src/app/globals.css:89` and `apps/helios/src/lib/chart-colors.ts:38`

**Issue:** The CSS token `--chart-bg` in `:root` is set to `oklch(0.97 0.02 70)` (described as matching `--background`), but `--background` itself is also `oklch(0.97 0.02 70)`. The JavaScript constant `LIGHT_COLORS.chartBg` is hardcoded to `"#faf8f5"` with a comment "matches --background". The approximate hex for `oklch(0.97 0.02 70)` is closer to `#f8f3ec` — not `#faf8f5`. This means the chart canvas background color will subtly differ from the page background in light mode, creating a visible border/seam around the chart.

```ts
// Fix: use the exact computed hex of oklch(0.97 0.02 70).
// Run: CSS.supports / browser DevTools color picker on :root --background
// and set LIGHT_COLORS.chartBg to the precise match.
// Alternatively, read the CSS variable at runtime:
chartBg: getComputedStyle(document.documentElement)
          .getPropertyValue("--background").trim()
// (This requires calling it inside a useEffect or event handler.)
```

---

## Info

### IN-01: `CHART_COLORS` deprecated export still present

**File:** `apps/helios/src/lib/chart-colors.ts:69`

**Issue:** The module exports `CHART_COLORS` marked `@deprecated`, which aliases `DARK_COLORS`. Deprecated exports remain importable and can be accidentally used by future contributors. Since this is a new codebase and the export was never public API, it can be removed now before it accrues callers.

**Fix:** Delete line 69. Confirm no file imports `CHART_COLORS` before removing (a codebase-wide grep shows no usages among the reviewed files).

---

### IN-02: `error-state.tsx` uses hardcoded Tailwind color classes instead of semantic tokens

**File:** `apps/helios/src/components/ui/error-state.tsx:14`

**Issue:** `text-red-700 dark:text-red-400` bypasses the `--destructive` and `--stock-down` semantic tokens established in `globals.css`. This creates a maintenance inconsistency — if the error color is changed in the design tokens, this component will not update.

**Fix:**
```tsx
// Replace:
<AlertCircle className="h-12 w-12 text-red-700 dark:text-red-400" />
// With:
<AlertCircle className="h-12 w-12 text-destructive" />
```

---

### IN-03: `globals.css` mixes two color spaces across light and dark themes

**File:** `apps/helios/src/app/globals.css:51-135`

**Issue:** The light theme uses `oklch(...)` values while the dark theme uses `hsl(...)` values. This is not a bug, but it is an inconsistency that will make future design-token maintenance harder — editors/tools need to reason in two color spaces. The dark theme's financial semantic tokens also switch to raw hex literals (`#22c55e`, `#ef4444`, etc.) at line 129-134, a third format.

**Fix:** Standardize all tokens to one color space. `oklch` is preferred (it is already used for light and is more perceptually uniform for accessibility math). This can be done as a follow-up task, not a blocker.

---

### IN-04: `formatVolume` does not handle negative values

**File:** `apps/helios/src/lib/utils.ts:28-33`

**Issue:** `formatVolume` checks `>= 1_000_000` and `>= 1_000` but does not handle negative inputs. A volume should never be negative from the API, but if corrupt data arrives the output will be a large negative string (`"-1234"`) with no suffix, which may confuse users. The function silently returns `String(value)` for anything below 1000, including negatives.

**Fix:**
```ts
export function formatVolume(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value < 0) return "—";  // guard against corrupt data
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return String(value);
}
```

---

_Reviewed: 2026-04-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
