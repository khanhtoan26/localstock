# Stack Research — LocalStock v1.1 (UX Polish & Educational Depth)

**Domain:** Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (Base UI "base-nova" style) — frontend polish milestone (theme system, drawer-based stock page, academic/glossary page)
**Researched:** 2026-04-17
**Confidence:** HIGH (existing stack inspected directly; library versions verified against npm/GitHub as of April 2026)

> This STACK.md is scoped to **v1.1 frontend polish only**. Backend, crawlers, LLM pipeline, Telegram, PostgreSQL, etc. are unchanged — see git history / prior milestones for that stack.

---

## Executive Pick (TL;DR)

- **Theme system** → `next-themes@0.4.6` + Tailwind v4 `@custom-variant` + CSS-variable light/dark blocks. Use `attribute="class"` so the existing `<html className="dark">` pattern still works; flip default to `"claude"` (warm light) with `defaultTheme="claude"`.
- **Right-side drawer** → `@base-ui/react/drawer` (already installed in `@base-ui/react@1.4.0`, stable in 1.3.0). Do NOT add `vaul` or `@radix-ui/react-dialog`. Matches the existing `base-nova` shadcn style — no primitive mixing.
- **Markdown for LLM reports** → `react-markdown@10` + `remark-gfm@4` + `rehype-sanitize@6`. Wrap in `prose` classes from `@tailwindcss/typography@0.5.19` via the v4 `@plugin` directive.
- **Glossary popovers** → `@base-ui/react/preview-card` (hover, reading-focused) and `@base-ui/react/popover` (tap/keyboard). Static typed `glossary.ts` module keyed by indicator code — no new content framework.
- **Academic page content** → Plain `.tsx` pages + typed `glossary.ts`. **Do NOT add** `@next/mdx`, Contentlayer, Nextra, or Velite — the v1.1 corpus is ~25 Vietnamese entries; MDX pipelines are overkill and conflict with the streaming LLM markdown renderer.
- **Vietnamese reading typography** → `next/font/google` loading **Be Vietnam Pro** (body) + keep Geist Mono. Don't rely on system `-apple-system`/Segoe for Vietnamese diacritics.

---

## Existing Stack (Verified by Direct Inspection — DO NOT RE-RESEARCH)

From `apps/helios/package.json` and `node_modules/`:

| Package | Installed | Role in v1.1 |
|---|---|---|
| `next` | 16.2.4 | Runtime — no upgrade needed |
| `react` / `react-dom` | 19.2.4 | Runtime — no upgrade needed |
| `tailwindcss` + `@tailwindcss/postcss` | ^4 | Already using `@theme inline`, `@custom-variant`, OKLCH — add theme block & typography plugin |
| `@base-ui/react` | 1.4.0 | Primitive library. Already has `drawer/`, `popover/`, `preview-card/`, `tooltip/`, `dialog/` — confirmed in `node_modules` |
| `shadcn` CLI | 4.2.0 | `components.json` → `"style": "base-nova"` (locks Base UI primitives) |
| `lightweight-charts` | 5.1.0 | Mounts inside drawer for chart view |
| `recharts` | 3.8.1 | Dashboard charts — untouched |
| `@tanstack/react-query` | 5.99.0 | Drives drawer's on-demand fetches |
| `lucide-react` | 1.8.0 | `Sun`/`Moon` for toggle, `BookOpen`/`Info` for glossary |
| `class-variance-authority`, `clsx`, `tailwind-merge` | — | shadcn invariants — do not touch |
| `tw-animate-css` | 1.4.0 | Drawer enter/exit animations |

---

## Recommended Stack — New Dependencies

| Package | Version | Purpose | Why this pick for LocalStock |
|---|---|---|---|
| `next-themes` | `^0.4.6` | Theme state + SSR-safe `<html>` class injection | De-facto standard; v0.4.6 (Mar 2025) is still current in Apr 2026. Ships the inline `<script>` that writes the class *before* hydration, so the cream default never flashes to dark on load. Works with Tailwind v4 via `@custom-variant`. No React 19 / Next 16 peer issues reported. |
| `@tailwindcss/typography` | `^0.5.19` (dev dep) | `prose` classes for LLM-generated Vietnamese Markdown | Only typography plugin keeping pace with v4 (`@plugin` directive, last publish ~7 months ago). Reading-first AI reports need paragraph rhythm, list spacing, and blockquote tone out of the box — hand-writing them in utilities wastes a week. |
| `react-markdown` | `^10.1.0` | Renders Markdown strings from Ollama into React | Battle-tested and v10 has proper React 19 support. Accepts custom `components` override so we can rewrite `` `RSI` `` inline-code tokens → `<GlossaryTerm code="RSI">RSI</GlossaryTerm>`. |
| `remark-gfm` | `^4.0.1` | GFM tables, strikethrough, task lists | LLM outputs indicator tables constantly; without GFM they render as raw pipe characters. |
| `rehype-sanitize` | `^6.0.0` | XSS hardening on LLM output | Even a local Ollama can emit `<img onerror>` or `<iframe>` if prompts are contaminated by scraped news/sentiment data. `defaultSchema` + `user-content-` ID clobber guard is the accepted baseline. |

### Existing Dependencies — Action Required (no install, just wiring)

| Package | Action | Rationale |
|---|---|---|
| `@base-ui/react@1.4.0` | Import `drawer`, `popover`, `preview-card`, `tooltip` primitives | All stable; we already pay the bundle cost |
| `tailwindcss@^4` | Add new `@custom-variant` + `:root` warm block; keep `.dark` block verbatim | v4 moved dark-mode config into CSS; current `globals.css` already follows this pattern |
| `shadcn@4.2.0` CLI | `npx shadcn add sheet drawer popover tooltip hover-card` | CLI generates wrappers that match the existing Base-UI-based `button`/`badge` pattern in `components/ui/` |
| `next/font/google` | Load `Be Vietnam Pro` as `--font-be-vietnam-pro`; retain Geist Mono | System fonts render Vietnamese diacritics poorly (Segoe UI, Arial, -apple-system). Be Vietnam Pro was designed for Vietnamese by Vietnamese designers, ships variable axes. |

---

## Installation

```bash
cd apps/helios

# Runtime deps
npm install next-themes@^0.4.6 \
            react-markdown@^10.1.0 \
            remark-gfm@^4.0.1 \
            rehype-sanitize@^6.0.0

# Dev dep (Tailwind plugin, build-time only)
npm install -D @tailwindcss/typography@^0.5.19

# Generate shadcn/base-nova wrappers (interactive, accept defaults)
npx shadcn@latest add sheet drawer popover tooltip hover-card
```

**Intentionally not installed:** `vaul`, `@radix-ui/*`, `@next/mdx`, `@mdx-js/loader`, `@mdx-js/react`, `contentlayer`, `contentlayer2`, `velite`, `nextra`, `streamdown`, `framer-motion`, `motion`, `styled-components`, `emotion`, `@headlessui/react`, `prismjs`, `highlight.js`, `katex`, `react-katex`. Rationale in "What NOT to Use" below.

---

## Theme Variables Strategy (Tailwind v4 specifics)

Two named themes: **`claude`** (default, warm light) and **`dark`** (existing financial dark palette, preserved verbatim per `UI-SPEC.md`). next-themes manages state; Tailwind v4 reads it via a custom variant.

### `globals.css` skeleton (diff from current)

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@plugin "@tailwindcss/typography";          /* NEW */

/* Keep this variant — next-themes (attribute="class") toggles .dark */
@custom-variant dark (&:where(.dark, .dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --font-sans: var(--font-be-vietnam-pro);   /* CHANGED from --font-sans */
  --font-mono: var(--font-geist-mono);
  --font-heading: var(--font-be-vietnam-pro);/* or --font-geist-sans if we keep Geist headings */
  /* … rest of existing @theme inline block unchanged … */
}

/* DEFAULT theme = Claude warm-light. :root now holds the cream palette. */
:root {
  --background:           oklch(0.97 0.02 70);   /* cream ≈ #F5F0E8 */
  --foreground:           oklch(0.22 0.02 60);   /* warm near-black */
  --card:                 oklch(0.99 0.01 70);
  --card-foreground:      oklch(0.22 0.02 60);
  --popover:              oklch(0.99 0.01 70);
  --popover-foreground:   oklch(0.22 0.02 60);
  --primary:              oklch(0.70 0.14 45);   /* terracotta ≈ #D97757 */
  --primary-foreground:   oklch(0.99 0.01 70);
  --secondary:            oklch(0.93 0.02 70);
  --secondary-foreground: oklch(0.28 0.02 60);
  --muted:                oklch(0.93 0.02 70);
  --muted-foreground:     oklch(0.50 0.02 60);
  --accent:               oklch(0.90 0.04 55);
  --accent-foreground:    oklch(0.25 0.03 45);
  --destructive:          oklch(0.577 0.245 27);
  --border:               oklch(0.88 0.02 70);
  --input:                oklch(0.88 0.02 70);
  --ring:                 oklch(0.70 0.14 45);

  /* Financial semantics — same hues as dark theme, just adjusted lightness */
  --stock-up:       oklch(0.62 0.18 145);
  --stock-down:     oklch(0.58 0.22 27);
  --stock-warning:  oklch(0.75 0.16 85);

  --radius: 0.625rem;
}

.dark {
  /* PRESERVE the existing UI-SPEC.md-contracted dark palette byte-for-byte */
  --background: hsl(222.2 84% 4.9%);
  /* … the 25+ existing .dark variables stay exactly as in current globals.css … */
}
```

### Provider wiring in `app/layout.tsx`

```tsx
import { ThemeProvider } from "next-themes";
import { Be_Vietnam_Pro, Geist_Mono } from "next/font/google";

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-be-vietnam-pro",
  display: "swap",
});

const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning className={`${beVietnamPro.variable} ${geistMono.variable}`}>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="claude"
          themes={["claude", "dark"]}
          value={{ claude: "", dark: "dark" }}   // "claude" = bare :root, "dark" = .dark
          enableSystem={false}                    // product decision: Claude is default, not OS-driven
          disableTransitionOnChange               // prevents orange→navy flash during toggle
          storageKey="localstock-theme"
        >
          <QueryProvider>
            <AppShell>{children}</AppShell>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

Key details:
- `suppressHydrationWarning` on `<html>` is **required** — next-themes writes the class pre-hydration and React's mismatch detector would flag it otherwise. Documented, officially blessed escape hatch (not a blanket hydration-bug silencer).
- `value={{ claude: "", dark: "dark" }}` maps theme name `claude` → *no class* (so `:root` applies) and `dark` → `.dark`. Avoids introducing a third `.claude` class that would duplicate CSS variables.
- `enableSystem={false}` because the spec is "Claude is default"; leaving system detection on would surprise dark-OS users on first visit.
- `storageKey` is scoped to the app so we don't collide with any next-themes demo on the same localhost.

---

## Component Choices — Detailed Rationale

### Drawer (right-side data panel on stock page)

**Pick:** `@base-ui/react/drawer` wrapped via `npx shadcn add drawer` under `base-nova`.

| Alternative | Why rejected |
|---|---|
| `vaul` (Emil Kowalski's Radix-based drawer) | Brings Radix Dialog into a project that deliberately chose Base UI → two focus-trap implementations = a11y bugs. ~40 kB extra. |
| `@radix-ui/react-dialog` raw | Same primitive-mixing problem; contradicts `components.json` → `"style": "base-nova"`. |
| Custom `position: fixed` panel | Loses focus trap, Esc handling, `inert` background, swipe gestures. Not worth rebuilding. |
| shadcn `Sheet` (Base UI port) | Fine for simple side panels. Base UI's `Drawer` additionally has `direction="right"` plus swipe-to-dismiss and the `Indent` / `IndentBackground` parts that give the "pushed content" feel the redesign brief calls for. Prefer `Drawer`; install `Sheet` too for simpler cases (mobile nav). |

### Glossary term interaction

**Pick (reading):** `@base-ui/react/preview-card` — shows a definition card on pointer hover (and on focus for keyboard users) with a ~300 ms delay. This is the Base UI analog of Radix HoverCard. Ideal for *scanning* an AI report where the user wants passive enrichment without clicking.

**Pick (tap / mobile / committed reading):** `@base-ui/react/popover` — opens on click and stays until dismissed. Use on macro-concept pages where users want to read the full definition.

**Content source:** a typed TS module, not MDX:

```ts
// lib/glossary.ts
export type GlossaryCode = "RSI" | "MACD" | "MA" | "BOLLINGER" | "PE" | "PB" | "ROE" | "ROA" | "CPI" | "LAI_SUAT" | "T3" /* … */;

export type GlossaryEntry = {
  title: string;
  short: string;           // 1 sentence, for hover preview
  long: string;            // 2–3 paragraphs Markdown, for full page
  formula?: string;
  seeAlso?: GlossaryCode[];
};

export const glossary: Record<GlossaryCode, GlossaryEntry> = {
  RSI: {
    title: "RSI — Relative Strength Index",
    short: "Chỉ báo động lượng đo tốc độ thay đổi giá (thang 0–100).",
    long: "…",
    formula: "RSI = 100 − 100 / (1 + RS)",
    seeAlso: ["MACD", "MA"],
  },
  // … ~25 entries total for v1.1
};
```

Rationale for **not** using MDX here:
- ~25 short entries — a TS object literal is shorter than the MDX pipeline config.
- Compile-time typing means a typo in `seeAlso: ["MACDD"]` is a build error, not a runtime dead link.
- The glossary is consumed from **inside LLM-generated markdown** (we rewrite ``` `RSI` ``` tokens in `react-markdown`'s `components.code`). MDX files would force a second rendering context.

### Glossary linking inside LLM reports

In the `react-markdown` `components` prop, override `code` (inline) and optionally `a`:

```tsx
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeSanitize]}
  components={{
    code({ className, children, ...props }) {
      const isInline = !className;
      if (isInline) {
        const key = String(children).trim().toUpperCase();
        if (key in glossary) return <GlossaryTerm code={key as GlossaryCode}>{children}</GlossaryTerm>;
      }
      return <code className={className} {...props}>{children}</code>;
    },
  }}
>
  {reportMarkdown}
</ReactMarkdown>
```

The LLM prompt stays simple: "wrap indicator names in backticks." (It already does this — no retraining.)

### Typography for Vietnamese reading

**Pick:** `next/font/google` → `Be Vietnam Pro` (variable) as body, `Geist Mono` for code.

- **Why not system fonts:** Vietnamese stacked diacritics (`ế`, `ợ`, `ủ`, `ườ`) collide visibly in `-apple-system`, `Segoe UI`, `Arial`. Be Vietnam Pro was designed by Vietnamese type designers and ships a variable axis (wght 100–900), so one file covers body + emphasis.
- **Why not Inter:** Inter covers Vietnamese but its diacritics were retrofitted; line-height in long-form Vietnamese paragraphs is visibly tight. Be Vietnam Pro renders cleaner at 16–18px reading sizes.
- **Why not `@fontsource/*`:** `next/font` self-hosts Google Fonts with automatic `size-adjust` and `font-display: swap`. Zero CLS for reports that stream in progressively.
- **Reading size target:** `prose-lg` (~18px / 1.75 leading) for the center-column AI report. The `@tailwindcss/typography` plugin handles this with zero manual CSS.

### Academic page content format

**Pick:** Plain `.tsx` pages at `app/hoc-thuat/...` with content imported from `lib/glossary.ts`. The page renders entries via the same `react-markdown` component used for AI reports, giving style parity for free.

| Option | Verdict | Reason |
|---|---|---|
| **Plain `.tsx` + TS glossary** (pick) | ✅ | Zero new deps, compile-time typed links, one Markdown renderer path shared with LLM output. Fits the ~25-entry scope perfectly. |
| `@next/mdx` | ❌ | Requires `next.config.ts` changes + `mdx-components.tsx` + `pageExtensions` tweak; entries are short enough that JSX noise outweighs Markdown ergonomics. |
| Contentlayer / Contentlayer2 | ❌ | Contentlayer is unmaintained as of late 2024; Contentlayer2 exists but adds a build-time transform pipeline. Overkill for 25 items. |
| Velite | ❌ | Modern and well-made, but again — 25 items. Re-evaluate if v2 adds 200+ articles. |
| Nextra | ❌ | It's a docs *framework* that wants to own routing + layout. Our app already has `AppShell` + sidebar chrome. |

---

## Alternatives Considered

| Recommended | Alternative | When the alternative would win |
|---|---|---|
| `next-themes` | Hand-rolled theme cookie + RSC reader | Only if we needed server components to render *themed HTML* from cookies without any client JS. LocalStock's chrome is already client-heavy (React Query, charts), so client-side flip is cheaper to ship. |
| Base UI `Drawer` | `vaul` | If we wanted iOS-sheet physics (rubber-banding velocity curves) for a mobile-first app. LocalStock is desktop-primary. |
| Base UI `PreviewCard` | Plain `Tooltip` | If glossary entries were <1 sentence. Ours are paragraph-length with formulas — need the card layout. |
| `react-markdown` | `streamdown@2.5.0` | Streamdown has *better* handling of partial/streaming markdown chunks. **Revisit in v1.2** if we move to live-streamed reports; for v1.1 reports arrive complete from backend, so react-markdown's smaller surface area wins. |
| `@tailwindcss/typography` | `tw-prose` (CSS-only fork) | If we wanted zero build-time plugins. Not a big enough constraint to diverge from the official plugin. |
| TS glossary module | JSON glossary + import assertion | If non-developers were editing entries. Single-developer project → TS (with autocomplete on `seeAlso` keys) is strictly better. |
| Be Vietnam Pro | Inter, Geist Sans, Lexend | If Vietnamese diacritics weren't central. They are (most of the app content is Vietnamese). |

---

## What NOT to Use (explicit anti-recommendations)

| Avoid | Why | Use Instead |
|---|---|---|
| `vaul` | Pulls in Radix Dialog → primitive fragmentation with Base UI. Extra ~40 kB. | `@base-ui/react/drawer` (already installed) |
| `@radix-ui/react-*` packages | `components.json` is locked to `"style": "base-nova"`. Mixing libraries doubles focus-trap code paths and causes subtle a11y bugs (focus returns to wrong element). | `@base-ui/react/*` equivalents |
| `@next/mdx` + `@mdx-js/*` | Requires `next.config.ts` changes, `mdx-components.tsx`, `pageExtensions` — heavy wiring for 25 entries. MDX also fights the streaming LLM-markdown pipeline (two separate renderers). | TS glossary module rendered by `react-markdown` |
| `contentlayer` / `velite` / `nextra` | Content framework weight ≫ content size. | Same TS module |
| `streamdown` | Nice project but overkill when reports arrive as complete strings; adds Shiki/Mermaid/LaTeX plugin bundles we don't need. | `react-markdown` + `remark-gfm` + `rehype-sanitize` |
| `framer-motion` / `motion` | Drawer animations come free from `tw-animate-css` + Base UI's built-in open/close states. No page transitions planned for v1.1. | Existing `tw-animate-css` |
| `styled-components`, `emotion`, any CSS-in-JS | App is 100% Tailwind v4 utility-first. Mixing runtimes adds SSR complexity and wrecks the theme-variable story. | Tailwind + CSS variables |
| `@headlessui/react` | Another primitive library — would triple-stack with Base UI and shadcn's Radix ghosts. | Base UI |
| `prismjs`, `highlight.js`, `shiki` | Academic page shows formulas, not source code. No syntax highlighting need. | Plain `<code>` with `font-mono` |
| `katex` / `react-katex` / `mathjax` | RSI/MACD formulas are simple enough (`RSI = 100 − 100/(1+RS)`) to render as styled text. | Plain text in `<code>` or `<pre>` |
| `react-helmet` / `next-seo` | Next 16 `metadata` export covers everything needed. | `export const metadata` per page |
| Custom cookie-based theme in a Server Component | next-themes already solves this with its inline script. Reinventing = hydration bugs. | `next-themes` |
| Pre-release `@base-ui/react@next` | 1.4.0 (Apr 13, 2026) is stable; Drawer stabilized in 1.3.0. Do not pin to betas. | Keep `^1.4.0` |
| Changing to `radix-*` shadcn styles | Would force regenerating every existing `components/ui/*` wrapper and retraining muscle memory. | Stay on `base-nova` |

---

## Stack Patterns by Variant

**If a glossary term appears inside a chart tooltip or sidebar (not inside markdown):**
- Use `<GlossaryTerm code="RSI" />` directly. The component internally picks `PreviewCard` vs `Popover` based on device pointer capability: `window.matchMedia("(hover: hover)")`.

**If the academic corpus grows past ~50 entries in a future milestone:**
- Switch glossary source from inline TS module to generated `.ts` from a `content/*.md` directory (remark plugin at build time). Still no MDX needed.

**If v1.2 adds real-time streaming reports:**
- Swap `react-markdown` → `streamdown`; the API is almost drop-in. Keep `remark-gfm` / `rehype-sanitize` plugins and the `components` override.

**If a third theme is requested (e.g., "high-contrast"):**
- Add another `:root[data-theme="hc"] { … }` block and a third `@custom-variant`. next-themes supports arbitrary `themes={[...]}` arrays — no config surgery.

---

## Version Compatibility Matrix

| Package | Compatible With | Notes |
|---|---|---|
| `next-themes@^0.4.6` | `next@16.x`, `react@19.x` | Peer range covers React 18–19. No known Next 16 issues (Apr 2026). |
| `@tailwindcss/typography@^0.5.19` | `tailwindcss@^4` via `@plugin` directive only | Do NOT add to a (non-existent) `tailwind.config.js` — v4 reads it from CSS. |
| `react-markdown@^10` | `react@19` | v10 added React 19 support; v9 throws `React.Children` warnings. |
| `rehype-sanitize@^6` | `react-markdown@^10` (via `rehypePlugins`) | Use `defaultSchema` unless we need to whitelist `<table>` attributes beyond GFM. |
| `remark-gfm@^4` | `react-markdown@^10` | Pair with `rehype-sanitize` — GFM can emit raw HTML without it. |
| `@base-ui/react@^1.4.0` | `react@19`, `next@16` | Drawer stable ≥1.3.0 (Mar 2026). Popover/Dialog/Tooltip/PreviewCard stable since 1.0 GA (Dec 11, 2025). |
| `shadcn@^4.2.0` CLI | `style: "base-nova"` in `components.json` | Generates wrappers around `@base-ui/react`. Do not switch to `radix-*` styles. |
| `lightweight-charts@^5.1.0` | Runs inside Drawer content with no issues | Call `chart.remove()` in the Drawer's unmount effect to avoid dangling canvases. |
| `next/font/google` `Be_Vietnam_Pro` | Next 16 | `subsets: ["vietnamese", "latin"]` is required — default omits Vietnamese. |

---

## Sources

- [next-themes on npm](https://www.npmjs.com/package/next-themes) — v0.4.6 confirmed current, hydration behavior verified — HIGH confidence
- [pacocoursey/next-themes on GitHub](https://github.com/pacocoursey/next-themes) — release history, Tailwind v3.4+ selector-mode guidance — HIGH confidence
- [Base UI releases page](https://base-ui.com/react/overview/releases) — v1.4.0 (Apr 13, 2026), Drawer stable since v1.3.0, GA in v1.0.0 (Dec 11, 2025) — HIGH confidence
- Local inspection: `apps/helios/node_modules/@base-ui/react/` — confirms `drawer/`, `popover/`, `preview-card/`, `tooltip/`, `dialog/` directories present in installed 1.4.0 — HIGH confidence
- Local inspection: `apps/helios/components.json` — `"style": "base-nova"` locks primitive choice to Base UI + Nova density — HIGH confidence
- [Tailwind CSS v4 Dark Mode docs](https://tailwindcss.com/docs/dark-mode) — `@custom-variant dark` syntax — HIGH confidence
- [Tailwind CSS discussion #17405: Multi-theme with dark & light modes in v4](https://github.com/tailwindlabs/tailwindcss/discussions/17405) — pattern for `data-theme` + class variants — MEDIUM confidence
- [@tailwindcss/typography on npm](https://www.npmjs.com/package/@tailwindcss/typography) — v0.5.19 confirmed current, `@plugin` install path for v4 — HIGH confidence
- [Vercel Streamdown GitHub](https://github.com/vercel/streamdown) — v2.5.0 confirmed; considered and deferred to v1.2+ — MEDIUM confidence
- [react-markdown homepage](https://remarkjs.github.io/react-markdown/) — `components` override pattern for glossary tokens — HIGH confidence
- [rehype-sanitize readme](https://github.com/rehypejs/rehype-sanitize) — `defaultSchema` + DOM-clobber `user-content-` prefix — HIGH confidence
- [Be Vietnam Pro on Google Fonts](https://fonts.google.com/specimen/Be+Vietnam+Pro) — variable axes, Vietnamese diacritic design — HIGH confidence
- [Vietnamese Typography type recommendations](https://vietnamesetypography.com/type-recommendations/) — long-form diacritic legibility criteria — MEDIUM confidence
- [shadcnblocks: Vega/Nova/Maia/Lyra/Mira styles](https://www.shadcnblocks.com/blog/shadcn-component-styles-vega-nova-maia-lyra-mira/) — confirms `base-nova` = Base UI + Nova density — MEDIUM confidence
- [Claude brand colors on Mobbin](https://mobbin.com/colors/brand/claude) — warm terracotta (~oklch(0.70 0.14 45)) + cream (~oklch(0.97 0.02 70)) reference — MEDIUM confidence (palette is reverse-engineered from public UI, not an official brand spec)
- Existing `apps/helios/src/app/globals.css` — current theme variable structure preserved in the proposed diff — HIGH confidence
- Next.js 16 internal docs at `apps/helios/node_modules/next/dist/docs/01-app/02-guides/mdx.md` — confirmed MDX path adds non-trivial wiring; reinforces "skip MDX for this milestone" decision — HIGH confidence

---

*Stack research for: LocalStock v1.1 frontend polish (theme + drawer + academic page)*
*Researched: 2026-04-17*
