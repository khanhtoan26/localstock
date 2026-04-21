# Phase 10: Interactive Glossary Linking - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Auto-link glossary terms in AI report text with interactive hover cards. Users hover/tap a highlighted term to see a short definition preview with a link to the full learn page. Click-through navigates to /learn/[category]#[term].

Does NOT include: editing glossary content, adding new entries at runtime, analytics on term clicks, or glossary terms outside AI reports (e.g., in score breakdowns or market pages).

</domain>

<decisions>
## Implementation Decisions

### Hover Card Design
- **D-01:** Hover card shows: term (Vietnamese), short definition (shortDef), and a "Xem chi tiết →" link to /learn/[category]#[term-id]. If formula exists, show it below shortDef in a monospace block. Agent's Discretion on exact card layout.
- **D-02:** Hover card width is Agent's Discretion — recommended: max-w-xs (320px), enough for a sentence definition without being overwhelming.

### Link Visual Style
- **D-03:** Highlighted terms use a dotted underline with the accent color (hsl(210 70.9% 51.6%)) — visually distinct from regular text but not distracting. No background color. On hover, underline becomes solid.
- **D-04:** Terms are rendered as inline elements (not block) — they flow naturally within the prose text. Use `<span>` or `<a>`, not breaking elements.

### Matching Strategy
- **D-05:** Use longest-first matching per GLOSS-04 — sort aliases by length (descending) before scanning text. This prevents "RSI" from matching inside "chỉ số RSI".
- **D-06:** Matching is case-insensitive but NOT diacritic-insensitive — report text already contains correct Vietnamese diacritics from the AI model. Exact string matching on aliases is sufficient.
- **D-07:** Each term should only be linked on its FIRST occurrence in the report text. Subsequent occurrences render as normal text — reduces visual clutter.
- **D-08:** Implementation approach: override react-markdown text rendering via custom component. The `<Markdown>` component in ai-report-panel.tsx supports `components` prop for custom renderers. Agent's Discretion on exact implementation.

### Hover Card Interaction
- **D-09:** Desktop: hover with 200ms delay before showing card. Card stays visible while mouse is over the term or the card itself (standard popover behavior).
- **D-10:** Mobile: tap to show card, tap outside to dismiss. No long-press — simple tap toggle.
- **D-11:** Use Popover component from shadcn (or equivalent) for hover card rendering. Agent's Discretion on whether to use existing Popover or a lightweight custom tooltip.

### Click-Through Navigation
- **D-12:** "Xem chi tiết →" link navigates to `/learn/[category]#[term-id]`. The learn page should auto-scroll to and expand the matching entry. This connects back to Phase 9's GlossaryEntryCard collapsible behavior.
- **D-13:** Navigation uses Next.js `<Link>` for client-side routing.

### Agent's Discretion
- Exact hover card animation/transition
- Whether to use Popover from shadcn or a custom lightweight tooltip
- How to structure the text-scanning utility (regex vs string search)
- Whether to memoize the processed markdown content
- Error handling if a glossary entry is referenced but not found
- Z-index and positioning strategy for hover cards

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Interactive Glossary — GLOSS-01 through GLOSS-04 acceptance criteria

### Phase 9 Context (Glossary Data)
- `.planning/phases/09-academic-learning-page-glossary-data/09-CONTEXT.md` — Glossary data model decisions (D-04 through D-06, aliases field purpose)
- `apps/helios/src/lib/glossary.ts` — Glossary data module with aliases, normalizeForSearch, getEntriesByCategory

### Integration Point
- `apps/helios/src/components/stock/ai-report-panel.tsx` — Where linking happens: react-markdown `<Markdown>` component renders AI report text
- `apps/helios/src/app/learn/[category]/page.tsx` — Deep link target with hash-based scroll
- `apps/helios/src/components/learn/glossary-entry-card.tsx` — Collapsible card component (needs hash-triggered auto-expand)

### Design System
- `.planning/phases/09-academic-learning-page-glossary-data/09-UI-SPEC.md` — Visual design contract (typography, spacing, color tokens)

### Project Guidelines
- `copilot-instructions.md` — Next.js 16, @base-ui/react, lucide-react, named exports

</canonical_refs>

<code_context>
## Code Context

### AI Report Panel (Integration Point)
`ai-report-panel.tsx` uses `react-markdown` v10's `<Markdown>` component with `prose` styling. The `components` prop can override text rendering to inject glossary links. Currently renders plain markdown — no custom components.

### Glossary Module
`glossary.ts` exports `GlossaryEntry` type with `aliases: string[]` field designed specifically for Phase 10 matching. Each entry has 2-6 aliases covering Vietnamese, English, and abbreviated forms. `getAllEntries()` returns all 25 entries.

### Learn Pages (Deep Link Target)
Category pages at `/learn/[category]` render `GlossarySearch` → `GlossaryEntryCard` with `@base-ui/react` Collapsible. Hash-based auto-expand already partially implemented (URL hash detection in GlossarySearch).

</code_context>

<specifics>
## Specific Ideas

- The aliases field in glossary.ts was designed for this phase — use it directly
- react-markdown v10 supports `components={{ p: CustomParagraph }}` for text processing
- Longest-first matching prevents partial matches (GLOSS-04 requirement)
- First-occurrence-only linking reduces visual noise in long reports

</specifics>

<deferred>
## Deferred Ideas

- **EDU-01:** Live example charts embedded in glossary entries
- **EDU-02:** Cross-linking between related glossary entries ("Xem thêm: MACD, Bollinger Bands")
- **EDU-03:** AI-powered simplification of glossary content
- **LINK-01:** Glossary linking in score breakdowns and market pages (not just AI reports)
- **LINK-02:** Click analytics on glossary terms (track which terms users look up most)

</deferred>

---

*Phase: 10-interactive-glossary-linking*
*Context gathered: 2026-04-21 via discuss-phase (all Agent's Discretion)*
