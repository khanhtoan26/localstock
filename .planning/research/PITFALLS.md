# Pitfalls Research — LocalStock v1.1 UX Polish & Educational Depth

**Domain:** Adding theme toggle, layout redesign, educational content, and glossary linking to an existing dark-only Next.js 16 + Tailwind v4 + shadcn/ui financial dashboard
**Researched:** 2026-04-17
**Confidence:** HIGH (grounded in verified codebase reading + current library documentation)

## Codebase State Inventory (verified, not assumed)

Before listing pitfalls, here is the exact state of the code that each pitfall references:

| File | Current State | Why It Matters |
|------|---------------|----------------|
| `layout.tsx` | `<html lang="vi" className="dark">` hardcoded, no ThemeProvider | Theme switch requires removing this and adding a provider |
| `globals.css` `:root` | Uses `oklch(1 0 0)` values (pure white/near-white) — shadcn default light | Never actually rendered because `dark` class is always on |
| `globals.css` `.dark` | Uses `hsl(222.2 84% 4.9%)` etc. — actual theme in use | Different color space from `:root` (hsl vs oklch) |
| `globals.css` financial tokens | `--stock-up: #22c55e`, `--chart-bg: #0f172a` etc. in `:root` only | Dark values sitting in `:root` — will be used as light-mode values when dark class removed |
| `chart-colors.ts` | All hex constants (`#0f172a`, `#22c55e` etc.), no theme awareness | Canvas charts cannot read CSS variables; need imperative color switching |
| `price-chart.tsx` | `useEffect` depends on `[prices, indicators]` only | Theme changes won't trigger chart re-creation or color update |
| `sub-panel.tsx` | Same pattern as `price-chart.tsx` | Same problem × 2 chart instances (MACD + RSI) |
| `utils.ts` `gradeColors` | `text-green-400`, `text-blue-400`, `text-red-400` — arbitrary Tailwind colors | These are not CSS-variable-based; green-400 on cream fails contrast |
| `error-state.tsx` | `text-red-400` hardcoded | Same contrast issue on light backgrounds |
| Stock page | Charts at top, AI report card below with `max-h-[400px]` ScrollArea | Reading-first redesign inverts this entire layout |
| AI report rendering | `whitespace-pre-wrap` plain text, `{summary \|\| JSON.stringify(content_json)}` | No Markdown parser exists yet; glossary requires one |
| `components.json` | `"style": "base-nova"` | Newer shadcn style — component internals differ from `new-york`/`default` |
| Dynamic imports | `PriceChart` and `SubPanel` use `next/dynamic({ ssr: false })` | Load-bearing pattern; lightweight-charts crashes in SSR |
| AppShell | `ml-60` fixed left margin for sidebar | Layout changes must preserve or adapt this spacing |

---

## Critical Pitfalls

### Pitfall 1: Theme flash (FOUC) because server can't read localStorage

**What goes wrong:**
Server renders `<html className="dark">` (current hardcoded value). After hydration, client-side code reads `localStorage('theme')` → finds `'light'` → toggles class. User sees a dark-to-light flash for 100–400ms. Alternatively, if the new default is warm-light: server renders without `dark` class, but user previously chose dark, and they see a light flash before dark activates. Both paths also risk a React hydration error: `"Prop 'className' did not match. Server: 'dark' Client: ''"`.

**Why it happens:**
`localStorage` doesn't exist on the server. `layout.tsx` is a Server Component in Next.js 16 App Router. Without a blocking inline script that runs before React hydration, the server and client will disagree on the initial class.

**How to avoid:**
- Use `next-themes` (2kB) with `attribute="class"`, `defaultTheme="light"` (warm-light is the new default per PROJECT.md)
- Add `suppressHydrationWarning` to the `<html>` element — this is the **only** element where this attribute is acceptable
- Remove the hardcoded `className="dark"` from `layout.tsx` — let `next-themes`'s inline blocking script set the class before React hydrates
- `next-themes` injects a `<script>` before `</head>` that synchronously reads `localStorage` and sets the class — this script is the critical FOUC prevention mechanism; do not replace it with a `useEffect`
- For server-side theme awareness (e.g., generating correct OG images), persist theme to cookie on change and read via `await cookies()` (async in Next.js 16)

**Warning signs:**
- Visible flicker on hard refresh (throttle to Slow 3G to make it obvious)
- Console: `"Hydration failed because the initial UI does not match..."`
- Lighthouse CLS score regresses

**Phase to address:** Phase 1 (Theme foundation). **Gate:** Hard-refresh 10× on Slow 3G → zero flashes, zero hydration warnings in console.

---

### Pitfall 2: Financial semantic tokens are dark values placed under `:root` — theme switch inverts their meaning

**What goes wrong:**
`globals.css` line 122–129 defines financial tokens under `:root`:
```css
:root {
  --stock-up: #22c55e;    /* green — correct for dark bg */
  --chart-bg: #0f172a;    /* slate-900 — IS the dark background */
  --chart-grid: #1e293b;  /* slate-800 */
  --chart-text: #94a3b8;  /* slate-400 */
}
```
These are dark-theme values. They sit in `:root` because the app was always dark. When light theme is introduced, `:root` becomes the *light* context. Now `--chart-bg: #0f172a` means "light-mode chart background is dark navy" — the exact opposite of intent. Any component reading `var(--chart-bg)` gets nonsensical colors.

The second `:root` block also has no `.dark` counterpart for these tokens, so there's no mechanism to give them different values per theme.

**Why it happens:**
When building a dark-only app, `:root` and `.dark` blur together. The team added financial tokens to `:root` knowing the `dark` class on `<html>` would cascade everything. Nobody needed light-mode variants because light mode didn't exist.

**How to avoid:**
- **Audit every CSS variable in globals.css.** Every token must appear in BOTH `:root` (warm-light values) AND `.dark` (current dark values)
- Move the financial tokens block into the theme matrix:
  ```css
  :root {
    --stock-up: #15803d;     /* green-700 — 6:1 contrast on cream */
    --stock-down: #b91c1c;   /* red-700 — 5.4:1 on cream */
    --chart-bg: #faf8f5;     /* cream — matches warm-light */
    --chart-grid: #e7e0d5;   /* warm gray */
    --chart-text: #57534e;   /* stone-600 */
  }
  .dark {
    --stock-up: #22c55e;     /* current value, good on dark */
    --stock-down: #ef4444;
    --chart-bg: #0f172a;
    --chart-grid: #1e293b;
    --chart-text: #94a3b8;
  }
  ```
- Stock up/down must remain green/red in both themes (financial convention), but darkened for light backgrounds to meet 4.5:1 contrast
- **Color space consistency:** `:root` shadcn tokens use `oklch`, `.dark` uses `hsl`. Pick one. `oklch` is preferred (Tailwind v4 default, perceptually uniform) — convert `.dark` values to oklch too

**Warning signs:**
- Any component that looks correct in one theme but broken in the other
- `getComputedStyle(document.documentElement).getPropertyValue('--chart-bg')` returns a dark color when theme is light

**Phase to address:** Phase 1 (Theme foundation) — token matrix audit before any component work.

---

### Pitfall 3: lightweight-charts renders to `<canvas>` and cannot reactively follow CSS variables or class changes

**What goes wrong:**
`price-chart.tsx` calls `createChart()` inside `useEffect` with dependencies `[prices, indicators]`. Chart colors come from `CHART_COLORS` (hardcoded hex constants). When user toggles theme:
1. Theme class changes → Tailwind/shadcn components update correctly
2. Chart stays dark navy because nothing re-invokes the effect
3. Result: dark chart rectangle embedded in a cream page — looks completely broken

**Why it happens:**
Canvas-based libraries don't participate in CSS cascade. They receive pixel-level color values at creation time. The `useEffect` dependency array doesn't include theme, so theme changes are invisible to chart code.

**How to avoid:**
- Refactor `chart-colors.ts` from a constant object to a function: `getChartColors(theme: 'light' | 'dark'): ChartColorSet`
- In chart components, use `const { resolvedTheme } = useTheme()` from `next-themes`
- **Best approach:** Add a separate `useEffect` that depends only on `[resolvedTheme]` and calls `chart.applyOptions({ layout: { background, textColor }, grid: { ... } })` — this updates chart colors WITHOUT destroying/recreating the chart (lightweight-charts v5 supports `applyOptions` for live updates)
- Also update series colors: `candleSeries.applyOptions({ upColor, downColor, ... })`, `volumeSeries.applyOptions(...)` etc.
- **Don't** destroy and recreate the chart on theme toggle — this causes visible flicker and loses zoom/scroll state
- Apply same fix to `SubPanel` (MACD and RSI charts)
- Special attention: volume alpha values (`#22c55e40`) — the `40` hex alpha (25% opacity) may be too faint on cream. Use different alpha per theme

**Warning signs:**
- Toggle theme → chart stays previous color
- Volume bars vanish in one theme
- `CHART_COLORS` imported as a constant (not from a function) anywhere

**Phase to address:** Phase 1 (Theme foundation). **Gate:** On `/stock/VNM`, toggle theme → all 3 charts (price, MACD, RSI) repaint within 200ms without destroying chart instances.

---

### Pitfall 4: `gradeColors` in utils.ts uses hardcoded Tailwind classes that fail contrast on light backgrounds

**What goes wrong:**
`utils.ts` line 36–42:
```typescript
export const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  B: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  C: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  F: "bg-red-500/20 text-red-400 border-red-500/30",
};
```
`text-green-400` (#4ade80) on cream (#faf8f5) = ~2.0:1 contrast ratio. `text-yellow-400` on cream is even worse (~1.5:1). These badges become unreadable in light mode.

Same issue: `error-state.tsx` uses `text-red-400` hardcoded.

**Why it happens:**
`-400` shade Tailwind colors are designed for dark backgrounds. On light backgrounds, you need `-600` or `-700` shades. The existing code never needed to consider this.

**How to avoid:**
- Replace hardcoded color classes with theme-aware variants using `dark:` prefix:
  ```typescript
  A: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  ```
- OR better: define grade colors as CSS variables in the theme matrix and use semantic classes
- Audit every instance of `text-{color}-400` in the codebase — all are suspect on light backgrounds
- Use same approach for `error-state.tsx`: `text-red-700 dark:text-red-400`

**Warning signs:**
- Grade badges appear "washed out" or invisible in light mode
- `text-{color}-400` appears in `rg` results outside of `.dark` context

**Phase to address:** Phase 1 (Theme foundation) — part of the hardcoded-color audit sweep.

---

### Pitfall 5: Warm-light orange accent fails WCAG contrast on cream backgrounds

**What goes wrong:**
"Claude warm-light" aesthetic uses cream background (~`#f5f0e8`) with orange accent (~`#c96442`–`#d97757` range). Used as body text or small icon tint on cream, typical orange lands at 3.0:1–4.0:1 contrast — passes for large text (18pt+) but **fails WCAG AA for body text** (requires 4.5:1).

Additionally, `#22c55e` (current stock-up green) on cream = ~2.1:1 contrast, far below any threshold. The entire rankings table becomes hard to read.

**Why it happens:**
Warm palettes are tonally compressed. Orange-on-cream passes the "vibes" test but fails the numbers test. Developers test in dark mode (habit from v1.0) and switch to light mode last.

**How to avoid:**
- Use two shades of accent orange: "display" (brand-correct, for button backgrounds where foreground adjusts) and "text" (darker, hits 4.5:1 on cream)
- For stock colors in light mode: green-700 (`#15803d`, ~6:1 on cream), red-700 (`#b91c1c`, ~5.4:1)
- Run every token pair through `WebAIM Contrast Checker` before committing the palette
- Tailwind v4's oklch makes programmatic contrast checking easier — use `oklch` lightness channel to verify
- Consider automated contrast testing: `axe-core` via Playwright on key pages in both themes

**Warning signs:**
- Anyone says "feels a little washed out" in light mode
- `axe-core` reports contrast violations

**Phase to address:** Phase 1 (Theme foundation). Every palette choice verified before moving to Phase 2.

---

### Pitfall 6: Drawer refactor eager-loads chart data when drawer is closed (wasting bandwidth and regressing TTI)

**What goes wrong:**
Current stock page fires `useStockPrices`, `useStockIndicators`, `useStockScore`, `useStockReport` on mount — all four in parallel. After redesign, if the drawer is closed by default (reading-first intent), chart data fetches are wasted. `/api/prices/VNM?days=365` returns a full year of daily OHLCV data — significant payload for content the user hasn't requested.

The inverse trap: lazy-loading on drawer open but showing empty space for 2 seconds with no loading indicator.

**Why it happens:**
React Query makes eager fetching easy. The existing code already does it. "Don't change what isn't broken" instinct preserves the eager pattern even when the layout no longer warrants it.

**How to avoid:**
- Use React Query's `enabled` option: `useStockPrices(symbol, days, { enabled: drawerOpen })`
- Keep `useStockScore` and `useStockReport` eager — these drive the main page content
- On drawer open: render `<Skeleton>` immediately, fetch begins, render on data ready
- Prefetch on hover/focus intent: when user hovers the "Biểu đồ" tab for >150ms, fire `queryClient.prefetchQuery(...)` — gives instant-feel open
- **Measure:** On cold page load, Network tab should show only `/scores/` and `/reports/` requests. `/prices` and `/indicators` should fire only after drawer interaction

**Warning signs:**
- Lighthouse TTI regresses vs v1.0
- `/api/prices/:symbol?days=365` appears in Network on every `/stock/*` navigation

**Phase to address:** Phase 2 (Reading-first layout). **Gate:** Network tab audit on cold load — no chart data requests.

---

### Pitfall 7: LLM output is non-deterministic — glossary terms appear in many surface forms

**What goes wrong:**
Ollama generates Vietnamese reports. The same indicator appears as: `RSI`, `chỉ số RSI`, `chỉ báo RSI`, `chỉ báo sức mạnh tương đối`, `Relative Strength Index`, `RSI (Relative Strength Index)`, `rsi`. A naive exact-string matcher catches only one form. Worse: `MA` matches the Vietnamese word "ma" (ghost), "mà" (but/which), "mã" (code/stock ticker prefix) — creating false positives across all reports.

LLM surface forms also drift between Ollama model updates, so a matcher tested today may fail silently next month.

**Why it happens:**
Developers think of glossaries as static dictionaries. LLM output is free text with paraphrase, mixed-language, varying casing, and Vietnamese diacritics.

**How to avoid:**
- Define each glossary entry with a **list of surface forms** (aliases):
  ```typescript
  { id: "rsi", canonical: "Chỉ báo RSI", aliases: ["RSI", "chỉ số RSI", "chỉ báo RSI", "sức mạnh tương đối", "Relative Strength Index"] }
  ```
- Use Vietnamese-aware word boundaries. Default `\b` is ASCII-only. Use `(?<![\p{L}])` and `(?![\p{L}])` with the `u` flag
- For ambiguous abbreviations like `MA` (collides with common Vietnamese words): require uppercase-only match AND context (`MA\s*\d+` → "MA 20"), or avoid auto-linking and rely on LLM system prompt to emit full form
- **LLM prompt engineering:** Add to system prompt: `"Khi nhắc đến chỉ báo kỹ thuật, luôn viết dạng đầy đủ kèm viết tắt, ví dụ: 'chỉ báo RSI (Relative Strength Index)'"` — normalizes surface forms at source
- Build regression test: 20–30 real report samples, measure recall per term, fail if below 80%
- Normalize before matching: lowercase, NFC (not NFD — NFC keeps Vietnamese diacritics intact), collapse whitespace

**Warning signs:**
- Glossary link count varies wildly between reports (some have 12 links, others 0)
- `MA` linking inside Vietnamese words or names
- Glossary worked last week but matches nothing after Ollama model update

**Phase to address:** Phase 3 (Glossary). Matcher design is the first subtask, before any UI. **Gate:** Recall ≥80% on real report corpus.

---

### Pitfall 8: Client-side DOM mutation for glossary linking fights React and breaks SSR

**What goes wrong:**
Developer renders report with `react-markdown`, then adds a `useEffect` that walks the DOM with `TreeWalker`, runs regex on text nodes, wraps matches in `<a>` tags. Problems:
1. Initial paint shows plain text; links "pop in" after hydration — visible flash
2. Mutating DOM React owns triggers reconciliation warnings
3. Text inside code blocks or blockquotes gets linked (unwanted)
4. Tooltip positioning fails because anchors didn't exist at React render time

**Why it happens:**
DOM mutation is the "easy" path that works on any rendered content without understanding the render pipeline. But it violates React's ownership model.

**How to avoid:**
- Write a **remark plugin** that runs during the Markdown→HAST transformation. The plugin visits text nodes, splits them into text + glossary-link nodes at transform time
- This runs once at render time (server or with `useMemo`) — not as post-hoc DOM mutation
- Skip matching inside `code`, `pre`, `blockquote` nodes — the remark visitor checks parent node type
- Render glossary links as a custom React component via `react-markdown`'s `components` prop: `components={{ a: GlossaryLink }}`
- Memoize transformed output on `(reportText, glossaryVersion)` — reports don't change per render
- Result: SSR-correct output (links present at first paint), zero hydration mismatch

**Warning signs:**
- `useEffect` containing `document.querySelectorAll` or `TreeWalker` in report renderer
- Links flicker in after initial render
- Console warnings about DOM mutations outside React's control

**Phase to address:** Phase 3 (Glossary). Architecture decision logged at phase start: remark plugin, not DOM mutation.

---

### Pitfall 9: Reading-first layout breaks existing deep links from Telegram bot

**What goes wrong:**
v1.0 stock page lives at `/stock/VNM`. The drawer refactor introduces UI state: drawer open/closed, which panel is showing (chart/data/news). Developer implements drawer state as local `useState` — bookmarks to "open chart for VNM" are impossible. Or: developer changes URL structure to `/s/VNM`, breaking the Telegram bot's daily digest messages that link to `/stock/:symbol`.

**Why it happens:**
Local state is faster to implement than URL state. "Nobody bookmarks this" reasoning ignores Telegram message history as external references.

**How to avoid:**
- Keep `/stock/:symbol` route **unchanged** — verify via grep that the Python backend Telegram module links to this path
- Drawer state in URL search params: `?drawer=chart|data|news|closed`; use `useSearchParams` + `router.replace({ scroll: false })`
- Default (no param) = drawer closed = reading-first view — **this IS the design intent**
- Any future URL change requires redirect rules in `next.config.ts` AND migration of Telegram bot templates

**Warning signs:**
- Refreshing page closes the drawer user had open
- Telegram bot links land on unexpected view or 404
- Browser back button doesn't undo drawer open/close

**Phase to address:** Phase 2 (Reading-first layout). URL contract decided before implementing drawer.

---

### Pitfall 10: Scroll position lost when drawer opens/closes

**What goes wrong:**
User scrolls halfway through the AI report (paragraph 5 of a long analysis), clicks "Xem biểu đồ" to peek at chart. Drawer opens → main scroll jumps to top, or layout reflow shifts content. User loses reading position. On close, same problem in reverse.

Mobile variant: drawer/sheet calls `document.body.overflow = 'hidden'`, which on iOS Safari resets scroll position.

**Why it happens:**
Drawers that change main column width cause reflow. Modal scroll-lock on mobile uses `position: fixed` on body, which discards scroll position.

**How to avoid:**
- Desktop: drawer is `position: fixed` on the right side — do NOT change main column width. Main column scroll is untouched
- Mobile: use `vaul` (underlying shadcn Drawer) — it handles iOS scroll-lock via techniques that preserve position
- **Test:** On `/stock/VNM`, scroll to ~50% of report → open drawer → close drawer → scroll position unchanged (±10px). Test on iOS Safari specifically
- If drawer pushes content on desktop, save/restore `scrollTop` explicitly — but prefer overlay approach

**Warning signs:**
- Clicking drawer trigger visibly scrolls the page
- Closing drawer puts user at page top
- iOS Safari scroll feels "sticky" after drawer interactions

**Phase to address:** Phase 2 (Reading-first layout). Scroll preservation is an explicit acceptance criterion.

---

### Pitfall 11: Vietnamese typography with stacked diacritics looks cramped at default line-height

**What goes wrong:**
Tailwind's `leading-relaxed` (1.625) is tuned for Latin text. Vietnamese has stacked diacritics (`ế`, `ỗ`, `ậ` — tone mark + vowel mark) that sit above the normal ascender line. At 1.625, these marks touch or overlap descenders from the line above. The reading-first layout amplifies this: long Vietnamese prose, full-width, tight line-height = visually noisy.

The current `whitespace-pre-wrap` rendering makes this worse because soft-wraps happen at arbitrary points.

**Why it happens:**
Default typography is English-first. Designers who don't read Vietnamese can't spot the overlap visually.

**How to avoid:**
- Line-height ≥ 1.75 for Vietnamese body text: `leading-[1.75]` or `leading-loose`
- Use a Vietnamese-optimized font: **Be Vietnam Pro** (Google Font, designed for Vietnamese diacritics) via `next/font/google`; `display: 'swap'` default avoids FOIT
- Replace `whitespace-pre-wrap` plain text rendering with `react-markdown` — gives proper paragraph rendering with appropriate spacing
- Reading measure: 65–75ch per line (same as Latin); Vietnamese "short words" don't warrant wider columns
- Remove the `font-family: system-ui, -apple-system, sans-serif` hardcoded in `globals.css` `body` rule — let `next/font` variable take over via Tailwind's `font-sans`

**Warning signs:**
- Vietnamese reader says "rối mắt" (visually noisy) or "khó đọc" (hard to read)
- Diacritics visually overlap at zoom or on Windows (heavier font hinting)

**Phase to address:** Phase 2 (Reading-first layout). Typography pass uses real LLM output samples, not Lorem Ipsum. Native Vietnamese reader reviews before declaring done.

---

### Pitfall 12: Dynamic chart import inside an animating drawer gets wrong container dimensions

**What goes wrong:**
Charts use `next/dynamic({ ssr: false })` and measure `containerRef.current.clientWidth` at creation. When moved inside a drawer that animates open (slide-in transition), the chart creates during the animation when the container is at intermediate width (e.g., 0px → 400px transition). Chart renders at 0px or 200px width, then drawer finishes animating to 400px — chart doesn't resize because `ResizeObserver` may not fire for the initial animation.

**Why it happens:**
Dynamic imports resolve asynchronously. The chart component may mount and measure during any point of the drawer's CSS transition. `ResizeObserver` is not guaranteed to fire for CSS animations on all browsers.

**How to avoid:**
- Delay chart creation until drawer animation completes: use `onAnimationEnd` or `transitionend` callback to set `chartReady` state, chart effect depends on it
- OR: create chart with `autoSize: true` option (lightweight-charts v5 supports this) — delegates sizing to the library's internal ResizeObserver
- OR: use `requestAnimationFrame` after drawer open state settles to trigger a manual `chart.applyOptions({ width: container.clientWidth })`
- Simplest: defer the dynamic import entirely — don't even load `PriceChart` until `drawerFullyOpen` is true

**Warning signs:**
- Chart appears as a thin sliver or invisible when drawer first opens
- Chart width doesn't match drawer width
- Chart only sizes correctly on second open (after being cached in memory)

**Phase to address:** Phase 2 (Reading-first layout). Test specifically: first-ever drawer open on a stock page → chart fills drawer width correctly.

---

### Pitfall 13: Glossary tooltip dismisses before user can click "see full entry" link

**What goes wrong:**
Desktop design uses `Tooltip` component for glossary definitions. User hovers a term, tooltip appears with definition + "Xem chi tiết →" link. User moves cursor toward the tooltip — tooltip dismisses because cursor left the trigger element. User can never reach the link.

On mobile: no hover at all. Tap does nothing, or navigates somewhere unexpected.

**Why it happens:**
shadcn/Radix `Tooltip` is designed for **non-interactive** hover hints. It explicitly docs that it "is for sighted mouse users" and doesn't support interactive content. Using it for glossary definitions with clickable links is an API misuse.

**How to avoid:**
- Use `HoverCard` (desktop: hover-to-open, content stays open when cursor moves to it) paired with `Popover` fallback for touch/keyboard
- Detect input modality: `window.matchMedia('(hover: hover)')` to pick component at runtime
- Alternative: always use `Popover` (tap/click to open on all devices) — simpler, more predictable
- "See full entry" navigates to `/academic/[term]` — route, don't nest complex interactive content
- For positioning: use Radix's built-in `collisionPadding` — don't hand-roll math
- Keyboard: Tab to glossary link opens tooltip; Escape closes; Enter follows to academic page

**Warning signs:**
- On desktop, tooltip disappears when moving cursor toward it
- On mobile, tapping a glossary term does nothing
- Tooltip rendered outside viewport near page edges

**Phase to address:** Phase 3 (Glossary). Mobile behavior is a phase-gate test.

---

### Pitfall 14: Glossary cold-start — feature ships with empty content

**What goes wrong:**
Phase 3 delivers glossary infrastructure (matcher, tooltips, academic page routing) but ships with 5 stub entries. User opens a report, sees zero glossary links, concludes the feature is broken.

Inverse failure: team writes 50 exhaustive entries before shipping infrastructure — engineering blocked by content work.

**Why it happens:**
Content and infrastructure are decoupled in planning, but the user-visible value is the product of both. A working matcher with 5 entries is indistinguishable from a broken matcher.

**How to avoid:**
- Ship with **≥15 high-frequency entries** covering the indicators that appear in most reports:
  - Technical (8): RSI, MACD, MA/SMA/EMA, Bollinger Bands, Volume, Candlestick, Support/Resistance, Trend
  - Fundamental (7): P/E, P/B, ROE, ROA, EPS, Revenue Growth, Profit Margin
  - Macro (5): VN-Index, HOSE, T+3, Free Float, Dividend Yield
- Build frequency list first: run matcher on last 30 reports, rank terms by occurrence, write definitions top-down
- Content writing is a parallel stream — starts at Phase 3 kickoff, not after engineering is done
- Academic content can be `.md` files in the repo — no DB needed for <50 entries

**Warning signs:**
- First report viewed has zero glossary links
- Academic page shows "Chưa có nội dung" for most terms

**Phase to address:** Phase 3 (Glossary). Content inventory starts in parallel with engineering.

---

### Pitfall 15: Scope creep — "while we're touching the stock page…"

**What goes wrong:**
Phase 2 is "reading-first layout." Developer notices the header bar is ugly, timeframe selector uses outdated styling, score breakdown card could show a radar chart. All get added. Phase 2 slips 3× estimate; v1.1 ships late; reading-first goal gets lost.

**Why it happens:**
Polish phases are magnetic for scope creep. Every component looks improvable once you're editing its file.

**How to avoid:**
- Each phase plan lists "NOT in this phase" items explicitly
- Any new idea goes to a "v1.2 ideas" backlog, not in-flight work
- Time-box: if a visual tweak takes >30 minutes, it's out of scope
- Commit check: every commit must map to the phase's one-sentence goal

**Warning signs:**
- Phase is >50% over estimate
- Commit log touches files unrelated to phase goal

**Phase to address:** All phases — process discipline enforced at phase transitions.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `className="dark"` and hack a second class for light | No `next-themes` dependency | Hydration errors accumulate, no system preference, every theme feature must check a global | Never — `next-themes` is 2kB and solves this in one file |
| Hardcode chart hex colors without theme function | Copy-paste from existing `chart-colors.ts` | Charts break on theme switch, any palette change requires editing hex in 3+ files | Never — this debt is already present, must be paid in Phase 1 |
| Store glossary entries in `.ts` files as hardcoded objects | No DB schema, no admin UI | Content updates require a deploy; non-engineers can't contribute | v1.1 MVP (<50 entries); migrate to DB or CMS in v1.2 if content grows |
| Glossary matcher uses `string.replaceAll(term, ...)` | 3-line implementation | No word boundaries → false positives everywhere; case-sensitive; no aliases | Never for Vietnamese text |
| Drawer state in `useState` instead of URL params | Simpler, no router work | Bookmarks broken, back button broken, Telegram deep links can't specify panel | Never for v1.1 |
| Mixed color spaces (oklch in `:root`, hsl in `.dark`) | No migration effort | Can't programmatically compare/interpolate tokens across themes; confusing to maintain | Pay down in Phase 1 — convert everything to oklch |
| Skip `react-markdown` and keep `whitespace-pre-wrap` for reports | No new dependency | Can't add glossary links, can't style headings, no Markdown formatting in LLM output | Never for v1.1 — glossary feature requires a Markdown renderer |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `next-themes` ↔ lightweight-charts | Assuming CSS variables propagate to canvas | Explicitly call `chart.applyOptions({ layout: { background, textColor } })` on `resolvedTheme` change |
| `next-themes` ↔ `next/font` | Adding font but CSS still has `font-family: system-ui` hardcoded in `globals.css` body rule | Set `className={font.variable}` on `<html>`, reference via `--font-sans` CSS variable; remove hardcoded `system-ui` |
| `react-markdown` ↔ glossary remark plugin | Plugin defined after `ReactMarkdown` usage; links not rendered | Pass `remarkPlugins={[glossaryPlugin]}` prop; never try to wrap/mutate children post-render |
| Tailwind v4 `@custom-variant dark` ↔ `next-themes` | v4 replaced `darkMode: 'class'` in `tailwind.config`; line 5 of `globals.css` already has `@custom-variant dark (&:is(.dark *))` — this is the correct v4 syntax; don't add a `tailwind.config.ts` darkMode config that conflicts | Keep `@custom-variant dark` in CSS; ensure `next-themes` uses `attribute="class"` so `<html class="dark">` matches the `:is(.dark *)` selector |
| shadcn `base-nova` style ↔ new drawer component | `base-nova` uses `@base-ui/react` instead of Radix for some primitives; shadcn `Drawer` wraps `vaul` which wraps Radix Dialog — mixing `@base-ui` and Radix in the same modal stack can cause focus-trap conflicts | Check if `shadcn@4 add drawer` for `base-nova` uses `@base-ui` or Radix; if it uses Radix, ensure no `@base-ui` Dialog is open simultaneously |
| Ollama LLM output ↔ glossary matcher | Model swap changes surface forms; matcher silently matches less | Include model name in regression test metadata; alert when recall drops below threshold |
| Drawer URL params ↔ Next.js App Router | `useSearchParams()` in a client component triggers full page de-opt from static rendering | Use `router.replace` with `{ scroll: false }` for param updates; wrap search params reading in Suspense boundary to preserve streaming |
| Dynamic chart import ↔ drawer animation | Chart measures container during CSS transition, gets wrong width | Gate chart creation on `transitionend` event or use `autoSize: true` option |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Glossary regex re-runs on every render | React profiler shows `GlossaryRenderer` >16ms | Memoize on `(reportText, glossaryVersion)`; build single compiled regex from all aliases; single pass per text node | Reports >5000 words or glossary >50 terms |
| Fetching all chart data on mount when drawer is closed | TTI regresses; `/prices?days=365` in Network on every stock page visit | React Query `enabled: drawerOpen`; prefetch on hover | Every page view — constant regression |
| Destroying/recreating chart on every theme toggle | Brief flash of empty canvas; GC pressure | `chart.applyOptions` for color updates, not destroy/recreate | Every theme toggle (frequent during demos) |
| Loading `react-markdown` + remark + rehype on every page route | Bundle size bloat, TTI regression on non-stock routes | Route-specific dynamic import; only load on `/stock/*` and `/academic/*` | First load of any page |
| Unoptimized Vietnamese font loading (Be Vietnam Pro with all weights) | Large font download, FOUT on slow connections | Load only weights 400, 500, 600, 700; use `next/font/google` with `display: 'swap'` | Every first visit |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Rendering LLM output via `dangerouslySetInnerHTML` | Prompt injection → XSS if LLM echoes HTML from crawled articles | Always render via `react-markdown` which sanitizes by default; current `whitespace-pre-wrap` is safe but lacks features |
| Glossary content loaded from external source without sanitization | XSS if academic content includes scripts | Use `react-markdown` + `rehype-sanitize` for all user/content-facing Markdown rendering |
| Academic page `[term]` param used unsanitized in DB query | Path traversal / SQL injection | Validate param matches `/^[a-z0-9-]+$/`; 404 otherwise; parameterized queries only |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Every indicator term linked → report is a hyperlink minefield | Reading becomes skimming; blue underlines everywhere | Link **first occurrence only** per report; subsequent mentions render plain |
| Theme toggle hidden in settings dropdown | Users who prefer dark can't find it | Sun/moon icon in top-right header, one click, no modal |
| Drawer opens over report, obscuring reading position | User must close drawer to re-read context | Desktop: drawer slides in from right, overlays but doesn't push main content; add close affordance; Mobile: full sheet with clear X |
| Warm-light default alienates returning v1.0 dark-mode users | Disorientation on first visit after update | Honor `prefers-color-scheme` on first visit; if OS is dark, start dark even though app default is light |
| Academic page is dry reference with no examples | User reads definition but still doesn't understand | Every entry includes: plain definition + real example from LocalStock ("Ví dụ: VNM hiện tại RSI = 32, gần ngưỡng quá bán...") |
| Glossary tooltip contains link but dismisses on mouse-leave | Frustrating "tooltip race" | Use `HoverCard` (content stays open when cursor moves to it), not `Tooltip` |
| Report has Vietnamese curly quotes but matcher only handles ASCII quotes | Glossary misses phrases quoted differently | Normalize quotes in text before matching |

## "Looks Done But Isn't" Checklist

- [ ] **Theme toggle:** Cookie persistence so server renders correct theme on refresh — hard-refresh 10× with cache disabled → zero flashes
- [ ] **Theme toggle:** `suppressHydrationWarning` on `<html>` — grep `layout.tsx` for the attribute
- [ ] **Theme toggle:** Chart colors follow theme — toggle on `/stock/VNM`, all charts repaint within one frame
- [ ] **Theme toggle:** `--stock-up`/`--stock-down` meet 4.5:1 contrast in light mode — run `axe-core` on `/rankings`
- [ ] **Theme toggle:** Respects `prefers-color-scheme` on first visit — clear storage, set OS to dark, open app → starts dark
- [ ] **Theme toggle:** `gradeColors` badges readable in light mode — visually verify all 5 grades on cream background
- [ ] **Theme toggle:** Color spaces consistent (all oklch or all hsl) — grep globals.css for mixed formats
- [ ] **Reading layout:** URL state for drawer — copy URL with drawer open, paste in new tab → same drawer state
- [ ] **Reading layout:** Scroll preservation — scroll to middle of report, open/close drawer → position unchanged
- [ ] **Reading layout:** Chart data NOT fetched when drawer closed — Network tab clear on page load except score/report
- [ ] **Reading layout:** Keyboard close (Escape) — Tab into drawer, press Escape → drawer closes, focus returns to trigger
- [ ] **Reading layout:** Vietnamese line-height ≥ 1.75 on report prose — native reader confirms comfort
- [ ] **Reading layout:** `system-ui` font override removed from globals.css body rule
- [ ] **Glossary:** Matcher recall ≥80% on corpus of 30 real reports
- [ ] **Glossary:** False-positive audit — no Vietnamese common words captured (e.g., "ma" in names)
- [ ] **Glossary:** Mobile tap interaction — tap term → popover opens; tap outside → closes
- [ ] **Glossary:** Tooltip doesn't overflow viewport — test terms near right edge
- [ ] **Glossary:** Academic page deep link — `/academic/rsi` loads directly via URL
- [ ] **Glossary:** First-occurrence-only linking — report with 5 RSI mentions, only first is linked
- [ ] **Glossary:** Content coverage ≥15 entries at launch

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Theme flash shipped | LOW | Add `next-themes` inline script + `suppressHydrationWarning` — 1 file, 30 min |
| Chart colors don't follow theme | LOW | Refactor `chart-colors.ts` to function; add theme dep + `applyOptions` — ~2h per chart type |
| Hardcoded Tailwind colors scattered | MEDIUM | `rg "text-.*-400"` in src/; replace each with `dark:` variant — ~4h total |
| Token inversion (dark values in `:root`) | LOW | Move financial tokens into proper `:root`/`.dark` blocks — ~1h, but must be done before any component work |
| Glossary matcher false positives | LOW | Add alias refinement + word boundaries; ~1h per problematic term |
| Glossary stopped matching after Ollama model swap | MEDIUM | Run regression suite, identify new surface forms, add aliases — <2h if suite exists |
| Telegram deep links broken by URL change | LOW | Add redirect in `next.config.ts`; fix Telegram templates — 30 min |
| Vietnamese typography complaints | LOW | Adjust line-height + font in `globals.css` + `layout.tsx` — <1h |
| Scope creep caused deadline miss | HIGH | Descope ruthlessly; move additions to v1.2; organizational fix only |
| Academic page has no content | HIGH | Content authoring is linear work; must be parallel to engineering from start |
| Drawer chart dimensions wrong | LOW | Add `transitionend` gate or `autoSize: true` — ~1h |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1 Theme flash / hydration | Phase 1 (Theme) | Hard-refresh 10× across browsers, zero flash, zero warnings |
| #2 Token inversion (`:root` has dark values) | Phase 1 (Theme) | Every CSS var exists in both `:root` and `.dark` |
| #3 Charts don't follow theme | Phase 1 (Theme) | Toggle theme on `/stock/VNM` → 3 charts repaint without reload |
| #4 `gradeColors` hardcoded colors | Phase 1 (Theme) | All grade badges pass contrast check in both themes |
| #5 Orange accent fails WCAG | Phase 1 (Theme) | `axe-core` on 3 pages in light mode → zero contrast violations |
| #6 Drawer eager-loads data | Phase 2 (Layout) | Network tab cold load: only score + report requests |
| #7 LLM surface-form variance | Phase 3 (Glossary) | Matcher recall ≥80% on 30 real reports |
| #8 DOM mutation breaks SSR | Phase 3 (Glossary) | No `querySelector` in report renderer; links in SSR HTML |
| #9 Deep links broken | Phase 2 (Layout) | Telegram test message lands correctly; `?drawer=...` survives refresh |
| #10 Scroll position lost | Phase 2 (Layout) | Scroll-preservation test on iOS Safari |
| #11 Vietnamese typography cramped | Phase 2 (Layout) | Native reader reviews real report; line-height ≥1.75 |
| #12 Chart dimension in animating drawer | Phase 2 (Layout) | First drawer open → chart fills width correctly |
| #13 Glossary tooltip dismisses | Phase 3 (Glossary) | HoverCard stays open when cursor moves to it; mobile tap works |
| #14 Glossary cold-start | Phase 3 (Glossary) | ≥15 entries authored; last 30 reports have ≥15 distinct linked terms |
| #15 Scope creep | All phases | Phase plan lists explicit "NOT in this phase" items |

## Sources

- Verified codebase analysis: `layout.tsx`, `globals.css`, `chart-colors.ts`, `price-chart.tsx`, `sub-panel.tsx`, `utils.ts` (gradeColors), `error-state.tsx`, `stock/[symbol]/page.tsx`, `app-shell.tsx`, `sidebar.tsx`, `components.json`, `package.json`
- `.planning/PROJECT.md` — v1.1 requirements and design philosophy
- `apps/helios/AGENTS.md` — Next.js 16 divergence warning (APIs differ from training data)
- [next-themes (pacocoursey/next-themes)](https://github.com/pacocoursey/next-themes) — inline blocking script for FOUC prevention, `suppressHydrationWarning` requirement
- [Tailwind CSS v4 Dark Mode docs](https://tailwindcss.com/docs/dark-mode) — `@custom-variant` syntax for class-based dark mode
- [lightweight-charts — Chart colors tutorial](https://tradingview.github.io/lightweight-charts/tutorials/customization/chart-colors) — `applyOptions` for dynamic theme updates without chart recreation
- [lightweight-charts discussion #902](https://github.com/tradingview/lightweight-charts/discussions/902) — real-world theme switching patterns
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) — WCAG 4.5:1 body text / 3:1 UI component requirements
- [Vietnamese Typography — Type Recommendations](https://vietnamesetypography.com/type-recommendations/) — stacked diacritic line-height guidance
- [Be Vietnam Pro — Google Fonts](https://fonts.google.com/specimen/Be%2BVietnam%2BPro) — Vietnamese-optimized font
- [vaul (emilkowalski/vaul)](https://vaul.emilkowal.ski/) — drawer with correct iOS scroll-lock behavior
- [shadcn/ui Drawer docs](https://ui.shadcn.com/docs/components/radix/drawer) — drawer accessibility and focus management

---
*Pitfalls research for: LocalStock v1.1 UX Polish & Educational Depth*
*Researched: 2026-04-17*
