# Requirements: LocalStock

**Defined:** 2026-04-17
**Core Value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## v1.1 Requirements

Requirements for milestone v1.1 UX Polish & Educational Depth. Each maps to roadmap phases.

### Theme System

- [ ] **THEME-01**: User can switch giữa warm-light và dark theme qua toggle, preference persist localStorage
- [ ] **THEME-02**: Trang load không flash sai theme (FOUC-free via inline blocking script từ next-themes)
- [ ] **THEME-03**: Warm-light palette (cream + terracotta/orange) là default theme cho toàn bộ app
- [ ] **THEME-04**: Charts (lightweight-charts canvas) tự re-theme khi chuyển theme via chart.applyOptions()
- [ ] **THEME-05**: Financial color tokens (grade colors, stock-up/down) legible trên cả 2 theme backgrounds (WCAG AA contrast)

### Stock Page Redesign

- [ ] **STOCK-01**: Stock page hiển thị AI report full-width ở center scroll, data/chart là secondary content
- [ ] **STOCK-02**: AI report render structured sections via react-markdown với typography plugin (không plain text/JSON.stringify)
- [ ] **STOCK-03**: Right drawer (Sheet component) chứa tabs Chart / Raw Data, mở khi user click
- [ ] **STOCK-04**: Drawer đóng/mở không mất scroll position của page chính
- [ ] **STOCK-05**: Drawer state persist trong URL search params (?drawer=chart) cho shareable links và browser back

### Academic/Learning Page

- [ ] **LEARN-01**: Trang Learn với 3 category pages: Technical Indicators / Fundamental Ratios / Macro Concepts
- [ ] **LEARN-02**: Glossary data module (typed TypeScript Record, ≥15 entries ban đầu) làm single source of truth
- [ ] **LEARN-03**: Category-based routing (/learn/technical, /learn/fundamental, /learn/macro) với Server Components
- [ ] **LEARN-04**: Search/filter entries với Vietnamese diacritic-insensitive matching (client-side)

### Interactive Glossary

- [ ] **GLOSS-01**: Auto-link glossary terms trong AI report text sang definitions (via react-markdown component override)
- [ ] **GLOSS-02**: Hover card preview hiển thị short definition + link to full learn page
- [ ] **GLOSS-03**: Click-through navigation từ report → /learn/[category]#[term] (deep link)
- [ ] **GLOSS-04**: Alias-based matching (RSI, chỉ số RSI, Relative Strength Index → cùng 1 glossary entry, longest-first)

## Future Requirements

Deferred to v1.2+. Tracked but not in current roadmap.

### UX Enhancements

- **UX-01**: Vietnamese font (Be Vietnam Pro via next/font/google) cho optimal diacritic rendering
- **UX-02**: Keyboard shortcut system cho drawer toggle và navigation
- **UX-03**: In-drawer mini-chart preview khi hover dates/prices trong report text

### Educational Depth

- **EDU-01**: Per-term live example charts trong academic entries
- **EDU-02**: Cross-linking giữa các academic entries (seeAlso navigation)
- **EDU-03**: AI-powered "giải thích đơn giản hơn" button trong learn pages

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Backend/API changes | v1.1 là pure-frontend milestone |
| MDX/CMS pipeline | ~25 entries không cần — typed TS module đủ |
| Radix UI components | Locked to @base-ui/react via base-nova style |
| Mobile app | Web dashboard là đủ cho v1 |
| Multi-user / auth | Tool cá nhân |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| THEME-01 | — | Pending |
| THEME-02 | — | Pending |
| THEME-03 | — | Pending |
| THEME-04 | — | Pending |
| THEME-05 | — | Pending |
| STOCK-01 | — | Pending |
| STOCK-02 | — | Pending |
| STOCK-03 | — | Pending |
| STOCK-04 | — | Pending |
| STOCK-05 | — | Pending |
| LEARN-01 | — | Pending |
| LEARN-02 | — | Pending |
| LEARN-03 | — | Pending |
| LEARN-04 | — | Pending |
| GLOSS-01 | — | Pending |
| GLOSS-02 | — | Pending |
| GLOSS-03 | — | Pending |
| GLOSS-04 | — | Pending |
