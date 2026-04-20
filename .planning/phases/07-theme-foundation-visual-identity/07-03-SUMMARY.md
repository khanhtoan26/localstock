---
phase: 07-theme-foundation-visual-identity
plan: 03
subsystem: ui
tags: [react-markdown, tailwindcss-typography, shadcn, tabs, collapsible, stock-page]

requires:
  - phase: 07-02
    provides: Theme-aware chart system and useChartTheme hook
provides:
  - AIReportPanel component with markdown rendering and ScrollArea
  - ScoreBreakdown component with 4-dimension visual progress bars
  - Tabs and Collapsible shadcn UI components (base-nova)
  - @tailwindcss/typography plugin configured for prose classes
affects: [07-04-stock-page-layout]

tech-stack:
  added: [react-markdown@10, @tailwindcss/typography@0.5]
  patterns: [prose-typography-rendering, scroll-area-content-panels]

key-files:
  created:
    - apps/helios/src/components/stock/ai-report-panel.tsx
    - apps/helios/src/components/stock/score-breakdown.tsx
    - apps/helios/src/components/ui/tabs.tsx
    - apps/helios/src/components/ui/collapsible.tsx
  modified:
    - apps/helios/src/app/globals.css
    - apps/helios/package.json

key-decisions:
  - "Wrapped Markdown in div with prose classes (react-markdown v10 dropped className prop)"
  - "Used prose-sm for consistency with 14px body text, max-w-none to let parent control width"

patterns-established:
  - "Markdown rendering: wrap <Markdown> in <div className='prose dark:prose-invert'>"
  - "Score visualization: progress bars with dimension-specific colors (blue/emerald/amber/violet)"

requirements-completed: [STOCK-02]

duration: 5min
completed: 2025-06-19
---

# Plan 07-03: Stock Page Component Dependencies & Building Blocks

**AIReportPanel with react-markdown prose rendering, ScoreBreakdown with 4-dimension visual bars, plus shadcn Tabs/Collapsible and @tailwindcss/typography**

## Performance

- **Duration:** 5 min
- **Started:** 2025-06-19
- **Completed:** 2025-06-19
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Installed react-markdown and @tailwindcss/typography as npm dependencies
- Generated shadcn Tabs and Collapsible components (base-nova style)
- Created AIReportPanel: markdown rendering via prose typography, ScrollArea internal scroll, summary→content_json fallback
- Created ScoreBreakdown: 4 Vietnamese-labeled dimension scores with visual progress bars

## Task Commits

1. **Task 1+2: Dependencies, shadcn components, AIReportPanel, ScoreBreakdown** - `e64ce2f` (feat)

## Files Created/Modified
- `apps/helios/src/components/stock/ai-report-panel.tsx` - Markdown-rendered AI report with ScrollArea
- `apps/helios/src/components/stock/score-breakdown.tsx` - 4-dimension score breakdown with visual bars
- `apps/helios/src/components/ui/tabs.tsx` - Shadcn Tabs component (base-nova)
- `apps/helios/src/components/ui/collapsible.tsx` - Shadcn Collapsible component (base-nova)
- `apps/helios/src/app/globals.css` - Added @plugin "@tailwindcss/typography"
- `apps/helios/package.json` - Added react-markdown, @tailwindcss/typography
- `apps/helios/package-lock.json` - Lock file updated

## Decisions Made
- react-markdown v10 no longer accepts `className` prop — wrapped `<Markdown>` in a `<div>` with prose classes instead
- Used `prose-sm` (not default prose) to match existing 14px body text size

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] react-markdown v10 API change**
- **Found during:** Task 2 (AIReportPanel creation)
- **Issue:** `<Markdown className="...">` fails type check in v10 — `className` prop removed
- **Fix:** Wrapped `<Markdown>` in `<div className="prose dark:prose-invert prose-sm max-w-none">`
- **Verification:** `npm run build` passes
- **Committed in:** e64ce2f

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** API adaptation necessary for v10 compatibility. No scope creep.

## Issues Encountered
- shadcn CLI failed with SSL certificate error — resolved with `NODE_TLS_REJECT_UNAUTHORIZED=0` workaround

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AIReportPanel and ScoreBreakdown ready for consumption by 07-04 (StockDataPanel + page layout)
- Tabs and Collapsible components available for right panel tab structure
- Typography plugin active for prose rendering

---
*Phase: 07-theme-foundation-visual-identity*
*Completed: 2025-06-19*
