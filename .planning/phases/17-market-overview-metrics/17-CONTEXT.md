# Phase 17: Market Overview Metrics - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a live market summary section to the Market Overview page: 4 metric cards (VN-Index, total volume, advances count, declines count / market breadth) backed by a new backend API endpoint `GET /api/market/summary`. Data comes from the daily crawl. Intraday live prices, additional market indices, and push-based updates are out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Backend Data Source
- **D-01:** VN-Index data comes from tracking `VNINDEX` as a regular stock symbol in the existing prices table — same crawl path, same schema as any other stock. No new crawler needed.
- **D-02:** Advances/declines/breadth are computed at query time from the ~400 tracked stocks in the DB: compare today's close vs previous close, count up/flat/down movers. Breadth = advances / (advances + declines).
- **D-03:** New endpoint `GET /api/market/summary` returns: `{ vnindex: { value, change_pct }, total_volume, advances, declines, breadth, as_of: "YYYY-MM-DD" }`.

### Staleness & Transparency
- **D-04:** The API response always includes `as_of` (the date of the data). The frontend shows a small "as of [date]" label near the market summary section — not on individual cards. User sees data age without it dominating the UI.

### Card Content
- **D-05:** Each card shows: primary value + % change + trend arrow (↑ or ↓). Example: "VN-Index  1,245.3  +0.8% ↑". This adds a change indicator on top of the existing MacroCards value-only pattern.
- **D-06:** The 4 cards: (1) VN-Index — close value + day change %, (2) Total Volume — sum across tracked stocks + vs 20-day avg %, (3) Advances — count of stocks with close > prev_close, (4) Market Breadth — advances / (advances + declines) as %.
- **D-07:** VN-Index % change is `(close - prev_close) / prev_close × 100`. Volume % change is `(today_vol - 20d_avg_vol) / 20d_avg_vol × 100`.

### Layout on Market Page
- **D-08:** New "Market Summary" section appears at the TOP of the Market page, before the existing MacroCards section. Reading order: market summary → macro indicators → sector performance.
- **D-09:** Grid layout: `grid grid-cols-2 gap-4` — consistent with the existing MacroCards grid.

### Auto-refresh
- **D-10:** Frontend uses `staleTime: 30 * 60 * 1000` (30 minutes) for the `useMarketSummary` query. No smart market-hours logic needed. Consistent with daily-crawl data rhythm.
- **D-11:** Loading: show skeleton cards (same as MacroCards skeleton pattern). Error: show `ErrorState` component.

### Claude's Discretion
- Exact color/icon choice for trend arrows (up = green, down = red — standard convention)
- Exact label text for each card (Vietnamese labels matching i18n pattern of existing market page)
- Where in `app.ts` the new market router is registered
- Pydantic response model field naming conventions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `apps/helios/src/components/market/macro-cards.tsx` — Card layout, skeleton, and value formatting pattern to extend
- `apps/helios/src/app/market/page.tsx` — Page structure where new section is inserted at top
- `apps/helios/src/lib/queries.ts` — `useMacroLatest` as the direct pattern for `useMarketSummary` hook
- `apps/helios/src/lib/types.ts` — Where new `MarketSummaryResponse` type goes
- `apps/prometheus/src/localstock/api/routes/prices.py` — Reference for route structure and repo usage pattern
- `apps/prometheus/src/localstock/db/repositories/price_repo.py` — Price query patterns (get latest close, prev close)

### Requirements
- `apps/helios/src/components/market/macro-cards.tsx` §MacroCards — card component to adapt
- `.planning/REQUIREMENTS.md` §Market Info — MKT-03 and MKT-04 acceptance criteria

### No external specs
No external ADRs or design docs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MacroCards` component: card grid + skeleton + value formatting — adapt for market summary (add % change + arrow)
- `Card`, `CardContent` from `@/components/ui/card`: already in use, no new UI primitives needed
- `Skeleton` from `@/components/ui/skeleton`: loading state pattern ready
- `ErrorState` from `@/components/ui/error-state`: error fallback pattern ready
- `useQuery` from TanStack Query: established data fetching pattern
- `apiFetch` from `@/lib/api`: API client wrapper used by all queries

### Established Patterns
- All market/data queries: `useQuery` with `staleTime`, skeleton while loading, `ErrorState` on error
- Card grid: `grid grid-cols-2 gap-4` — matches MacroCards, maintain consistency
- Vietnamese i18n labels: `useTranslations("market.X")` — new market summary labels go in the same namespace
- Backend routes: FastAPI router in `apps/prometheus/src/localstock/api/routes/`, registered in `app.py`
- Pydantic response schemas: defined inline in route files or in a shared `schemas.py` in the routes package

### Integration Points
- Frontend: `market/page.tsx` — new section rendered at top, new `useMarketSummary` hook imported from `queries.ts`
- Backend: new `market.py` router file → registered in `apps/prometheus/src/localstock/api/app.py`
- DB: `PriceRepository` — reuse existing `get_prices(symbol, ...)` for VNINDEX; new aggregate query for advances/declines
- VNINDEX must be added to tracked stocks (either via `admin_service.add_stock("VNINDEX")` or a migration seed)

</code_context>

<specifics>
## Specific Ideas

- MacroCards is the direct visual template — new `MarketSummaryCards` component extends it with a change + arrow column
- "as of [date]" label should be a small muted text below the section title (not per-card)
- Trend arrows: standard financial convention — green ↑ for positive, red ↓ for negative

</specifics>

<deferred>
## Deferred Ideas

- Smart refresh based on market hours (5min during 9:00–15:00 VN time, 1hr outside) — decided to keep simple 30min for now
- Intraday live price feeds — out of scope (daily crawl only for v1.3)
- Additional market indices (HNX, UPCOM) — out of scope per PROJECT.md (HOSE only)
- Volume breakdown by sector — out of scope for this phase

</deferred>

---

*Phase: 17-market-overview-metrics*
*Context gathered: 2026-04-25*
