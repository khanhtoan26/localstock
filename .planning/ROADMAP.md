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
- [ ] **Phase 15: Sidebar Float & Collapse** - Floating collapsible sidebar with icon rail and tab groups
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

### Phase 15: Sidebar Float & Collapse
**Goal**: Sidebar operates as a floating, collapsible panel with icon navigation and persistent state
**Depends on**: Phase 14
**Requirements**: LAY-01, LAY-02, LAY-03, LAY-04
**Success Criteria** (what must be TRUE):
  1. Sidebar collapses to a narrow icon rail (~56px) that is always visible; content area uses full width without left margin shift
  2. Clicking an icon expands the sidebar as a floating overlay panel — content underneath is not pushed or shifted
  3. Sidebar displays two tab groups (Main: Rankings, Market, Learn / Admin) with clear visual separation
  4. Collapsed/expanded state persists across page reloads via localStorage
  5. Clicking outside the expanded sidebar (backdrop area) collapses it back to the icon rail
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 15-01: TBD

### Phase 16: Table, Search & Session Bar
**Goal**: Tables sort correctly, search persists across navigation, and header shows live HOSE market session status
**Depends on**: Phase 15
**Requirements**: TBL-01, TBL-02, TBL-03, TBL-04, MKT-01, MKT-02
**Success Criteria** (what must be TRUE):
  1. Clicking a numeric column header sorts rows by numeric value (not alphabetically), with stock symbol as tiebreaker; active sort column shows directional arrow icon
  2. Search input on rankings page filters stocks by symbol or name; the search term survives navigation to another page and back (persisted in URL params)
  3. Header displays a market session progress bar showing current HOSE phase (Pre-market / ATO / Trading / Lunch / ATC / Closed) with time remaining countdown
  4. Outside trading hours (evenings, weekends), session bar shows when market next opens (e.g., "Opens in Xh Ym" or "Reopens Monday")
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 16-01: TBD

### Phase 17: Market Overview Metrics
**Goal**: Market Overview page displays live market summary data powered by a real backend API
**Depends on**: Phase 16
**Requirements**: MKT-03, MKT-04
**Success Criteria** (what must be TRUE):
  1. Market Overview page shows 4 metric cards (VN-Index, total volume, advances vs declines, market breadth) populated with real data from the backend
  2. Backend exposes a new API endpoint (GET /api/market/summary) returning current market summary data
  3. Metric cards auto-refresh periodically and display loading skeleton / error fallback gracefully when API is slow or unavailable
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 17-01: TBD

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
| 15. Sidebar Float & Collapse | v1.3 | 0/0 | Not started | - |
| 16. Table, Search & Session Bar | v1.3 | 0/0 | Not started | - |
| 17. Market Overview Metrics | v1.3 | 0/0 | Not started | - |

## Backlog

### Phase 999.1: Paper Trading Emulator (BACKLOG)

**Goal:** Giả lập mua/bán cổ phiếu (paper trading) để kiểm chứng độ chính xác của khuyến nghị AI. Người dùng đặt lệnh mua thử với số lượng tùy chọn, hệ thống theo dõi P&L theo thời gian thực để đánh giá nhận định đúng/sai.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
