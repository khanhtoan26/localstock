---
phase: 09-academic-learning-page-glossary-data
plan: "02"
subsystem: frontend/learn-pages
tags: [learn, glossary, ui, routing, search, accessibility]
dependency_graph:
  requires: [09-01]
  provides: [learn-hub-page, learn-category-pages, glossary-search, glossary-entry-card]
  affects: [10-glossary-linking]
tech_stack:
  added: []
  patterns: [server-component-shell-client-wrapper, generateStaticParams-SSG, collapsible-animation, diacritic-insensitive-search]
key_files:
  created:
    - apps/helios/src/components/learn/glossary-entry-card.tsx
    - apps/helios/src/components/learn/glossary-search.tsx
    - apps/helios/src/app/learn/page.tsx
    - apps/helios/src/app/learn/[category]/page.tsx
  modified:
    - apps/helios/src/app/globals.css
decisions:
  - Server Components for pages, Client Components for interactivity (search + expand)
  - generateStaticParams for SSG of 3 category pages at build time
  - Collapsible CSS animation via data-slot attribute selector (200ms ease-out)
metrics:
  duration: 2m 52s
  completed: 2026-04-21T02:28:19Z
  tasks: 3/3
  files_created: 4
  files_modified: 1
---

# Phase 09 Plan 02: Learn Pages & Interactive Components Summary

Interactive learn hub + category pages with search and expandable glossary entries consuming Plan 01's data module — Server Component shell with client-side GlossarySearch and collapsible entry cards using diacritic-insensitive matching

## What Was Done

### Task 1: GlossaryEntryCard and GlossarySearch client components (527a09b)

Created two client components in `apps/helios/src/components/learn/`:

**GlossaryEntryCard** — Expandable card wrapping `@base-ui/react` Collapsible with:
- Card showing Vietnamese term + shortDef in collapsed state
- ChevronDown/Up toggle icon with aria-label in Vietnamese
- Expanded state renders formula block (monospace) + full markdown article via `react-markdown`
- `scroll-mt-20` on Card for future deep-link scrolling (Phase 10)
- Prose typography classes for markdown content: `prose prose-sm dark:prose-invert max-w-none`

**GlossarySearch** — Search input + filtered entry list with:
- Category-specific Vietnamese placeholders ("Tìm chỉ báo kỹ thuật...", "Tìm tỷ số cơ bản...", "Tìm yếu tố vĩ mô...")
- Diacritic-insensitive filtering via `normalizeForSearch` on term, termEn, shortDef, aliases
- `aria-live="polite"` on result count for screen readers
- Clear button with `aria-label="Xóa tìm kiếm"` and Escape key support
- URL hash auto-expand for Phase 10 deep links
- Empty state message: "Không tìm thấy kết quả cho..."

### Task 2: Learn hub page, category routing, and collapsible CSS (1842557)

**Learn hub page** (`/learn`) — Server Component with:
- Title: "Học — Kiến Thức Đầu Tư"
- 3 category cards (Technical, Fundamental, Macro) with icons, Vietnamese/English titles, entry count badges
- Responsive grid: 1-col mobile → 2-col sm → 3-col lg
- Hover effects and focus-visible ring for keyboard navigation

**Category page** (`/learn/[category]`) — Server Component with:
- `generateStaticParams` producing 3 pages at build time (SSG)
- `await params` for Next.js 16 async params
- `notFound()` for invalid category slugs
- Delegates to `GlossarySearch` client component for interactivity

**Collapsible CSS** — Added to globals.css:
- `[data-slot="collapsible-content"]` with `transition: height 200ms ease-out`
- `[data-slot="collapsible-content"][data-closed]` with `height: 0`

### Task 3: Visual verification checkpoint

**Automated checks — all PASS:**
- ✅ `npm run build` passes clean (10/10 static pages generated)
- ✅ Routes visible: `/learn` (static), `/learn/[category]` (SSG with 3 variants)
- ✅ Sidebar has "Học" link with BookOpen icon
- ✅ Hub page has 3 category cards
- ✅ Entry counts: technical=10, fundamental=10, macro=5
- ✅ All grep verification checks pass (exports, aria attributes, Vietnamese strings)

**Visual verification checklist (requires human):**
- [ ] Open http://localhost:3000 — verify sidebar shows "Học" with BookOpen icon
- [ ] Click "Học" — verify `/learn` hub page shows title, 3 category cards with icons + counts
- [ ] Resize browser — verify responsive grid (1-col mobile, 3-col desktop)
- [ ] Click "Chỉ Báo Kỹ Thuật" card — verify `/learn/technical` renders
- [ ] Verify search input has placeholder "Tìm chỉ báo kỹ thuật..."
- [ ] Click any entry card — verify smooth expand animation with formula + markdown
- [ ] Click again to collapse — verify smooth collapse animation
- [ ] Type "chi so" in search — verify diacritic-insensitive match finds "chỉ số" entries
- [ ] Type "RSI" — verify RSI entry appears
- [ ] Clear with × button and Escape key — both work
- [ ] Visit `/learn/invalid` — verify 404
- [ ] Visit `/learn/fundamental` and `/learn/macro` — entries render correctly
- [ ] Toggle dark mode — verify all learn pages look correct

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Server Component shell + Client wrapper pattern** — Hub and category pages are Server Components; GlossarySearch is the client boundary for search state + collapsible interaction
2. **SSG via generateStaticParams** — All 3 category pages pre-rendered at build time for instant navigation
3. **CSS-based collapsible animation** — Using `data-slot` attribute selectors to target `@base-ui/react` Collapsible panel, 200ms ease-out transition

## Self-Check: PASSED
