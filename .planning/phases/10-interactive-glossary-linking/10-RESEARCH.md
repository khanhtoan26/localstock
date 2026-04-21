# Phase 10: Interactive Glossary Linking - Research

**Researched:** 2025-07-18
**Domain:** React text processing, popover/tooltip UI, react-markdown custom components
**Confidence:** HIGH

## Summary

Phase 10 adds interactive glossary linking to AI report text. The implementation has three distinct sub-problems: (1) building a text-scanning utility that finds glossary term aliases in markdown-rendered text and replaces them with interactive elements, (2) creating a hover/tap card component using `@base-ui/react` Popover that shows term previews, and (3) wiring click-through navigation to the existing `/learn/[category]#[term-id]` deep link target.

The codebase is well-prepared for this phase. The `glossary.ts` module already exports `getAllEntries()` with `aliases: string[]` per entry (25 entries, ~90 total aliases). The `ai-report-panel.tsx` component uses `react-markdown` v10's `<Markdown>` component which accepts a `components` prop for overriding rendered HTML elements. The learn page's `GlossarySearch` component already has URL hash detection and auto-scroll/expand logic for deep links. The `@base-ui/react` Popover component has a `openOnHover` prop on `PopoverTrigger` with configurable `delay`/`closeDelay`, making it an ideal fit for the hover card requirement.

**Primary recommendation:** Use `@base-ui/react` Popover with `openOnHover` for the hover card, override react-markdown's text-rendering elements via the `components` prop to inject glossary links, and build a pure-function text scanner that processes string children into mixed arrays of text + GlossaryLink components.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hover card shows: term (Vietnamese), short definition (shortDef), and a "Xem chi tiết →" link to /learn/[category]#[term-id]. If formula exists, show it below shortDef in a monospace block.
- **D-02:** Hover card width max-w-xs (320px).
- **D-03:** Highlighted terms use dotted underline with accent color (hsl(210 70.9% 51.6%)), solid on hover. No background color.
- **D-04:** Terms rendered as inline elements (`<span>` or `<a>`), not block.
- **D-05:** Longest-first matching — sort aliases by length (descending) before scanning text.
- **D-06:** Case-insensitive but NOT diacritic-insensitive matching.
- **D-07:** First occurrence only — subsequent occurrences render as normal text.
- **D-08:** Override react-markdown text rendering via custom component.
- **D-09:** Desktop: hover with 200ms delay before showing card. Card stays visible while mouse is over term or card.
- **D-10:** Mobile: tap to show card, tap outside to dismiss.
- **D-11:** Use Popover component from shadcn (or equivalent).
- **D-12:** "Xem chi tiết →" link navigates to `/learn/[category]#[term-id]`. Auto-scroll and expand matching entry.
- **D-13:** Navigation uses Next.js `<Link>` for client-side routing.

### Agent's Discretion
- Exact hover card animation/transition
- Whether to use Popover from shadcn or a custom lightweight tooltip
- How to structure the text-scanning utility (regex vs string search)
- Whether to memoize the processed markdown content
- Error handling if a glossary entry is referenced but not found
- Z-index and positioning strategy for hover cards

### Deferred Ideas (OUT OF SCOPE)
- **EDU-01:** Live example charts embedded in glossary entries
- **EDU-02:** Cross-linking between related glossary entries ("Xem thêm: MACD, Bollinger Bands")
- **EDU-03:** AI-powered simplification of glossary content
- **LINK-01:** Glossary linking in score breakdowns and market pages (not just AI reports)
- **LINK-02:** Click analytics on glossary terms
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GLOSS-01 | Auto-link glossary terms in AI report text via react-markdown component override | react-markdown v10 `components` prop overrides `p`, `li`, `td`, `th` — text scanner processes string children into GlossaryLink components |
| GLOSS-02 | Hover card preview showing short definition + link to full learn page | `@base-ui/react` Popover with `openOnHover` on trigger, `delay={200}` — supports hoverable popup content natively |
| GLOSS-03 | Click-through navigation from report → /learn/[category]#[term] (deep link) | GlossarySearch already has hash detection + auto-scroll + auto-expand via `defaultOpen={entry.id === hashId}` |
| GLOSS-04 | Alias-based matching with longest-first strategy | Build alias map from `getAllEntries()`, sort by length descending, scan text with indexOf loop |
</phase_requirements>

## Project Constraints (from copilot-instructions.md)

- Next.js 16+ with App Router [VERIFIED: package.json shows `"next": "16.2.4"`]
- React 19 [VERIFIED: package.json shows `"react": "19.2.4"`]
- `@base-ui/react` for primitives (NOT Radix UI) [VERIFIED: package.json shows `"@base-ui/react": "^1.4.0"`]
- `lucide-react` for icons [VERIFIED: used across existing components]
- Named exports (not default exports) [VERIFIED: all existing components follow this pattern]
- Tailwind CSS v4 [VERIFIED: `@import "tailwindcss"` in globals.css]
- `shadcn` CLI 4.2+ for UI component scaffolding [VERIFIED: copilot-instructions.md]

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-markdown | ^10.1.0 | Markdown rendering with custom components | Already in use in ai-report-panel.tsx; `components` prop enables text-node interception [VERIFIED: package.json] |
| @base-ui/react | ^1.4.0 | Popover primitive for hover cards | Project-locked UI primitive. Popover.Trigger has `openOnHover`, `delay`, `closeDelay` props — purpose-built for this use case [VERIFIED: node_modules type definitions] |
| next | 16.2.4 | Client-side routing via `<Link>` | Already installed, needed for click-through navigation [VERIFIED: package.json] |

### No New Dependencies Required

This phase requires zero new npm packages. All functionality is covered by existing dependencies:
- Text scanning: pure TypeScript string manipulation
- Hover card: `@base-ui/react` Popover (already installed)
- Markdown override: `react-markdown` (already installed)
- Navigation: `next/link` (already installed)
- Icons: `lucide-react` (already installed)

## Architecture Patterns

### Recommended File Structure

```
apps/helios/src/
├── lib/
│   ├── glossary.ts                    # Existing — data + types (unchanged)
│   └── glossary-linker.ts             # NEW — text scanning utility (pure functions)
├── components/
│   ├── stock/
│   │   └── ai-report-panel.tsx        # MODIFIED — add components prop to <Markdown>
│   └── glossary/
│       ├── glossary-term.tsx           # NEW — inline term trigger + popover hover card
│       └── glossary-markdown.tsx       # NEW — markdown wrapper with glossary-aware components
└── app/learn/[category]/page.tsx      # Existing (unchanged — deep link already works)
```

### Pattern 1: Text Scanner (glossary-linker.ts)

**What:** Pure function that takes a text string and an alias map, returns an array of `string | GlossaryMatch` segments. The scanner finds all alias matches in the text, applies longest-first priority, and marks only the first occurrence of each entry.

**When to use:** Called by the react-markdown component overrides for every text-containing element.

**Key design decisions:**
- Build alias map once: `Map<string (lowercased alias), GlossaryEntry>` — sorted by alias length descending [VERIFIED: D-05, D-06]
- Use `String.prototype.indexOf` with case-insensitive comparison (lowercase both sides) for matching — NOT regex [ASSUMED: indexOf is simpler and avoids regex special character escaping issues with terms like "P/E", "D/E", "%K", "%D"]
- Track a `Set<string>` of already-linked entry IDs for first-occurrence-only behavior [VERIFIED: D-07]

```typescript
// Source: Architecture recommendation based on codebase analysis

interface GlossaryMatch {
  entry: GlossaryEntry;
  matchedText: string; // Preserve original casing from source text
}

type TextSegment = string | GlossaryMatch;

// Build once, reuse across all renders
function buildAliasMap(entries: GlossaryEntry[]): { alias: string; entry: GlossaryEntry }[] {
  const pairs: { alias: string; entry: GlossaryEntry }[] = [];
  for (const entry of entries) {
    for (const alias of entry.aliases) {
      pairs.push({ alias, entry });
    }
  }
  // Sort by alias length descending — longest-first matching (D-05)
  pairs.sort((a, b) => b.alias.length - a.alias.length);
  return pairs;
}

// Process a single text string into segments
function processText(
  text: string,
  aliasMap: { alias: string; entry: GlossaryEntry }[],
  linkedIds: Set<string>,
): TextSegment[] {
  // ... scanning logic
}
```

### Pattern 2: react-markdown Component Override

**What:** The `<Markdown>` component's `components` prop maps HTML tag names to custom React components. To intercept text content, override elements that contain text: `p`, `li`, `td`, `th`, `strong`, `em`.

**Critical insight:** react-markdown v10's `components` prop type is `{ [Key in keyof JSX.IntrinsicElements]?: ComponentType<...> }`. Overriding `p` gives access to `children` which may be strings or React elements (for inline formatting like bold/italic). The text scanner must handle both — process strings, pass through non-string children. [VERIFIED: react-markdown lib/index.d.ts type definitions]

```typescript
// Source: react-markdown v10 API (verified from node_modules type definitions)

// The components prop maps tag names to custom renderers
<Markdown components={{
  p: ({ children, ...props }) => (
    <p {...props}>{processChildren(children, aliasMap, linkedIds)}</p>
  ),
  li: ({ children, ...props }) => (
    <li {...props}>{processChildren(children, aliasMap, linkedIds)}</li>
  ),
  // ... other text-containing elements
}}>
  {content}
</Markdown>
```

**Important:** The `processChildren` function must recursively handle React children — when it encounters a string, it runs the text scanner; when it encounters a React element (e.g., `<strong>`, `<em>`, `<code>`), it recursively processes that element's children. Skip `<code>` elements to avoid linking terms inside code blocks. [ASSUMED]

### Pattern 3: @base-ui/react Popover for Hover Card

**What:** Use `@base-ui/react` Popover with `openOnHover` on the trigger. This gives hover-on-desktop and tap-on-mobile behavior with configurable delays.

**Why Popover over Tooltip:** The hover card contains interactive content (a clickable "Xem chi tiết →" link). Tooltips are informational-only by convention. Popover supports rich interactive content and the `openOnHover` prop makes it behave like a tooltip when needed. [VERIFIED: PopoverTrigger.d.ts shows `openOnHover?: boolean`, `delay?: number`, `closeDelay?: number`]

```typescript
// Source: @base-ui/react Popover API (verified from node_modules type definitions)
import { Popover } from "@base-ui/react/popover";

<Popover.Root>
  <Popover.Trigger
    openOnHover
    delay={200}      // D-09: 200ms hover delay
    closeDelay={300}  // Keep card visible briefly when moving to it
    nativeButton={false}  // Renders as span, not button
    render={<span />}     // Inline element per D-04
  >
    {matchedText}
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Positioner sideOffset={8}>
      <Popover.Popup>
        {/* Card content: term, shortDef, formula, link */}
      </Popover.Popup>
    </Popover.Positioner>
  </Popover.Portal>
</Popover.Root>
```

**Key Popover props verified from type definitions:**
- `PopoverTrigger.openOnHover`: `boolean` (default: `false`) — enables hover opening [VERIFIED: PopoverTrigger.d.ts]
- `PopoverTrigger.delay`: `number` (default: `300`) — ms before open on hover [VERIFIED: PopoverTrigger.d.ts]
- `PopoverTrigger.closeDelay`: `number` (default: `0`) — ms before close after hover leaves [VERIFIED: PopoverTrigger.d.ts]
- `PopoverTrigger.nativeButton`: `boolean` (default: `true`) — set to `false` when rendering as non-button [VERIFIED: PopoverTrigger.d.ts]
- `PopoverTrigger.render`: accepts `ReactElement` to change rendered element (e.g., `<span />`) [VERIFIED: BaseUIComponentProps types]

### Pattern 4: Deep Link Click-Through

**What:** The "Xem chi tiết →" link navigates to `/learn/{category}#{entry.id}`. The target page already handles this.

**Already implemented in Phase 9:**
- `GlossarySearch` component reads `window.location.hash` on mount [VERIFIED: glossary-search.tsx line 27]
- Matching entry auto-expands via `defaultOpen={entry.id === hashId}` [VERIFIED: glossary-search.tsx line 100]
- Auto-scroll via `el.scrollIntoView({ behavior: "smooth", block: "start" })` [VERIFIED: glossary-search.tsx line 32]
- `GlossaryEntryCard` renders with `id={entry.id}` and `className="scroll-mt-20"` [VERIFIED: glossary-entry-card.tsx line 20]

**No changes needed on the learn page side.** The deep link target is fully functional.

### Anti-Patterns to Avoid

- **Regex-based matching with unescaped special characters:** Aliases contain regex-special chars like `%K`, `%D`, `P/E`, `D/E`. Using `new RegExp(alias)` without escaping will break. Use `indexOf` instead. [VERIFIED: glossary.ts aliases include "%K", "%D", "P/E", "D/E"]
- **Modifying glossary.ts:** This phase should NOT change the glossary data module. It's a consumer, not a modifier.
- **Global mutable state for linked IDs tracking:** The `linkedIds` Set must be scoped per-render of the AI report, not global. Otherwise, navigating between stock pages would incorrectly skip linking.
- **Wrapping each term in its own Popover.Root:** Each `GlossaryTerm` component needs its own `Popover.Root` — but avoid creating 25+ provider contexts unnecessarily. The popover is lightweight and only mounts the popup when opened.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hover/tap popover | Custom mouseenter/mouseleave/touch handlers | `@base-ui/react` Popover with `openOnHover` | Handles focus management, positioning, portal rendering, dismissal, mobile tap vs hover, accessibility attributes (aria-describedby, role). Edge cases: scroll repositioning, viewport boundary flipping, nested interactive content. [VERIFIED: Popover API] |
| Popover positioning | Manual `getBoundingClientRect` + absolute positioning | `@base-ui/react` Popover.Positioner | Uses Floating UI internally for viewport-aware positioning with flip/shift/offset. [VERIFIED: Positioner component exists in popover/] |
| Markdown rendering | Custom markdown parser | `react-markdown` v10 `components` prop | Already in use. Custom components prop is the supported API for exactly this use case. [VERIFIED: ai-report-panel.tsx] |

**Key insight:** The `@base-ui/react` Popover already solves the hardest UX problems — hover delay, hover-to-popup bridge (keeping card open while moving mouse from trigger to popup), mobile tap behavior, focus trapping, portal rendering, and viewport-aware positioning. Hand-rolling any of these would be a major time sink.

## Common Pitfalls

### Pitfall 1: Partial Match Collision
**What goes wrong:** "RSI" matches inside "chỉ số RSI", creating overlapping or double links.
**Why it happens:** Shorter aliases match substrings of longer aliases.
**How to avoid:** Sort aliases by length descending (longest-first per D-05). When a match is found, mark those character positions as consumed. The scanner advances past the match, preventing overlapping.
**Warning signs:** "chỉ số RSI" shows two highlights — one for the full phrase and one for "RSI" within it.

### Pitfall 2: React Children Type Complexity
**What goes wrong:** Text scanner only handles `string` children but react-markdown passes mixed children arrays (strings + React elements for inline formatting).
**Why it happens:** Markdown like `**RSI** là chỉ báo` becomes `[<strong>RSI</strong>, " là chỉ báo"]` in React children — the text scanner never sees the "RSI" string inside `<strong>`.
**How to avoid:** The `processChildren` function must recursively process React element children. For each child: if string → scan for terms; if React element → clone with processed children; if other → pass through.
**Warning signs:** Bold or italic terms never get linked.

### Pitfall 3: Inline vs Block Element Nesting
**What goes wrong:** Wrapping a `<span>` trigger inside `<p>` is fine, but if the Popover renders a `<div>` inside `<p>`, React warns about invalid DOM nesting.
**Why it happens:** Popover.Popup renders a `<div>` by default. If the popup is portaled (rendered via `Popover.Portal`), this is avoided because the popup renders at document body level.
**How to avoid:** Always use `Popover.Portal` to render the popup outside the prose text flow. [VERIFIED: Portal component exists in popover/]
**Warning signs:** React hydration warnings or DOM nesting warnings in console.

### Pitfall 4: Performance with Many Terms
**What goes wrong:** Scanning every text node against ~90 aliases on every render could be slow.
**Why it happens:** AI reports can have many paragraphs; each `p` element triggers a scan.
**How to avoid:** (1) Build the alias map once outside render (module-level or via `useMemo`). (2) The first-occurrence-only rule (D-07) means the `linkedIds` set grows quickly, and the scanner can early-exit once all 25 entries are linked. (3) Memoize the processed content with `useMemo` keyed on the report text.
**Warning signs:** Noticeable lag when switching between stock pages.

### Pitfall 5: Word Boundary Issues with Vietnamese
**What goes wrong:** "EMA" matches inside "thEMA" or other unintended substrings.
**Why it happens:** Vietnamese doesn't use spaces between all words the way English does, and simple `indexOf` has no word boundary awareness.
**How to avoid:** For short aliases (≤3 chars like "MA", "EMA", "BB"), check that the match is not surrounded by word characters (letters, digits). For longer aliases and Vietnamese phrases, this is less of a concern because they're specific enough. A lightweight boundary check: verify the character before and after the match is not a letter/digit (or is start/end of string).
**Warning signs:** False positive matches in unrelated Vietnamese words.

### Pitfall 6: Stale linkedIds Across Paragraphs
**What goes wrong:** Each `<p>` component override creates its own `linkedIds` Set, so the same term gets linked in every paragraph (violating D-07 first-occurrence-only).
**Why it happens:** The `components` prop creates independent component instances for each `<p>`.
**How to avoid:** Lift the `linkedIds` Set to the wrapper component (`GlossaryMarkdown`) and pass it via React context or closure. All `<p>`, `<li>`, etc. share the same Set instance during a single render pass.
**Warning signs:** "RSI" is highlighted in every paragraph instead of just the first.

## Code Examples

### Example 1: Alias Map Builder

```typescript
// Source: Architecture recommendation
// File: apps/helios/src/lib/glossary-linker.ts

import { getAllEntries, type GlossaryEntry } from "@/lib/glossary";

export interface AliasMapping {
  aliasLower: string;  // Lowercased for case-insensitive matching
  alias: string;       // Original casing for display
  entry: GlossaryEntry;
}

export function buildAliasMap(): AliasMapping[] {
  const entries = getAllEntries();
  const mappings: AliasMapping[] = [];

  for (const entry of entries) {
    for (const alias of entry.aliases) {
      mappings.push({
        aliasLower: alias.toLowerCase(),
        alias,
        entry,
      });
    }
  }

  // Longest-first sort (D-05)
  mappings.sort((a, b) => b.aliasLower.length - a.aliasLower.length);
  return mappings;
}
```

### Example 2: Text Scanner

```typescript
// Source: Architecture recommendation
// File: apps/helios/src/lib/glossary-linker.ts

export interface GlossaryMatch {
  entry: GlossaryEntry;
  matchedText: string; // Original text from source (preserves casing)
}

export type TextSegment = string | GlossaryMatch;

function isWordBoundary(char: string | undefined): boolean {
  if (char === undefined) return true; // Start/end of string
  return !/[\p{L}\p{N}]/u.test(char);  // Not a letter or digit
}

export function scanText(
  text: string,
  aliasMap: AliasMapping[],
  linkedIds: Set<string>,
): TextSegment[] {
  const segments: TextSegment[] = [];
  const textLower = text.toLowerCase();
  let cursor = 0;

  while (cursor < text.length) {
    let matched = false;

    for (const { aliasLower, entry } of aliasMap) {
      // Skip if this entry already linked (first-occurrence-only)
      if (linkedIds.has(entry.id)) continue;

      const idx = textLower.indexOf(aliasLower, cursor);
      if (idx !== cursor) continue; // Only match at current cursor position

      // Word boundary check
      const before = text[idx - 1];
      const after = text[idx + aliasLower.length];
      if (!isWordBoundary(before) || !isWordBoundary(after)) continue;

      // Found a match
      if (cursor < idx) {
        segments.push(text.slice(cursor, idx));
      }
      const matchedText = text.slice(idx, idx + aliasLower.length);
      segments.push({ entry, matchedText });
      linkedIds.add(entry.id);
      cursor = idx + aliasLower.length;
      matched = true;
      break;
    }

    if (!matched) {
      // No alias matches at this position, advance by one character
      // Optimization: find the next potential match position
      let nextMatch = text.length;
      for (const { aliasLower } of aliasMap) {
        const idx = textLower.indexOf(aliasLower, cursor + 1);
        if (idx !== -1 && idx < nextMatch) {
          nextMatch = idx;
        }
      }
      segments.push(text.slice(cursor, nextMatch));
      cursor = nextMatch;
    }
  }

  return segments;
}
```

### Example 3: GlossaryTerm Component

```typescript
// Source: Architecture recommendation using @base-ui/react Popover API
// File: apps/helios/src/components/glossary/glossary-term.tsx

"use client";

import Link from "next/link";
import { Popover } from "@base-ui/react/popover";
import type { GlossaryEntry } from "@/lib/glossary";

interface GlossaryTermProps {
  entry: GlossaryEntry;
  children: React.ReactNode; // The matched text from the source
}

export function GlossaryTerm({ entry, children }: GlossaryTermProps) {
  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={200}
        closeDelay={300}
        nativeButton={false}
        render={<span />}
        className="decoration-dotted underline underline-offset-2 decoration-primary cursor-pointer hover:decoration-solid"
      >
        {children}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={8} align="center">
          <Popover.Popup className="z-50 max-w-xs rounded-lg border bg-popover p-4 shadow-md">
            <p className="font-semibold text-sm">{entry.term}</p>
            <p className="text-sm text-muted-foreground mt-1">{entry.shortDef}</p>
            {entry.formula && (
              <code className="block bg-muted rounded p-2 text-xs font-mono mt-2">
                {entry.formula}
              </code>
            )}
            <Link
              href={`/learn/${entry.category}#${entry.id}`}
              className="text-xs text-primary hover:underline mt-2 inline-block"
            >
              Xem chi tiết →
            </Link>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
```

### Example 4: GlossaryMarkdown Wrapper

```typescript
// Source: Architecture recommendation combining react-markdown + glossary linker
// File: apps/helios/src/components/glossary/glossary-markdown.tsx

"use client";

import { useMemo, useRef } from "react";
import Markdown from "react-markdown";
import { buildAliasMap, scanText, type TextSegment } from "@/lib/glossary-linker";
import { GlossaryTerm } from "./glossary-term";
import type { ReactNode } from "react";

// Build alias map once at module level
const aliasMap = buildAliasMap();

interface GlossaryMarkdownProps {
  content: string;
}

export function GlossaryMarkdown({ content }: GlossaryMarkdownProps) {
  // Track linked IDs across all elements in this render
  const linkedIdsRef = useRef(new Set<string>());

  // Reset linked IDs when content changes
  useMemo(() => {
    linkedIdsRef.current = new Set<string>();
  }, [content]);

  function processChildren(children: ReactNode): ReactNode {
    if (typeof children === "string") {
      const segments = scanText(children, aliasMap, linkedIdsRef.current);
      return segments.map((seg, i) =>
        typeof seg === "string" ? seg : (
          <GlossaryTerm key={`${seg.entry.id}-${i}`} entry={seg.entry}>
            {seg.matchedText}
          </GlossaryTerm>
        )
      );
    }
    if (Array.isArray(children)) {
      return children.map((child, i) =>
        typeof child === "string" ? processChildren(child) : child
      );
    }
    return children;
  }

  return (
    <Markdown
      components={{
        p: ({ children, ...props }) => <p {...props}>{processChildren(children)}</p>,
        li: ({ children, ...props }) => <li {...props}>{processChildren(children)}</li>,
        td: ({ children, ...props }) => <td {...props}>{processChildren(children)}</td>,
        th: ({ children, ...props }) => <th {...props}>{processChildren(children)}</th>,
      }}
    >
      {content}
    </Markdown>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-markdown v8 `components.text` | react-markdown v10 override `p`, `li` etc. | v9+ (2024) | v10 removed the `text` component. Override parent elements instead. [VERIFIED: v10 type definition shows `Components = { [Key in keyof JSX.IntrinsicElements]?: ... }` — no `text` key] |
| Radix UI Popover | @base-ui/react Popover | Project decision | @base-ui/react Popover has `openOnHover` built-in on trigger — Radix equivalent requires manual hover handling [VERIFIED: project uses @base-ui/react exclusively] |
| shadcn HoverCard | @base-ui/react Popover with openOnHover | Project decision | shadcn's HoverCard wraps Radix. This project uses @base-ui/react. Popover with `openOnHover` provides equivalent behavior. [VERIFIED: no HoverCard component in project UI components] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `indexOf` is better than regex for alias matching due to special characters in aliases (%K, P/E, D/E) | Architecture Patterns - Pattern 1 | LOW — regex would work too if properly escaped, but indexOf is simpler |
| A2 | `<code>` elements inside markdown should be skipped (not scanned for glossary terms) | Pitfall 2 | LOW — terms in code blocks would get incorrectly highlighted, minor UX issue |
| A3 | Word boundary check with Unicode `\p{L}\p{N}` regex is sufficient for Vietnamese text | Code Example 2 | MEDIUM — might need tuning if false positives appear in Vietnamese compound words |
| A4 | `closeDelay={300}` on PopoverTrigger gives enough time for mouse to travel from trigger to popup | Code Example 3 | LOW — value can be adjusted easily; @base-ui handles hover bridge internally |
| A5 | Module-level `buildAliasMap()` is safe for Next.js (no SSR issues) | Code Example 4 | LOW — glossary.ts is static data, no runtime dependencies; worst case, move to component-level useMemo |

## Open Questions

1. **Performance of text scanning with ~90 aliases**
   - What we know: 25 entries × ~3.6 aliases each = ~90 aliases to check per text node. AI reports are typically 500-2000 words across 10-20 paragraphs.
   - What's unclear: Whether character-by-character scanning is fast enough or if a more optimized approach (like Aho-Corasick) is needed.
   - Recommendation: Start with the simple `indexOf` approach. Profile only if users report lag. ~90 aliases × ~20 paragraphs = ~1800 indexOf calls — this is trivially fast for modern JS engines.

2. **React children recursion depth**
   - What we know: react-markdown can produce nested inline elements: `<p><strong><em>RSI</em></strong> text</p>`.
   - What's unclear: How deep the nesting can go and whether recursive processing handles all edge cases.
   - Recommendation: Handle 2 levels (direct string children + one level of React element cloning). Deeper nesting is rare in AI-generated markdown.

3. **linkedIds ref vs state for first-occurrence tracking**
   - What we know: React refs don't trigger re-renders. Using a ref for `linkedIds` means the Set persists across the component tree render.
   - What's unclear: Whether React's rendering order guarantees that `<p>` elements are processed in document order.
   - Recommendation: Use `useRef` — React processes children in order during a synchronous render pass. This is safe for the current use case.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected — no test config or test files in project |
| Config file | None — needs Wave 0 setup |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GLOSS-01 | Text scanner identifies glossary terms in text | unit | `npx vitest run src/lib/glossary-linker.test.ts` | ❌ Wave 0 |
| GLOSS-04 | Longest-first matching prevents partial collisions | unit | `npx vitest run src/lib/glossary-linker.test.ts` | ❌ Wave 0 |
| GLOSS-04 | Case-insensitive, first-occurrence-only behavior | unit | `npx vitest run src/lib/glossary-linker.test.ts` | ❌ Wave 0 |
| GLOSS-02 | GlossaryTerm renders popover with correct content | manual-only | Visual inspection in browser | N/A |
| GLOSS-03 | Click-through navigates to /learn/[category]#[term] | manual-only | Visual inspection in browser | N/A |

### Sampling Rate
- **Per task commit:** Visual inspection of AI report page
- **Per wave merge:** Full visual check of hover cards + click-through navigation
- **Phase gate:** All 4 GLOSS requirements verified manually

### Wave 0 Gaps
- [ ] Test framework install: `npm install -D vitest @testing-library/react` (if unit tests are added)
- [ ] `apps/helios/src/lib/glossary-linker.test.ts` — covers GLOSS-01, GLOSS-04 (text scanning logic is pure functions — highly testable)

*(Note: The text scanning utility is the only pure-function, easily-testable part. Component rendering with popovers is best verified visually.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no auth in this personal tool |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes (minimal) | AI report text is rendered via react-markdown which sanitizes HTML by default |
| V6 Cryptography | No | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via AI report text | Tampering | react-markdown sanitizes HTML by default — no raw `dangerouslySetInnerHTML`. Glossary terms are rendered as text content, not injected as HTML. [VERIFIED: react-markdown handles sanitization] |
| Link injection via glossary aliases | Tampering | Aliases are static TypeScript constants, not user input. Navigation targets are computed from entry.category and entry.id — both static. |

**Risk assessment:** Very low. All data sources (glossary entries, AI report text) are internal/trusted. No user input flows into the linking logic.

## Sources

### Primary (HIGH confidence)
- `apps/helios/node_modules/@base-ui/react/esm/popover/` — Popover API types verified from installed package v1.4.0
- `apps/helios/node_modules/@base-ui/react/esm/tooltip/` — Tooltip API types verified for comparison
- `apps/helios/node_modules/react-markdown/lib/index.d.ts` — v10 Options/Components type definitions
- `apps/helios/src/lib/glossary.ts` — 25 entries, ~90 aliases, GlossaryEntry type with aliases field
- `apps/helios/src/components/stock/ai-report-panel.tsx` — Current Markdown usage
- `apps/helios/src/components/learn/glossary-search.tsx` — Deep link hash detection already implemented
- `apps/helios/src/components/learn/glossary-entry-card.tsx` — Card with id and scroll-mt-20
- `apps/helios/package.json` — Verified versions: react-markdown ^10.1.0, @base-ui/react ^1.4.0, next 16.2.4

### Secondary (MEDIUM confidence)
- npm registry — Verified latest versions: react-markdown 10.1.0, @base-ui/react 1.4.1

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already installed and verified from node_modules
- Architecture: HIGH — text scanning is a well-understood problem; @base-ui/react Popover API verified from type definitions; react-markdown components prop verified
- Pitfalls: HIGH — identified from actual codebase analysis (special chars in aliases, React children types, DOM nesting)
- Deep link integration: HIGH — verified existing implementation handles hash detection and auto-expand

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (stable — no fast-moving dependencies)
