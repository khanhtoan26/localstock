# Phase 14: Visual Foundation - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current blue primary + terracotta accent color palette with a neutral tone palette (warm white/gray/black) inspired by Claude Desktop. Replace the system-ui default font with Source Sans 3 (Vietnamese subset). Both light and dark themes must be updated. Financial semantic colors (stock up/down) adjusted to harmonize with the new neutral palette.

</domain>

<decisions>
## Implementation Decisions

### Color Palette Direction
- **D-01:** Replace blue `--primary` (hsl(210 70.9% 51.6%)) with a neutral tone. Claude Desktop uses warm whites, grays, and near-blacks — no bright accent colors for buttons, links, or interactive elements. The app should feel clean, professional, and monochromatic.
- **D-02:** Keep the warm cream background base (#FAF9F5 / hsl(48 33.3% 97.1%)) from Phase 7 — it already matches Claude Desktop's warm off-white. Only the interactive/accent colors (primary, ring, sidebar-primary) need changing from blue to neutral gray/black.
- **D-03:** Dark mode palette must follow the same neutral principle — warm dark grays with neutral interactive elements, no blue.
- **D-04:** All CSS variable locations need auditing: `:root`, `.dark`, `@theme inline` mappings, and any hardcoded hex in TypeScript (e.g., `chart-colors.ts`).

### Font Change
- **D-05:** Load Source Sans 3 via `next/font/google` with `subsets: ['latin', 'vietnamese']` in `layout.tsx`. Assign CSS variable `--font-sans`.
- **D-06:** Agent's discretion on exact weight range — suggest variable font or 400/500/600/700 range.
- **D-07:** Remove any hardcoded `font-family: system-ui` in `globals.css` that would override the CSS variable.
- **D-08:** Heading font (`--font-heading`) should also use Source Sans 3 (same family, heavier weight for headings is fine).

### Financial Colors
- **D-09:** Financial up/down/warning colors (green/red/yellow) remain conceptually the same but agent should adjust exact shades to harmonize with the new neutral palette. WCAG AA contrast ratios must be maintained against both light and dark backgrounds.

### Agent's Discretion
- Exact HSL/oklch values for the new neutral palette (research Claude Desktop's actual tones)
- Source Sans 3 weight range and variable font configuration
- Dark mode neutral gray scale exact values
- Chart color tokens update (chart-1 through chart-5) to work with neutral theme
- Ring/focus color choice (subtle gray vs darker gray)
- Transition between old and new sidebar CSS variables

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme System (from Phase 7)
- `.planning/phases/07-theme-foundation-visual-identity/07-CONTEXT.md` — Original theme decisions (D-01 through D-12), warm cream base, financial token system, chart re-theming strategy
- `apps/helios/src/app/globals.css` — All CSS variables (:root + .dark blocks), current blue primary values
- `apps/helios/src/app/layout.tsx` — Provider ordering, font loading location, FOUC prevention script

### Color Locations to Audit
- `apps/helios/src/app/globals.css` lines 52-136 — `:root` and `.dark` CSS variable blocks (primary blue appears ~10 times)
- `apps/helios/src/components/layout/sidebar.tsx` — Uses `text-primary` for active nav items
- `apps/helios/src/components/layout/app-shell.tsx` — Header layout, border classes

### Research
- `.planning/research/SUMMARY.md` — v1.3 research synthesis
- `.planning/research/PITFALLS.md` — Font variable collision warning, color layer audit checklist

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `globals.css` CSS variable system: already structured with `:root` + `.dark` blocks — just need value changes
- `ThemeProvider` + FOUC prevention script in `layout.tsx` — no changes needed
- `@theme inline` block in globals.css maps CSS vars to Tailwind tokens — propagates automatically
- `chart-colors.ts` `getChartColors()` function — already theme-aware from Phase 7

### Established Patterns
- CSS variables → `@theme inline` → Tailwind classes. Components use semantic classes (`text-primary`, `bg-background`), not hardcoded colors — palette change propagates automatically.
- `next-themes` NOT used — custom ThemeProvider with localStorage. Theme class added in `<head>` script.

### Integration Points
- `layout.tsx` — font loading with `next/font/google`, CSS variable assignment
- `globals.css` — all color variables (single source of truth)
- Components using `text-primary`, `bg-primary`, `border-primary` — will auto-update when CSS vars change

</code_context>

<specifics>
## Specific Ideas

- User referenced Claude Desktop (code) as the visual target: "chỉ thấy trắng xám và đen" (only whites, grays, and blacks)
- Not exact #FFF/#000 — warm neutral tones like Claude Desktop's actual palette
- The app should feel like a tool, not a colorful dashboard — professional and restrained

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-visual-foundation*
*Context gathered: 2026-04-24*
