---
phase: 10-interactive-glossary-linking
plan: 02
name: Wire GlossaryMarkdown into AI Report Panel
status: complete
completed: 2026-04-21T16:10:00Z
duration: ~2hrs (including debugging)
subsystem: frontend/stock
tags: [glossary-linking, ai-report, component-wiring, react-strict-mode-fix]
dependency_graph:
  requires: [GlossaryMarkdown from Plan 01]
  provides: [glossary-linked AI report rendering]
  affects: [stock page AI report display]
tech_stack:
  added: []
  patterns: [drop-in component replacement, per-invocation state isolation]
key_files:
  created: []
  modified:
    - apps/helios/src/components/stock/ai-report-panel.tsx
    - apps/helios/src/components/glossary/glossary-markdown.tsx
decisions:
  - Drop-in replacement of Markdown with GlossaryMarkdown
  - Moved linkedIds into processChildren to fix react-markdown memoization interaction with React strict mode
  - Filtered out react-markdown node prop from DOM spread
metrics:
  duration: 2hrs
  tasks_completed: 2
  tasks_total: 2
  tests_added: 0
  files_created: 0
  files_modified: 2
---

# Phase 10 Plan 02: Wire GlossaryMarkdown + Visual Verification

Drop-in replacement of `<Markdown>` with `<GlossaryMarkdown>` in ai-report-panel.tsx, plus two rounds of bug fixing for React strict mode / react-markdown memoization issues.

## What Was Built

### Task 1: ai-report-panel.tsx — Component Wiring
- Replaced `import Markdown from "react-markdown"` with `import { GlossaryMarkdown }`
- Replaced `<Markdown>{content}</Markdown>` with `<GlossaryMarkdown content={content} />`
- All existing functionality preserved

### Task 2: Visual Verification + Bug Fixes
- **Bug 1 (React strict mode)**: `useRef` for `linkedIds` persisted across strict mode double-renders, causing 0 matches on committed render. Fixed with plain `const linkedIds = new Set()`.
- **Bug 2 (react-markdown memoization)**: react-markdown internally caches component callbacks, so `linkedIds` at component level was shared across strict mode renders. Fixed by moving Set creation into each `processChildren` invocation.
- Also filtered out react-markdown's `node` prop to avoid DOM attribute warnings.
- Visual verification passed: dotted underlines, hover cards, click-through all working.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| d16a403 | feat | Wire GlossaryMarkdown into AI report panel |
| 18124fe | fix | Use per-render Set for linkedIds instead of useRef |
| 17db8f4 | fix | Move linkedIds into processChildren to fix react-markdown memoization |

## Verification Results

- ✅ 16/16 vitest tests pass
- ✅ Visual: dotted underlines visible on glossary terms
- ✅ Visual: hover card shows definition, formula, "Xem chi tiết →"
- ✅ Visual: P/E, RSI matched correctly
- ✅ User approved visual result
