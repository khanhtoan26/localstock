# Phase 12: Admin Console UI - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Web-based admin console at `/admin` for managing tracked stocks, triggering pipeline operations (crawl, analyze, score, report, full pipeline), and monitoring background job status. Single Next.js page with tabbed interface. Consumes the 10 admin API endpoints built in Phase 11.

</domain>

<decisions>
## Implementation Decisions

### Page Layout
- **D-01:** Single page at `/admin` with Tabs component (3 tabs: Stocks, Pipeline, Jobs). Add "Admin" nav item to sidebar with Settings/Shield icon. No sub-pages — everything on one page for quick access.

### Stock Table
- **D-02:** Table of tracked stocks with inline add form at the top (Input field + "Add" button). Each row has a Remove (x) button. Symbol input validates uppercase pattern (matching backend `^[A-Z0-9]+$`). Shows symbol, name, exchange, industry columns.

### Pipeline Triggers
- **D-03:** Checkbox selection in stock table rows. Action buttons (Crawl, Analyze, Score) operate on selected stocks. Pipeline button runs full pipeline for all tracked stocks. Buttons disabled when no stocks selected (except Pipeline). Each trigger returns job_id, switches user to Jobs tab to monitor.

### Job Monitor
- **D-04:** Table of recent jobs (from GET /api/admin/jobs) showing job_type, status, duration, created_at. Polling every 3 seconds via TanStack Query `refetchInterval` when any job has status='running' or 'pending'. Auto-stops polling when all jobs are done/failed. Click row to expand details (result/error from GET /api/admin/jobs/{id}).

### Agent's Discretion
- Component file structure (one file per tab vs separate files)
- Status badge colors (green=completed, red=failed, yellow=running, etc.)
- Empty state messaging
- Toast notifications for trigger confirmations
- i18n keys structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Admin API (Phase 11 output)
- `apps/prometheus/src/localstock/api/routes/admin.py` — All 10 admin endpoints, request/response schemas
- `apps/prometheus/src/localstock/services/admin_service.py` — Background task patterns
- `apps/prometheus/src/localstock/db/models.py` — AdminJob model (job_type, status, params, result, error fields)

### Frontend Patterns
- `apps/helios/src/components/layout/sidebar.tsx` — Sidebar nav items pattern (add Admin here)
- `apps/helios/src/lib/api.ts` — `apiFetch<T>()` client for backend calls
- `apps/helios/src/lib/queries.ts` — TanStack Query hooks pattern
- `apps/helios/src/lib/types.ts` — TypeScript types for API responses
- `apps/helios/src/components/ui/table.tsx` — Table component
- `apps/helios/src/components/ui/tabs.tsx` — Tabs component
- `apps/helios/src/components/ui/input.tsx` — Input component
- `apps/helios/src/components/ui/button.tsx` — Button component
- `apps/helios/src/components/ui/badge.tsx` — Badge component (for status indicators)

### i18n
- `apps/helios/messages/en.json` — English translations
- `apps/helios/messages/vi.json` — Vietnamese translations

### Existing Page Pattern
- `apps/helios/src/app/rankings/page.tsx` — Reference for page structure with data fetching
- `apps/helios/src/components/rankings/` — Reference for component organization

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Tabs` component — already exists in `ui/tabs.tsx`, ready to use for 3-tab layout
- `Table` component — already exists in `ui/table.tsx`, used in rankings
- `Badge` component — for status indicators (running, completed, failed)
- `Button`, `Input` — standard form components
- `apiFetch<T>()` — generic typed API client
- `useQuery`/`useMutation` from TanStack Query — established data fetching pattern
- i18n with `useTranslations()` hook — all UI text must be translated

### Established Patterns
- **Data fetching:** TanStack Query hooks in `lib/queries.ts`
- **Styling:** Tailwind CSS 4 with CSS variables (`text-primary`, `bg-card`, `border-border`)
- **Components:** Client components with `"use client"` directive
- **Navigation:** Sidebar with icon + label, active state highlighting via pathname

### Integration Points
- Sidebar: Add admin nav item in `sidebar.tsx` navItems array
- API types: Add admin types to `lib/types.ts`
- Query hooks: Add admin hooks to `lib/queries.ts`
- New page: Create `app/admin/page.tsx`
- i18n: Add admin keys to both `en.json` and `vi.json`

</code_context>

<specifics>
## Specific Ideas

- Pipeline tab with checkbox selection from stock table — cross-tab stock selection reuses stock list data
- Jobs tab auto-switches to foreground and starts polling when user triggers an operation
- Keep UI consistent with existing dark theme (Tailwind CSS 4 variables)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-admin-console-ui*
*Context gathered: 2026-04-22*
