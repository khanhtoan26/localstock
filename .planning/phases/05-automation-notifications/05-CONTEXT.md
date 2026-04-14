# Phase 5: Automation & Notifications - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Tự động hóa pipeline phân tích hàng ngày và gửi thông báo qua Telegram. Bao gồm: scheduler chạy sau 15:30, on-demand analysis, Telegram daily digest, score change alerts (>15 điểm), và sector rotation tracking.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion (toàn bộ phase)
- **D-01:** Agent tự thiết kế Telegram bot: format tin nhắn, kênh/nhóm, tần suất.
- **D-02:** Agent tự cấu hình scheduler: thời gian chạy, xử lý lỗi, nhận biết ngày nghỉ/lễ VN.
- **D-03:** Agent tự thiết kế score change alerts: ngưỡng cảnh báo, loại tín hiệu, format.
- **D-04:** Agent tự implement sector rotation: cách đo dòng tiền, so sánh giữa các ngành.

### Carrying forward
- Supabase database (Phase 1)
- Composite scores + grade letters (Phase 3)
- AI reports tiếng Việt (Phase 4)
- HOSE trading hours: 9:00-15:00, thứ 2-6

</decisions>

<canonical_refs>
## Canonical References

### Requirements
- `.planning/REQUIREMENTS.md` — AUTO-01..02, NOTI-01..02, SCOR-04..05

### Research
- `.planning/research/PITFALLS.md` — Vietnamese holiday calendar handling
- `.planning/research/ARCHITECTURE.md` — APScheduler recommendation

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- Reads from: All pipeline results (Phase 1-4)
- Writes to: Telegram API, scheduler state
- Orchestrates: Full crawl→analyze→score→report→notify pipeline

</code_context>

<specifics>
## Specific Ideas

- Cần Vietnamese holiday calendar — HOSE nghỉ các ngày lễ VN
- Scheduler chạy sau 15:30 khi data settle
- Score change detection cần compare vs previous run

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 05-automation-notifications*
*Context gathered: 2026-04-14*
