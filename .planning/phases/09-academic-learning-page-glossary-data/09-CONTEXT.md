# Phase 9: Academic/Learning Page & Glossary Data - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Educational pages explaining technical indicators, fundamental ratios, and macro concepts used in AI reports. Typed glossary data module as single source of truth. Category-based routing with client-side diacritic-insensitive search. Adds "Học" nav item to sidebar.

Does NOT include: interactive glossary linking (Phase 10), live example charts in entries (EDU-01), cross-linking between entries (EDU-02), or AI-powered simplification (EDU-03).

</domain>

<decisions>
## Implementation Decisions

### Content Structure
- **D-01:** Each glossary entry is a detailed article — includes definition, formula/calculation, how to read/interpret, practical examples, and related notes. Not just a short definition.
- **D-02:** Content language is Vietnamese with English technical terms in parentheses. Example: "Chỉ số sức mạnh tương đối (RSI)" — maintains consistency with AI report tone.
- **D-03:** Display format is Agent's Discretion — recommended: expandable cards on category page, each card shows title + short definition, click expands to full article. This balances scanability with depth.

### Glossary Data Model
- **D-04:** Typed TypeScript module per REQUIREMENTS (LEARN-02). Single file `src/lib/glossary.ts` exporting typed Record with all entries. No JSON files, no MDX.
- **D-05:** Entry count is Agent's Discretion — recommended: ~25 entries covering all indicators actually used in the system (SMA, EMA, RSI, MACD, Bollinger Bands, P/E, P/B, EPS, ROE, ROA, D/E, revenue growth, profit growth, market cap, CPI, GDP, interest rates, exchange rates, etc.).
- **D-06:** Each entry must have: `id` (slug), `term` (Vietnamese name), `termEn` (English name), `aliases` (alternative names for Phase 10 matching), `category` (technical | fundamental | macro), `shortDef` (1-sentence definition), `content` (full markdown article), and `formula` (optional — for calculable indicators).

### Search & Filtering
- **D-07:** Client-side array filter — simple `.filter()` on entry fields. No external library needed for ~25 entries.
- **D-08:** Diacritic-insensitive matching via `normalize('NFD').replace(/[\u0300-\u036f]/g, '')` — matches "chi so" to "chỉ số".
- **D-09:** Search bar position is Agent's Discretion — recommended: at the top of each category page, filtering entries within that category.

### Page Layout & Navigation
- **D-10:** Add "Học" item to sidebar `navItems` array with `BookOpen` icon from lucide-react, linking to `/learn`.
- **D-11:** Navigation structure is Agent's Discretion — recommended: hub page `/learn` with overview + category cards, then `/learn/[category]` pages for each category (LEARN-03 requires separate URLs). Enables Server Components per REQUIREMENTS.
- **D-12:** Visual style matches existing app — use Card components, consistent typography, badge/tag for category labels. Same warm-cream / dark theme support.
- **D-13:** Responsive behavior: entries display as full-width cards on mobile (stacked), comfortable reading width on desktop.

### Agent's Discretion
- Exact card layout and expand/collapse animation
- Number of entries per category (aim for balanced distribution)
- Order of entries within a category (alphabetical vs grouped by complexity)
- Whether to show entry count per category on hub page
- Empty state handling (unlikely but defensive)
- URL structure for individual entries (if full pages instead of expandable cards)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Academic/Learning Page — LEARN-01 through LEARN-04 acceptance criteria
- `.planning/REQUIREMENTS.md` §Interactive Glossary — GLOSS-01 through GLOSS-04 (Phase 10 — understand alias field purpose)

### Existing Code
- `apps/helios/src/components/layout/sidebar.tsx` — Add "Học" nav item here
- `apps/helios/src/app/layout.tsx` — App layout with ThemeProvider
- `apps/helios/src/components/ui/card.tsx` — Card, CardHeader, CardTitle, CardContent components
- `apps/helios/src/components/ui/tabs.tsx` — Tabs component (if used for category switching)
- `apps/helios/src/lib/types.ts` — Existing type definitions (pattern reference for glossary types)
- `apps/helios/src/lib/utils.ts` — Utility functions (cn, formatScore, etc.)
- `apps/helios/src/app/globals.css` — Theme variables and color tokens

### Prior Phase Context
- `.planning/phases/07-theme-foundation-visual-identity/07-CONTEXT.md` — Theme decisions (D-01 to D-26) that apply to learn pages

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Card` component (card.tsx): Used for entry display — CardHeader/CardTitle/CardContent pattern
- `Badge` component (badge.tsx): Category labels (Kỹ Thuật, Cơ Bản, Vĩ Mô)
- `Collapsible` component (collapsible.tsx): Expandable card sections
- `Skeleton` component: Loading states
- `EmptyState` / `ErrorState` components: Defensive states
- `cn()` utility: Class name merging
- `react-markdown` already installed: Can render glossary content markdown

### Established Patterns
- App Router with `src/app/[route]/page.tsx` convention
- Client components with `"use client"` for interactive features
- TanStack Query for data fetching (but glossary is static data — no API call needed)
- Sidebar navItems array pattern for navigation
- Tailwind CSS v4 with theme variables

### Integration Points
- Sidebar `navItems[]` — add new entry for `/learn`
- App Router — create `src/app/learn/` directory with page.tsx + `[category]/page.tsx`
- Glossary data module — `src/lib/glossary.ts` consumed by learn pages AND Phase 10 glossary linking

</code_context>

<specifics>
## Specific Ideas

- User explicitly requested "Học" as sidebar label with BookOpen icon
- Style must match existing app (cards + tables + badges) — not a documentation site layout
- Vietnamese with English terms in parentheses — consistent with AI report language
- Client-side filter is sufficient (no fuzzy search library needed for ~25 entries)
- Content should be detailed articles, not just definitions — this is educational, not just a glossary

</specifics>

<deferred>
## Deferred Ideas

- **EDU-01**: Per-term live example charts — deferred to v1.2+
- **EDU-02**: Cross-linking between academic entries (seeAlso) — deferred to v1.2+
- **EDU-03**: AI-powered "giải thích đơn giản hơn" button — deferred to v1.2+

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-academic-learning-page-glossary-data*
*Context gathered: 2026-04-18*
