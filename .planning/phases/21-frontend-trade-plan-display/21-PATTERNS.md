# Phase 21: Frontend Trade Plan Display - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 3 (1 new, 2 modified)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/helios/src/components/stock/trade-plan-section.tsx` | component | request-response | `apps/helios/src/components/stock/ai-report-panel.tsx` | exact |
| `apps/helios/src/app/stock/[symbol]/page.tsx` (modify) | page | request-response | self | exact |
| `apps/helios/src/lib/types.ts` (modify) | types | — | self | exact |

## Pattern Assignments

### `apps/helios/src/components/stock/trade-plan-section.tsx` (component, new)

**Primary Analog:** `apps/helios/src/components/stock/ai-report-panel.tsx`
This is the closest match — a client component that receives report query state (loading/error/data), conditionally renders, and uses badges + formatting utilities.

**Imports pattern** (ai-report-panel.tsx lines 1-9):
```typescript
"use client";

import { useTranslations } from "next-intl";
import { Skeleton } from "@/components/ui/skeleton";
import { formatScore } from "@/lib/utils";
import type { StockReport } from "@/lib/types";
```

New component should additionally import:
```typescript
import { formatVND } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipTrigger, TooltipPortal, TooltipPositioner, TooltipContent } from "@/components/ui/tooltip";
import { AlertCircle } from "lucide-react"; // or AlertTriangle for ⚠️
import type { TradePlanData } from "@/lib/types"; // new interface
```

**Props interface pattern** (ai-report-panel.tsx lines 11-15):
```typescript
interface AIReportPanelProps {
  report: StockReport | undefined;
  isLoading: boolean;
  isError: boolean;
}
```
TradePlanSection should follow the same pattern but also receive `currentClose` for percentage calculation:
```typescript
interface TradePlanSectionProps {
  report: StockReport | undefined;
  isLoading: boolean;
  currentClose: number | null;
}
```

**Loading skeleton pattern** (ai-report-panel.tsx lines 20-29):
```typescript
if (isLoading) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  );
}
```

**Conditional null return pattern** (D-09 — hide when no trade plan data):
```typescript
// When report has no trade plan fields, return null (completely hidden)
if (!report || !tradePlanData) {
  return null;
}
```

**Risk badge color map** — follow `recommendation-badge.tsx` (lines 6-12) and `gradeColors` in `utils.ts` (lines 36-42):
```typescript
// recommendation-badge.tsx pattern — Record<string, string> for Tailwind classes with dark mode
const recommendationStyles: Record<string, string> = {
  "strong_buy": "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700",
  // ...
};

// gradeColors pattern from utils.ts
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  // ...
};
```
Risk badge should use same pattern:
```typescript
const riskStyles: Record<string, string> = {
  low:    "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700",
  medium: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700",
  high:   "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700",
};
```

**Badge rendering** — follow `GradeBadge` (grade-badge.tsx lines 3-9):
```typescript
export function GradeBadge({ grade }: { grade: string }) {
  const colors = gradeColors[grade] || gradeColors.F;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${colors}`}>
      {grade}
    </span>
  );
}
```

**Tooltip usage** — use `@/components/ui/tooltip` (tooltip.tsx full file):
```typescript
import { Tooltip, TooltipTrigger, TooltipPortal, TooltipPositioner, TooltipContent } from "@/components/ui/tooltip";

// Usage pattern (no existing usage in codebase — construct from component API):
<Tooltip>
  <TooltipTrigger>
    <RiskBadge ... />
  </TooltipTrigger>
  <TooltipPortal>
    <TooltipPositioner>
      <TooltipContent>{reasoningText}</TooltipContent>
    </TooltipPositioner>
  </TooltipPortal>
</Tooltip>
```

**VND formatting** — follow `page.tsx` (lines 89-90):
```typescript
<span className="text-2xl font-bold font-mono">
  {formatVND(latest.close)}
</span>
```

**Percentage display** — follow `page.tsx` (lines 105-106):
```typescript
{isUp ? "+" : ""}
{formatVND(priceChange)} ({priceChangePct!.toFixed(2)}%)
```

---

### `apps/helios/src/app/stock/[symbol]/page.tsx` (modify)

**Insertion point** — between ScoreBreakdown Card and AIReport Card (lines 193-224).

Current layout pattern (lines 193-224):
```typescript
{/* ─── Score + AI Report (two columns on desktop) ─── */}
<div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
  {/* Score breakdown */}
  <Card>
    <CardHeader>
      <CardTitle>{t("scoreAnalysis")}</CardTitle>
    </CardHeader>
    <CardContent>
      {scoreQuery.isLoading ? (
        <Skeleton className="h-[180px] w-full" />
      ) : scoreQuery.data ? (
        <ScoreBreakdown score={scoreQuery.data} />
      ) : (
        <EmptyState body={t("data.noScore")} />
      )}
    </CardContent>
  </Card>

  {/* AI Report */}
  <Card>
    ...
  </Card>
</div>
```

**Import pattern** (lines 1-22 — add TradePlanSection alongside other stock component imports):
```typescript
import { ScoreBreakdown } from "@/components/stock/score-breakdown";
import { AIReportPanel } from "@/components/stock/ai-report-panel";
// ADD:
import { TradePlanSection } from "@/components/stock/trade-plan-section";
```

**Data passing pattern** — follows how AIReportPanel receives data (lines 217-221):
```typescript
<AIReportPanel
  report={reportQuery.data}
  isLoading={reportQuery.isLoading}
  isError={reportQuery.isError}
/>
```

TradePlanSection should be inserted as a full-width section between the grid rows, or within the grid. Pass `reportQuery` state + `latest?.close`:
```typescript
<TradePlanSection
  report={reportQuery.data}
  isLoading={reportQuery.isLoading}
  currentClose={latest?.close ?? null}
/>
```

---

### `apps/helios/src/lib/types.ts` (modify)

**Type definition pattern** — follow existing interfaces (lines 104-115):
```typescript
export interface StockReport {
  symbol: string;
  report_type?: string;
  content_json: Record<string, unknown> | null;
  summary: string | null;
  recommendation: string | null;
  t3_prediction: string | null;
  total_score: number | null;
  grade: string | null;
  model_used?: string;
  generated_at: string;
}
```

Add `TradePlanData` interface for type-safe extraction from `content_json`:
```typescript
export interface TradePlanData {
  entry_price: number | null;
  stop_loss: number | null;
  target_price: number | null;
  risk_rating: "high" | "medium" | "low" | null;
  signal_conflicts: string | null;
  catalyst: string | null;
}
```

---

## Shared Patterns

### Card Section Wrapper
**Source:** `apps/helios/src/app/stock/[symbol]/page.tsx` lines 148-167, 196-209
**Apply to:** TradePlanSection (if wrapping in a Card)
```typescript
<Card>
  <CardHeader>
    <CardTitle>{t("someTitle")}</CardTitle>
  </CardHeader>
  <CardContent>
    {isLoading ? (
      <Skeleton className="h-[180px] w-full" />
    ) : data ? (
      <ComponentContent ... />
    ) : (
      <EmptyState body={t("data.noData")} />
    )}
  </CardContent>
</Card>
```

### Color-Coded Style Map (dark mode aware)
**Source:** `apps/helios/src/components/stock/recommendation-badge.tsx` lines 6-12
**Apply to:** RiskBadge sub-component
```typescript
const recommendationStyles: Record<string, string> = {
  "strong_buy": "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700",
  "hold":       "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700",
  "strong_sell":"bg-red-100 text-red-800 border-red-300 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700",
};
```

### Badge Pill Shape
**Source:** `apps/helios/src/components/rankings/grade-badge.tsx` lines 3-9
**Apply to:** RiskBadge
```typescript
<span className={`px-2 py-0.5 rounded text-xs font-bold border ${colors}`}>
  {label}
</span>
```

### VND Formatting
**Source:** `apps/helios/src/lib/utils.ts` lines 15-19
**Apply to:** PriceLevelRow sub-component
```typescript
const vnFormatter = new Intl.NumberFormat("vi-VN");
export function formatVND(value: number | null | undefined): string {
  if (value == null) return "—";
  return vnFormatter.format(Math.round(value));
}
```

### Muted Text for Secondary Info
**Source:** `apps/helios/src/app/stock/[symbol]/page.tsx` lines 109-111
**Apply to:** Percentage variance display in PriceLevelRow
```typescript
<span className="text-xs text-muted-foreground">
  {/* secondary text */}
</span>
```

### Up/Down Color Classes
**Source:** `apps/helios/src/app/stock/[symbol]/page.tsx` lines 93-98
**Apply to:** Percentage variance coloring
```typescript
className={`... ${
  isUp
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400"
}`}
```

### Skeleton Loading
**Source:** `apps/helios/src/components/ui/skeleton.tsx` full file + usage in page.tsx line 155
**Apply to:** TradePlanSection loading state
```typescript
<Skeleton className="h-[180px] w-full" />
```

### Tooltip Component
**Source:** `apps/helios/src/components/ui/tooltip.tsx` full file (lines 1-56)
**Apply to:** RiskBadge tooltip for reasoning text
```typescript
// 5-part composition: Tooltip > TooltipTrigger > TooltipPortal > TooltipPositioner > TooltipContent
<Tooltip>
  <TooltipTrigger>{triggerElement}</TooltipTrigger>
  <TooltipPortal>
    <TooltipPositioner>
      <TooltipContent>{tooltipText}</TooltipContent>
    </TooltipPositioner>
  </TooltipPortal>
</Tooltip>
```

### i18n Translation
**Source:** `apps/helios/src/components/stock/score-breakdown.tsx` lines 2, 18
**Apply to:** All user-visible text in TradePlanSection
```typescript
import { useTranslations } from "next-intl";
// ...
const t = useTranslations("stock.tradePlan");
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All files have strong analogs |

## Metadata

**Analog search scope:** `apps/helios/src/`
**Files scanned:** 12 (components, pages, types, utils, queries, UI primitives)
**Pattern extraction date:** 2026-04-28
