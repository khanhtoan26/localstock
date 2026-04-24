# Phase 15: Sidebar Float & Collapse - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 15-sidebar-float-collapse
**Areas discussed:** Icon Rail Design, Tab Group Layout, Expand/Collapse Interaction

---

## Icon Rail Design

| Option | Description | Selected |
|--------|-------------|----------|
| Icon + tooltip khi hover | Clean, Claude Desktop style | ✓ |
| Chỉ icon, không tooltip | Minimal but less usable | |
| Icon + label nhỏ bên dưới | Kiểu mobile tab bar | |

**User's choice:** Icon + tooltip khi hover
**Notes:** Recommended option for clean Claude Desktop aesthetic

### Logo/Branding khi collapsed

| Option | Description | Selected |
|--------|-------------|----------|
| Logo icon nhỏ | Chữ "L" hoặc icon custom | |
| Hamburger menu icon | Standard mobile pattern | |
| Giữ nguyên chữ "LocalStock" dọc | Rotated text | |
| Bỏ hẳn — icon rail chỉ có nav icons | Clean, no branding in rail | ✓ |

**User's choice:** Bỏ hẳn — icon rail chỉ có nav icons

### Badge indicators

| Option | Description | Selected |
|--------|-------------|----------|
| Không cần badge | Keep it clean | ✓ |
| Badge chấm đỏ trên Admin icon | Khi có jobs đang chạy | |
| Agent quyết định | | |

**User's choice:** Không cần badge

---

## Tab Group Layout

### Cách phân tách Main và Admin

| Option | Description | Selected |
|--------|-------------|----------|
| Divider line mỏng giữa 2 nhóm | Subtle, clean | |
| Admin ở dưới cùng có khoảng trống lớn | Spacer approach | |
| 2 tab buttons ở đầu sidebar | Kiểu Slack | |
| Agent quyết định | | ✓ |

**User's choice:** Agent quyết định

### Admin icon vị trí

| Option | Description | Selected |
|--------|-------------|----------|
| Admin ở dưới cùng (bottom of rail) | Tách rõ với main nav | |
| Admin ở ngay dưới Main group có divider | | |
| Agent quyết định | | ✓ |

**User's choice:** Agent quyết định

---

## Expand/Collapse Interaction

### Cách mở sidebar overlay

| Option | Description | Selected |
|--------|-------------|----------|
| Click icon → mở overlay panel | Rõ ràng, không bị mở nhầm | ✓ |
| Hover icon → tự động mở overlay | | |
| Double click để mở/đóng | | |

**User's choice:** Click icon → mở overlay panel

### Backdrop và cách đóng

| Option | Description | Selected |
|--------|-------------|----------|
| Backdrop mờ + click ngoài để đóng | | |
| Không backdrop, chỉ click icon lần nữa để đóng | Toggle behavior | ✓ |
| Agent quyết định | | |

**User's choice:** Không backdrop, chỉ click icon lần nữa để đóng

### Animation

| Option | Description | Selected |
|--------|-------------|----------|
| Slide-in từ trái với animation mượt | 150-200ms | ✓ |
| Xuất hiện ngay, không animation | | |
| Agent quyết định | | |

**User's choice:** Slide-in từ trái với animation mượt (150-200ms)

### Default state

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar mặc định collapsed (icon rail) khi lần đầu | | ✓ |
| Sidebar mặc định expanded khi lần đầu | | |
| Agent quyết định | | |

**User's choice:** Sidebar mặc định collapsed (icon rail) khi lần đầu

---

## Agent's Discretion

- Visual separation approach for Main vs Admin groups
- Admin icon position in the rail
- Exact dimensions (icon rail width, overlay panel width)
- Z-index layering, transition easing
- Whether clicking a nav link also collapses the sidebar

## Deferred Ideas

- LAY-05: Keyboard shortcut (Cmd+B) toggle — future requirement
- LAY-06: Mobile responsive sidebar — future requirement
