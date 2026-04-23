# Project Research Summary

**Project:** LocalStock v1.3 — UI/UX Refinement
**Domain:** Stock analysis dashboard — visual polish & interaction improvement
**Researched:** 2026-04-24
**Confidence:** HIGH

## Executive Summary

LocalStock v1.3 is a pure UI/UX refinement milestone for an existing, functional Vietnamese stock analysis dashboard built on Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (base-nova). The existing stack is mature and well-chosen — research confirms that **only 1 new npm dependency (`nuqs`) and 1 new shadcn component (`tooltip`)** are needed. All 7 committed features can be implemented using existing primitives: `@base-ui/react` for tooltips/collapsibles/progress, `next/font/google` for typography, CSS variables for theming, `Intl.DateTimeFormat` for timezone handling, and TanStack Query for data fetching. The architecture is CSS-variable-driven, meaning font and color changes propagate globally with zero component modifications.

The recommended approach is a 4-phase build ordered by dependency chains: **Foundation first** (font + colors — everything else inherits from these), **Layout second** (sidebar rewrite — the highest-complexity item that restructures the app shell), **Feature integration third** (search persistence, market session bar, table sort fix), and **Market metrics last** (blocked on a new backend API endpoint that doesn't exist yet). The sidebar rewrite is the critical path — it touches `app-shell.tsx`, changes the `ml-60` → `ml-14` content offset, introduces 3 new components, and must settle before the market session bar can be placed in the header.

Key risks are well-understood and preventable. The top 3: (1) **Font variable collision** — `next/font` CSS variable and hardcoded `font-family` in `globals.css` compete, causing silent fallback to system fonts; fix by removing the hardcoded rule. (2) **Sidebar overlay blocking clicks** — expanded sidebar covers content with no dismiss mechanism; fix with a backdrop element. (3) **nuqs + next-intl provider ordering** — wrong nesting causes hydration mismatches; the correct order is `NextIntlClientProvider → ThemeProvider → QueryProvider → NuqsAdapter → AppShell`. All 3 are avoidable with the specific mitigations documented in PITFALLS.md.

## Key Findings

### Recommended Stack

The existing stack handles 95% of v1.3 needs. One new dependency, one shadcn add.

**Core technologies (existing — no changes):**
- **Next.js 16** (`next/font/google`): Self-hosts Source Sans 3, Vietnamese subset verified in font-data.json
- **Tailwind v4** (`@theme inline` in CSS): Color tokens via CSS variables, no `tailwind.config.ts` needed
- **@base-ui/react 1.4.0**: `tooltip/`, `collapsible/`, `progress/` primitives — all verified installed
- **TanStack Query 5.99.0**: Market metrics data fetching with `refetchInterval`
- **lucide-react 1.8.0**: Sidebar icons (PanelLeftClose/Open, ChevronLeft/Right)

**New additions:**
- **`nuqs` ^2.8.9** (only new npm dep): URL-based search/sort state persistence. Replaces `useState` in 3 components. Requires `<NuqsAdapter>` wrapper in layout.tsx. ~5KB gzipped.
- **`shadcn add tooltip`** (not a new npm dep): Styled wrapper over already-installed `@base-ui/react/tooltip`. Needed for collapsed sidebar icon labels.

**Explicitly rejected:** `@radix-ui/*` (conflicts with base-nova), `framer-motion` (CSS transitions suffice), `date-fns`/`dayjs` (`Intl.DateTimeFormat` handles timezone), `zustand`/`jotai` (URL state via nuqs is better), `@fontsource/*` (`next/font` handles self-hosting).

### Expected Features

All 7 features are committed scope per the v1.3 spec. No features are deferred.

**Must have (table stakes) — all 7:**

| # | Feature | Complexity | Key Constraint |
|---|---------|------------|----------------|
| 1 | Source Sans 3 font | Low | Vietnamese subset required; `next/font/google` handles it |
| 2 | Claude Desktop color palette | Low | Change 10 blue CSS vars to warm terracotta; backgrounds already warm |
| 3 | Sidebar float + collapse | **High** | Full rewrite: 3 new components, localStorage state, z-index layers |
| 4 | Fix table sort | Low | Bug fix — string vs number comparator |
| 5 | Search state persistence | Medium | `nuqs` replaces `useState` in 3 components + `NuqsAdapter` wrapper |
| 6 | Market session progress bar | Medium | HOSE hours 9:00–15:00 ICT, timezone via `Intl.DateTimeFormat` |
| 7 | Market overview metrics | Medium | **Blocked on new backend API** — `GET /api/market/summary` doesn't exist |

**Should have (differentiators — if time allows):**
- Sidebar keyboard shortcut (`Cmd+B` toggle)
- Search highlight in filtered results
- Session state transition toasts

**Anti-features (explicitly out of scope):**
- Mobile responsive layout (spec says desktop-only)
- WebSocket real-time data (polling via TanStack Query suffices)
- Custom charts for market overview (simple number cards)
- Theme variants beyond light/dark
- New navigation pages

### Architecture Approach

The architecture is a surgical modification of an existing, well-structured Next.js App Router app. The component tree stays the same — only the sidebar subtree gets replaced and the header gains a new child. All styling flows through CSS variables, so font and color changes require zero component modifications. The file change footprint is precise: **9 files modified, 7 files created, 1 file deleted**.

**Major components:**

1. **FloatingSidebar** (NEW — replaces `sidebar.tsx`): Container managing collapse state (`useState` + `localStorage`), active tab group, and expand/close behavior. Contains `IconRail` (w-14, always visible, z-30) and `SidebarPanel` (w-60, overlay, z-50).

2. **MarketSessionBar** (NEW — in header): Client-side HOSE session progress. Uses `Intl.DateTimeFormat` with `timeZone: 'Asia/Ho_Chi_Minh'`, updates via `setInterval(60s)`, renders status dot + label + progress bar + countdown.

3. **MarketMetrics** (NEW — on `/market` page): 4-card market summary (VN-Index, volume, advances/declines, breadth). Depends on new backend endpoint. Uses existing `Card` component + new TanStack Query hook.

4. **Search persistence layer**: `nuqs` `useQueryState` replaces `useState` in `admin/stock-table.tsx`, `learn/glossary-search.tsx`, and adds search to `rankings/stock-table.tsx`.

**Z-index layer system:**
```
z-0:  Content (default)
z-30: Icon rail (always visible)
z-40: Backdrop (dismiss overlay)
z-50: Sidebar panel (expanded)
z-50: Toaster/modals
```

**Provider nesting order (critical):**
```
NextIntlClientProvider → ThemeProvider → QueryProvider → NuqsAdapter → AppShell
```

### Critical Pitfalls

Research identified 10 pitfalls (3 critical, 4 moderate, 3 minor). The top 5 that must be addressed:

1. **Font variable collision** (Critical) — `next/font` sets `--font-sans` via className on `<html>`, but `globals.css` body rule has hardcoded `font-family: system-ui`. **Fix:** Remove the hardcoded `font-family` rule. **Detection:** DevTools Computed tab → check if body shows `"Source Sans 3"` or `system-ui`.

2. **Sidebar overlay blocks clicks** (Critical) — Expanded sidebar covers content with no dismiss mechanism. **Fix:** Add backdrop div (`fixed inset-0 z-30`) that collapses sidebar on click. Test by expanding sidebar and clicking content area.

3. **nuqs + next-intl provider ordering** (Critical) — Wrong nesting causes hydration mismatches or lost URL params. **Fix:** `NuqsAdapter` goes inside `QueryProvider`, outside `AppShell`. Test by navigating `/rankings?q=VNM` → `/market` → back → verify `q=VNM` survives.

4. **Warm primary color vs financial semantics** (Moderate) — Terracotta primary (~24° hue) could clash with `--stock-warning` (yellow ~48°) or `--chart-4` (existing terracotta ~15°). **Fix:** Target hue ~24° for separation from both. Visually test primary buttons next to stock-up/down/warning indicators.

5. **Sort state polluting browser history** (Moderate) — Every sort click with `nuqs` creates a history entry; "back" changes sort instead of navigating. **Fix:** Use `history: 'replace'` option for sort params; only search query `q` uses default `push`.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation — Font + Color Palette
**Rationale:** Every other feature inherits typography and color tokens. Screenshots and visual testing are meaningless until these are correct. Lowest risk, highest global impact.
**Delivers:** Source Sans 3 with Vietnamese subset active across all pages; warm terracotta accent replacing all 10 blue CSS variable values in both light and dark themes.
**Addresses:** Features #1 (font), #2 (colors)
**Avoids:** Pitfall #1 (font variable collision) — remove hardcoded font-family; Pitfall #4 (color semantic clash) — test warm accent against financial indicators
**Files touched:** `layout.tsx` (font import + className), `globals.css` (10 color vars + remove font-family rule)
**Complexity:** Low — 2 files, pure configuration

### Phase 2: Layout — Sidebar Float/Collapse
**Rationale:** Highest complexity feature. Restructures the app shell (`ml-60` → `ml-14`), which affects header width and content placement. Must settle before market session bar (which lives in the header).
**Delivers:** Collapsible floating sidebar with icon rail (always visible), expandable panel (overlay), 2 tab groups (Main/Admin), tooltip labels on collapsed icons, localStorage persistence.
**Addresses:** Feature #3 (sidebar)
**Avoids:** Pitfall #2 (overlay click blocking) — backdrop element; Pitfall #6 (collapse flash on load) — `useState` lazy initializer reading `localStorage` synchronously
**Files touched:** Delete `sidebar.tsx`; create `floating-sidebar.tsx`, `icon-rail.tsx`, `sidebar-panel.tsx`; modify `app-shell.tsx`
**Complexity:** High — 3 new components, z-index layering, CSS transitions, localStorage

### Phase 3: Feature Integration — Search, Sort, Session Bar
**Rationale:** These 3 features are independent of each other and can be developed in parallel within the phase. They all depend on the settled layout from Phase 2 (header structure, content area). Grouped because they're all medium/low complexity frontend-only work.
**Delivers:** URL-persisted search across rankings/admin/learn pages; fixed string vs number sort comparator; live HOSE market session progress bar in header with timezone-aware countdown.
**Addresses:** Features #4 (sort fix), #5 (search persistence), #6 (market session bar)
**Avoids:** Pitfall #3 (nuqs provider ordering) — correct nesting; Pitfall #5 (timezone assumptions) — always `Intl.DateTimeFormat`; Pitfall #7 (sort history pollution) — `history: 'replace'`; Pitfall #9 (useless closed-hours bar) — show "Opens in Xh Ym" countdown
**Files touched:** Install `nuqs`; add `NuqsAdapter` to layout; modify 3 search components; fix sort in `stock-table.tsx`; create `market-session-bar.tsx`; modify header in `app-shell.tsx`
**Complexity:** Medium — multiple independent workstreams, nuqs is the only new dependency

### Phase 4: Market Metrics + Polish
**Rationale:** Market overview metrics depend on a **new backend API endpoint** (`GET /api/market/summary`) that doesn't exist. This is the only feature with an external dependency. Place it last so backend work can happen in parallel during Phases 1–3. Polish tasks (i18n keys, visual QA) naturally follow.
**Delivers:** 4-card market overview on `/market` page (VN-Index, volume, advances/declines, breadth); graceful fallback if API not ready; final visual polish.
**Addresses:** Feature #7 (market metrics)
**Avoids:** Pitfall #10 (backend not ready) — build with skeleton → error → "Coming soon" fallback; define API contract upfront for parallel backend work
**Files touched:** Create `market-metrics.tsx`; add `useMarketSummary()` to `queries.ts`; add `MarketSummary` type; modify `/market/page.tsx`; backend: create `api/routes/market.py`
**Complexity:** Medium — frontend straightforward, backend dependency is the risk

### Phase Ordering Rationale

- **Foundation before everything** — CSS variables cascade globally. Wrong font or wrong color makes all visual testing invalid.
- **Sidebar before session bar** — Session bar lives in the header, which is restructured by the sidebar rewrite (`ml-60` → `ml-14`). Building the session bar before the sidebar is stable creates rework.
- **Search/sort/session bar grouped** — All independent, all frontend-only, all medium/low complexity. Can be parallelized within the phase.
- **Market metrics last** — Only feature requiring new backend code. Placing it last gives maximum time for backend API to be built in parallel. If backend isn't ready, the frontend still ships with graceful fallback.

### Research Flags

**Phases with standard patterns (skip `/gsd-research-phase`):**
- **Phase 1 (Foundation):** `next/font/google` and CSS variable theming are well-documented, verified patterns. Font data confirmed in `node_modules`.
- **Phase 3 (Search/Sort/Session):** `nuqs` has excellent docs, sort fix is a simple code change, `Intl.DateTimeFormat` is standard API.

**Phases that may benefit from brief research during planning:**
- **Phase 2 (Sidebar):** The floating sidebar with icon rail + overlay panel + tab groups is a custom pattern, not a standard shadcn component. Z-index layering, CSS transitions, and the backdrop dismiss pattern need careful implementation. Consider researching existing icon-rail sidebar implementations if the implementer hasn't built one before.
- **Phase 4 (Market Metrics):** The backend API contract (`GET /api/market/summary`) needs to be defined. Research what data is available in existing DB tables to compute VN-Index, volume, advances/declines without adding new crawlers.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All primitives verified in `node_modules/`. Font subset confirmed in font-data.json. `nuqs` is the only new dep and is well-documented. |
| Features | **HIGH** | All 7 features clearly specified in project milestone. Dependency graph is straightforward. No ambiguity in scope. |
| Architecture | **HIGH** | Based on direct codebase inspection. File change map (9 modify, 7 create, 1 delete) is precise. Provider ordering verified against existing layout.tsx. |
| Pitfalls | **HIGH** | All 10 pitfalls come from direct code inspection and known patterns. Prevention strategies are specific and testable. |

**Overall confidence: HIGH** — This is a well-scoped UI polish milestone on a mature codebase with a known stack. No speculative technology choices. All assertions verified against actual source code and `node_modules/`.

### Gaps to Address

1. **Backend API contract for market metrics** — `GET /api/market/summary` needs a defined response schema. The frontend can be built against a type interface, but the backend computation (VN-Index from individual stock prices? aggregate volume?) needs clarification. **Action:** Define the API contract in Phase 1/2 so backend work can begin in parallel.

2. **Exact warm terracotta HSL values** — Research recommends ~`hsl(24 70% 50%)` for primary accent, but the exact values for both light and dark themes need visual tuning against the existing warm backgrounds (`hsl(48 33.3% 97.1%)`) and financial indicators. **Action:** Create a color test page or Storybook story during Phase 1 implementation to dial in the exact values.

3. **Sidebar behavior on narrow desktop viewports** — Spec says "no mobile," but what happens on a 1280px laptop screen with sidebar expanded (240px overlay)? Is the backdrop sufficient, or should auto-collapse trigger below a breakpoint? **Action:** Decide during Phase 2 planning — likely auto-collapse below ~1440px is prudent.

4. **Holiday/weekend awareness for session bar** — PITFALLS.md mentions showing "Reopens Monday" on weekends. The backend has a `holidays` package, but there's no `is_trading_day` endpoint exposed. **Action:** Either add a simple backend endpoint or hardcode Vietnamese market holidays in the frontend for v1.3.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `layout.tsx`, `app-shell.tsx`, `sidebar.tsx`, `globals.css`, `stock-table.tsx`, all `components/ui/*`
- `node_modules/next/dist/compiled/@next/font/dist/google/font-data.json` — Source Sans 3 Vietnamese subset confirmed
- `node_modules/@base-ui/react/` — tooltip, collapsible, progress primitives verified
- `apps/prometheus/src/localstock/scheduler/calendar.py` — HOSE trading hours
- `apps/prometheus/src/localstock/api/routes/*.py` — confirmed no market summary endpoint exists

### Secondary (MEDIUM confidence)
- `nuqs` v2.8.9 npm registry and documentation — history mode options, adapter patterns
- Claude Desktop UI reference — warm neutral palette principles (hue ranges approximate)
- MDN `Intl.DateTimeFormat.formatToParts()` — timezone handling patterns

---
*Research completed: 2026-04-24*
*Ready for roadmap: yes*
