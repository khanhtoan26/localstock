# Phase 21: Frontend Trade Plan Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 21-frontend-trade-plan-display
**Areas discussed:** Layout & Positioning, Risk Badge + Signal Conflict, Price Levels Display, Graceful Degradation

---

## Layout & Positioning

| Option | Description | Selected |
|--------|-------------|----------|
| Giữa Score Breakdown và AI Report | Trade Plan ngay sau điểm số, trước báo cáo AI | ✓ |
| Trước Score Breakdown | Section đầu tiên sau biểu đồ giá | |
| Sau AI Report | Kết luận hành động cuối trang | |

**User's choice:** Giữa Score Breakdown và AI Report — user thấy giá trước khi đọc phân tích
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Full-width card riêng 1 hàng | Chiếm toàn bộ chiều ngang | |
| 3 cột trên lg | Trade Plan ở giữa, compact | |
| Cùng cột với Score Breakdown | Stack dọc: Score trên, Trade Plan dưới | |

**User's choice:** Agent discretion — investigate and design for best fit
**Notes:** User deferred layout details to agent

---

## Risk Badge + Signal Conflict

| Option | Description | Selected |
|--------|-------------|----------|
| Badge nhỏ (giống GradeBadge) | Pill/tag màu: đỏ = Cao, vàng = Trung bình, xanh = Thấp | ✓ |
| Icon + text | Biểu tượng cảnh báo + text màu | |
| Progress bar ngang | Thanh gradient từ xanh đến đỏ | |

**User's choice:** Badge nhỏ matching GradeBadge pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Alert box vàng/cam với icon ⚠️ | Nổi bật, hiển thị text xung đột từ LLM | ✓ |
| Đoạn text nhỏ inline | Hiển thị trực tiếp trong card | |
| Ẩn hoàn toàn, chỉ tooltip | Chỉ hiện khi hover | |

**User's choice:** Alert box with ⚠️ icon

| Option | Description | Selected |
|--------|-------------|----------|
| Tooltip với lý do từ LLM | Hover/tap risk badge để xem giải thích | ✓ |
| Hiển thị luôn dưới badge | Text nhỏ giải thích ngay dưới | |
| Chỉ badge, không tooltip | Giữ đơn giản | |

**User's choice:** Tooltip on hover/tap showing LLM reasoning

---

## Price Levels Display

| Option | Description | Selected |
|--------|-------------|----------|
| 3 hàng dọc | Entry Zone range, SL, TP mỗi hàng với label + VND | ✓ |
| 2 cột compact | Cột trái labels, cột phải giá | |
| 1 hàng ngang | Entry/SL/TP trên cùng 1 dòng | |

**User's choice:** 3 vertical rows with labels + VND formatted prices

| Option | Description | Selected |
|--------|-------------|----------|
| Có, hiện % variance | Ví dụ: Cắt lỗ: 48.000 (-4.0%) | ✓ |
| Không cần | Chỉ hiện giá VND | |

**User's choice:** Show percentage variance next to each price level

---

## Graceful Degradation

| Option | Description | Selected |
|--------|-------------|----------|
| Ẩn hoàn toàn Trade Plan section | Không render gì nếu không có dữ liệu giá | ✓ |
| Hiện section với trạng thái trống | "Chưa có dữ liệu kế hoạch giao dịch" | |
| Hiện skeleton/placeholder | Giữ layout ổn định | |

**User's choice:** Hide completely when no trade plan data

| Option | Description | Selected |
|--------|-------------|----------|
| Skeleton loading giống PriceChart | Animated placeholder trong khi fetch | ✓ |
| Không hiện gì cho đến khi data sẵn sàng | Trade Plan xuất hiện khi load xong | |

**User's choice:** Skeleton loading matching PriceChart pattern

---

## Agent's Discretion

- Exact layout (grid columns, widths, responsive breakpoints)
- Card wrapper vs custom section styling
- Tooltip implementation approach
- Catalyst data placement

## Deferred Ideas

None
