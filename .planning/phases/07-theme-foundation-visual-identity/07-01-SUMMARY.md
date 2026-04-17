---
phase: 07-theme-foundation-visual-identity
plan: "01"
subsystem: frontend-theme
tags: [theme, next-themes, tailwind, css, accessibility]
dependency_graph:
  requires: []
  provides: [theme-provider, theme-toggle, warm-oklch-palette, financial-color-tokens]
  affects: [apps/helios/src/app/layout.tsx, apps/helios/src/components/layout/app-shell.tsx, apps/helios/src/app/globals.css]
tech_stack:
  added: [next-themes@0.4.6]
  patterns: [class-based theme switching, oklch warm palette, dual-mode financial tokens, FOUC prevention via suppressHydrationWarning]
key_files:
  created:
    - apps/helios/src/components/theme/theme-provider.tsx
    - apps/helios/src/components/theme/theme-toggle.tsx
  modified:
    - apps/helios/src/app/globals.css
    - apps/helios/src/lib/utils.ts
    - apps/helios/src/components/ui/error-state.tsx
    - apps/helios/src/app/layout.tsx
    - apps/helios/src/components/layout/app-shell.tsx
decisions:
  - "next-themes value={{ claude: '' , dark: 'dark' }} maps warm-light to no class so :root applies unmodified"
  - "enableSystem=false forces warm-light for all new visitors regardless of OS preference"
  - "disableTransitionOnChange prevents CSS transition flash during theme switch"
  - "suppressHydrationWarning on html element is the official next-themes escape hatch for SSR class mismatch"
  - "Financial tokens split: oklch warm values in :root, hex dark values inside .dark block"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-17T10:03:44Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 5
---

# Phase 7 Plan 01: Theme Foundation & Visual Identity Summary

**One-liner:** FOUC-free warm cream/dark dual-theme via next-themes with oklch palette, terracotta primary, and WCAG-AA financial color tokens for both themes.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Install next-themes, create ThemeProvider + ThemeToggle | f1fce83 | theme-provider.tsx, theme-toggle.tsx, package.json |
| 2 | Rewrite warm oklch palette, fix financial tokens, update grade colors | a3ffded | globals.css, utils.ts, error-state.tsx |
| 3 | Wire ThemeProvider into layout, add toggle to AppShell header | fbf0589 | layout.tsx, app-shell.tsx |

## Decisions Made

1. **Theme value mapping:** `value={{ claude: "", dark: "dark" }}` — the "claude" theme name maps to an empty string (no class applied), so `:root` CSS block provides all warm-light tokens. The "dark" name maps to the `dark` class, triggering `.dark` block overrides. This is the cleanest approach for Tailwind v4 `@custom-variant dark`.

2. **No system theme detection:** `enableSystem={false}` — warm cream is forced for all new visitors. OS dark-mode preference is not respected by design (D-05: explicit user choice over system defaults).

3. **Financial token split:** Warm-light tokens (`--stock-up: oklch(0.62 0.18 145)`) live in `:root` for ~6:1 contrast on cream. Dark tokens (`--stock-up: #22c55e`) live in `.dark` for brightness on dark background. Eliminates the duplicate `:root` block that was incorrectly using dark hex values as defaults.

4. **suppressHydrationWarning:** next-themes sets the `class` attribute on `<html>` before React hydrates (via a blocking inline script). This causes a React SSR mismatch if the class is absent server-side. `suppressHydrationWarning` is the official, documented escape hatch.

5. **gradeColors dual-mode pattern:** `text-{color}-700 dark:text-{color}-400` — 700-shade provides sufficient contrast on cream (#F5F0E8), 400-shade provides brightness on dark navy. `bg-*` and `border-*` use opacity-based classes (`/20`, `/30`) that work on both backgrounds without modification.

## Verification Results

- TypeScript: PASS (no errors)
- Production build: PASS (6 routes, Turbopack)
- `oklch(0.97 0.02 70)` in `:root`: PASS
- Terracotta primary `oklch(0.70 0.14 45)`: PASS
- Single `:root` block (duplicate removed): PASS
- `suppressHydrationWarning` on html: PASS
- No `className="dark"` on html: PASS

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all financial color tokens are wired to real CSS custom properties consumed by existing components. ThemeToggle correctly reads `resolvedTheme` from next-themes context.

## Threat Flags

No new security-relevant surface introduced. Theme preference stored in localStorage as a non-sensitive string ("claude" or "dark") per the plan's threat model (T-07-01: accepted).

## Self-Check: PASSED

All created files exist on disk. All 3 task commits verified in git history.
