# Architecture Patterns — v1.3 UI/UX Refinement

**Domain:** UI/UX integration for existing stock analysis dashboard
**Researched:** 2026-04-24
**Confidence:** HIGH — based on direct codebase inspection

## Current Architecture (Baseline)

```
layout.tsx (RootLayout — server component)
  <html lang={locale} suppressHydrationWarning>
    <head> inline theme script (FOUC prevention)
    <body>
      NextIntlClientProvider
        ThemeProvider (custom, useSyncExternalStore — NOT next-themes)
          QueryProvider (TanStack Query)
            AppShell
              Sidebar (fixed left, w-60, client component)
                Logo header
                Nav links: 4 items (rankings, market, learn, admin)
              div.ml-60
                Header (flex end: LanguageToggle + ThemeToggle)
                main.p-6 → {children}
              Toaster (sonner)
```

### Key Observations

1. **Sidebar is fixed-width (w-60 = 240px)** — content uses `ml-60`. No collapse/float logic.
2. **No font loaded via next/font** — `globals.css` body uses `font-family: system-ui, -apple-system, sans-serif`. The `--font-sans` CSS var in `@theme inline` exists but is self-referential (not set by any font call).
3. **Color palette is CSS-variable-based** — `:root` and `.dark` blocks. Current primary: `hsl(210 70.9% 51.6%)` (blue). All components use semantic tokens.
4. **No search on rankings/market** — search only in admin stock table and learn glossary, both `useState` (lost on navigation).
5. **No market session indicator** anywhere.
6. **MacroCards = macro-economic data** (interest_rate, CPI, GDP) — NOT market metrics (VN-Index, volume, advances/declines).
7. **No VN-Index / market summary endpoint** in backend.

## Target Architecture (After v1.3)

```
layout.tsx
  <html className={sourceSans.variable} lang={locale}>  ← NEW: font CSS var
    <head> inline theme script
    <body>
      NextIntlClientProvider
        ThemeProvider
          QueryProvider
            AppShell
              FloatingSidebar (NEW — replaces Sidebar)
                IconRail (w-14, always visible, z-30)
                  Logo icon
                  Main tab icon / Admin tab icon
                  Expand/collapse toggle
                SidebarPanel (w-60, overlay, z-50)
                  Full logo + subtitle
                  Nav links for active tab group
                Backdrop (z-40, click to close)
              div.ml-14  ← changed from ml-60
                Header
                  MarketSessionBar (NEW — left side)
                  LanguageToggle + ThemeToggle (right side)
                main.p-6 → {children}
              Toaster
```

## Integration Architecture for Each Feature

### Feature 1: Font Change (Source Sans 3)

**Integration point:** `layout.tsx` + `globals.css`

Source Sans 3 confirmed in `next/font/google` font-data.json. Variable font, Vietnamese subset available.

```
layout.tsx (MODIFY):
  import { Source_Sans_3 } from "next/font/google"
  const sourceSans = Source_Sans_3({
    subsets: ["latin", "vietnamese"],
    variable: "--font-sans",
    display: "swap"
  })
  <html className={sourceSans.variable}>

globals.css (MODIFY):
  Remove: font-family: system-ui, -apple-system, sans-serif (from body rule)
  The --font-sans var from @theme inline now resolves via next/font injection
```

**Components affected:** None — CSS variable cascade handles globally.
**Critical:** Include `"vietnamese"` subset for diacritics (ă, â, đ, ê, ô, ơ, ư).

### Feature 2: Color Palette Change

**Integration point:** `globals.css` only

All components use semantic tokens. Changing CSS variable values propagates everywhere.

```
globals.css (MODIFY):
  :root {
    --primary: hsl(NEW_WARM);  ← was hsl(210 70.9% 51.6%) blue
    --ring: hsl(NEW_WARM);
    --sidebar-primary: hsl(NEW_WARM);
    --sidebar-ring: hsl(NEW_WARM);
    --chart-2: hsl(DIFFERENT);
  }
  .dark { ... same variables ... }
```

**Components affected:** ZERO. Backgrounds, borders, text already warm from v1.1.

### Feature 3: Floating Sidebar — MAJOR REWRITE

**Integration point:** `app-shell.tsx` + `sidebar.tsx` → 3 new components

```
BEFORE:                         AFTER (collapsed):
+----------+-----------+        +----+------------------+
| Sidebar  | Content   |        |icon| Content (ml-14)  |
| w-60     | ml-60     |        |w-14|                  |
| fixed    |           |        +----+------------------+
+----------+-----------+

AFTER (expanded, overlay):
+----------+------------------+
| Sidebar  | Content (ml-14)  |
| w-60     | + dimmed backdrop |
| z-50     |                  |
+----------+------------------+
```

**New components:**
- `FloatingSidebar` — container: state (open/close, activeTab), localStorage persist
- `IconRail` — w-14, always visible, tab icons + toggle
- `SidebarPanel` — w-60, slides over content, nav links for active group

**State:** `useState` + `localStorage`. No global state needed.

### Feature 4: Icon Tabs (Main / Admin Groups)

Inside FloatingSidebar. Auto-detect from `usePathname()`:
- `/admin/*` → admin tab
- Everything else → main tab

Click tab icon → switch group AND expand panel.

### Feature 5: Search Persistence

**Approach:** URL search params (built-in `useSearchParams` or `nuqs` library)

**Components to modify:**
- `rankings/stock-table.tsx` — ADD search input above table
- `admin/stock-table.tsx` — swap `useState` → URL param
- `learn/glossary-search.tsx` — swap `useState` → URL param

**Pattern:**
```typescript
// hooks/use-search-param.ts (NEW)
// Syncs input with URL ?q=value, debounced
```

### Feature 6: Market Session Progress Bar

**Purely client-side.** HOSE hours (from `scheduler/calendar.py`):

| Session | Time (ICT/UTC+7) |
|---------|------------------|
| ATO | 09:00–09:15 |
| Session 1 | 09:15–11:30 |
| Lunch | 11:30–13:00 |
| Session 2 | 13:00–14:30 |
| ATC | 14:30–14:45 |
| Post | 14:45–15:00 |

**MarketSessionBar** renders: status dot + label + time remaining + progress bar.
Updates via `setInterval(60s)`. Uses `Intl.DateTimeFormat` with `timeZone: 'Asia/Ho_Chi_Minh'`.

**Holiday awareness:** Enhance `/health` with `is_trading_day` (backend has `holidays` package).

### Feature 7: Market Metrics — NEEDS BACKEND

**No VN-Index endpoint exists.** New endpoint required.

```python
# api/routes/market.py (NEW)
GET /api/market/summary
# Compute from existing stock prices:
# total_volume, advances, declines, unchanged, avg_change_percent
```

**Frontend:** `MarketMetrics` component on `/market` page, above MacroCards.

## File Change Map

### MODIFY (9 files)

| File | Changes |
|------|---------|
| `src/app/layout.tsx` | Add Source_Sans_3, apply variable to `<html>` |
| `src/app/globals.css` | Update color vars, remove hardcoded font-family |
| `src/components/layout/app-shell.tsx` | FloatingSidebar, `ml-60`→`ml-14`, header restructure |
| `src/components/rankings/stock-table.tsx` | Add search input |
| `src/app/market/page.tsx` | Add MarketMetrics above MacroCards |
| `src/components/admin/stock-table.tsx` | Swap search state |
| `src/components/learn/glossary-search.tsx` | Swap search state |
| `src/lib/queries.ts` | Add `useMarketSummary()` |
| `src/lib/types.ts` | Add `MarketSummary` interface |

### CREATE (7 files)

| File | Purpose |
|------|---------|
| `src/components/layout/floating-sidebar.tsx` | Sidebar: open/close/tab, localStorage |
| `src/components/layout/icon-rail.tsx` | w-14 icon strip, tab switcher |
| `src/components/layout/sidebar-panel.tsx` | Expandable nav panel |
| `src/components/layout/market-session-bar.tsx` | Session progress in header |
| `src/components/market/market-metrics.tsx` | 4-card market summary |
| `src/hooks/use-search-param.ts` | URL-param search hook |
| Backend: `api/routes/market.py` | GET /api/market/summary |

### DELETE (1 file)

| File | Reason |
|------|--------|
| `src/components/layout/sidebar.tsx` | Replaced by floating-sidebar |

### UNCHANGED

All `components/ui/*` — semantic CSS variables, no changes needed.

## Patterns to Follow

### Pattern 1: CSS Variable Font (next/font + Tailwind v4)
```typescript
const sourceSans = Source_Sans_3({
  subsets: ['latin', 'vietnamese'],
  variable: '--font-sans', display: 'swap',
});
// <html className={sourceSans.variable}>
// globals.css @theme inline { --font-sans: var(--font-sans); } already maps it
```

### Pattern 2: Sidebar Collapse via CSS Transitions
```tsx
<aside className={cn(
  "fixed left-0 top-0 h-screen border-r bg-card z-40",
  "transition-[width] duration-200 ease-in-out",
  collapsed ? "w-14" : "w-60"
)}>
```

### Pattern 3: Timezone-Aware Time (no date library)
```typescript
function getVNTime(): { hours: number; minutes: number } {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: 'numeric', minute: 'numeric', hour12: false,
  }).formatToParts(new Date());
  return {
    hours: Number(parts.find(p => p.type === 'hour')?.value),
    minutes: Number(parts.find(p => p.type === 'minute')?.value),
  };
}
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Do Instead |
|-------------|---------|------------|
| Import `@radix-ui/*` | Project uses `@base-ui/react` (base-nova). Don't mix. | Use `@base-ui/react/*` via `shadcn add` |
| Sidebar state in zustand/context | Over-engineering for single boolean | `useState` + `localStorage` |
| Create `tailwind.config.ts` | Tailwind v4 = CSS-only config | All theme in `globals.css` |
| Parse `toLocaleString()` for timezone | String format is locale-dependent, brittle | Use `formatToParts()` |
| Add `framer-motion` for sidebar | Overkill | CSS `transition-[width]` is sufficient |

## Z-Index Layer System

```
z-0:    Content (default)
z-30:   Icon rail
z-40:   Backdrop (behind panel, above content)
z-50:   Sidebar panel
z-50:   Toaster/sonner
z-50+:  Modals/AlertDialogs
```

## Build Order

```
Phase 1: Foundation (parallelizable)
  1a. Font (layout.tsx + globals.css)
  1b. Colors (globals.css)
  1c. Search hook (independent)

Phase 2: Layout (depends on 1a, 1b)
  2a. FloatingSidebar + IconRail + SidebarPanel
  2b. AppShell restructure
  2c. MarketSessionBar

Phase 3: Features (depends on Phase 2)
  3a. Search on rankings
  3b. Search swap on admin/learn
  3c. Backend: /api/market/summary
  3d. MarketMetrics (needs 3c)

Phase 4: Polish
  4a. Table sort fix
  4b. i18n keys
  4c. E2E tests
```

## Sources

- Direct codebase: layout.tsx, app-shell.tsx, sidebar.tsx, globals.css, all components (HIGH)
- Next.js 16 font docs: `node_modules/next/dist/docs/` (HIGH)
- Font availability: `font-data.json` — Source Sans 3 with Vietnamese subset (HIGH)
- HOSE hours: `scheduler/calendar.py` (HIGH)
- Backend API: all `api/routes/*.py` inspected — no market summary endpoint (HIGH)
