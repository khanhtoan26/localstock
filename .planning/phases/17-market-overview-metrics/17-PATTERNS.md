# Phase 17: Market Overview Metrics - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 10 (3 new, 7 modified)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/prometheus/src/localstock/api/routes/market.py` | route | request-response | `apps/prometheus/src/localstock/api/routes/macro.py` | exact |
| `apps/prometheus/src/localstock/db/repositories/price_repo.py` | repository | CRUD | `apps/prometheus/src/localstock/db/repositories/price_repo.py` (existing methods) | exact |
| `apps/prometheus/src/localstock/api/app.py` | config | request-response | `apps/prometheus/src/localstock/api/app.py` (existing router list) | exact |
| `apps/prometheus/tests/test_market_route.py` | test | request-response | `apps/prometheus/tests/test_admin.py` | exact |
| `apps/helios/src/lib/types.ts` | utility | transform | `apps/helios/src/lib/types.ts` (existing interfaces) | exact |
| `apps/helios/src/lib/queries.ts` | hook | request-response | `apps/helios/src/lib/queries.ts` (`useMacroLatest`) | exact |
| `apps/helios/src/components/market/market-summary-cards.tsx` | component | request-response | `apps/helios/src/components/market/macro-cards.tsx` | exact |
| `apps/helios/src/app/market/page.tsx` | component | request-response | `apps/helios/src/app/market/page.tsx` (existing structure) | exact |
| `apps/helios/messages/en.json` | config | transform | `apps/helios/messages/en.json` (`market.*` block) | exact |
| `apps/helios/messages/vi.json` | config | transform | `apps/helios/messages/vi.json` (`market.*` block) | exact |

---

## Pattern Assignments

### `apps/prometheus/src/localstock/api/routes/market.py` (route, request-response)

**Analog:** `apps/prometheus/src/localstock/api/routes/macro.py`

**Imports pattern** (lines 1-18 of macro.py):
```python
"""API endpoints for macro economic data."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.price_repo import PriceRepository

router = APIRouter(prefix="/api")
```

**Inline Pydantic response model pattern** (macro.py lines 22-38 — MacroInput as the model definition template):
```python
class MacroInput(BaseModel):
    indicator_type: str = Field(
        pattern=r"^(interest_rate|exchange_rate_usd_vnd|cpi|gdp)$",
        description="One of: interest_rate, exchange_rate_usd_vnd, cpi, gdp",
    )
    value: float = Field(description="Indicator value (numeric)")
    period: str = Field(min_length=4, max_length=20)
    source: str = Field(default="manual", max_length=50)
```
New file uses this pattern for the RESPONSE model (not request), e.g.:
```python
class VnindexData(BaseModel):
    value: float | None
    change_pct: float | None

class MarketSummaryResponse(BaseModel):
    vnindex: VnindexData | None
    total_volume: int | None
    total_volume_change_pct: float | None
    advances: int
    declines: int
    breadth: float | None
    as_of: str | None
```

**Core endpoint pattern** (macro.py lines 45-69 — GET handler with repo call + return dict):
```python
@router.get("/macro/latest")
async def get_latest_macro(
    session: AsyncSession = Depends(get_session),
):
    """Get latest macro indicators."""
    repo = MacroRepository(session)
    indicators = await repo.get_all_latest()
    return {
        "indicators": [...],
        "count": len(indicators),
    }
```
New endpoint mirrors this shape:
```python
@router.get("/market/summary")
async def get_market_summary(
    session: AsyncSession = Depends(get_session),
):
    """Get market summary: VN-Index, volume, advances/declines, breadth."""
    repo = PriceRepository(session)
    # ... call repo methods, build response
    return MarketSummaryResponse(...)
```

**Error handling pattern** (prices.py lines 34-36 — raise HTTPException on missing data):
```python
if not prices:
    raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
```
For market summary: return a structured response with `null` fields instead of 404 when data is unavailable (graceful degradation per Risk 2 in RESEARCH.md).

---

### `apps/prometheus/src/localstock/db/repositories/price_repo.py` (repository, CRUD) — new `get_market_aggregate()` method

**Analog:** Existing methods in the same file.

**Class constructor pattern** (price_repo.py lines 17-25):
```python
class PriceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
```

**Async select with aggregate functions pattern** (price_repo.py lines 102-115 — `get_latest_date` using `func.max`):
```python
async def get_latest_date(self, symbol: str) -> date | None:
    stmt = select(func.max(StockPrice.date)).where(StockPrice.symbol == symbol)
    result = await self.session.execute(stmt)
    return result.scalar()
```

**Async select with ordering + limit pattern** (price_repo.py lines 117-133 — `get_latest`):
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

**New method signature to add** (after `get_prices`, end of file):
```python
async def get_market_aggregate(self) -> dict:
    """Compute advances/declines/volume for most recent trading day.

    Uses self-join on stock_prices to compare today's close vs prev close.
    Excludes VNINDEX (symbol='VNINDEX') from advance/decline counts.
    Uses MAX(date) to determine the most recent available trading day
    (never date.today() — crawl data may lag).

    Returns dict with:
        as_of: date | None
        advances: int
        declines: int
        flat: int
        total_volume: int
        total_volume_change_pct: float | None

    Raises ValueError if fewer than 2 trading days of data available.
    """
```

**Imports needed** (price_repo.py lines 1-8 — add `case`, `literal_column`, or `label` as needed):
```python
from sqlalchemy import func, select, case, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
```

---

### `apps/prometheus/src/localstock/api/app.py` (config) — register market router

**Analog:** Self (existing router registration block).

**Import pattern** (app.py lines 7-16 — alphabetical router imports):
```python
from localstock.api.routes.admin import router as admin_router
from localstock.api.routes.analysis import router as analysis_router
from localstock.api.routes.automation import router as automation_router
from localstock.api.routes.dashboard import router as dashboard_router
from localstock.api.routes.health import router as health_router
from localstock.api.routes.macro import router as macro_router
# ADD HERE (alphabetical between macro and news):
from localstock.api.routes.market import router as market_router
from localstock.api.routes.news import router as news_router
```

**Router registration pattern** (app.py lines 48-57 — `include_router` calls):
```python
app.include_router(health_router, tags=["health"])
app.include_router(analysis_router, tags=["analysis"])
app.include_router(news_router, tags=["news"])
app.include_router(scores_router, tags=["scores"])
app.include_router(reports_router, tags=["reports"])
app.include_router(macro_router, tags=["macro"])
# ADD (after macro_router, before automation_router):
app.include_router(market_router, tags=["market"])
app.include_router(automation_router, tags=["automation"])
```

---

### `apps/prometheus/tests/test_market_route.py` (test, request-response)

**Analog:** `apps/prometheus/tests/test_admin.py`

**File header + imports pattern** (test_admin.py lines 1-19):
```python
"""Tests for Phase 17: Market API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from localstock.api.app import create_app
from localstock.api.routes.market import router as market_router
```

**Router structure test class pattern** (test_admin.py lines 22-50 — `TestAdminRouterStructure`):
```python
class TestMarketRouterStructure:
    def test_router_prefix(self):
        assert market_router.prefix == "/api"

    def test_summary_route_exists(self):
        paths = [r.path for r in market_router.routes]
        assert "/api/market/summary" in paths
```

**App registration test class pattern** (test_admin.py lines 53-68 — `TestAdminAppRegistration`):
```python
class TestMarketAppRegistration:
    def test_app_has_market_route(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/market/summary" in paths
```

**Endpoint callable test pattern** (test_admin.py lines 71-113 — `TestAdminEndpointFunctions`):
```python
class TestMarketEndpointFunctions:
    def test_get_market_summary_exists(self):
        from localstock.api.routes.market import get_market_summary
        assert callable(get_market_summary)
```

**Async mock test pattern** (test_admin.py lines 115-149 — `TestRequestModels` pattern, adapted for async response shape):
```python
class TestMarketSummaryResponse:
    async def test_response_shape_with_mocked_repo(self):
        # Mock PriceRepository to return controlled data
        # Verify response keys: vnindex, total_volume, advances, declines, breadth, as_of
        ...
```

**pytest-asyncio mode:** `auto` — no `@pytest.mark.asyncio` decorator needed (configured in pyproject.toml).

---

### `apps/helios/src/lib/types.ts` (utility, transform) — add `MarketSummaryResponse`

**Analog:** Existing interfaces in same file.

**Interface definition pattern** (types.ts lines 61-73 — `MacroIndicator` + `MacroLatestResponse`):
```typescript
export interface MacroIndicator {
  indicator_type: string;
  value: number;
  period: string;
  source: string;
  trend: string | null;
  recorded_at: string;
}

export interface MacroLatestResponse {
  indicators: MacroIndicator[];
  count: number;
}
```

**New interfaces to add** (after `SectorsLatestResponse`, before `StockReport`):
```typescript
export interface VnindexData {
  value: number | null;
  change_pct: number | null;
}

export interface MarketSummaryResponse {
  vnindex: VnindexData | null;
  total_volume: number | null;
  total_volume_change_pct: number | null;
  advances: number;
  declines: number;
  breadth: number | null;
  as_of: string | null;
}
```

---

### `apps/helios/src/lib/queries.ts` (hook, request-response) — add `useMarketSummary`

**Analog:** `useMacroLatest` in same file (lines 83-89).

**Direct copy pattern** (queries.ts lines 83-89):
```typescript
export function useMacroLatest() {
  return useQuery({
    queryKey: ["macro", "latest"],
    queryFn: () => apiFetch<MacroLatestResponse>(`/api/macro/latest`),
    staleTime: 60 * 60 * 1000,
  });
}
```

**New hook** (add after `useMacroLatest`, before `useSectorsLatest`):
```typescript
export function useMarketSummary() {
  return useQuery({
    queryKey: ["market", "summary"],
    queryFn: () => apiFetch<MarketSummaryResponse>(`/api/market/summary`),
    staleTime: 30 * 60 * 1000,  // D-10: 30 minutes
  });
}
```

**Import line** (queries.ts line 1 — add `MarketSummaryResponse` to the type import list):
```typescript
import type {
  TopScoresResponse,
  // ... existing types ...
  MarketSummaryResponse,   // ADD
} from "./types";
```

---

### `apps/helios/src/components/market/market-summary-cards.tsx` (component, request-response) — new file

**Analog:** `apps/helios/src/components/market/macro-cards.tsx`

**File header + imports pattern** (macro-cards.tsx lines 1-6):
```typescript
"use client";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MarketSummaryResponse } from "@/lib/types";
```

**Props interface pattern** (macro-cards.tsx lines 15-18):
```typescript
interface MarketSummaryCardsProps {
  data: MarketSummaryResponse | undefined;
  isLoading?: boolean;
}
```

**Skeleton rendering pattern** (macro-cards.tsx lines 24-37 — map over fixed keys, render 2 skeletons per card):
```typescript
if (isLoading) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {["vnindex", "totalVolume", "advances", "breadth"].map((key) => (
        <Card key={key} className="border border-border">
          <CardContent className="p-4">
            <Skeleton className="h-3 w-20 mb-2" />
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-3 w-16 mt-1" />  {/* extra row for change % */}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

**Card rendering pattern** (macro-cards.tsx lines 42-58 — card grid with label + value):
```typescript
return (
  <div className="grid grid-cols-2 gap-4">
    <Card className="border border-border">
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{t("summaryLabels.vnindex")}</p>
        <p className="text-xl font-semibold font-mono text-foreground mt-1">
          {data?.vnindex?.value != null
            ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(data.vnindex.value)
            : "—"}
        </p>
        {/* Change indicator — new on top of MacroCards pattern */}
        <p className={`text-xs mt-1 ${changePct >= 0 ? "text-green-600" : "text-red-500"}`}>
          {changePct >= 0 ? "↑" : "↓"} {Math.abs(changePct).toFixed(2)}%
        </p>
      </CardContent>
    </Card>
    {/* ... remaining 3 cards */}
  </div>
);
```

**Key difference from MacroCards:** Each card has a third row for the change % + trend arrow (green ↑ / red ↓). This is why `MarketSummaryCards` is a separate component, not a prop variant of `MacroCards`.

---

### `apps/helios/src/app/market/page.tsx` (component, request-response) — insert new section

**Analog:** Self (existing structure).

**Hook import pattern** (market/page.tsx lines 1-8):
```typescript
"use client";
import { useMacroLatest, useSectorsLatest, useMarketSummary } from "@/lib/queries";  // ADD useMarketSummary
import { useTranslations } from "next-intl";
import { MacroCards } from "@/components/market/macro-cards";
import { MarketSummaryCards } from "@/components/market/market-summary-cards";  // ADD
import { SectorTable } from "@/components/market/sector-table";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
```

**Hook call pattern** (market/page.tsx lines 10-13 — add `summary` alongside existing hooks):
```typescript
export default function MarketPage() {
  const macro = useMacroLatest();
  const sectors = useSectorsLatest();
  const summary = useMarketSummary();  // ADD
  const t = useTranslations("market");
```

**Section structure pattern** (market/page.tsx lines 19-30 — existing macro section):
```typescript
{/* Macro indicator cards */}
<section className="mb-8">
  <h2 className="text-sm font-semibold text-muted-foreground mb-4">{t("macroTitle")}</h2>
  {macro.isError ? (
    <ErrorState body={t("macroError")} />
  ) : (
    <MacroCards indicators={macro.data?.indicators || []} isLoading={macro.isLoading} />
  )}
</section>
```

**New section — insert BEFORE the macro section** (per D-08):
```typescript
{/* Market Summary section — FIRST after page title */}
<section className="mb-8">
  <div className="flex items-baseline justify-between mb-4">
    <h2 className="text-sm font-semibold text-muted-foreground">{t("summaryTitle")}</h2>
    {summary.data?.as_of && (
      <span className="text-xs text-muted-foreground">{t("asOf", { date: summary.data.as_of })}</span>
    )}
  </div>
  {summary.isError ? (
    <ErrorState body={t("summaryError")} />
  ) : (
    <MarketSummaryCards data={summary.data} isLoading={summary.isLoading} />
  )}
</section>
```

---

### `apps/helios/messages/en.json` and `apps/helios/messages/vi.json` (config) — add market.summary* keys

**Analog:** Existing `market.*` block in same files.

**Existing `market` block structure** (en.json lines 56-75):
```json
"market": {
  "title": "Market Overview",
  "macroTitle": "Macro Indicators",
  "sectorTitle": "Sector Performance",
  "macroError": "Unable to load macro data.",
  "sectorError": "Unable to load sector data.",
  "emptyBody": "No macro data available. Run pipeline to collect market data.",
  "macroLabels": {
    "interest_rate": "SBV Interest Rate",
    "exchange_rate_usd_vnd": "USD/VND Exchange Rate",
    "cpi": "CPI",
    "gdp": "GDP"
  },
  "sectorColumns": { ... }
}
```

**New keys to add** (insert after `emptyBody`, before `macroLabels`):
```json
"summaryTitle": "Market Summary",
"summaryError": "Unable to load market summary.",
"asOf": "As of {date}",
"summaryLabels": {
  "vnindex": "VN-Index",
  "totalVolume": "Total Volume",
  "advances": "Advances",
  "breadth": "Market Breadth"
},
```

**Vietnamese equivalents for vi.json** (same key paths):
```json
"summaryTitle": "Tổng quan thị trường",
"summaryError": "Không thể tải dữ liệu thị trường.",
"asOf": "Cập nhật: {date}",
"summaryLabels": {
  "vnindex": "VN-Index",
  "totalVolume": "Tổng khối lượng",
  "advances": "Tăng",
  "breadth": "Độ rộng thị trường"
},
```

**Critical rule:** Both locale files MUST be updated in the same commit (next-intl throws on missing keys — see Pitfall 6 in RESEARCH.md).

---

## Shared Patterns

### Async Session Injection
**Source:** `apps/prometheus/src/localstock/api/routes/prices.py` (lines 21-25) and `apps/prometheus/src/localstock/api/routes/macro.py` (lines 45-48)
**Apply to:** `market.py` route handler
```python
async def get_market_summary(
    session: AsyncSession = Depends(get_session),
):
    repo = PriceRepository(session)
```

### SQLAlchemy `func.max` for Latest Date
**Source:** `apps/prometheus/src/localstock/db/repositories/price_repo.py` (lines 102-115)
**Apply to:** New `get_market_aggregate()` — use `func.max(StockPrice.date)` to find the latest trading day, NEVER `date.today()`
```python
stmt = select(func.max(StockPrice.date)).where(StockPrice.symbol == symbol)
result = await self.session.execute(stmt)
latest_date = result.scalar()
```

### ErrorState Usage
**Source:** `apps/helios/src/components/ui/error-state.tsx` (lines 1-22) + `apps/helios/src/app/market/page.tsx` (lines 22-24)
**Apply to:** `market/page.tsx` new summary section, `market-summary-cards.tsx` (via parent)
```typescript
{summary.isError ? (
  <ErrorState body={t("summaryError")} />
) : (
  <MarketSummaryCards ... />
)}
```

### TanStack Query Hook Shape
**Source:** `apps/helios/src/lib/queries.ts` lines 83-89 (`useMacroLatest`)
**Apply to:** `useMarketSummary` in queries.ts
```typescript
return useQuery({
  queryKey: ["market", "summary"],
  queryFn: () => apiFetch<MarketSummaryResponse>(`/api/market/summary`),
  staleTime: 30 * 60 * 1000,
});
```

### Skeleton Loading in Card Grid
**Source:** `apps/helios/src/components/market/macro-cards.tsx` (lines 24-37)
**Apply to:** `market-summary-cards.tsx` — identical grid + per-card skeleton structure, with one extra `Skeleton` row for the change % indicator
```typescript
<div className="grid grid-cols-2 gap-4">
  {keys.map((key) => (
    <Card key={key} className="border border-border">
      <CardContent className="p-4">
        <Skeleton className="h-3 w-20 mb-2" />
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-3 w-16 mt-1" />
      </CardContent>
    </Card>
  ))}
</div>
```

### Pydantic Inline Model Definition
**Source:** `apps/prometheus/src/localstock/api/routes/macro.py` (lines 22-43)
**Apply to:** `market.py` — define `VnindexData` and `MarketSummaryResponse` Pydantic models inline in the route file (not in a shared schemas.py)

### TypeScript Interface Pattern
**Source:** `apps/helios/src/lib/types.ts` (lines 61-87)
**Apply to:** New `VnindexData` and `MarketSummaryResponse` interfaces in types.ts — use `number | null` for optional numeric fields

---

## No Analog Found

All files have close analogs in the codebase. No files require fallback to RESEARCH.md patterns exclusively.

| File | Role | Note |
|------|------|-------|
| `market-summary-cards.tsx` | component | Close analog is `macro-cards.tsx`; differs only in adding a change % row. Not a gap — a deliberate extension. |

---

## Metadata

**Analog search scope:** `apps/prometheus/src/localstock/api/routes/`, `apps/prometheus/src/localstock/db/repositories/`, `apps/prometheus/tests/`, `apps/helios/src/lib/`, `apps/helios/src/components/market/`, `apps/helios/src/app/market/`, `apps/helios/messages/`
**Files scanned:** 13 source files read directly
**Pattern extraction date:** 2026-04-25
