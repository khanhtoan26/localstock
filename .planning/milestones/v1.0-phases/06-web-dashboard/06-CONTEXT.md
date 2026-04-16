# Phase 6: Web Dashboard - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Xây dựng web dashboard hiển thị: bảng xếp hạng cổ phiếu theo grade/score, trang chi tiết từng mã (biểu đồ giá, chỉ báo kỹ thuật, báo cáo AI), và tổng quan thị trường kèm phân tích vĩ mô.

</domain>

<decisions>
## Implementation Decisions

### Tech Stack
- **D-01:** Next.js + shadcn/ui — SSR, App Router, Tailwind CSS
- **D-02:** Monorepo — dashboard đặt trong folder `web/` của project hiện tại
- **D-03:** TradingView Lightweight Charts — 45KB, purpose-built cho financial data

### Layout & Navigation
- **D-04:** Sidebar cố định bên trái — kiểu Simplize/Bloomberg terminal
- **D-05:** Dark theme cố định — kiểu terminal tài chính, dễ đọc chart
- **D-06:** Cấu trúc trang — Agent's Discretion (gợi ý: Rankings, Stock Detail, Market Overview)

### Charts & Indicators
- **D-07:** Loại biểu đồ giá — Agent's Discretion (gợi ý: candlestick + volume bars)
- **D-08:** Technical indicators: overlay trên chart chính (SMA/EMA/BB) + panel phụ phía dưới (MACD/RSI)
- **D-09:** Timeframe options, mức độ interactive — Agent's Discretion

### Agent's Discretion
- Responsive design (desktop-first cho tool cá nhân)
- Trang tổng quan thị trường layout
- Empty states, loading states

### Carrying forward
- Supabase/PostgreSQL database (Phase 1) — data source cho dashboard
- FastAPI backend có 23 API routes sẵn sàng (scores, analysis, reports, macro, news, automation)
- Grade letters A/B/C/D/F + composite scores (Phase 3)
- AI reports tiếng Việt (Phase 4)
- Macro analysis (Phase 4)
- Score change detection + sector rotation (Phase 5)

</decisions>

<canonical_refs>
## Canonical References

### Requirements
- `.planning/REQUIREMENTS.md` — DASH-01, DASH-02, DASH-03

### Research
- `.planning/research/STACK.md` — Next.js, shadcn/ui, lightweight-charts 5.1.0
- `.planning/research/FEATURES.md` — Dashboard features, competitor analysis (Simplize, WiChart)

### Backend API (data source)
- `src/localstock/api/routes/scores.py` — GET /scores/top, GET /scores/{symbol}
- `src/localstock/api/routes/analysis.py` — GET /analysis/{symbol}/technical, fundamental, trend
- `src/localstock/api/routes/reports.py` — GET /reports/top, GET /reports/{symbol}
- `src/localstock/api/routes/macro.py` — GET /macro/latest
- `src/localstock/api/routes/news.py` — GET /news, GET /news/{symbol}/sentiment
- `src/localstock/api/routes/automation.py` — GET /automation/status, POST /automation/run

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- FastAPI backend: 23 REST endpoints across 7 route modules
- Database: PostgreSQL via SQLAlchemy async (scores, reports, macro data, indicators, news)
- All data available via API — dashboard is pure frontend consumer

### Established Patterns
- API returns flat JSON dicts (no Pydantic response models)
- All endpoints under /api/ prefix
- CORS needs to be configured for Next.js dev server

</code_context>

<specifics>
## Specific Ideas

- TradingView lightweight-charts (45KB) — purpose-built cho financial data
- Dashboard là phase cuối — tất cả data đã sẵn sàng từ Phase 1-5
- Tool cá nhân nên UX functional > đẹp
- Dark theme kiểu Bloomberg/Simplize terminal
- Vietnamese language cho UI text

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-web-dashboard*
*Context gathered: 2026-04-16*
