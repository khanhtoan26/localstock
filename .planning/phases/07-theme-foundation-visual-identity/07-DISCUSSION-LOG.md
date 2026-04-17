# Phase 7: Theme + Stock Page Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 07-theme-foundation-visual-identity
**Areas discussed:** (Session 1) Warm palette aesthetic, Toggle placement, Financial colors on light, Chart re-theming; (Session 2) Layout, AI Report Rendering, Chart & Data Placement, Responsive Behavior

---

## Session 1 — Theme Foundation (2026-04-17, original scope)

### Warm Palette Aesthetic

| Option | Description | Selected |
|--------|-------------|----------|
| Claude-inspired cream | oklch(0.97 0.02 70) with terracotta accent | ✓ |
| Neutral warm | Warmer white without orange accent | |
| Bold orange | Strong orange identity | |

**User's choice:** Delegated to agent — "AI quyết định đi"

### Toggle Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Header top-right | Sun/moon icon in AppShell header | ✓ |
| Sidebar footer | Toggle at bottom of sidebar | |
| Settings page | Toggle buried in settings | |

**User's choice:** Delegated to agent

### Financial Colors on Light Background

| Option | Description | Selected |
|--------|-------------|----------|
| CSS variables + dual classes | `text-green-700 dark:text-green-400` pattern | ✓ |
| Single class per theme | Only CSS variable-based | |
| Same colors both themes | Keep -400 shades, accept poor contrast on cream | |

**User's choice:** Delegated to agent

### Chart Re-Theming Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| applyOptions() dynamic | Update colors imperatively, no chart destruction | ✓ |
| Destroy/recreate | Tear down and rebuild chart on theme change | |
| CSS filter invert | Apply CSS filter to canvas (hacky) | |

**User's choice:** Delegated to agent

---

## Session 2 — Stock Page Redesign (2026-04-17, merged scope)

**Context:** User requested merging Phase 8 (Stock Page Redesign) into Phase 7. Rejected drawer-based approach (original STOCK-03) in favor of side-by-side layout. User's priorities: "layout tôi mong muốn là side by side, phần báo cáo ai phải đặt ở đầu vì nó quan trọng nhất."

### Layout — AI report placement

| Option | Description | Selected |
|--------|-------------|----------|
| AI Report bên trái (60-70%) + Chart/Data bên phải (30-40%) | Mắt đọc trái→phải | ✓ |
| AI Report bên phải + Chart/Data bên trái | Reversed layout | |
| AI Report full-width trên cùng + Chart/Score grid bên dưới | Two-row layout | |

**User's choice:** AI Report bên trái (60-70%)

### Layout — Panel scroll behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Panel phải cố định (sticky) | Chart stays visible while reading | ✓ |
| Cả 2 bên scroll độc lập | Dual scroll areas | |
| Panel phải scroll cùng trang | Single page scroll | |

**User's choice:** Panel phải cố định (sticky)

### Layout — Score placement

| Option | Description | Selected |
|--------|-------------|----------|
| Score overview ở header + chi tiết trong panel phải | Compact + full details | ✓ |
| Score breakdown riêng trong panel phải | Full card only | |
| Bỏ score breakdown | Minimal display | |

**User's choice:** Score overview ở header + chi tiết trong panel phải

### Layout — Mobile stacking

| Option | Description | Selected |
|--------|-------------|----------|
| Stack dọc: AI report trước, chart/data bên dưới | AI report first | ✓ |
| Giữ side-by-side thu nhỏ | Cramped | |
| Tab layout | Tab-based | |

**User's choice:** Stack dọc

### AI Report — Rendering approach

| Option | Description | Selected |
|--------|-------------|----------|
| react-markdown với typography plugin | Headers, lists, tables | ✓ |
| Plain text cải tiến | Regex-based sections | |
| Custom parser | content_json components | |

**User's choice:** react-markdown

### AI Report — Typography

| Option | Description | Selected |
|--------|-------------|----------|
| Prose class (tailwindcss-typography) | Automatic typography | ✓ |
| Custom CSS | Manual styling | |
| Agent decides | Agent discretion | |

**User's choice:** Prose class

### AI Report — Height handling

| Option | Description | Selected |
|--------|-------------|----------|
| Scroll nội bộ + ScrollArea | Contained scroll | ✓ |
| Full height | Infinite page | |
| Collapsible sections | Expandable parts | |

**User's choice:** Scroll nội bộ

### Chart/Data — Panel organization

| Option | Description | Selected |
|--------|-------------|----------|
| Tabs: Chart \| Indicators \| Score | Gọn, không quá tải | ✓ |
| Stack dọc tất cả | One scrollable column | |
| Accordion/Collapsible | Expandable sections | |

**User's choice:** Tabs

### Chart/Data — Default tab

| Option | Description | Selected |
|--------|-------------|----------|
| Tab Chart mở mặc định | Giá là context quan trọng | |
| Tab Score mở mặc định | Thấy điểm ngay | |
| Nhớ tab cuối cùng (localStorage) | Personalized | ✓ |

**User's choice:** Initially selected Chart default, then **revised** to localStorage persistence. Fallback: Chart.
**Notes:** User specifically requested: "thay vì mở chart mặc định hãy sửa required để lưu hành vi của ng dùng ở localStorage"

### Chart/Data — TimeframeSelector

| Option | Description | Selected |
|--------|-------------|----------|
| Trong tab Chart, trên biểu đồ | Grouped with chart | ✓ |
| Ngoài tabs, luôn hiển thị | Always visible | |
| Bỏ | Default 1 year | |

**User's choice:** Trong tab Chart

### Responsive — Breakpoint

| Option | Description | Selected |
|--------|-------------|----------|
| 768px (md) | Standard tablet/mobile | ✓ |
| 1024px (lg) | Large screens only | |
| 640px (sm) | Side-by-side as much as possible | |

**User's choice:** 768px

### Responsive — Mobile tab conversion

| Option | Description | Selected |
|--------|-------------|----------|
| Accordion/collapsible sections | Independent expand/collapse | ✓ |
| Giữ tabs full-width | Same tabs, wider | |
| Agent decides | Agent discretion | |

**User's choice:** Accordion/collapsible

---

## Agent's Discretion

- Session 1: All 4 theme areas delegated to agent
- Session 2: Exact panel width ratio, tab/accordion component choice, ScrollArea max-height, chart height in narrow panel

## Deferred Ideas

- Original Phase 8 drawer-based approach (STOCK-03, STOCK-04, STOCK-05) — replaced by side-by-side layout per user preference
