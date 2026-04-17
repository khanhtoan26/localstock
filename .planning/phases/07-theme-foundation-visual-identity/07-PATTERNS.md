# Phase 7: Theme Foundation & Visual Identity - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 8 (2 new, 6 modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/hooks/use-chart-theme.ts` (NEW) | hook | event-driven | `src/lib/queries.ts` (hook pattern) | role-match |
| `src/components/theme-toggle.tsx` (NEW) | component | event-driven | `src/components/charts/timeframe-selector.tsx` | exact |
| `src/app/globals.css` (MODIFY) | config | — | self (existing CSS variable blocks) | exact |
| `src/app/layout.tsx` (MODIFY) | provider | request-response | `src/lib/query-provider.tsx` | exact |
| `src/lib/chart-colors.ts` (MODIFY) | utility | transform | self (refactor from const → function) | exact |
| `src/lib/utils.ts` (MODIFY) | utility | — | self (gradeColors update) | exact |
| `src/components/ui/error-state.tsx` (MODIFY) | component | — | self (color class fix) | exact |
| `src/components/layout/app-shell.tsx` (MODIFY) | component | — | self (add header) | exact |

## Pattern Assignments

### `src/hooks/use-chart-theme.ts` (NEW — hook, event-driven)

**Analog:** `src/lib/queries.ts` (custom hook pattern) + `src/lib/query-provider.tsx` ("use client" pattern)

This is the first custom hook in the `hooks/` directory. The codebase has no `src/hooks/` directory yet, but `components.json` aliases define `"hooks": "@/hooks"`. The closest hook-like patterns are the TanStack Query wrappers in `queries.ts`.

**"use client" directive pattern** (from `src/lib/query-provider.tsx`, line 1):
```typescript
"use client";
```
All files using React hooks (useState, useEffect) or browser APIs must have this directive. This is established across `query-provider.tsx`, `sidebar.tsx`, `price-chart.tsx`, `sub-panel.tsx`, `stock-table.tsx`, `timeframe-selector.tsx`.

**Import path alias pattern** (from `src/lib/queries.ts`, lines 2-3):
```typescript
import { apiFetch } from "./api";
import type { TopScoresResponse, ... } from "./types";
```
Convention: use `@/` prefix for cross-directory imports, `./` for same-directory imports.

**Hook export pattern** (from `src/lib/queries.ts`, lines 16-22):
```typescript
export function useTopScores(limit = 20) {
  return useQuery({
    queryKey: ["scores", "top", limit],
    queryFn: () => apiFetch<TopScoresResponse>(`/api/scores/top?limit=${limit}`),
    staleTime: 5 * 60 * 1000,
  });
}
```
Convention: named export, `use` prefix, function (not arrow), returns hook result directly.

**Key for new hook:** `useChartTheme()` should follow the same naming and export style — named export function, "use client" directive, returns data directly (the chart color set).

---

### `src/components/theme-toggle.tsx` (NEW — component, event-driven)

**Analog:** `src/components/charts/timeframe-selector.tsx` (small interactive component using Button + events)

**Imports pattern** (from `src/components/charts/timeframe-selector.tsx`, lines 1-2):
```typescript
"use client";
import { Button } from "@/components/ui/button";
```
Convention: "use client" first, then UI component imports via `@/components/ui/` path.

**Icon usage pattern** (from `src/components/layout/sidebar.tsx`, lines 3-4):
```typescript
import { BarChart3, Globe } from "lucide-react";
// Used as: <Icon className="h-4 w-4" />
```
Convention: Named icon imports from `lucide-react`, sizing via `className="h-4 w-4"`.

**Button with icon variant** (from `src/components/ui/button.tsx`, lines 28-29):
```typescript
// size variants include:
icon: "size-8",
"icon-sm": "size-7 rounded-[min(var(--radius-md),12px)]",
```
The `size="icon"` variant exists and should be used for the toggle button.

**Button ghost variant** (from `src/components/ui/button.tsx`, lines 17-18):
```typescript
ghost:
  "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
```
ThemeToggle should use `variant="ghost"` + `size="icon"` to match sidebar navigation style.

**Component interface pattern** (from `src/components/charts/timeframe-selector.tsx`, lines 4-22):
```typescript
export interface TimeframeOption {
  label: string;
  days: number;
}

// ...

export function TimeframeSelector({
  selectedDays,
  onChange,
}: TimeframeSelectorProps) {
```
Convention: interface defined before component, named export function (not default export).

**Note:** ThemeToggle has NO props — it reads theme from `useTheme()` hook internally. So it's even simpler than TimeframeSelector. Pattern:
```tsx
"use client";
export function ThemeToggle() { ... }
```

---

### `src/app/layout.tsx` (MODIFY — provider wrapping)

**Analog:** Self + `src/lib/query-provider.tsx` (provider wrapping pattern)

**Provider wrapper pattern** (from `src/lib/query-provider.tsx`, lines 1-18):
```typescript
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            retry: 1,
          },
        },
      })
  );
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```
Convention: "use client" provider wrappers accept `{ children: React.ReactNode }`, wrap children in provider component. ThemeProvider follows the same pattern.

**Current layout.tsx nesting** (lines 16-24):
```tsx
<html lang="vi" className="dark">
  <body>
    <QueryProvider>
      <AppShell>{children}</AppShell>
    </QueryProvider>
  </body>
</html>
```
ThemeProvider wraps QueryProvider (outermost body child). Remove `className="dark"`, add `suppressHydrationWarning` to `<html>`.

---

### `src/app/globals.css` (MODIFY — CSS variable restructuring)

**Analog:** Self (existing `:root` and `.dark` block structure)

**CSS variable declaration pattern** (lines 51-84, `:root` block):
```css
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  /* ... */
  --radius: 0.625rem;
}
```
Convention: `:root` uses oklch color space for shadcn tokens. One variable per line, commented hex equivalents in `.dark` block.

**Dark block pattern** (lines 86-119):
```css
.dark {
  /* Financial dark theme — UI-SPEC.md contract */
  --background: hsl(222.2 84% 4.9%);        /* #020817 */
  --foreground: hsl(210 40% 98%);            /* #f8fafc */
  /* ... */
}
```
Convention: `.dark` uses hsl color space with hex comments. Per D-02, new warm-light `:root` tokens use oklch, `.dark` keeps hsl to minimize diff.

**Financial token pattern** (lines 121-129):
```css
/* Financial semantic tokens — UI-SPEC.md */
:root {
  --stock-up: #22c55e;
  --stock-down: #ef4444;
  --stock-warning: #eab308;
  --chart-bg: #0f172a;
  --chart-grid: #1e293b;
  --chart-text: #94a3b8;
}
```
**BUG:** These are dark-mode values in `:root`. Must be split: warm-light values in `:root` (oklch), dark values in `.dark` (hex). This second `:root` block should be merged into the primary `:root` block.

**Tailwind integration pattern** (lines 1-5):
```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));
```
Convention: imports first, then `@custom-variant`, then `@theme inline`, then `:root`, then `.dark`, then `@layer base`.

---

### `src/lib/chart-colors.ts` (MODIFY — refactor const to function)

**Analog:** Self (current structure) + `src/lib/utils.ts` (typed export pattern)

**Current structure** (lines 1-20):
```typescript
/** Chart color constants from UI-SPEC.md — single source of truth for all charts */
export const CHART_COLORS = {
  candleUp: "#22c55e",
  candleDown: "#ef4444",
  /* ... */
  chartBg: "#0f172a",
  chartGrid: "#1e293b",
  chartText: "#94a3b8",
} as const;
```
Refactor to: export `interface ChartColorSet`, two `const` objects (`LIGHT_COLORS`, `DARK_COLORS`), export `function getChartColors(theme)`, keep backward-compat `CHART_COLORS` during migration.

**Typed export pattern** (from `src/lib/utils.ts`, lines 36-42):
```typescript
/** Grade color map — returns Tailwind classes for badge styling */
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  /* ... */
};
```
Convention: JSDoc comment, explicit type annotation on exports.

**Consumers to update:** `price-chart.tsx` (line 10) and `sub-panel.tsx` (line 9) both import `CHART_COLORS`:
```typescript
import { CHART_COLORS } from "@/lib/chart-colors";
```
After refactor, these will use `useChartTheme()` hook instead.

---

### `src/lib/utils.ts` (MODIFY — gradeColors dual-mode)

**Analog:** Self (update in-place)

**Current gradeColors** (lines 36-42):
```typescript
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  B: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  C: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  F: "bg-red-500/20 text-red-400 border-red-500/30",
};
```
Pattern: Replace `text-{color}-400` with `text-{color}-700 dark:text-{color}-400` for WCAG contrast on cream.

**Tailwind dark: variant pattern** (from `src/components/ui/button.tsx`, line 18):
```typescript
"dark:hover:bg-muted/50"
```
Convention: `dark:` prefix for dark-mode overrides is already used in shadcn/ui components.

---

### `src/components/ui/error-state.tsx` (MODIFY — color class fix)

**Analog:** Self (single line change)

**Current** (line 14):
```tsx
<AlertCircle className="h-12 w-12 text-red-400" />
```
Change to: `text-red-700 dark:text-red-400` (same dual-mode pattern as gradeColors).

**Lucide icon import pattern** (line 1):
```typescript
import { AlertCircle } from "lucide-react";
```

---

### `src/components/layout/app-shell.tsx` (MODIFY — add header)

**Analog:** Self + `src/components/layout/sidebar.tsx` (layout structure)

**Current AppShell** (lines 1-10):
```typescript
import { Sidebar } from "./sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar />
      <main className="ml-60 p-6">{children}</main>
    </div>
  );
}
```
Convention: Server component (no "use client"), simple wrapper, uses semantic CSS variable classes (`bg-background`, `text-foreground`), Tailwind utility classes.

**Sidebar border pattern** (from `src/components/layout/sidebar.tsx`, line 15):
```tsx
<aside className="fixed left-0 top-0 h-screen w-60 border-r border-border bg-card flex flex-col">
```
Convention: borders use `border-border` token. Header should use `border-b border-border`.

---

## Shared Patterns

### "use client" Directive
**Source:** All interactive components (`query-provider.tsx`, `sidebar.tsx`, `price-chart.tsx`, `sub-panel.tsx`, `stock-table.tsx`, `timeframe-selector.tsx`)
**Apply to:** `theme-toggle.tsx`, `use-chart-theme.ts`, `theme-provider.tsx` (any file that uses React hooks or browser APIs)

```typescript
"use client";
```
Must be the FIRST line in the file, before any imports.

### Import Path Aliases
**Source:** `components.json` aliases + all existing files
**Apply to:** All new/modified files

```
@/components/...  — component imports
@/lib/...         — utility/library imports
@/hooks/...       — hook imports (defined in components.json but no hooks dir exists yet)
```

### CSS Variable Token Usage
**Source:** All components (`app-shell.tsx`, `sidebar.tsx`, `macro-cards.tsx`, `stock-table.tsx`)
**Apply to:** All component files — never use raw colors, always use semantic tokens

```tsx
// ✅ Correct — uses CSS variable tokens
className="bg-background text-foreground"
className="text-muted-foreground"
className="border-border"

// ❌ Wrong — hardcoded colors (what we're fixing in this phase)
className="text-red-400"    // Needs dark: variant
style={{ color: "#0f172a" }} // Needs theme awareness
```

### Lucide Icon Pattern
**Source:** `src/components/layout/sidebar.tsx` (lines 3-4), `src/components/ui/error-state.tsx` (line 1)
**Apply to:** `theme-toggle.tsx`

```typescript
import { Sun, Moon } from "lucide-react";
// Usage:
<Sun className="h-4 w-4" />
<Moon className="h-4 w-4" />
```

### Component Export Convention
**Source:** All components in codebase
**Apply to:** All new components

```typescript
// Named exports (NOT default exports)
export function ThemeToggle() { ... }
export function ThemeProvider({ children }: ...) { ... }
export function useChartTheme() { ... }
```

### Chart Ref + useEffect Cleanup Pattern
**Source:** `src/components/charts/price-chart.tsx` (lines 19-21, 144-148)
**Apply to:** Chart components consuming `useChartTheme`

```typescript
const containerRef = useRef<HTMLDivElement>(null);
const chartRef = useRef<IChartApi | null>(null);

useEffect(() => {
  // ... create chart ...
  chartRef.current = chart;
  return () => {
    resizeObserver.disconnect();
    chart.remove();
    chartRef.current = null;
  };
}, [prices, indicators]);
```
The new theme-update `useEffect` reads from `chartRef.current` — it does NOT create/destroy charts.

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `src/hooks/use-chart-theme.ts` | hook | event-driven | No `hooks/` directory exists yet — this is the first hook | Use RESEARCH.md pattern (simple 5-line hook). Follow `queries.ts` naming convention and `"use client"` pattern from other client files. |
| `src/components/theme-toggle.tsx` | component | event-driven | No theme components exist yet | Use `timeframe-selector.tsx` as structural analog (small client component using Button + event handler). Research has exact code. |

**Note:** While these are "no analog" in the strict sense (no identical file type exists), the codebase has strong enough conventions (named exports, "use client", lucide icons, Button component) that the patterns are well-established. The RESEARCH.md provides exact implementation code for both.

## Metadata

**Analog search scope:** `apps/helios/src/` (all subdirectories: `app/`, `components/`, `lib/`, `hooks/`)
**Files scanned:** 18 component/lib files + package.json + components.json
**Pattern extraction date:** 2026-04-17
