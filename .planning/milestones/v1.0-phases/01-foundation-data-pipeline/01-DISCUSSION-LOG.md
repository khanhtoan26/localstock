# Phase 1: Foundation & Data Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 1-Foundation & Data Pipeline
**Areas discussed:** Nguồn dữ liệu, Database, Điều chỉnh giá, Crawl strategy

---

## Nguồn dữ liệu

| Option | Description | Selected |
|--------|-------------|----------|
| vnstock là chính, fallback crawl trực tiếp nếu lỗi | Dùng vnstock v3.5.1 làm primary, crawl web nếu API lỗi | ✓ |
| Crawl trực tiếp luôn | Không dùng vnstock, tự crawl tất cả | |
| Agent tự quyết định | | |

**User's choice:** vnstock là chính, fallback crawl trực tiếp nếu lỗi

| Option | Description | Selected |
|--------|-------------|----------|
| Retry 3 lần + cache dữ liệu cuối cùng + log lỗi | Cố gắng retry trước khi bỏ qua | |
| Bỏ qua mã lỗi, tiếp tục các mã khác | Skip lỗi, không block pipeline | ✓ |
| Dừng toàn bộ và báo lỗi | Fail-fast approach | |
| Agent tự quyết định | | |

**User's choice:** Bỏ qua mã lỗi, tiếp tục các mã khác

---

## Database

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL (Docker) | Mạnh mẽ, scale tốt, chạy qua docker-compose | |
| SQLite | Đơn giản, không cần server | |
| Supabase | PostgreSQL hosted, free tier 500MB | ✓ |

**User's choice:** Supabase (user provided freeform — đã chọn Supabase thay vì Docker/local install)

---

## Điều chỉnh giá

| Option | Description | Selected |
|--------|-------------|----------|
| Tự tính từ dữ liệu sự kiện | Chính xác hơn, cần tìm nguồn corporate actions | |
| Lấy giá đã điều chỉnh từ nguồn khác | Nếu có nguồn sẵn | |
| Agent tự quyết định cách tốt nhất | | ✓ |

**User's choice:** Agent tự quyết định cách tốt nhất

---

## Crawl Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Backfill 2 năm lần đầu + cập nhật incremental hàng ngày | Full history upfront | |
| Chỉ lấy dữ liệu mới từ hôm nay, tích lũy dần | Nhẹ hơn nhưng thiếu lịch sử ban đầu | |
| Agent tự quyết định | | ✓ |

**User's choice:** Agent tự quyết định

---

## Agent's Discretion

- Cách xử lý điều chỉnh giá (corporate actions)
- Chiến lược backfill lịch sử
- Rate limiting và batch size
- Database schema design

## Deferred Ideas

None
