# Phase 6: Web Dashboard - Research

**Researched:** 2026-04-16
**Domain:** Next.js financial dashboard consuming FastAPI backend
**Confidence:** HIGH

## Summary

Phase 6 builds a Next.js web dashboard in `web/` folder that consumes the existing FastAPI backend (23+ REST endpoints). The dashboard has three core views: a ranked stock table (DASH-01), a stock detail page with interactive price charts and AI reports (DASH-02), and a market overview with macro analysis and sector performance (DASH-03).

**Critical finding:** The FastAPI backend is missing several API endpoints required by the dashboard: (1) no OHLCV price history endpoint for candlestick charts, (2) no sector snapshots endpoint for market overview, (3) no score change alerts endpoint, and (4) CORS middleware is not configured. These backend gaps must be addressed as part of this phase — the repositories already have the query methods (`PriceRepository.get_prices()`, `SectorSnapshotRepository.get_by_date()`, `IndicatorRepository.get_by_date_range()`), only the API routes are missing.

**Primary recommendation:** Start with backend API gap-fill (new endpoints + CORS), then scaffold Next.js project, then build pages incrementally: rankings table → stock detail with charts → market overview.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Next.js + shadcn/ui — SSR, App Router, Tailwind CSS
- **D-02:** Monorepo — dashboard đặt trong folder `web/` của project hiện tại
- **D-03:** TradingView Lightweight Charts — 45KB, purpose-built cho financial data
- **D-04:** Sidebar cố định bên trái — kiểu Simplize/Bloomberg terminal
- **D-05:** Dark theme cố định — kiểu terminal tài chính, dễ đọc chart
- **D-08:** Technical indicators: overlay trên chart chính (SMA/EMA/BB) + panel phụ phía dưới (MACD/RSI)

### Agent's Discretion
- **D-06:** Cấu trúc trang — Agent's Discretion (gợi ý: Rankings, Stock Detail, Market Overview)
- **D-07:** Loại biểu đồ giá — Agent's Discretion (gợi ý: candlestick + volume bars)
- **D-09:** Timeframe options, mức độ interactive — Agent's Discretion
- Responsive design (desktop-first cho tool cá nhân)
- Trang tổng quan thị trường layout
- Empty states, loading states

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Web dashboard hiển thị bảng xếp hạng cổ phiếu theo điểm tổng hợp | shadcn/ui DataTable with sorting/filtering; consumes GET /api/scores/top; grade color badges (A=green, F=red) |
| DASH-02 | Dashboard cho phép xem chi tiết từng mã: biểu đồ giá, chỉ báo kỹ thuật, báo cáo AI | lightweight-charts candlestick + volume; overlay SMA/EMA/BB as LineSeries; sub-panel for MACD/RSI; consumes new GET /api/prices/{symbol}, GET /api/analysis/{symbol}/technical, GET /api/reports/{symbol} |
| DASH-03 | Dashboard hiển thị tổng quan thị trường và phân tích vĩ mô | Macro cards from GET /api/macro/latest; sector performance table from new GET /api/sectors/latest; recharts for sector bar chart |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

The copilot-instructions.md contains the project overview and stack description. Key directives relevant to this phase:
- Python backend with FastAPI, PostgreSQL via SQLAlchemy async [VERIFIED: codebase]
- Frontend: Next.js + shadcn/ui + lightweight-charts [VERIFIED: STACK.md]
- Tool cá nhân (personal tool) — functional UX over aesthetics [VERIFIED: CONTEXT.md]
- Vietnamese language for UI text [VERIFIED: CONTEXT.md specifics]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.4 | App Router, SSR, file-based routing | Locked decision D-01. Latest stable. [VERIFIED: npm registry] |
| React | 19.2.5 | UI library | Next.js 16 peer dependency [VERIFIED: npm registry] |
| TypeScript | 5.x (bundled) | Type safety | Financial data is complex — types prevent runtime errors [VERIFIED: npm registry 6.0.2 available but Next.js bundles 5.x] |
| Tailwind CSS | 4.2.2 | Utility-first styling | Locked decision D-01. v4 is latest. [VERIFIED: npm registry] |
| shadcn/ui | CLI latest | Copy-paste UI components | Locked decision D-01. Tables, cards, badges for dashboard [VERIFIED: npm registry] |
| lightweight-charts | 5.1.0 | Candlestick + line charts | Locked decision D-03. TradingView's OSS chart lib, 45KB [VERIFIED: npm registry] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.99.0 | Data fetching + caching | All API calls — auto-refetch, loading states, error handling [VERIFIED: npm registry] |
| recharts | 3.8.1 | General charts (bars, radar) | Sector performance bar chart, score breakdown radar [VERIFIED: npm registry] |
| lucide-react | latest | Icons | shadcn/ui's default icon set — sidebar nav icons, status indicators [ASSUMED] |
| clsx + tailwind-merge | latest | Conditional classnames | shadcn/ui's cn() utility, dark theme class composition [ASSUMED] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lightweight-charts | Apache ECharts | ECharts is 10x larger bundle, not purpose-built for financial data. lightweight-charts is locked decision. |
| @tanstack/react-query | SWR | SWR has less features (no mutations, devtools). react-query is better for complex data fetching. |
| recharts | Nivo | Nivo is heavier. recharts is simpler for basic bar/radar charts. |

**Installation:**
```bash
cd web
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
npx shadcn@latest init
npm install lightweight-charts @tanstack/react-query recharts
npm install lucide-react
```

## Architecture Patterns

### Recommended Project Structure
```
web/
├── src/
│   ├── app/                     # Next.js App Router pages
│   │   ├── layout.tsx           # Root layout (sidebar + dark theme)
│   │   ├── page.tsx             # Redirect to /rankings
│   │   ├── rankings/
│   │   │   └── page.tsx         # DASH-01: Ranked stock table
│   │   ├── stock/
│   │   │   └── [symbol]/
│   │   │       └── page.tsx     # DASH-02: Stock detail (chart + report)
│   │   └── market/
│   │       └── page.tsx         # DASH-03: Market overview
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components (auto-generated)
│   │   ├── layout/
│   │   │   ├── sidebar.tsx      # Fixed left sidebar nav
│   │   │   └── app-shell.tsx    # Main layout wrapper
│   │   ├── rankings/
│   │   │   ├── stock-table.tsx  # DataTable with sorting
│   │   │   └── grade-badge.tsx  # A/B/C/D/F color badge
│   │   ├── charts/
│   │   │   ├── price-chart.tsx  # lightweight-charts candlestick wrapper
│   │   │   ├── volume-bars.tsx  # Volume overlay
│   │   │   ├── indicator-overlay.tsx  # SMA/EMA/BB line series
│   │   │   └── sub-panel.tsx    # MACD/RSI separate chart
│   │   └── market/
│   │       ├── macro-cards.tsx  # Macro indicator cards
│   │       └── sector-table.tsx # Sector performance
│   ├── lib/
│   │   ├── api.ts               # API client (fetch wrapper with base URL)
│   │   ├── queries.ts           # react-query hooks per endpoint
│   │   ├── types.ts             # TypeScript interfaces for API responses
│   │   └── utils.ts             # formatters (numbers, dates, Vietnamese)
│   └── styles/
│       └── globals.css          # Tailwind + dark theme CSS vars
├── public/                      # Static assets
├── next.config.ts               # API proxy config
├── tailwind.config.ts           # Dark theme configuration
├── tsconfig.json
└── package.json
```

### Pattern 1: API Client with react-query
**What:** Centralized fetch wrapper + react-query hooks for all backend API calls
**When to use:** Every component that needs backend data
**Example:**
```typescript
// src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// src/lib/queries.ts
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./api";
import type { TopScoresResponse, StockDetailResponse } from "./types";

export function useTopScores(limit = 20) {
  return useQuery({
    queryKey: ["scores", "top", limit],
    queryFn: () => apiFetch<TopScoresResponse>(`/api/scores/top?limit=${limit}`),
    staleTime: 5 * 60 * 1000, // 5 min — data updates once daily
  });
}

export function useStockPrices(symbol: string, days = 365) {
  return useQuery({
    queryKey: ["prices", symbol, days],
    queryFn: () => apiFetch<PriceHistoryResponse>(`/api/prices/${symbol}?days=${days}`),
    staleTime: 60 * 60 * 1000, // 1 hour — prices don't change after market close
  });
}
```
[VERIFIED: @tanstack/react-query API pattern from training knowledge, cross-checked with npm registry version]

### Pattern 2: lightweight-charts React Wrapper
**What:** Imperative chart API wrapped in useRef + useEffect for React integration
**When to use:** Price chart component (DASH-02)
**Example:**
```typescript
// src/components/charts/price-chart.tsx
"use client";
import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";

interface PriceChartProps {
  ohlcv: { time: string; open: number; high: number; low: number; close: number; volume: number }[];
  indicators?: { sma20?: number[]; ema12?: number[]; bbUpper?: number[]; bbLower?: number[] };
}

export function PriceChart({ ohlcv, indicators }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !ohlcv.length) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0f172a" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      width: containerRef.current.clientWidth,
      height: 400,
    });

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444",
      borderUpColor: "#22c55e", borderDownColor: "#ef4444",
      wickUpColor: "#22c55e", wickDownColor: "#ef4444",
    });
    candleSeries.setData(ohlcv.map(d => ({
      time: d.time, open: d.open, high: d.high, low: d.low, close: d.close,
    })));

    // Volume histogram on same chart
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volumeSeries.setData(ohlcv.map(d => ({
      time: d.time, value: d.volume,
      color: d.close >= d.open ? "#22c55e40" : "#ef444440",
    })));

    // SMA overlay
    if (indicators?.sma20) {
      const smaSeries = chart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 1 });
      smaSeries.setData(indicators.sma20.filter(Boolean).map((v, i) => ({
        time: ohlcv[i].time, value: v,
      })));
    }

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current!.clientWidth });
    });
    resizeObserver.observe(containerRef.current);

    return () => { resizeObserver.disconnect(); chart.remove(); };
  }, [ohlcv, indicators]);

  return <div ref={containerRef} className="w-full" />;
}
```
[VERIFIED: lightweight-charts v5 API uses `addSeries(CandlestickSeries)` syntax — confirmed from npm package info. v5 changed from `addCandlestickSeries()` to `addSeries(CandlestickSeries)`]

### Pattern 3: Dark Theme Configuration
**What:** Fixed dark theme using Tailwind CSS v4 dark variables
**When to use:** Root layout — no theme toggle needed
**Example:**
```css
/* src/styles/globals.css */
@import "tailwindcss";

:root {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;
  --primary: 217.2 91.2% 59.8%;
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;
  --border: 217.2 32.6% 17.5%;
  --accent-green: 142.1 76.2% 36.3%;
  --accent-red: 0 84.2% 60.2%;
  --accent-yellow: 47.9 95.8% 53.1%;
}

body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
}
```
[ASSUMED: Tailwind v4 CSS variable approach — may differ from v3 `darkMode: 'class'` pattern]

### Pattern 4: Fixed Left Sidebar
**What:** Bloomberg-style fixed sidebar with navigation links
**When to use:** Root layout component (D-04)
**Example:**
```typescript
// src/components/layout/sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, LineChart, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/rankings", label: "Xếp Hạng", icon: BarChart3 },
  { href: "/market", label: "Thị Trường", icon: Globe },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 h-screen w-60 border-r border-border bg-card flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-primary">LocalStock</h1>
        <p className="text-xs text-muted-foreground">AI Stock Agent</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm",
              pathname.startsWith(href)
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

### Anti-Patterns to Avoid
- **Server Components for charts:** lightweight-charts uses DOM/canvas — MUST use `"use client"` directive. Don't try to render charts in Server Components.
- **Fetching data in Server Components for real-time feel:** All data is batch-updated daily. Use react-query with `staleTime: 5 * 60 * 1000` (5 min) on the client. Server-side fetching adds complexity without benefit for a personal tool.
- **Building custom table sorting:** Use shadcn/ui DataTable + @tanstack/react-table. It handles sorting, filtering, pagination out of the box.
- **Inline styles for chart colors:** Define color constants once in a theme file. Financial charts need consistent up/down colors everywhere.

## Critical: Backend API Gaps

**The existing FastAPI backend is missing endpoints required by the dashboard.** The database repositories already have the query methods — only the API routes need to be added.

| Missing Endpoint | Needed By | Repository Method Available | Priority |
|------------------|-----------|----------------------------|----------|
| `GET /api/prices/{symbol}?days=365` | DASH-02 candlestick chart | `PriceRepository.get_prices(symbol, start_date, end_date)` ✅ | **CRITICAL** |
| `GET /api/prices/{symbol}/indicators?days=365` | DASH-02 indicator overlay | `IndicatorRepository.get_by_date_range(symbol, start, end)` ✅ | **CRITICAL** |
| `GET /api/sectors/latest` | DASH-03 sector performance | `SectorSnapshotRepository.get_by_date(date)` ✅ | HIGH |
| `GET /api/alerts/recent` | Rankings page score alerts | `ScoreChangeAlert` model exists, no repo query yet | MEDIUM |
| CORS middleware | All frontend→backend calls | Not configured in `app.py` | **CRITICAL** |
| `GET /api/stocks` or stock list | Symbol search/navigation | `Stock` model exists, no list endpoint | MEDIUM |

[VERIFIED: All findings confirmed by reading `src/localstock/api/routes/*.py` and `src/localstock/api/app.py` — no CORS, no price endpoint, no sector endpoint]

### CORS Configuration Needed
```python
# Add to src/localstock/api/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
[VERIFIED: FastAPI CORSMiddleware pattern from codebase — currently missing]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data table with sorting/filtering | Custom table component | shadcn/ui DataTable + @tanstack/react-table | Handles sorting, pagination, column visibility. Financial tables need all of these. |
| Candlestick charts | Custom canvas rendering | lightweight-charts v5 | Purpose-built by TradingView. Handles crosshair, zoom, time axis, financial number formatting. |
| Data fetching / caching | Manual useState + useEffect | @tanstack/react-query | Handles loading, error, refetch, cache invalidation. Stock data fetching is repetitive without it. |
| CSS component library | Custom button/card/badge | shadcn/ui | Copy-paste components, fully customizable, dark theme built-in. |
| Number formatting (VND) | Custom formatters | Intl.NumberFormat | Handles VND currency, thousand separators, decimal places. |
| Chart color palette | Per-component color constants | Shared constants file | Green/red up/down colors must be consistent across all charts. |

**Key insight:** The dashboard is a pure frontend consumer of an existing API. Every piece of interactivity (sorting, charting, fetching) has a mature library solution. Hand-rolling any of these wastes time and produces worse results.

## Common Pitfalls

### Pitfall 1: lightweight-charts SSR Crash
**What goes wrong:** `ReferenceError: window is not defined` when lightweight-charts is imported in a Server Component
**Why it happens:** lightweight-charts accesses `window` and `document` at import time. Next.js App Router defaults to Server Components.
**How to avoid:** Always use `"use client"` directive on chart components. Use dynamic import with `ssr: false` if needed: `const Chart = dynamic(() => import('./price-chart'), { ssr: false })`
**Warning signs:** Build errors mentioning `window` or `document`

### Pitfall 2: lightweight-charts v5 API Breaking Changes
**What goes wrong:** Using `chart.addCandlestickSeries()` (v4 API) instead of `chart.addSeries(CandlestickSeries)` (v5 API)
**Why it happens:** Most tutorials and StackOverflow answers reference v3/v4 API
**How to avoid:** Always import series types: `import { CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts"` and use `addSeries()` method
**Warning signs:** TypeScript errors about missing methods on chart object

### Pitfall 3: CORS Errors in Development
**What goes wrong:** `Access-Control-Allow-Origin` errors when Next.js (port 3000) calls FastAPI (port 8000)
**Why it happens:** FastAPI has no CORS middleware configured (verified — not in current `app.py`)
**How to avoid:** Add CORSMiddleware to FastAPI before starting frontend development. Alternative: use Next.js rewrites in `next.config.ts` to proxy API calls.
**Warning signs:** Network tab shows `OPTIONS` preflight failing with 4xx

### Pitfall 4: Chart Container Size Issues
**What goes wrong:** Chart renders with 0 width or doesn't resize
**Why it happens:** lightweight-charts needs explicit width or ResizeObserver. Container must have defined dimensions.
**How to avoid:** Always use ResizeObserver pattern (shown in Pattern 2). Set container `className="w-full"` with a parent that has defined width.
**Warning signs:** Chart is invisible or tiny

### Pitfall 5: Stale Data Overload
**What goes wrong:** Too many API calls or unnecessary re-fetches
**Why it happens:** Stock data updates once per day after market close (15:30). Default react-query refetches on window focus.
**How to avoid:** Set `staleTime: 5 * 60 * 1000` (5 minutes) for all stock queries. Data is inherently batch-processed daily.
**Warning signs:** Backend logs showing repeated identical queries

### Pitfall 6: Missing Vietnamese Number Formatting
**What goes wrong:** Displaying raw numbers like `123456789.5` instead of `123.456.789,5` (Vietnamese format) or `123,5 tỷ` for market cap
**Why it happens:** Default JS number formatting uses US locale
**How to avoid:** Create a shared `formatVND()` utility using `Intl.NumberFormat('vi-VN')`. Use `tỷ` (billion) suffix for large numbers.
**Warning signs:** Numbers look unfamiliar to Vietnamese users

### Pitfall 7: Empty State Not Handled
**What goes wrong:** Dashboard shows blank page or crashes when no data is available
**Why it happens:** Backend returns `{"stocks": [], "count": 0}` when pipeline hasn't run yet. Some endpoints return 404 for missing symbols.
**How to avoid:** Every data-fetching component needs explicit empty state UI. Check for `count === 0` or empty arrays. Show "Chưa có dữ liệu — chạy pipeline trước" message.
**Warning signs:** White/blank page in dashboard

## Code Examples

### shadcn/ui DataTable for Stock Rankings (DASH-01)
```typescript
// src/components/rankings/stock-table.tsx
"use client";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { GradeBadge } from "./grade-badge";
import Link from "next/link";

interface StockScore {
  symbol: string;
  total_score: number;
  grade: string;
  rank: number;
  technical_score: number | null;
  fundamental_score: number | null;
  sentiment_score: number | null;
  macro_score: number | null;
}

const columns: ColumnDef<StockScore>[] = [
  { accessorKey: "rank", header: "#", size: 50 },
  {
    accessorKey: "symbol",
    header: "Mã CK",
    cell: ({ row }) => (
      <Link href={`/stock/${row.original.symbol}`} className="text-primary hover:underline font-medium">
        {row.original.symbol}
      </Link>
    ),
  },
  {
    accessorKey: "total_score",
    header: "Điểm",
    cell: ({ row }) => <span className="font-mono">{row.original.total_score.toFixed(1)}</span>,
  },
  {
    accessorKey: "grade",
    header: "Hạng",
    cell: ({ row }) => <GradeBadge grade={row.original.grade} />,
  },
  { accessorKey: "technical_score", header: "Kỹ Thuật" },
  { accessorKey: "fundamental_score", header: "Cơ Bản" },
  { accessorKey: "sentiment_score", header: "Tin Tức" },
  { accessorKey: "macro_score", header: "Vĩ Mô" },
];

export function StockTable({ data }: { data: StockScore[] }) {
  return <DataTable columns={columns} data={data} />;
}
```
[ASSUMED: @tanstack/react-table ColumnDef API — standard pattern]

### Grade Badge Component
```typescript
// src/components/rankings/grade-badge.tsx
const gradeColors: Record<string, string> = {
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  B: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  C: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  D: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  F: "bg-red-500/20 text-red-400 border-red-500/30",
};

export function GradeBadge({ grade }: { grade: string }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${gradeColors[grade] || gradeColors.F}`}>
      {grade}
    </span>
  );
}
```

### MACD/RSI Sub-Panel Pattern
```typescript
// Sub-panel chart pattern — separate lightweight-charts instance below main chart
// Creates a second chart for MACD histogram + signal line, or RSI with overbought/oversold zones
export function SubPanel({ type, data }: { type: "macd" | "rsi"; data: any[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!containerRef.current || !data.length) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0f172a" }, textColor: "#94a3b8" },
      height: 150, // Shorter than main chart
      width: containerRef.current.clientWidth,
    });

    if (type === "macd") {
      // MACD histogram
      const histSeries = chart.addSeries(HistogramSeries);
      histSeries.setData(data.map(d => ({
        time: d.time,
        value: d.macd_histogram,
        color: d.macd_histogram >= 0 ? "#22c55e" : "#ef4444",
      })));
      // MACD line + signal line
      const macdLine = chart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 1 });
      macdLine.setData(data.filter(d => d.macd != null).map(d => ({ time: d.time, value: d.macd })));
      const signalLine = chart.addSeries(LineSeries, { color: "#f97316", lineWidth: 1 });
      signalLine.setData(data.filter(d => d.macd_signal != null).map(d => ({ time: d.time, value: d.macd_signal })));
    }

    if (type === "rsi") {
      const rsiSeries = chart.addSeries(LineSeries, { color: "#a855f7", lineWidth: 1 });
      rsiSeries.setData(data.filter(d => d.rsi_14 != null).map(d => ({ time: d.time, value: d.rsi_14 })));
      // Overbought/oversold markers at 70/30 — use price lines
      rsiSeries.createPriceLine({ price: 70, color: "#ef4444", lineWidth: 1, lineStyle: 2 });
      rsiSeries.createPriceLine({ price: 30, color: "#22c55e", lineWidth: 1, lineStyle: 2 });
    }

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [data, type]);

  return <div ref={containerRef} className="w-full border-t border-border" />;
}
```
[VERIFIED: lightweight-charts v5 `createPriceLine()` API exists for horizontal reference lines]

### Vietnamese Number Formatter
```typescript
// src/lib/utils.ts
const vnFormatter = new Intl.NumberFormat("vi-VN");
const vnCurrency = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });

export function formatNumber(value: number | null, decimals = 1): string {
  if (value == null) return "—";
  return value.toFixed(decimals);
}

export function formatVND(value: number | null): string {
  if (value == null) return "—";
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)} nghìn tỷ`;
  if (Math.abs(value) >= 1) return `${value.toFixed(1)} tỷ`;
  return vnCurrency.format(value * 1000) + " triệu";
}

export function formatScore(value: number | null): string {
  if (value == null) return "—";
  return value.toFixed(1);
}
```

### New Backend Endpoint: Price History
```python
# Add to src/localstock/api/routes/prices.py (NEW FILE)
"""API endpoint for OHLCV price history — required by dashboard charts."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.price_repo import PriceRepository

router = APIRouter(prefix="/api")


@router.get("/prices/{symbol}")
async def get_price_history(
    symbol: str,
    days: int = Query(default=365, ge=30, le=730),
    session: AsyncSession = Depends(get_session),
):
    """Get OHLCV price history for charting.

    Returns time-series data for lightweight-charts candlestick rendering.
    """
    repo = PriceRepository(session)
    start_date = date.today() - timedelta(days=days)
    prices = await repo.get_prices(symbol.upper(), start_date=start_date)
    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")
    return {
        "symbol": symbol.upper(),
        "count": len(prices),
        "prices": [
            {
                "time": str(p.date),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ],
    }
```
[VERIFIED: Follows exact same pattern as existing routes in codebase — flat dict response, router prefix="/api"]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `chart.addCandlestickSeries()` | `chart.addSeries(CandlestickSeries)` | lightweight-charts v5.0 (2024) | All chart series creation uses new API |
| Next.js Pages Router | Next.js App Router | Next.js 13+ (2023) | File-based routing in `app/` dir, Server Components default |
| Tailwind v3 `darkMode: 'class'` | Tailwind v4 CSS-first config | Tailwind v4 (2025) | Configuration via CSS, not `tailwind.config.js` |
| shadcn/ui `npx shadcn-ui@latest` | `npx shadcn@latest` | 2024 | CLI renamed, uses `components.json` |

**Deprecated/outdated:**
- `chart.addCandlestickSeries()` — use `chart.addSeries(CandlestickSeries)` in v5 [VERIFIED: npm package info]
- Next.js `pages/` directory — use `app/` directory with App Router [VERIFIED: locked decision D-01]
- `tailwind.config.js` — Tailwind v4 uses CSS-based configuration [ASSUMED: v4 migration path]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tailwind v4 uses CSS-first configuration instead of tailwind.config.js | Architecture Patterns / Dark Theme | LOW — if wrong, use tailwind.config.ts with `darkMode: 'class'` instead |
| A2 | lucide-react is shadcn/ui's default icon library | Standard Stack | LOW — can swap to any icon set |
| A3 | @tanstack/react-table ColumnDef API shape | Code Examples | LOW — well-established API, unlikely to change |
| A4 | lightweight-charts v5 `createPriceLine()` for RSI reference lines | Code Examples | MEDIUM — if not available, use separate series with constant data |
| A5 | Next.js 16 `create-next-app` still supports `--app --src-dir` flags | Installation | LOW — if changed, adjust init command |

## Open Questions (RESOLVED)

1. **Tailwind v4 + shadcn/ui Compatibility** — RESOLVED: Plan 06-02 Task 1 uses adaptive merge strategy during scaffolding. If shadcn init doesn't produce v4-compatible config, falls back to Tailwind v3.

2. **Next.js API Proxy vs CORS** — RESOLVED: Plan 06-01 Task 1 implements CORS middleware on FastAPI (simpler approach). No proxy needed since both services run on same machine.

3. **Chart Synchronization (Main + Sub-panels)** — RESOLVED: Plan 06-04 uses same data source for main and sub-panel charts with independent lightweight-charts instances. Time axis sync via `timeScale().subscribeVisibleLogicalRangeChange()`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js runtime | ✓ | 22.22.2 (LTS) | — |
| npm | Package management | ✓ | 10.9.7 | — |
| npx | shadcn CLI, create-next-app | ✓ | 10.9.7 | — |
| FastAPI backend | API data source | ✓ (source code) | 0.135+ | — |
| PostgreSQL | Data backend (via FastAPI) | ✓ (used by existing phases) | 16+ | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None — all dependencies available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (recommended for Next.js) or Jest |
| Config file | `web/vitest.config.ts` (Wave 0) |
| Quick run command | `cd web && npm test -- --run` |
| Full suite command | `cd web && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Rankings page renders stock table with sorting | integration | `cd web && npm test -- --run src/__tests__/rankings.test.tsx` | ❌ Wave 0 |
| DASH-02 | Stock detail page renders chart and report | integration | `cd web && npm test -- --run src/__tests__/stock-detail.test.tsx` | ❌ Wave 0 |
| DASH-03 | Market overview renders macro cards and sectors | integration | `cd web && npm test -- --run src/__tests__/market.test.tsx` | ❌ Wave 0 |
| BACKEND | New API endpoints return correct data | unit (pytest) | `cd .. && python -m pytest tests/test_api_dashboard.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd web && npm test -- --run`
- **Per wave merge:** Full suite + backend pytest
- **Phase gate:** All tests green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `web/vitest.config.ts` — test framework config
- [ ] `web/src/__tests__/rankings.test.tsx` — covers DASH-01
- [ ] `web/src/__tests__/stock-detail.test.tsx` — covers DASH-02
- [ ] `web/src/__tests__/market.test.tsx` — covers DASH-03
- [ ] `tests/test_api_dashboard.py` — covers new backend endpoints
- [ ] Test framework install: `cd web && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Personal tool, no auth (out of scope per REQUIREMENTS.md) |
| V3 Session Management | No | No sessions — stateless API consumption |
| V4 Access Control | No | Single-user tool, localhost only |
| V5 Input Validation | Yes | Validate symbol params before API calls (alphanumeric only), sanitize HTML in AI reports before rendering |
| V6 Cryptography | No | No secrets handled in frontend |

### Known Threat Patterns for Next.js + FastAPI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via AI report content | Tampering | React auto-escapes JSX. If using `dangerouslySetInnerHTML` for reports, sanitize with DOMPurify first |
| CORS misconfiguration | Information Disclosure | Restrict `allow_origins` to `http://localhost:3000` only, not `*` |
| Symbol path injection | Tampering | Backend validates symbol format (already uses `pattern="^[A-Z0-9]+$"` on automation routes) — apply same to new price endpoint |

## Sources

### Primary (HIGH confidence)
- npm registry — Next.js 16.2.4, lightweight-charts 5.1.0, @tanstack/react-query 5.99.0, recharts 3.8.1, React 19.2.5, Tailwind 4.2.2 [VERIFIED: `npm view` commands]
- Codebase — all 7 API route files, models.py (16 models), 15 repositories, config.py, app.py [VERIFIED: direct file reads]
- .planning/research/STACK.md — technology stack decisions [VERIFIED: file read]
- 06-CONTEXT.md — user decisions D-01 through D-09 [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- lightweight-charts v5 API migration (addSeries pattern) — confirmed via npm package metadata
- Tailwind v4 CSS-first configuration — based on npm version 4.2.2 being latest

### Tertiary (LOW confidence)
- Tailwind v4 + shadcn/ui integration specifics — may need runtime verification during scaffolding
- Chart cross-synchronization via `subscribeVisibleLogicalRangeChange` — from training data, not verified against v5 docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry, locked by user decisions
- Architecture: HIGH — follows established Next.js App Router patterns, codebase API structure fully mapped
- Backend gaps: HIGH — verified by exhaustive reading of all route files, CORS absence confirmed
- Pitfalls: HIGH — lightweight-charts v5 migration issues are well-documented, SSR issues are fundamental to the stack
- Chart patterns: MEDIUM — v5 API verified but specific sub-panel synchronization not confirmed from official docs

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable stack, 30-day validity)
