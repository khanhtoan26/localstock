# Phase 9: Academic/Learning Page & Glossary Data - Research

**Researched:** 2026-04-20
**Domain:** Next.js App Router static pages, typed data modules, Vietnamese text search, Collapsible UI
**Confidence:** HIGH

## Summary

Phase 9 adds educational content pages (`/learn`) to the Helios dashboard, displaying glossary entries for technical indicators, fundamental ratios, and macro concepts used in AI reports. The implementation is entirely frontend — no API calls, no backend changes. The glossary data lives as a typed TypeScript module (`src/lib/glossary.ts`), consumed directly by Server Components and client-side search.

All required UI building blocks already exist in the codebase: Card, Badge, Collapsible (from `@base-ui/react`), Button, Skeleton, EmptyState, ErrorState. Only the `Input` component needs installation via shadcn CLI. The `react-markdown` v10 and `@tailwindcss/typography` v0.5.19 packages are already installed and configured for rendering markdown content. The sidebar navigation pattern is simple — an array of `{ href, label, icon }` objects.

**Primary recommendation:** Build the glossary data module first (it's the foundation), then create Server Component pages with client-side interactive wrappers for search and collapsible entry cards. Use `generateStaticParams` to statically generate the three category pages at build time.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Each glossary entry is a detailed article — includes definition, formula/calculation, how to read/interpret, practical examples, and related notes. Not just a short definition.
- **D-02:** Content language is Vietnamese with English technical terms in parentheses. Example: "Chỉ số sức mạnh tương đối (RSI)"
- **D-04:** Typed TypeScript module per REQUIREMENTS (LEARN-02). Single file `src/lib/glossary.ts` exporting typed Record with all entries. No JSON files, no MDX.
- **D-05:** ~25 entries covering all indicators actually used in the system (SMA, EMA, RSI, MACD, Bollinger Bands, P/E, P/B, EPS, ROE, ROA, D/E, revenue growth, profit growth, market cap, CPI, GDP, interest rates, exchange rates, etc.).
- **D-06:** Each entry must have: `id` (slug), `term` (Vietnamese name), `termEn` (English name), `aliases` (alternative names for Phase 10 matching), `category` (technical | fundamental | macro), `shortDef` (1-sentence definition), `content` (full markdown article), and `formula` (optional — for calculable indicators).
- **D-07:** Client-side array filter — simple `.filter()` on entry fields. No external library needed for ~25 entries.
- **D-08:** Diacritic-insensitive matching via normalization — matches "chi so" to "chỉ số".
- **D-10:** Add "Học" item to sidebar `navItems` array with `BookOpen` icon from lucide-react, linking to `/learn`.
- **D-11:** Hub page `/learn` with overview + category cards, then `/learn/[category]` pages for each category (LEARN-03 requires separate URLs). Enables Server Components per REQUIREMENTS.

### Agent's Discretion
- Exact card layout and expand/collapse animation
- Number of entries per category (aim for balanced distribution)
- Order of entries within a category (alphabetical vs grouped by complexity)
- Whether to show entry count per category on hub page
- Empty state handling (unlikely but defensive)
- URL structure for individual entries (if full pages instead of expandable cards)
- Display format (D-03): recommended expandable cards on category page
- Search bar position (D-09): recommended at top of each category page
- D-12: Visual style matches existing app — use Card components, consistent typography, badge/tag for category labels
- D-13: Responsive behavior — full-width cards on mobile, comfortable reading width on desktop

### Deferred Ideas (OUT OF SCOPE)
- **EDU-01**: Per-term live example charts — deferred to v1.2+
- **EDU-02**: Cross-linking between academic entries (seeAlso) — deferred to v1.2+
- **EDU-03**: AI-powered "giải thích đơn giản hơn" button — deferred to v1.2+
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEARN-01 | Trang Learn với 3 category pages: Technical Indicators / Fundamental Ratios / Macro Concepts | App Router `src/app/learn/page.tsx` (hub) + `src/app/learn/[category]/page.tsx` (category pages). Server Components with client wrappers. Existing Card/Badge components for layout. |
| LEARN-02 | Glossary data module (typed TypeScript Record, ≥15 entries ban đầu) làm single source of truth | `src/lib/glossary.ts` — typed `GlossaryEntry` interface, `Record<string, GlossaryEntry>` export, helper functions `getEntriesByCategory()`, `getAllEntries()`, `normalizeForSearch()`. 25+ entries. |
| LEARN-03 | Category-based routing (/learn/technical, /learn/fundamental, /learn/macro) với Server Components | Dynamic route `[category]` with `generateStaticParams()` returning 3 slugs. `notFound()` for invalid slugs. Server Component shell delegates interactivity to client components. |
| LEARN-04 | Search/filter entries với Vietnamese diacritic-insensitive matching (client-side) | `normalizeForSearch()` using `NFD` decomposition + combining mark removal + `Đ/đ` → `d` replacement. Client component with controlled `Input` + `.filter()` on ~25 entries. No debounce needed. |
</phase_requirements>

## Project Constraints (from copilot-instructions.md)

- Stack: Next.js 16 + React 19 + TypeScript 5 + Tailwind CSS 4 + shadcn (base-nova preset) [VERIFIED: package.json]
- Component library: `@base-ui/react` v1.4.0 (NOT Radix UI) [VERIFIED: package.json]
- Icon library: `lucide-react` [VERIFIED: sidebar.tsx imports]
- Path aliases: `@/components`, `@/lib`, `@/hooks`, `@/components/ui` [VERIFIED: components.json]
- Named exports for all components (NOT default exports) [VERIFIED: codebase pattern]
- `"use client"` directive on files using hooks or browser APIs [VERIFIED: codebase pattern]
- CSS variables for theming, never raw color values in components [VERIFIED: globals.css]
- No Radix UI — app uses `@base-ui/react` (locked per REQUIREMENTS Out of Scope table)

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Verified |
|---------|---------|---------|----------|
| Next.js | 16.2.4 | App Router, Server/Client Components, `generateStaticParams` | [VERIFIED: package.json] |
| React | 19.2.4 | UI rendering | [VERIFIED: package.json] |
| TypeScript | ^5 | Type safety for glossary data model | [VERIFIED: package.json] |
| Tailwind CSS | ^4 | Utility styling | [VERIFIED: package.json] |
| react-markdown | 10.1.0 | Render glossary `content` markdown to React elements | [VERIFIED: npm ls] |
| @tailwindcss/typography | 0.5.19 | `prose` classes for article content styling | [VERIFIED: npm ls, globals.css `@plugin`] |
| @base-ui/react | 1.4.0 | Collapsible component for expandable entries | [VERIFIED: npm ls] |
| lucide-react | 1.8.0 | Icons: BookOpen, Search, ChevronDown, ChevronUp, Calculator, TrendingUp, Globe, X | [VERIFIED: node import test] |
| class-variance-authority | 0.7.1 | Badge variant styling | [VERIFIED: package.json] |

### To Install (1 component)

| Component | Install Command | Purpose |
|-----------|-----------------|---------|
| Input | `npx shadcn@latest add input` | Search input field on category pages |

**No new npm packages needed.** Everything is already in `package.json`.

### Alternatives Considered

| Instead of | Could Use | Why Not |
|------------|-----------|---------|
| Typed TS module | JSON file + zod parse | Locked decision D-04: TS module is single source of truth. Type safety at compile time. |
| Client-side filter | Fuse.js fuzzy search | D-07 locks to simple `.filter()`. ~25 entries don't need fuzzy matching. |
| MDX pages | per-entry MDX files | Locked out-of-scope per REQUIREMENTS. TS module with markdown strings is simpler for ~25 entries. |

## Architecture Patterns

### Recommended Project Structure

```
apps/helios/src/
├── app/
│   └── learn/
│       ├── page.tsx                    # Hub page (Server Component)
│       └── [category]/
│           └── page.tsx                # Category page (Server shell + Client wrapper)
├── components/
│   └── learn/
│       ├── glossary-entry-card.tsx     # Expandable entry card (Client Component)
│       └── glossary-search.tsx         # Search + filtered list (Client Component)
├── lib/
│   └── glossary.ts                    # Typed data module + helpers
└── components/layout/
    └── sidebar.tsx                    # Modified: add "Học" nav item
```

### Pattern 1: Server Component Shell with Client Interactive Wrapper

**What:** Category page is a Server Component that reads glossary data at build time and passes it as props to a Client Component that handles search/collapsible interactions.

**When to use:** When page data is static (glossary entries) but UI needs interactivity (search, expand/collapse).

**Example:**
```typescript
// src/app/learn/[category]/page.tsx (Server Component — no "use client")
import { notFound } from "next/navigation";
import { getEntriesByCategory, type GlossaryCategory } from "@/lib/glossary";
import { GlossarySearch } from "@/components/learn/glossary-search";

const VALID_CATEGORIES: GlossaryCategory[] = ["technical", "fundamental", "macro"];

// Static generation: build all 3 category pages at build time
export function generateStaticParams() {
  return VALID_CATEGORIES.map((category) => ({ category }));
}

export default async function LearnCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;
  
  if (!VALID_CATEGORIES.includes(category as GlossaryCategory)) {
    notFound();
  }
  
  const entries = getEntriesByCategory(category as GlossaryCategory);
  
  return (
    <div className="max-w-3xl mx-auto">
      {/* Server-rendered heading */}
      <h1 className="text-lg font-semibold">{/* category title */}</h1>
      {/* Client component handles search + collapsible */}
      <GlossarySearch entries={entries} category={category as GlossaryCategory} />
    </div>
  );
}
```
[VERIFIED: Next.js 16 `params` is a Promise — must `await` it. See existing `stock/[symbol]/page.tsx` pattern using `useParams()`]

### Pattern 2: Glossary Data Module as Typed Record

**What:** Single TypeScript file exporting all glossary entries as a `Record<string, GlossaryEntry>` with helper functions.

**When to use:** Small static datasets (<100 entries) that need type safety and O(1) lookup by ID.

**Example:**
```typescript
// src/lib/glossary.ts
export type GlossaryCategory = "technical" | "fundamental" | "macro";

export interface GlossaryEntry {
  id: string;                    // URL-safe slug: "rsi", "pe-ratio", "cpi"
  term: string;                  // Vietnamese: "Chỉ số sức mạnh tương đối (RSI)"
  termEn: string;                // English: "Relative Strength Index"
  aliases: string[];             // Phase 10 matching: ["RSI", "chỉ số RSI"]
  category: GlossaryCategory;
  shortDef: string;              // 1-sentence Vietnamese definition
  content: string;               // Full markdown article
  formula?: string;              // Optional plain text formula
}

export const glossary: Record<string, GlossaryEntry> = {
  rsi: {
    id: "rsi",
    term: "Chỉ số sức mạnh tương đối (RSI)",
    termEn: "Relative Strength Index",
    aliases: ["RSI", "chỉ số RSI", "Relative Strength Index"],
    category: "technical",
    shortDef: "Chỉ báo đo lường tốc độ và biên độ thay đổi giá...",
    content: `## Định nghĩa\n\nRSI (Relative Strength Index)...`,
    formula: "RSI = 100 - (100 / (1 + RS)), RS = Avg Gain / Avg Loss",
  },
  // ... more entries
};

export function getEntriesByCategory(category: GlossaryCategory): GlossaryEntry[] {
  return Object.values(glossary).filter((e) => e.category === category);
}

export function getAllEntries(): GlossaryEntry[] {
  return Object.values(glossary);
}

export function normalizeForSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
}
```
[VERIFIED: Type pattern consistent with existing `src/lib/types.ts`]

### Pattern 3: Collapsible Entry Card with @base-ui/react

**What:** Uses shadcn's Collapsible wrapper (which wraps `@base-ui/react` Collapsible) for expand/collapse with CSS transitions.

**When to use:** Content that should be scannable (title + short def visible) with optional detail expansion.

**Example:**
```typescript
// src/components/learn/glossary-entry-card.tsx
"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import type { GlossaryEntry } from "@/lib/glossary";

interface GlossaryEntryCardProps {
  entry: GlossaryEntry;
  defaultOpen?: boolean;
}

export function GlossaryEntryCard({ entry, defaultOpen = false }: GlossaryEntryCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card id={entry.id} className="scroll-mt-20">
        <CollapsibleTrigger className="w-full cursor-pointer text-left">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{entry.term}</CardTitle>
              {open ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            <CardDescription>{entry.shortDef}</CardDescription>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent>
            {entry.formula && (
              <div className="mb-4">
                <span className="text-xs text-muted-foreground">Công thức</span>
                <code className="block bg-muted rounded-md p-3 font-mono text-sm mt-1">
                  {entry.formula}
                </code>
              </div>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-code:text-muted-foreground">
              <ReactMarkdown>{entry.content}</ReactMarkdown>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
```
[VERIFIED: Collapsible component exists at `src/components/ui/collapsible.tsx`, wrapping `@base-ui/react` Collapsible with `Root.Props`, `Trigger.Props`, `Panel.Props`]

### Pattern 4: Vietnamese Diacritic-Insensitive Search

**What:** Normalizes both search query and entry fields by removing combining diacritical marks AND replacing Vietnamese special characters (`đ/Đ`).

**When to use:** Any text search involving Vietnamese content.

**Critical finding:** Standard `NFD` + combining mark removal does NOT handle `Đ/đ` → `d` because `Đ` (U+0110) is a distinct Unicode character, not a composed form.

**Example:**
```typescript
// WRONG — misses Đ/đ
const bad = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
// bad("Đường") → "đuong" ❌ (still has đ)

// CORRECT — handles all Vietnamese characters
export function normalizeForSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")  // Remove combining diacritical marks
    .replace(/[đĐ]/g, "d")            // Vietnamese đ/Đ → d
    .toLowerCase();
}
// normalizeForSearch("Đường Trung Bình") → "duong trung binh" ✅
// normalizeForSearch("duong trung binh") → "duong trung binh" ✅
```
[VERIFIED: Tested in Node.js — NFD alone produces "đuong" for "Đường", adding `Đ/đ` replacement produces "duong"]

### Anti-Patterns to Avoid

- **Don't use `useParams()` for Server Component category pages:** The category page should be a Server Component using `generateStaticParams` + `params` prop (which is a `Promise` in Next.js 16). `useParams()` is for Client Components only. [VERIFIED: existing `stock/[symbol]/page.tsx` uses `useParams()` because it's a client component — the learn pages should be Server Components per LEARN-03]
- **Don't fetch glossary data via API:** The data is static TypeScript — import directly. No `useQuery`, no `fetch()`. Server Components can import the module directly.
- **Don't use `dangerouslySetInnerHTML` for markdown:** Use `react-markdown` component which already handles sanitization. [VERIFIED: `react-markdown` v10.1.0 is installed]
- **Don't create separate pages per entry:** Use expandable cards on category pages for ~25 entries. Individual pages create unnecessary routing complexity for this entry count.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom parser | `react-markdown` v10 (already installed) | Handles edge cases, XSS-safe, integrates with React |
| Prose typography | Manual CSS for article text | `@tailwindcss/typography` `prose` classes (already configured) | Handles headings, paragraphs, code blocks, lists automatically |
| Expand/collapse animation | Custom height animation | `@base-ui/react` Collapsible (via shadcn wrapper) | Manages `aria-expanded`, transition status, keyboard navigation |
| Text input component | Raw `<input>` element | shadcn `Input` component (install required) | Consistent styling with theme tokens, focus ring, border |

## Common Pitfalls

### Pitfall 1: Vietnamese Đ/đ Not Handled by NFD Normalization

**What goes wrong:** Search for "duong" doesn't match "Đường" because `Đ` (U+0110) is NOT a composed character — NFD decomposition leaves it unchanged.
**Why it happens:** Most tutorials only show `normalize('NFD').replace(/[\u0300-\u036f]/g, '')` which handles accented vowels but not the distinct letter Đ.
**How to avoid:** Always include `.replace(/[đĐ]/g, "d")` AFTER the NFD normalization step.
**Warning signs:** Search works for "chi so" → "chỉ số" but fails for any term containing đ/Đ.

### Pitfall 2: Next.js 16 params is a Promise

**What goes wrong:** Accessing `params.category` directly causes a runtime error because in Next.js 16, `params` is a `Promise<{ category: string }>`, not `{ category: string }`.
**Why it happens:** Next.js 16 changed dynamic route params to async — breaking change from Next.js 14/15.
**How to avoid:** Always `await params` in async Server Components: `const { category } = await params;`
**Warning signs:** Build error or runtime "cannot read property" errors on category pages.

### Pitfall 3: Collapsible Trigger Must Be a Button

**What goes wrong:** Wrapping the entire `CardHeader` in `CollapsibleTrigger` but losing accessibility because the trigger renders a `<button>` element.
**Why it happens:** `@base-ui/react` CollapsibleTrigger renders a `<button>` — putting block-level content inside violates HTML spec.
**How to avoid:** Make `CollapsibleTrigger` wrap the header area with `className="w-full text-left cursor-pointer"`. The trigger IS the button — style it to look like the card header. Use `aria-label` for screen reader context.
**Warning signs:** Odd focus outlines, nested button warnings in console.

### Pitfall 4: prose Class Inheriting Wrong Colors

**What goes wrong:** `prose` class applies default gray colors that don't match the warm-cream theme.
**Why it happens:** `@tailwindcss/typography` has its own color palette that ignores CSS variables.
**How to avoid:** Override with `prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-code:text-muted-foreground`. Add `dark:prose-invert` for dark mode.
**Warning signs:** Article text appears in wrong shade of gray, or is invisible in dark mode.

### Pitfall 5: Large Glossary File Slowing Editor

**What goes wrong:** `glossary.ts` with 25+ detailed articles (each 500-1000 chars of markdown content) becomes a 1000+ line file that's hard to navigate.
**Why it happens:** Inline markdown strings in TypeScript are verbose.
**How to avoid:** Group entries by category with clear section comments. Use template literals for multiline content. Consider alphabetical order within each category section for findability.
**Warning signs:** File exceeds 1500 lines, hard to find specific entries.

### Pitfall 6: URL Hash Auto-Expand Not Working on Initial Load

**What goes wrong:** Navigating to `/learn/technical#rsi` from Phase 10 glossary links doesn't auto-expand the RSI entry.
**Why it happens:** Client components need to read `window.location.hash` on mount and set the correct entry's `defaultOpen` state.
**How to avoid:** Add `useEffect` on mount to check hash, find matching entry, set it open, and scroll into view. Use `scroll-mt-20` on entry cards to account for header.
**Warning signs:** Deep links work for scrolling but entry stays collapsed.

## Code Examples

### Sidebar Navigation Addition

```typescript
// src/components/layout/sidebar.tsx — add to navItems array
import { BarChart3, Globe, BookOpen } from "lucide-react";

const navItems = [
  { href: "/rankings", label: "Xếp Hạng", icon: BarChart3 },
  { href: "/market", label: "Thị Trường", icon: Globe },
  { href: "/learn", label: "Học", icon: BookOpen },
];
```
[VERIFIED: Current sidebar.tsx has exactly this navItems pattern at line 7-10]

### Hub Page Server Component

```typescript
// src/app/learn/page.tsx (Server Component)
import Link from "next/link";
import { TrendingUp, Calculator, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getEntriesByCategory } from "@/lib/glossary";

const categories = [
  { slug: "technical", title: "Chỉ Báo Kỹ Thuật", desc: "Các chỉ báo phân tích xu hướng và động lượng giá cổ phiếu", icon: TrendingUp },
  { slug: "fundamental", title: "Tỷ Số Cơ Bản", desc: "Các chỉ số đánh giá sức khỏe tài chính và định giá doanh nghiệp", icon: Calculator },
  { slug: "macro", title: "Yếu Tố Vĩ Mô", desc: "Các chỉ số kinh tế vĩ mô ảnh hưởng đến thị trường chứng khoán", icon: Globe },
] as const;

export default function LearnPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Học — Kiến Thức Đầu Tư</h1>
      <p className="text-sm text-muted-foreground mt-2">
        Tìm hiểu các chỉ báo kỹ thuật, tỷ số cơ bản và yếu tố vĩ mô được sử dụng trong phân tích AI
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
        {categories.map(({ slug, title, desc, icon: Icon }) => {
          const count = getEntriesByCategory(slug).length;
          return (
            <Link key={slug} href={`/learn/${slug}`}>
              <Card className="hover:ring-2 hover:ring-primary/20 hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader>
                  <Icon className="h-8 w-8 text-primary" />
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <Badge variant="outline">{count} mục</Badge>
                  <CardDescription>{desc}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
```
[VERIFIED: Card/Badge components confirmed at `src/components/ui/card.tsx` and `src/components/ui/badge.tsx`]

### Client-Side Search Component

```typescript
// src/components/learn/glossary-search.tsx
"use client";

import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";
import { GlossaryEntryCard } from "./glossary-entry-card";
import { normalizeForSearch, type GlossaryEntry } from "@/lib/glossary";

interface GlossarySearchProps {
  entries: GlossaryEntry[];
}

export function GlossarySearch({ entries }: GlossarySearchProps) {
  const [query, setQuery] = useState("");
  const [hashId, setHashId] = useState<string | null>(null);

  // Read URL hash on mount for deep-link auto-expand
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash) setHashId(hash);
  }, []);

  const filtered = query
    ? entries.filter((entry) => {
        const normalized = normalizeForSearch(query);
        return (
          normalizeForSearch(entry.term).includes(normalized) ||
          normalizeForSearch(entry.termEn).includes(normalized) ||
          normalizeForSearch(entry.shortDef).includes(normalized) ||
          entry.aliases.some((alias) =>
            normalizeForSearch(alias).includes(normalized)
          )
        );
      })
    : entries;

  return (
    <div>
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Escape") setQuery(""); }}
          placeholder="Tìm chỉ báo..."
          className="h-10 w-full rounded-md border border-input bg-background pl-10 pr-10 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2"
            aria-label="Xóa tìm kiếm"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Result count */}
      <p className="text-xs text-muted-foreground mt-2" aria-live="polite">
        {filtered.length} kết quả
      </p>

      {/* Entry list */}
      <div className="mt-4 space-y-4">
        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Không tìm thấy kết quả cho &quot;{query}&quot;
          </p>
        ) : (
          filtered.map((entry) => (
            <GlossaryEntryCard
              key={entry.id}
              entry={entry}
              defaultOpen={entry.id === hashId}
            />
          ))
        )}
      </div>
    </div>
  );
}
```

### Collapsible CSS Transition (for @base-ui/react)

```css
/* Add to globals.css — enables smooth height animation for Collapsible */
[data-slot="collapsible-content"] {
  overflow: hidden;
  transition: height 200ms ease-out;
}

[data-slot="collapsible-content"][data-closed] {
  height: 0;
}
```
[VERIFIED: `@base-ui/react` Collapsible Panel uses `data-open`/`data-closed` attributes and `data-starting-style`/`data-ending-style` for transition states. The shadcn wrapper adds `data-slot="collapsible-content"` on Panel.]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `params: { category: string }` | `params: Promise<{ category: string }>` | Next.js 15→16 | Must `await params` in Server Components |
| `react-markdown` v8 with `remark-*` plugins | `react-markdown` v10 with `Markdown` / `MarkdownAsync` | v9→v10 | Simpler API, sync by default, async for plugins |
| Radix Collapsible | `@base-ui/react` Collapsible | shadcn base-nova | Uses `Collapsible.Root`/`.Trigger`/`.Panel` instead of Radix primitives |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `react-markdown` v10 synchronous `Markdown` component works in Server Components | Architecture Patterns | LOW — may need `MarkdownAsync` or move to client component |
| A2 | `prose prose-sm` Tailwind typography classes are sufficient for article readability | Architecture Patterns | LOW — may need additional prose overrides for specific elements |
| A3 | 25 entries × ~800 chars content each ≈ 20KB — acceptable for single TS module import | Architecture Patterns | LOW — even at 50KB, tree-shaking and SSR handle this fine |

## Open Questions

1. **react-markdown in Server Components**
   - What we know: `react-markdown` v10 exports `Markdown` (sync) and `MarkdownAsync` (async). Sync should work in Server Components since it returns `ReactElement`.
   - What's unclear: Whether the sync `Markdown` component has any client-side dependencies that prevent Server Component usage.
   - Recommendation: Use `Markdown` in client component (`GlossaryEntryCard` is already `"use client"` because of Collapsible state). No issue since the entry card is client-side anyway.

2. **Collapsible CSS animation in Tailwind v4**
   - What we know: `@base-ui/react` Collapsible uses `data-open`/`data-closed` attributes. Tailwind v4 supports `data-*` attribute selectors.
   - What's unclear: Whether the CSS height transition requires explicit CSS rules or if `@base-ui/react` handles it automatically.
   - Recommendation: Add explicit CSS transition rules in `globals.css` targeting `[data-slot="collapsible-content"]` for controlled height animation.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None installed — no test runner in helios app |
| Config file | None |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEARN-01 | 3 category pages render | smoke | Manual: visit `/learn`, `/learn/technical`, `/learn/fundamental`, `/learn/macro` | ❌ |
| LEARN-02 | Glossary module exports ≥15 entries | unit | `npx tsx --eval "..."` inline check | ❌ |
| LEARN-03 | Category routing works, invalid slug → 404 | smoke | Manual: visit `/learn/invalid` → 404 | ❌ |
| LEARN-04 | Diacritic search matches correctly | unit | `npx tsx --eval "..."` inline check | ❌ |

### Sampling Rate
- **Per task commit:** `npm run build` (catches TypeScript errors and broken imports)
- **Per wave merge:** `npm run build` + manual smoke test of all learn pages
- **Phase gate:** Build green + all 4 learn URLs render correctly + search works

### Wave 0 Gaps
- [ ] No test framework installed — validation relies on TypeScript compilation (`npm run build`) and manual smoke testing
- [ ] For LEARN-02 and LEARN-04, inline TypeScript checks via `npx tsx` can validate data integrity and search normalization without a test framework

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no auth in personal tool |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — public read-only content |
| V5 Input Validation | Yes | Search input is text-only, used for client-side `.filter()` — no server-side execution. `react-markdown` handles sanitization of content strings. |
| V6 Cryptography | No | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via markdown content | Tampering | `react-markdown` sanitizes HTML by default — no `dangerouslySetInnerHTML`. Content is author-controlled (hardcoded in TS module). |
| Search input injection | Tampering | Input is only used for client-side string comparison — never sent to server, never inserted into DOM as HTML. |

**Risk assessment: MINIMAL** — This phase is read-only static content with no user-generated data, no API calls, and no server-side processing of user input.

## Sources

### Primary (HIGH confidence)
- `apps/helios/package.json` — verified all dependency versions [LOCAL]
- `apps/helios/src/components/ui/collapsible.tsx` — confirmed `@base-ui/react` Collapsible API [LOCAL]
- `apps/helios/src/components/layout/sidebar.tsx` — confirmed navItems pattern [LOCAL]
- `apps/helios/src/lib/types.ts` — confirmed TypeScript interface pattern [LOCAL]
- `apps/helios/src/app/globals.css` — confirmed theme CSS variables and `@plugin "@tailwindcss/typography"` [LOCAL]
- `@base-ui/react` v1.4.0 type definitions — confirmed Collapsible Root/Trigger/Panel props, `data-open`/`data-closed`/`data-starting-style`/`data-ending-style` attributes [LOCAL: node_modules]
- Node.js runtime test — confirmed Vietnamese diacritic normalization behavior, including `Đ/đ` edge case [VERIFIED: bash execution]

### Secondary (MEDIUM confidence)
- `react-markdown` v10 type definitions — confirmed `Markdown` sync + `MarkdownAsync` async exports [LOCAL: node_modules]

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in local `package.json` and `node_modules`
- Architecture: HIGH — patterns derived from existing codebase (sidebar, routing, components)
- Pitfalls: HIGH — diacritic normalization bug verified empirically, Next.js 16 params change documented
- Data model: HIGH — type structure verified against existing `types.ts` patterns and UI-SPEC contract

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — no moving parts, all static content)
