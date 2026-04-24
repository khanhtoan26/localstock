# Phase 16: Table, Search & Session Bar - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix table sort behavior (numeric sort with tiebreaker + grade semantic sort), add a search bar on the rankings page with URL-based persistence, and add a HOSE market session progress bar in the app header center. No backend changes required for search (client-side filter). No changes to sidebar cosmetic search.

</domain>

<decisions>
## Implementation Decisions

### Table Sort Fix
- **D-01:** Tiebreaker: when two rows have equal values for the sorted column, use `a.symbol.localeCompare(b.symbol)` as the secondary sort key. Current code returns `0` on equal — this must be fixed.
- **D-02:** Sort icons: replace current plain-text `" ↑"` / `" ↓"` indicators with `ChevronUp` / `ChevronDown` icons from `lucide-react` (already installed). Show only the active column's icon.
- **D-03:** Non-numeric columns: Recommendation is NOT sortable (header not clickable). Grade IS sortable but uses semantic order.
- **D-04:** Grade semantic sort order (asc = worst to best): C (5) → B (4) → B+ (3) → A (2) → A+ (1). Clicking Grade desc puts A+ stocks first. Implement via a grade rank lookup map `{ 'A+': 1, 'A': 2, 'B+': 3, 'B': 4, 'C': 5 }`.
- **D-05:** For numeric columns with `null` values: continue using `-Infinity` as null sentinel for sort purposes (current behavior is correct — keeps null rows at the bottom in desc).

### Search on Rankings Page
- **D-06:** Search input is placed above the table in the rankings page content area (not in title row, not in sidebar). Appears between the page title and the table.
- **D-07:** Filtering is client-side only: filter the already-loaded 50 stocks in the browser. No API call. Matches on `symbol` prefix (case-insensitive) OR `name` substring if name is available in `StockScore` type.
- **D-08:** URL param: `?q=VNM`. Use `nuqs` library for URL state management (new dependency). Handles Next.js App Router SSR and pushState cleanly.
- **D-09:** Search term persists when navigating to another page and returning (URL param survives navigation because it's in the URL, not component state).
- **D-10:** Clear button (×) appears inside the input when query is non-empty.

### Market Session Bar — Header Layout
- **D-11:** Session bar lives in the center section of the `h-12` header, in a `flex-1` region between the logo block and the lang/theme toggles.
- **D-12:** Visual format: slim horizontal progress bar showing elapsed % of current HOSE phase + phase label + time remaining. Example: `[ ATO  ████░░░░░░  8m left ]`.
- **D-13:** The component is a pure client-side `"use client"` component that calculates current phase and elapsed % from `Date.now()` with a 1-minute refresh interval (`setInterval`).

### HOSE Session Phases (UTC+7)
- **D-14:** Phase boundaries (all times are Vietnam time, UTC+7):
  - Pre-market: 8:30 – 9:00
  - ATO: 9:00 – 9:15
  - Morning trading: 9:15 – 11:30
  - Lunch break: 11:30 – 13:00
  - Afternoon trading: 13:00 – 14:30
  - ATC: 14:30 – 14:45
  - Closed: 14:45+
- **D-15:** Market is open Monday–Friday only. No public holiday handling in v1 (deferred).

### Outside Trading Hours Display
- **D-16:** When market is closed (evening/weekend), show: `● Closed • Opens in 14h 30m` with a live countdown to the next weekday 8:30 opening.
- **D-17:** On weekends, countdown skips to Monday 8:30. On weekday evenings, countdown targets next-day 8:30.
- **D-18:** Progress bar shows as fully empty (0% fill) when market is closed.

### Claude's Discretion
- Exact CSS for the progress bar (height, color, border-radius — should use neutral palette tokens)
- Whether to debounce the search input (recommend 150ms to avoid re-filtering on every keystroke)
- Exact width of the session bar component in the center section
- Whether the session indicator is always visible or hidden on very small screens (sm: hidden is fine)
- nuqs version to install (latest stable)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Table Sort
- `apps/helios/src/components/rankings/stock-table.tsx` — Current sort implementation (handleSort, sorted, sortIndicator), columns array, StockScore field types
- `apps/helios/src/lib/types.ts` — StockScore interface: score fields are `number | null`, grade is `string`, recommendation is `string | null`

### Rankings Page & Search
- `apps/helios/src/app/rankings/page.tsx` — Current rankings page (no search input, passes data directly to StockTable)
- `apps/helios/src/components/rankings/stock-table.tsx` — Table component (will receive filtered data from parent)

### App Shell & Header
- `apps/helios/src/components/layout/app-shell.tsx` — Header layout: `h-12`, left=[toggle+logo], right=[LanguageToggle+ThemeToggle]. Session bar goes in center flex-1 block.
- `apps/helios/src/app/globals.css` — CSS tokens: use `--foreground`, `--muted-foreground`, `--border` for session bar colors (no hardcoded colors)

### Theme System (Phase 14)
- `.planning/phases/14-visual-foundation/14-CONTEXT.md` — Neutral palette decisions: no blue, use muted/foreground tokens

### Research Reference
- `.planning/research/SUMMARY.md` — v1.3 research synthesis (nuqs mentioned as URL state library)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChevronUp`, `ChevronDown` from `lucide-react` (already installed) — use for sort column indicators
- `cn()` from `@/lib/utils` — conditional class merging (use everywhere)
- `useTranslations("rankings.columns")` — i18n for table column headers (already used in StockTable)
- `ThemeToggle`, `LanguageToggle` — right-side header controls pattern to follow for session bar placement
- `"use client"` pattern with `useState` + `useEffect` — established for all interactive components

### Established Patterns
- Table sort: `handleSort` → `sorted` → render. Keep same pattern, extend with tiebreaker.
- CSS variable approach: all colors via `var(--token)`, no hardcoded hex. Session bar must follow same rule.
- Client components use `"use client"` at top, hooks inline.

### Integration Points
- `app-shell.tsx` header div: insert `<MarketSessionBar />` between logo block and right controls. Wrap in `<div className="flex-1 flex items-center justify-center">`.
- `rankings/page.tsx`: add `nuqs` `useQueryState('q')` for search, pass filtered `data.stocks` to `StockTable` instead of raw `data.stocks`.
- `stock-table.tsx`: no URL state needed in the table — parent filters, table just renders sorted data.

</code_context>

<specifics>
## Specific Ideas

- Session bar center section: `[ ATO  ████░░░░░░  8m left ]` — phase name on left, progress bar in middle, countdown on right
- Countdown format: "8m left" during active phase, "Opens in 14h 30m" when closed
- Grade sort: A+ should appear at the TOP when clicking Grade (desc = best first = A+ first)
- The sidebar cosmetic search (⌘K placeholder) is NOT wired up in this phase — only the rankings page search input

</specifics>

<deferred>
## Deferred Ideas

- **Vietnamese public holidays** — HOSE holiday closures (Tết, 30/4, 2/9, etc.) not handled in v1. Planner should add a note/TODO comment in the session component for future handling.
- **Sidebar ⌘K search** — the command palette / global search triggered by ⌘K in the sidebar search input is out of scope for Phase 16
- **Search suggestions/autocomplete** (TBL-05/TBL-06 future requirements)
- **Grade/Recommendation sort order** for Recommendation column — deferred, Recommendation is non-sortable in this phase

</deferred>

---

*Phase: 16-table-search-session-bar*
*Context gathered: 2026-04-24*
