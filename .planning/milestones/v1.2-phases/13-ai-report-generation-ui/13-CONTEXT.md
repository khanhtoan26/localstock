# Phase 13: AI Report Generation UI - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add AI report generation capability to the admin console. Users can select stocks in the Pipeline tab, click "Report" to trigger Ollama-based report generation, and preview the generated report in a modal/drawer — all without leaving the admin page. Leverages existing backend endpoints (POST /api/admin/report), TanStack Query hooks (useTriggerAdminReport), and Phase 12.1 infrastructure (toast notifications, cache invalidation, job transitions).

</domain>

<decisions>
## Implementation Decisions

### Report Trigger
- **D-01:** Add "Report" button to Pipeline tab alongside existing Crawl, Analyze, Score buttons. Uses the same checkbox selection pattern — select stocks, click Report, creates job(s). Button disabled when no stocks selected.

### Progress Display
- **D-02:** Modal/drawer shows realtime progress from Ollama while LLM is generating. Opens automatically when Report is triggered. Stays open until generation completes.
- **D-02a:** Progress display style is agent's discretion — streaming text, progress steps, or combination. Optimize for smooth UX.

### Report Preview
- **D-03:** Generated report displays directly in the modal/drawer after completion — no redirect to stock page. User reads the report in-context without leaving admin.
- **D-03a:** Report content layout is agent's discretion. Priority: smooth, fast rendering. Can reuse AIReportPanel or design optimized layout for modal context.

### Batch Behavior
- **D-04:** Batch generation via checkbox selection. Multiple stocks → jobs created sequentially (not parallel). Each job tracked in Jobs tab as usual. Modal shows progress for current stock being generated.

### Agent's Discretion
- Modal/drawer component choice (Sheet from shadcn vs custom Dialog)
- Streaming implementation approach (SSE, polling, or WebSocket)
- Progress UI style (streaming text, step indicators, or combination)
- Report content rendering (reuse AIReportPanel or custom layout)
- Whether to add a "Generate Report" shortcut in Stocks tab per-row
- i18n keys structure for report generation UI
- Error states (Ollama offline, generation timeout)
- How batch progress is communicated (one modal per stock or aggregate view)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend API (existing)
- `apps/prometheus/src/localstock/api/routes/admin.py` — POST /api/admin/report endpoint, TriggerRequest schema
- `apps/prometheus/src/localstock/services/admin_service.py` — run_report() background task, ReportService integration
- `apps/prometheus/src/localstock/services/report_service.py` — generate_for_symbol() Ollama integration
- `apps/prometheus/src/localstock/ai/prompts.py` — Vietnamese system prompts for reports

### Frontend (existing, to integrate with)
- `apps/helios/src/lib/queries.ts` — useTriggerAdminReport(), useStockReport(), invalidateForJob("report")
- `apps/helios/src/lib/types.ts` — StockReport interface, AdminJob type
- `apps/helios/src/hooks/use-job-transitions.ts` — Job transition detection hook (Phase 12.1)
- `apps/helios/src/app/admin/page.tsx` — Admin page shell, tab state, toast + transition wiring
- `apps/helios/src/components/admin/job-monitor.tsx` — Job monitor with row highlight
- `apps/helios/src/components/stock/ai-report-panel.tsx` — Existing report display component

### UI Patterns
- `apps/helios/src/app/globals.css` — job-highlight animation (Phase 12.1)
- `apps/helios/messages/en.json` — i18n pattern for admin toast keys
- `apps/helios/messages/vi.json` — Vietnamese i18n keys

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useTriggerAdminReport()` — mutation hook ready to call POST /api/admin/report
- `invalidateForJob("report", symbols)` — auto-invalidates report query cache when job completes
- `useJobTransitions` — detects job completion, fires toast with "View job" action
- `AIReportPanel` — renders StockReport with markdown, score badges, recommendation
- Pipeline tab checkbox selection pattern — reuse for Report button
- `GlossaryMarkdown` — renders report text with interactive glossary links

### Established Patterns
- Action buttons in Pipeline tab: disabled when no selection, call mutation, switch to Jobs tab
- Job lifecycle: trigger → pending → running → completed/failed → toast notification
- Phase 12.1 toast: success (5s) / error (8s) with action button

### Integration Points
- Pipeline tab: add Report button next to Score button
- Modal/drawer: new component, triggered by Report action or toast "View" action
- Backend: may need SSE/streaming endpoint for realtime Ollama output (new endpoint)

</code_context>

<specifics>
## Specific Ideas

- User wants modal/drawer with realtime progress — not just a spinner
- UX must feel "mượt" (smooth) — prioritize rendering performance
- Batch generates sequentially, not in parallel (Ollama is single-threaded)
- Report stays viewable in modal after generation — no forced redirect

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-ai-report-generation-ui*
*Context gathered: 2026-04-23*
