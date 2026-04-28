# Phase 21: Frontend Trade Plan Display - Research

**Researched:** 2026-04-28
**Domain:** React/Next.js frontend component — stock detail page UI
**Confidence:** HIGH

## Summary

Phase 21 is a pure frontend component phase. The `/stock/[symbol]` page already fetches all needed data via `useStockReport(symbol)` — the report's `content_json` contains `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `signal_conflicts`, and `catalyst` fields (all Optional, null for pre-v1.4 reports). The task is to create a `TradePlanSection` component that extracts these fields from `content_json`, renders them with VND formatting and color-coded badges, and gracefully hides when data is missing.

The codebase has strong established patterns: `GradeBadge` for pill-style badges, `RecommendationBadge` for color-coded Vietnamese text, `Skeleton` for loading states, `Card/CardHeader/CardContent` for section wrappers, `formatVND()` for VND formatting, shadcn/ui Tooltip via `@base-ui/react`, and `next-intl` for i18n. No new dependencies are needed. No new API endpoints. No new data fetching hooks.

**Primary recommendation:** Build a single `TradePlanSection` client component that receives `reportQuery` (loading/error/data), extracts trade fields from `content_json`, and renders conditionally. Insert it between ScoreBreakdown and AIReportPanel in the page layout grid.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Trade Plan section placed BETWEEN Score Breakdown and AI Report Panel — user sees prices right after scores, before reading the full AI analysis.
- **D-03:** Risk badge uses pill/tag style matching GradeBadge pattern — red for "high" (Cao), yellow/amber for "medium" (Trung bình), green for "low" (Thấp).
- **D-04:** Risk badge has a tooltip on hover/tap showing reasoning text from the report's analysis content.
- **D-05:** Signal conflict section is conditionally rendered — only appears when `signal_conflicts` field is non-null in the report. Completely absent from DOM when null.
- **D-06:** Uses alert box style with yellow/amber background and ⚠️ icon, displaying the conflict text from the LLM verbatim.
- **D-07:** 3 vertical rows for price levels: Entry Zone (range), Stop-Loss, Target Price. Each row has label + VND-formatted price using existing `formatVND()`.
- **D-08:** Each price level shows percentage variance from current close price — e.g., "Cắt lỗ: 48.000 (-4.0%)" in a smaller, muted text next to the price.
- **D-09:** When report is from v1.3 or earlier (all new fields null), Trade Plan section is completely hidden. No empty state, no placeholder.
- **D-10:** When report is loading, show skeleton placeholder (animated) matching the existing PriceChart skeleton pattern.

### Agent's Discretion
- **D-02:** Layout details: exact widths, responsive breakpoints, grid column spans. Investigate what fits best given the existing 2-column responsive grid (Score left 380px, AI Report right flexible).
- Layout details: exact widths, responsive breakpoints, grid column spans
- Component internal structure: whether to use Card wrapper or custom section
- Color shade choices within the established palette
- Tooltip implementation (native title vs custom component)
- Whether catalyst_data gets its own row or is part of the conflict section

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRONTEND-01 | `/stock/[symbol]` shows dedicated Trade Plan section with entry zone, stop-loss, and target price formatted in VND | `content_json` contains `entry_price`, `stop_loss`, `target_price` as float\|null; `formatVND()` exists in utils.ts; price percentage from close requires passing latest close price to component |
| FRONTEND-02 | Trade Plan section shows colored risk badge (red=high, yellow=medium, green=low) with tooltip displaying Vietnamese reasoning text | `risk_rating` field is `"high"\|"medium"\|"low"\|null` in content_json; `GradeBadge` pattern exists; `Tooltip` component available via @base-ui/react; reasoning sourced from report `summary` or `content_json` analysis sections |
| FRONTEND-03 | Signal conflict section conditionally rendered — only shown when `signal_conflicts` field is non-null in report | `signal_conflicts` is `string\|null` in content_json; use simple `{value && <Component />}` pattern |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trade plan data | API / Backend | — | Already computed in Phase 20 and stored in content_json JSONB |
| Trade plan display | Browser / Client | — | Pure client component — conditionally renders from existing query cache |
| VND formatting | Browser / Client | — | `formatVND()` runs client-side with `Intl.NumberFormat("vi-VN")` |
| Risk badge tooltip | Browser / Client | — | UI interaction, no server involvement |
| Signal conflict rendering | Browser / Client | — | Conditional DOM — entirely client-side |

## Standard Stack

### Core (already installed — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19+ | UI rendering | Next.js dependency, already installed [VERIFIED: apps/helios/package.json] |
| next-intl | — | i18n translations | Already used for all stock page text [VERIFIED: page.tsx imports] |
| @base-ui/react | — | Tooltip primitive | Already installed, used by shadcn/ui tooltip.tsx [VERIFIED: tooltip.tsx] |
| lucide-react | — | Icons (AlertCircle, etc.) | Already used across the app [VERIFIED: page.tsx, admin pages] |
| class-variance-authority | — | Badge variants | Already installed for badge.tsx [VERIFIED: badge.tsx] |
| Tailwind CSS | 4+ | Styling | Project standard [VERIFIED: copilot-instructions.md] |

### Supporting
No new libraries needed. All functionality is achievable with existing dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @base-ui Tooltip | Native `title` attribute | title is unstyled, no dark mode support, no positioning control — use @base-ui Tooltip per existing pattern |
| Custom alert div | shadcn Alert component | No Alert component installed; a simple styled div with Tailwind matches the codebase better than adding a new shadcn component |

**Installation:** None needed — zero new dependencies.

## Architecture Patterns

### System Architecture Diagram

```
useStockReport(symbol) → TanStack Query cache
                              │
                              ▼
              ┌─────── StockDetailPage ────────┐
              │                                │
              │  ┌── ScoreBreakdown ──┐        │
              │  └────────────────────┘        │
              │          ▼                     │
              │  ┌── TradePlanSection ──────┐  │   ◄── NEW COMPONENT
              │  │  ├─ PriceLevels         │  │
              │  │  │  (entry/SL/TP + %)   │  │
              │  │  ├─ RiskBadge + Tooltip │  │
              │  │  └─ SignalConflictAlert  │  │
              │  └─────────────────────────┘  │
              │          ▼                     │
              │  ┌── AIReportPanel ──┐         │
              │  └───────────────────┘         │
              └────────────────────────────────┘
```

### Data Flow

```
API response → content_json: { entry_price, stop_loss, target_price, risk_rating, signal_conflicts, catalyst, ... }
                     │
                     ▼
         TradePlanSection receives report.content_json
                     │
                     ├─ hasTradePlan = entry_price != null || stop_loss != null || target_price != null
                     │   └─ false → render nothing (v1.3 backward compat)
                     │
                     ├─ PriceLevels: formatVND(entry_price), formatVND(stop_loss), formatVND(target_price)
                     │   └─ % variance = ((price - close) / close) * 100
                     │
                     ├─ RiskBadge: risk_rating → color map → pill badge
                     │   └─ Tooltip: summary or analysis text from content_json
                     │
                     └─ SignalConflictAlert: signal_conflicts != null → render alert box
```

### Recommended Project Structure

```
src/components/stock/
├── trade-plan-section.tsx    # NEW — main Trade Plan component
├── ai-report-panel.tsx       # Existing — AI report display
├── score-breakdown.tsx       # Existing — score bars
└── recommendation-badge.tsx  # Existing — recommendation pill
```

### Pattern 1: Content JSON Field Extraction

**What:** Extract typed fields from `content_json: Record<string, unknown>` with runtime type narrowing.
**When to use:** Always when reading new v1.4 fields from content_json.
**Example:**
```typescript
// Source: [VERIFIED: apps/helios/src/lib/types.ts — content_json is Record<string, unknown> | null]
interface TradePlanData {
  entry_price: number | null;
  stop_loss: number | null;
  target_price: number | null;
  risk_rating: "high" | "medium" | "low" | null;
  signal_conflicts: string | null;
  catalyst: string | null;
}

function extractTradePlan(contentJson: Record<string, unknown> | null): TradePlanData | null {
  if (!contentJson) return null;
  
  const entry = typeof contentJson.entry_price === "number" ? contentJson.entry_price : null;
  const sl = typeof contentJson.stop_loss === "number" ? contentJson.stop_loss : null;
  const tp = typeof contentJson.target_price === "number" ? contentJson.target_price : null;
  
  // If ALL price fields are null, this is a pre-v1.4 report → return null to hide section
  if (entry === null && sl === null && tp === null) return null;
  
  return {
    entry_price: entry,
    stop_loss: sl,
    target_price: tp,
    risk_rating: ["high", "medium", "low"].includes(contentJson.risk_rating as string)
      ? (contentJson.risk_rating as "high" | "medium" | "low")
      : null,
    signal_conflicts: typeof contentJson.signal_conflicts === "string" ? contentJson.signal_conflicts : null,
    catalyst: typeof contentJson.catalyst === "string" ? contentJson.catalyst : null,
  };
}
```

### Pattern 2: Risk Badge Color Map

**What:** Map risk_rating to Tailwind classes matching GradeBadge style.
**Example:**
```typescript
// Source: [VERIFIED: grade-badge.tsx + gradeColors in utils.ts pattern]
const riskColors: Record<string, string> = {
  high: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  medium: "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
  low: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
};

const riskLabels: Record<string, string> = {
  high: "Cao",
  medium: "Trung bình",
  low: "Thấp",
};
```

### Pattern 3: Tooltip Usage (Base UI)

**What:** Use existing shadcn/ui Tooltip wrapper from @base-ui/react.
**Example:**
```typescript
// Source: [VERIFIED: apps/helios/src/components/ui/tooltip.tsx]
import { Tooltip, TooltipTrigger, TooltipPortal, TooltipPositioner, TooltipContent } from "@/components/ui/tooltip";

<Tooltip>
  <TooltipTrigger>
    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${colors}`}>
      {label}
    </span>
  </TooltipTrigger>
  <TooltipPortal>
    <TooltipPositioner sideOffset={5}>
      <TooltipContent className="max-w-xs">
        {reasoningText}
      </TooltipContent>
    </TooltipPositioner>
  </TooltipPortal>
</Tooltip>
```

### Pattern 4: Conditional Section Rendering

**What:** Completely omit DOM element when data is null — no empty wrapper.
**Example:**
```typescript
// Source: [VERIFIED: established pattern in page.tsx lines 117-145, 170-191]
{tradePlan && (
  <Card>
    <CardHeader>...</CardHeader>
    <CardContent>...</CardContent>
  </Card>
)}
```

### Pattern 5: Skeleton Loading State

**What:** Match existing PriceChart skeleton pattern — animated placeholder.
**Example:**
```typescript
// Source: [VERIFIED: page.tsx line 29, skeleton.tsx]
{reportQuery.isLoading && (
  <Card>
    <CardHeader>
      <Skeleton className="h-5 w-32" />
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </CardContent>
  </Card>
)}
```

### Anti-Patterns to Avoid
- **Don't create a new data fetching hook:** `useStockReport()` already fetches everything including content_json. No new queries needed.
- **Don't add fields to StockReport TypeScript interface top-level:** The trade plan fields live inside `content_json`, not as top-level API response fields. The backend `get_report()` returns `content_json: report.content_json` which is the full model_dump() dict.
- **Don't render empty state for missing trade plan:** Per D-09, hide the entire section when data is null — no "Chưa có dữ liệu" placeholder.
- **Don't use hardcoded Vietnamese strings in component:** Use next-intl translation keys (add new keys to vi.json and en.json).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VND formatting | Custom number formatter | `formatVND()` from `@/lib/utils` | Already handles `Intl.NumberFormat("vi-VN")` with dot separators |
| Badge styling | Custom CSS classes | `gradeColors` pattern from utils.ts | Consistent with GradeBadge dark mode support |
| Tooltip | CSS-only hover tooltip | `@/components/ui/tooltip` (Base UI) | Handles positioning, portal, accessibility, animations |
| Card layout | Custom div with borders | `Card/CardHeader/CardContent` from shadcn/ui | Consistent ring, rounded corners, padding |
| Loading skeleton | Custom pulse animation | `Skeleton` component | Already has animate-pulse + bg-muted |

**Key insight:** This phase creates ONE new component file. Everything else (formatting, badges, tooltips, cards, skeletons, data fetching) already exists and should be reused.

## Common Pitfalls

### Pitfall 1: content_json Type Safety
**What goes wrong:** Accessing `report.content_json.entry_price` directly causes TypeScript errors because content_json is `Record<string, unknown>`.
**Why it happens:** content_json is a generic JSON column — TypeScript doesn't know the shape.
**How to avoid:** Create an `extractTradePlan()` helper with explicit type narrowing (Pattern 1 above).
**Warning signs:** TypeScript errors about `unknown` type, or using `as any` casts.

### Pitfall 2: Percentage Variance Requires Close Price
**What goes wrong:** Component can't calculate "(-4.0%)" without knowing the current close price.
**Why it happens:** The report data doesn't include the current close price — it's in `priceQuery.data`.
**How to avoid:** Pass `currentClose` as a prop to `TradePlanSection` from the page (where `latest.close` is already computed).
**Warning signs:** Undefined/NaN in percentage display.

### Pitfall 3: Layout Grid Disruption
**What goes wrong:** Inserting Trade Plan between Score and AI Report in the 2-column grid breaks the layout.
**Why it happens:** The current grid is `grid-cols-1 lg:grid-cols-[380px_1fr]` with Score (left) and AI Report (right). Inserting a third element either creates a third column or pushes AI Report down.
**How to avoid:** Place TradePlanSection as a full-width row ABOVE or BELOW the 2-column grid, OR restructure the grid. Best approach: make TradePlanSection span full width between the chart section and the score+report grid, since D-01 says "between Score and AI Report" in visual order (not necessarily grid siblings).
**Warning signs:** AI Report dropping below Score on desktop instead of staying side-by-side.

### Pitfall 4: Missing i18n Keys
**What goes wrong:** Translation keys show raw key strings like `stock.tradePlan.entryZone` instead of text.
**Why it happens:** Forgetting to add new keys to BOTH `vi.json` AND `en.json`.
**How to avoid:** Add all new translation keys before implementing the component.
**Warning signs:** Console warnings about missing translations.

### Pitfall 5: Tooltip on Mobile
**What goes wrong:** Tooltip doesn't appear on touch devices (no hover event).
**Why it happens:** @base-ui/react Tooltip by default may not handle touch interaction well.
**How to avoid:** The @base-ui Tooltip supports `delay` and should work with touch events (opens on tap). Test on mobile viewport. Alternatively, show reasoning text inline on small screens.
**Warning signs:** Risk badge shows no reasoning text on mobile.

## Code Examples

### Complete TradePlanSection Component Structure

```typescript
// Source: [VERIFIED: established patterns from score-breakdown.tsx, ai-report-panel.tsx, grade-badge.tsx]
"use client";

import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipTrigger, TooltipPortal, TooltipPositioner, TooltipContent } from "@/components/ui/tooltip";
import { formatVND } from "@/lib/utils";
import type { StockReport } from "@/lib/types";

// ... extractTradePlan helper (Pattern 1)
// ... riskColors map (Pattern 2)
// ... RiskBadge sub-component
// ... PriceLevelRow sub-component
// ... SignalConflictAlert sub-component

interface TradePlanSectionProps {
  report: StockReport | undefined;
  isLoading: boolean;
  currentClose: number | null;
}

export function TradePlanSection({ report, isLoading, currentClose }: TradePlanSectionProps) {
  const t = useTranslations("stock.tradePlan");
  
  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader><Skeleton className="h-5 w-32" /></CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </CardContent>
      </Card>
    );
  }
  
  // Extract trade plan data
  const tradePlan = extractTradePlan(report?.content_json ?? null);
  
  // D-09: Completely hidden when null (pre-v1.4 report)
  if (!tradePlan) return null;
  
  // ... render Card with PriceLevels, RiskBadge, SignalConflictAlert
}
```

### Page Integration Point

```typescript
// Source: [VERIFIED: apps/helios/src/app/stock/[symbol]/page.tsx lines 193-224]
// Current layout:
//   <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
//     <Card>ScoreBreakdown</Card>
//     <Card>AIReportPanel</Card>
//   </div>

// NEW layout — insert TradePlanSection as full-width before the 2-column grid:
<TradePlanSection
  report={reportQuery.data}
  isLoading={reportQuery.isLoading}
  currentClose={latest?.close ?? null}
/>
<div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
  <Card>{/* ScoreBreakdown */}</Card>
  <Card>{/* AIReportPanel */}</Card>
</div>
```

### Price Level Row with Percentage

```typescript
function PriceLevelRow({
  label,
  price,
  currentClose,
}: {
  label: string;
  price: number | null;
  currentClose: number | null;
}) {
  if (price == null) return null;
  
  const pctVariance = currentClose
    ? ((price - currentClose) / currentClose) * 100
    : null;
  
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-sm font-semibold">
          {formatVND(price)}
        </span>
        {pctVariance != null && (
          <span className={`text-xs text-muted-foreground ${pctVariance < 0 ? "text-red-500" : "text-green-500"}`}>
            ({pctVariance >= 0 ? "+" : ""}{pctVariance.toFixed(1)}%)
          </span>
        )}
      </div>
    </div>
  );
}
```

### Signal Conflict Alert

```typescript
// Source: [VERIFIED: D-06 decision, AlertCircle usage in admin pages]
function SignalConflictAlert({ text }: { text: string }) {
  const t = useTranslations("stock.tradePlan");
  return (
    <div className="flex gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3">
      <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" />
      <div>
        <p className="text-xs font-semibold text-yellow-700 dark:text-yellow-300">
          {t("signalConflict")}
        </p>
        <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
          {text}
        </p>
      </div>
    </div>
  );
}
```

### i18n Keys to Add

```json
// vi.json — stock.tradePlan
"tradePlan": {
  "title": "Kế Hoạch Giao Dịch",
  "entryZone": "Vùng vào lệnh",
  "stopLoss": "Cắt lỗ",
  "targetPrice": "Giá mục tiêu",
  "riskLevel": "Mức rủi ro",
  "riskHigh": "Cao",
  "riskMedium": "Trung bình",
  "riskLow": "Thấp",
  "signalConflict": "⚠️ Xung đột tín hiệu",
  "catalyst": "Chất xúc tác"
}

// en.json — stock.tradePlan
"tradePlan": {
  "title": "Trade Plan",
  "entryZone": "Entry Zone",
  "stopLoss": "Stop-Loss",
  "targetPrice": "Target Price",
  "riskLevel": "Risk Level",
  "riskHigh": "High",
  "riskMedium": "Medium",
  "riskLow": "Low",
  "signalConflict": "⚠️ Signal Conflict",
  "catalyst": "Catalyst"
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| content_json had 9 fields | content_json now has 15 fields (6 new Optional) | Phase 19 (v1.4) | Frontend must handle both old (null fields) and new shapes |
| No trade plan display | Trade plan fields computed server-side in Phase 20 | Phase 20 (v1.4) | Data is ready to consume — frontend just renders |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | @base-ui/react Tooltip supports touch/tap interaction on mobile | Pitfalls | Tooltip may not show on mobile; would need alternative display |
| A2 | `⚠️` emoji renders correctly in all target browsers | Code Examples | May need `AlertTriangle` lucide icon instead of emoji |
| A3 | TooltipPositioner accepts `sideOffset` prop | Code Examples | May need different positioning prop name — check @base-ui docs |

## Open Questions (RESOLVED)

1. **Layout placement of TradePlanSection in the grid** — RESOLVED
   - What we know: D-01 says "between Score Breakdown and AI Report Panel." Current layout has them side-by-side in a 2-column grid.
   - Resolution: Full-width row above the 2-column grid (simplest, doesn't break existing layout). This places Trade Plan visually between the chart section and the score+report row — user scrolls: Chart → Trade Plan → Score + AI Report. D-02 gives agent discretion on layout.

2. **Risk badge tooltip content source** — RESOLVED
   - What we know: D-04 says "reasoning text from the LLM report" but there's no dedicated `risk_reasoning` field.
   - Resolution: Use `report.summary` (2-3 sentence overview) as tooltip text. This is the most information-dense field summarizing the LLM's analysis.

3. **Entry zone as range vs single price** — RESOLVED
   - What we know: FRONTEND-01 says "entry zone" (range), but content_json only has a single `entry_price` (float). Backend computes entry as `(entry_lower + entry_upper) / 2`.
   - Resolution: Display as single price with `formatVND(entry_price)`. Label as "Điểm vào" (entry point) since backend has already averaged the range.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (configured in apps/helios/vitest.config.ts) |
| Config file | `apps/helios/vitest.config.ts` |
| Quick run command | `cd apps/helios && npx vitest run --reporter=verbose` |
| Full suite command | `cd apps/helios && npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRONTEND-01 | extractTradePlan returns correct data from content_json | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "extract" --reporter=verbose` | ❌ Wave 0 |
| FRONTEND-01 | formatVND displays prices correctly | unit | Already covered by existing utils | ✅ |
| FRONTEND-02 | Risk badge maps rating to correct color class | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "risk" --reporter=verbose` | ❌ Wave 0 |
| FRONTEND-03 | extractTradePlan returns null for pre-v1.4 reports | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "null" --reporter=verbose` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/helios && npx vitest run tests/trade-plan.test.ts --reporter=verbose`
- **Per wave merge:** `cd apps/helios && npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/helios/tests/trade-plan.test.ts` — covers FRONTEND-01, FRONTEND-02, FRONTEND-03 (extractTradePlan logic, risk color mapping, null handling)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Type narrowing in extractTradePlan — never trust content_json shape |
| V6 Cryptography | no | — |

### Known Threat Patterns for React/Next.js Frontend

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via signal_conflicts text | Tampering | React auto-escapes JSX text content — no dangerouslySetInnerHTML |
| Prototype pollution from content_json | Tampering | Type-narrow each field explicitly; don't spread content_json into component props |

## Sources

### Primary (HIGH confidence)
- `apps/helios/src/app/stock/[symbol]/page.tsx` — current page layout, data flow, component composition
- `apps/helios/src/lib/types.ts` — StockReport interface (content_json: Record<string, unknown>)
- `apps/helios/src/lib/utils.ts` — formatVND, gradeColors, cn utilities
- `apps/helios/src/lib/queries.ts` — useStockReport hook definition
- `apps/helios/src/components/stock/ai-report-panel.tsx` — report rendering patterns
- `apps/helios/src/components/stock/score-breakdown.tsx` — score rendering patterns
- `apps/helios/src/components/rankings/grade-badge.tsx` — badge pattern
- `apps/helios/src/components/stock/recommendation-badge.tsx` — color-coded badge with Vietnamese text
- `apps/helios/src/components/ui/tooltip.tsx` — @base-ui tooltip wrapper
- `apps/helios/src/components/ui/skeleton.tsx` — loading placeholder
- `apps/helios/src/components/ui/card.tsx` — Card component system
- `apps/prometheus/src/localstock/ai/client.py` — StockReport Pydantic model (15 fields)
- `apps/prometheus/src/localstock/services/report_service.py` — get_report() returns content_json = report.content_json
- `apps/helios/messages/vi.json` — existing i18n keys
- `apps/helios/messages/en.json` — existing i18n keys

### Secondary (MEDIUM confidence)
- None needed — all findings from direct codebase inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all verified in codebase
- Architecture: HIGH — clear data flow from existing useStockReport → content_json → new component
- Pitfalls: HIGH — identified from actual codebase patterns and type definitions

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable — no external dependency changes expected)
