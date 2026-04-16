# Phase 2: Technical & Fundamental Analysis - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Tính toán chỉ báo kỹ thuật và chỉ số tài chính cho ~400 mã HOSE. Đây là 2 chiều đầu tiên trong hệ thống chấm điểm 4 chiều. Kết quả: mỗi mã có bộ indicators và ratios sẵn sàng cho scoring ở Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Chỉ báo kỹ thuật
- **D-01:** Agent tự chọn bộ chỉ báo phù hợp nhất (tối thiểu: SMA, EMA, RSI, MACD, Bollinger Bands theo requirements). Có thể thêm Stochastic, ADX, OBV, VWAP nếu phù hợp.
- **D-02:** Dùng pandas-ta để tính toán (research đã recommend, pure Python, 130+ indicators).

### Phân tích cơ bản
- **D-03:** Phân ngành theo đặc thù Việt Nam (không dùng ICB chuẩn quốc tế). Agent tự định nghĩa các nhóm ngành VN phù hợp.

### Trend & Support/Resistance
- **D-04:** Xác định hỗ trợ/kháng cự bằng Pivot Points + đỉnh/đáy gần nhất.

### Carrying forward from Phase 1
- Dữ liệu OHLCV + BCTC đã có trong Supabase từ Phase 1
- vnstock làm nguồn chính

### Agent's Discretion
- Bộ chỉ báo kỹ thuật cụ thể (ngoài bộ tối thiểu)
- Cách nhóm ngành VN (số nhóm, tiêu chí phân loại)
- Schema lưu kết quả phân tích trong Supabase

</decisions>

<canonical_refs>
## Canonical References

### Project Context
- `.planning/PROJECT.md` — Constraints, core value
- `.planning/REQUIREMENTS.md` — TECH-01..04, FUND-01..03

### Prior Phase
- `.planning/phases/01-foundation-data-pipeline/01-CONTEXT.md` — Database (Supabase), data source decisions

### Research
- `.planning/research/STACK.md` — pandas-ta recommendation
- `.planning/research/FEATURES.md` — Expected analysis features

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield — Phase 1 sẽ cung cấp data models và DB connection

### Established Patterns
- Chưa có — sẽ kế thừa patterns từ Phase 1

### Integration Points
- Reads from: Supabase tables (OHLCV, BCTC) created in Phase 1
- Writes to: Analysis results tables (indicators, ratios, trends)

</code_context>

<specifics>
## Specific Ideas

- Phân ngành VN: cần mapping riêng vì HOSE có đặc thù (VD: ngân hàng, bất động sản, thép, thủy sản... có động thái khác nhau)
- Support/Resistance bằng Pivot Points — đơn giản và phù hợp cho automated scoring

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-technical-fundamental-analysis*
*Context gathered: 2026-04-14*
