# Project Research Summary

**Project:** LocalStock v1.1 — UX Polish & Educational Depth
**Domain:** Frontend redesign of a Vietnamese stock market AI agent (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui)
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

LocalStock v1.1 is a **pure-frontend milestone** that transforms an existing dark-mode-only financial dashboard into a reading-first AI report experience. The four features — theme system, stock page redesign, academic/learning page, and interactive glossary linking — share a clear dependency chain and require zero backend changes. The existing stack (Next.js 16, @base-ui/react 1.4.0, Tailwind v4, shadcn/ui base-nova style, TanStack Query 5) is well-suited for all four features; only 5 new npm packages are needed (`next-themes`, `react-markdown`, `remark-gfm`, `rehype-sanitize`, `@tailwindcss/typography`), plus 3 shadcn component installs (Sheet, Tabs, Popover/HoverCard). The recommended approach is a typed TypeScript glossary module (not MDX/CMS) for ~25 entries, `react-markdown` for structured report rendering, and `next-themes` for FOUC-free theme switching.

The recommended build order follows the dependency chain: **Theme foundation first** (it touches `globals.css` and `layout.tsx` which every other feature depends on), then **stock page redesign** (creates the `AIReportView` component that glossary hooks into), then **academic/learning page** (produces the glossary data that glossary linking consumes), and finally **glossary linking** (requires both the report renderer and the glossary data). Content authoring (~25 glossary entries) should start in parallel with engineering from Phase 2 onward — it's the single biggest time cost (~50 hours for 50 entries, but a minimum viable set of 15-20 entries suffices for launch).

The key risks are: (1) **financial semantic tokens are dark-mode values sitting in `:root`** — they will render nonsensically when the warm-light theme activates unless audited and duplicated into both theme blocks; (2) **canvas-based charts (lightweight-charts) cannot follow CSS variable changes** — they require imperative `chart.applyOptions()` calls keyed to theme state; (3) **Vietnamese typography requires intentional font and line-height choices** — stacked diacritics clip at default line-height, and many popular fonts have poor Vietnamese coverage; (4) **glossary linking against LLM output is non-deterministic** — the same indicator appears in many surface forms across reports, requiring alias-based matching with Vietnamese-aware word boundaries. All four risks have well-documented mitigation strategies and should be addressed in Phase 1 (risks 1-3) and Phase 3-4 (risk 4).

## Key Findings

### Recommended Stack

The existing stack handles v1.1 without framework changes. Five new runtime/dev dependencies are needed, all battle-tested and React 19 / Next.js 16 compatible. The critical stack decision is to **stay within the Base UI primitive ecosystem** — do not introduce Radix UI, vaul, or any competing primitive library, as the project is locked to `base-nova` style via `components.json`.

**Core technologies:**
- **next-themes@^0.4.6**: Theme state management — injects an inline `<script>` before hydration to prevent FOUC; handles localStorage persistence and `<html>` class toggling. Use `attribute="class"`, `defaultTheme="claude"`, `enableSystem={false}`.
- **react-markdown@^10 + remark-gfm@^4 + rehype-sanitize@^6**: Replaces current `whitespace-pre-wrap` plain text rendering with structured Markdown. Enables GFM tables (LLM outputs these constantly), XSS sanitization on LLM output, and custom `components` overrides for glossary term injection.
- **@tailwindcss/typography@^0.5.19**: `prose` classes for reading-first AI reports — paragraph rhythm, list spacing, and blockquote tone for Vietnamese long-form content at `prose-lg` (~18px / 1.75 leading).
- **Be Vietnam Pro (via next/font/google)**: Vietnamese-optimized variable font — system fonts render Vietnamese stacked diacritics (`ế`, `ợ`, `ủ`) poorly. `subsets: ["vietnamese", "latin"]` required.
- **@base-ui/react (existing 1.4.0)**: Drawer, Popover, PreviewCard, and Tooltip primitives already installed. Use Drawer for right-side data panel, PreviewCard for hover glossary definitions.
- **Typed TS glossary module (not MDX)**: ~25 entries as a `Record<GlossaryCode, GlossaryEntry>` in `lib/glossary.ts`. Compile-time type safety on `seeAlso` links, zero new dependencies, shared by report renderer and academic pages.

**Explicitly rejected:** vaul, @radix-ui/*, @next/mdx, contentlayer/velite/nextra, streamdown, framer-motion, styled-components/emotion, prismjs/shiki, katex. See STACK.md for per-item rationale.

### Expected Features

**Must have (table stakes — v1.1 broken without these):**
- Theme persistence across reloads (localStorage via next-themes)
- No flash of wrong theme on load (inline blocking script)
- Theme toggle visible from every page (top-right header or sidebar)
- Stock page loads AI report first, not chart (the philosophy shift)
- Structured section rendering of AI reports (not `JSON.stringify`)
- Drawer open/close without breaking scroll position
- Glossary terms clickable (not hover-only — mobile has no hover)
- Academic page searchable with Vietnamese diacritic-insensitive matching
- Charts re-themed for warm mode (candle colors legible on cream)

**Should have (differentiators):**
- Claude-style warm cream (`oklch(0.97 0.02 70)`) + terracotta accent palette — unclaimed aesthetic in the stock tool space
- Right drawer with tabbed panels (Chart / Raw Data) — one drawer, tabs inside (Linear/Notion pattern)
- AI report auto-links known terms to glossary — client-side `react-markdown` component override on inline code tokens
- Hover card definitions with click-to-expand (PreviewCard for hover, Popover for tap/mobile)
- Drawer state persisted in URL search params (`?drawer=chart`) for shareable links and browser back support

**Defer to v1.2+:**
- Per-term live example charts in academic entries
- Keyboard shortcut system (single drawer toggle binding is fine for v1.1)
- In-drawer mini-chart preview on hover over dates/prices in report text
- Cross-linking between academic entries (only after content stabilizes)
- AI-powered "explain this simpler" button

### Architecture Approach

All four features are frontend-only and follow a clear dependency chain: Theme → Stock Page Redesign + Academic Page → Glossary Linking. The architecture adds **15 new components** and **modifies 8 existing components**, with 3 shadcn/ui installs (Sheet, Tabs, Popover/HoverCard) and 4 new route pages under `/learn`. The single most important architectural insight is that the **glossary data module (`glossary-data.ts`) is the shared spine** — it feeds both the academic/learning pages and the report term-linking system. It must be designed first even if populated incrementally.

**Major components:**
1. **ThemeProvider + ThemeToggle** — Client-side theme context wrapping `next-themes`; manages `<html>` class toggle between no-class (warm `:root`) and `.dark`. Chart colors updated imperatively via `chart.applyOptions()` keyed to `resolvedTheme`.
2. **AIReportView** — New component replacing `whitespace-pre-wrap` text dump. Renders `content_json` sections via `react-markdown` with glossary term injection through custom `components.code` override. This is the integration point for Features 2 and 4.
3. **StockDataDrawer** — shadcn Sheet (right-side, `position: fixed`) with internal Tabs (Chart / Data). Lazy-loads chart data via React Query `enabled: drawerOpen`. Existing PriceChart, SubPanel, TimeframeSelector components move inside largely unchanged.
4. **Glossary data module + linkify engine** — Typed `glossary.ts` with aliases per term; `glossary-linkify.ts` builds a compiled regex from all aliases (longest-first), scans report text in a single pass, wraps matches in `<GlossaryLink>` components. Runs at render time via remark plugin or react-markdown component override, not post-hoc DOM mutation.
5. **Academic/Learning pages** — Static Server Component routes at `/learn/[category]`, rendering `ConceptCard` components from the same glossary data. Category-based navigation (Technical / Fundamental / Macro).

### Critical Pitfalls

1. **Financial tokens are dark values in `:root`** — `--chart-bg: #0f172a` (dark navy) sits in `:root` because the app was always dark. When warm-light activates, every component reading `var(--chart-bg)` gets inverted colors. **Fix:** Audit every CSS variable; provide values in both `:root` (warm) and `.dark` blocks. Unify color spaces on oklch.

2. **Canvas charts ignore CSS/class changes** — `lightweight-charts` renders to `<canvas>` with colors set at `createChart()` time. Theme toggle changes nothing visually. **Fix:** Refactor `chart-colors.ts` from constants to `getChartColors(theme)` function. Add `useEffect` on `resolvedTheme` that calls `chart.applyOptions()` and `series.applyOptions()` — no chart destruction needed.

3. **Hardcoded Tailwind colors fail on light backgrounds** — `gradeColors` uses `text-green-400` (contrast 2.0:1 on cream), `text-yellow-400` (1.5:1 on cream). **Fix:** Replace with `text-green-700 dark:text-green-400` pattern or define grade colors as CSS variables in the theme matrix.

4. **LLM output surface forms are non-deterministic** — "RSI" appears as `RSI`, `chỉ số RSI`, `chỉ báo sức mạnh tương đối`, `Relative Strength Index` across reports. `MA` collides with Vietnamese words. **Fix:** Each glossary entry declares an alias list; match longest-first; require uppercase for ambiguous abbreviations; add LLM system prompt guidance to normalize forms. Build regression tests against 20-30 real reports.

5. **Glossary cold-start kills perceived quality** — Shipping glossary UI with 5 stub entries looks broken. **Fix:** Ship with ≥15 high-frequency entries (top 8 technical + 7 fundamental indicators). Build frequency list from actual report corpus. Start content authoring in parallel with engineering, not after.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Theme Foundation & Visual Identity
**Rationale:** Every subsequent feature renders differently per theme. Theme touches `globals.css`, `layout.tsx`, and the color pipeline — foundational files. Doing theme last would mean reworking every component twice.
**Delivers:** Warm-light default (Claude cream + terracotta) + preserved dark mode, FOUC-free toggle, theme-aware charts, contrast-passing financial tokens, Be Vietnam Pro font pipeline.
**Addresses:** Theme persistence, FOUC prevention, chart re-theming, grade badge contrast, warm palette, Vietnamese font — all P1 features from FEATURES.md.
**Avoids:** Pitfalls #1 (FOUC), #2 (token inversion), #3 (canvas charts), #4 (hardcoded colors), #5 (WCAG contrast).
**Files:** `globals.css` (major), `layout.tsx` (major), new `theme-provider.tsx` / `theme-toggle.tsx`, `chart-colors.ts` (major refactor), `utils.ts`, `grade-badge.tsx`, `price-chart.tsx`, `sub-panel.tsx`, `sidebar.tsx`.
**Estimate:** 3-4 days (including palette tuning and contrast verification).

### Phase 2: Stock Page Reading-First Redesign
**Rationale:** Creates the `AIReportView` component that Phase 4 hooks into. Drawer component is the backbone for on-demand data access. Must happen before glossary linking because the report renderer is the injection point for term links.
**Delivers:** AI report full-width above the fold, right-side drawer with Chart/Data tabs, structured section rendering via react-markdown, lazy chart data loading, drawer state in URL params.
**Addresses:** Report-first layout, drawer component, structured report rendering, drawer URL state, scroll preservation, lazy data loading — core differentiator features.
**Avoids:** Pitfalls #6 (eager chart loading), #9 (broken deep links), #10 (scroll position), #11 (Vietnamese typography), #12 (chart dimensions in drawer).
**Uses:** react-markdown, remark-gfm, rehype-sanitize, @tailwindcss/typography (new deps installed in Phase 1), Sheet + Tabs (shadcn installs).
**Estimate:** 3-4 days.

### Phase 3: Academic/Learning Page + Glossary Content
**Rationale:** Produces the glossary data module that Phase 4 consumes. Content authoring is the single biggest time cost — starting it here (parallel with engineering) ensures ≥15 entries are ready when glossary linking ships. Academic pages also validate the glossary data schema before it's wired into reports.
**Delivers:** `/learn` route with Technical/Fundamental/Macro category pages, glossary data module (`glossary-data.ts` or `glossary.ts`), ConceptCard components, diacritic-insensitive client-side search, sidebar nav expansion ("Học Thuật").
**Addresses:** Academic page skeleton, glossary content authoring, client-side search, sidebar navigation.
**Avoids:** Pitfall #14 (glossary cold-start — content ships with infrastructure).
**Implements:** Static content architecture (typed TS arrays, not MDX). FormulaBlock + InterpretationGuide components for visual learning aids.
**Estimate:** 2-3 days engineering + 3-5 days content authoring (parallel track).

### Phase 4: Interactive Glossary Linking
**Rationale:** Must be last — depends on both AIReportView (from Phase 2) and glossary-data.ts (from Phase 3). This is the "tie it together" feature that connects AI reports to educational content.
**Delivers:** Term auto-detection in AI reports via react-markdown component override, PreviewCard hover definitions (desktop), Popover tap definitions (mobile), "Xem chi tiết →" navigation to academic pages, first-occurrence-only linking to avoid hyperlink clutter.
**Addresses:** Interactive term linking, hover preview + click-through, cross-referencing between reports and learning content.
**Avoids:** Pitfalls #7 (LLM surface forms — alias-based matching), #8 (DOM mutation — remark plugin instead), #13 (tooltip dismissal — use PreviewCard/Popover, not Tooltip).
**Uses:** @base-ui/react PreviewCard + Popover (existing), glossary-linkify.ts (new pure function).
**Estimate:** 2-3 days (including matcher regression testing against real reports).

### Phase Ordering Rationale

- **Theme first because it's foundational:** Every CSS variable, every component color, every chart is affected. Building anything on the old dark-only styling means rework.
- **Stock page before academic page:** The stock page redesign creates the `AIReportView` component and installs react-markdown. Academic pages can then reuse the same Markdown renderer for style parity. However, these two phases have minimal code overlap and could partially overlap if needed.
- **Content authoring starts in Phase 3 but continues through Phase 4:** The glossary data module is defined in Phase 3 (schema + initial 15+ entries). Additional entries can be added during Phase 4 without blocking engineering.
- **Glossary linking is strictly last:** It depends on both the report renderer (Phase 2) and the glossary data (Phase 3). Attempting it earlier means building against components that don't exist yet.
- **This ordering also groups pitfalls naturally:** Phase 1 handles all 5 theme-related pitfalls. Phase 2 handles all 4 layout/drawer pitfalls. Phase 3-4 handle all 4 glossary pitfalls. Scope creep (Pitfall #15) is a process discipline across all phases.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Chart re-theming):** The `chart.applyOptions()` approach for lightweight-charts v5 theme switching needs validation with the actual chart code. Verify that series colors (candle up/down, volume alpha) update correctly without chart destruction. Also verify Be Vietnam Pro Vietnamese diacritic rendering at actual report text sizes.
- **Phase 4 (Glossary matcher):** Vietnamese-aware word boundary regex (`(?<![\p{L}])` with `u` flag) needs testing against real LLM report corpus. The alias list per term needs to be built empirically from actual reports, not guessed. Consider running matcher on last 30 reports to measure recall before shipping.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Stock page redesign):** shadcn Sheet + Tabs is a well-documented pattern; existing React Query hooks provide all data; layout restructure is CSS/JSX work with no unknowns.
- **Phase 3 (Academic page):** Static content pages with typed data arrays — the simplest possible content architecture. No API integration, no build pipeline, no unknowns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified against npm as of Apr 2026; existing codebase inspected directly; version compatibility matrix confirmed. No speculative choices. |
| Features | HIGH | Feature landscape well-defined by existing competitive analysis (Seeking Alpha, Linear, Claude.ai); prioritization grounded in actual codebase state (what exists vs what's missing). |
| Architecture | HIGH | All 4 features use established patterns within the existing stack. No new backend work. Component inventory verified against actual `src/` file tree. |
| Pitfalls | HIGH | 15 pitfalls grounded in verified codebase reading (actual file contents cited); mitigation strategies reference specific APIs and patterns. Recovery costs assessed realistically. |

**Overall confidence:** HIGH

### Gaps to Address

- **next-themes vs hand-rolled theme provider:** ARCHITECTURE.md flags next-themes as an anti-pattern (unnecessary dependency for 2 themes), while STACK.md and PITFALLS.md both recommend it strongly (handles the tricky inline blocking script and hydration warning correctly). **Recommendation: Use next-themes.** The 2kB cost is trivially justified by eliminating the FOUC edge cases that a hand-rolled solution inevitably hits. The inline `<script>` timing is subtle and next-themes has been battle-tested for 3+ years.

- **Exact drawer width:** 420px? 480px? 560px? Depends on minimum readable chart width inside the drawer. Current PriceChart uses ResizeObserver and should adapt, but need to verify that a ~450px-wide candlestick chart is still legible. **Resolve during Phase 2 implementation** with real chart data.

- **Glossary entry count:** FEATURES.md estimates 50 entries (~50 hours), ARCHITECTURE.md says 30-40, STACK.md says ~25. **Recommendation:** Start with 15-20 high-frequency entries (the terms that appear in >50% of reports), ship as MVP, add more incrementally. Build the frequency list by grepping actual LLM report output.

- **Vietnamese serif font for report body:** FEATURES.md suggests serif for AI reports (Claude/Stratechery pattern), STACK.md recommends Be Vietnam Pro (a sans-serif font). **Recommendation:** Use Be Vietnam Pro as the primary body font (verified Vietnamese diacritic support) and defer serif exploration to v1.2. Serif Vietnamese fonts with good diacritic coverage are rare and need per-font testing.

- **`lightweight-charts` v5 `applyOptions()` live color update:** Confirmed supported in the API, but not yet tested against the actual `price-chart.tsx` code which creates multiple series (candle, volume, SMA lines). Verify in Phase 1 that all series types accept runtime color updates without flicker.

## Sources

### Primary (HIGH confidence)
- Local codebase inspection: `package.json`, `components.json`, `globals.css`, `layout.tsx`, `chart-colors.ts`, `utils.ts`, `price-chart.tsx`, `sub-panel.tsx`, `stock/[symbol]/page.tsx`, `sidebar.tsx`, `app-shell.tsx`, `queries.ts`
- [next-themes on GitHub](https://github.com/pacocoursey/next-themes) — v0.4.6 behavior, inline script FOUC prevention, hydration warning handling
- [Base UI releases](https://base-ui.com/react/overview/releases) — v1.4.0 (Apr 13, 2026), Drawer stable since v1.3.0
- [Tailwind CSS v4 Dark Mode docs](https://tailwindcss.com/docs/dark-mode) — `@custom-variant dark` syntax
- [@tailwindcss/typography on npm](https://www.npmjs.com/package/@tailwindcss/typography) — v0.5.19 with `@plugin` directive for v4
- [react-markdown](https://remarkjs.github.io/react-markdown/) — custom `components` override pattern for glossary tokens
- [rehype-sanitize](https://github.com/rehypejs/rehype-sanitize) — `defaultSchema` for XSS hardening on LLM output
- [Be Vietnam Pro on Google Fonts](https://fonts.google.com/specimen/Be+Vietnam+Pro) — Vietnamese-optimized variable font
- [lightweight-charts theme tutorial](https://tradingview.github.io/lightweight-charts/tutorials/customization/chart-colors) — `applyOptions` for dynamic updates
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) — WCAG 4.5:1 requirements

### Secondary (MEDIUM confidence)
- [Tailwind CSS discussion #17405](https://github.com/tailwindlabs/tailwindcss/discussions/17405) — multi-theme pattern with `data-theme` + class variants
- [Claude brand colors on Mobbin](https://mobbin.com/colors/brand/claude) — warm terracotta + cream reference (reverse-engineered, not official spec)
- [Vietnamese Typography recommendations](https://vietnamesetypography.com/type-recommendations/) — stacked diacritic line-height guidance
- [shadcn Claude theme](https://www.shadcn.io/theme/claude) — community-maintained shadcn tokens matching Claude palette
- Competitive analysis: Seeking Alpha, Morningstar, Simply Wall St, Linear, Notion, Claude.ai — layout patterns, drawer UX, glossary approaches

### Tertiary (LOW confidence)
- Exact glossary entry count and authoring time — varies by depth; 15 entries is safe MVP, 50 is aspirational for v1.1
- Serif font choice for Vietnamese body text — candidates identified but not rendering-tested

---
*Research completed: 2026-04-17*
*Ready for roadmap: yes*
