# Phase 17: Market Overview Metrics - Research

**Researched:** 2026-04-25
**Domain:** FastAPI new route + SQLAlchemy aggregate queries + React TanStack Query hook + new UI component
**Confidence:** HIGH — all findings come from direct codebase reads, no guessing

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: VN-Index data comes from tracking `VNINDEX` as a regular stock symbol in the existing prices table — same crawl path, same schema as any other stock. No new crawler needed.
- D-02: Advances/declines/breadth are computed at query time from the ~400 tracked stocks in the DB: compare today's close vs previous close, count up/flat/down movers. Breadth = advances / (advances + declines).
- D-03: New endpoint `GET /api/market/summary` returns: `{ vnindex: { value, change_pct }, total_volume, advances, declines, breadth, as_of: "YYYY-MM-DD" }`.
- D-04: The API response always includes `as_of`. Frontend shows a small "as of [date]" label near the market summary section — not on individual cards.
- D-05: Each card shows: primary value + % change + trend arrow (↑ or ↓).
- D-06: The 4 cards: (1) VN-Index — close value + day change %, (2) Total Volume — sum across tracked stocks + vs 20-day avg %, (3) Advances — count of stocks with close > prev_close, (4) Market Breadth — advances / (advances + declines) as %.
- D-07: VN-Index % change is `(close - prev_close) / prev_close × 100`. Volume % change is `(today_vol - 20d_avg_vol) / 20d_avg_vol × 100`.
- D-08: New "Market Summary" section appears at the TOP of the Market page, before the existing MacroCards section.
- D-09: Grid layout: `grid grid-cols-2 gap-4` — consistent with the existing MacroCards grid.
- D-10: Frontend uses `staleTime: 30 * 60 * 1000` (30 minutes) for the `useMarketSummary` query.
- D-11: Loading: show skeleton cards (same as MacroCards skeleton pattern). Error: show `ErrorState` component.

### Claude's Discretion
- Exact color/icon choice for trend arrows (up = green, down = red — standard convention)
- Exact label text for each card (Vietnamese labels matching i18n pattern of existing market page)
- Where in `app.ts` the new market router is registered
- Pydantic response model field naming conventions

### Deferred Ideas (OUT OF SCOPE)
- Smart refresh based on market hours
- Intraday live price feeds
- Additional market indices (HNX, UPCOM)
- Volume breakdown by sector
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-03 | 4 metric cards on Market Overview work with real backend data | Backend aggregate query (advances/declines/volume), VNINDEX seeding, frontend hook + component |
| MKT-04 | Backend API endpoint provides market summary data | New `GET /api/market/summary` in new `market.py` router registered in `app.py` |
</phase_requirements>

---

## Summary

Phase 17 adds a "Market Summary" section to the top of the existing Market Overview page (`apps/helios/src/app/market/page.tsx`). It requires: (1) a new backend route file `apps/prometheus/src/localstock/api/routes/market.py` with a `GET /api/market/summary` endpoint, (2) a one-time VNINDEX seeding step (adding it to the stocks table via `stock_repo.add_stock`), (3) a new `PriceRepository` aggregate query method, and (4) frontend additions in `queries.ts`, `types.ts`, a new `MarketSummaryCards` component, and the market page itself.

The codebase is highly consistent. Every pattern needed here already exists in at least one other place in the codebase. No new libraries are needed. The primary complexity is in the SQL aggregate query (advances/declines computation requires a self-join on `stock_prices` to get today vs previous trading day), but this is a well-understood query pattern given the existing schema.

**Primary recommendation:** Build the backend aggregate query first and validate it returns correct data, then wire up the frontend. The VNINDEX seeding is a prerequisite for the VN-Index card but the other 3 cards can work without it.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| VNINDEX seeding | Database / Storage | API / Backend | One-time data bootstrapping via stock_repo.add_stock |
| Advances/declines/breadth computation | Database / Storage | API / Backend | Aggregate SQL query; computed at query time per D-02 |
| Volume aggregate + 20-day avg | Database / Storage | API / Backend | Reads from stock_prices; avg_volume_20 available in TechnicalIndicator |
| Market summary API endpoint | API / Backend | — | New FastAPI route, new router file |
| useMarketSummary hook | Frontend Server (SSR) | Browser / Client | TanStack Query hook in queries.ts |
| MarketSummaryCards component | Browser / Client | — | New React component following MacroCards pattern |
| i18n strings for market summary | Frontend Server (SSR) | — | New keys in market.* namespace in both locale files |

---

## Standard Stack

No new libraries needed. Phase 17 uses only what is already installed.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | installed | New route handler | Already the project's API framework |
| SQLAlchemy async | installed | Aggregate price query | Already used for all DB queries |
| Pydantic BaseModel | installed | Response schema validation | Already used in admin.py and macro.py |
| TanStack Query | installed | Frontend data fetching | Already used for all API calls in queries.ts |
| next-intl | installed | i18n translation | Already used for all UI strings |

**No `npm install` or `uv add` needed.**

---

## Architecture Patterns

### System Architecture Diagram

```
Browser
  |
  | HTTP GET /api/market/summary
  v
FastAPI app.py
  -> market_router (new)
     |
     |-- PriceRepository.get_latest(symbol="VNINDEX")
     |   -> stock_prices WHERE symbol='VNINDEX' ORDER BY date DESC LIMIT 1
     |
     |-- PriceRepository.get_prev(symbol="VNINDEX")
     |   -> stock_prices WHERE symbol='VNINDEX' ORDER BY date DESC LIMIT 1 OFFSET 1
     |
     |-- PriceRepository.get_market_summary_data()  (new method)
         -> self-join on stock_prices to get today's latest date row
         -> per-stock close vs prev_close
         -> SUM(volume), COUNT advances/declines
         -> subquery for 20d avg volume via TechnicalIndicator.avg_volume_20
  |
  JSON response: { vnindex, total_volume, total_volume_change_pct, advances, declines, breadth, as_of }
  |
  v
Frontend: useMarketSummary() hook (queries.ts)
  -> MarketSummaryCards component (new)
     -> 4 Card components (grid grid-cols-2 gap-4)
     -> Skeleton while loading
     -> ErrorState on error
  -> "as of [date]" label below section title
```

### Recommended Project Structure

No new directories. New files:
```
apps/prometheus/src/localstock/api/routes/
├── market.py              # NEW — GET /api/market/summary

apps/helios/src/
├── lib/
│   ├── types.ts           # ADD MarketSummaryResponse type
│   └── queries.ts         # ADD useMarketSummary hook
├── components/market/
│   └── market-summary-cards.tsx  # NEW component
└── app/market/
    └── page.tsx           # MODIFY — insert new section at top
```

### Pattern 1: FastAPI Router Registration
**What:** New route file with `router = APIRouter(prefix="/api")`, registered in `app.py`.
**When to use:** Every new route group.
**Example (from `macro.py`):**
```python
# apps/prometheus/src/localstock/api/routes/macro.py
router = APIRouter(prefix="/api")

@router.get("/macro/latest")
async def get_latest_macro(session: AsyncSession = Depends(get_session)):
    ...
```
**Equivalent for market:**
```python
# apps/prometheus/src/localstock/api/routes/market.py
router = APIRouter(prefix="/api")

@router.get("/market/summary")
async def get_market_summary(session: AsyncSession = Depends(get_session)):
    ...
```
**Registration in `app.py`:**
```python
from localstock.api.routes.market import router as market_router
# ...
app.include_router(market_router, tags=["market"])
```

### Pattern 2: PriceRepository Query Methods
**What:** Async SQLAlchemy queries on `StockPrice` model.
**When to use:** All price data access.
**Example (from `price_repo.py` `get_latest`):**
```python
async def get_latest(self, symbol: str) -> StockPrice | None:
    stmt = (
        select(StockPrice)
        .where(StockPrice.symbol == symbol)
        .order_by(StockPrice.date.desc())
        .limit(1)
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```
**StockPrice columns:** `id, symbol, date, open, high, low, close, volume, adj_close, adj_factor`
**Unique constraint:** `uq_stock_price` on `(symbol, date)` — one row per stock per day.

### Pattern 3: Advances/Declines Aggregate Query
**What:** Compute advances, declines, total volume from the latest two trading days.
**Approach:** Get the two most recent distinct dates from `stock_prices`, then join rows on those dates to compute per-stock direction.

```python
# Pseudocode — exact SQLAlchemy version in implementation
# Step 1: Find the two most recent trading dates across all tracked stocks
# Step 2: Subquery for today's prices (latest date)
# Step 3: Subquery for yesterday's prices (second-most-recent date)
# Step 4: Join on symbol, compute advance/decline counts and total volume
```

**Key concern:** "Today" and "yesterday" in this system are relative to the latest crawl date, NOT `date.today()`. The DB may not have today's data yet (crawl runs at 15:45). Always use `MAX(date)` from `stock_prices` to determine the most recent trading day.

**Recommended new method on `PriceRepository`:**
```python
async def get_market_aggregate(self) -> dict:
    """Compute advances/declines/volume for most recent trading day.
    
    Returns dict with:
        as_of: date (most recent trading day in DB)
        advances: int
        declines: int
        flat: int
        total_volume: int
        
    Raises ValueError if fewer than 2 trading days of data available.
    """
```

### Pattern 4: Pydantic Response Schema (inline in route file)
**What:** Define response model inline in the route file, not in a shared schema.
**When to use:** Per established pattern in `admin.py` and `macro.py`.
**Example (from `admin.py`):**
```python
class AddStockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$")
```

### Pattern 5: useQuery Hook (from `queries.ts`)
**What:** TanStack Query hook calling `apiFetch`.
**Direct model — `useMacroLatest`:**
```typescript
export function useMacroLatest() {
  return useQuery({
    queryKey: ["macro", "latest"],
    queryFn: () => apiFetch<MacroLatestResponse>(`/api/macro/latest`),
    staleTime: 60 * 60 * 1000,
  });
}
```
**For `useMarketSummary`:** Same shape, different key/URL/staleTime:
```typescript
export function useMarketSummary() {
  return useQuery({
    queryKey: ["market", "summary"],
    queryFn: () => apiFetch<MarketSummaryResponse>(`/api/market/summary`),
    staleTime: 30 * 60 * 1000,  // D-10: 30 minutes
  });
}
```

### Pattern 6: MacroCards Component (direct visual template)
**What:** Card grid with skeleton while loading.
**Key details from `macro-cards.tsx`:**
- Props: `{ indicators: MacroIndicator[]; isLoading?: boolean }`
- Skeleton: 2 `Skeleton` elements per card — `h-3 w-20` (label) + `h-6 w-24` (value)
- Card: `<Card className="border border-border"><CardContent className="p-4">...</CardContent></Card>`
- Label: `<p className="text-xs text-muted-foreground">...</p>`
- Value: `<p className="text-xl font-semibold font-mono text-foreground mt-1">...</p>`
- Grid: `<div className="grid grid-cols-2 gap-4">`

**MarketSummaryCards extends this pattern** by adding a change indicator row below the primary value. The new component will be self-contained (not extend MacroCards) since the props shape differs.

### Pattern 7: ErrorState Component
**What:** Standard error display with heading + body text.
**Source:** `apps/helios/src/components/ui/error-state.tsx`
**Props:**
```typescript
interface ErrorStateProps {
  heading?: string;  // optional — defaults to common.loadError
  body?: string;     // optional — defaults to common.connectionError
}
```
**Usage in `market/page.tsx`:**
```typescript
{macro.isError ? (
  <ErrorState body={t("macroError")} />
) : (
  <MacroCards ... />
)}
```
**New usage for market summary:** Same pattern — `<ErrorState body={t("summaryError")} />`.

### Pattern 8: market/page.tsx Section Structure
**What:** How sections are organized in the market page.
**Current structure (verified from reading the file):**
```tsx
<div>
  <h1 className="text-xl font-semibold mb-6">{t("title")}</h1>

  {/* Macro indicator cards */}
  <section className="mb-8">
    <h2 className="text-sm font-semibold text-muted-foreground mb-4">{t("macroTitle")}</h2>
    {macro.isError ? <ErrorState /> : <MacroCards ... />}
  </section>

  {/* Sector performance table */}
  <section>
    <h2 ...>{t("sectorTitle")}</h2>
    ...
  </section>
</div>
```
**New market summary section goes BEFORE `<h1>` is rendered — actually D-08 says before MacroCards, so it's the first `<section>` after `<h1>`.**

The updated structure:
```tsx
<div>
  <h1 ...>{t("title")}</h1>

  {/* NEW: Market Summary section — FIRST */}
  <section className="mb-8">
    <div className="flex items-baseline justify-between mb-4">
      <h2 ...>{t("summaryTitle")}</h2>
      {summary.data && <span className="text-xs text-muted-foreground">{t("asOf", { date: summary.data.as_of })}</span>}
    </div>
    {summary.isError ? <ErrorState body={t("summaryError")} /> : <MarketSummaryCards ... />}
  </section>

  {/* Existing Macro indicator cards */}
  <section className="mb-8">...</section>

  {/* Existing Sector performance table */}
  <section>...</section>
</div>
```

### Anti-Patterns to Avoid
- **Using `date.today()` as "latest trading day":** The DB may have data from several days ago if crawl missed a session. Always use `MAX(date)` from `stock_prices` to find the latest available date.
- **Querying 400 stocks individually:** Use a single aggregate SQL query across all tracked stocks, not a Python loop.
- **Computing 20d avg volume from scratch:** `TechnicalIndicator.avg_volume_20` already exists in the DB and is computed during the analysis step. Read from there for the volume comparison, but fall back to `None` / `0` if not available for a given stock.
- **Hardcoding VNINDEX in the stocks filter:** The VNINDEX row in stocks may have `exchange='HOSE'` or a different value; filter for advances/declines should exclude VNINDEX (it's an index, not a traded stock), or include it — but be explicit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API response schema | Custom dict construction | Pydantic BaseModel | Already used in admin.py; provides automatic validation + docs |
| Card skeleton | Custom loading shimmer | `Skeleton` from `@/components/ui/skeleton` | Already used in MacroCards |
| Error display | Custom error UI | `ErrorState` from `@/components/ui/error-state` | Already used in market/page.tsx |
| Data fetching | Custom fetch wrapper | `apiFetch` + `useQuery` | Already the project standard in queries.ts |
| i18n formatting | String concatenation | `useTranslations("market.X")` | All strings go through next-intl |

---

## Common Pitfalls

### Pitfall 1: VNINDEX Not in stocks Table
**What goes wrong:** `GET /api/market/summary` returns 404 or null for VN-Index because `VNINDEX` doesn't exist in `stock_prices`.
**Why it happens:** VNINDEX is not a traded HOSE stock — it won't be seeded by `fetch_and_store_listings`. It must be added manually via `stock_repo.add_stock("VNINDEX")` and then crawled via `admin/crawl`.
**How to avoid:** Plan includes a Wave 0 step to seed VNINDEX. The endpoint must handle `None` gracefully if no price data exists (return `vnindex: null` rather than 500).
**Warning signs:** `get_latest("VNINDEX")` returns `None` in tests.

### Pitfall 2: "Latest Trading Day" Mismatch Between VNINDEX and Stock Prices
**What goes wrong:** VNINDEX close date is 2026-04-24, but tracked stocks have 2026-04-25 data, making advances/declines look wrong.
**Why it happens:** VNINDEX and individual stocks are crawled separately. They may have different `MAX(date)` values.
**How to avoid:** Use `as_of = MAX(date)` computed from the general stock population for the advances/declines query. Return `as_of` in the response so the frontend can display data age.

### Pitfall 3: Advances/Declines Self-Join Returns Wrong Results
**What goes wrong:** The query joins today vs yesterday but returns 0 advances because the subqueries don't select the right dates.
**Why it happens:** "Previous day" is the second-most-recent date across all stocks, not `date - 1` (markets are closed on weekends/holidays).
**How to avoid:** Use a subquery to get `DISTINCT date ORDER BY date DESC LIMIT 2` to identify the two most recent trading dates before constructing the join.

### Pitfall 4: Volume % Change When avg_volume_20 Is NULL
**What goes wrong:** Division by zero or null errors when computing `(today_vol - avg) / avg`.
**Why it happens:** `TechnicalIndicator.avg_volume_20` is NULL until analysis has been run for a stock.
**How to avoid:** Use `NULLIF(avg_volume_20, 0)` in SQL or handle `None` in Python. Return `total_volume_change_pct: null` if avg is unavailable.

### Pitfall 5: VNINDEX Counted in Advances/Declines
**What goes wrong:** VNINDEX is included in the advance/decline count alongside individual stocks, making the count incorrect (it's an index, not a stock).
**Why it happens:** If VNINDEX is added to the `stocks` table with `is_tracked=True`, it will appear in the general stock population query.
**How to avoid:** Either add VNINDEX with `is_tracked=False` and a special `exchange='INDEX'` value, or explicitly exclude `symbol='VNINDEX'` in the advances/declines aggregate query.

### Pitfall 6: i18n Key Missing in Both Locale Files
**What goes wrong:** `useTranslations("market.summaryTitle")` throws at runtime (next-intl throws on missing keys in strict mode).
**Why it happens:** Adding keys to only `en.json` and forgetting `vi.json` (or vice versa).
**How to avoid:** Always update both `en.json` and `vi.json` in the same commit. The market namespace currently ends at line 75 in both files.

---

## Research Answers to Focus Questions

### Q1: VNINDEX Seeding Mechanism
**Answer:** `StockRepository.add_stock("VNINDEX")` is the correct mechanism. It does: (1) check if VNINDEX exists in stocks table via `get_by_symbol`, (2) if yes: set `is_tracked=True` and commit, (3) if no: create a minimal `Stock(symbol="VNINDEX", name="VNINDEX", exchange="HOSE", is_tracked=True)` and commit. This is called by the `POST /api/admin/stocks` endpoint. After seeding, a crawl job must be triggered via `POST /api/admin/crawl` with `{"symbols": ["VNINDEX"]}` to populate `stock_prices`. The seeding step is idempotent (safe to call multiple times). **CRITICAL:** VNINDEX must use a different `exchange` value or be explicitly excluded from advances/declines queries (see Pitfall 5).

### Q2: Advances/Declines Query
**Answer:** No `prev_close` column exists in `stock_prices` — the table only has `(id, symbol, date, open, high, low, close, volume, adj_close, adj_factor)`. The query requires a self-join on two different dates. The recommended approach:
1. Get the two most recent `DISTINCT date` values from `stock_prices` (where symbol != 'VNINDEX' and is_tracked=True stocks).
2. Join today's rows with yesterday's rows on `symbol`.
3. Aggregate: `COUNT(CASE WHEN today.close > yesterday.close THEN 1 END)` for advances, `COUNT(CASE WHEN today.close < yesterday.close THEN 1 END)` for declines, `SUM(today.volume)` for total volume.

### Q3: Total Volume
**Answer:** `stock_prices.volume` is `BigInteger` per stock per day. Total volume = `SUM(volume)` across all tracked stocks on the most recent trading date. For the 20-day avg comparison: `TechnicalIndicator.avg_volume_20` stores the pre-computed 20-day average volume per stock. The endpoint should sum `avg_volume_20` across stocks from the `technical_indicators` table on the same date, then compare: `(total_today - sum_avg_20d) / sum_avg_20d × 100`.

### Q4: PriceRepository Existing Methods
**Answer (verified from reading the file):**
- `upsert_prices(symbol, prices_df)` — bulk upsert OHLCV
- `get_latest_date(symbol)` — most recent date for a symbol
- `get_latest(symbol)` — most recent `StockPrice` row for a symbol
- `get_prices(symbol, start_date, end_date)` — list of rows in date range

**New methods needed:** `get_latest_two(symbol)` (for VNINDEX prev_close) and `get_market_aggregate()` (for advances/declines/volume). Alternatively, `get_latest` already exists for VNINDEX; the previous row needs a new method or inline query.

### Q5: FastAPI Router Registration
**Answer (verified from `app.py`):** Pattern is:
```python
from localstock.api.routes.market import router as market_router
# in create_app():
app.include_router(market_router, tags=["market"])
```
All existing routers use `router = APIRouter(prefix="/api")` in their own file. No shared prefix. Tags are lowercase strings. The new router should go after `dashboard_router` and before `admin_router` (alphabetical/logical ordering, though order doesn't affect functionality).

### Q6: Frontend Query Hook Pattern
**Answer (verified from `queries.ts`):** The exact `useMacroLatest` shape to mirror:
```typescript
export function useMacroLatest() {
  return useQuery({
    queryKey: ["macro", "latest"],
    queryFn: () => apiFetch<MacroLatestResponse>(`/api/macro/latest`),
    staleTime: 60 * 60 * 1000,
  });
}
```
`useMarketSummary` follows this exactly except: queryKey = `["market", "summary"]`, URL = `/api/market/summary`, staleTime = `30 * 60 * 1000`. The `apiFetch` wrapper throws on non-2xx responses (TanStack Query catches and sets `isError`). No `enabled` guard needed (no symbol dependency).

### Q7: MacroCards Component Structure
**Answer (verified):** Props: `{ indicators: MacroIndicator[]; isLoading?: boolean }`. Skeleton: two `Skeleton` components per card — label skeleton `h-3 w-20 mb-2` and value skeleton `h-6 w-24`. The new `MarketSummaryCards` will be a separate component (not extend MacroCards) because it needs an extra "change %" row in each card. The skeleton pattern is identical.

### Q8: Market Page Structure
**Answer (verified from reading `market/page.tsx`):** The page currently has:
1. `<h1>` — page title
2. `<section className="mb-8">` — macro cards (with `useMacroLatest`)
3. `<section>` — sector table (with `useSectorsLatest`)

The new market summary section inserts between the `<h1>` and the existing macro section (per D-08). The "as of [date]" label should be inline with the section heading (flex row, justified).

### Q9: i18n Namespace
**Answer (verified from reading both locale files):** The `market.*` namespace currently has these keys:
- `title`, `macroTitle`, `sectorTitle`, `macroError`, `sectorError`, `emptyBody`
- `macroLabels.*` — 4 indicator type keys
- `sectorColumns.*` — 4 column name keys

New keys needed (in both `en.json` and `vi.json`):
- `market.summaryTitle` — section heading
- `market.summaryError` — error fallback body text
- `market.asOf` — "As of {date}" template
- `market.summaryLabels.vnindex` — "VN-Index"
- `market.summaryLabels.totalVolume` — "Total Volume"
- `market.summaryLabels.advances` — "Advances"
- `market.summaryLabels.breadth` — "Market Breadth"

### Q10: ErrorState Props
**Answer (verified):** `{ heading?: string; body?: string }`. Both are optional — defaults come from `common.loadError` and `common.connectionError`. The market page passes only `body` (translated string). Same pattern should be used for the new summary section: `<ErrorState body={t("summaryError")} />`.

---

## Files to Create/Modify

### Backend (Prometheus)
| File | Action | What Changes |
|------|--------|--------------|
| `apps/prometheus/src/localstock/api/routes/market.py` | CREATE | New router with `GET /api/market/summary` endpoint |
| `apps/prometheus/src/localstock/db/repositories/price_repo.py` | MODIFY | Add `get_market_aggregate()` method (and optionally `get_prev(symbol)`) |
| `apps/prometheus/src/localstock/api/app.py` | MODIFY | Import + register `market_router` |

### Frontend (Helios)
| File | Action | What Changes |
|------|--------|--------------|
| `apps/helios/src/lib/types.ts` | MODIFY | Add `MarketSummaryResponse` interface |
| `apps/helios/src/lib/queries.ts` | MODIFY | Add `useMarketSummary()` hook |
| `apps/helios/src/components/market/market-summary-cards.tsx` | CREATE | New component (4 cards, skeleton, change indicators) |
| `apps/helios/src/app/market/page.tsx` | MODIFY | Add `useMarketSummary`, insert new section at top |
| `apps/helios/messages/en.json` | MODIFY | Add `market.summaryTitle`, `market.summaryError`, `market.asOf`, `market.summaryLabels.*` |
| `apps/helios/messages/vi.json` | MODIFY | Same keys in Vietnamese |

### Tests
| File | Action | What Changes |
|------|--------|--------------|
| `apps/prometheus/tests/test_market_route.py` | CREATE | Tests for router structure + endpoint response shape |

---

## Implementation Approach

**Recommended sequence:**

**Wave 0 — VNINDEX Seeding + Test Stub**
1. Seed VNINDEX into `stocks` table (via `stock_repo.add_stock("VNINDEX")` — callable from a one-time script or via the admin UI). Add VNINDEX to `exchange='INDEX'` to exclude it from advances/declines queries automatically.
2. Create `tests/test_market_route.py` stub with test class skeletons.

**Wave 1 — Backend**
3. Add `get_market_aggregate()` to `PriceRepository` — aggregate query returning advances, declines, total_volume, as_of.
4. Create `apps/prometheus/src/localstock/api/routes/market.py` with `GET /api/market/summary`.
5. Register `market_router` in `app.py`.
6. Implement tests in `test_market_route.py`.

**Wave 2 — Frontend**
7. Add `MarketSummaryResponse` type to `types.ts`.
8. Add `useMarketSummary()` hook to `queries.ts`.
9. Create `market-summary-cards.tsx` component.
10. Modify `market/page.tsx` to add the new section.
11. Add i18n keys to both locale files.

**Wave 3 — Verification**
12. Trigger VNINDEX crawl (via admin UI or manual API call).
13. Visual check of all 4 cards, skeleton, error state.

---

## Risks and Landmines

### Risk 1: VNINDEX may not be crawlable via vnstock
**Severity:** High — blocks the VN-Index card entirely.
**Context:** `vnstock` crawls individual stock OHLCV via `Quote.history(symbol)`. VNINDEX may be a special symbol that vnstock supports (it's a market index, not a stock). Whether vnstock's VCI source supports `VNINDEX` as a symbol is not verified.
**Mitigation:** The endpoint should return `vnindex: null` gracefully if no data exists. The other 3 cards (volume, advances, declines) work independently of VNINDEX.
**Confidence:** LOW — needs empirical testing.

### Risk 2: No data available at all (fresh install)
**Severity:** Medium — endpoint returns 404 or empty response if no price data exists.
**Mitigation:** Endpoint should return a structured response with all fields null and `as_of: null` rather than raising a 404. Frontend treats null fields as "—" display.

### Risk 3: `TechnicalIndicator.avg_volume_20` may be NULL for many stocks
**Severity:** Low — makes the volume % change unavailable, but total volume still works.
**Mitigation:** Return `total_volume_change_pct: null` when avg unavailable. Frontend displays "—" for the change indicator.

### Risk 4: SQL aggregate query performance
**Severity:** Low — 400 stocks × 2 rows = 800 rows in the self-join; PostgreSQL handles this trivially.
**Mitigation:** The existing `ix_stock_prices_symbol_date` composite index on `(symbol, date)` covers this query efficiently.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (mode=auto) |
| Config file | `apps/prometheus/pyproject.toml` |
| Quick run command | `uv run pytest tests/test_market_route.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-04 | Router prefix is `/api` with route `/market/summary` | unit | `pytest tests/test_market_route.py::TestMarketRouterStructure -x` | Wave 0 |
| MKT-04 | Router registered in main app | unit | `pytest tests/test_market_route.py::TestMarketAppRegistration -x` | Wave 0 |
| MKT-04 | Response schema matches expected fields | unit | `pytest tests/test_market_route.py::TestMarketSummaryResponse -x` | Wave 1 |
| MKT-03 | Frontend type `MarketSummaryResponse` has correct shape | manual/TS | `npm run build` (type check) | Wave 2 |
| MKT-03 | MarketSummaryCards renders skeleton while loading | visual | manual | Wave 3 |
| MKT-03 | MarketSummaryCards renders ErrorState on error | visual | manual | Wave 3 |

### Test pattern (follow `test_admin.py` exactly):
```python
class TestMarketRouterStructure:
    def test_router_prefix(self):
        assert market_router.prefix == "/api"

    def test_summary_route_exists(self):
        paths = [r.path for r in market_router.routes]
        assert "/api/market/summary" in paths

class TestMarketAppRegistration:
    def test_app_has_market_route(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/market/summary" in paths

class TestMarketSummaryResponse:
    async def test_response_shape_with_mocked_repo(self):
        # Mock PriceRepository to return controlled data
        # Verify response keys: vnindex, total_volume, advances, declines, breadth, as_of
        ...
```

### Wave 0 Gaps
- [ ] `tests/test_market_route.py` — covers MKT-03, MKT-04

*(No framework install needed — pytest and pytest-asyncio already configured)*

---

## Environment Availability

Step 2.6: No new external dependencies. All tools used (PostgreSQL, FastAPI, SQLAlchemy, Next.js) are already running in the dev environment. SKIPPED for detailed audit.

The only runtime concern: VNINDEX price data must be crawled via the existing admin crawl flow before the VN-Index card shows real data.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | VNINDEX is a valid symbol for vnstock's VCI crawler | Risk 1 | VN-Index card always shows null; must use a different data source |
| A2 | `stock_repo.add_stock("VNINDEX")` with exchange='INDEX' is the right seeding approach | Q1 answer | VNINDEX might be excluded from or included in wrong queries |
| A3 | The SQLAlchemy self-join for advances/declines is the most efficient approach vs Python-level computation | Q2 answer | Python loop over 400 stocks would also work but is slower |

---

## Sources

### Primary (HIGH confidence — direct file reads)
- `apps/prometheus/src/localstock/db/repositories/price_repo.py` — PriceRepository methods and StockPrice schema
- `apps/prometheus/src/localstock/db/models.py` — StockPrice columns, TechnicalIndicator.avg_volume_20, all model schemas
- `apps/prometheus/src/localstock/api/routes/macro.py` — Route structure pattern to follow
- `apps/prometheus/src/localstock/api/app.py` — Router registration pattern
- `apps/prometheus/src/localstock/db/repositories/stock_repo.py` — add_stock implementation
- `apps/helios/src/lib/queries.ts` — useMacroLatest hook pattern
- `apps/helios/src/components/market/macro-cards.tsx` — MacroCards component structure
- `apps/helios/src/app/market/page.tsx` — Market page current structure
- `apps/helios/src/lib/types.ts` — Type definition pattern
- `apps/helios/src/components/ui/error-state.tsx` — ErrorState props
- `apps/helios/messages/en.json` — i18n market.* keys
- `apps/helios/messages/vi.json` — i18n market.* keys (Vietnamese)
- `apps/prometheus/tests/test_admin.py` — Test pattern to follow

### Tertiary (LOW confidence — not verified empirically)
- A1: vnstock VCI source supports VNINDEX as a crawlable symbol — not tested in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, no new dependencies
- Architecture: HIGH — read every file in the canonical refs list
- Pitfalls: HIGH — derived from schema analysis and query logic
- VNINDEX crawlability: LOW — empirical test needed

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable codebase, no fast-moving dependencies)
