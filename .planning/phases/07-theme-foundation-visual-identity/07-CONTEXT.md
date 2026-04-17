# Phase 7: Theme Foundation & Visual Identity - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a warm-light default theme with dark toggle, FOUC-free switching, chart re-theming, and WCAG-passing financial color tokens. No new pages, no layout changes, no new data features — purely visual identity and infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Warm Palette Aesthetic
- **D-01:** Use Claude-inspired warm cream as the base: `oklch(0.97 0.02 70)` for background, with terracotta/orange accent colors. The warmth should be subtle — not a saturated orange theme, but a clearly warm cream that feels professional and inviting.
- **D-02:** Unify color space to oklch for the warm-light theme block (`:root`). The `.dark` block can keep hsl values to minimize diff, but new tokens should be in oklch.
- **D-03:** The warm-light theme is the DEFAULT — new visitors see warm cream, not dark mode. Dark mode is opt-in via toggle.

### Toggle Placement & Behavior
- **D-04:** Theme toggle is a sun/moon icon button in the header top-right area (inside AppShell header). Standard icon-based toggle — click to switch, no dropdown menu needed for just 2 themes.
- **D-05:** Use `next-themes` with `attribute="class"`, `defaultTheme="light"`, `enableSystem={false}`. The warm-light theme uses `:root` (no class), dark uses `.dark` class — matching existing Tailwind v4 `@custom-variant dark` setup.
- **D-06:** Preference persists via localStorage (next-themes default behavior). FOUC prevented via next-themes inline blocking script.

### Financial Colors on Light Background
- **D-07:** Replace hardcoded Tailwind classes in `gradeColors` (e.g., `text-green-400`) with CSS variables or dual-mode classes (`text-green-700 dark:text-green-400`). All grade colors must pass WCAG AA (4.5:1) against both cream and dark backgrounds.
- **D-08:** Financial semantic tokens (`--stock-up`, `--stock-down`, `--stock-warning`, `--chart-bg`, `--chart-grid`, `--chart-text`) must have values in BOTH `:root` (warm-light) and `.dark` blocks. Current `:root` values are dark-mode colors — this is the #1 bug to fix.
- **D-09:** Stock up/down colors: green/red stays universal (standard financial convention), but use darker shades on cream (green-700, red-700) and brighter on dark (green-400, red-400).

### Chart Re-Theming Strategy
- **D-10:** Refactor `chart-colors.ts` from static `CHART_COLORS` object to a `getChartColors(theme: 'light' | 'dark')` function that returns theme-appropriate colors.
- **D-11:** Use `chart.applyOptions()` + `series.applyOptions()` to update chart colors dynamically when theme changes — do NOT destroy/recreate charts. This preserves zoom/scroll state.
- **D-12:** Create a `useChartTheme()` hook that listens to `resolvedTheme` from next-themes and returns the current chart color set. Chart components consume this hook.

### Agent's Discretion
- Color space unification strategy (oklch vs hsl migration timeline)
- Exact oklch values for warm-light palette — starting from research suggestions, fine-tuned during implementation
- Chart background/grid colors for warm-light theme
- Transition animation on theme switch (instant vs 200ms fade)
- Icon choice for toggle (lucide sun/moon or custom)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme & Color System
- `.planning/research/STACK.md` — next-themes setup, Tailwind v4 `@custom-variant` approach, version pins
- `.planning/research/PITFALLS.md` — 5 theme pitfalls (#1-5): token inversion, canvas charts, hardcoded colors, FOUC, contrast
- `.planning/research/ARCHITECTURE.md` — ThemeProvider + ThemeToggle component design
- `.planning/research/SUMMARY.md` — Synthesized research with recommended stack and build order

### Existing Code (must understand before modifying)
- `apps/helios/src/app/globals.css` — Current CSS variables, financial tokens in `:root` (dark values!), `.dark` block
- `apps/helios/src/app/layout.tsx` — Hardcoded `className="dark"` to replace with ThemeProvider
- `apps/helios/src/lib/chart-colors.ts` — Static hex constants to refactor into theme-aware function
- `apps/helios/src/lib/utils.ts` — `gradeColors` with hardcoded dark-mode Tailwind classes
- `apps/helios/src/components/rankings/grade-badge.tsx` — Consumes gradeColors
- `apps/helios/src/components/charts/price-chart.tsx` — Creates lightweight-charts instances
- `apps/helios/src/components/charts/sub-panel.tsx` — Chart sub-panels (MACD, RSI)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **shadcn/ui components** — Button, Badge already exist. Toggle button can reuse Button component with icon variant.
- **`cn()` utility** — Standard class merging, already used everywhere.
- **`@custom-variant dark`** — Tailwind v4 dark mode variant already configured in globals.css.

### Established Patterns
- **CSS variables** — shadcn/ui uses CSS custom properties for all colors. Both `:root` and `.dark` blocks exist.
- **Component composition** — Components are small, focused, import from `@/lib/` and `@/components/ui/`.
- **Chart initialization** — Charts created in `useEffect` with cleanup. Colors passed at creation time via `CHART_COLORS` import.

### Integration Points
- **`layout.tsx`** — Must wrap children with ThemeProvider, remove hardcoded `className="dark"`
- **`globals.css`** — Must add warm-light values to `:root`, fix financial tokens
- **`chart-colors.ts`** — Refactor to function, consumed by `price-chart.tsx` and `sub-panel.tsx`
- **`utils.ts` `gradeColors`** — Must use theme-responsive classes, consumed by `grade-badge.tsx`
- **`app-shell.tsx`** — Must add ThemeToggle to header area

</code_context>

<specifics>
## Specific Ideas

- Claude warm-light inspiration: cream background, not pure white — feels like quality paper
- Terracotta/orange accent for primary interactive elements in light mode
- Financial convention preserved: green = up, red = down — adjust brightness not hue
- Charts should feel native in both themes — not "light theme with dark chart" or vice versa

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-theme-foundation-visual-identity*
*Context gathered: 2026-04-17*
