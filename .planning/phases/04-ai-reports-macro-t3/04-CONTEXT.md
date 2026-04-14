# Phase 4: AI Reports, Macro Context & T+3 - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Tạo báo cáo phân tích tiếng Việt chi tiết bằng LLM cho từng mã, tích hợp phân tích vĩ mô (lãi suất, tỷ giá, CPI), và logic T+3 cho gợi ý lướt sóng. Output: báo cáo narrative giải thích TẠI SAO mã được chấm điểm cao/thấp, liên kết với bối cảnh vĩ mô.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion (toàn bộ phase)
- **D-01:** Agent tự quyết định cấu trúc và độ dài báo cáo AI tiếng Việt.
- **D-02:** Agent tự chọn nguồn dữ liệu vĩ mô (SBV, GSO...) và cách thu thập.
- **D-03:** Agent tự thiết kế cách liên kết macro → ngành → cổ phiếu.
- **D-04:** Agent tự implement logic dự đoán 3 ngày cho T+3 và cách cảnh báo.
- **D-05:** Agent tự phân biệt giữa gợi ý dài hạn vs lướt sóng trong báo cáo.

### Carrying forward
- Supabase database (Phase 1)
- LLM model qua Ollama (Phase 3 — sẽ reuse model đã chọn)
- Composite score + grade letter A/B/C/D/F (Phase 3)
- JSON structured output (Phase 3)

</decisions>

<canonical_refs>
## Canonical References

### Requirements
- `.planning/REQUIREMENTS.md` — REPT-01..02, MACR-01..02, T3-01..02

### Prior Phases
- `.planning/phases/03-sentiment-analysis-scoring-engine/03-CONTEXT.md` — LLM model, scoring, JSON output

### Research
- `.planning/research/PITFALLS.md` — Macro data sourcing challenges (SBV/GSO no clean API)
- `.planning/research/FEATURES.md` — LLM narrative reports as differentiator

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- Reads from: All analysis results (tech, fund, sentiment, scores) from Phase 2+3
- Writes to: Report storage, macro data tables

</code_context>

<specifics>
## Specific Ideas

- T+3 awareness là đặc thù HOSE — khi gợi ý lướt sóng, phải dự đoán 3 ngày tới không giảm
- Macro data từ SBV/GSO có thể cần semi-manual (research cảnh báo)
- Báo cáo phải giải thích TẠI SAO, không chỉ liệt kê con số

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 04-ai-reports-macro-t3*
*Context gathered: 2026-04-14*
