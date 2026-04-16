# Phase 3: Sentiment Analysis & Scoring Engine - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Crawl tin tức tài chính VN, dùng LLM local phân loại sentiment, xây dựng scoring engine kết hợp 3 chiều (kỹ thuật + cơ bản + sentiment). Output: composite score cho mỗi mã với grade letter (A/B/C/D/F) + điểm chi tiết, và danh sách top 10-20 mã đáng mua.

</domain>

<decisions>
## Implementation Decisions

### Nguồn tin tức
- **D-01:** Agent tự research và chọn nguồn tin tức tài chính VN tốt nhất. Gợi ý từ research: CafeF, VnExpress, Thanh Niên.

### LLM Sentiment
- **D-02:** Agent tự test và chọn model Ollama tốt nhất cho sentiment tiếng Việt (gợi ý: Qwen2.5 7B hoặc 14B Q4).
- **D-03:** Output format: JSON cấu trúc — `{ sentiment: "positive/negative/neutral", score: 0-1, reason: "..." }`. Dùng Ollama structured output (format parameter với JSON Schema).

### Scoring Engine
- **D-04:** Agent tự chọn trọng số composite score phù hợp.
- **D-05:** Thang điểm kết hợp: Grade letter (A/B/C/D/F) hiển thị cho user + điểm số chi tiết (0-100) lưu bên trong. Tránh false precision khi hiển thị.
- **D-06:** Trọng số scoring phải configurable — user có thể tùy chỉnh sau.

### Carrying forward
- Supabase database (Phase 1)
- Phân ngành VN tự định nghĩa (Phase 2)
- pandas-ta indicators + financial ratios (Phase 2)

### Agent's Discretion
- Nguồn tin tức cụ thể và cách crawl/parse
- Model LLM cho sentiment (Qwen2.5 7B vs 14B vs khác)
- Trọng số mặc định cho composite score
- Funnel strategy: bao nhiêu mã qua LLM sentiment (research gợi ý ~50 sau khi lọc bằng tech+fund score)

</decisions>

<canonical_refs>
## Canonical References

### Project Context
- `.planning/PROJECT.md` — Core value: gợi ý đáng mua kèm lý do
- `.planning/REQUIREMENTS.md` — SENT-01..03, SCOR-01..03

### Prior Phases
- `.planning/phases/01-foundation-data-pipeline/01-CONTEXT.md` — Supabase, vnstock
- `.planning/phases/02-technical-fundamental-analysis/02-CONTEXT.md` — Indicators, ratios, phân ngành VN

### Research
- `.planning/research/STACK.md` — Ollama, Qwen2.5 recommendation
- `.planning/research/PITFALLS.md` — LLM hallucination risks, Vietnamese NLP challenges
- `.planning/research/ARCHITECTURE.md` — Funnel strategy for LLM (filter 400→50→20)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield — Phase 1 & 2 sẽ cung cấp data pipeline + analysis modules

### Integration Points
- Reads from: OHLCV data, BCTC ratios, indicators (Phase 1+2)
- Writes to: Sentiment scores, composite scores, rankings

</code_context>

<specifics>
## Specific Ideas

- Funnel strategy: không chạy LLM cho tất cả 400 mã — lọc bằng tech+fund score trước, chỉ LLM sentiment cho top ~50
- Structured JSON output từ Ollama — đáng tin cậy hơn text parsing
- Grade A/B/C/D/F mapping cần rõ ràng (VD: A=80-100, B=60-79, C=40-59, D=20-39, F=0-19)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-sentiment-analysis-scoring-engine*
*Context gathered: 2026-04-14*
