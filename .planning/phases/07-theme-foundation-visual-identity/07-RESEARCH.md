# Phase 7: Theme Foundation & Visual Identity - Research

**Researched:** 2026-04-17
**Domain:** CSS theming (next-themes + Tailwind v4 + oklch) + canvas chart re-theming (lightweight-charts v5)
**Confidence:** HIGH

## Summary

Phase 7 transforms a dark-mode-only Next.js 16 financial dashboard into a dual-theme app with a warm cream+terracotta default and preserved dark mode. The work is primarily CSS variable restructuring, a small React integration (next-themes provider + toggle), and imperative canvas chart color switching.

The existing codebase has **three separate color systems** that all need attention: (1) shadcn/ui CSS custom properties in `:root` and `.dark` blocks, (2) hardcoded hex constants in `chart-colors.ts` for lightweight-charts canvas rendering, and (3) hardcoded Tailwind `-400` shade classes in `gradeColors` and `error-state.tsx`. The critical bug is that financial semantic tokens (`--stock-up`, `--chart-bg`, etc.) are dark-mode values placed under `:root` — when the dark class is removed, these will render nonsensically on a light background.

The milestone-level research (STACK.md, PITFALLS.md, ARCHITECTURE.md) has already identified the exact library (`next-themes@^0.4.6`), configuration pattern, warm palette values, and all five pitfalls. This phase research validates those findings against the actual codebase, identifies every file that needs modification, and provides the exact code patterns the planner needs.

**Primary recommendation:** Install `next-themes`, wire ThemeProvider in layout.tsx, replace `:root` with warm oklch palette, add warm-light financial tokens alongside `.dark` values, refactor chart-colors.ts to a theme-aware function, and replace all hardcoded color classes with `dark:` variant pairs.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use Claude-inspired warm cream as the base: `oklch(0.97 0.02 70)` for background, with terracotta/orange accent colors. The warmth should be subtle — not a saturated orange theme, but a clearly warm cream that feels professional and inviting.
- **D-02:** Unify color space to oklch for the warm-light theme block (`:root`). The `.dark` block can keep hsl values to minimize diff, but new tokens should be in oklch.
- **D-03:** The warm-light theme is the DEFAULT — new visitors see warm cream, not dark mode. Dark mode is opt-in via toggle.
- **D-04:** Theme toggle is a sun/moon icon button in the header top-right area (inside AppShell header). Standard icon-based toggle — click to switch, no dropdown menu needed for just 2 themes.
- **D-05:** Use `next-themes` with `attribute="class"`, `defaultTheme="claude"`, `enableSystem={false}`. The warm-light theme uses `:root` (no class), dark uses `.dark` class — matching existing Tailwind v4 `@custom-variant dark` setup.
- **D-06:** Preference persists via localStorage (next-themes default behavior). FOUC prevented via next-themes inline blocking script.
- **D-07:** Replace hardcoded Tailwind classes in `gradeColors` (e.g., `text-green-400`) with CSS variables or dual-mode classes (`text-green-700 dark:text-green-400`). All grade colors must pass WCAG AA (4.5:1) against both cream and dark backgrounds.
- **D-08:** Financial semantic tokens (`--stock-up`, `--stock-down`, `--stock-warning`, `--chart-bg`, `--chart-grid`, `--chart-text`) must have values in BOTH `:root` (warm-light) and `.dark` blocks. Current `:root` values are dark-mode colors — this is the #1 bug to fix.
- **D-09:** Stock up/down colors: green/red stays universal (standard financial convention), but use darker shades on cream (green-700, red-700) and brighter on dark (green-400, red-400).
- **D-10:** Refactor `chart-colors.ts` from static `CHART_COLORS` object to a `getChartColors(theme: 'light' | 'dark')` function that returns theme-appropriate colors.
- **D-11:** Use `chart.applyOptions()` + `series.applyOptions()` to update chart colors dynamically when theme changes — do NOT destroy/recreate charts. This preserves zoom/scroll state.
- **D-12:** Create a `useChartTheme()` hook that listens to `resolvedTheme` from next-themes and returns the current chart color set. Chart components consume this hook.

### Agent's Discretion
- Color space unification strategy (oklch vs hsl migration timeline)
- Exact oklch values for warm-light palette — starting from research suggestions, fine-tuned during implementation
- Chart background/grid colors for warm-light theme
- Transition animation on theme switch (instant vs 200ms fade)
- Icon choice for toggle (lucide sun/moon or custom)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| THEME-01 | User can switch between warm-light and dark theme via toggle, preference persists in localStorage | next-themes handles localStorage persistence + class toggle; ThemeToggle component in AppShell header |
| THEME-02 | Page loads without flashing wrong theme (FOUC-free via inline blocking script from next-themes) | next-themes injects synchronous `<script>` before hydration; `suppressHydrationWarning` on `<html>`; `disableTransitionOnChange` prevents flash during toggle |
| THEME-03 | Warm-light palette (cream + terracotta/orange) is default theme for entire app | `:root` block rewritten with oklch warm palette; `defaultTheme="claude"` in ThemeProvider; `value={{ claude: "", dark: "dark" }}` maps theme names to CSS classes |
| THEME-04 | Charts (lightweight-charts canvas) auto re-theme when switching theme via chart.applyOptions() | `getChartColors(theme)` function replaces static CHART_COLORS; `useChartTheme()` hook reads `resolvedTheme`; separate `useEffect` on theme calls `chart.applyOptions()` without destroying chart |
| THEME-05 | Financial color tokens (grade colors, stock-up/down) legible on both theme backgrounds (WCAG AA contrast) | gradeColors refactored to `text-green-700 dark:text-green-400` pattern; financial semantic tokens duplicated into both `:root` and `.dark` with appropriate lightness |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

The `copilot-instructions.md` contains the full project context and stack decisions. Key constraints relevant to this phase:

- **Frontend stack:** Next.js 16, React 19, TypeScript 5, Tailwind v4, shadcn/ui (base-nova style with @base-ui/react) [VERIFIED: copilot-instructions.md + package.json]
- **Icon library:** lucide-react (locked via components.json `iconLibrary: "lucide"`) [VERIFIED: components.json]
- **UI primitives:** @base-ui/react — NOT Radix UI [VERIFIED: components.json `style: "base-nova"`]
- **No CSS-in-JS:** styled-components, emotion are excluded [VERIFIED: copilot-instructions.md anti-stack]
- **Package manager:** npm for frontend [VERIFIED: package.json lockfile]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next-themes | ^0.4.6 | Theme state management + FOUC prevention | De-facto standard for Next.js theming; 2kB; injects blocking `<script>` before hydration; handles localStorage + class toggle [VERIFIED: STACK.md research, confirmed current Apr 2026] |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 1.8.0 | Sun/Moon icons for toggle | ThemeToggle component; `Sun` and `Moon` icons [VERIFIED: package.json] |
| lightweight-charts | ^5.1.0 | Financial charts (canvas) | Already used; `chart.applyOptions()` API for live color updates [VERIFIED: price-chart.tsx, sub-panel.tsx] |
| tailwindcss | ^4 | Utility-first CSS | `@custom-variant dark` already configured in globals.css [VERIFIED: globals.css line 5] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| next-themes | Hand-rolled theme context | next-themes solves FOUC with inline script — hand-rolling this correctly is error-prone (hydration mismatches). Use next-themes. |
| `dark:` variant classes for gradeColors | CSS custom properties (`--grade-a-text`) | CSS vars are more DRY but require touching globals.css + every consumer. `dark:` variants are simpler for 5 grade entries and match existing Tailwind patterns. Use `dark:` variants per D-07. |
| `disableTransitionOnChange` | 200ms CSS transition | Instant switch avoids any "flash" during toggle. Aesthetic preference — recommend `disableTransitionOnChange` to start, can add transitions later. |

**Installation:**
```bash
cd apps/helios && npm install next-themes@^0.4.6
```

## Architecture Patterns

### Files to Create
```
apps/helios/src/
├── components/
│   └── theme/
│       ├── theme-provider.tsx    # Wraps next-themes ThemeProvider with app config
│       └── theme-toggle.tsx      # Sun/Moon icon button, client component
└── hooks/
    └── use-chart-theme.ts        # Returns chart colors based on resolvedTheme
```

### Files to Modify (Complete Inventory)
```
apps/helios/src/
├── app/
│   ├── globals.css               # MAJOR: Rewrite :root with warm oklch palette, add financial tokens to .dark
│   └── layout.tsx                # MAJOR: Remove className="dark", wrap with ThemeProvider, add suppressHydrationWarning
├── components/
│   ├── layout/
│   │   └── app-shell.tsx         # Add ThemeToggle to header area (currently no header)
│   ├── charts/
│   │   ├── price-chart.tsx       # Add theme dependency, useEffect for applyOptions
│   │   └── sub-panel.tsx         # Same as price-chart.tsx
│   ├── rankings/
│   │   └── grade-badge.tsx       # No change needed (consumes gradeColors from utils.ts)
│   └── ui/
│       └── error-state.tsx       # Replace text-red-400 with text-red-700 dark:text-red-400
├── lib/
│   ├── chart-colors.ts           # MAJOR: Refactor from const to getChartColors(theme) function
│   └── utils.ts                  # Update gradeColors with dark: variant pairs
```

### Pattern 1: ThemeProvider Wiring (next-themes)
**What:** Wrap the app with next-themes ThemeProvider in layout.tsx.
**When to use:** Root layout, single instance.

```tsx
// Source: STACK.md research + next-themes docs
// apps/helios/src/components/theme/theme-provider.tsx
"use client";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="claude"
      themes={["claude", "dark"]}
      value={{ claude: "", dark: "dark" }}
      enableSystem={false}
      disableTransitionOnChange
      storageKey="localstock-theme"
    >
      {children}
    </NextThemesProvider>
  );
}
```

Key configuration details [VERIFIED: STACK.md]:
- `value={{ claude: "", dark: "dark" }}` — maps theme name "claude" → no class (`:root` applies), "dark" → `.dark` class
- `enableSystem={false}` — warm-light is default for all users, not OS-driven
- `disableTransitionOnChange` — prevents visual flash during toggle
- `storageKey="localstock-theme"` — scoped to avoid collisions on localhost

```tsx
// apps/helios/src/app/layout.tsx
import { ThemeProvider } from "@/components/theme/theme-provider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <QueryProvider>
            <AppShell>{children}</AppShell>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### Pattern 2: Theme Toggle Component
**What:** Sun/Moon icon button using existing Button component + lucide-react icons.
**When to use:** In AppShell header area.

```tsx
// Source: Codebase pattern (button.tsx has size="icon" variant)
// apps/helios/src/components/theme/theme-toggle.tsx
"use client";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // resolvedTheme is undefined during SSR — render placeholder
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(resolvedTheme === "dark" ? "claude" : "dark")}
      aria-label={resolvedTheme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {resolvedTheme === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  );
}
```

### Pattern 3: AppShell Header Addition
**What:** AppShell currently has no header — just a sidebar + main area. Need to add a header strip for the toggle.
**Current state:** [VERIFIED: app-shell.tsx]

```tsx
// Current: <main className="ml-60 p-6">{children}</main>
// Need to add a header area for ThemeToggle
// apps/helios/src/components/layout/app-shell.tsx
import { Sidebar } from "./sidebar";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="ml-60">
        <header className="flex items-center justify-end px-6 py-3 border-b border-border">
          <ThemeToggle />
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
```

### Pattern 4: Chart Color Refactoring
**What:** Replace static CHART_COLORS constant with a function returning theme-appropriate colors.
**When to use:** chart-colors.ts + useChartTheme hook.

```typescript
// apps/helios/src/lib/chart-colors.ts
export interface ChartColorSet {
  candleUp: string;
  candleDown: string;
  volumeUp: string;
  volumeDown: string;
  sma20: string;
  ema12: string;
  bbBands: string;
  macdLine: string;
  macdSignal: string;
  macdHistPositive: string;
  macdHistNegative: string;
  rsiLine: string;
  rsiOverbought: string;
  rsiOversold: string;
  chartBg: string;
  chartGrid: string;
  chartText: string;
}

const LIGHT_COLORS: ChartColorSet = {
  candleUp: "#15803d",       // green-700 for cream bg
  candleDown: "#b91c1c",     // red-700 for cream bg
  volumeUp: "#15803d40",     // 25% opacity
  volumeDown: "#b91c1c40",
  sma20: "#2563eb",          // blue-600
  ema12: "#7c3aed",          // violet-600
  bbBands: "#6b728080",      // gray
  macdLine: "#2563eb",
  macdSignal: "#ea580c",     // orange-600
  macdHistPositive: "#15803d",
  macdHistNegative: "#b91c1c",
  rsiLine: "#7c3aed",
  rsiOverbought: "#b91c1c",
  rsiOversold: "#15803d",
  chartBg: "#faf8f5",        // warm cream (matches --background)
  chartGrid: "#e7e0d5",      // warm light gray
  chartText: "#57534e",      // stone-600
};

const DARK_COLORS: ChartColorSet = {
  candleUp: "#22c55e",
  candleDown: "#ef4444",
  volumeUp: "#22c55e40",
  volumeDown: "#ef444440",
  sma20: "#3b82f6",
  ema12: "#a855f7",
  bbBands: "#6b728080",
  macdLine: "#3b82f6",
  macdSignal: "#f97316",
  macdHistPositive: "#22c55e",
  macdHistNegative: "#ef4444",
  rsiLine: "#a855f7",
  rsiOverbought: "#ef4444",
  rsiOversold: "#22c55e",
  chartBg: "#0f172a",
  chartGrid: "#1e293b",
  chartText: "#94a3b8",
};

export function getChartColors(theme: "light" | "dark"): ChartColorSet {
  return theme === "dark" ? DARK_COLORS : LIGHT_COLORS;
}

// Keep backward compat export during migration — remove after all consumers updated
export const CHART_COLORS = DARK_COLORS;
```

### Pattern 5: useChartTheme Hook
**What:** Connects next-themes resolvedTheme to chart color set.
**When to use:** In PriceChart and SubPanel components.

```typescript
// apps/helios/src/hooks/use-chart-theme.ts
"use client";
import { useTheme } from "next-themes";
import { getChartColors, type ChartColorSet } from "@/lib/chart-colors";

export function useChartTheme(): ChartColorSet {
  const { resolvedTheme } = useTheme();
  // resolvedTheme can be undefined during SSR — default to light
  return getChartColors(resolvedTheme === "dark" ? "dark" : "light");
}
```

### Pattern 6: Chart Component Theme Integration
**What:** Add a separate useEffect that updates chart colors on theme change WITHOUT destroying the chart.
**Critical detail:** The data useEffect creates the chart + series. A second useEffect depends on theme and calls applyOptions on the existing chart ref.

```tsx
// Key pattern for price-chart.tsx (and similarly sub-panel.tsx)
// Add ALONGSIDE existing data useEffect — do NOT merge them

const chartColors = useChartTheme();

// Existing effect: creates chart, sets data (depends on prices, indicators)
useEffect(() => {
  // ... existing chart creation code, but use chartColors for initial colors
  // Store series refs for theme updates
}, [prices, indicators, chartColors]); // NOTE: chartColors triggers full recreate

// OR BETTER: Split into create + theme-update effects
// Effect 1: Create chart (depends on data)
// Effect 2: Update colors only (depends on chartColors)
// See "Don't Hand-Roll" section for the recommended split pattern
```

**Recommended approach for chart theme update (applyOptions without recreate):**

The chart components currently destroy and recreate the chart in their single useEffect. The cleanest approach per D-11 is to:
1. Keep the data useEffect creating the chart (it already stores `chartRef`)
2. Add a SECOND useEffect that runs when `chartColors` changes, calling `chart.applyOptions()` on the stored ref
3. Store series refs (candleSeries, volumeSeries, etc.) to call `series.applyOptions()` too

```tsx
// Second useEffect — runs when theme changes
const seriesRefs = useRef<{ candle: ISeriesApi<"Candlestick"> | null; volume: ISeriesApi<"Histogram"> | null }>({ candle: null, volume: null });

useEffect(() => {
  const chart = chartRef.current;
  if (!chart) return;
  
  chart.applyOptions({
    layout: {
      background: { color: chartColors.chartBg },
      textColor: chartColors.chartText,
    },
    grid: {
      vertLines: { color: chartColors.chartGrid },
      horzLines: { color: chartColors.chartGrid },
    },
  });
  
  if (seriesRefs.current.candle) {
    seriesRefs.current.candle.applyOptions({
      upColor: chartColors.candleUp,
      downColor: chartColors.candleDown,
      borderUpColor: chartColors.candleUp,
      borderDownColor: chartColors.candleDown,
      wickUpColor: chartColors.candleUp,
      wickDownColor: chartColors.candleDown,
    });
  }
  // ... same for volume, indicators
}, [chartColors]);
```

### Anti-Patterns to Avoid
- **Don't add `.claude` class to `<html>`** — warm-light is the default (`:root`), so "claude" theme maps to NO class. Adding `.claude` would require duplicating all CSS variables into a third block. [VERIFIED: STACK.md D-05]
- **Don't use `getComputedStyle()` to read CSS variables for canvas charts** — This introduces layout-dependent reads, race conditions with class toggling, and doesn't work during SSR. Pass hex values directly via the `getChartColors()` function. [VERIFIED: PITFALLS.md #3]
- **Don't destroy/recreate charts on theme toggle** — Loses zoom/scroll state. Use `chart.applyOptions()` + `series.applyOptions()` for live updates. [VERIFIED: D-11]
- **Don't use `enableSystem={true}`** — Per D-05, warm-light is the forced default. System detection would surprise dark-OS users on first visit. [VERIFIED: D-05]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Theme state + persistence | Custom React context + localStorage logic | `next-themes` (2kB) | FOUC prevention requires a synchronous inline `<script>` injected before `</head>` — `next-themes` handles this correctly; hand-rolling it leads to hydration mismatches [VERIFIED: PITFALLS.md #1] |
| FOUC prevention script | `useEffect(() => { document.documentElement.classList... })` | next-themes built-in blocking script | `useEffect` runs AFTER paint — user sees flash. next-themes script runs synchronously before React hydrates [VERIFIED: PITFALLS.md #1] |
| Dark variant detection | `@media (prefers-color-scheme: dark)` | `@custom-variant dark (&:is(.dark *))` (already exists) | App uses class-based toggling, not media queries [VERIFIED: globals.css line 5] |
| Contrast checking | Manual eyeballing | Verify oklch lightness values or use WebAIM tool | oklch lightness channel directly maps to perceived brightness — L < 0.5 is dark, L > 0.5 is light [ASSUMED] |

**Key insight:** The only truly custom code in this phase is (1) the warm oklch palette values, (2) the chart color refactoring, and (3) the `useChartTheme` hook. Everything else is library configuration.

## Common Pitfalls

### Pitfall 1: Financial Token Inversion
**What goes wrong:** Current `globals.css` has `--stock-up: #22c55e` and `--chart-bg: #0f172a` in `:root` — these are dark-mode values. When `.dark` is removed (warm-light activates), every component reading `var(--chart-bg)` gets a dark navy color on a cream page.
**Why it happens:** The app was always dark, so `:root` and `.dark` were functionally equivalent.
**How to avoid:** Audit every CSS variable. Financial semantic tokens must appear in BOTH `:root` (warm-light values) and `.dark` (current values). The `:root` financial tokens must be rewritten to warm-light values.
**Warning signs:** Any component that looks inverted — dark elements on light background or vice versa.
[VERIFIED: globals.css lines 122-129, PITFALLS.md #2]

### Pitfall 2: Canvas Charts Don't Follow CSS Changes
**What goes wrong:** Theme class toggles → Tailwind/shadcn components update correctly → canvas charts remain dark navy on a cream page.
**Why it happens:** `lightweight-charts` renders to `<canvas>` with pixel-level colors set at `createChart()`. The `useEffect` dependency array `[prices, indicators]` doesn't include theme.
**How to avoid:** Add `useChartTheme()` hook. Use `chart.applyOptions()` and `series.applyOptions()` in a theme-dependent useEffect. Do NOT destroy/recreate charts.
**Warning signs:** Toggle theme → charts don't change color. Volume bars disappear (alpha too low on new background).
[VERIFIED: price-chart.tsx, sub-panel.tsx, PITFALLS.md #3]

### Pitfall 3: Hardcoded -400 Shade Colors Fail Contrast on Cream
**What goes wrong:** `text-green-400` (#4ade80) on cream (#faf8f5) = ~2.0:1 contrast ratio. `text-yellow-400` on cream ≈ 1.5:1. Grade badges become unreadable.
**Why it happens:** `-400` shades are designed for dark backgrounds. On light backgrounds, need `-600` or `-700`.
**How to avoid:** Replace with `text-green-700 dark:text-green-400` dual-mode pattern. Same for error-state.tsx `text-red-400`.
**Warning signs:** `text-{color}-400` appearing in any component without a `dark:` counterpart.
[VERIFIED: utils.ts lines 37-42, error-state.tsx line 14, PITFALLS.md #4]

### Pitfall 4: Warm Orange Accent Fails Body Text Contrast
**What goes wrong:** Terracotta primary (~`oklch(0.70 0.14 45)`) on cream background ≈ 3.0-4.0:1 contrast — passes for large text but fails WCAG AA for body text (4.5:1).
**Why it happens:** Warm palettes are tonally compressed. Orange-on-cream looks fine visually but fails numbers.
**How to avoid:** Use the primary/terracotta for button backgrounds (foreground is white/cream — high contrast) and interactive elements, NOT for body text. For text on cream, use the `--foreground` token (warm near-black, high contrast).
**Warning signs:** Any orange/terracotta text smaller than 18pt on cream background.
[VERIFIED: PITFALLS.md #5]

### Pitfall 5: suppressHydrationWarning Placement
**What goes wrong:** `suppressHydrationWarning` must be on the `<html>` element only. Placing it elsewhere (or forgetting it) causes React hydration error: `"Prop 'className' did not match"`.
**Why it happens:** next-themes modifies `<html>` className before React hydrates. React detects the mismatch.
**How to avoid:** Always add `suppressHydrationWarning` to the `<html>` tag in layout.tsx. This is a documented, officially blessed escape hatch for next-themes.
**Warning signs:** Console error about className mismatch on page load.
[VERIFIED: STACK.md line 185]

### Pitfall 6: Volume Bar Alpha Values on Cream Background
**What goes wrong:** Current volume colors use `40` hex alpha (25% opacity): `#22c55e40`. On dark background this gives a subtle tint. On cream, 25% green on cream may be nearly invisible.
**Why it happens:** Alpha transparency works differently on light vs dark backgrounds.
**How to avoid:** Use different alpha values per theme. Light theme may need `60` (37.5%) or higher. Test visually.
**Warning signs:** Volume bars disappear or become invisible when switching to light theme.
[VERIFIED: chart-colors.ts lines 5-6, PITFALLS.md #3]

## Code Examples

### CSS Variables: Complete Warm-Light `:root` Block
```css
/* Source: STACK.md research + D-01/D-02 decisions */
:root {
  --background:           oklch(0.97 0.02 70);   /* cream ≈ #F5F0E8 */
  --foreground:           oklch(0.22 0.02 60);   /* warm near-black */
  --card:                 oklch(0.99 0.01 70);
  --card-foreground:      oklch(0.22 0.02 60);
  --popover:              oklch(0.99 0.01 70);
  --popover-foreground:   oklch(0.22 0.02 60);
  --primary:              oklch(0.70 0.14 45);   /* terracotta ≈ #D97757 */
  --primary-foreground:   oklch(0.99 0.01 70);
  --secondary:            oklch(0.93 0.02 70);
  --secondary-foreground: oklch(0.28 0.02 60);
  --muted:                oklch(0.93 0.02 70);
  --muted-foreground:     oklch(0.50 0.02 60);
  --accent:               oklch(0.90 0.04 55);
  --accent-foreground:    oklch(0.25 0.03 45);
  --destructive:          oklch(0.577 0.245 27);
  --border:               oklch(0.88 0.02 70);
  --input:                oklch(0.88 0.02 70);
  --ring:                 oklch(0.70 0.14 45);
  --chart-1:              oklch(0.62 0.18 145);  /* green for charts */
  --chart-2:              oklch(0.55 0.20 260);  /* blue for charts */
  --chart-3:              oklch(0.75 0.16 85);   /* yellow for charts */
  --chart-4:              oklch(0.70 0.14 45);   /* orange for charts */
  --chart-5:              oklch(0.58 0.22 27);   /* red for charts */
  --radius: 0.625rem;
  --sidebar:              oklch(0.96 0.015 70);
  --sidebar-foreground:   oklch(0.22 0.02 60);
  --sidebar-primary:      oklch(0.70 0.14 45);
  --sidebar-primary-foreground: oklch(0.99 0.01 70);
  --sidebar-accent:       oklch(0.93 0.02 70);
  --sidebar-accent-foreground: oklch(0.25 0.02 60);
  --sidebar-border:       oklch(0.88 0.02 70);
  --sidebar-ring:         oklch(0.70 0.14 45);

  /* Financial semantic tokens — warm-light values */
  --stock-up:       oklch(0.62 0.18 145);  /* green-700 equivalent, ~6:1 on cream */
  --stock-down:     oklch(0.58 0.22 27);   /* red-700 equivalent, ~5.4:1 on cream */
  --stock-warning:  oklch(0.75 0.16 85);   /* yellow-600 equivalent */
  --chart-bg:       oklch(0.97 0.02 70);   /* matches --background */
  --chart-grid:     oklch(0.90 0.015 70);  /* subtle warm grid */
  --chart-text:     oklch(0.45 0.02 60);   /* readable on cream */
}
```

### Financial Tokens in `.dark` Block
```css
/* Add to .dark block in globals.css — currently these only exist in :root with dark values */
.dark {
  /* ... existing shadcn tokens unchanged ... */

  /* Financial semantic tokens — dark theme values (moved from :root) */
  --stock-up: #22c55e;
  --stock-down: #ef4444;
  --stock-warning: #eab308;
  --chart-bg: #0f172a;
  --chart-grid: #1e293b;
  --chart-text: #94a3b8;
}
```

### gradeColors Dual-Mode Pattern
```typescript
// Source: D-07 decision
// apps/helios/src/lib/utils.ts
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  B: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30",
  C: "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
  F: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
};
```

### error-state.tsx Fix
```tsx
// Source: D-07 decision pattern applied to error-state
<AlertCircle className="h-12 w-12 text-red-700 dark:text-red-400" />
```

## Complete File Modification Inventory

| File | Change Type | What Changes | Risk |
|------|------------|--------------|------|
| `app/globals.css` | MAJOR | Rewrite `:root` with warm oklch palette; add financial tokens to `.dark`; potentially update `@custom-variant` selector | HIGH — affects every page |
| `app/layout.tsx` | MAJOR | Remove `className="dark"`, add `suppressHydrationWarning`, wrap with ThemeProvider | HIGH — root layout |
| `lib/chart-colors.ts` | MAJOR | Refactor from `const CHART_COLORS` to `getChartColors(theme)` function with light+dark sets | MEDIUM — 2 consumers |
| `components/charts/price-chart.tsx` | MODERATE | Add `useChartTheme`, store series refs, add theme useEffect with `applyOptions` | MEDIUM — chart behavior |
| `components/charts/sub-panel.tsx` | MODERATE | Same as price-chart.tsx | MEDIUM — chart behavior |
| `components/layout/app-shell.tsx` | MODERATE | Add header with ThemeToggle | LOW — layout addition |
| `lib/utils.ts` | MINOR | Update gradeColors to dual-mode classes | LOW — 5 entries |
| `components/ui/error-state.tsx` | MINOR | `text-red-400` → `text-red-700 dark:text-red-400` | LOW — single line |

**New files:**
| File | Purpose |
|------|---------|
| `components/theme/theme-provider.tsx` | next-themes wrapper with app config |
| `components/theme/theme-toggle.tsx` | Sun/Moon toggle button |
| `hooks/use-chart-theme.ts` | Bridges next-themes resolvedTheme → chart color set |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@media (prefers-color-scheme)` for dark mode | Class-based dark mode via `@custom-variant` (Tailwind v4) | Tailwind v4 (2024) | Class toggle gives user control, works with next-themes |
| hsl color space for CSS variables | oklch color space | Tailwind v4 default (2024) | Perceptually uniform — lightness channel directly maps to perceived brightness |
| Hand-rolled theme script in `<head>` | next-themes inline blocking script | next-themes v0.4+ | Handles all edge cases (SSR, localStorage, class injection) |
| Chart recreate on theme change | `chart.applyOptions()` for live updates | lightweight-charts v4+ | Preserves zoom/scroll state, no flicker |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | oklch lightness < 0.5 is dark, > 0.5 is light (for contrast checking) | Don't Hand-Roll | Low — well-established color science, just not verified with a specific tool in this session |
| A2 | Light chart colors (#15803d green-700, #b91c1c red-700) have sufficient contrast on cream (#faf8f5) | Code Examples / Chart Colors | Medium — ratios cited from PITFALLS.md research (~6:1 and ~5.4:1) but not independently verified with a contrast checker |
| A3 | `next-themes@^0.4.6` has no compatibility issues with Next.js 16.2.4 + React 19.2.4 | Standard Stack | Low — STACK.md confirms "No known Next 16 issues (Apr 2026)" |
| A4 | Volume alpha `40` (25%) will be nearly invisible on cream, `60` (37.5%) is better | Pitfall 6 | Low — easily testable during implementation, visual tuning |

## Open Questions

1. **Exact oklch values for sidebar in warm-light theme**
   - What we know: Background is `oklch(0.97 0.02 70)`, sidebar should be slightly different
   - What's unclear: Should sidebar be slightly darker or slightly lighter than main bg?
   - Recommendation: Use `oklch(0.96 0.015 70)` (slightly darker) — agent's discretion per CONTEXT.md

2. **`@custom-variant` selector: `&:is(.dark *)` vs `&:where(.dark, .dark *)`**
   - What we know: Current globals.css uses `(&:is(.dark *))`. STACK.md research suggests `(&:where(.dark, .dark *))` which also matches the `<html>` element itself
   - What's unclear: Whether the current selector causes issues (it doesn't match `<html class="dark">` directly, only its children)
   - Recommendation: Keep `(&:is(.dark *))` since shadcn/ui generated it and it's working. The `body` already inherits from `<html>`, so all visible elements match via `*`. Only matters if applying `dark:` directly on `<html>` element — unlikely.

3. **Transition animation on theme switch**
   - What we know: `disableTransitionOnChange` prevents any CSS transition during toggle (instant switch)
   - What's unclear: Whether instant switch feels jarring
   - Recommendation: Start with `disableTransitionOnChange` (prevents flash artifacts). If user feedback says it's jarring, add a 150ms fade later — this is trivially reversible by removing the prop.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual visual testing + browser DevTools |
| Config file | N/A — no test framework installed |
| Quick run command | `cd apps/helios && npm run dev` (visual inspection) |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| THEME-01 | Toggle switches theme, persists across reload | manual | Open app → click toggle → reload → verify same theme | ❌ Manual |
| THEME-02 | No FOUC on load (10x hard refresh Slow 3G) | manual | DevTools → Network → Slow 3G → hard refresh × 10 → no flashes | ❌ Manual |
| THEME-03 | Warm-light is default (clear localStorage, reload) | manual | DevTools → Application → localStorage → clear `localstock-theme` → reload → cream bg visible | ❌ Manual |
| THEME-04 | Charts re-theme on toggle without page reload | manual | On stock page → toggle theme → charts repaint within 200ms → zoom state preserved | ❌ Manual |
| THEME-05 | Grade badges + financial colors legible on both themes | manual | Visual check + optional contrast ratio check via DevTools | ❌ Manual |

### Sampling Rate
- **Per task commit:** `npm run dev` + visual check of affected component
- **Per wave merge:** Full walkthrough: Rankings page + Stock detail page + Market page in both themes
- **Phase gate:** All 5 manual test scenarios pass on both themes

### Wave 0 Gaps
- No automated test framework exists for the frontend — all validation is manual
- Consider `npm run build` as a build-time smoke test (catches TypeScript errors and import issues)
- WCAG contrast could be automated with `axe-core` but this is out of scope for this phase

## Security Domain

This phase is purely visual (CSS variables, theme toggle, chart colors). No authentication, data access, input processing, or API changes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | N/A — no user input beyond toggle click |
| V6 Cryptography | No | N/A |

No security concerns for this phase. The theme toggle stores a string ("claude" or "dark") in localStorage — no sensitive data.

## Sources

### Primary (HIGH confidence)
- `apps/helios/src/app/globals.css` — Current CSS variables, financial token placement (lines 51-129) — verified in this session
- `apps/helios/src/app/layout.tsx` — Hardcoded `className="dark"` on line 17 — verified in this session
- `apps/helios/src/lib/chart-colors.ts` — All 17 hex constants, static export — verified in this session
- `apps/helios/src/lib/utils.ts` — `gradeColors` lines 36-42 with hardcoded `-400` shades — verified in this session
- `apps/helios/src/components/charts/price-chart.tsx` — Chart creation pattern with `createChart()` + `CHART_COLORS` — verified in this session
- `apps/helios/src/components/charts/sub-panel.tsx` — Same chart pattern — verified in this session
- `apps/helios/src/components/layout/app-shell.tsx` — No header, just sidebar + main — verified in this session
- `apps/helios/src/components/ui/error-state.tsx` — `text-red-400` on line 14 — verified in this session
- `apps/helios/package.json` — Current deps: lightweight-charts ^5.1.0, lucide-react 1.8.0, next 16.2.4, react 19.2.4 — verified in this session
- `apps/helios/components.json` — style: "base-nova", iconLibrary: "lucide" — verified in this session
- `.planning/research/STACK.md` — next-themes configuration, warm palette values, ThemeProvider wiring — verified in this session
- `.planning/research/PITFALLS.md` — 5 theme-related pitfalls with mitigation strategies — verified in this session
- `.planning/research/ARCHITECTURE.md` — Theme system architecture, component inventory — verified in this session

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` — next-themes v0.4.6 compatibility with Next 16 / React 19 claim (from Apr 2026 research)
- `.planning/research/PITFALLS.md` — WCAG contrast ratios for green-700/red-700 on cream (cited as ~6:1 and ~5.4:1)

### Tertiary (LOW confidence)
- None — all findings verified against codebase or milestone research

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — next-themes is the only new dependency, well-researched in STACK.md
- Architecture: HIGH — every file to modify has been inspected, patterns come from existing codebase + milestone research
- Pitfalls: HIGH — all 6 pitfalls verified against actual code (not hypothetical)

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days — stable domain, no fast-moving dependencies)
