# Architecture: v1.1 UX Polish & Educational Depth

**Domain:** Integration architecture for 4 new features into existing LocalStock frontend
**Researched:** 2026-04-17
**Confidence:** HIGH — all features use well-established patterns within the existing stack

## Executive Summary

v1.1 adds four frontend-centric features to an existing Next.js 16 + shadcn/ui + Tailwind v4 app. The critical insight is that **these features are almost entirely frontend work** — no new backend API endpoints are needed for theme, stock page redesign, or academic content. Only the glossary linking _could_ benefit from backend support (term extraction from AI reports), but a static glossary dictionary is the pragmatic first approach.

The existing architecture is well-suited for all four features. shadcn/ui's CSS variable system already supports theming. The stock page redesign is a layout restructure (not a data change). The academic page is static content with a new route. The glossary is a client-side text-processing layer over existing AI report strings.

**No backend changes required for v1.1.**

---

## Current Architecture Snapshot

### File Structure (Relevant to v1.1)
```
apps/helios/src/
├── app/
│   ├── globals.css          ← Theme CSS variables live here
│   ├── layout.tsx           ← Root layout, hardcodes className="dark"
│   ├── page.tsx             ← Redirects to /rankings
│   ├── rankings/page.tsx
│   ├── market/page.tsx
│   └── stock/[symbol]/page.tsx  ← Major redesign target
├── components/
│   ├── layout/
│   │   ├── app-shell.tsx    ← Shell with sidebar + main area
│   │   └── sidebar.tsx      ← Navigation (2 items: Xếp Hạng, Thị Trường)
│   ├── charts/
│   │   ├── price-chart.tsx  ← lightweight-charts candlestick
│   │   ├── sub-panel.tsx    ← MACD/RSI sub-charts
│   │   └── timeframe-selector.tsx
│   ├── rankings/
│   │   ├── stock-table.tsx
│   │   └── grade-badge.tsx  ← Uses hardcoded dark-theme Tailwind colors
│   ├── market/
│   │   ├── macro-cards.tsx
│   │   └── sector-table.tsx
│   └── ui/                  ← shadcn/ui components (9 total)
│       ├── badge.tsx, button.tsx, card.tsx
│       ├── empty-state.tsx, error-state.tsx
│       ├── scroll-area.tsx, separator.tsx
│       ├── skeleton.tsx, table.tsx
└── lib/
    ├── api.ts               ← API client (single fetch wrapper)
    ├── chart-colors.ts      ← Hardcoded dark-theme chart colors
    ├── queries.ts           ← TanStack Query hooks (9 hooks)
    ├── query-provider.tsx   ← QueryClient provider
    ├── types.ts             ← API response types
    └── utils.ts             ← cn(), formatScore(), gradeColors (hardcoded)
```

### Key Architectural Facts

1. **Theme is hardcoded dark**: `layout.tsx` has `<html lang="vi" className="dark">` — no theme switching infrastructure exists.
2. **CSS variables use two color spaces**: Light `:root` uses `oklch()`, dark `.dark` uses `hsl()`. This inconsistency should be normalized.
3. **`@custom-variant dark (&:is(.dark *))` in globals.css**: This is Tailwind v4's way to define the dark variant — it checks for `.dark` class on an ancestor.
4. **Chart colors are hardcoded constants**: `chart-colors.ts` exports a single `CHART_COLORS` object with hex values. No theme awareness.
5. **Grade badge colors are hardcoded**: `gradeColors` in `utils.ts` uses hardcoded dark-theme Tailwind classes like `bg-green-500/20 text-green-400`.
6. **Financial semantic tokens**: `--stock-up`, `--stock-down`, `--chart-bg`, `--chart-grid`, `--chart-text` exist as CSS custom properties in `:root` but are dark-theme-only values.
7. **Stock page is vertical scroll**: Charts on top → timeframe → MACD/RSI → AI report card → score breakdown. AI report is buried at the bottom.
8. **AI report renders as plain text**: `whitespace-pre-wrap` on `reportQuery.data.summary` — no structured parsing, no clickable terms.
9. **No `Sheet`/`Drawer` component exists**: Would need to install from shadcn/ui for the right-drawer pattern.
10. **shadcn/ui style is `base-nova`**: Uses `@base-ui/react` primitives (not Radix UI). This is the newer shadcn v4 style.

---

## Feature 1: Theme System (Warm-Light Default + Dark Toggle)

### Architecture Pattern: CSS Variable Swapping via Class Toggle

**How it works**: shadcn/ui themes are already CSS-variable-driven. Currently the app has `:root` (light, unused) and `.dark` class overrides. The approach is:

1. Define a **warm-light theme** as the new `:root` defaults (cream backgrounds, orange accents)
2. Keep `.dark` class overrides (existing, with minor tweaks)
3. Toggle by adding/removing `.dark` class on `<html>` (exactly how shadcn/ui intends)
4. Persist preference in `localStorage`
5. Prevent flash of wrong theme (FOWT) with a `<script>` in `<head>` that reads localStorage before React hydrates

### Components to Create

| Component | Path | Purpose |
|-----------|------|---------|
| `ThemeProvider` | `src/components/theme/theme-provider.tsx` | React Context providing `theme` state + `toggleTheme()`. Client component. |
| `ThemeToggle` | `src/components/theme/theme-toggle.tsx` | Sun/Moon icon button in sidebar. Client component. |
| `ThemeScript` | `src/components/theme/theme-script.tsx` | Inline `<script>` to prevent FOWT. Server component that renders a raw script tag. |

### Components to Modify

| Component | File | What Changes |
|-----------|------|-------------|
| `RootLayout` | `src/app/layout.tsx` | Remove hardcoded `className="dark"`. Wrap with `ThemeProvider`. Add `ThemeScript` in `<head>`. Remove `suppressHydrationWarning` is needed on `<html>` since theme script modifies the DOM before hydration. |
| `Sidebar` | `src/components/layout/sidebar.tsx` | Add `ThemeToggle` button at bottom of sidebar. |
| `GradeBadge` | `src/components/rankings/grade-badge.tsx` | Replace hardcoded color classes with CSS variable-based or theme-aware classes. |
| `globals.css` | `src/app/globals.css` | Replace `:root` light theme with warm-light (cream/orange). Update `.dark` to use consistent oklch. Add warm-light financial semantic tokens. |
| `chart-colors.ts` | `src/lib/chart-colors.ts` | Make theme-aware: export a function `getChartColors(isDark: boolean)` or use CSS variables via `getComputedStyle()`. |
| `utils.ts` | `src/lib/utils.ts` | Update `gradeColors` to use semantic CSS variable-based classes instead of hardcoded dark-theme colors. |

### Data Flow: Theme State

```
localStorage("localstock-theme")
        ↓ (read on page load)
ThemeScript (inline <script>)
        ↓ (sets className on <html> before paint)
ThemeProvider (React Context)
        ↓ (provides theme + toggleTheme to component tree)
ThemeToggle ←→ ThemeProvider (toggle action → updates className + localStorage)
        ↓
CSS Variables automatically cascade
        ↓
All components re-render with new colors (no prop drilling)
```

### Warm-Light Theme Color Palette (Claude-inspired)

```css
:root {
  /* Warm cream background */
  --background: oklch(0.97 0.01 85);        /* warm cream, not pure white */
  --foreground: oklch(0.25 0.02 50);         /* warm dark brown, not black */
  
  /* Cards slightly warmer than bg */
  --card: oklch(0.98 0.008 85);
  --card-foreground: oklch(0.25 0.02 50);
  
  /* Orange accent (Claude-style) */
  --primary: oklch(0.65 0.18 50);            /* warm orange */
  --primary-foreground: oklch(0.98 0.005 85);
  
  /* Warm muted tones */
  --muted: oklch(0.93 0.01 85);
  --muted-foreground: oklch(0.50 0.02 50);
  
  /* Financial semantic tokens for light theme */
  --stock-up: oklch(0.55 0.2 145);           /* green, slightly muted for light bg */
  --stock-down: oklch(0.55 0.2 25);          /* red, slightly muted for light bg */
  --chart-bg: oklch(0.97 0.01 85);           /* matches background */
  --chart-grid: oklch(0.90 0.01 85);         /* subtle warm grid */
  --chart-text: oklch(0.45 0.02 50);         /* readable on cream */
}
```

### Critical Integration Points

1. **lightweight-charts requires imperative color updates**: Charts use `createChart()` with color options, not CSS. When theme toggles, charts must either: (a) re-create with new colors (simple — `useEffect` already destroys/recreates on data change), or (b) call `chart.applyOptions()` to update. Option (a) is simpler since charts already re-render when data changes — just add `theme` to the dependency array.

2. **`@custom-variant dark (&:is(.dark *))` already works**: Tailwind v4's dark variant targets `.dark` ancestor. No changes needed to the variant definition.

3. **Hydration mismatch risk**: Server renders without theme class → client adds it → React complains. The `ThemeScript` inline `<script>` in `<head>` solves this by setting the class before React hydrates. Must use `suppressHydrationWarning` on `<html>`.

4. **Grade badge colors need semantic approach**: Current `bg-green-500/20 text-green-400` is dark-theme-only. Replace with CSS custom properties: `--grade-a-bg`, `--grade-a-text`, etc., defined per theme. Or use `text-green-600 dark:text-green-400` dual-mode classes.

### Suggested Implementation

```tsx
// src/components/theme/theme-provider.tsx
"use client";
import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "localstock-theme";

const ThemeContext = createContext<{
  theme: Theme;
  toggleTheme: () => void;
}>({ theme: "light", toggleTheme: () => {} });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    // Read from DOM (set by ThemeScript before hydration)
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem(STORAGE_KEY, next);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
```

```tsx
// src/components/theme/theme-script.tsx
// Server component — renders inline script to prevent FOWT
export function ThemeScript() {
  const script = `
    (function() {
      var t = localStorage.getItem('localstock-theme');
      if (t === 'dark') document.documentElement.classList.add('dark');
    })();
  `;
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
```

---

## Feature 2: Stock Page Redesign (AI Report Center + Right Drawer)

### Architecture Pattern: Report-Centric Layout with Slide-Over Drawer

**Current layout** (vertical scroll, top-to-bottom):
```
┌─────────────────────────────────┐
│ Header (← Back, Symbol, Grade)  │
├─────────────────────────────────┤
│ Price Chart (400px)             │
├─────────────────────────────────┤
│ Timeframe Selector              │
├─────────────────────────────────┤
│ MACD Sub-panel                  │
├─────────────────────────────────┤
│ RSI Sub-panel                   │
├─────────────────────────────────┤
│ AI Report Card (max-h 400px)    │  ← buried at bottom
├─────────────────────────────────┤
│ Score Breakdown Card            │
└─────────────────────────────────┘
```

**New layout** (AI report centered, data in drawer):
```
┌─────────────────────────────────────────────┐
│ Header (← Back, Symbol, Grade) [📊 Data]    │  ← Data button opens drawer
├─────────────────────────────────────────────┤
│                                             │
│  AI Report (full-width, unlimited scroll)   │  ← The main content
│  - Structured sections                      │
│  - Glossary-linked terms (Feature 4)        │
│                                             │
├─────────────────────────────────────────────┤
│ Score Breakdown (compact, always visible)    │
└─────────────────────────────────────────────┘

           Right Drawer (opened by [📊 Data] button)
           ┌──────────────────────┐
           │ Tabs: Chart │ Data   │
           ├──────────────────────┤
           │ Price Chart          │
           │ Timeframe Selector   │
           │ MACD / RSI           │
           │ ─── or ───           │
           │ Technical Data Table │
           │ Fundamental Data     │
           └──────────────────────┘
```

### Components to Create

| Component | Path | Purpose |
|-----------|------|---------|
| `Sheet` (shadcn/ui) | `src/components/ui/sheet.tsx` | Install from shadcn/ui. Right-side slide-over panel. |
| `Tabs` (shadcn/ui) | `src/components/ui/tabs.tsx` | Install from shadcn/ui. Tab switching within drawer. |
| `StockDataDrawer` | `src/components/stock/data-drawer.tsx` | Composition component: Sheet + Tabs containing charts and data tables. |
| `AIReportView` | `src/components/stock/ai-report-view.tsx` | Structured rendering of AI report with glossary term highlighting (Feature 4 hook). |
| `ScoreBreakdown` | `src/components/stock/score-breakdown.tsx` | Extracted from current stock page — compact score grid. |
| `TechnicalDataTable` | `src/components/stock/technical-data-table.tsx` | Table view of latest technical indicators (new — currently only chart view). |
| `FundamentalDataTable` | `src/components/stock/fundamental-data-table.tsx` | Table view of fundamental ratios (new — uses existing `useStockFundamental` hook). |

### Components to Modify

| Component | File | What Changes |
|-----------|------|-------------|
| Stock page | `src/app/stock/[symbol]/page.tsx` | **Major restructure**: Move charts into `StockDataDrawer`. Move AI report to center. Extract score breakdown to `ScoreBreakdown`. Add drawer toggle button. |
| AppShell | `src/components/layout/app-shell.tsx` | No changes needed — main content area accommodates the new layout. |

### Data Flow: No New API Calls

The redesign uses the **exact same 4 TanStack Query hooks** that exist today:
- `useStockPrices(symbol, days)` → moves into drawer's Chart tab
- `useStockIndicators(symbol, days)` → moves into drawer's Chart tab
- `useStockScore(symbol)` → stays in main area (ScoreBreakdown)
- `useStockReport(symbol)` → elevated to main area (AIReportView)

Plus two existing hooks currently unused on the stock page:
- `useStockTechnical(symbol)` → drawer's Data tab
- `useStockFundamental(symbol)` → drawer's Data tab

### Critical Integration Points

1. **Drawer width**: The drawer should be ~480-600px wide to give charts enough room. On screens <1024px, it should be full-width overlay.

2. **Chart re-initialization**: Moving charts into a Sheet means they mount/unmount with drawer open/close. The existing `useEffect` cleanup in `PriceChart` already handles this correctly (`chart.remove()` in cleanup). No issue.

3. **Timeframe state**: Currently `days` state lives in the stock page. After redesign, it should live in `StockDataDrawer` since the timeframe selector is drawer-internal.

4. **Report rendering upgrade**: The current `whitespace-pre-wrap` plain text rendering should be upgraded to parse the `summary` string into structured sections (headers, bullet points) for better readability. This is also the hook point for glossary linking (Feature 4).

5. **Sheet from shadcn/ui v4 (base-nova)**: Need to install via `npx shadcn@latest add sheet`. This pulls in `@base-ui/react` Dialog primitive (already in deps as `@base-ui/react`).

### shadcn/ui Components to Install

```bash
cd apps/helios
npx shadcn@latest add sheet
npx shadcn@latest add tabs
npx shadcn@latest add tooltip   # needed for Feature 4 glossary
npx shadcn@latest add popover   # alternative for glossary definitions
```

---

## Feature 3: Academic/Learning Page

### Architecture Pattern: Static Content Page with Category Navigation

This is a **new route** with educational content. No backend API needed — content is static (or MDX if desired, but plain TSX is simpler for v1.1).

### Route Structure

```
src/app/learn/
├── page.tsx                    ← Landing: category cards linking to sub-pages
├── layout.tsx                  ← Optional: sidebar or breadcrumb navigation for learn section
├── technical/
│   └── page.tsx                ← Technical indicators explained (RSI, MACD, SMA, BB, etc.)
├── fundamental/
│   └── page.tsx                ← Financial ratios explained (P/E, ROE, EPS, etc.)
└── macro/
    └── page.tsx                ← Macro concepts explained (CPI, interest rates, GDP, etc.)
```

### Components to Create

| Component | Path | Purpose |
|-----------|------|---------|
| `ConceptCard` | `src/components/learn/concept-card.tsx` | Card with term name, short description, formula (if applicable), interpretation guide. Reusable for all concept types. |
| `CategoryNav` | `src/components/learn/category-nav.tsx` | Horizontal tab navigation or card grid for the 3 categories. |
| `FormulaBlock` | `src/components/learn/formula-block.tsx` | Styled block for displaying mathematical formulas (e.g., RSI formula). Uses monospace + custom styling, no need for LaTeX/KaTeX. |
| `InterpretationGuide` | `src/components/learn/interpretation-guide.tsx` | Visual guide showing ranges (e.g., RSI: 0-30 oversold, 30-70 neutral, 70-100 overbought) with color-coded bars. |

### Components to Modify

| Component | File | What Changes |
|-----------|------|-------------|
| `Sidebar` | `src/components/layout/sidebar.tsx` | Add "Học Thuật" nav item with `BookOpen` icon from lucide-react. |

### Content Architecture

The educational content should be defined as **typed data arrays** (not hardcoded JSX) so the glossary system (Feature 4) can reference the same data:

```typescript
// src/lib/glossary-data.ts — SINGLE SOURCE OF TRUTH for both Learn pages and glossary linking

export interface GlossaryTerm {
  id: string;                    // URL-safe slug: "rsi-14", "pe-ratio"
  name: string;                  // Display: "RSI (14)"
  nameVi: string;                // Vietnamese: "Chỉ số sức mạnh tương đối"
  category: "technical" | "fundamental" | "macro";
  shortDescription: string;      // 1-2 sentences
  fullDescription: string;       // Detailed explanation (Vietnamese)
  formula?: string;              // e.g., "RSI = 100 - (100 / (1 + RS))"
  interpretation?: {             // Ranges for visual guide
    ranges: { min: number; max: number; label: string; sentiment: "positive" | "neutral" | "negative" }[];
  };
  relatedTerms?: string[];       // IDs of related terms
  keywords: string[];            // Strings to match in AI reports for glossary linking
}

export const GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    id: "rsi-14",
    name: "RSI (14)",
    nameVi: "Chỉ số sức mạnh tương đối",
    category: "technical",
    shortDescription: "Đo lường tốc độ và mức thay đổi của giá trong 14 phiên gần nhất.",
    fullDescription: "RSI (Relative Strength Index) là chỉ báo động lượng...",
    formula: "RSI = 100 - (100 / (1 + RS)), RS = Avg Gain / Avg Loss",
    interpretation: {
      ranges: [
        { min: 0, max: 30, label: "Quá bán", sentiment: "positive" },
        { min: 30, max: 70, label: "Trung tính", sentiment: "neutral" },
        { min: 70, max: 100, label: "Quá mua", sentiment: "negative" },
      ],
    },
    keywords: ["RSI", "rsi", "quá mua", "quá bán", "overbought", "oversold"],
  },
  // ... more terms
];
```

### Data Flow

```
GLOSSARY_TERMS (static data)
    ↓ (import)
Learn pages ← render ConceptCard for each term in category
    ↓ (same import)
AIReportView ← scan report text for keywords → create links to /learn/technical#rsi-14
```

### Critical Integration Points

1. **No MDX needed**: The educational content is structured data, not freeform prose. TypeScript arrays are easier to maintain and type-safe. Each `ConceptCard` renders from the data. If content grows large later, MDX can be added — but for ~30-40 financial terms, typed arrays are simpler.

2. **Anchor-based navigation**: Each term on its category page gets an `id` attribute matching the term's `id` field. Glossary links from AI reports navigate to `/learn/technical#rsi-14` for direct scroll-to-term.

3. **SEO/SSR**: Learn pages are static content → can be Server Components (no `"use client"`). This makes them fast and SEO-friendly.

4. **Sidebar nav expansion**: Currently 2 items (Xếp Hạng, Thị Trường). Adding "Học Thuật" is trivial — add to the `navItems` array in `sidebar.tsx`.

---

## Feature 4: Interactive Glossary Linking

### Architecture Pattern: Client-Side Text Processing + Popover/Navigate

The AI report text (currently plain string from `reportQuery.data.summary`) needs to be scanned for glossary terms and those terms converted to interactive elements (links or popover triggers).

### Processing Pipeline

```
Raw report text (string)
    ↓
glossaryLinkify(text, GLOSSARY_TERMS)   ← pure function
    ↓
Array of React nodes: [string, <GlossaryLink>, string, <GlossaryLink>, ...]
    ↓
Render in AIReportView
```

### Components to Create

| Component | Path | Purpose |
|-----------|------|---------|
| `GlossaryLink` | `src/components/glossary/glossary-link.tsx` | Inline styled span/link that: (1) shows a Popover with short description on hover/click, (2) has a "Tìm hiểu thêm" link to the full Learn page. |
| `GlossaryPopover` | `src/components/glossary/glossary-popover.tsx` | Popover content: term name (Vi), short description, link to full definition. Uses shadcn/ui Popover. |
| `glossary-linkify.ts` | `src/lib/glossary-linkify.ts` | Pure function: takes a string + GlossaryTerm[] → returns ReactNode[]. Scans text for keyword matches and wraps them in `<GlossaryLink>`. |

### Components to Modify

| Component | File | What Changes |
|-----------|------|-------------|
| `AIReportView` | `src/components/stock/ai-report-view.tsx` | (New component from Feature 2) Uses `glossaryLinkify()` to render report text with interactive terms instead of plain `whitespace-pre-wrap`. |

### Text Processing Strategy

```typescript
// src/lib/glossary-linkify.ts
import { GLOSSARY_TERMS, type GlossaryTerm } from "./glossary-data";

/**
 * Build a sorted keyword → term lookup (longest keywords first to avoid
 * partial matches like "SMA" matching before "SMA 20").
 */
function buildKeywordMap(): Map<string, GlossaryTerm> {
  const map = new Map<string, GlossaryTerm>();
  for (const term of GLOSSARY_TERMS) {
    for (const kw of term.keywords) {
      map.set(kw, term);
    }
  }
  return map;
}

/**
 * Scan text and split into segments: plain strings and matched terms.
 * Returns array of { type: "text", value } | { type: "term", term, matched }.
 * 
 * Uses a compiled regex from all keywords (sorted longest-first).
 * Each keyword is matched only once (first occurrence) to avoid over-linking.
 */
export function glossaryLinkify(text: string): GlossarySegment[] {
  // Implementation: build regex, scan, split, dedup
}
```

### Critical Integration Points

1. **Performance**: AI report text is typically 500-2000 characters. Scanning against ~50-100 keywords is negligible. No memoization needed beyond standard React re-render avoidance.

2. **First-occurrence-only linking**: Link only the first occurrence of each term in a report to avoid visual clutter. If "RSI" appears 5 times, only the first becomes a link.

3. **Vietnamese text matching**: Keywords include both English terms ("RSI", "P/E") and Vietnamese equivalents ("quá mua", "đường trung bình"). The `keywords` array in each `GlossaryTerm` handles this — no NLP needed, just string matching.

4. **Popover vs Navigate**: Use a **Popover** (hover/click → short description) rather than navigating away. The popover includes a "Xem chi tiết →" link to `/learn/technical#rsi-14` for users who want the full explanation. This keeps the user on the stock page.

5. **No backend needed**: The glossary data is static TypeScript. The text scanning is client-side. This avoids adding complexity to the Python backend for what is fundamentally a UI enhancement.

---

## Cross-Feature Dependencies

```
Feature 1: Theme System ─────────────────────────┐
    (must be done first — all other features      │
     render differently per theme)                 │
                                                   ↓
Feature 2: Stock Page Redesign ──────────→ Feature 4: Glossary Linking
    (creates AIReportView component)         (hooks into AIReportView)
                                                   ↑
Feature 3: Academic/Learning Page ───────→ Feature 4: Glossary Linking
    (defines glossary-data.ts)               (imports glossary-data.ts)
```

### Dependency Chain

1. **Theme System** → independent, no deps. Must be first because it changes `globals.css`, `layout.tsx`, and color handling — which every subsequent feature touches.

2. **Academic Page** → depends on Theme (to look correct in both themes). Produces `glossary-data.ts` which Feature 4 consumes.

3. **Stock Page Redesign** → depends on Theme (drawer theming, chart colors). Produces `AIReportView` component which Feature 4 hooks into.

4. **Glossary Linking** → depends on both Feature 2 (AIReportView exists) and Feature 3 (glossary-data.ts exists). Must be last.

---

## Suggested Build Order

### Phase 1: Theme System
**Files touched:** `globals.css`, `layout.tsx`, `chart-colors.ts`, `utils.ts`, `grade-badge.tsx`, new `theme-provider.tsx`, `theme-toggle.tsx`, `theme-script.tsx`, `sidebar.tsx`
**Risk:** LOW — CSS variable theming is a well-understood pattern with shadcn/ui
**New components:** 3
**Modified components:** 6

### Phase 2: Academic/Learning Page + Glossary Data
**Files touched:** New `src/app/learn/` route tree, new `src/components/learn/` directory, new `src/lib/glossary-data.ts`, `sidebar.tsx`
**Risk:** LOW — static content pages, no API integration
**New components:** 5 + route pages
**Modified components:** 1 (sidebar)

### Phase 3: Stock Page Redesign
**Files touched:** `stock/[symbol]/page.tsx` (major rewrite), new `src/components/stock/` directory, install Sheet + Tabs from shadcn/ui
**Risk:** MEDIUM — chart re-initialization in drawer, responsive drawer width, UX testing needed
**New components:** 5
**Modified components:** 1 (stock page — major)
**New shadcn/ui installs:** Sheet, Tabs

### Phase 4: Glossary Linking
**Files touched:** New `src/lib/glossary-linkify.ts`, new `src/components/glossary/` directory, modify `AIReportView` from Phase 3
**Risk:** LOW — text processing is straightforward, but Vietnamese keyword matching needs testing
**New components:** 2
**Modified components:** 1 (AIReportView)
**New shadcn/ui installs:** Popover (or Tooltip)

---

## Component Inventory Summary

### New Components (15 total)

| # | Component | Feature | Type |
|---|-----------|---------|------|
| 1 | `ThemeProvider` | Theme | Client Context |
| 2 | `ThemeToggle` | Theme | Client UI |
| 3 | `ThemeScript` | Theme | Server Script |
| 4 | `ConceptCard` | Learn | Server Component |
| 5 | `CategoryNav` | Learn | Server/Client |
| 6 | `FormulaBlock` | Learn | Server Component |
| 7 | `InterpretationGuide` | Learn | Client Component |
| 8 | `StockDataDrawer` | Stock Redesign | Client Component |
| 9 | `AIReportView` | Stock Redesign | Client Component |
| 10 | `ScoreBreakdown` | Stock Redesign | Client Component |
| 11 | `TechnicalDataTable` | Stock Redesign | Client Component |
| 12 | `FundamentalDataTable` | Stock Redesign | Client Component |
| 13 | `GlossaryLink` | Glossary | Client Component |
| 14 | `GlossaryPopover` | Glossary | Client Component |
| 15 | `glossary-linkify.ts` | Glossary | Pure Function |

### Modified Components (8 total, some modified in multiple phases)

| # | Component | Modified By | Severity |
|---|-----------|-------------|----------|
| 1 | `globals.css` | Theme | Major — new color palette |
| 2 | `layout.tsx` | Theme | Major — remove hardcoded dark, add providers |
| 3 | `sidebar.tsx` | Theme + Learn | Minor — add toggle + nav item |
| 4 | `chart-colors.ts` | Theme | Major — make theme-aware |
| 5 | `utils.ts` | Theme | Minor — update gradeColors |
| 6 | `grade-badge.tsx` | Theme | Minor — use theme-aware colors |
| 7 | `stock/[symbol]/page.tsx` | Stock Redesign | **Major rewrite** — entire layout change |
| 8 | `price-chart.tsx` | Theme | Minor — use theme-aware colors from context |

### New shadcn/ui Components to Install (3)

| Component | Used By |
|-----------|---------|
| `Sheet` | Stock page drawer |
| `Tabs` | Drawer tab navigation |
| `Popover` | Glossary term definitions |

### New Route Pages (4)

| Route | Purpose |
|-------|---------|
| `/learn` | Learning hub landing |
| `/learn/technical` | Technical indicators |
| `/learn/fundamental` | Financial ratios |
| `/learn/macro` | Macro concepts |

### New Data Files (1)

| File | Purpose | Consumed By |
|------|---------|-------------|
| `src/lib/glossary-data.ts` | Term definitions + keywords | Learn pages, glossary linkify |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: next-themes Package
**What:** Installing `next-themes` package for theme switching.
**Why bad:** Adds unnecessary dependency. The app already has the CSS variable infrastructure from shadcn/ui. `next-themes` is ~5KB and adds complexity (system theme detection, forced-color-scheme, multiple theme support) that this app doesn't need. Two themes (light/dark) with a simple context + localStorage is <50 lines of code.
**Instead:** Build the 3 thin components (ThemeProvider, ThemeToggle, ThemeScript) directly.

### Anti-Pattern 2: MDX for Educational Content
**What:** Setting up MDX pipeline for learn pages.
**Why bad:** MDX requires `@next/mdx`, `remark`, `rehype` plugins, build config changes, and adds 100KB+ to dev deps. For ~30-40 financial terms with formulaic structure (name, description, formula, interpretation ranges), typed TypeScript data is simpler, faster, and gives you type safety + ability to query/filter terms programmatically.
**Instead:** Use `GlossaryTerm[]` data + React components. If content outgrows this later, migrate to MDX then.

### Anti-Pattern 3: Backend Glossary API
**What:** Creating a `/api/glossary` endpoint to serve term definitions from PostgreSQL.
**Why bad:** The glossary is ~30-40 terms that change never (or once a quarter at most). Shipping this as static TypeScript data means zero API latency, zero backend work, and offline capability. Database storage adds migration, seeding, CRUD endpoints, and caching overhead for data that fits in 10KB of TypeScript.
**Instead:** Static `glossary-data.ts`. If user-contributed content is ever needed (v2+), migrate then.

### Anti-Pattern 4: Global State for Drawer
**What:** Using Zustand/Redux/Context for drawer open/close state.
**Why bad:** Drawer state is local to the stock page. It doesn't need to survive navigation or be accessible from other routes. React `useState` in the page component is sufficient.
**Instead:** `const [drawerOpen, setDrawerOpen] = useState(false)` in stock page.

### Anti-Pattern 5: CSS-in-JS for Theme Colors
**What:** Using styled-components, emotion, or inline styles for theme-specific colors.
**Why bad:** The entire shadcn/ui system is built on CSS custom properties + Tailwind classes. Mixing in CSS-in-JS breaks the consistency and adds bundle size.
**Instead:** Everything through CSS variables in `globals.css` + Tailwind utility classes.

---

## Scalability Considerations

| Concern | Current (v1.1) | Future (v2+) |
|---------|----------------|--------------|
| Glossary size | ~30-40 terms, static TS | Could grow to 100+. If so, consider MDX or CMS. Data structure supports it. |
| Theme count | 2 (warm-light, dark) | Could add more (high contrast, etc.). CSS variable system supports N themes. |
| AI report structure | Plain text string | Could become structured JSON (sections, scores, charts). `AIReportView` is designed to handle either. |
| Learn content depth | Short explanations per term | Could expand to full articles with examples, charts. Route structure supports sub-pages. |
| Report text length | ~500-2000 chars | If reports grow to 5000+ chars, glossary regex scan might need optimization (compile once, cache). |

---

## Sources

- **shadcn/ui v4 theming**: Based on codebase analysis of `globals.css` CSS variable pattern, `components.json` config (`style: "base-nova"`, `cssVariables: true`). HIGH confidence.
- **Tailwind v4 dark mode**: `@custom-variant dark (&:is(.dark *))` pattern confirmed in existing `globals.css`. HIGH confidence.
- **lightweight-charts v5 API**: Based on codebase analysis of `price-chart.tsx` and `sub-panel.tsx` — `createChart()`, `applyOptions()`, color configuration at chart creation time. HIGH confidence.
- **Next.js 16 App Router**: Based on existing route structure in `src/app/`. RSC + client component boundaries. HIGH confidence.
- **Sheet/Tabs/Popover availability in shadcn/ui v4**: shadcn v4 (base-nova style) ships these components. Uses `@base-ui/react` primitives which are already in `package.json`. HIGH confidence.
- **Theme persistence pattern**: Standard `localStorage` + inline script approach, widely documented in Next.js community. HIGH confidence.

---

*Research completed: 2026-04-17*
*Scope: v1.1 integration architecture only — no backend changes*
