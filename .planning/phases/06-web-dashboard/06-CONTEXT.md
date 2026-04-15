# Phase 6: Web Dashboard - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Xây dựng web dashboard hiển thị: bảng xếp hạng cổ phiếu theo grade/score, trang chi tiết từng mã (biểu đồ giá, chỉ báo kỹ thuật, báo cáo AI), và tổng quan thị trường kèm phân tích vĩ mô.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion (toàn bộ phase)
- **D-01:** Agent tự thiết kế layout và UX cho dashboard. Research gợi ý: Next.js + shadcn/ui + TradingView lightweight-charts.
- **D-02:** Agent tự quyết định loại biểu đồ, timeframe options, mức độ interactive.
- **D-03:** Agent tự thiết kế trang tổng quan thị trường.
- **D-04:** Agent tự quyết định responsive design (desktop-first cho tool cá nhân).

### Carrying forward
- Supabase database (Phase 1) — data source cho dashboard
- Grade letters A/B/C/D/F + điểm chi tiết (Phase 3)
- AI reports tiếng Việt (Phase 4)
- Macro analysis (Phase 4)

</decisions>

<canonical_refs>
## Canonical References

### Requirements
- `.planning/REQUIREMENTS.md` — DASH-01..03

### Research
- `.planning/research/STACK.md` — Next.js, shadcn/ui, lightweight-charts 5.1.0
- `.planning/research/FEATURES.md` — Dashboard features, competitor analysis (Simplize, WiChart)

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- Reads from: Supabase (scores, reports, macro data, indicators)
- Backend API from Phase 1-5 (FastAPI endpoints)

</code_context>

<specifics>
## Specific Ideas

- TradingView lightweight-charts (45KB) — purpose-built cho financial data
- Dashboard là phase cuối — tất cả data đã sẵn sàng
- Tool cá nhân nên UX functional > đẹp

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 06-web-dashboard*
*Context gathered: 2026-04-14*
