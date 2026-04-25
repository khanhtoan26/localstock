# Roadmap: LocalStock

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-16) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 UX Polish & Educational Depth** — Phases 7-10 (shipped 2026-04-21) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Admin Console** — Phases 11-13 (shipped 2026-04-23) — [Archive](milestones/v1.2-ROADMAP.md)
- 🚧 **v1.3 UI/UX Refinement** — Phases 14-17 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-04-16</summary>

- [x] Phase 1: Foundation & Data Pipeline (4/4 plans) — completed 2026-04-14
- [x] Phase 2: Technical & Fundamental Analysis (4/4 plans) — completed 2026-04-14
- [x] Phase 3: Sentiment Analysis & Scoring Engine (4/4 plans) — completed 2026-04-15
- [x] Phase 4: AI Reports, Macro Context & T+3 Awareness (4/4 plans) — completed 2026-04-15
- [x] Phase 5: Automation & Notifications (3/3 plans) — completed 2026-04-15
- [x] Phase 6: Web Dashboard (4/4 plans) — completed 2026-04-16

</details>

<details>
<summary>✅ v1.1 UX Polish & Educational Depth (Phases 7-10) — SHIPPED 2026-04-21</summary>

- [x] Phase 7: Theme Foundation & Visual Identity (4/4 plans) — completed 2026-04-20
- [x] Phase 8: Stock Page Reading-First Redesign (merged into Phase 7) — completed 2026-04-20
- [x] Phase 9: Academic/Learning Page & Glossary Data (2/2 plans) — completed 2026-04-20
- [x] Phase 10: Interactive Glossary Linking (2/2 plans) — completed 2026-04-21

</details>

<details>
<summary>✅ v1.2 Admin Console (Phases 11-13) — SHIPPED 2026-04-23</summary>

- [x] Phase 11: Admin API Endpoints (2/2 plans) — completed 2026-04-22
- [x] Phase 12: Admin Console UI (2/2 plans) — completed 2026-04-22
- [x] Phase 12.1: Performance & Polish (2/2 plans) — completed 2026-04-23
- [x] Phase 13: AI Report Generation UI (2/2 plans) — completed 2026-04-23

</details>

### 🚧 v1.3 UI/UX Refinement (In Progress)

**Milestone Goal:** Cải thiện giao diện và trải nghiệm người dùng — font, màu sắc, sidebar, table, search, market session indicator, market metrics.

- [x] **Phase 14: Visual Foundation** - Source Sans 3 font + warm neutral color palette (light & dark) — completed 2026-04-24
- [x] **Phase 15: Sidebar Redesign** - Claude Desktop floating card sidebar with tabs, push-content layout — completed 2026-04-24
- [ ] **Phase 16: Table, Search & Session Bar** - Sort fix, search persistence, market session progress bar
- [ ] **Phase 17: Market Overview Metrics** - Live 4-card market summary with new backend API

## Phase Details

### Phase 14: Visual Foundation
**Goal**: All pages render with Source Sans 3 typography and warm neutral color palette in both themes
**Depends on**: Phase 13 (v1.2 complete)
**Requirements**: VIS-01, VIS-02, VIS-03
**Success Criteria** (what must be TRUE):
  1. All text across the application renders in Source Sans 3, including Vietnamese characters with diacritics
  2. Buttons, links, and interactive elements use warm neutral accent color instead of blue
  3. Dark mode uses corresponding warm palette with WCAG AA contrast on all text
  4. Financial indicator colors (stock-up green, stock-down red, warning yellow) remain visually distinct from the new primary accent
**Plans**: 1 plan

Plans:
- [x] 14-01-PLAN.md — Source Sans 3 font + neutral color palette (both themes) + hardcoded blue cleanup ✅

### Phase 15: Sidebar Redesign
**Goal**: Sidebar redesigned as a Claude Desktop-style floating card with full-width header, tab switcher, and push-content layout
**Depends on**: Phase 14
**Requirements**: LAY-01, LAY-02, LAY-03, LAY-04
**Success Criteria** (what must be TRUE):
  1. Full-width top header (48px) with toggle button, logo, theme/language controls
  2. Sidebar is a floating card (rounded-xl, shadow, 260px) overlaying main content, 8px inset from edges
  3. Sidebar slides in/out via translateX with 220ms transition; state persists in localStorage
  4. Tab switcher (Screener/Watchlist/Reports) with icon-only centered display
  5. Three-zone structure: New Analysis + Search → Tabs + Nav (Rankings/Market/Learn) + Pinned/Recents → Footer (avatar + settings)
  6. Claude color palette: #f5f4ee app bg, #faf9f5 sidebar, #ffffff main panel; dark mode #1f1e1d/#2a2927
  7. Main panel uses padding-left push pattern (280px open, 24px closed) — always full-width background
**Plans**: 3 plans (design pivoted multiple times — final is Claude Desktop floating card)

Plans:
- [x] 15-01-PLAN.md — Foundation primitives (useSidebarState hook + Tooltip component) ✅
- [x] 15-02-PLAN.md — Floating sidebar component + layout restructuring ✅
- [x] 15-03-PLAN.md — Visual verification checkpoint ✅ (approved after redesign)

### Phase 16: Table, Search & Session Bar
**Goal**: Tables sort correctly, search persists across navigation, and header shows live HOSE market session status
**Depends on**: Phase 15
**Requirements**: TBL-01, TBL-02, TBL-03, TBL-04, MKT-01, MKT-02
**Success Criteria** (what must be TRUE):
  1. Clicking a numeric column header sorts rows by numeric value (not alphabetically), with stock symbol as tiebreaker; active sort column shows directional arrow icon
  2. Search input on rankings page filters stocks by symbol or name; the search term survives navigation to another page and back (persisted in URL params)
  3. Header displays a market session progress bar showing current HOSE phase (Pre-market / ATO / Trading / Lunch / ATC / Closed) with time remaining countdown
  4. Outside trading hours (evenings, weekends), session bar shows when market next opens (e.g., "Opens in Xh Ym" or "Reopens Monday")
**Plans**: 6 plans

Plans:
- [ ] 16-00-PLAN.md — Wave 0: Test stub files (sort-comparator, search-filter, hose-session)
- [ ] 16-01-PLAN.md — nuqs install + NuqsAdapter in layout.tsx (TBL-04 foundation)
- [ ] 16-02-PLAN.md — Table sort fix: sort-comparator.ts + stock-table.tsx (TBL-01, TBL-02)
- [ ] 16-03-PLAN.md — Search bar: filter-stocks.ts + StockSearchInput + rankings page + i18n (TBL-03, TBL-04)
- [ ] 16-04-PLAN.md — Market session bar: hose-session.ts + MarketSessionBar + app-shell + i18n (MKT-01, MKT-02)
- [ ] 16-05-PLAN.md — Visual verification checkpoint

### Phase 17: Market Overview Metrics
**Goal**: Market Overview page displays live market summary data powered by a real backend API
**Depends on**: Phase 16
**Requirements**: MKT-03, MKT-04
**Success Criteria** (what must be TRUE):
  1. Market Overview page shows 4 metric cards (VN-Index, total volume, advances vs declines, market breadth) populated with real data from the backend
  2. Backend exposes a new API endpoint (GET /api/market/summary) returning current market summary data
  3. Metric cards auto-refresh periodically and display loading skeleton / error fallback gracefully when API is slow or unavailable
**Plans**: 4 plans

Plans:
- [x] 17-00-PLAN.md — Wave 0: test stub file (test_market_route.py) — Nyquist RED state
- [x] 17-01-PLAN.md — Backend: PriceRepository.get_market_aggregate() + market.py router + app.py registration (MKT-04)
- [ ] 17-02-PLAN.md — Frontend: types + hook + MarketSummaryCards component + page integration + i18n (MKT-03)
- [ ] 17-03-PLAN.md — Visual verification checkpoint

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | v1.0 | 4/4 | Complete | 2026-04-14 |
| 2. Technical & Fundamental Analysis | v1.0 | 4/4 | Complete | 2026-04-14 |
| 3. Sentiment Analysis & Scoring Engine | v1.0 | 4/4 | Complete | 2026-04-15 |
| 4. AI Reports, Macro Context & T+3 | v1.0 | 4/4 | Complete | 2026-04-15 |
| 5. Automation & Notifications | v1.0 | 3/3 | Complete | 2026-04-15 |
| 6. Web Dashboard | v1.0 | 4/4 | Complete | 2026-04-16 |
| 7. Theme Foundation & Visual Identity | v1.1 | 4/4 | Complete | 2026-04-20 |
| 8. Stock Page Reading-First Redesign | v1.1 | - | Complete (merged) | 2026-04-20 |
| 9. Academic/Learning Page & Glossary Data | v1.1 | 2/2 | Complete | 2026-04-20 |
| 10. Interactive Glossary Linking | v1.1 | 2/2 | Complete | 2026-04-21 |
| 11. Admin API Endpoints | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12. Admin Console UI | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12.1 Performance & Polish | v1.2 | 2/2 | Complete | 2026-04-23 |
| 13. AI Report Generation UI | v1.2 | 2/2 | Complete | 2026-04-23 |
| 14. Visual Foundation | v1.3 | 0/1 | Planning complete | - |
| 15. Sidebar Float & Collapse | v1.3 | 1/3 | In progress | - |
| 16. Table, Search & Session Bar | v1.3 | 0/6 | Planning complete | - |
| 17. Market Overview Metrics | v1.3 | 0/4 | Planning complete | - |

## Backlog

### Phase 999.1: Paper Trading Emulator (BACKLOG)

**Goal:** Giả lập mua/bán cổ phiếu (paper trading) để kiểm chứng độ chính xác của khuyến nghị AI. Người dùng đặt lệnh mua thử với số lượng tùy chọn, hệ thống theo dõi P&L theo thời gian thực để đánh giá nhận định đúng/sai.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
