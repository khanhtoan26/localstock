# Feature Research — LocalStock v1.1 UX Polish

**Domain:** Reading-first AI stock analysis (personal tool, Vietnamese market, single-user web dashboard)
**Researched:** 2026-04-17 (updated 2026-04-18 with codebase-specific implementation analysis)
**Confidence:** HIGH (drawing on well-documented patterns from Seeking Alpha, Linear, Notion, ChatGPT/Claude, Investopedia, shadcn/ui, next-themes + verified against actual codebase)

> **Note:** This file has been replaced from its v1.0 version to reflect the v1.1 milestone. The v1.0 feature landscape (data crawling, scoring, LLM reports, Telegram alerts) is preserved in `.planning/PROJECT.md` under Validated requirements. This research is scoped strictly to v1.1 UX polish: theme system, stock-page redesign, academic/glossary page.

## Framing: What This Milestone Is Actually About

v1.1 is a **UX redesign milestone**, not a feature-addition milestone. The backend produces the exact same Vietnamese AI reports, rankings, and charts as v1.0 — the question is purely how those artifacts are presented to the one reader (the owner).

Three feature clusters, each with its own feasibility profile:

1. **Theme system** (warm-light default + dark toggle) — smallest cluster, highest table-stakes density
2. **Stock page reading-first redesign** (center AI report + right drawer) — largest cluster, core differentiator
3. **Academic/Learning + interactive glossary** — medium cluster, mostly content work plus a light interaction layer

Everything below is scoped to "what must work" vs "what's differentiating" vs "what to deliberately avoid" for a **personal-use reading tool**, not a multi-tenant SaaS.

## Codebase State (Verified)

Critical context for implementation planning — what exists today vs what's missing:

| Area | Current State | Impact on v1.1 |
|------|---------------|----------------|
| **Theme mechanism** | `className="dark"` hardcoded on `<html>` in `layout.tsx`; no toggle exists | Must install `next-themes`, add ThemeProvider, remove hardcoded class |
| **CSS variables** | `:root` uses oklch (neutral grey light), `.dark` uses hsl (financial dark); two different color systems | Warm theme replaces `:root` values; consider unifying on oklch for both themes |
| **Financial semantic tokens** | Hardcoded hex in `:root` CSS (`--stock-up: #22c55e`) — NOT theme-aware | Must make these CSS vars respond to `.dark` class, not just hardcode one set |
| **Chart colors** | `chart-colors.ts` exports hardcoded hex constants for dark theme only | `lightweight-charts` takes JS config objects, NOT CSS vars — needs a hook/context that returns theme-appropriate colors |
| **Grade badge colors** | `utils.ts` `gradeColors` uses dark-only Tailwind classes (`text-green-400`, `bg-green-500/20`) | Must create theme-aware variants; green-400 on cream background reads differently |
| **Report rendering** | `summary \|\| JSON.stringify(content_json, null, 2)` with `whitespace-pre-wrap` | `content_json` has 9 structured sections (summary, technical_analysis, etc.) — reading-first needs section-by-section rendering |
| **Drawer/Sheet component** | **NOT installed** — no shadcn Sheet in `components/ui/` | Must add via `npx shadcn@latest add sheet` |
| **HoverCard component** | **NOT installed** | Must add via `npx shadcn@latest add hover-card` |
| **Tabs component** | **NOT installed** | Must add via `npx shadcn@latest add tabs` |
| **next-themes** | **NOT installed** | Must `npm install next-themes` |
| **MDX pipeline** | **NOT configured** — no `@next/mdx`, `contentlayer`, or `next-mdx-remote` | Must set up MDX rendering for academic content |
| **Sidebar nav** | Two items: "Xếp Hạng" + "Thị Trường" | Add "Học Thuật" nav item |
| **shadcn style** | `base-nova` style, `neutral` base color | Warm theme changes base color semantics |
| **Stock page layout** | header → chart → timeframe → MACD/RSI → AI report → scores (chart-first) | Complete layout inversion needed — report first, chart in drawer |
| **StockReport API** | Returns `content_json` as `Record<string, unknown>` with 9 Pydantic fields | Frontend can render structured sections (not just raw text) |

## Feature Landscape

### Table Stakes (Users Expect These)

Features the owner assumes exist. Missing any of these makes v1.1 feel broken, even though nothing new is added to the product surface.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Theme persistence across reloads** | Every modern app remembers theme choice via `localStorage`; re-picking on every reload is immediately annoying | LOW (hours) | `next-themes` handles this out of the box with Next.js 16; set `attribute="class"`, `storageKey="localstock-theme"` |
| **No flash of wrong theme on load (FOUC)** | Reading app; bright flash on dark preference is jarring | LOW (hours) | `next-themes` injects a pre-hydration script in `<head>`; set `suppressHydrationWarning` on `<html>`. Currently `layout.tsx` hardcodes `className="dark"` — must remove and let `next-themes` manage the class. This is THE main reason to use the library vs rolling your own |
| **System preference auto-detect (first visit)** | 2025+ convention: respect `prefers-color-scheme` until user overrides | LOW (hours) | Owner explicitly wants warm-light as default, but auto-detect is still table stakes — offer "System" as a selectable option. `defaultTheme="light"` (warm) with "System" available in the toggle |
| **Theme toggle visible from every page** | Reader can't hunt for a setting; location must be consistent | LOW (hours) | Current `AppShell` has no header bar — sidebar only. Add a top bar or place toggle in sidebar header (near "LocalStock" branding). Top-right of global header is 2026 convention (shadcn docs, Vercel, Linear, GitHub) |
| **Readable body typography at comfortable line length** | AI reports are the product; unreadable body = product broken | LOW (hours) | `max-width: 65–75ch` for prose, `line-height: 1.7`, 16–18px base. Claude.ai uses serif for body; consider it for reports specifically |
| **Stock page loads AI report first, not chart** | Philosophy shift from v1.0; if the chart is still visually dominant the redesign failed | LOW (layout work) | Current page layout in `stock/[symbol]/page.tsx`: header → PriceChart → TimeframeSelector → SubPanel (MACD/RSI) → AI Report card → Score card. Must invert: header → AI report (full-width) → Score summary → "Open data" buttons. Chart components (PriceChart, SubPanel, TimeframeSelector) move into drawer |
| **Render AI report with structured sections, not raw text** | Report has 9 distinct sections (summary, technical_analysis, etc.) but is rendered via `summary \|\| JSON.stringify(content_json)`. Reading-first must show each section with its own heading | LOW-MEDIUM | Parse `content_json` keys → render as sections with Vietnamese headings. Map: `technical_analysis` → "📈 Phân Tích Kỹ Thuật", `recommendation` → "💡 Khuyến Nghị", etc. |
| **Drawer open/close without breaking scroll position** | Standard drawer behavior (Linear, Notion, Gmail); losing scroll place mid-article is infuriating | LOW (hours) | shadcn `Sheet` handles this; must install first (`npx shadcn@latest add sheet`). Avoid custom drawer |
| **Drawer closeable via Escape key** | Universal modal/drawer convention (WCAG + Radix default) | LOW (free with shadcn `Sheet`) | Do not disable this — shadcn/ui's Sheet component gives it for free |
| **Drawer doesn't re-fetch data on every open** | Chart/raw data only needs to load once per stock page visit | LOW | Current React Query hooks (`useStockPrices`, `useStockIndicators`) already have `staleTime: 60min`. Mount drawer content lazily on first open, keep mounted after that (React state, not remount on toggle) |
| **Glossary terms clickable, not just hoverable** | Mobile has no hover; keyboard users need focus; clicking should always work | LOW (hours) | shadcn `HoverCard` supports focus/click (must install: `npx shadcn@latest add hover-card`). Pattern: hover shows preview, click opens drawer or navigates to academic page |
| **Academic page searchable** | Any glossary with >20 entries needs search; owner won't memorize every term's URL | LOW (hours) | Client-side fuzzy search (Fuse.js or `cmdk`) over a static JSON/MDX index. No backend endpoint needed |
| **Vietnamese diacritic-insensitive search** | Vietnamese owner searching "RSI" or "chỉ báo" — Fuse.js without normalization misses "chi bao" → "chỉ báo" | LOW-MEDIUM (hours) | Normalize both index and query via `.normalize('NFD').replace(/[\u0300-\u036f]/g, '')` before fuzzy match |
| **Keyboard shortcut to toggle drawer** | Reading tool; hand on keyboard. Linear, Notion, VS Code all have this | LOW (~1 hour) | Single binding (e.g., `\` or `]`) is enough — owner will use it, or won't; don't over-invest in a shortcut system |
| **Mobile: drawer becomes bottom sheet or full-screen overlay** | Right drawer makes no sense on 375px viewport; reading layout breaks | LOW (shadcn Sheet handles `side="right"` → swap to `side="bottom"` on mobile via conditional prop) | Even though "no mobile" is out-of-scope, owner likely opens this on phone occasionally. Don't break it; don't optimize it |
| **Links in AI report open academic page in new tab or drawer, not navigate away** | User is reading the report; losing reading position is the cardinal sin | LOW | Open in drawer (preferred, preserves report scroll) or `target="_blank"`. Never replace current page |

### Differentiators (Competitive Advantage for a Personal Tool)

For a personal tool, "differentiator" means "what makes using this more pleasant than the generic alternative." Not competing with Seeking Alpha; competing with "just reading a text file" or "using generic shadcn defaults."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Claude-style warm cream + terracotta theme as default** | Signals "this is a reading experience, not a trading terminal"; aligns with philosophy shift | MEDIUM (days) | Claude's palette: `oklch(0.97 0.02 70)` cream bg, `oklch(0.70 0.14 45)` terracotta accent. Current `:root` uses oklch neutrals (0 chroma), `.dark` uses hsl — must update `:root` to warm oklch values. Requires auditing: (1) `gradeColors` in `utils.ts` uses dark-theme Tailwind classes, (2) `chart-colors.ts` hardcoded dark-only colors, (3) financial semantic tokens in CSS are theme-unaware, (4) candle red/green must still read on cream background |
| **Serif typography for AI report body, sans for UI chrome** | Strongest single signal that this is "report" not "dashboard"; Stratechery, Claude, Substack all do this | LOW (hours) | Next.js `next/font` with a Vietnamese-supporting serif (e.g., Source Serif 4, Lora, Noto Serif). MUST verify Vietnamese diacritics render correctly — many serifs have poor Vietnamese coverage |
| **Right drawer with tabbed panels** (Chart / Raw Data / News) | One drawer, three contents — avoids drawer-per-data-type complexity; mirrors Linear's "one right panel, tabs inside" pattern | MEDIUM (1–2 days) | Must install shadcn `Sheet` + `Tabs` components (neither exists yet). Move existing PriceChart, SubPanel, TimeframeSelector into drawer's Chart tab. Raw Data tab uses existing `useStockTechnical` + `useStockFundamental` hooks. Drawer state (open/closed/active-tab) in URL search params (`?panel=chart`) so links are shareable and browser back works |
| **Hover card definitions with click-to-expand** | Investopedia-style: hover = brief tooltip, click = full academic page in drawer or new tab | LOW-MEDIUM (1 day + content) | shadcn `HoverCard`. 150-char max preview. Click → navigate to `/academic/[term]` OR open academic drawer. Recommend: click opens drawer with full content, preserving report scroll position |
| **AI report auto-links known terms** | Owner doesn't have to manually wrap every "RSI" in a component; a client-side transform does it | MEDIUM (day) | Client-side approach: during report rendering, run a regex-replace pass over text nodes against glossary term list, wrapping matches in `<TermLink>`. Current report is plain text via `whitespace-pre-wrap` — transition to a custom renderer that processes `content_json` section-by-section and applies term linking per section. Avoid linking inside code blocks, headings, or already-linked text. Longest-match-first to handle multi-word Vietnamese terms |
| **Drawer content persists across navigation within same stock session** | Opening chart in VNM page → clicking to VCB → drawer stays "chart" tab, just for VCB | LOW (hours) | Store active tab in URL param, not component state. Drawer content (the actual chart data) refetches per stock — only the UI state persists |
| **"Reading mode" line-length and max-width tuned for AI reports** | Most dashboards use 100% width tables; AI reports are prose and need 65–75ch | LOW (CSS) | Simple: wrap report content in `max-w-prose` (Tailwind) or custom `65ch` container. Keep drawer outside the max-width |
| **Glossary content as MDX, not a CMS** | Owner is sole author; no editorial workflow needed; MDX gives inline charts/examples in definitions | LOW (setup) + MEDIUM (content authoring time) | ~50–100 terms. Store in `apps/helios/content/academic/*.mdx`. Setup is minutes; writing the content is the actual work |
| **Academic entry supports live example chart** | Learning RSI? Show live RSI for FPT inline. MDX makes this a one-liner | MEDIUM (per-entry) | Import existing chart components into MDX. Be selective — not every term needs a live chart; prioritize the 10–15 most-referenced ones |
| **Three-way theme toggle: Warm / Dark / System** | Clearer than light/dark binary when "light" is a named theme ("Warm") | LOW (shadcn dropdown + next-themes) | Dropdown with three options + icons (sun, moon, monitor). Named themes are clearer than "light/dark" when the light theme has personality. Label: "Ấm" / "Tối" / "Hệ thống" for Vietnamese UI consistency |
| **In-drawer mini-chart preview on hover over date/price in report** | Claude artifact-style: AI mentions "spike on March 15" → tiny sparkline or price pin appears on hover | HIGH (days) | Premium touch, defer unless Phase 3 ahead of schedule. Requires parser to identify dates/prices in report text |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like they "should" be in a polish milestone but will drain weeks without improving the core reading experience.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **CMS / admin UI for glossary authoring** | "Proper" glossary tools (Contentful, Sanity) for a single-user tool | Adds auth, deployment, backend complexity for 50 markdown files the owner will edit once | MDX files in git. Edit in VS Code. Commit. Done. |
| **Multiple independent drawers** (one for chart, one for news, one for data) | "More flexibility" | Z-index wars, state management explosion, Linear/Notion all settled on ONE drawer with tabs for a reason | Single drawer, Tabs inside |
| **Animated theme transitions (morphing, ripple-from-click)** | Delight, trending on Dribbble | Slows down theme switch perceptibly; motion sickness for some; extra JS bundle; owner switches theme ~once then never again | Instant switch. If anything, a 150ms opacity fade on `body`. `View Transitions API` is overkill here |
| **Real-time collaborative glossary edits** | Inherited from SaaS thinking | Single-user tool; no collaboration exists | N/A — don't build |
| **Per-report custom themes / color picker** | "Maximum customization" | Two well-designed themes > ten mediocre ones; maintenance burden on every new component | Warm + Dark only |
| **Infinite-scroll academic page** | Modern feed UX | Glossary is reference material, not a feed; user wants to FIND a term, not browse | Alphabetized list + search + category filter (Kỹ thuật / Cơ bản / Vĩ mô / Sentiment) |
| **Gamified learning paths ("complete 10 indicators to earn badge")** | Robinhood-style engagement | Owner is not a beginner needing engagement loops; reference material, not course | Plain content. Add table-of-contents per category |
| **Drawer that opens automatically on page load** | "Make data discoverable" | Defeats the entire point of reading-first redesign — report is hidden behind drawer immediately | Drawer closed by default. Ensure "Mở biểu đồ" / "Xem dữ liệu" buttons are obviously clickable |
| **Full TradingView chart embed in drawer** | "Why reinvent?" | Heavyweight iframe, cold-load delay, theming conflicts with cream, no AI-report cross-reference integration | Continue with existing `lightweight-charts` v5 setup — just needs re-theming for warm mode |
| **Markdown preview/edit UI for reports** | "Let me tweak the AI output" | Reports are generated content, not authored; editing breaks reproducibility | If edit is needed, edit the generator prompt, not the output |
| **Per-term AI explainer ("ask AI to explain RSI for my context")** | LLM-era expectation | Introduces 5–15s LLM latency into reading flow; owner already has LLM locally for reports, but adding it to every term = slow glossary + prompt engineering for 50 terms | Write definitions manually once. MDX allows rich examples. Outcome: instant, consistent |
| **Drawer width user-resizable with drag handle** | Power-user flex | Extra state, layout math, edge cases on small viewports; owner picks one good width and never resizes | Fixed drawer width (e.g., 420–480px on desktop). Configurable via CSS var if owner wants to change once |
| **Theme toggle inside every page (multiple entry points)** | "Accessibility" | Confusing; two toggles desync if not careful; one in header is universal convention | Single toggle, global header, top-right |
| **Tooltip glossary WITHOUT click-through to full term page** | "Minimalist" | Preview ≠ full definition; owner will want the full page when term is complex | Hover preview AND click-through — both |
| **Four themes (warm-light, cream-dark, true-dark, high-contrast)** | Theming rabbit hole | 4 themes = 4x the visual QA on every new component | Two themes: "Ấm" (Warm) and "Tối" (Dark). Named clearly |

## Feature Dependencies

```
[Theme system foundation]
    ├──enables──> [Claude-style warm theme]
    ├──enables──> [Dark theme preservation]
    └──enables──> [Chart re-theming for warm mode]

[Right drawer component] (shadcn Sheet wrapper)
    ├──enables──> [Chart-on-demand]
    ├──enables──> [Raw data-on-demand]
    ├──enables──> [News-on-demand]
    └──enables──> [Glossary term click-through drawer]

[Academic MDX content] (~50 terms written)
    └──requires──> [MDX pipeline in Next.js 16]
           └──enables──> [Glossary hover cards with real content]
                   └──enables──> [AI report auto-link terms]

[Stock page reading-first layout]
    ├──requires──> [Right drawer component]
    ├──requires──> [Theme system foundation] (palette affects layout hierarchy)
    ├──enhances──> [AI report typography (serif, max-width)]
    └──enhances──> [Interactive glossary in report]

[Glossary hover card component]
    ├──requires──> [Academic MDX content] (HARD — empty hovercard is worse than no hovercard)
    ├──requires──> [Term index / lookup mechanism]
    └──enhances──> [AI report reading experience]

[Keyboard shortcut for drawer]
    └──requires──> [Right drawer component]

[URL-persisted drawer state (?panel=chart)]
    └──requires──> [Right drawer component]
    └──enables──> [Shareable deep-links to stock + drawer view]
```

### Dependency Notes

- **Glossary hover cards require academic MDX content:** Shipping interactive term links before the definitions exist produces empty hovercards — worse UX than plain text. **Academic content must land before or with glossary interactivity**, not after. This is the single most important ordering constraint for the roadmap.
- **Chart re-theming depends on theme foundation:** `lightweight-charts` v5 uses its own theme API, not CSS vars. The current `chart-colors.ts` exports hardcoded hex constants consumed directly in `PriceChart` and `SubPanel` `createChart()` calls. When theme system ships, charts must switch to a hook/context pattern: `useChartTheme()` returns resolved colors based on current theme, passed to `chart.applyOptions()`. The financial semantic tokens in CSS (`:root { --stock-up }`) and the `CHART_COLORS` constants are a dual source of truth that should be unified. Doing theme first, then chart refactor, is cheap; doing them simultaneously is risky.
- **Drawer component blocks everything in stock page redesign:** This is the backbone — shadcn Sheet + Tabs must be installed first (`npx shadcn@latest add sheet tabs`), then build a clean, reusable `<StockDetailDrawer>` with Tabs inside. The existing `PriceChart`, `SubPanel`, and `TimeframeSelector` components move into the drawer's Chart tab largely unchanged (they already render into a container div).
- **AI report auto-linking enhances but doesn't require interactive glossary:** Term auto-link can ship as plain internal links (navigating to `/academic/[term]`) first, then upgrade to hover-card previews once MDX content and `HoverCard` wrapper are in place. Two-phase upgrade is safer than one-shot. Note: current report rendering is raw text — the auto-link pass requires switching from `whitespace-pre-wrap` text to a structured renderer that processes `content_json` section-by-section.
- **Serif typography enhances reading-first redesign:** Can ship independently (just a font swap), but impact is maximized when layout has already shifted to prose-centric max-width.
- **Theme persistence and system detection are table stakes of the theme system itself:** Do not ship "warm theme" without persistence — it'll be re-picked every reload.

## MVP Definition

For v1.1, "MVP" means **the minimum that delivers the philosophy shift** ("insight is central, data is secondary") without adding net-new data functionality.

### Launch With (v1.1 target)

- [ ] **Theme system: Warm (default) + Dark + System, persisted, no FOUC, top-right global toggle** — without this, the "warm reading" identity doesn't exist; also the smallest cluster, should land first
- [ ] **shadcn Sheet-based right drawer on stock page, single drawer with 3 tabs (Chart, Raw Data, News)** — backbone of the reading-first redesign; every downstream feature depends on it
- [ ] **Stock page default layout: AI report full-width (max-w-prose) above the fold, drawer closed** — the philosophy made visible
- [ ] **Serif body typography for AI report content with Vietnamese diacritic coverage verified** — signal that this is a report, not a dashboard
- [ ] **Charts re-themed for warm mode** (candle colors, grid, crosshair legible on cream) — otherwise charts break the theme identity
- [ ] **Academic page at `/academic` with ~50 core terms** (top indicators, ratios, macro concepts) as MDX, client-side search with diacritic-insensitive matching — without content, interactive glossary is an empty shell
- [ ] **Interactive term linking in AI reports: hover preview (HoverCard) + click opens full term in drawer or navigates to academic page** — the "tie it together" feature; depends on the prior item
- [ ] **Drawer state in URL search params (`?panel=chart`)** — makes the drawer a first-class page mode; free browser back button support

### Add After Validation (v1.1.x / v1.2)

- [ ] **Keyboard shortcut for drawer toggle** — 1-hour job, defer to end of milestone or v1.1.x
- [ ] **Per-term live example charts in academic entries** — high-value but per-term authoring cost; do top 10 terms post-MVP
- [ ] **Cross-linking between academic entries** ("RSI thường được so sánh với → MACD") — only once core content stabilizes
- [ ] **Drawer content preserves last-viewed tab across stocks** — polish that only matters if drawer is heavily used

### Future Consideration (v2+)

- [ ] **Intraday data in drawer** — depends on out-of-scope v2 intraday data crawling
- [ ] **AI-powered "explain this section in simpler terms" button** — novelty, not core
- [ ] **Portfolio/watchlist personalization with per-stock reading progress** — out-of-scope of "tool, not SaaS"
- [ ] **Mobile-first rethink (bottom sheet, swipe gestures)** — PROJECT.md explicitly says web dashboard is enough
- [ ] **Markdown/MDX editor UI for academic content** — not worth building; VS Code + git is fine

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Theme system foundation (Warm + Dark + System, persisted, FOUC-free) | HIGH | LOW | **P1** |
| Warm Claude-style palette (tokens in Tailwind v4 + shadcn vars) | HIGH | MEDIUM | **P1** |
| Chart re-theming for warm mode | HIGH | MEDIUM | **P1** |
| Right drawer component (shadcn Sheet + Tabs) | HIGH | LOW-MEDIUM | **P1** |
| Stock page reading-first layout (report full-width, drawer closed) | HIGH | LOW | **P1** |
| Serif typography for report body (Vietnamese-capable font) | HIGH | LOW | **P1** |
| Academic page skeleton + MDX pipeline | HIGH | LOW | **P1** |
| 50 core glossary MDX entries (the actual content writing) | HIGH | HIGH | **P1** |
| Client-side search with diacritic normalization | HIGH | LOW | **P1** |
| HoverCard definitions on terms in AI report | HIGH | MEDIUM | **P1** |
| Term click → drawer or academic page | HIGH | LOW | **P1** |
| Drawer state persisted in URL search params | MEDIUM | LOW | **P1** |
| Keyboard shortcut for drawer toggle | MEDIUM | LOW | **P2** |
| Live example charts in top-10 academic entries | MEDIUM | MEDIUM | **P2** |
| Cross-linking between academic entries | MEDIUM | LOW | **P2** |
| Drawer last-viewed tab persisted across stocks | LOW | LOW | **P2** |
| "Explain this in simpler terms" AI button | LOW | HIGH | **P3** |
| Custom theme color picker | LOW | HIGH | **P3** |
| CMS admin UI for glossary | LOW | HIGH | **P3** (anti-feature) |

**Priority key:**
- **P1:** Must have for v1.1 to deliver the philosophy shift
- **P2:** Should have, add in v1.1.x sprints
- **P3:** Defer to v2+ or skip entirely (includes anti-features)

## Competitor Feature Analysis

| Feature | Seeking Alpha | Morningstar | Simply Wall St | Linear / Notion | Claude.ai | Our Approach |
|---------|---------------|-------------|----------------|-----------------|-----------|--------------|
| **Reading layout** | Article center, ratings+stats sidebar right (sticky) | Company report as a PDF-ish section embedded in quote page | Infographic-heavy "Snowflake" one-pager, report as a flow of visuals | N/A (not financial) | Chat center, artifact panel right | AI report center (max-w-prose), drawer right (on-demand) |
| **Data-on-demand** | Always-visible sidebar (ratings, key stats) | Inline "Read full report" expand | Visuals always inline, no hiding | Right drawer with one context at a time | Artifact panel opens on demand | Right drawer closed by default, tabbed Chart/Data/News |
| **Glossary / term definitions** | Links to dedicated explainer articles (separate site area) | Inline italic term + footnote-style definitions | Hover tooltips on key metrics in Snowflake | N/A | Inline links in responses | HoverCard preview + click to open in drawer or /academic |
| **Theme system** | Light + Dark toggle, top-right, icon only | Light only (!) | Light + Dark, hidden in settings | Three-way (light/dark/system) dropdown | Light only (warm), no dark | Three-way (Warm/Dark/System), top-right, named dropdown |
| **Keyboard shortcuts** | Minimal | None visible | None visible | Extensive (`?` key for cheatsheet, `[` to toggle sidebar) | Minimal (`/` for new) | Minimal: one toggle-drawer shortcut, Esc to close |
| **Typography for long reading** | Sans-serif body, no special reading mode | Sans-serif, dense | Sans-serif, infographic-first | Sans (it's an app, not reading) | Serif body for responses | Serif for report body, sans for UI chrome |
| **Drawer interaction** | N/A (always-visible sidebar) | N/A (inline) | N/A (inline) | Click issue → slide in from right, Tabs inside, Esc closes, URL updates | Click artifact button → slide in from right, single-content | Click "Show chart" button → slide from right, tabbed, Esc closes, URL updates |
| **Content source for long-form** | Contributor-authored articles | Analyst-written PDFs | Auto-generated from data | N/A | AI-generated in chat | AI-generated by Prometheus, rendered as MDX/markdown |

**Key takeaways for LocalStock v1.1:**

- **Nobody in finance currently does "reading-first with drawer" well.** Seeking Alpha, Morningstar, Simply Wall St all have always-visible data panels. The closest analog is Claude/ChatGPT artifact panels or Linear issue panels — which is why the philosophy shift is genuinely differentiated for a stock tool. (Not that LocalStock competes with them — but the pattern is proven; it just hasn't been applied to this domain.)
- **Financial glossary UX is table stakes, not a differentiator.** Every serious platform has hover/inline definitions. Skipping this while positioning as an "insight-first" tool would be inconsistent.
- **The warm theme is the single most distinctive visual signature.** Every other platform is either pure-finance-dark (Bloomberg) or default-light-sans (Morningstar). Claude-style warm serif is unclaimed in the stock space.

## Domain-Specific Considerations (Vietnamese Market)

| Consideration | Impact | Action |
|---------------|--------|--------|
| **Font Vietnamese diacritic coverage** | Many serifs (e.g., Charter, some Playfair weights) have gaps on Vietnamese characters like `ế`, `ờ`, `ử` | Test candidates: Source Serif 4, Noto Serif, Lora; Inter for UI. Verify with sample `"Thị trường chứng khoán Việt Nam"` plus sample AI report paragraph |
| **No good Vietnamese finance glossary exists online** | Shinhan Securities has one but it's scattered and not interactive; no TradingView-equivalent glossary for Vietnamese | Owner's academic page becomes a genuinely useful artifact for the owner's own future reference |
| **Search must handle ASCII-fold** | Typing "chi bao ky thuat" should find "chỉ báo kỹ thuật" | Normalize NFD + strip combining marks before fuzzy match, index-side and query-side both |
| **Term linking must handle Vietnamese word boundaries** | Regex `\bRSI\b` works for ASCII; Vietnamese multi-word terms ("chỉ số P/E", "hệ số thanh khoản") need careful matching | Use a term list sorted by length descending; match longest first; prefer exact-string match over word-boundary regex. Avoid inside code blocks, headings, or already-linked nodes |
| **AI report text is mixed Vietnamese + English tickers** (e.g., "Chỉ số RSI của FPT đang ở mức 65") | Term-link pass must handle mixed-language content | Same long-match-first approach works; test with actual report samples before shipping |
| **Vietnamese typography nuances** | Diacritics stack tall; overly tight line-height clips them | Use `line-height: 1.7` minimum for body; verify on actual reports not just Latin samples |

## Complexity Estimates (Codebase-Aware)

For roadmap decomposition — these are "one engineer, focused" estimates, not team-days. Updated with actual codebase file counts and dependencies.

| Feature cluster | Engineering | Content/Design | Total | Files Impacted |
|----------|-------------|----------------|-------|----------------|
| Theme system foundation + toggle | 4–6h | 1h | ~1 day | `layout.tsx`, `globals.css`, new `ThemeProvider`, new `ThemeToggle`, `sidebar.tsx` or new header |
| Warm palette + token design + shadcn var override | 4h | 4–8h (palette tuning) | ~1–2 days | `globals.css` (`:root` vars), `chart-colors.ts`, `utils.ts` (gradeColors) |
| Chart re-theming for warm + dark | 4–8h | 2h | ~1 day | `chart-colors.ts` → `useChartTheme` hook, `price-chart.tsx`, `sub-panel.tsx` |
| Right drawer component (Sheet + Tabs + URL state) | 6–10h | 1h | ~1–2 days | New `Sheet` + `Tabs` shadcn installs, new `StockDetailDrawer`, `stock/[symbol]/page.tsx` |
| Stock page layout shift (report-first) | 4h | 2h | ~1 day | `stock/[symbol]/page.tsx` (major rewrite), new `ReportSections` renderer for `content_json` |
| Serif font pipeline + Vietnamese verification | 2h | 1h (sampling) | ~0.5 day | `layout.tsx` (next/font), `globals.css` (font-family) |
| Academic page skeleton + MDX + search | 6–8h | 1h | ~1 day | `next.config.ts` (MDX plugin), new `/academic` route, new `content/` dir, `sidebar.tsx` (nav item) |
| 50 glossary MDX entries (content writing) | 1h/term × 50 | — | **~50 hours = 6–7 days** (the biggest single cost) | `content/academic/*.mdx` (50 files) |
| HoverCard wrapper + term auto-link transform | 8–12h | 1h | ~1.5 days | New `HoverCard` shadcn install, new `TermLink` component, new `term-linker` utility, report renderer |
| Drawer keyboard shortcut | 1h | — | negligible | `stock/[symbol]/page.tsx` (useEffect keydown) |
| Integration, theming polish, QA across routes | 8–16h | — | ~1–2 days | All pages: `rankings/page.tsx`, `market/page.tsx`, component files |

**Total rough estimate:** ~16–20 engineer-days. The glossary content is the single dominant cost — roadmap should treat it as its own parallel track.

## Sources

- [Seeking Alpha stock article sidebar pattern](https://stockanalysis.com/article/seeking-alpha-review/) — always-visible ratings/stats sidebar
- [Morningstar company report layout](https://www.morningstar.com/help-center/stocks/company-reports) — Read Full Report entry, structured sections (Bulls/Bears, Fair Value, Moat)
- [Simply Wall St visual-first approach](https://stockunlock.com/simply-wall-st-review.html) — Snowflake infographic, visual-first reports
- [Linear board/drawer shortcuts](https://linear.app/docs/board-layout) — `[` to toggle sidebar, Esc to close drawers
- [Notion side peek pattern](https://www.notion.com/releases/2022-07-20) — side/center/full-page as three opening modes, default configurable
- [ChatGPT Canvas / Claude Artifacts side panel pattern](https://venturebeat.com/ai/openai-launches-chatgpt-canvas-challenging-claude-artifacts) — chat on left, artifact on right, on-demand
- [Claude.ai design system: warm cream + terracotta + serif](https://design-foundations.com/domains/claude-ai) — `oklch(0.97 0.02 70)` cream, `oklch(0.70 0.14 45)` terracotta, classic serif body
- [shadcn Claude theme](https://www.shadcn.io/theme/claude) — community-maintained shadcn theme tokens matching Claude's palette
- [next-themes library (FOUC-free theme system for Next.js)](https://github.com/pacocoursey/next-themes) — canonical solution in 2026
- [shadcn theme-switcher button with Sun/Moon/Monitor](https://www.shadcn.io/button/theme-switcher) — dropdown with three-way switcher
- [shadcn HoverCard vs Tooltip discussion](https://github.com/shadcn-ui/ui/discussions/2417) — HoverCard for rich previews, Tooltip for short labels
- [Robinhood Learn educational UX](https://learn.robinhood.com/) — embedded micro-learning in complex tools, not gamification-first
- [Investopedia-style tooltip glossary pattern](https://www.uxpin.com/studio/blog/what-is-a-tooltip-in-ui-ux/) — 150-char preview, click-through to full page
- [Tailwind v4 dark mode docs](https://tailwindcss.com/docs/dark-mode) — `class` strategy, `@media (prefers-color-scheme)` fallback
- [Best practices for dark mode 2026](https://natebal.com/best-practices-for-dark-mode/) — soft blacks (#121212), different primary colors per theme, SVG images
- [Shinhan Securities Vietnamese glossary reference](https://shinhansec.com.vn/en/investment-knowledge/2/cac-thuat-ngu-trong-chung-khoan-danh-cho-nha-dau-tu-moi.html) — Vietnamese finance terms exist but scattered
- [Dark Mode UX Guide 2025](https://altersquare.medium.com/dark-mode-vs-light-mode-the-complete-ux-guide-for-2025-5cbdaf4e5366) — 2025-era conventions

---

## Confidence & Gaps

**HIGH confidence:**
- Drawer pattern (shadcn Sheet + Tabs) — universal pattern, well-documented, Helios already uses shadcn `base-nova` style with Radix primitives
- Theme system (`next-themes` + Tailwind v4 + shadcn vars) — canonical 2026 stack; Tailwind v4's `@custom-variant dark (&:is(.dark *))` already configured in `globals.css`
- Warm palette values (Claude's published `oklch` values are public)
- MDX for content (standard Next.js 16 pattern, low risk)
- "One drawer with tabs" vs "multiple drawers" — every mature product settled on single drawer
- Report structured data available — `StockReport` Pydantic model has 9 cleanly separated sections; frontend just needs to render them properly instead of JSON.stringify
- React Query hooks already exist for all data types — drawer content can use existing `useStockPrices`, `useStockIndicators`, `useStockTechnical`, `useStockFundamental`

**MEDIUM confidence:**
- Specific term-matching algorithm for Vietnamese auto-link — need to validate regex vs trie approach with real report samples; edge cases around "P/E" (slash), "ROE" (acronym), "chỉ số giá tiêu dùng" (long multi-word)
- Serif font choice — list of candidates is known, but actual Vietnamese-diacritic rendering must be tested per-font before committing
- Exact drawer width (420? 480? 560?) — depends on how much chart info must be legible inside; current `PriceChart` uses `width: containerRef.current.clientWidth` via ResizeObserver — should adapt to drawer width automatically, but need to verify 400px-ish chart is still readable
- `lightweight-charts` v5 theming API — current code uses `createChart()` with inline color objects; must verify `chart.applyOptions()` can dynamically update colors on theme switch without chart re-creation

**LOW confidence / gaps:**
- Whether owner will actually use a keyboard shortcut for drawer. Recommend shipping one simple binding (`\` or `]`) and not investing in a full shortcut system until usage is observed.
- Exact count of "core" glossary terms — 50 is an estimate. Could be 30 (table stakes only) or 80 (including macro). Recommend starting with a shortlist derived from actual AI report content: grep existing reports for indicator names and rank by frequency.
- Whether drawer should be modal-ish (blocks report interaction) or side-by-side (allows simultaneous scroll). Linear uses side-by-side at wide viewports. Recommend: shadcn Sheet with `modal={false}` at `≥1280px` for side-by-side, default modal below.
- MDX pipeline choice for Next.js 16 — `@next/mdx`, `next-mdx-remote`, or `contentlayer2`. Need to verify which supports Next.js 16's RSC model best. `@next/mdx` is simplest but requires file-based content; `next-mdx-remote` supports dynamic loading.

**Research flags for roadmap:**
- The **"Academic content authoring" phase is the single biggest time risk** — content writing is easy to underestimate, and it blocks interactive glossary. Treat as its own phase or parallel track.
- **Chart re-theming** requires a refactor of `chart-colors.ts` from static constants to a theme-reactive pattern. The `PriceChart` component's `useEffect` currently creates the chart on mount with hardcoded colors — adding theme reactivity means either re-creating the chart on theme switch or calling `chart.applyOptions()`.
- **Vietnamese serif verification** is a small task that can derail aesthetics if skipped — fold into theme-foundation phase, not left for polish.
- **Report renderer refactor** is a hidden dependency — switching from `whitespace-pre-wrap` text dump to structured section rendering is prerequisite for both the reading-first layout AND the term auto-linking. Budget this explicitly.
- **`gradeColors` in `utils.ts`** uses `text-green-400` / `bg-green-500/20` patterns that assume dark background. Must be theme-aware; consider using shadcn semantic tokens instead of raw Tailwind color utilities.

*Feature research for: LocalStock v1.1 reading-first UX redesign*
*Researched: 2026-04-17*
