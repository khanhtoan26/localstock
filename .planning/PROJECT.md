# LocalStock

## What This Is

LocalStock là một AI Stock Agent cá nhân cho thị trường chứng khoán Việt Nam (HOSE). Agent tự động crawl dữ liệu ~400 mã cổ phiếu, phân tích đa chiều (kỹ thuật, cơ bản, sentiment, vĩ mô), xếp hạng và đưa ra gợi ý mã đáng mua kèm báo cáo chi tiết. Chạy trên máy cá nhân với LLM local miễn phí qua Ollama (RTX 3060).

## Core Value

Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Agent tự crawl dữ liệu giá/khối lượng ~400 mã HOSE (định kỳ + on-demand)
- [ ] Tính toán chỉ báo kỹ thuật (MA, RSI, MACD, Bollinger Bands...)
- [ ] Thu thập dữ liệu cơ bản (P/E, EPS, ROE, doanh thu, lợi nhuận từ BCTC)
- [ ] Crawl tin tức tài chính để phân tích sentiment
- [ ] Thu thập dữ liệu vĩ mô (lãi suất, tỷ giá, CPI, GDP...)
- [ ] LLM local (Ollama) tổng hợp phân tích đa chiều và đưa gợi ý
- [ ] Xếp hạng điểm cho từng mã (VD: VNM 85/100)
- [ ] Báo cáo chi tiết từng mã (kỹ thuật + cơ bản + sentiment + vĩ mô)
- [ ] Dashboard web hiển thị bảng xếp hạng, biểu đồ, chi tiết mã
- [ ] Notification qua Telegram khi có gợi ý tốt
- [ ] Agent chạy định kỳ (hàng ngày) tự động
- [ ] Agent chạy on-demand khi người dùng yêu cầu

### Out of Scope

- Thị trường HNX/UPCOM — tập trung HOSE trước, mở rộng sau
- Multi-user / authentication — tool cá nhân, không cần auth
- Paid LLM API (GPT/Claude) — dùng local LLM miễn phí qua Ollama
- Trading tự động (auto-buy/sell) — chỉ gợi ý, không tự giao dịch
- Mobile app — web dashboard là đủ cho v1

## Context

- **Thị trường mục tiêu:** Sàn HOSE (~400 mã có thanh khoản cao)
- **Phân tích đa chiều:** Kỹ thuật (chỉ báo giá/volume) + Cơ bản (BCTC, chỉ số tài chính) + Sentiment (tin tức) + Vĩ mô (lãi suất, tỷ giá, CPI)
- **AI engine:** LLM chạy local qua Ollama trên RTX 3060 (12GB VRAM) — hỗ trợ model 7B-13B (Llama, Mistral, Qwen...)
- **Nguồn dữ liệu:** Agent tự research và tìm nguồn phù hợp (CafeF, VnDirect, SSI, TCBS API...)
- **Output:** Bảng xếp hạng điểm + báo cáo chi tiết + phân tích vĩ mô liên kết
- **Notification:** Telegram bot gửi alert khi có gợi ý tốt
- **Deployment:** Localhost trước, kiến trúc sẵn sàng lên cloud sau
- **Tech stack:** Agent research và gợi ý stack phù hợp

## Constraints

- **Hardware**: RTX 3060 12GB VRAM — giới hạn model LLM ≤ 13B parameters
- **Cost**: Miễn phí hoàn toàn — không dùng paid API, chỉ local LLM + free data sources
- **Market hours**: Sàn HOSE giao dịch 9:00-15:00 thứ 2-6 — crawl dữ liệu theo lịch này
- **Data availability**: Phụ thuộc vào nguồn dữ liệu free/public — có thể bị rate limit hoặc thay đổi API

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LLM local qua Ollama thay vì paid API | Miễn phí, có RTX 3060, data sovereignty | — Pending |
| Chỉ HOSE, không HNX/UPCOM | Tập trung thanh khoản cao, giảm scope v1 | — Pending |
| Tool cá nhân, không multi-user | Giảm complexity, không cần auth/billing | — Pending |
| Tech stack do agent research | Để research phase tìm stack tối ưu cho use case | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-14 after initialization*
