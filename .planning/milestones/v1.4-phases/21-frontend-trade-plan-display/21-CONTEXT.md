# Phase 21: Frontend Trade Plan Display - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

The stock detail page (`/stock/[symbol]`) gets a dedicated Trade Plan section that surfaces entry zone, stop-loss, target price, risk badge, and signal conflict — all conditionally rendered from the existing report API response (`content_json`). No new API endpoints. No new data fetching hooks — reuses `useStockReport()`.

</domain>

<decisions>
## Implementation Decisions

### Layout & Positioning
- **D-01:** Trade Plan section placed BETWEEN Score Breakdown and AI Report Panel — user sees prices right after scores, before reading the full AI analysis.
- **D-02:** Agent's discretion on exact layout (3-column grid, stacked, or inline with Score Breakdown). Investigate what fits best given the existing 2-column responsive grid (Score left 380px, AI Report right flexible).

### Risk Badge
- **D-03:** Risk badge uses pill/tag style matching GradeBadge pattern — red for "high" (Cao), yellow/amber for "medium" (Trung bình), green for "low" (Thấp).
- **D-04:** Risk badge has a tooltip on hover/tap showing reasoning text from the LLM report. Use the report's analysis content as the tooltip source since there's no separate `risk_reasoning` field.

### Signal Conflict Display
- **D-05:** Signal conflict section is conditionally rendered — only appears when `signal_conflicts` field is non-null in the report. Completely absent from DOM when null.
- **D-06:** Uses alert box style with yellow/amber background and ⚠️ icon, displaying the conflict text from the LLM verbatim.

### Price Levels Display
- **D-07:** 3 vertical rows for price levels: Entry Zone (range), Stop-Loss, Target Price. Each row has label + VND-formatted price using existing `formatVND()`.
- **D-08:** Each price level shows percentage variance from current close price — e.g., "Cắt lỗ: 48.000 (-4.0%)" in a smaller, muted text next to the price.

### Graceful Degradation
- **D-09:** When report is from v1.3 or earlier (all new fields null — entry_price, stop_loss, target_price, risk_rating all null), Trade Plan section is completely hidden. No empty state, no placeholder.
- **D-10:** When report is loading, show skeleton placeholder (animated) matching the existing PriceChart skeleton pattern.

### Agent's Discretion
- Layout details: exact widths, responsive breakpoints, grid column spans
- Component internal structure: whether to use Card wrapper or custom section
- Color shade choices within the established palette
- Tooltip implementation (native title vs custom component)
- Whether catalyst_data gets its own row or is part of the conflict section

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Stock Detail Page
- `apps/helios/src/app/stock/[symbol]/page.tsx` — Current page layout, data fetching hooks, component composition
- `apps/helios/src/components/stock/ai-report-panel.tsx` — AI report display (Trade Plan goes BEFORE this)
- `apps/helios/src/components/stock/score-breakdown.tsx` — Score display (Trade Plan goes AFTER this)

### UI Patterns to Follow
- `apps/helios/src/components/rankings/grade-badge.tsx` — Badge pattern for Risk Badge
- `apps/helios/src/components/stock/recommendation-badge.tsx` — Color-coded badge with Vietnamese text normalization
- `apps/helios/src/components/ui/card.tsx` — Card component system
- `apps/helios/src/components/ui/badge.tsx` — Generic badge with CVA variants

### Data Types & API
- `apps/helios/src/lib/types.ts` — StockReport interface (content_json: Record<string, unknown>)
- `apps/helios/src/lib/queries.ts` — useStockReport() hook
- `apps/helios/src/lib/utils.ts` — formatVND(), formatScore(), gradeColors
- `apps/prometheus/src/localstock/ai/client.py` — Backend StockReport model (15 fields incl. entry_price, stop_loss, target_price, risk_rating, signal_conflicts, catalyst)

### Next.js 16 Guidance
- `apps/helios/AGENTS.md` — Next.js 16 breaking changes and patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `formatVND()` in utils.ts — Vietnamese dong formatting with dot separators
- `GradeBadge` component — pill/tag badge pattern with color map
- `RecommendationBadge` — Vietnamese text normalization + color-coded styles
- `Card/CardHeader/CardContent` — standard card wrapper
- `EmptyState` / `ErrorState` — fallback display components
- `Skeleton` component — loading placeholder (used in PriceChart)

### Established Patterns
- TanStack Query hooks for data fetching (`useStockReport`, `useStockScore`)
- Dynamic imports with `next/dynamic` for heavy components
- Tailwind CSS 4 with dark mode support (dark: prefix)
- Responsive grid: `grid grid-cols-1 lg:grid-cols-[380px_1fr]`

### Integration Points
- Stock detail page layout grid — insert Trade Plan section
- `useStockReport(symbol)` hook — already fetches all needed data including content_json
- Report content_json — contains entry_price, stop_loss, target_price, risk_rating, signal_conflicts, catalyst

</code_context>

<specifics>
## Specific Ideas

- Risk badge should visually match GradeBadge — same pill shape, similar sizing
- Alert box for signal conflict should feel like a warning, not an error
- Price levels use "đ" suffix or similar VND indicator familiar to Vietnamese users
- Percentage variance text should be muted/secondary color, smaller font

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-frontend-trade-plan-display*
*Context gathered: 2026-04-28*
