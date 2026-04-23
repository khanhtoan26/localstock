# Phase 13: AI Report Generation UI - Research

**Researched:** 2026-04-23
**Domain:** React UI — admin console Sheet drawer, job polling integration, report preview
**Confidence:** HIGH

## Summary

Phase 13 thêm khả năng tạo báo cáo AI vào admin console. Backend đã hoàn chỉnh: `POST /api/admin/report` tạo job, worker chạy Ollama sinh report, lưu DB. Frontend đã có `useTriggerAdminReport()` mutation, `useJobTransitions` hook phát hiện job hoàn thành, `invalidateForJob("report")` tự xóa cache, và `AIReportPanel` render report. Phase này cần xây 3 component mới (ReportGenerationSheet, ReportProgress, ReportPreview), cài 2 shadcn component (Sheet, Progress), và wire vào admin page.

Toàn bộ phase là pure-frontend, không cần thay đổi backend. Pattern polling 3s đã tồn tại (`useAdminJobs` refetchInterval) cung cấp realtime-enough progress. `useJobTransitions` hook sẽ trigger chuyển sheet từ "generating" sang "completed". Report data fetch qua `useStockReport(symbol)` đã có cache invalidation tự động khi job hoàn thành.

**Primary recommendation:** Dùng shadcn Sheet (right drawer) + state machine đơn giản (CLOSED → GENERATING → COMPLETED/FAILED) quản lý flow. Reuse AIReportPanel cho report preview. Không cần SSE/WebSocket — polling 3s đủ cho Ollama generation time 30-120s.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add "Report" button to Pipeline tab alongside existing Crawl, Analyze, Score buttons. Uses the same checkbox selection pattern — select stocks, click Report, creates job(s). Button disabled when no stocks selected.
- **D-02:** Modal/drawer shows realtime progress from Ollama while LLM is generating. Opens automatically when Report is triggered. Stays open until generation completes.
- **D-02a:** Progress display style is agent's discretion — streaming text, progress steps, or combination. Optimize for smooth UX.
- **D-03:** Generated report displays directly in the modal/drawer after completion — no redirect to stock page. User reads the report in-context without leaving admin.
- **D-03a:** Report content layout is agent's discretion. Priority: smooth, fast rendering. Can reuse AIReportPanel or design optimized layout for modal context.
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADMIN-08 | Users can generate and preview AI reports for any tracked stock from the admin console | Sheet component + AIReportPanel reuse + useTriggerAdminReport mutation + useJobTransitions hook. All pieces exist — phase wires them together with progress UI. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Report generation trigger (UI button) | Browser / Client | — | Pipeline tab already has the pattern; add Report button with same mutation flow |
| Job progress tracking | Browser / Client | API / Backend | Frontend polls existing `/api/admin/jobs` at 3s; backend provides job status — no new endpoint needed |
| Report preview rendering | Browser / Client | — | `AIReportPanel` + `GlossaryMarkdown` render markdown on client; report data fetched via existing `useStockReport()` |
| Report generation execution | API / Backend | — | Already implemented: `AdminService.run_report()` → `ReportService.generate_for_symbol()` → Ollama. No backend changes. |
| Sheet state management | Browser / Client | — | Local React state + useJobTransitions callback. No server state needed for UI flow. |

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @base-ui/react | ^1.4.0 | Primitive components (Sheet is Dialog primitive) | shadcn base-nova style depends on it [VERIFIED: apps/helios/package.json] |
| @tanstack/react-query | ^5.99.0 | Data fetching, polling, cache invalidation | Already powers all admin data flow [VERIFIED: apps/helios/package.json] |
| next-intl | ^4.9.1 | i18n — all UI text through translation keys | Already used for all admin console copy [VERIFIED: apps/helios/package.json] |
| react-markdown | ^10.1.0 | Report content rendering (via GlossaryMarkdown) | Already renders AI reports in stock pages [VERIFIED: apps/helios/package.json] |
| sonner | ^2.0.7 | Toast notifications | Already used for job transition toasts [VERIFIED: apps/helios/package.json] |
| lucide-react | ^1.8.0 | Icons (AlertCircle, Check, Loader2, FileText) | Already used across entire admin UI [VERIFIED: apps/helios/package.json] |

### To Install (shadcn Components)

| Component | Install Command | Purpose | Primitive |
|-----------|----------------|---------|-----------|
| Sheet | `npx shadcn@latest add sheet` | Right-side drawer for report progress + preview | `@base-ui/react/dialog` [VERIFIED: shadcn --view output] |
| Progress | `npx shadcn@latest add progress` | Determinate progress bar for batch progress | `@base-ui/react/progress` [VERIFIED: shadcn --view output] |

**Note:** Sheet and Progress components are NOT currently installed. [VERIFIED: ls src/components/ui/ — neither sheet.tsx nor progress.tsx exists]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sheet (right drawer) | Dialog (modal) | Sheet provides more vertical space for report content, matches stock page drawer pattern from Phase 8. Dialog would block the full viewport. Sheet is better. |
| Polling (3s) | SSE/WebSocket | Backend doesn't expose token-level streaming, only job status. Polling is already implemented with `useAdminJobs` refetchInterval. Adding SSE would require new backend endpoint for no meaningful UX benefit given 30-120s generation time. |
| Step indicator | Streaming text preview | Backend only reports job status (pending/running/completed/failed), not per-token output. Step indicator matches available data granularity. |

**Installation:**
```bash
cd apps/helios
NODE_TLS_REJECT_UNAUTHORIZED=0 npx shadcn@latest add sheet progress
```

**Note about TLS:** Current environment requires `NODE_TLS_REJECT_UNAUTHORIZED=0` for shadcn registry access (self-signed certificate issue). [VERIFIED: direct test against shadcn registry]

## Architecture Patterns

### System Architecture Diagram

```
User clicks "Report" in Pipeline tab
         │
         ▼
┌──────────────────────┐     POST /api/admin/report
│  PipelineControl     │─────────────────────────────►┌─────────────────┐
│  (useTriggerAdmin    │                               │ Backend creates │
│   Report mutation)   │◄──── TriggerResponse ─────────│ job (pending)   │
└──────────────────────┘     { job_id, status }        └─────────────────┘
         │
         │ onSuccess → open sheet
         ▼
┌──────────────────────┐     3s polling via useAdminJobs
│  ReportGeneration    │◄──────────────────────────────┐
│  Sheet               │     GET /api/admin/jobs       │
│  ┌─────────────────┐ │                               │ Worker picks up
│  │ ReportProgress  │ │   job.status transitions:     │ pending job,
│  │ (step indicator)│ │   pending → running → done    │ runs Ollama
│  └─────────────────┘ │                               └─────────────────┐
│  ┌─────────────────┐ │                                                 │
│  │ ReportPreview   │ │◄── useStockReport(symbol) ── GET /api/reports/X │
│  │ (AIReportPanel) │ │    (after job completes,                        │
│  └─────────────────┘ │     cache auto-invalidated)                     │
└──────────────────────┘                                                 │
         ▲                                                               │
         │ useJobTransitions detects                                     │
         │ completed/failed status ─── triggers sheet state transition   │
```

### Recommended Project Structure

```
src/
├── components/
│   ├── admin/
│   │   ├── pipeline-control.tsx      # MODIFY: add sheet open callback + job_id tracking
│   │   ├── report-generation-sheet.tsx # NEW: main sheet container
│   │   ├── report-progress.tsx        # NEW: step indicator UI
│   │   └── report-preview.tsx         # NEW: wraps AIReportPanel for sheet context
│   ├── stock/
│   │   └── ai-report-panel.tsx        # REUSE: render completed report
│   └── ui/
│       ├── sheet.tsx                  # NEW: shadcn Sheet component (install)
│       └── progress.tsx              # NEW: shadcn Progress component (install)
├── app/
│   └── admin/
│       └── page.tsx                   # MODIFY: wire sheet state + useJobTransitions integration
└── messages/
    ├── en.json                        # MODIFY: add admin.report.* keys
    └── vi.json                        # MODIFY: add admin.report.* keys
```

### Pattern 1: Sheet State Machine

**What:** Quản lý trạng thái sheet bằng state machine đơn giản thay vì boolean flags rời rạc.
**When to use:** Khi UI có nhiều trạng thái chuyển tiếp logic (closed → generating → completed/failed).

```typescript
// Source: Derived from UI-SPEC state machine + existing codebase patterns
type SheetState =
  | { status: "closed" }
  | { status: "generating"; symbols: string[]; jobId: number; currentIndex: number }
  | { status: "completed"; symbols: string[]; lastSymbol: string }
  | { status: "failed"; symbols: string[]; failedSymbol: string; error?: string };
```

State transitions:
- `CLOSED` → `GENERATING`: When Report button clicked + mutation succeeds
- `GENERATING` → `COMPLETED`: When `useJobTransitions` detects job completed
- `GENERATING` → `FAILED`: When `useJobTransitions` detects job failed
- `FAILED` → `GENERATING`: When user clicks Retry
- Any → `CLOSED`: When user clicks X/overlay/Escape

### Pattern 2: Job-to-Sheet Wiring via useJobTransitions

**What:** Extend existing `handleTransition` callback in AdminPage to update sheet state alongside toast notifications.
**When to use:** When job transitions need to drive multiple UI effects simultaneously.

```typescript
// Source: Existing pattern in apps/helios/src/app/admin/page.tsx
const handleTransition = useCallback(
  ({ job }: { job: AdminJob }) => {
    // 1. Existing: cache invalidation
    invalidateForJob(queryClient, job);
    
    // 2. Existing: toast notification
    // ... (current toast logic)
    
    // 3. NEW: update sheet state if this job matches tracked report job
    if (job.job_type === "report" && sheetState.status === "generating") {
      if (job.id === sheetState.jobId) {
        if (job.status === "completed") {
          const symbols = getJobSymbols(job);
          setSheetState({
            status: "completed",
            symbols,
            lastSymbol: symbols[symbols.length - 1] || "",
          });
        } else if (job.status === "failed") {
          setSheetState({
            status: "failed",
            symbols: sheetState.symbols,
            failedSymbol: sheetState.symbols[sheetState.currentIndex] || "",
          });
        }
      }
    }
  },
  [queryClient, t, sheetState],
);
```

### Pattern 3: PipelineControl → AdminPage Communication

**What:** PipelineControl needs to communicate the triggered job_id and symbols to AdminPage for sheet tracking.
**When to use:** When child component triggers action that parent needs to track.

```typescript
// Source: Existing onOperationTriggered callback pattern in pipeline-control.tsx
interface PipelineControlProps {
  onOperationTriggered: () => void;
  // NEW: callback for report specifically
  onReportTriggered?: (data: { jobId: number; symbols: string[] }) => void;
}

// In PipelineControl, Report button handler:
triggerReport.mutate([...validSelected], {
  onSuccess: (data: TriggerResponse) => {
    handleSuccess(t("pipeline.report"));
    // NEW: notify parent with job details
    onReportTriggered?.({ jobId: data.job_id, symbols: [...validSelected] });
  },
  onError: handleMutationError,
});
```

### Pattern 4: Report Fetch After Job Completion

**What:** After job completes, report data is fetched via `useStockReport(symbol)`. Cache is already invalidated by `invalidateForJob` → data is fresh.
**When to use:** In ReportPreview component when sheet transitions to "completed" state.

```typescript
// Source: Existing pattern in apps/helios/src/lib/queries.ts
// useStockReport already handles:
// - queryKey: ["report", symbol]
// - auto-refetch after invalidateForJob clears cache
// - staleTime: 5 min
// ReportPreview just needs to call:
const { data: report, isLoading, isError } = useStockReport(symbol);
// Then pass to AIReportPanel
```

### Anti-Patterns to Avoid

- **Direct mutation state as progress:** Don't use `triggerReport.isPending` as the sole progress indicator. The mutation completes immediately (backend returns job_id); actual progress comes from job polling. [VERIFIED: backend creates pending job and returns immediately]
- **New polling hooks:** Don't create a separate polling mechanism for report status. `useAdminJobs` already polls at 3s when active jobs exist, and `useJobTransitions` detects completions. Reuse these. [VERIFIED: apps/helios/src/lib/queries.ts L229-237]
- **Fetching report before job completes:** Don't call `useStockReport` while job is still running — report doesn't exist yet. Only fetch after `useJobTransitions` fires with `status: "completed"`. [VERIFIED: report is written to DB only after Ollama completes]
- **Multiple sheets for batch:** Per D-04, batch generates sequentially with one sheet showing aggregate progress, not one sheet per stock. [VERIFIED: CONTEXT.md D-04]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Right drawer/sheet | Custom overlay + slide animation | `shadcn Sheet` (wraps @base-ui/react Dialog) | Focus trap, Escape, overlay click, enter/exit animations, portal, all built-in [VERIFIED: shadcn --view output] |
| Progress bar | Custom div with width transition | `shadcn Progress` (wraps @base-ui/react Progress) | Accessible `aria-valuenow/min/max`, ARIA label, smooth transitions [VERIFIED: shadcn --view output] |
| Job status polling | Custom setInterval + fetch | `useAdminJobs` existing refetchInterval | Already polls at 3s when active jobs exist, stops when idle [VERIFIED: queries.ts L229-237] |
| Job transition detection | Comparing job lists manually | `useJobTransitions` hook | Already handles initial-load skip, prev-state diffing, transition batching [VERIFIED: use-job-transitions.ts] |
| Report rendering | Custom markdown renderer | `AIReportPanel` + `GlossaryMarkdown` | Handles recommendation badge, grade, score, T+3, markdown with glossary links [VERIFIED: ai-report-panel.tsx] |
| Toast notifications | Custom notification system | `sonner` (via `toast`) | Already integrated, matches Phase 12.1 pattern [VERIFIED: admin/page.tsx] |

**Key insight:** Gần như toàn bộ infrastructure cho phase này đã tồn tại. Phase 13 chủ yếu là "wiring" — kết nối các pieces có sẵn vào một Sheet UI mới. Không có logic backend mới, không có data fetching mới, chỉ có UI components + state management.

## Common Pitfalls

### Pitfall 1: Sheet Open/Close Race with Mutation
**What goes wrong:** Sheet opens before mutation completes, showing stale/wrong state.
**Why it happens:** `triggerReport.mutate()` is async — `onSuccess` fires after network round-trip.
**How to avoid:** Only open sheet in `onSuccess` callback, not on button click. Capture `job_id` from `TriggerResponse` for tracking.
**Warning signs:** Sheet shows "generating" but no matching job appears in Jobs tab.

### Pitfall 2: useJobTransitions Callback Stale Closure
**What goes wrong:** `handleTransition` callback captures stale `sheetState` reference, doesn't update sheet correctly.
**Why it happens:** `useCallback` dependency array doesn't include `sheetState`, or sheet state is managed outside the callback's closure scope.
**How to avoid:** Use `useRef` for sheet state that the callback reads, or use `setState(prev => ...)` functional form. Alternatively, manage sheet state with `useReducer` to avoid stale closure entirely.
**Warning signs:** Sheet stays in "generating" state even after job completes.

### Pitfall 3: Batch Job Tracking Confusion
**What goes wrong:** Backend creates ONE job for multiple symbols (not one job per symbol). Sheet UI assumes one job per stock.
**Why it happens:** `POST /api/admin/report` with `symbols: ["VNM", "FPT"]` creates ONE job with `params.symbols` array. `run_report()` processes them sequentially within that single job.
**How to avoid:** Track by job_id, not by symbol count. For batch progress, the only states are pending → running → completed/failed for the entire batch. Individual stock progress within the batch is NOT visible via polling.
**Warning signs:** Progress bar jumps from 0% to 100% with no intermediate steps.

### Pitfall 4: Sheet Default Width Too Narrow for Report Content
**What goes wrong:** `sm:max-w-sm` (384px) is default Sheet width — too narrow for prose report content.
**Why it happens:** shadcn Sheet defaults to `sm:max-w-sm` for right side.
**How to avoid:** Override to `sm:max-w-lg` (512px) as specified in UI-SPEC. Add `className="sm:max-w-lg"` to `SheetContent`.
**Warning signs:** Report text wraps excessively, markdown tables overflow.

### Pitfall 5: Missing Sheet Component Controlled Open State
**What goes wrong:** Sheet doesn't respond to programmatic open/close because it uses uncontrolled state.
**Why it happens:** shadcn Sheet (base-nova) wraps `@base-ui/react Dialog` which uses `open`/`onOpenChange` props for controlled mode.
**How to avoid:** Use `<Sheet open={isOpen} onOpenChange={setIsOpen}>` pattern. The `open` prop controls visibility, `onOpenChange` handles close from overlay/escape.
**Warning signs:** Sheet only opens via SheetTrigger, not from callback.

## Code Examples

### Example 1: Sheet Controlled Mode with @base-ui/react Dialog

```typescript
// Source: Verified from shadcn --view output — Sheet wraps @base-ui/react Dialog
// The Sheet component's Root accepts `open` and `onOpenChange` props
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";

// Controlled usage:
<Sheet open={sheetState.status !== "closed"} onOpenChange={(open) => {
  if (!open) setSheetState({ status: "closed" });
}}>
  <SheetContent side="right" className="sm:max-w-lg">
    <SheetHeader>
      <SheetTitle>{t("admin.report.sheetTitle")}</SheetTitle>
      <SheetDescription>
        {/* Dynamic description based on single/batch */}
      </SheetDescription>
    </SheetHeader>
    <ScrollArea className="flex-1 px-4">
      {/* Content based on sheetState.status */}
    </ScrollArea>
    <SheetFooter>
      {/* Conditional buttons */}
    </SheetFooter>
  </SheetContent>
</Sheet>
```

### Example 2: Progress Component with Batch Counter

```typescript
// Source: Verified from shadcn --view output — Progress wraps @base-ui/react Progress
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
  ProgressLabel,
  ProgressValue,
} from "@/components/ui/progress";

// Usage for batch progress:
<Progress value={completedCount} max={totalCount}>
  <div className="flex items-center justify-between">
    <ProgressLabel>{t("admin.report.batchProgress", { completed: completedCount, total: totalCount })}</ProgressLabel>
    <ProgressValue />
  </div>
  <ProgressTrack>
    <ProgressIndicator />
  </ProgressTrack>
</Progress>
```

### Example 3: Step Indicator Component

```typescript
// Source: Pattern derived from UI-SPEC step indicator styling
function StepIndicator({ step, status }: { step: string; status: "pending" | "active" | "completed" | "failed" }) {
  return (
    <div className="flex items-center gap-2">
      <div className={cn(
        "h-2 w-2 rounded-full",
        status === "pending" && "border border-muted-foreground",
        status === "active" && "bg-primary step-active-pulse",
        status === "completed" && "bg-[var(--stock-up)]",
        status === "failed" && "bg-destructive",
      )} />
      <span className={cn(
        "text-sm",
        status === "pending" && "text-muted-foreground",
        status === "active" && "text-foreground font-medium",
        status === "completed" && "text-muted-foreground line-through",
        status === "failed" && "text-destructive",
      )}>
        {step}
      </span>
    </div>
  );
}
```

### Example 4: Connecting Report Trigger to Sheet Open

```typescript
// Source: Existing mutation pattern in pipeline-control.tsx (L246-261)
// Modified to capture job_id and trigger sheet
const handleReportClick = useCallback(() => {
  triggerReport.mutate([...validSelected], {
    onSuccess: (data: TriggerResponse) => {
      handleSuccess(t("pipeline.report"));
      // Notify parent to open sheet with job tracking info
      onReportTriggered?.({
        jobId: data.job_id,
        symbols: [...validSelected],
      });
    },
    onError: handleMutationError,
  });
}, [validSelected, triggerReport, handleSuccess, handleMutationError, onReportTriggered, t]);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| shadcn based on Radix UI | shadcn base-nova based on @base-ui/react | 2025 | Sheet uses `@base-ui/react/dialog` not `@radix-ui/react-dialog`. API differs slightly (data-slot attributes, render prop for close button) [VERIFIED: shadcn --view output] |
| Separate SSE endpoint for progress | Job polling via TanStack Query refetchInterval | Project decision (Phase 12.1) | Simpler architecture, no new backend endpoints. 3s polling acceptable for Ollama 30-120s generation time [VERIFIED: CONTEXT.md D-02a, UI-SPEC] |

**Deprecated/outdated:**
- Radix UI primitives: This project uses `@base-ui/react` (base-nova style). Do NOT import from `@radix-ui/*`. [VERIFIED: components.json preset "base-nova"]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Backend creates ONE job for batch symbols (not N separate jobs) | Pitfall 3 | If backend creates N jobs, batch progress tracking logic must change from single job_id tracking to multi-job tracking. Medium risk — would require different sheet state model. |
| A2 | `@base-ui/react Dialog` supports controlled `open`/`onOpenChange` pattern | Code Example 1 | If Dialog API differs, Sheet open/close won't work programmatically. LOW risk — standard React dialog pattern. |

**Verification for A1:** Backend code in `admin.py` line 157-160 shows `trigger_report` creates ONE job record with `params={"symbols": request.symbols}`. `run_report` in `admin_service.py` line 154-173 loops through symbols within that single job. **CONFIRMED by code inspection — this is not an assumption.** Removing from log.

**Verification for A2:** shadcn Sheet wraps `@base-ui/react/dialog` which exports `Dialog.Root` with standard `open` prop. The shadcn `Sheet` function passes `...props` to `SheetPrimitive.Root`, so `open` and `onOpenChange` are forwarded. **CONFIRMED by shadcn --view output.** Removing from log.

**Final status: All claims verified — no assumptions requiring user confirmation.**

## Open Questions

1. **Batch progress granularity**
   - What we know: Backend creates ONE job for multiple symbols. Job status only has pending/running/completed/failed — no per-symbol progress within a job.
   - What's unclear: UI-SPEC shows per-stock progress bar "2/5 stocks completed" — but this info isn't available from the job polling endpoint.
   - Recommendation: For single job, show 3-step progress (Queued → Generating → Complete). For batch, after job completes, show overall completion. The step indicator can show job-level status transitions only. Alternatively, for real per-stock progress, we'd need to check each symbol's report existence — but that's N extra queries.

2. **Re-opening sheet for in-progress job**
   - What we know: If user closes sheet during generation and wants to reopen, there's no built-in "reopen sheet" affordance.
   - What's unclear: Should there be a persistent indicator that a report is being generated?
   - Recommendation: When sheet is closed during active generation, show the job in Jobs tab as usual. User can click the toast action "View job" to navigate to Jobs tab. Re-opening the sheet can be triggered from a second Report button click on the same (or any) stocks — but this might trigger a NEW job. Keep it simple: closing sheet doesn't stop generation, but doesn't provide re-open. The toast remains the re-entry point.

## Project Constraints (from copilot-instructions.md)

- Stack: Next.js 16+ / React 19+ / TypeScript / Tailwind CSS 4 / shadcn base-nova style [VERIFIED: copilot-instructions.md]
- Component library: `@base-ui/react` (NOT Radix UI) [VERIFIED: components.json]
- Icon library: `lucide-react` [VERIFIED: components.json]
- i18n: `next-intl` with en.json / vi.json message files [VERIFIED: existing codebase]
- Data fetching: `@tanstack/react-query` [VERIFIED: package.json]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1+ (unit), Playwright 1.59+ (e2e) |
| Config file | `apps/helios/vitest.config.ts`, `apps/helios/playwright.config.ts` |
| Quick run command | `cd apps/helios && npx vitest run --reporter=verbose` |
| Full suite command | `cd apps/helios && npx vitest run && npx playwright test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-08a | Report button visible in Pipeline tab, disabled when no selection | unit | `cd apps/helios && npx vitest run src/components/admin/__tests__/report-generation-sheet.test.tsx -x` | ❌ Wave 0 |
| ADMIN-08b | Sheet opens on Report trigger with correct symbols | unit | `cd apps/helios && npx vitest run src/components/admin/__tests__/report-generation-sheet.test.tsx -x` | ❌ Wave 0 |
| ADMIN-08c | Step indicator transitions (queued → generating → complete) | unit | `cd apps/helios && npx vitest run src/components/admin/__tests__/report-progress.test.tsx -x` | ❌ Wave 0 |
| ADMIN-08d | Report preview renders AIReportPanel after completion | unit | `cd apps/helios && npx vitest run src/components/admin/__tests__/report-preview.test.tsx -x` | ❌ Wave 0 |
| ADMIN-08e | i18n keys exist for both en.json and vi.json | unit | `cd apps/helios && npx vitest run src/components/admin/__tests__/report-i18n.test.tsx -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd apps/helios && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd apps/helios && npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/components/admin/__tests__/report-generation-sheet.test.tsx` — covers ADMIN-08a, ADMIN-08b
- [ ] `src/components/admin/__tests__/report-progress.test.tsx` — covers ADMIN-08c
- [ ] `src/components/admin/__tests__/report-preview.test.tsx` — covers ADMIN-08d
- [ ] Test infrastructure exists (vitest configured with `@` alias), but no admin component tests exist yet

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — personal tool, no auth |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — single user |
| V5 Input Validation | no | No user text input — only checkbox selection of pre-existing symbols |
| V6 Cryptography | no | N/A |

### Known Threat Patterns

No new threat surface. Phase is pure-frontend wiring of existing backend endpoints that already validate input (Pydantic `SymbolsRequest` with pattern validation). No new API endpoints, no new user input fields.

## Sources

### Primary (HIGH confidence)
- `apps/helios/src/app/admin/page.tsx` — AdminPage component, tab state, toast + transition wiring
- `apps/helios/src/components/admin/pipeline-control.tsx` — Report button pattern, mutation usage, onOperationTriggered callback
- `apps/helios/src/lib/queries.ts` — All TanStack Query hooks, job polling, cache invalidation
- `apps/helios/src/hooks/use-job-transitions.ts` — Job transition detection hook
- `apps/helios/src/components/stock/ai-report-panel.tsx` — Report rendering component
- `apps/prometheus/src/localstock/api/routes/admin.py` — POST /api/admin/report endpoint (creates single job)
- `apps/prometheus/src/localstock/services/admin_service.py` — run_report (sequential per-symbol within single job)
- `apps/helios/components.json` — shadcn config: base-nova style, @base-ui/react
- shadcn `--view` output — Sheet and Progress component source code verified

### Secondary (MEDIUM confidence)
- `apps/helios/src/lib/types.ts` — TypeScript types for AdminJob, StockReport, TriggerResponse
- UI-SPEC `13-UI-SPEC.md` — Design contract from gsd-ui-researcher

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in package.json, shadcn components verified via --dry-run and --view
- Architecture: HIGH — all integration points verified by reading actual source code, data flow traced end-to-end
- Pitfalls: HIGH — identified through code inspection of actual backend job creation pattern, shadcn API, and existing hook behavior

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable — no moving parts, all libraries already pinned in project)
