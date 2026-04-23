# Roadmap: LocalStock

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-16) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 UX Polish & Educational Depth** — Phases 7-10 (shipped 2026-04-21) — [Archive](milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 Admin Console** — Phases 11-13 (in progress)

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

### 🚧 v1.2 Admin Console

- [x] **Phase 11: Admin API Endpoints** - Backend routes for stock management, pipeline control, job history (2/2 plans) — completed 2026-04-22
- [x] **Phase 12: Admin Console UI** - Admin page with stock management, pipeline trigger, job monitoring (2/2 plans) (completed 2026-04-22)
- [x] **Phase 12.1: Performance & Polish** - Optimize admin table rendering, fix stale caches, improve UX polish (completed 2026-04-23)
  **Plans:** 2 plans
  Plans:
  - [x] 12.1-01-PLAN.md — Foundation: cache invalidation utility, job transition hook, i18n, CSS animation
  - [x] 12.1-02-PLAN.md — Integration: wire transitions into admin page, job row highlight + scroll
- [x] **Phase 13: AI Report Generation UI** - Generate AI reports for specific stocks from the admin console
  **Plans:** 2 plans
  Plans:
  - [x] 13-01-PLAN.md — Foundation: shadcn Sheet + Progress install, i18n keys, CSS animation
  - [x] 13-02-PLAN.md — Components + wiring: ReportProgress, job detail page, admin page integration

## Phase Details

### Phase 11: Admin API Endpoints
**Goal**: Backend exposes REST endpoints for admin operations (stock CRUD, pipeline trigger, job status)
**Depends on**: Phase 5 (automation service), Phase 1 (pipeline)
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04
**Success Criteria** (what must be TRUE):
  1. POST /api/admin/stocks — add a stock symbol to the watch list
  2. DELETE /api/admin/stocks/{symbol} — remove a stock from the watch list
  3. POST /api/admin/crawl — trigger crawl for 1 or more symbols (returns job ID)
  4. POST /api/admin/analyze — trigger analysis + scoring for 1 or more symbols
  5. POST /api/admin/pipeline — trigger full daily pipeline
  6. POST /api/admin/report — generate AI report for a specific symbol
  7. GET /api/admin/jobs — list recent pipeline/job history with status
  8. GET /api/admin/jobs/{id} — get detailed job status + errors
**Plans:** 2 plans
Plans:
- [x] 11-01-PLAN.md — Data layer foundation (models, migration, repositories)
- [x] 11-02-PLAN.md — Admin API endpoints + service + tests
**UI hint**: no

### Phase 12: Admin Console UI
**Goal**: Users can manage stocks, trigger pipeline operations, and monitor jobs from a web UI
**Depends on**: Phase 11
**Requirements**: ADMIN-05, ADMIN-06, ADMIN-07
**Success Criteria** (what must be TRUE):
  1. /admin page accessible from sidebar navigation
  2. Stock Management section: table of tracked stocks with add/remove buttons
  3. Pipeline Control section: buttons to trigger crawl, analyze, full pipeline for selected stocks
  4. Job Monitor section: table of recent jobs with status (running/completed/failed), duration, errors
  5. Real-time job status updates (polling or SSE)
**Plans**: 2 plans
Plans:
- [x] 12-01-PLAN.md — Foundation: types, hooks, i18n, sidebar nav, shadcn installs
- [x] 12-02-PLAN.md — Admin page: stock table, pipeline control, job monitor, page shell
**UI hint**: yes

### Phase 13: AI Report Generation UI
**Goal**: Users can generate and preview AI reports for any tracked stock from the admin console
**Depends on**: Phase 12
**Requirements**: ADMIN-08
**Success Criteria** (what must be TRUE):
  1. Generate Report button available per stock in admin console
  2. Report generation shows progress indicator while LLM is processing
  3. Generated report is immediately visible in the stock detail page
**Plans**: 2 plans
Plans:
- [ ] 13-01-PLAN.md — Foundation: shadcn Sheet + Progress install, i18n keys, CSS animation
- [ ] 13-02-PLAN.md — Components + wiring: ReportProgress, ReportPreview, ReportGenerationSheet, admin page integration

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
| 8. Stock Page Reading-First Redesign | v1.1 | - | Complete (merged into Phase 7) | 2026-04-20 |
| 9. Academic/Learning Page & Glossary Data | v1.1 | 2/2 | Complete | 2026-04-20 |
| 10. Interactive Glossary Linking | v1.1 | 2/2 | Complete | 2026-04-21 |
| 11. Admin API Endpoints | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12. Admin Console UI | v1.2 | 2/2 | Complete   | 2026-04-22 |
| 12.1 Performance & Polish | v1.2 | 2/2 | Complete | 2026-04-23 |
| 13. AI Report Generation UI | v1.2 | 0/2 | Not started | - |

## Backlog

### Phase 999.1: Paper Trading Emulator (BACKLOG)

**Goal:** Giả lập mua/bán cổ phiếu (paper trading) để kiểm chứng độ chính xác của khuyến nghị AI. Người dùng đặt lệnh mua thử với số lượng tùy chọn, hệ thống theo dõi P&L theo thời gian thực để đánh giá nhận định đúng/sai.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
