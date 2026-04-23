# Phase 13: AI Report Generation UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 13-ai-report-generation-ui
**Areas discussed:** Report trigger placement, Progress display, Report preview, Batch behavior

---

## Report Trigger Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline tab button | Thêm nút "Report" cạnh Crawl, Analyze, Score — dùng checkbox selection | ✓ |
| Stocks tab per-row | Thêm cột "Actions" với nút Report per-row | |
| Both | Pipeline tab cho batch, Stocks tab cho single | |

**User's choice:** Pipeline tab button (Recommended)
**Notes:** Consistent with existing action button pattern

---

## Progress Display

| Option | Description | Selected |
|--------|-------------|----------|
| Toast + auto-refresh | Dùng hạ tầng Phase 12.1 | |
| Progress bar inline | Trong Jobs tab row | |
| Modal/drawer realtime | Hiển thị progress realtime từ Ollama | ✓ |

**User's choice:** Modal/drawer realtime
**Notes:** User wants to see real-time progress from Ollama

### Follow-up: Progress Style

| Option | Description | Selected |
|--------|-------------|----------|
| Streaming text | Hiển thị từng chữ như ChatGPT (SSE) | |
| Progress steps | Hiển thị các bước (đang phân tích... đang viết...) | |
| Both | Progress steps + streaming text | |

**User's choice:** "Bạn quyết định đi" → Agent's discretion
**Notes:** Agent decides progress UI style, optimize for smooth UX

---

## Report Preview

| Option | Description | Selected |
|--------|-------------|----------|
| Modal/drawer in-place | Xem ngay sau khi generate, không chuyển trang | ✓ |
| Redirect to stock page | Chuyển sang /stock/[symbol] | |
| Both | Preview + link mở stock page | |

**User's choice:** Modal/drawer in-place (Recommended)
**Notes:** User said "Làm sao cho trang mượt" — prioritize smooth rendering

---

## Batch Generation

| Option | Description | Selected |
|--------|-------------|----------|
| Checkbox batch sequential | Chọn nhiều mã, tạo tuần tự | ✓ |
| Single only | Chỉ từng mã một | |
| Batch with queue UI | Batch + hiển thị progress per-mã | |

**User's choice:** Checkbox batch sequential (Recommended)
**Notes:** Uses existing checkbox selection pattern from Pipeline tab

---

## Agent's Discretion

- Progress display style (streaming text, steps, or combination)
- Report content rendering (reuse AIReportPanel or custom modal layout)
- Modal/drawer component choice
- Streaming implementation approach

## Deferred Ideas

None
