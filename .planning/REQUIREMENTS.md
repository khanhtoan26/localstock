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

- [ ] **LAY-01**: Sidebar float overlay thay vì fixed, content không bị đẩy khi sidebar mở
- [ ] **LAY-02**: Sidebar collapse thành icon rail (~56px), expand khi click
- [ ] **LAY-03**: Sidebar có 2 icon tab groups: Main (Rankings, Market, Learn) và Admin
- [x] **LAY-04
**: Sidebar state (collapsed/expanded) persist qua localStorage

### Table & Search

- [ ] **TBL-01**: Table sort hoạt động đúng: numeric sort cho số, tiebreaker bằng symbol
- [ ] **TBL-02**: Sort state hiển thị rõ (icon direction) trên column đang sort
- [ ] **TBL-03**: Search bar trên rankings page filter stocks theo symbol/tên
- [ ] **TBL-04**: Search state persist khi chuyển trang/tab (URL params)

### Market Info

- [ ] **MKT-01**: Header hiển thị market session progress bar (HOSE 9:00-15:00 với các phiên)
- [ ] **MKT-02**: Session bar hiện trạng thái phiên (Pre-market / Trading / Lunch / Closed)
- [ ] **MKT-03**: 4 ô metrics trên Market Overview hoạt động với data thật từ backend
- [ ] **MKT-04**: Backend API endpoint mới cung cấp market summary data

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
| VIS-01 | Phase 14 | Pending |
| VIS-02 | Phase 14 | Pending |
| VIS-03 | Phase 14 | Pending |
| LAY-01 | Phase 15 | Pending |
| LAY-02 | Phase 15 | Pending |
| LAY-03 | Phase 15 | Pending |
| LAY-04 | Phase 15 | Pending |
| TBL-01 | Phase 16 | Pending |
| TBL-02 | Phase 16 | Pending |
| TBL-03 | Phase 16 | Pending |
| TBL-04 | Phase 16 | Pending |
| MKT-01 | Phase 16 | Pending |
| MKT-02 | Phase 16 | Pending |
| MKT-03 | Phase 17 | Pending |
| MKT-04 | Phase 17 | Pending |

**Coverage:**
- v1.3 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after initial definition*
