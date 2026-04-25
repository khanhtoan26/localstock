# LocalStock

## What This Is

LocalStock là một AI Stock Agent cá nhân cho thị trường chứng khoán Việt Nam (HOSE). Agent tự động crawl dữ liệu ~400 mã cổ phiếu, phân tích đa chiều (kỹ thuật, cơ bản, sentiment, vĩ mô), xếp hạng và đưa ra gợi ý mã đáng mua kèm báo cáo tiếng Việt chi tiết. Hệ thống chạy tự động hàng ngày sau phiên giao dịch, gửi alert qua Telegram, và có web dashboard để theo dõi trực quan. Chạy trên máy cá nhân với LLM local miễn phí qua Ollama (RTX 3060).

## Core Value

Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## Current State: v1.3 Shipped

**Shipped:** 2026-04-25 — UI/UX Refinement complete (Phases 14–17, 14 plans)

All v1.3 goals delivered: Source Sans 3 typography, warm neutral palette, Claude Desktop floating sidebar, numeric table sort, live market session bar, live market metrics cards with real backend data.

## Requirements

### Validated

- ✓ Agent tự crawl dữ liệu giá/khối lượng ~400 mã HOSE (định kỳ + on-demand) — v1.0
- ✓ Tính toán chỉ báo kỹ thuật (MA, RSI, MACD, Bollinger Bands...) — v1.0
- ✓ Thu thập dữ liệu cơ bản (P/E, EPS, ROE, doanh thu, lợi nhuận từ BCTC) — v1.0
- ✓ Crawl tin tức tài chính để phân tích sentiment — v1.0
- ✓ Thu thập dữ liệu vĩ mô (lãi suất, tỷ giá, CPI, GDP...) — v1.0
- ✓ LLM local (Ollama) tổng hợp phân tích đa chiều và đưa gợi ý — v1.0
- ✓ Xếp hạng điểm cho từng mã (VD: VNM 85/100) — v1.0
- ✓ Báo cáo chi tiết từng mã (kỹ thuật + cơ bản + sentiment + vĩ mô) — v1.0
- ✓ Dashboard web hiển thị bảng xếp hạng, biểu đồ, chi tiết mã — v1.0
- ✓ Notification qua Telegram khi có gợi ý tốt — v1.0
- ✓ Agent chạy định kỳ (hàng ngày) tự động — v1.0
- ✓ Agent chạy on-demand khi người dùng yêu cầu — v1.0
- ✓ Theme system: Claude warm-light (cream + orange) default + dark toggle, preference persist — v1.1
- ✓ Stock page redesign: AI report + score breakdown + chart components — v1.1
- ✓ Academic/Learning page: giải thích technical indicators, fundamental ratios, macro concepts — v1.1
- ✓ Interactive glossary linking từ chỉ số trong AI report → định nghĩa — v1.1
- ✓ Admin Console: trang quản trị để quản lý mã, chạy crawl/analysis/report từ UI — v1.2
- ✓ Stock management: thêm/xóa mã cổ phiếu theo dõi từ web UI — v1.2
- ✓ Pipeline control: trigger crawl/analysis/scoring/report từ UI — v1.2
- ✓ Job monitoring: xem trạng thái pipeline, lịch sử chạy, errors — v1.2

- ✓ Font Source Sans 3 (Vietnamese subset, FOUC-free via next/font) — v1.3
- ✓ Color palette Claude Desktop warm neutral (bỏ blue, warm near-black/gray) — v1.3
- ✓ Sidebar float collapsible: icon rail (w-14) + overlay panel (w-60), localStorage persist — v1.3
- ✓ Fix sort behavior trên tables (numeric + grade semantic, tiebreaker) — v1.3
- ✓ Search bar filter stocks theo symbol/tên (local state) — v1.3
- ✓ Market session progress bar trên header (HOSE phases, countdown) — v1.3
- ✓ Market overview 4 metrics với data thật (GET /api/market/summary) — v1.3

### Active

(No active requirements — planning v1.4)

### Out of Scope

- Thị trường HNX/UPCOM — tập trung HOSE trước, mở rộng sau (v2 candidate)
- Multi-user / authentication — tool cá nhân, không cần auth
- Paid LLM API (GPT/Claude) — dùng local LLM miễn phí qua Ollama
- Trading tự động (auto-buy/sell) — chỉ gợi ý, không tự giao dịch
- Mobile app — web dashboard là đủ cho v1
- Intraday data (phút/giờ) — v2 candidate
- Backtesting — v2 candidate

## Context

- **Current version:** v1.3 shipped 2026-04-25
- **Codebase:** ~8,500 LOC Python (backend) + ~41,200 LOC TypeScript (frontend) + ~4,100 LOC CSS (v1.2 baseline; +31,495/-3,786 LOC in v1.3 across 399 files)
- **Backend:** Python + FastAPI + SQLAlchemy + Alembic + PostgreSQL (Supabase)
- **Frontend:** Next.js 16 + shadcn/ui + Tailwind v4 + lightweight-charts v5
- **AI:** Ollama local LLM (RTX 3060, 12GB VRAM) for sentiment analysis and report generation
- **Notifications:** Telegram bot via python-telegram-bot
- **Automation:** APScheduler daily pipeline after market close (15:30)
- **Tests:** 324 backend unit tests + 8 new market API tests (332 total) + 44 frontend vitest tests
- **Thị trường mục tiêu:** Sàn HOSE (~400 mã có thanh khoản cao)

## Constraints

- **Hardware**: RTX 3060 12GB VRAM — giới hạn model LLM ≤ 13B parameters
- **Cost**: Miễn phí hoàn toàn — không dùng paid API, chỉ local LLM + free data sources
- **Market hours**: Sàn HOSE giao dịch 9:00-15:00 thứ 2-6 — crawl dữ liệu theo lịch này
- **Data availability**: Phụ thuộc vào nguồn dữ liệu free/public — có thể bị rate limit hoặc thay đổi API

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LLM local qua Ollama thay vì paid API | Miễn phí, có RTX 3060, data sovereignty | ✓ Good — chạy ổn trên RTX 3060, model 7B đủ cho sentiment + reports |
| Chỉ HOSE, không HNX/UPCOM | Tập trung thanh khoản cao, giảm scope v1 | ✓ Good — ~400 mã là đủ cho v1 |
| Tool cá nhân, không multi-user | Giảm complexity, không cần auth/billing | ✓ Good — giữ đơn giản, CORS chỉ localhost |
| Python + FastAPI backend | Hệ sinh thái data science mạnh (pandas, pandas-ta) | ✓ Good — tận dụng vnstock, pandas-ta |
| PostgreSQL (Supabase) | Free tier đủ cho cá nhân, SQL mạnh cho analytics | ✓ Good — JSONB cho financial statements |
| Next.js 16 + shadcn/ui frontend | Modern React, dark theme sẵn, component library mạnh | ✓ Good — build nhanh, responsive |
| vnstock v3.5.1 cho data | Library Việt Nam cho HOSE data, community active | ✓ Good — API stable, cover đủ data |
| lightweight-charts v5 cho biểu đồ | Nhẹ, chuyên cho financial charts, TradingView quality | ✓ Good — candlestick + volume overlay tốt |
| APScheduler cho automation | Đơn giản, chạy trong process, không cần Celery/Redis | ✓ Good — daily pipeline ổn định |
| Telegram cho notifications | User quen dùng, API đơn giản, push notification miễn phí | ✓ Good — daily digest + alert hoạt động tốt |
| Source Sans 3 via next/font/google | FOUC-free, Vietnamese subset, no paid hosting | ✓ Good — v1.3 |
| Warm neutral palette thay blue | Claude Desktop aesthetic, warm cream on light/dark | ✓ Good — v1.3 |
| FloatingSidebar: icon rail + overlay | No push-content layout complexity, always-visible icon rail | ✓ Good — v1.3 |
| nuqs removed — search dùng local useState | URL persistence thêm complexity không cần thiết cho tool cá nhân | ✓ Good — v1.3 |
| GET /api/market/summary dùng MAX(date) | Robust với weekends/holidays — không bao giờ dùng date.today() | ✓ Good — v1.3 |
| MarketSummaryCards staleTime 30min | Khớp với daily crawl rhythm — tránh refetch thừa | ✓ Good — v1.3 |

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
*Last updated: 2026-04-25 after milestone v1.3 complete*
