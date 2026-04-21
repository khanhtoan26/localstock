---
phase: 10-interactive-glossary-linking
plan: 01
name: Glossary Text Scanner & Interactive Components
status: complete
completed: 2026-04-21T07:58:00Z
duration: ~5min
subsystem: frontend/glossary
tags: [text-scanning, popover, react-markdown, glossary-linking]
dependency_graph:
  requires: [glossary.ts data module from Phase 9]
  provides: [buildAliasMap, scanText, GlossaryTerm, GlossaryMarkdown]
  affects: [ai-report-panel.tsx via Plan 02 wiring]
tech_stack:
  added: [vitest (devDependency for TDD)]
  patterns: [pure-function text scanner, @base-ui/react Popover with openOnHover, react-markdown component overrides]
key_files:
  created:
    - apps/helios/src/lib/glossary-linker.ts
    - apps/helios/src/components/glossary/glossary-term.tsx
    - apps/helios/src/components/glossary/glossary-markdown.tsx
    - apps/helios/src/lib/__tests__/glossary-linker.test.ts
    - apps/helios/vitest.config.ts
  modified: []
decisions:
  - Used character-by-character cursor scan with textStart tracking instead of indexOf-based jump optimization (eliminated text fragmentation bug from word boundary failures)
  - Module-level buildAliasMap() for GlossaryMarkdown (static data, no SSR concern)
  - ReactElement<{ children?: ReactNode }> typing for cloneElement to satisfy strict TypeScript
metrics:
  duration: 5min
  tasks_completed: 2
  tasks_total: 2
  tests_added: 16
  files_created: 5
  files_modified: 2
---

# Phase 10 Plan 01: Glossary Text Scanner & Interactive Components Summary

Pure-function text scanner (glossary-linker.ts) with longest-first alias matching, case-insensitive comparison, word boundary validation, and first-occurrence tracking; GlossaryTerm hover card via @base-ui/react Popover with openOnHover; GlossaryMarkdown wraps react-markdown with glossary-aware component overrides for p/li/td/th elements.

## What Was Built

### glossary-linker.ts — Text Scanning Engine
- `buildAliasMap()`: Collects all aliases from glossary entries, sorts by length descending (longest-first per D-05)
- `scanText(text, aliasMap, linkedIds)`: Character-by-character scanner with case-insensitive matching via toLowerCase(), word boundary checks via Unicode regex `/[\p{L}\p{N}]/u`, first-occurrence-only tracking via linkedIds Set
- `isWordBoundary(char)`: Prevents partial matches (e.g., "MA" inside "thematic")
- No diacritic normalization per D-06 — exact Vietnamese diacritic matching

### glossary-term.tsx — Interactive Hover Card
- `GlossaryTerm` component: inline `<span>` trigger with dotted underline (`decoration-dotted underline underline-offset-2 decoration-primary`)
- @base-ui/react Popover with `openOnHover`, `delay={200}`, `closeDelay={300}`, `nativeButton={false}`, `render={<span />}`
- Hover card shows: term name (semibold), shortDef (muted), optional formula (mono code block), "Xem chi tiết →" link
- Link navigates to `/learn/{category}#{id}` via Next.js `<Link>` with `aria-label`

### glossary-markdown.tsx — Markdown Wrapper
- `GlossaryMarkdown` component wraps react-markdown with `components` prop overrides
- Overrides `p`, `li`, `td`, `th` elements to process text through `scanText`
- `processChildren()` recursively handles React element children (bold, italic terms get scanned)
- Skips `<code>` elements per RESEARCH A2
- `linkedIdsRef` shared across all element overrides for cross-paragraph first-occurrence tracking

### Test Suite (TDD)
- 16 vitest tests for glossary-linker.ts covering:
  - isWordBoundary: undefined, space, punctuation, letters, digits, Vietnamese Unicode
  - buildAliasMap: sorting, structure
  - scanText: longest match, first-occurrence, case-insensitive, word boundaries, linkedIds respect, multiple terms

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Text fragmentation from indexOf-based jump optimization**
- **Found during:** Task 1 GREEN phase
- **Issue:** The original indexOf-based optimization for skipping to next potential match position didn't account for word boundary failures. When "MA" had a potential match inside "thematic" but failed the boundary check, the text was fragmented into ["th", "e", "matic content"] instead of ["thematic content"].
- **Fix:** Replaced indexOf jump optimization with simple `cursor++` advancement and textStart tracking. Character-by-character scanning is fast enough for ~90 aliases × ~20 paragraphs.
- **Files modified:** apps/helios/src/lib/glossary-linker.ts
- **Commit:** 524c809

**2. [Rule 1 - Bug] TypeScript spread types error with ReactElement**
- **Found during:** Task 2 build verification
- **Issue:** `cloneElement(child as ReactElement, { ...child.props, children: ... })` caused "Spread types may only be created from object types" with strict TypeScript.
- **Fix:** Cast to `ReactElement<{ children?: ReactNode }>` and use `cloneElement(el, { children: processChildren(el.props.children) })` without spreading existing props (cloneElement merges props automatically).
- **Files modified:** apps/helios/src/components/glossary/glossary-markdown.tsx
- **Commit:** 962f505

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 70a0e4b | test | Add failing tests for glossary-linker text scanning (TDD RED) |
| 524c809 | feat | Implement glossary-linker text scanning utility (TDD GREEN) |
| 962f505 | feat | Create GlossaryTerm and GlossaryMarkdown components |
| 3b4a053 | chore | Add vitest devDependency for TDD tests |

## Verification Results

- ✅ `npm run build` in apps/helios passes with no TypeScript errors
- ✅ All 16 vitest tests pass
- ✅ glossary-linker.ts exports: buildAliasMap, scanText, isWordBoundary, AliasMapping, GlossaryMatch, TextSegment
- ✅ glossary-term.tsx: GlossaryTerm with Popover, openOnHover, delays, inline span, hover card content
- ✅ glossary-markdown.tsx: GlossaryMarkdown wrapping react-markdown with component overrides
- ✅ No normalizeForSearch import (D-06 compliance)

## Self-Check: PASSED

All 5 files exist, all 4 commits verified.
