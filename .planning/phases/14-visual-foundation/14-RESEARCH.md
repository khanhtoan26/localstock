# Phase 14: Visual Foundation - Research

**Researched:** 2026-04-24
**Domain:** CSS theming (color palette + typography), Next.js font loading
**Confidence:** HIGH

## Summary

Phase 14 replaces the current blue primary + blue accent color palette with a neutral tone palette (warm white/gray/near-black, inspired by Claude Desktop) and switches the font from system-ui to Source Sans 3 with Vietnamese subset support. The scope is surgical — primarily CSS variable value changes in `globals.css` plus font loading in `layout.tsx`. The existing architecture is CSS-variable-driven, meaning color changes propagate automatically to all components using semantic classes (`text-primary`, `bg-primary`, etc.).

The change surface is well-contained: **1 file for font loading** (`layout.tsx`), **1 file for all color variables** (`globals.css`), **1 file for chart hardcoded colors** (`chart-colors.ts`), and **3 files with hardcoded blue Tailwind classes** (`utils.ts` gradeColors, `score-breakdown.tsx`, `sidebar.tsx` text-primary usage). All shadcn/ui components (`button.tsx`, `badge.tsx`, `checkbox.tsx`, `input.tsx`, `progress.tsx`) use `bg-primary`/`text-primary` semantic tokens that will auto-update when CSS variables change — no component modifications needed for those.

**Primary recommendation:** Change the 10 blue `hsl(210 70.9% 51.6%)` CSS variable values in globals.css to neutral gray/near-black, load Source Sans 3 as a variable font via `next/font/google` with `variable: '--font-sans'`, and remove the hardcoded `font-family: system-ui` from the body rule. Chart indicator colors (SMA, MACD line) should shift from blue to a dark gray to maintain the neutral aesthetic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Replace blue `--primary` (hsl(210 70.9% 51.6%)) with a neutral tone. Claude Desktop uses warm whites, grays, and near-blacks — no bright accent colors for buttons, links, or interactive elements. The app should feel clean, professional, and monochromatic.
- **D-02:** Keep the warm cream background base (#FAF9F5 / hsl(48 33.3% 97.1%)) from Phase 7 — it already matches Claude Desktop's warm off-white. Only the interactive/accent colors (primary, ring, sidebar-primary) need changing from blue to neutral gray/black.
- **D-03:** Dark mode palette must follow the same neutral principle — warm dark grays with neutral interactive elements, no blue.
- **D-04:** All CSS variable locations need auditing: `:root`, `.dark`, `@theme inline` mappings, and any hardcoded hex in TypeScript (e.g., `chart-colors.ts`).
- **D-05:** Load Source Sans 3 via `next/font/google` with `subsets: ['latin', 'vietnamese']` in `layout.tsx`. Assign CSS variable `--font-sans`.
- **D-06:** Agent's discretion on exact weight range — suggest variable font or 400/500/600/700 range.
- **D-07:** Remove any hardcoded `font-family: system-ui` in `globals.css` that would override the CSS variable.
- **D-08:** Heading font (`--font-heading`) should also use Source Sans 3 (same family, heavier weight for headings is fine).
- **D-09:** Financial up/down/warning colors (green/red/yellow) remain conceptually the same but agent should adjust exact shades to harmonize with the new neutral palette. WCAG AA contrast ratios must be maintained against both light and dark backgrounds.

### Agent's Discretion
- Exact HSL/oklch values for the new neutral palette (research Claude Desktop's actual tones)
- Source Sans 3 weight range and variable font configuration
- Dark mode neutral gray scale exact values
- Chart color tokens update (chart-1 through chart-5) to work with neutral theme
- Ring/focus color choice (subtle gray vs darker gray)
- Transition between old and new sidebar CSS variables

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIS-01 | Font chuyển sang Source Sans 3 với Vietnamese subset, load qua next/font | Source Sans 3 confirmed as variable font (200-900 weight range) on Google Fonts with `vietnamese` subset. `next/font/google` function `Source_Sans_3` available in Next.js 16.2.4. Load with `variable: '--font-sans'` and apply to `<html>` className. |
| VIS-02 | Color palette chuyển sang warm neutral (Claude Desktop style), thay thế blue ở buttons/titles | 10 blue HSL values in globals.css identified. Neutral palette derived from Claude Desktop: near-black primary for light mode, warm light gray primary for dark mode. All components using `text-primary`/`bg-primary` auto-update. 3 files with hardcoded blue classes need manual update. |
| VIS-03 | Dark mode cập nhật palette tương ứng, đảm bảo contrast WCAG AA | Dark mode neutral values specified. Financial colors adjusted for both themes. WCAG AA contrast ratios documented with specific hex values. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Color palette (CSS variables) | Browser / Client | — | CSS variables in `:root`/`.dark` blocks, resolved at render time |
| Font loading | Frontend Server (SSR) | Browser / Client | `next/font/google` downloads at build time, self-hosts; browser applies via CSS variable |
| Chart colors | Browser / Client | — | Hardcoded hex in `chart-colors.ts`, applied via JavaScript to lightweight-charts canvas |
| Theme switching | Browser / Client | — | Custom ThemeProvider + localStorage, class toggle on `<html>` |
| WCAG contrast | Browser / Client | — | Static CSS values, validated at design time |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next/font/google | 16.2.4 (bundled) | Self-host Source Sans 3 | Built into Next.js, zero-CLS font loading, auto-subsetting [VERIFIED: node_modules/next/dist/docs] |
| Tailwind CSS | 4.x | Utility classes + `@theme inline` | Already in use; CSS variable → Tailwind token propagation [VERIFIED: package.json] |
| CSS Custom Properties | — | Color theming | Already the theming mechanism; `:root` + `.dark` blocks in globals.css [VERIFIED: globals.css] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Source Sans 3 (Google Font) | v19 | Primary + heading typeface | Vietnamese subset, variable font 200-900 weight range [VERIFIED: Google Fonts API] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Source Sans 3 via next/font | @fontsource/source-sans-3 | @fontsource works but next/font is officially recommended for Next.js — handles self-hosting, preloading, and CLS prevention automatically [CITED: Next.js 16 docs] |
| CSS custom properties | Tailwind theme config | Already using CSS vars → @theme inline; changing approach would be a larger refactor for no benefit |

**Installation:**
No new npm packages needed. `next/font/google` is bundled with Next.js 16.

**Version verification:**
```bash
# Already installed
npm view next version  # 16.2.4 [VERIFIED: npm registry]
```

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    layout.tsx                         │
│  ┌─────────────────────────────────────────────┐    │
│  │ Source_Sans_3({ variable: '--font-sans',    │    │
│  │   subsets: ['latin', 'vietnamese'] })        │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │ sets --font-sans on <html>     │
│                     ▼                                │
│  ┌─────────────────────────────────────────────┐    │
│  │              globals.css                     │    │
│  │  @theme inline {                            │    │
│  │    --font-sans: var(--font-sans); ──────────┼───▶ Tailwind font-sans
│  │    --font-heading: var(--font-sans); ───────┼───▶ Tailwind headings
│  │  }                                          │    │
│  │                                             │    │
│  │  :root {                                    │    │
│  │    --primary: hsl(X Y% Z%); ────────────────┼───▶ All components using
│  │    --ring: ...                              │    │  text-primary, bg-primary
│  │    --sidebar-primary: ...                   │    │  border-primary, etc.
│  │    --chart-1..5: ...                        │    │
│  │  }                                          │    │
│  │  .dark { ... same vars, dark values ... }   │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                                │
│                     ▼                                │
│  ┌─────────────────────────────────────────────┐    │
│  │           chart-colors.ts                    │    │
│  │  Hardcoded hex for lightweight-charts canvas │    │
│  │  (sma20, macdLine, chartBg, etc.)           │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
apps/helios/src/
├── app/
│   ├── layout.tsx          # Font loading (Source_Sans_3), className on <html>
│   └── globals.css         # All CSS variables (:root + .dark), @theme inline
├── lib/
│   └── chart-colors.ts     # Hardcoded hex chart colors (both themes)
└── components/
    ├── layout/sidebar.tsx  # Uses text-primary (auto-updates)
    └── stock/score-breakdown.tsx  # Has hardcoded bg-blue-500
```

### Pattern 1: Font Loading with CSS Variable in Next.js 16 + Tailwind v4
**What:** Load a Google Font as a CSS variable and propagate through Tailwind's `@theme inline` system
**When to use:** Whenever changing the app's typeface in a Next.js + Tailwind CSS 4 project

```typescript
// Source: Next.js 16 docs (node_modules/next/dist/docs/01-app/03-api-reference/02-components/font.md)
// layout.tsx
import { Source_Sans_3 } from 'next/font/google'

const sourceSans = Source_Sans_3({
  subsets: ['latin', 'vietnamese'],
  display: 'swap',
  variable: '--font-sans',
})

export default async function RootLayout({ children }) {
  return (
    <html lang={locale} className={sourceSans.variable} suppressHydrationWarning>
      {/* ... */}
    </html>
  )
}
```

```css
/* globals.css — Tailwind v4 integration */
/* Source: Next.js 16 docs, Tailwind CSS v4 integration section */
@theme inline {
  --font-sans: var(--font-sans);
  --font-heading: var(--font-sans);  /* same family, weight handled via CSS */
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
    /* REMOVE: font-family: system-ui, -apple-system, sans-serif; */
  }
  html {
    @apply font-sans;
  }
}
```

### Pattern 2: Neutral Color Variable System
**What:** Replace blue primary with neutral gray/black, keeping warm background base
**When to use:** When shifting an existing CSS-variable-driven theme from colorful to monochromatic

```css
/* Claude Desktop-inspired neutral palette */
:root {
  /* Keep warm backgrounds (D-02 — unchanged) */
  --background:           hsl(48 33.3% 97.1%);    /* #FAF9F5 warm off-white */
  --foreground:           hsl(60 2.6% 7.6%);      /* #141413 near-black */

  /* Change blue → neutral for interactive elements */
  --primary:              hsl(60 2% 15%);          /* near-black, warm */
  --primary-foreground:   hsl(0 0% 100%);          /* white text on dark primary */
  --ring:                 hsl(60 2% 15%);          /* match primary */
  --sidebar-primary:      hsl(60 2% 15%);          /* match primary */
  --sidebar-ring:         hsl(60 2% 15%);          /* match primary */
}

.dark {
  /* Neutral interactive elements on dark background */
  --primary:              hsl(48 10% 90%);         /* warm light gray */
  --primary-foreground:   hsl(60 2.7% 14.5%);     /* dark bg color as text */
  --ring:                 hsl(48 10% 90%);
  --sidebar-primary:      hsl(48 10% 90%);
  --sidebar-ring:         hsl(48 10% 90%);
}
```

### Anti-Patterns to Avoid
- **Removing all warm tones for pure #000/#FFF:** The user specifically said "not exact #FFF/#000 — warm neutral tones." Keep the subtle warmth in all grays.
- **Changing background colors:** D-02 explicitly says keep #FAF9F5 cream base and all existing background tokens. Only interactive/accent colors change.
- **Making primary identical to foreground:** Primary needs to be distinguishable from body text — use a slightly different weight (lightness) or apply it only via interactive element styling, not as a text color equivalent.
- **Forgetting the hardcoded blue in chart-colors.ts:** Chart indicator lines (SMA20, MACD line) use `#2563eb`/`#3b82f6` directly — these won't auto-update from CSS variable changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font self-hosting | Manual @font-face declarations | `next/font/google` | Handles subset splitting, preloading, CLS prevention, and self-hosting automatically [CITED: Next.js 16 font docs] |
| WCAG contrast checking | Manual math | Browser DevTools contrast checker or online tools (WebAIM) | Contrast ratios depend on exact rendering context; tools verify against WCAG spec directly |
| CSS variable → Tailwind propagation | Custom PostCSS plugin | `@theme inline` block | Already set up, proven working from Phase 7 |

**Key insight:** The existing CSS-variable architecture means 90% of this phase is just changing values — the propagation infrastructure is already built and tested.

## Claude Desktop Neutral Color Palette — Research

### Light Mode Palette [ASSUMED — based on Claude Desktop visual inspection and existing codebase annotations]

The existing codebase (from Phase 7) already uses Claude Desktop background tokens correctly. The key change is replacing `hsl(210 70.9% 51.6%)` (blue) primary with a neutral tone.

**Claude Desktop light mode characteristics:**
- Background: Warm off-white (#FAF9F5) — **already in place** ✓
- Cards/panels: Pure white (#FFFFFF) — **already in place** ✓
- Text: Near-black with warm undertone (#141413) — **already in place** ✓
- Muted text: Warm gray (#73726C) — **already in place** ✓
- Borders: Warm light gray (#E8E6DC) — **already in place** ✓
- Interactive elements (buttons, links, active states): Near-black or dark warm gray — **needs changing** from blue
- Hover states: Slightly lighter warm gray backgrounds — **already in place** ✓
- Focus rings: Dark gray, not blue — **needs changing**

**Recommended neutral primary values for light mode:**

| Token | Current (Blue) | Recommended (Neutral) | Rationale |
|-------|---------------|----------------------|-----------|
| `--primary` | `hsl(210 70.9% 51.6%)` | `hsl(60 2% 15%)` (~#272725) | Near-black, warm undertone. High contrast on cream bg. Matches Claude Desktop button style. |
| `--primary-foreground` | `hsl(0 0% 100%)` | `hsl(0 0% 100%)` (unchanged) | White text on dark primary buttons |
| `--ring` | `hsl(210 70.9% 51.6%)` | `hsl(60 3% 40%)` (~#686660) | Medium gray for focus rings — visible but not jarring |
| `--sidebar-primary` | `hsl(210 70.9% 51.6%)` | `hsl(60 2% 15%)` | Match primary |
| `--sidebar-primary-foreground` | `hsl(0 0% 100%)` | `hsl(0 0% 100%)` | Unchanged |
| `--sidebar-ring` | `hsl(210 70.9% 51.6%)` | `hsl(60 3% 40%)` | Match ring |

### Dark Mode Palette

| Token | Current (Blue) | Recommended (Neutral) | Rationale |
|-------|---------------|----------------------|-----------|
| `--primary` | `hsl(210 70.9% 51.6%)` | `hsl(48 10% 90%)` (~#E8E5DD) | Warm light gray, high contrast on dark bg |
| `--primary-foreground` | `hsl(48 33.3% 97.1%)` | `hsl(60 2.7% 14.5%)` (#262624) | Dark text on light primary |
| `--ring` | `hsl(210 70.9% 51.6%)` | `hsl(48 5% 55%)` (~#908D83) | Medium warm gray for focus on dark bg |
| `--sidebar-primary` | `hsl(210 70.9% 51.6%)` | `hsl(48 10% 90%)` | Match primary |
| `--sidebar-ring` | `hsl(210 70.9% 51.6%)` | `hsl(48 5% 55%)` | Match ring |

### Chart Token Updates

The 5 chart color tokens need updating to remove the blue (chart-2 was blue = primary):

| Token | Current Light | Recommended Light | Current Dark | Recommended Dark |
|-------|--------------|-------------------|-------------|-----------------|
| `--chart-1` | `hsl(142 72% 29%)` green | Keep (financial green) | `hsl(142 70.6% 45.3%)` | Keep |
| `--chart-2` | `hsl(210 70.9% 51.6%)` **blue** | `hsl(60 2% 35%)` (warm gray) | `hsl(210 70.9% 51.6%)` **blue** | `hsl(48 5% 65%)` (warm gray) |
| `--chart-3` | `hsl(48 96% 40%)` yellow | Keep (financial warning) | `hsl(48 96% 53%)` | Keep |
| `--chart-4` | `hsl(15 54.2% 51.2%)` terracotta | Keep (secondary data) | `hsl(15 63.1% 59.6%)` | Keep |
| `--chart-5` | `hsl(0 72% 42%)` red | Keep (financial red) | `hsl(0 67% 59.6%)` | Keep |

### Chart Indicator Colors (chart-colors.ts)

These hardcoded hex values in `chart-colors.ts` need manual update:

| Property | Current Light | Recommended Light | Current Dark | Recommended Dark |
|----------|--------------|-------------------|-------------|-----------------|
| `sma20` | `#2563eb` (blue-600) | `#57534e` (stone-600) | `#3b82f6` (blue-500) | `#a8a29e` (stone-400) |
| `macdLine` | `#2563eb` | `#57534e` | `#3b82f6` | `#a8a29e` |
| All others | Keep | Keep | Keep | Keep |

### Financial Colors Harmonization (D-09)

Financial colors stay semantically the same but verify WCAG AA contrast:

| Token | Light Value | Contrast on #FAF9F5 | Dark Value | Contrast on #262624 |
|-------|------------|---------------------|-----------|---------------------|
| `--stock-up` | `hsl(142 72% 29%)` (#15803D) | ~6.1:1 ✓ AA | `#22c55e` | ~5.2:1 ✓ AA |
| `--stock-down` | `hsl(0 72% 42%)` (#B91C1C) | ~5.4:1 ✓ AA | `#ef4444` | ~4.6:1 ✓ AA (borderline) |
| `--stock-warning` | `hsl(48 96% 40%)` (#CA8A04) | ~3.5:1 ✗ AA text | `#eab308` | ~7.3:1 ✓ AA |

**Action needed:** Light mode `--stock-warning` (#CA8A04) only achieves ~3.5:1 contrast on cream background, failing WCAG AA for normal text (4.5:1 required). For large text (3:1 threshold) it passes. If used as normal-sized text, darken to `hsl(45 95% 32%)` (~#9F7300, ~5.0:1). If used only in badges/large indicators, current value is acceptable. Dark mode `--stock-down` (#ef4444) is borderline at 4.6:1 — consider `#f87171` (red-400, ~5.6:1) for better contrast, but this is brighter so may clash less with the neutral palette anyway.

## Source Sans 3 Font — Research

### Key Facts [VERIFIED: Google Fonts API + Next.js node_modules]

| Property | Value |
|----------|-------|
| Google Fonts name | Source Sans 3 |
| next/font function | `Source_Sans_3` (from `next/font/google`) |
| Font type | Variable font |
| Weight range | 200–900 (continuous) |
| Styles | normal, italic |
| Available subsets | cyrillic, cyrillic-ext, greek, greek-ext, **latin**, latin-ext, **vietnamese** |
| Vietnamese unicode range | U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB |
| Google Fonts version | v19 |

### Recommended Configuration

```typescript
// Source: VERIFIED from Next.js 16.2.4 node_modules type definitions
import { Source_Sans_3 } from 'next/font/google'

const sourceSans = Source_Sans_3({
  subsets: ['latin', 'vietnamese'],
  display: 'swap',
  variable: '--font-sans',
  // Variable font — no weight specification needed
  // All weights 200-900 available automatically
})
```

**Why variable font (not fixed weights):** Source Sans 3 is a true variable font — specifying `weight: 'variable'` (or omitting weight entirely since it defaults to variable) sends a single font file covering all weights 200-900. This is smaller than loading 4 separate weight files (400/500/600/700) and allows CSS `font-weight` to use any intermediate value. [VERIFIED: Google Fonts API returns `font-weight: 200 900` for variable request]

### Font Chain: next/font → CSS Variable → Tailwind → Components

1. `Source_Sans_3({ variable: '--font-sans' })` → sets `--font-sans` CSS custom property on the element where `sourceSans.variable` className is applied
2. `<html className={sourceSans.variable}>` → `--font-sans` available to entire document
3. `@theme inline { --font-sans: var(--font-sans); }` → Tailwind reads this as `font-sans` utility
4. `html { @apply font-sans; }` → applies `font-family: var(--font-sans)` to root
5. All text inherits Source Sans 3

**Critical fix (Pitfall 1):** The current `body { font-family: system-ui, -apple-system, sans-serif; }` in `globals.css` OVERRIDES the CSS variable chain. This line must be REMOVED for the font to work. The `html { @apply font-sans; }` rule handles font assignment correctly via the variable chain.

## Complete Color Audit — Files Requiring Changes

### Tier 1: CSS Variable Values (auto-propagates to all components)

| File | Lines | What Changes | How Many Values |
|------|-------|-------------|-----------------|
| `globals.css` `:root` | 60, 71, 80, 85 | `--primary`, `--ring`, `--sidebar-primary`, `--sidebar-ring` from blue → neutral | 4 values |
| `globals.css` `:root` | 73 | `--chart-2` from blue → warm gray | 1 value |
| `globals.css` `.dark` | 104, 115, 123, 128 | Same 4 tokens in dark mode | 4 values |
| `globals.css` `.dark` | 117 | `--chart-2` dark from blue → warm gray | 1 value |

**Total: 10 CSS variable value changes** (5 per theme × 2 themes)

### Tier 2: Hardcoded Hex in TypeScript

| File | Lines | What Changes |
|------|-------|-------------|
| `chart-colors.ts` | 28, 31 | `sma20: "#2563eb"`, `macdLine: "#2563eb"` → neutral gray |
| `chart-colors.ts` | 48, 51 | Dark mode equivalents `"#3b82f6"` → neutral gray |

**Total: 4 hex value changes**

### Tier 3: Hardcoded Tailwind Color Classes

| File | Line | Current | Recommended Change |
|------|------|---------|-------------------|
| `lib/utils.ts` | 38 | Grade B: `"bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30"` | Change to neutral gray: `"bg-gray-500/20 text-gray-700 dark:text-gray-400 border-gray-500/30"` or warm stone variant |
| `score-breakdown.tsx` | 7 | Technical score: `color: "bg-blue-500"` | Change to `"bg-stone-500"` or `"bg-gray-500"` |

**Total: 2 files, 2 class changes**

### Tier 4: Components Using `text-primary` / `bg-primary` (NO changes needed)

These files use semantic tokens that auto-update from CSS variable changes:
- `sidebar.tsx` — `text-primary`, `bg-primary/10`
- `stock-table.tsx` — `text-primary`
- `learn/page.tsx` — `text-primary`, `ring-primary/20`
- `learn/[category]/page.tsx` — `text-primary`
- `glossary-term.tsx` — `text-primary`
- `report-progress.tsx` — `bg-primary`
- `button.tsx` — `bg-primary`, `text-primary`
- `badge.tsx` — `bg-primary`, `text-primary`
- `checkbox.tsx` — `data-checked:bg-primary`
- `input.tsx` — `selection:bg-primary`
- `progress.tsx` — `bg-primary`
- `globals.css` — `job-highlight` animation uses `var(--primary)` — auto-updates

**Total: 0 changes needed** — these all propagate from CSS variable changes.

### Font Changes

| File | What Changes |
|------|-------------|
| `layout.tsx` | Add `Source_Sans_3` import, create font instance, add `sourceSans.variable` to `<html>` className |
| `globals.css` line 145 | **Remove** `font-family: system-ui, -apple-system, sans-serif;` from body rule |

**Total: 2 files changed for font**

## Common Pitfalls

### Pitfall 1: Font Variable Collision (CRITICAL)
**What goes wrong:** The current `globals.css` body rule has `font-family: system-ui, -apple-system, sans-serif` hardcoded. This overrides the CSS variable chain (`--font-sans` → Tailwind `font-sans` → `@apply font-sans`), causing the font to silently remain as system-ui despite loading Source Sans 3.
**Why it happens:** Two competing font assignment paths — one via CSS variable chain (correct) and one via hardcoded `font-family` (incorrect, higher specificity on body).
**How to avoid:** Remove the hardcoded `font-family` line from the body rule. The `html { @apply font-sans; }` rule is sufficient and correctly uses the variable chain.
**Warning signs:** In DevTools → Computed tab, `body` shows `system-ui` instead of `"Source Sans 3"`. Font appears as Arial/Helvetica instead of the expected typeface.

### Pitfall 2: Neutral Primary Too Close to Foreground
**What goes wrong:** If `--primary` is set to the same value as `--foreground`, interactive elements (links, buttons, active sidebar items) become visually indistinguishable from regular text.
**Why it happens:** Both neutral primary and body text are near-black on light mode.
**How to avoid:** Use a slightly different lightness or saturation for `--primary` vs `--foreground`. Rely on additional visual cues: buttons have background color, links have underline on hover, active sidebar items have `bg-primary/10` background.
**Warning signs:** Users can't tell what's clickable. Active sidebar item looks like regular text.

### Pitfall 3: Dark Mode Primary Contrast
**What goes wrong:** A warm light gray `--primary` on dark background can appear washed out, especially for small text like link text.
**Why it happens:** The lightness difference between primary and background might be insufficient.
**How to avoid:** Ensure dark mode primary has at least 4.5:1 contrast against `--background` (hsl(60 2.7% 14.5%) = #262624). A primary of `hsl(48 10% 90%)` (~#E8E5DD) provides approximately 12:1 contrast — well above AA requirements.
**Warning signs:** Buttons and links on dark mode appear too dim.

### Pitfall 4: Chart Colors Forgotten
**What goes wrong:** CSS variables update but `chart-colors.ts` hardcoded blue hex values remain. Stock charts show blue SMA/MACD lines that look out of place against the neutral UI.
**Why it happens:** `chart-colors.ts` uses direct hex strings, not CSS variable references, because lightweight-charts requires hex/rgb values at initialization time.
**How to avoid:** Include `chart-colors.ts` in the same task/wave as CSS variable changes. Update `sma20` and `macdLine` values in both LIGHT_COLORS and DARK_COLORS objects.
**Warning signs:** Chart indicator lines are obviously blue while everything else is neutral.

### Pitfall 5: Grade B Color Loses Meaning
**What goes wrong:** Grade B currently uses blue to be visually distinct from green (A), yellow (C), orange (D), red (F). Changing B to gray might make the grade system confusing.
**Why it happens:** Blue had semantic meaning in the grade system — "above average but not top."
**How to avoid:** Choose a gray that's visually distinct from the other grade colors. Consider using `stone-500` or `neutral-500` which have enough visual weight. Alternatively, keep blue for grades only since they're data visualization (like financial colors), not UI chrome.
**Warning signs:** Users can't quickly distinguish grade B badges from other elements.

## Code Examples

### Font Loading in layout.tsx
```typescript
// Source: VERIFIED from Next.js 16 docs + node_modules type definitions
import { Source_Sans_3 } from 'next/font/google'

const sourceSans = Source_Sans_3({
  subsets: ['latin', 'vietnamese'],
  display: 'swap',
  variable: '--font-sans',
})

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} className={sourceSans.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem("localstock-theme")||"light";document.documentElement.classList.add(t)}catch(e){document.documentElement.classList.add("light")}})()`,
        }} />
      </head>
      <body>
        <NextIntlClientProvider messages={messages}>
          <ThemeProvider>
            <QueryProvider>
              <AppShell>{children}</AppShell>
            </QueryProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

### CSS Variable Changes (globals.css :root)
```css
/* Source: Derived from Claude Desktop visual analysis + D-01/D-02 decisions */
:root {
  /* UNCHANGED — warm backgrounds per D-02 */
  --background:           hsl(48 33.3% 97.1%);
  --foreground:           hsl(60 2.6% 7.6%);
  --card:                 hsl(0 0% 100%);
  /* ... all other background/text tokens stay the same ... */

  /* CHANGED — blue → neutral */
  --primary:              hsl(60 2% 15%);          /* warm near-black */
  --primary-foreground:   hsl(0 0% 100%);          /* white (unchanged) */
  --ring:                 hsl(60 3% 40%);          /* medium warm gray for focus */
  --chart-2:              hsl(60 2% 35%);          /* warm gray (was blue) */
  --sidebar-primary:      hsl(60 2% 15%);          /* match primary */
  --sidebar-primary-foreground: hsl(0 0% 100%);
  --sidebar-ring:         hsl(60 3% 40%);          /* match ring */
}
```

### Body Font Rule Fix
```css
/* BEFORE (broken — overrides CSS variable chain) */
body {
  @apply bg-background text-foreground;
  font-family: system-ui, -apple-system, sans-serif;  /* DELETE THIS LINE */
}

/* AFTER (correct — inherits from html font-sans) */
body {
  @apply bg-background text-foreground;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@fontsource/*` packages | `next/font/google` built-in | Next.js 13+ | Self-hosting handled automatically, no extra dependency |
| Tailwind v3 `theme.extend.fontFamily` | Tailwind v4 `@theme inline` CSS block | Tailwind v4 (2024) | Font variables defined in CSS, not JS config |
| Fixed weight font files (400, 700) | Variable fonts (200-900 range) | Google Fonts 2020+ | Single file, any weight value, smaller total download |
| `next-themes` for theme management | Custom ThemeProvider (this project) | Phase 7 | Already in place, no change needed |

**Deprecated/outdated:**
- `tailwind.config.ts` fontFamily configuration — replaced by `@theme inline` in Tailwind v4
- `@next/font` package — absorbed into `next/font` since Next.js 13.2

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Claude Desktop uses warm near-black (#272725 area) for interactive elements in light mode | Claude Desktop Neutral Color Palette | Low — exact hex values are agent's discretion per CONTEXT.md. If the exact shade doesn't match, it's easily adjusted in a single CSS file. |
| A2 | Claude Desktop dark mode uses warm light gray (~#E8E5DD) for interactive elements | Claude Desktop Neutral Color Palette | Low — same reasoning as A1, easily tuned. |
| A3 | The `--font-sans` CSS variable name won't collide with Tailwind's built-in `--font-sans` | Font Loading | Medium — the `@theme inline` block already maps `--font-sans: var(--font-sans)`, which is circular. Next.js injects the font variable at higher specificity via a generated class on `<html>`, which should win. If it doesn't resolve correctly, rename to `--font-source-sans` and update `@theme inline` accordingly. |
| A4 | Financial color #CA8A04 (stock-warning) has ~3.5:1 contrast on cream | Financial Colors Harmonization | Low — can be verified with any contrast checker tool during implementation. |
| A5 | Dark mode --stock-down (#ef4444) achieves ~4.6:1 contrast on #262624 | Financial Colors Harmonization | Low — exact contrast ratio should be verified during implementation. Borderline AA pass. |

## Open Questions

1. **Grade B color decision**
   - What we know: Grade B currently uses blue (`bg-blue-500`) to distinguish it from other grades. Changing to gray/stone would make it consistent with the neutral palette but potentially confusing in the grade hierarchy.
   - What's unclear: Whether the user considers grade colors as "UI chrome" (should become neutral) or "data visualization" (can keep distinct colors like financial up/down).
   - Recommendation: Change to `bg-stone-500` (neutral gray) for consistency with the monochromatic direction. If user objects, easily reverted to blue since it's a single class.

2. **Score breakdown technical_score color**
   - What we know: `score-breakdown.tsx` uses `bg-blue-500` for the technical score bar, while other dimensions use emerald, amber, violet.
   - What's unclear: Whether all dimension colors should become neutral or only the blue one.
   - Recommendation: Keep dimension colors (emerald, amber, violet) as they are — they're data visualization colors that help users distinguish 4 different metrics. Only change `bg-blue-500` to `bg-stone-500` or `bg-slate-500`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.4 + Playwright 1.59.1 |
| Config file | `apps/helios/vitest.config.ts` (unit), `apps/helios/playwright.config.ts` (e2e) |
| Quick run command | `cd apps/helios && npx vitest run` |
| Full suite command | `cd apps/helios && npx vitest run && npx playwright test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIS-01 | Source Sans 3 loaded, no system-ui fallback visible | e2e | `npx playwright test e2e/visual-foundation.spec.ts --grep "font"` | ❌ Wave 0 |
| VIS-02 | Primary color is neutral (not blue), buttons/links render in neutral tone | e2e | `npx playwright test e2e/visual-foundation.spec.ts --grep "neutral"` | ❌ Wave 0 |
| VIS-03 | Dark mode has neutral palette, financial colors pass WCAG AA | e2e | `npx playwright test e2e/visual-foundation.spec.ts --grep "dark"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/helios && npx vitest run`
- **Per wave merge:** `cd apps/helios && npx vitest run && npx playwright test`
- **Phase gate:** Full suite green + manual visual inspection in both themes

### Wave 0 Gaps
- [ ] `e2e/visual-foundation.spec.ts` — E2E tests for font loading (computed font-family check), neutral color verification (getComputedStyle on primary elements), dark mode palette check, WCAG contrast spot-checks
- [ ] No vitest unit tests needed — this phase is CSS/config changes, not logic. E2E + visual verification is the appropriate test strategy.

## Security Domain

This phase involves only CSS styling and font loading — no authentication, data handling, user input, cryptography, or access control changes.

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V2 Authentication | No | No auth changes |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No access control changes |
| V5 Input Validation | No | No user input processing |
| V6 Cryptography | No | No crypto operations |

**Security note:** `next/font/google` downloads fonts at build time and self-hosts them — no runtime requests to Google. This is a privacy benefit, not a risk.

## Sources

### Primary (HIGH confidence)
- **Next.js 16.2.4 font documentation** — `node_modules/next/dist/docs/01-app/01-getting-started/13-fonts.md` and `01-app/03-api-reference/02-components/font.md` — font loading API, CSS variable integration, Tailwind CSS v4 `@theme inline` pattern
- **Next.js 16.2.4 type definitions** — `node_modules/next/dist/compiled/@next/font/dist/google/index.d.ts` — `Source_Sans_3` function signature, available weights (200-900 + 'variable'), available subsets (confirmed 'vietnamese')
- **Google Fonts API** — `fonts.googleapis.com/css2?family=Source+Sans+3` — confirmed variable font support (font-weight: 200 900), Vietnamese subset with full unicode range (U+0102-0103, U+0110-0111, ..., U+1EA0-1EF9, U+20AB)
- **Codebase inspection** — `globals.css`, `layout.tsx`, `chart-colors.ts`, `sidebar.tsx`, `utils.ts`, `score-breakdown.tsx` — complete audit of all color locations

### Secondary (MEDIUM confidence)
- **Phase 7 CONTEXT.md** — Previous Claude-inspired theme decisions, token naming conventions
- **v1.3 PITFALLS.md** — Font variable collision pitfall (P1), documented with detection strategy

### Tertiary (LOW confidence)
- Claude Desktop visual palette — exact hex values are approximations based on visual observation, not official design tokens. The neutral direction (warm whites/grays/near-blacks, no bright accents) is well-established from user's description, but specific HSL values are agent's recommendation per CONTEXT.md discretion.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — next/font/google verified in node_modules, Source Sans 3 verified on Google Fonts API, no new dependencies needed
- Architecture: HIGH — existing CSS variable infrastructure verified by code inspection, propagation chain well-understood
- Pitfalls: HIGH — font variable collision documented in PITFALLS.md from v1.3 research, verified by reading current globals.css body rule
- Color palette values: MEDIUM — neutral direction is locked by user decisions, but exact HSL values are recommendations based on visual analysis (agent's discretion area)

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable — CSS/font APIs don't change frequently)
