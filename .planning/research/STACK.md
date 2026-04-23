# Stack Research — LocalStock v1.3 (UI/UX Refinement)

**Domain:** Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (base-nova) — UI polish milestone
**Researched:** 2026-04-24
**Confidence:** HIGH (stack inspected directly; font data verified in `node_modules/next/dist/compiled/@next/font/dist/google/font-data.json`; all primitives verified in `node_modules/@base-ui/react/`)

> Scoped to **v1.3 UI/UX refinement only**. Backend, database, LLM pipeline — all unchanged.

---

## Executive Pick (TL;DR)

| Feature | Decision | Rationale |
|---------|----------|-----------|
| **Font** | `next/font/google` → `Source_Sans_3` with `vietnamese` + `latin` subsets | Variable font (200–900 wght), has Vietnamese subset. `next/font` handles self-hosting, `font-display: swap`, and CSS var injection. **Zero new dependencies.** |
| **Color palette** | Modify CSS variables in `globals.css` — change 10 blue `hsl(210 70.9% 51.6%)` values to warm terracotta accent | Pure CSS change. No library needed. Map `--primary` to warm accent `hsl(24 70% 50%)` style. |
| **Sidebar** | Custom component rewrite of existing `sidebar.tsx` — CSS transitions + `localStorage` for collapse state | Already have `lucide-react` icons, `@base-ui/react/tooltip` for icon labels, `@base-ui/react/collapsible` for animation. **No new dependencies.** |
| **Tooltip** | `shadcn add tooltip` (uses `@base-ui/react/tooltip`, already installed) | Need tooltip for collapsed sidebar icon labels. One CLI command. |
| **Table sort fix** | Fix existing `StockTable` sort logic (pure code change) | Bug in current sort — no library needed. |
| **Search persistence** | `nuqs` v2 for URL-based search state management | Type-safe, Next.js App Router native, handles `useSearchParams` edge cases. **Only new dependency.** |
| **Market session bar** | Custom component using existing `Progress` primitive + `Date` API | HOSE hours (9:00–15:00 ICT) with live countdown. Uses existing `@base-ui/react/progress`. **No new deps.** |
| **Market overview metrics** | Enhance existing `MacroCards` component + new API queries | Uses existing TanStack Query hooks + existing `Card` component. **No new deps.** |

**Total new dependencies: 1** (`nuqs`)
**New shadcn components: 1** (`tooltip`)

---

## Existing Stack (DO NOT RE-INSTALL)

| Package | Installed | Role in v1.3 |
|---------|-----------|--------------|
| `next` | 16.2.4 | `next/font/google` for Source Sans 3 loading |
| `react` / `react-dom` | 19.2.4 | Runtime |
| `tailwindcss` + `@tailwindcss/postcss` | ^4 | `@theme inline` for color tokens, `@custom-variant dark` |
| `@base-ui/react` | 1.4.0 | `tooltip/`, `collapsible/`, `progress/` primitives |
| `shadcn` CLI | 4.2.0 | `shadcn add tooltip` for sidebar |
| `lucide-react` | 1.8.0 | Sidebar icons, ChevronLeft/Right for collapse toggle |
| `next-themes` | 0.4.6 | Theme switching (light/dark) — untouched |
| `@tanstack/react-query` | 5.99.0 | Market metrics data fetching |
| `next-intl` | 4.9.1 | i18n — untouched |
| `class-variance-authority`, `clsx`, `tailwind-merge` | — | shadcn invariants |
| `tw-animate-css` | 1.4.0 | Transition/animation utilities |

---

## New Dependencies

### 1. `nuqs` — URL Search Params State Manager

| Field | Value |
|-------|-------|
| Package | `nuqs` |
| Version | `^2.8.9` |
| Purpose | Persist search/filter state in URL query params across navigation |
| Why needed | Current search uses `useState` — state resets on page navigation. `nuqs` provides `useQueryState` that syncs React state with URL params. Type-safe, SSR-compatible, works with Next.js App Router. |
| Why not alternatives | **`useSearchParams` raw**: Verbose, no type safety, requires manual serialization. **Zustand/Jotai**: Client-only state doesn't survive URL sharing or browser back. **`nuqs`**: Purpose-built for exactly this — URL state for filters/search in Next.js. |

```bash
npm install nuqs
```

**Usage pattern:**
```typescript
// In StockTable or RankingsPage
import { useQueryState, parseAsString } from 'nuqs';

const [search, setSearch] = useQueryState('q', parseAsString.withDefault(''));
const [sortKey, setSortKey] = useQueryState('sort', parseAsString.withDefault('total_score'));
const [sortDir, setSortDir] = useQueryState('dir', parseAsString.withDefault('desc'));
```

**Integration:** Wrap app in `<NuqsAdapter>` in layout.tsx (required for Next.js App Router). Drop-in replacement for `useState` in search/sort state.

### 2. `tooltip` shadcn component (not a new npm dep)

```bash
npx shadcn@latest add tooltip
```

This installs `src/components/ui/tooltip.tsx` using the already-installed `@base-ui/react/tooltip` primitive. Needed for collapsed sidebar — icon-only nav items need hover labels.

---

## Feature-Specific Stack Analysis

### Feature 1: Source Sans 3 Font

**Approach:** `next/font/google` (built into Next.js 16, zero deps)

**Verified:** `Source Sans 3` exists in Next.js font data with:
- Variable font: weights 200–900
- Styles: normal, italic
- Subsets: `cyrillic`, `cyrillic-ext`, `greek`, `greek-ext`, **`latin`**, `latin-ext`, **`vietnamese`** ✅

**Implementation:**

```typescript
// src/app/layout.tsx
import { Source_Sans_3 } from 'next/font/google';

const sourceSans = Source_Sans_3({
  subsets: ['latin', 'vietnamese'],
  variable: '--font-sans',
  display: 'swap',
});

// In <html>: className={sourceSans.variable}
```

**CSS changes in `globals.css`:**
```css
@layer base {
  body {
    @apply bg-background text-foreground;
    /* REMOVE: font-family: system-ui, -apple-system, sans-serif; */
    /* next/font injects --font-sans var via className on <html> */
  }
}
```

**Why `next/font/google` not CSS `@import`:**
- Self-hosts font files at build time (no Google Fonts requests at runtime)
- Automatic `font-display: swap` for no FOIT
- Injects CSS variable via `variable` prop — integrates with Tailwind v4 `@theme inline`
- Font subsetting is handled automatically
- Zero layout shift via size-adjust fallback metrics

**Why Source Sans 3 not Be Vietnam Pro (v1.1 choice):**
- v1.3 spec explicitly requests "Source Sans 3 (kiểu Anthropic)"
- Source Sans 3 has full Vietnamese subset ✅
- Clean, professional sans-serif — matches Anthropic's design language
- Variable font = single file for all weights

### Feature 2: Claude Desktop Color Palette (Warm Neutral, No Blue)

**Approach:** Modify existing CSS variables in `globals.css` — pure CSS, zero deps.

**Current state:** Theme already has warm neutral backgrounds (cream `hsl(48 33.3% 97.1%)`), but uses **blue primary** (`hsl(210 70.9% 51.6%)`) for buttons, links, active states, ring, sidebar primary.

**10 blue values to change** (in both `:root` and `.dark`):

| Variable | Current (Blue) | Target (Warm Accent) | Used By |
|----------|---------------|---------------------|---------|
| `--primary` | `hsl(210 70.9% 51.6%)` | Warm terracotta ~`hsl(24 70% 50%)` | Buttons, links, active text |
| `--primary-foreground` | `hsl(0 0% 100%)` | Keep white | Text on primary bg |
| `--ring` | `hsl(210 70.9% 51.6%)` | Match new primary | Focus rings |
| `--sidebar-primary` | `hsl(210 70.9% 51.6%)` | Match new primary | Sidebar active |
| `--sidebar-ring` | `hsl(210 70.9% 51.6%)` | Match new primary | Sidebar focus |
| `--chart-2` | `hsl(210 70.9% 51.6%)` | Different chart color | Chart series |

**Claude Desktop reference palette** (warm neutral family):
- Background: cream/off-white ✅ (already have `hsl(48 33.3% 97.1%)`)
- Primary accent: warm terracotta/burnt orange — `hsl(24 70% 50%)` range
- Text: near-black warm ✅ (already have `hsl(60 2.6% 7.6%)`)
- Muted: warm gray ✅ (already have)
- Borders: warm tan ✅ (already have `hsl(50 20.7% 88.6%)`)

**Key principle:** The backgrounds, borders, text colors, and muted tones are ALREADY Claude-warm. Only the interactive/primary accent color needs to shift from blue to warm.

**No new Tailwind plugins needed.** The `@theme inline` block and CSS variable system handle everything.

### Feature 3: Sidebar Float/Overlay with Collapse

**Approach:** Rewrite `src/components/layout/sidebar.tsx` + adjust `app-shell.tsx`.

**Current sidebar:** Fixed left, 240px (`w-60`), always expanded, 4 nav items (Rankings, Market, Learn, Admin) with icons and labels. Main content has `ml-60`.

**Target sidebar:**
- Float/overlay (not pushing content — removes `ml-60`)
- Collapsible: expanded (240px) ↔ collapsed (icon-only, ~56px `w-14`)
- Collapse state persisted in `localStorage`
- 2 icon tab groups: Main pages (Rankings, Market, Learn) / Admin (Admin)
- Tooltips on icons when collapsed

**Components needed:**
- `@base-ui/react/tooltip` → for icon labels in collapsed mode (**already installed**)
- `shadcn tooltip` component → run `shadcn add tooltip` to get the styled wrapper
- `lucide-react` → `PanelLeftClose`, `PanelLeftOpen` (or `ChevronLeft`/`ChevronRight`) for collapse toggle
- CSS `transition-[width]` for smooth collapse animation

**No Sheet/Drawer needed.** The sidebar should be a permanent fixture that slides between narrow and wide, not a modal overlay. The "float" means it overlays content when expanded (z-index above main), and in collapsed state it sits as a narrow icon strip.

**State management:**
```typescript
const [collapsed, setCollapsed] = useState(() => {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('sidebar-collapsed') === 'true';
});
```

### Feature 4: Fix Table Sort Behavior

**Approach:** Pure code fix in `StockTable` component.

**Current bug analysis** (from `stock-table.tsx`):
- Sort works but the comparator uses `?? -Infinity` fallback for all types including strings
- String columns (`symbol`, `grade`, `recommendation`) compared numerically → incorrect ordering
- Need to handle string vs number comparison properly

**No dependencies needed.** Fix the comparator:
```typescript
const sorted = [...data].sort((a, b) => {
  const aVal = a[sortKey];
  const bVal = b[sortKey];
  if (aVal == null && bVal == null) return 0;
  if (aVal == null) return 1;
  if (bVal == null) return -1;
  if (typeof aVal === 'string' && typeof bVal === 'string') {
    return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
  }
  return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
});
```

### Feature 5: Search State Persistence

**Approach:** `nuqs` for URL-based state + `NuqsAdapter` wrapper.

**Current search pattern** (found in 3 components):
1. `admin/stock-table.tsx` — `useState("")` for `searchQuery`
2. `admin/pipeline-control.tsx` — `useState("")` for `searchQuery`
3. `learn/glossary-search.tsx` — `useState("")` for `query`

**All use `useState`** — state is lost on navigation. Replace with `useQueryState` from `nuqs`:

```typescript
// Before:
const [searchQuery, setSearchQuery] = useState("");

// After:
import { useQueryState, parseAsString } from 'nuqs';
const [searchQuery, setSearchQuery] = useQueryState('q', parseAsString.withDefault(''));
```

**Integration requirement:** Add `<NuqsAdapter>` to `layout.tsx`:
```typescript
import { NuqsAdapter } from 'nuqs/adapters/next/app';
// Wrap children inside QueryProvider, outside AppShell
```

### Feature 6: Market Session Progress Bar

**Approach:** Custom component using existing `Progress` primitive.

**HOSE trading hours (ICT, UTC+7):**
- Pre-open: 9:00–9:15 (ATO)
- Session 1: 9:15–11:30
- Lunch: 11:30–13:00
- Session 2: 13:00–14:30
- ATC: 14:30–14:45
- Post-close: 14:45–15:00

**Component needs:**
- Current time in ICT (use `Intl.DateTimeFormat` with `timeZone: 'Asia/Ho_Chi_Minh'`)
- Progress percentage calculation
- Session label display
- Time remaining countdown
- Auto-refresh via `setInterval` (1 minute)

**Existing components used:**
- `Progress`, `ProgressTrack`, `ProgressIndicator` from `@/components/ui/progress`
- Clock icon from `lucide-react`

**No new dependencies.** JavaScript `Date` + `Intl.DateTimeFormat` handles timezone conversion.

### Feature 7: Market Overview Metrics with Real Data

**Approach:** Enhance existing `MacroCards` component + new API query hook.

**Current state:** `MacroCards` shows 4 cards (interest_rate, exchange_rate, CPI, GDP) using `useMacroLatest()`. These show static macro data.

**Target:** 4 market overview cards showing recent market data:
- VN-Index value + change
- HOSE volume
- Advancing/declining count
- Market breadth or sector leader

**Backend dependency:** New API endpoint needed from FastAPI:
- `GET /api/market/overview` → `{ vn_index, change, change_pct, volume, advances, declines, unchanged }`

**Frontend:** New TanStack Query hook:
```typescript
export function useMarketOverview() {
  return useQuery({
    queryKey: ["market", "overview"],
    queryFn: () => apiFetch<MarketOverview>("/api/market/overview"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}
```

---

## What NOT to Add

| Don't Add | Why Not |
|-----------|---------|
| `@radix-ui/*` | Project uses `@base-ui/react` (shadcn base-nova style). Don't mix primitive libraries. |
| `vaul` (drawer library) | Not needed. Sidebar is not a drawer. |
| `zustand` / `jotai` for search state | URL-based state via `nuqs` is better — survives navigation, shareable, browser-back friendly. |
| `framer-motion` | Overkill for sidebar animation. CSS `transition-[width]` is sufficient. |
| `@fontsource/source-sans-3` | `next/font/google` handles font self-hosting natively. No need for fontsource. |
| `date-fns` / `dayjs` / `luxon` | Only need timezone-aware current time. `Intl.DateTimeFormat` handles it natively. |
| `tailwind.config.ts` | Tailwind v4 uses CSS-only config via `@theme inline`. Don't create a JS config file. |
| Any state management library | TanStack Query for server state. `nuqs` for URL state. `localStorage` for sidebar. No global state needed. |

---

## Installation Summary

```bash
# Only new npm dependency
npm install nuqs

# Add shadcn tooltip component (uses already-installed @base-ui/react)
npx shadcn@latest add tooltip
```

**Total bundle impact:** `nuqs` is ~5KB gzipped. Tooltip component is a thin wrapper. Negligible.

---

## Integration Points

### `layout.tsx` Changes
1. Add `Source_Sans_3` import from `next/font/google`
2. Add font CSS variable to `<html>` via `className={sourceSans.variable}`
3. Wrap children in `<NuqsAdapter>` for search state
4. Remove `system-ui` font-family fallback from body (in globals.css)

### `globals.css` Changes
1. Update 10 `--primary`/`--ring`/`--sidebar-primary`/`--sidebar-ring` blue values → warm terracotta (in both `:root` and `.dark`)
2. Remove `font-family: system-ui, -apple-system, sans-serif` from body rule
3. Font-sans variable auto-injected by `next/font`

### `app-shell.tsx` Changes
1. Remove `ml-60` from main content wrapper
2. Add overlay/z-index logic for sidebar float behavior

### Component Changes (No New Deps)
- `sidebar.tsx` → Full rewrite: collapsible, icon tabs, tooltip, localStorage
- `stock-table.tsx` → Fix sort comparator
- `macro-cards.tsx` → Enhance or create `MarketOverviewCards`
- New: `market-session-bar.tsx` → Progress bar in header

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| Source Sans 3 in `next/font/google` with Vietnamese subset | Verified in `node_modules/next/dist/compiled/@next/font/dist/google/font-data.json` — subsets include `vietnamese` | HIGH |
| `@base-ui/react/tooltip` available | Verified: `ls node_modules/@base-ui/react/tooltip/` exists | HIGH |
| `@base-ui/react/collapsible` available | Already used in `src/components/ui/collapsible.tsx` | HIGH |
| `@base-ui/react/progress` available | Already used in `src/components/ui/progress.tsx` | HIGH |
| `nuqs` v2.8.9 for Next.js App Router | npm registry shows v2.8.9 current, documented for App Router | HIGH |
| `next/font` CSS variable injection | Standard Next.js pattern, project already uses `variable` prop pattern | HIGH |
| HOSE trading hours 9:00–15:00 ICT | Project constraints in PROJECT.md, public market schedule | HIGH |
| Tailwind v4 CSS-only config | Verified — no `tailwind.config.ts` exists, `@theme inline` in `globals.css` | HIGH |
| Current blue primary values (10 occurrences) | Counted via `grep "210 70" globals.css` — 10 lines | HIGH |
| Current search uses `useState` (3 components) | Grep of `searchQuery.*useState` across `src/` — confirmed 3 files | HIGH |
