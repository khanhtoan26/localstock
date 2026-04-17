# Phase 7: Theme Foundation & Visual Identity + Stock Page Redesign - Context

**Gathered:** 2026-04-17
**Updated:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

**Part A (DONE):** Warm-light default theme with dark toggle, FOUC-free switching, chart re-theming, and WCAG-passing financial color tokens — already built and executed (07-01, 07-02 plans).

**Part B (NEW):** Stock page redesign — side-by-side layout with AI report as primary content, tabbed data panel, react-markdown rendering. Replaces the original Phase 8 scope (right drawer) with user's preferred side-by-side approach. No drawer panel.

</domain>

<decisions>
## Implementation Decisions

### Warm Palette Aesthetic (DONE — from original Phase 7)
- **D-01:** Use Claude-inspired warm cream as the base: `oklch(0.97 0.02 70)` for background, with terracotta/orange accent colors. The warmth should be subtle — not a saturated orange theme, but a clearly warm cream that feels professional and inviting.
- **D-02:** Unify color space to oklch for the warm-light theme block (`:root`). The `.dark` block can keep hsl values to minimize diff, but new tokens should be in oklch.
- **D-03:** The warm-light theme is the DEFAULT — new visitors see warm cream, not dark mode. Dark mode is opt-in via toggle.

### Toggle Placement & Behavior (DONE — from original Phase 7)
- **D-04:** Theme toggle is a sun/moon icon button in the header top-right area (inside AppShell header). Standard icon-based toggle — click to switch, no dropdown menu needed for just 2 themes.
- **D-05:** Use `next-themes` with `attribute="class"`, `defaultTheme="light"`, `enableSystem={false}`. The warm-light theme uses `:root` (no class), dark uses `.dark` class — matching existing Tailwind v4 `@custom-variant dark` setup.
- **D-06:** Preference persists via localStorage (next-themes default behavior). FOUC prevented via next-themes inline blocking script.

### Financial Colors on Light Background (DONE — from original Phase 7)
- **D-07:** Replace hardcoded Tailwind classes in `gradeColors` (e.g., `text-green-400`) with CSS variables or dual-mode classes (`text-green-700 dark:text-green-400`). All grade colors must pass WCAG AA (4.5:1) against both cream and dark backgrounds.
- **D-08:** Financial semantic tokens (`--stock-up`, `--stock-down`, `--stock-warning`, `--chart-bg`, `--chart-grid`, `--chart-text`) must have values in BOTH `:root` (warm-light) and `.dark` blocks. Current `:root` values are dark-mode colors — this is the #1 bug to fix.
- **D-09:** Stock up/down colors: green/red stays universal (standard financial convention), but use darker shades on cream (green-700, red-700) and brighter on dark (green-400, red-400).

### Chart Re-Theming Strategy (DONE — from original Phase 7)
- **D-10:** Refactor `chart-colors.ts` from static `CHART_COLORS` object to a `getChartColors(theme: 'light' | 'dark')` function that returns theme-appropriate colors.
- **D-11:** Use `chart.applyOptions()` + `series.applyOptions()` to update chart colors dynamically when theme changes — do NOT destroy/recreate charts. This preserves zoom/scroll state.
- **D-12:** Create a `useChartTheme()` hook that listens to `resolvedTheme` from next-themes and returns the current chart color set. Chart components consume this hook.

### Stock Page Layout (NEW)
- **D-13:** Side-by-side layout: AI Report on LEFT (60-70% width) + Chart/Data panel on RIGHT (30-40% width). NO drawer panel — both panels visible simultaneously.
- **D-14:** Right panel is STICKY (position: sticky) — stays fixed in viewport while user scrolls through AI report content.
- **D-15:** Score overview (grade badge + total score + 4 dimension scores compact) displayed in the page header alongside stock symbol. Full score breakdown available in the right panel's Score tab.
- **D-16:** Breakpoint at 768px (md): below this, layout stacks vertically — AI report first, then chart/data below.

### AI Report Rendering (NEW)
- **D-17:** Use `react-markdown` with `@tailwindcss/typography` plugin. Report content wrapped in `prose` class for automatic typography (headers, paragraphs, lists, tables, bold/italic).
- **D-18:** AI report panel has internal scroll with max-height via `ScrollArea` component — report does not push page height infinitely.
- **D-19:** Render `summary` field as markdown first; fallback to `content_json` formatted display if summary is empty.

### Chart & Data Panel (NEW)
- **D-20:** Right panel organized as TABS: Chart | Indicators | Score. Clean, non-overwhelming.
- **D-21:** Tab selection persisted in localStorage — remembers user's last chosen tab. Fallback to Chart tab if no prior preference.
- **D-22:** Chart tab contains: TimeframeSelector (top) + PriceChart (candlestick). Existing components reused.
- **D-23:** Indicators tab contains: MACD SubPanel + RSI SubPanel. Existing SubPanel component reused.
- **D-24:** Score tab contains: full 4-dimension score breakdown (Kỹ Thuật, Cơ Bản, Tin Tức, Vĩ Mô) with visual bars or numbers.

### Responsive Behavior (NEW)
- **D-25:** Below 768px (md breakpoint): side-by-side → vertical stack. AI report renders first (full-width), chart/data below.
- **D-26:** On mobile, tabs convert to accordion/collapsible sections — each section (Chart, Indicators, Score) can be expanded/collapsed independently.

### Agent's Discretion
- Color space unification strategy (oklch vs hsl migration timeline)
- Exact oklch values for warm-light palette — starting from research suggestions, fine-tuned during implementation
- Chart background/grid colors for warm-light theme
- Transition animation on theme switch (instant vs 200ms fade)
- Icon choice for toggle (lucide sun/moon or custom)
- Exact width ratio between left/right panels (within 60-70% / 30-40% range)
- Tab component implementation (shadcn Tabs or custom)
- Accordion component for mobile (shadcn Accordion or Collapsible)
- ScrollArea max-height value for AI report panel
- Chart height in the narrower right panel

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme & Color System (Part A — already implemented)
- `.planning/research/STACK.md` — next-themes setup, Tailwind v4 `@custom-variant` approach, version pins
- `.planning/research/PITFALLS.md` — 5 theme pitfalls (#1-5): token inversion, canvas charts, hardcoded colors, FOUC, contrast
- `.planning/research/ARCHITECTURE.md` — ThemeProvider + ThemeToggle component design
- `.planning/research/SUMMARY.md` — Synthesized research with recommended stack and build order

### Existing Code (must understand before modifying)
- `apps/helios/src/app/globals.css` — Current CSS variables, financial tokens in `:root` and `.dark` blocks
- `apps/helios/src/app/layout.tsx` — ThemeProvider wrapping (already updated in Part A)
- `apps/helios/src/lib/chart-colors.ts` — Theme-aware chart colors (already refactored in Part A)
- `apps/helios/src/lib/utils.ts` — `gradeColors` with theme-responsive classes
- `apps/helios/src/components/rankings/grade-badge.tsx` — Consumes gradeColors
- `apps/helios/src/components/charts/price-chart.tsx` — Creates lightweight-charts instances
- `apps/helios/src/components/charts/sub-panel.tsx` — Chart sub-panels (MACD, RSI)
- `apps/helios/src/components/charts/timeframe-selector.tsx` — Timeframe selection UI
- `apps/helios/src/app/stock/[symbol]/page.tsx` — **PRIMARY TARGET** — current stock detail page to redesign
- `apps/helios/src/lib/queries.ts` — Data fetching hooks (useStockPrices, useStockIndicators, useStockScore, useStockReport)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **shadcn/ui components** — Card, Button, Badge, ScrollArea, Skeleton, Separator already exist.
- **`cn()` utility** — Standard class merging, already used everywhere.
- **PriceChart, SubPanel, TimeframeSelector** — Chart components already built, can be placed in right panel tabs.
- **GradeBadge** — Grade display component, reuse in header area.
- **Query hooks** — `useStockPrices`, `useStockIndicators`, `useStockScore`, `useStockReport` already handle data fetching.
- **`@custom-variant dark`** — Tailwind v4 dark mode variant already configured.

### Established Patterns
- **CSS variables** — shadcn/ui uses CSS custom properties for all colors. Both `:root` and `.dark` blocks exist.
- **Component composition** — Components are small, focused, import from `@/lib/` and `@/components/ui/`.
- **Chart initialization** — Charts created in `useEffect` with cleanup. Theme-aware via `useChartTheme()` hook.
- **Dynamic imports** — Charts use `next/dynamic` with `ssr: false` to avoid SSR crashes.

### Integration Points
- **`stock/[symbol]/page.tsx`** — Complete rewrite of layout structure (single-column → side-by-side)
- **New components needed:** Tabs (or shadcn Tabs), Accordion (for mobile), possibly a StockPageLayout wrapper
- **`package.json`** — Need to add `react-markdown`, `@tailwindcss/typography` dependencies

</code_context>

<specifics>
## Specific Ideas

- Claude warm-light inspiration: cream background, not pure white — feels like quality paper
- Terracotta/orange accent for primary interactive elements in light mode
- Financial convention preserved: green = up, red = down — adjust brightness not hue
- Charts should feel native in both themes — not "light theme with dark chart" or vice versa
- AI report is THE primary content — "insight & góc nhìn" philosophy, not traditional stock dashboard
- Side-by-side layout makes report readable while keeping chart context visible
- Tab persistence via localStorage mirrors the theme persistence pattern — consistent UX

</specifics>

<deferred>
## Deferred Ideas

- **STOCK-04 (Drawer scroll preservation):** No longer applicable — drawer replaced by side-by-side layout
- **STOCK-05 (Drawer state in URL params):** No longer applicable — no drawer. Tab state persisted in localStorage instead.

</deferred>

---

*Phase: 07-theme-foundation-visual-identity*
*Context gathered: 2026-04-17*
*Updated: 2026-04-17 — merged Stock Page Redesign scope*
