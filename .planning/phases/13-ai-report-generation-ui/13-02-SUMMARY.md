---
phase: 13-ai-report-generation-ui
plan: 02
subsystem: helios-report-ui-components
tags: [report-progress, job-detail-page, pipeline-control, navigation]
dependency_graph:
  requires:
    - "Sheet, Progress, step-active-pulse (Plan 01)"
    - "17 admin.report.* i18n keys (Plan 01)"
  provides:
    - "ReportProgress step indicator component"
    - "Job detail page at /admin/jobs/[id]"
    - "Pipeline Report button navigates to job page after trigger"
    - "JobMonitor view-detail button per row"
    - "5 admin.jobs.* i18n keys in en.json and vi.json"
  affects:
    - "apps/helios/src/app/admin/page.tsx (simplified, no sheet state)"
    - "apps/helios/src/components/admin/pipeline-control.tsx (navigation)"
    - "apps/helios/src/components/admin/job-monitor.tsx (view button)"
tech_stack:
  added: []
  patterns:
    - "Next.js dynamic route [id] for job detail"
    - "TanStack Query refetchInterval function for conditional polling"
---

## Execution Summary

### Design Pivot
Original plan specified a Sheet (right drawer) for report progress and preview. During execution, user requested replacement with a dedicated job detail page at `/admin/jobs/[id]`. This provides a better UX with full-page layout for report viewing.

### Tasks Completed

**Task 1 — Components (original)**
- Created `report-progress.tsx`: Step indicator with Queued → Generating → Complete states, uses step-active-pulse animation
- Created `report-preview.tsx`: Wrapper for AIReportPanel with useStockReport fetch (later removed in design pivot)
- Created `report-generation-sheet.tsx`: Sheet container with SheetState state machine (later removed in design pivot)

**Task 2 — Wiring (original)**
- Wired ReportGenerationSheet into AdminPage with sheetState management
- Extended PipelineControl with onReportTriggered callback
- Added report job status tracking in handleTransition

**Design Pivot — Drawer → Job Detail Page**
- Created `/admin/jobs/[id]/page.tsx` with:
  - Job metadata grid (type, symbols, created, duration)
  - ReportProgress for active report jobs
  - AIReportPanel for completed reports with "View Stock Page" link
  - Error display for failed jobs
  - Generic JSON result display for non-report jobs
- Updated `pipeline-control.tsx`:
  - Report button now navigates to `/admin/jobs/${id}` after triggering
  - Removed `reportMinimized`/`onReportReopen` props
  - Added `useRouter` for navigation
- Updated `job-monitor.tsx`:
  - Added ExternalLink view button per row → navigates to detail page
  - Added extra column header for view button
- Cleaned up `admin/page.tsx`:
  - Removed all sheet state management
  - Removed ReportGenerationSheet import and render
  - Simplified handleTransition (no more report sheet state updates)
- Deleted unused components:
  - `report-generation-sheet.tsx`
  - `report-preview.tsx`
- Updated `useAdminJobDetail` with `refetchInterval` function for auto-polling active jobs
- Added i18n keys: `admin.jobs.detailTitle`, `.backToAdmin`, `.notFound`, `.result`, `.viewDetail`, `.columns.symbols`

**Task 3 — Checkpoint (adjusted)**
- Manual verification deferred (design changed from original plan)
- TypeScript compiles cleanly after all changes

### Deviations from Plan
| Deviation | Reason | Impact |
|-----------|--------|--------|
| Sheet replaced with job detail page | User requested better UX for report viewing | Positive — full page layout, cleaner navigation |
| report-generation-sheet.tsx deleted | No longer needed with page approach | Reduced complexity |
| report-preview.tsx deleted | Job detail page fetches report directly | Reduced indirection |
| "minimized" state removed | No longer relevant with page navigation | Simplified state management |

### Commits
- `1d81dbc` feat(13-02): create ReportProgress, ReportPreview, ReportGenerationSheet components
- `353ea6a` feat(13-02): wire ReportGenerationSheet into PipelineControl and AdminPage
- `219d74b` feat(13): allow reopening report sheet after closing during generation
- `dff425b` feat(13): replace report drawer with dedicated job detail page
