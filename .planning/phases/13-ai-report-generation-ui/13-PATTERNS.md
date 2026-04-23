# Phase 13: AI Report Generation UI - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 8 (3 new components, 5 modifications)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/components/admin/report-generation-sheet.tsx` | component (container) | event-driven (job transitions → state machine) | `src/app/admin/page.tsx` | role-match |
| `src/components/admin/report-progress.tsx` | component (presentational) | request-response (renders job status) | `src/components/admin/status-badge.tsx` + `src/components/admin/job-monitor.tsx` | role-match |
| `src/components/admin/report-preview.tsx` | component (presentational) | request-response (fetches + renders report) | `src/components/stock/ai-report-panel.tsx` | exact |
| `src/app/admin/page.tsx` | page (orchestrator) | event-driven (state + callbacks) | — (self-modify) | exact |
| `src/components/admin/pipeline-control.tsx` | component (controller) | request-response (mutation trigger) | — (self-modify) | exact |
| `src/app/globals.css` | config (styles) | — | — (self-modify, append) | exact |
| `messages/en.json` | config (i18n) | — | — (self-modify, append) | exact |
| `messages/vi.json` | config (i18n) | — | — (self-modify, append) | exact |

## Pattern Assignments

### `src/components/admin/report-generation-sheet.tsx` (NEW — component container, event-driven)

**Analog:** `src/app/admin/page.tsx` (state management + useJobTransitions wiring pattern)

This is the main Sheet container. It orchestrates the state machine (CLOSED → GENERATING → COMPLETED/FAILED) and passes state to child components. The closest analog for its state management + callback pattern is AdminPage itself.

**Imports pattern** (from `src/app/admin/page.tsx` lines 1-13):
```typescript
"use client";

import { useTranslations } from "next-intl";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
// NEW imports for this component:
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ReportProgress } from "./report-progress";
import { ReportPreview } from "./report-preview";
import type { AdminJob } from "@/lib/types";
```

**State machine pattern** (derived from RESEARCH.md Pattern 1 + AdminPage state pattern lines 17-19):
```typescript
// AdminPage uses simple useState for tab/focus state:
const [activeTab, setActiveTab] = useState("stocks");
const [focusedJobId, setFocusedJobId] = useState<number | null>(null);

// ReportGenerationSheet uses discriminated union state:
type SheetState =
  | { status: "closed" }
  | { status: "generating"; symbols: string[]; jobId: number }
  | { status: "completed"; symbols: string[]; lastSymbol: string }
  | { status: "failed"; symbols: string[]; failedSymbol: string; error?: string };
```

**Controlled Sheet pattern** (from RESEARCH.md Code Example 1, verified via shadcn --view):
```typescript
// Sheet uses @base-ui/react Dialog — controlled via open/onOpenChange
<Sheet open={sheetState.status !== "closed"} onOpenChange={(open) => {
  if (!open) setSheetState({ status: "closed" });
}}>
  <SheetContent side="right" className="sm:max-w-lg">
    {/* ... */}
  </SheetContent>
</Sheet>
```

**Props interface pattern** (from `src/components/admin/job-monitor.tsx` lines 74-77):
```typescript
// JobMonitor receives parent-controlled state:
interface JobMonitorProps {
  focusedJobId?: number | null;
  onFocusHandled?: () => void;
}

// ReportGenerationSheet receives state + callbacks from AdminPage:
interface ReportGenerationSheetProps {
  sheetState: SheetState;
  onStateChange: (state: SheetState) => void;
  onRetry?: (symbols: string[]) => void;
}
```

---

### `src/components/admin/report-progress.tsx` (NEW — component presentational, request-response)

**Analog:** `src/components/admin/status-badge.tsx` (status-based styling pattern) + `src/components/admin/job-monitor.tsx` (Loader2 animation pattern)

This component renders step indicator (Queued → Generating → Complete) and optional batch progress bar.

**Imports pattern** (combined from `status-badge.tsx` lines 1-3 and `job-monitor.tsx` lines 5-6):
```typescript
"use client";

import { useTranslations } from "next-intl";
import { Check, Loader2, AlertCircle } from "lucide-react";
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
} from "@/components/ui/progress";
import { cn } from "@/lib/utils";
```

**Status-based conditional styling pattern** (from `src/components/admin/status-badge.tsx` lines 7-22):
```typescript
// StatusBadge uses Record<string, string> + conditional rendering:
const statusStyles: Record<string, string> = {
  completed:
    "border-transparent text-[var(--stock-up)] bg-[color-mix(in_srgb,var(--stock-up)_10%,transparent)]",
  running:
    "border-transparent text-[var(--stock-warning)] bg-[color-mix(in_srgb,var(--stock-warning)_10%,transparent)]",
};

// Apply same pattern to step indicator dots:
// pending → "border border-muted-foreground"
// active → "bg-primary step-active-pulse"
// completed → "bg-[var(--stock-up)]"
// failed → "bg-destructive"
```

**Loader2 spin pattern** (from `src/components/admin/job-monitor.tsx` lines 50-51, 268-269):
```typescript
// In JobMonitor — inline spinner for running state:
<Loader2 className="h-4 w-4 animate-spin" />

// In Pipeline buttons — spinner replaces icon when pending:
{triggerReport.isPending ? (
  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
) : (
  <FileText className="h-4 w-4 mr-1" />
)}
```

**Step indicator component pattern** (from RESEARCH.md Code Example 3):
```typescript
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

---

### `src/components/admin/report-preview.tsx` (NEW — component presentational, request-response)

**Analog:** `src/components/stock/ai-report-panel.tsx` (exact — wraps this component)

This component fetches report data via `useStockReport` and passes it to `AIReportPanel`. It's a thin wrapper that adds sheet-context-specific behavior (scroll, loading, error states).

**Imports pattern** (from `src/components/stock/ai-report-panel.tsx` lines 1-9):
```typescript
"use client";

import { useTranslations } from "next-intl";
import { Skeleton } from "@/components/ui/skeleton";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
import { useStockReport } from "@/lib/queries";
import type { StockReport } from "@/lib/types";
```

**Report data fetching pattern** (from `src/lib/queries.ts` lines 74-81):
```typescript
// useStockReport already handles queryKey, staleTime, enabled guard:
export function useStockReport(symbol: string) {
  return useQuery({
    queryKey: ["report", symbol],
    queryFn: () => apiFetch<StockReport>(`/api/reports/${symbol}`),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  });
}

// ReportPreview calls it and passes to AIReportPanel:
const { data: report, isLoading, isError } = useStockReport(symbol);
// Then: <AIReportPanel report={report} isLoading={isLoading} isError={isError} />
```

**AIReportPanel interface pattern** (from `src/components/stock/ai-report-panel.tsx` lines 11-15):
```typescript
interface AIReportPanelProps {
  report: StockReport | undefined;
  isLoading: boolean;
  isError: boolean;
}
```

**Loading skeleton pattern** (from `src/components/stock/ai-report-panel.tsx` lines 20-28):
```typescript
if (isLoading) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}
```

**Error/empty state pattern** (from `src/components/stock/ai-report-panel.tsx` lines 33-38):
```typescript
if (isError || !report) {
  return (
    <p className="text-sm text-muted-foreground">
      {t("noReport")}
    </p>
  );
}
```

---

### `src/app/admin/page.tsx` (MODIFY — page orchestrator, event-driven)

**Analog:** Self — extend existing patterns

**Current state management** (lines 15-19):
```typescript
export default function AdminPage() {
  const t = useTranslations("admin");
  const [activeTab, setActiveTab] = useState("stocks");
  const [focusedJobId, setFocusedJobId] = useState<number | null>(null);
  const queryClient = useQueryClient();
```

**Changes needed:**
1. Add `sheetState` / `setSheetState` (discriminated union state)
2. Extend `handleTransition` callback (lines 21-58) to update sheet state when `job.job_type === "report"`
3. Add `onReportTriggered` callback passed to PipelineControl
4. Render `<ReportGenerationSheet>` at the bottom of JSX

**handleTransition extension point** (lines 21-58 — add report job detection after existing toast logic):
```typescript
const handleTransition = useCallback(
  ({ job }: { job: AdminJob }) => {
    // 1. Existing: cache invalidation
    invalidateForJob(queryClient, job);

    // 2. Existing: toast notification (lines 26-56)
    // ... (keep unchanged)

    // 3. NEW: update sheet state for report jobs
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
            failedSymbol: sheetState.symbols[0] || "",
          });
        }
      }
    }
  },
  [queryClient, t, sheetState],
);
```

**PipelineControl callback extension** (line 79):
```typescript
// Current:
<PipelineControl onOperationTriggered={() => setActiveTab("jobs")} />

// After:
<PipelineControl
  onOperationTriggered={() => setActiveTab("jobs")}
  onReportTriggered={({ jobId, symbols }) => {
    setSheetState({ status: "generating", symbols, jobId });
  }}
/>
```

---

### `src/components/admin/pipeline-control.tsx` (MODIFY — component controller)

**Analog:** Self — extend existing Report button handler

**Current Report button** (lines 247-261):
```typescript
<Button
  variant="outline"
  disabled={validSelected.size === 0 || triggerReport.isPending}
  onClick={() =>
    triggerReport.mutate([...validSelected], {
      onSuccess: () => handleSuccess(t("pipeline.report")),
      onError: handleMutationError,
    })
  }
>
  {triggerReport.isPending ? (
    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
  ) : (
    <FileText className="h-4 w-4 mr-1" />
  )}
  {t("pipeline.report")}
</Button>
```

**Changes needed:**
1. Add `onReportTriggered` to `PipelineControlProps` interface (line 48-50)
2. Modify Report button `onSuccess` to call `onReportTriggered` with job_id + symbols

**Props extension** (lines 48-50):
```typescript
// Current:
interface PipelineControlProps {
  onOperationTriggered: () => void;
}

// After:
interface PipelineControlProps {
  onOperationTriggered: () => void;
  onReportTriggered?: (data: { jobId: number; symbols: string[] }) => void;
}
```

**Report button onSuccess extension** (lines 249-254):
```typescript
// Current:
onSuccess: () => handleSuccess(t("pipeline.report")),

// After:
onSuccess: (data: TriggerResponse) => {
  handleSuccess(t("pipeline.report"));
  onReportTriggered?.({ jobId: data.job_id, symbols: [...validSelected] });
},
```

---

### `src/app/globals.css` (MODIFY — append animation)

**Analog:** Self — follows existing `@keyframes` pattern (lines 163-171)

**Existing animation pattern** (lines 163-171):
```css
/* Job row highlight animation for admin job focus (Phase 12.1) */
@keyframes job-highlight {
  0%   { background-color: color-mix(in srgb, var(--primary) 8%, transparent); }
  13%  { background-color: color-mix(in srgb, var(--primary) 8%, transparent); }
  100% { background-color: transparent; }
}

.job-row-highlight {
  animation: job-highlight 2300ms ease-out forwards;
}
```

**New animation to append** (from UI-SPEC):
```css
/* Step pulse animation for report generation progress (Phase 13) */
@keyframes step-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.step-active-pulse {
  animation: step-pulse 2000ms ease-in-out infinite;
}
```

---

### `messages/en.json` and `messages/vi.json` (MODIFY — append i18n keys)

**Analog:** Self — follows existing `admin.*` key structure

**Existing key structure pattern** (from `en.json` admin section):
```json
{
  "admin": {
    "title": "Admin Console",
    "tabs": { "stocks": "...", "pipeline": "...", "jobs": "..." },
    "stocks": { ... },
    "pipeline": { "crawl": "Crawl", "report": "Report", ... },
    "jobs": { ... },
    "toast": { "operationStarted": "...", "jobCompleted": "...", ... }
  }
}
```

**New keys to add** (nested under `admin.report.*`):
```json
{
  "admin": {
    "report": {
      "sheetTitle": "Generate Report",
      "sheetDescriptionSingle": "Generating AI report for {symbol}",
      "sheetDescriptionBatch": "Generating AI reports for {count} stocks",
      "stepQueued": "Queued",
      "stepGenerating": "Generating report...",
      "stepComplete": "Report generated",
      "stepFailed": "Generation failed",
      "batchProgress": "{completed} of {total} stocks completed",
      "viewStockPage": "View stock page",
      "retry": "Retry",
      "close": "Close",
      "errorHeading": "Report generation failed",
      "errorOllamaOffline": "Ollama may be offline or unresponsive. Check that Ollama is running on localhost:11434.",
      "errorTimeout": "Generation timed out. The LLM model may be overloaded. Try again with fewer stocks.",
      "errorGeneric": "An unexpected error occurred. Check the Jobs tab for details.",
      "emptyPreview": "Report will appear here after generation completes.",
      "generatingFor": "Generating: {symbol}"
    }
  }
}
```

Vietnamese keys follow the same structure — see UI-SPEC Copywriting Contract for exact translations.

---

## Shared Patterns

### Pattern: "use client" + next-intl + lucide-react Component
**Source:** All admin components (`pipeline-control.tsx`, `job-monitor.tsx`, `status-badge.tsx`, `ai-report-panel.tsx`)
**Apply to:** All 3 new component files

Every component in this project follows this structure:
```typescript
"use client";

import { useTranslations } from "next-intl";
import { SomeIcon } from "lucide-react";
import { cn } from "@/lib/utils";
// ... shadcn components from @/components/ui/*
// ... project components from @/components/*
// ... hooks from @/lib/queries or @/hooks/*
// ... types from @/lib/types
```

### Pattern: TanStack Query Hook Usage
**Source:** `src/lib/queries.ts` (lines 74-81, 192-205, 224-237)
**Apply to:** `report-preview.tsx` (useStockReport), `report-generation-sheet.tsx` (indirectly via useJobTransitions)

```typescript
// Read query — enabled guard prevents fetch when symbol is empty
const { data, isLoading, isError } = useStockReport(symbol);

// Mutation — retry: 2, invalidates cache on success
useTriggerAdminReport().mutate(symbols, { onSuccess, onError });

// Polling — useAdminJobs already polls at 3s when active jobs exist
// useJobTransitions builds on this — no additional polling needed
```

### Pattern: Loading / Error / Empty States
**Source:** `src/components/admin/job-monitor.tsx` (lines 137-158)
**Apply to:** All 3 new components

```typescript
// Loading: Skeleton array
if (isLoading) {
  return (
    <div className="space-y-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

// Error: ErrorState component
if (isError) {
  return <ErrorState />;
}

// Empty: EmptyState with heading + body
if (!data || data.count === 0) {
  return (
    <EmptyState
      heading={t("jobs.emptyHeading")}
      body={t("jobs.emptyBody")}
    />
  );
}
```

### Pattern: Button Disabled State
**Source:** `src/components/admin/pipeline-control.tsx` (lines 195-208)
**Apply to:** Report button (already exists), Retry button in sheet

```typescript
<Button
  variant="outline"
  disabled={validSelected.size === 0 || triggerReport.isPending}
  onClick={() => triggerReport.mutate([...validSelected], { ... })}
>
  {triggerReport.isPending ? (
    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
  ) : (
    <FileText className="h-4 w-4 mr-1" />
  )}
  {t("pipeline.report")}
</Button>
```

### Pattern: CSS Custom Properties for Semantic Colors
**Source:** `src/app/globals.css` (lines 87-93)
**Apply to:** Step indicator styling in `report-progress.tsx`

```css
/* Financial semantic tokens used for step states */
--stock-up:       hsl(142 72% 29%);     /* green — completed step */
--stock-warning:  hsl(48 96% 40%);      /* yellow — running status */
/* Also: --destructive for failed, --primary for active */
```

Usage in components (from `status-badge.tsx` lines 8-11):
```typescript
"text-[var(--stock-up)] bg-[color-mix(in_srgb,var(--stock-up)_10%,transparent)]"
```

### Pattern: `cn()` for Conditional Classes
**Source:** `src/lib/utils.ts` (lines 1-6), used in `job-monitor.tsx` line 279
**Apply to:** All new components for conditional styling

```typescript
import { cn } from "@/lib/utils";

// Example from job-monitor.tsx:
<ChevronDown className={cn(
  "h-4 w-4 transition-transform",
  expandedJobId === job.id && "rotate-180",
)} />
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/components/ui/sheet.tsx` | ui primitive | — | Will be auto-generated by `npx shadcn@latest add sheet` — no manual coding |
| `src/components/ui/progress.tsx` | ui primitive | — | Will be auto-generated by `npx shadcn@latest add progress` — no manual coding |

---

## Metadata

**Analog search scope:** `apps/helios/src/` (components, app, lib, hooks)
**Files scanned:** 15 (all admin components, ai-report-panel, queries, types, utils, hooks, globals.css, i18n files)
**Pattern extraction date:** 2026-04-23
