# Feature Landscape — LocalStock v1.3

**Domain:** Stock analysis dashboard — UI/UX polish
**Researched:** 2026-04-24

## Table Stakes

Features that define this milestone. All 7 are committed scope.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Source Sans 3 font | Spec: "Font Source Sans 3 (kiểu Anthropic)" | Low | `next/font/google`, Vietnamese subset confirmed, zero deps |
| Claude Desktop color palette | Spec: "Màu sắc Claude Desktop palette (thay blue)" | Low | CSS variable changes only — 10 blue values in `globals.css` |
| Sidebar float + collapse | Spec: "Sidebar float + collapsible, 2 icon tabs" | **High** | Full rewrite of sidebar.tsx + app-shell.tsx layout |
| Fix table sort | Spec: "Fix hành vi sort trên tables" | Low | Fix comparator for string vs number types |
| Search state persist | Spec: "Search state persist khi chuyển trang/tab" | Medium | Add `nuqs`, wrap layout, replace `useState` in 3 components |
| Market session progress bar | Spec: "Market session progress bar trên header" | Medium | New component, timezone math, auto-refresh |
| Market overview metrics | Spec: "Market overview 4 ô metrics với data thật" | Medium | Needs new backend API endpoint + new query hook |

## Differentiators

Features that would add extra polish beyond the spec, if time allows.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Sidebar keyboard shortcut | `Cmd+B` / `Ctrl+B` to toggle sidebar | Low | `useEffect` keydown listener |
| Search highlight | Highlight matching text in filtered results | Low | Wrap matched substring in `<mark>` |
| Session state toasts | Notify when HOSE session changes (open→lunch→close) | Low | State change detection in interval + `sonner` toast |
| Animated metric transitions | Number animation when metric values update | Medium | CSS transitions or `requestAnimationFrame` |

## Anti-Features

Features to explicitly NOT build in v1.3.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full page restructure | v1.3 is polish, not redesign | Keep existing pages, just refine styling |
| Real-time WebSocket market data | Over-engineering for post-market-close app | TanStack Query polling with `refetchInterval` |
| Custom chart for market overview | lightweight-charts is for stock detail only | Simple number cards with change indicators |
| Mobile responsive sidebar | Spec: "web dashboard là đủ, không cần mobile" | Desktop-first, icon-rail on narrow screens |
| Theme beyond light/dark | Only 2 themes needed | Apply warm palette to both variants |
| New navigation pages | Sidebar restructures existing 4 pages | 2 groups (Main/Admin) with same destinations |

## Feature Dependencies

```
Font + Color palette → (global foundation, all features inherit)
  ↓
Sidebar overhaul → Header layout (sidebar width affects header)
  ↓
Market session bar (lives in header, needs settled layout)

Table sort fix (independent — can parallel anything)
Search persistence (independent — can parallel with sidebar)
Market overview metrics → Backend API (external dependency)
```

## MVP Recommendation

All 7 features are committed scope, but if forced to prioritize:

1. **Font + Color palette** — foundation, every screenshot wrong without it
2. **Sidebar float/collapse** — highest visual impact, most complex
3. **Table sort fix** — bug fix, should always ship
4. **Search state persist** — real UX improvement
5. **Market session bar** — nice to have
6. **Market overview metrics** — depends on backend API readiness

**Defer if blocked:** Market overview metrics requires backend work that may not be ready when frontend reaches phase 4.
