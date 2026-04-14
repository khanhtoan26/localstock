# Phase 1: Foundation & Data Pipeline - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Xây dựng data pipeline đáng tin cậy để crawl và lưu trữ dữ liệu ~400 mã HOSE: giá OHLCV, BCTC, thông tin công ty, với xử lý điều chỉnh giá cho corporate actions. Đây là nền tảng cho tất cả phân tích ở các phase sau.

</domain>

<decisions>
## Implementation Decisions

### Nguồn dữ liệu
- **D-01:** Sử dụng vnstock v3.5.1 làm nguồn chính (VCI/KBS data sources). Fallback sang crawl trực tiếp nếu vnstock lỗi.
- **D-02:** Khi một mã bị lỗi crawl (timeout, API trả empty), bỏ qua mã đó và tiếp tục các mã khác. Log lỗi để theo dõi.

### Database
- **D-03:** Sử dụng Supabase (PostgreSQL hosted) — free tier 500MB. Không cần tự quản lý DB, sẵn sàng scale lên cloud.

### Điều chỉnh giá
- **D-04:** Agent tự quyết định cách xử lý điều chỉnh giá (chia tách, phát hành cổ phiếu). Research lưu ý: vnstock không có logic điều chỉnh giá — cần tự implement hoặc tìm nguồn giá đã điều chỉnh.

### Crawl Strategy
- **D-05:** Agent tự quyết định chiến lược backfill + cập nhật incremental.

### Agent's Discretion
- Cách xử lý điều chỉnh giá (corporate actions) — tự chọn approach tốt nhất
- Chiến lược backfill lịch sử — tự quyết định khối lượng và tốc độ
- Rate limiting và batch size khi crawl vnstock — tự test và tối ưu
- Schema design cho Supabase — tự thiết kế phù hợp

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints (RTX 3060, free LLM, HOSE only)
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-05 requirements

### Research
- `.planning/research/STACK.md` — vnstock 3.5.1 usage patterns, Supabase setup
- `.planning/research/ARCHITECTURE.md` — Pipeline architecture, component boundaries
- `.planning/research/PITFALLS.md` — Data source instability, price adjustment gaps, vnai dependency risk

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Không có code hiện tại — greenfield project

### Established Patterns
- Không có patterns — đây là phase đầu tiên

### Integration Points
- Database (Supabase) sẽ là integration point cho tất cả phases sau
- Data models định nghĩa ở đây sẽ được dùng xuyên suốt project

</code_context>

<specifics>
## Specific Ideas

- Supabase free tier (500MB) — cần monitor usage khi lưu 2 năm lịch sử cho ~400 mã
- vnstock v3.5.1 cần pin version cẩn thận — có issue với vnai dependency (deadlock)
- HOSE trading hours: 9:00-15:00 thứ 2-6 — crawl sau 15:30 khi data settle

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-data-pipeline*
*Context gathered: 2026-04-14*
