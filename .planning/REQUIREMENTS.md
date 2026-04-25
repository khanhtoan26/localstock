# Requirements: LocalStock v1.3

**Defined:** 2026-04-24
**Core Value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## v1.3 Requirements

Requirements for UI/UX Refinement milestone. Each maps to roadmap phases.

### Visual Foundation

- [x] **VIS-01
**: Font chuyển sang Source Sans 3 với Vietnamese subset, load qua next/font
- [x] **VIS-02
**: Color palette chuyển sang warm terracotta (kiểu Claude Desktop), thay thế blue ở buttons/titles
- [x] **VIS-03
**: Dark mode cập nhật palette tương ứng, đảm bảo contrast WCAG AA

### Layout

- [x] **LAY-01
**: Sidebar float overlay thay vì fixed, content không bị đẩy khi sidebar mở
- [x] **LAY-02
**: Sidebar collapse thành icon rail (~56px), expand khi click
- [x] **LAY-03
**: Sidebar có 2 icon tab groups: Main (Rankings, Market, Learn) và Admin
- [x] **LAY-04
**: Sidebar state (collapsed/expanded) persist qua localStorage

### Table & Search

- [x] **TBL-01**: Table sort hoạt động đúng: numeric sort cho số, tiebreaker bằng symbol
- [x] **TBL-02**: Sort state hiển thị rõ (icon direction) trên column đang sort
- [x] **TBL-03**: Search bar trên rankings page filter stocks theo symbol/tên
- [x] **TBL-04**: Search filter hoạt động với local state (URL params removed — nuqs removed in 16-05, local useState used instead)

### Market Info

- [x] **MKT-01**: Header hiển thị market session progress bar (HOSE 9:00-15:00 với các phiên)
- [x] **MKT-02**: Session bar hiện trạng thái phiên (Pre-market / Trading / Lunch / Closed)
- [x] **MKT-03**: 4 ô metrics trên Market Overview hoạt động với data thật từ backend
- [x] **MKT-04**: Backend API endpoint mới cung cấp market summary data

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Layout Enhancements

- **LAY-05**: Sidebar keyboard shortcut (Cmd+B toggle)
- **LAY-06**: Mobile responsive sidebar (drawer pattern)

### Search Enhancements

- **TBL-05**: Search highlight trong filtered results
- **TBL-06**: Search suggestions / autocomplete

### Market Enhancements

- **MKT-05**: Market session state transition toasts
- **MKT-06**: Vietnamese market holidays awareness (Tết, 30/4, 2/9...)

## Out of Scope

| Feature | Reason |
|---------|--------|
| WebSocket real-time data | Polling via TanStack Query đủ cho v1.3, WebSocket là v2 |
| Custom charts cho market overview | Simple number cards đủ, charts cho individual stocks đã có |
| Theme variants ngoài light/dark | 2 themes là đủ, tránh complexity |
| Mobile responsive layout | Spec desktop-only cho v1.3 |
| Paid font hosting | next/font self-hosts miễn phí |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VIS-01 | Phase 14 | ✅ Complete |
| VIS-02 | Phase 14 | ✅ Complete |
| VIS-03 | Phase 14 | ✅ Complete |
| LAY-01 | Phase 15 | ✅ Complete |
| LAY-02 | Phase 15 | ✅ Complete |
| LAY-03 | Phase 15 | ✅ Complete |
| LAY-04 | Phase 15 | ✅ Complete |
| TBL-01 | Phase 16 | ✅ Complete |
| TBL-02 | Phase 16 | ✅ Complete |
| TBL-03 | Phase 16 | ✅ Complete |
| TBL-04 | Phase 16 | ✅ Complete (scope adjusted: local state instead of URL params) |
| MKT-01 | Phase 16 | ✅ Complete |
| MKT-02 | Phase 16 | ✅ Complete |
| MKT-03 | Phase 17 | ✅ Complete |
| MKT-04 | Phase 17 | ✅ Complete |

**Coverage:**
- v1.3 requirements: 15 total
- Completed: 15 ✅
- Scope adjustments: TBL-04 (URL params → local state)

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-25 after v1.3 milestone close*
