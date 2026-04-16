# Phase 6: Web Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 06-web-dashboard
**Areas discussed:** Tech Stack, Layout & Navigation, Charts & Indicators

---

## Tech Stack

| Option | Description | Selected |
|--------|-------------|----------|
| Next.js + shadcn/ui | SSR, routing sẵn, component library tốt | ✓ |
| React + Vite + Tailwind | Đơn giản hơn, SPA thuần | |

**User's choice:** Next.js + shadcn/ui

| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo (folder `web/`) | Trong project hiện tại | ✓ |
| Repo riêng | Tách frontend ra repo khác | |

**User's choice:** Monorepo trong folder `web/`

---

## Layout & Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar cố định bên trái | Kiểu Simplize/Bloomberg | ✓ |
| Top navbar + tabs | Kiểu WiChart | |
| Sidebar co lại được | Full view cho chart | |

**User's choice:** Sidebar cố định bên trái

| Option | Description | Selected |
|--------|-------------|----------|
| Dark theme cố định | Kiểu terminal tài chính | ✓ |
| Light theme / Toggle | | |

**User's choice:** Dark theme cố định

**Page structure:** Agent's Discretion

---

## Charts & Indicators

| Option | Description | Selected |
|--------|-------------|----------|
| TradingView Lightweight Charts | 45KB, purpose-built | ✓ |
| Recharts | React-native | |

**User's choice:** TradingView Lightweight Charts

**Chart type (candlestick/line):** Agent's Discretion
**Indicators:** Overlay (SMA/EMA/BB) + panel phụ (MACD/RSI)

---

## Agent's Discretion

- Cấu trúc trang, loại biểu đồ, timeframe, responsive, empty/loading states

## Deferred Ideas

None
