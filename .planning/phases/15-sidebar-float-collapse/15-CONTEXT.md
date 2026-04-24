# Phase 15: Sidebar Float & Collapse - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current fixed `w-60` sidebar with a floating, collapsible sidebar that defaults to an icon rail (~56px). Clicking a nav icon opens a full overlay panel (slide-in from left). The sidebar has two tab groups: Main (Rankings, Market, Learn) and Admin. Collapsed/expanded state persists via localStorage. Content area uses full width — no `ml-60` offset.

</domain>

<decisions>
## Implementation Decisions

### Icon Rail (Collapsed State)
- **D-01:** Collapsed sidebar shows only navigation icons (~56px wide). Each icon displays a tooltip on hover showing the page name.
- **D-02:** No logo/branding in the collapsed icon rail — just nav icons. The "LocalStock" + "AI Stock Agent" header only appears when expanded.
- **D-03:** No badge indicators on icons. Keep it clean and minimal.

### Tab Group Layout
- **D-04:** Agent's discretion on how to visually separate Main (Rankings, Market, Learn) from Admin group — divider line, spacing, or Admin pinned to bottom of rail are all acceptable approaches.
- **D-05:** Agent's discretion on Admin icon position in the rail — bottom-pinned or below Main group with separator.

### Expand/Collapse Interaction
- **D-06:** Click on any nav icon in the collapsed rail → sidebar expands as a floating overlay panel (positioned to the right of the icon rail). Content underneath is NOT pushed.
- **D-07:** No backdrop overlay when sidebar is expanded. Close by clicking any nav icon again (toggle behavior).
- **D-08:** Slide-in animation from left, smooth transition 150-200ms duration.
- **D-09:** Default state (first visit, no localStorage) is collapsed (icon rail only).

### Persistence
- **D-10:** Collapsed/expanded state persists via localStorage. On page reload, sidebar restores to the last user state.

### Agent's Discretion
- Visual separation approach for Main vs Admin groups (divider, spacing, or position)
- Admin icon position (bottom-pinned vs below Main)
- Exact icon rail width (target ~56px, adjust for visual balance)
- Overlay panel width (match current `w-60` or adjust)
- Z-index layering for overlay panel
- Transition easing function
- Whether clicking a nav link also collapses the sidebar or keeps it open

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current Layout
- `apps/helios/src/components/layout/sidebar.tsx` — Current fixed sidebar (w-60, 4 nav items, flat list)
- `apps/helios/src/components/layout/app-shell.tsx` — Content offset `ml-60`, header layout, Toaster placement
- `apps/helios/src/app/layout.tsx` — Provider ordering (NextIntlClientProvider → ThemeProvider → QueryProvider → AppShell)

### Theme System (Phase 14)
- `apps/helios/src/app/globals.css` — Neutral palette CSS variables (sidebar-specific: --sidebar, --sidebar-foreground, --sidebar-primary, --sidebar-accent, --sidebar-border)
- `.planning/phases/14-visual-foundation/14-CONTEXT.md` — Neutral palette decisions

### Research
- `.planning/research/SUMMARY.md` — v1.3 research synthesis (sidebar complexity assessment)
- `.planning/research/PITFALLS.md` — Sidebar pitfalls (7 identified, highest risk component)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lucide-react` icons already imported (BarChart3, Globe, BookOpen, Shield) — reuse for icon rail
- `cn()` utility from `@/lib/utils` for conditional classes
- `usePathname()` for active state detection — reuse in icon rail
- `useTranslations("nav")` for i18n labels — reuse for tooltips
- CSS variables `--sidebar`, `--sidebar-foreground`, `--sidebar-primary`, `--sidebar-accent`, `--sidebar-border` already defined in globals.css

### Established Patterns
- Client components use `"use client"` directive
- Navigation uses Next.js `Link` component with `pathname.startsWith(href)` for active detection
- Theme follows CSS variable approach — no hardcoded colors

### Integration Points
- `app-shell.tsx` must remove `ml-60` and restructure layout for icon rail + overlay
- `sidebar.tsx` needs full rewrite — new state management (useState + localStorage), new render paths (collapsed vs expanded)
- No changes needed to page components — layout restructuring is transparent to pages

</code_context>

<specifics>
## Specific Ideas

- Claude Desktop-inspired clean aesthetic — icon rail should feel minimal and professional
- User explicitly rejected backdrop overlay — just toggle open/close via icon click
- Default collapsed matches the "tool stays out of the way" philosophy

</specifics>

<deferred>
## Deferred Ideas

- **LAY-05:** Keyboard shortcut (Cmd+B) to toggle sidebar — future requirement
- **LAY-06:** Mobile responsive sidebar (drawer pattern) — future requirement

</deferred>

---

*Phase: 15-sidebar-float-collapse*
*Context gathered: 2026-04-24*
