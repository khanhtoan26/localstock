---
phase: 13
phase_name: ai-report-generation-ui
reviewer: gsd-code-reviewer
depth: standard
status: issues_found
files_reviewed: 11
files_reviewed_list:
  - apps/helios/src/app/admin/jobs/[id]/page.tsx
  - apps/helios/src/app/admin/page.tsx
  - apps/helios/src/app/globals.css
  - apps/helios/src/components/admin/job-monitor.tsx
  - apps/helios/src/components/admin/pipeline-control.tsx
  - apps/helios/src/components/admin/report-progress.tsx
  - apps/helios/src/components/ui/progress.tsx
  - apps/helios/src/components/ui/sheet.tsx
  - apps/helios/src/lib/queries.ts
  - apps/helios/messages/en.json
  - apps/helios/messages/vi.json
findings: 3
critical: 0
high: 0
medium: 1
low: 2
---

# Phase 13: Code Review Report

**Reviewed:** 2026-04-23
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 13 adds AI report generation UI: a dedicated job detail page at `/admin/jobs/[id]`, a step progress indicator component, pipeline Report button with navigation, and supporting i18n/CSS. The implementation is clean overall — TanStack Query polling is well-configured with conditional `refetchInterval`, `NaN` params are safely guarded, and React patterns are correct (proper keys, stable callbacks, no stale closure issues in hooks). The shadcn Sheet and Progress primitives are standard generated code.

One medium-severity bug was found: the error section on the job detail page uses report-specific copy for all job types, which would be misleading for failed crawl/analyze/score jobs. Two minor code quality items (unused import, dead prop) are noted.

No security issues found. All user-facing data is rendered via React JSX (auto-escaped), i18n interpolation uses next-intl (safe by default), and API data is properly typed.

## Warnings

### WR-01: Error section uses report-specific heading for all failed job types

**File:** `apps/helios/src/app/admin/jobs/[id]/page.tsx:114-128`
**Issue:** The error display block renders for **any** failed job (`job.status === "failed"`) but uses `t("report.errorHeading")` which translates to "Report generation failed" (en) / "Tạo báo cáo thất bại" (vi). When a crawl, analyze, score, or pipeline job fails, users would see a misleading report-specific error heading.
**Fix:** Guard the heading by job type, or use a generic error heading for non-report jobs:
```tsx
{job.status === "failed" && (
  <div className="mb-8 p-6 border border-destructive/30 rounded-lg bg-destructive/5">
    <div className="flex items-start gap-3">
      <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
      <div>
        <h2 className="text-base font-medium text-destructive">
          {isReportJob ? t("report.errorHeading") : t("toast.jobFailed", { type: job.job_type, symbols: symbols.join(", ") })}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {job.error || t("report.errorGeneric")}
        </p>
      </div>
    </div>
  </div>
)}
```
Alternatively, add a generic `jobs.errorHeading` i18n key (e.g., "Job failed") for non-report jobs.

## Info

### IN-01: Unused import `RefreshCw`

**File:** `apps/helios/src/app/admin/jobs/[id]/page.tsx:5`
**Issue:** `RefreshCw` is imported from `lucide-react` but never used in the component. Likely a leftover from design iteration.
**Fix:** Remove from import statement:
```tsx
import { ArrowLeft, AlertCircle } from "lucide-react";
```

### IN-02: Dead `onReportTriggered` prop in PipelineControl

**File:** `apps/helios/src/components/admin/pipeline-control.tsx:51`
**Issue:** `onReportTriggered` is defined in `PipelineControlProps`, destructured on line 54, and invoked on line 256, but the parent `admin/page.tsx` (line 80) never passes it. After the design pivot from Sheet to dedicated page, this callback became dead code. The navigation now happens directly via `router.push` on line 257, making this prop unnecessary.
**Fix:** Remove the prop and its usage:
```tsx
// In PipelineControlProps
interface PipelineControlProps {
  onOperationTriggered: () => void;
}

// In the Report button onSuccess
onSuccess: (data) => {
  handleSuccess(t("pipeline.report"));
  router.push(`/admin/jobs/${data.job_id}`);
},
```

---

_Reviewed: 2026-04-23_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
