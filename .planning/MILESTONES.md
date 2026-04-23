# Milestones

## v1.0 MVP (Shipped: 2026-04-16)

**Phases completed:** 6 phases, 23 plans, 45 tasks

**Key accomplishments:**

- Data pipeline: Automated crawlers for ~400 HOSE stocks (OHLCV, financials, corporate actions) with PostgreSQL storage and Alembic migrations
- Analysis engine: 11 technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands), fundamental ratios (P/E, P/B, ROE, ROA), and industry comparison across 20 VN-specific ICB sectors
- AI scoring: Multi-dimensional scoring engine (0-100) combining technical + fundamental + sentiment + macro, with sector rotation and change detection alerts
- AI reports: Vietnamese-language analysis reports via local Ollama LLM explaining WHY stocks score high/low, with macro context and T+3 settlement awareness
- Automation: Daily pipeline via APScheduler running after market close (15:30), Telegram bot notifications for daily digests and special alerts
- Web dashboard: Next.js 16 dark-theme dashboard with stock rankings table, candlestick charts (lightweight-charts v5), market overview, and sector analysis

---

## v1.1 UX Polish & Educational Depth (Shipped: 2026-04-21)

**Phases completed:** 4 phases (7-10), 12 plans

**Key accomplishments:**

- Theme system: Warm cream + dark theme with FOUC-free switching, financial-grade color tokens, chart auto-re-theming
- Stock page redesign: Reading-first layout with AI report center-stage, drawer for chart/data, URL-persisted state
- Learning hub: 3-category glossary (/learn/technical, /learn/fundamental, /learn/macro) with 15+ Vietnamese entries and diacritic-insensitive search
- Interactive glossary: Auto-linking glossary terms in AI reports, hover card previews, deep-link navigation

---

## v1.2 Admin Console (Shipped: 2026-04-23)

**Phases completed:** 4 phases (11-13 + 12.1), 8 plans

**Key accomplishments:**

- Admin API: 8 REST endpoints for stock CRUD, pipeline triggers (crawl/analyze/score/report/full), job management with background execution
- Admin Console UI: Full admin page with stock table (add/remove), pipeline control buttons, job monitor with real-time polling
- Job transitions: Toast notifications on job completion/failure with cache invalidation, row highlight + scroll-into-view
- AI Report Generation: Dedicated job detail page (/admin/jobs/[id]) with step progress indicator, inline report rendering, error display

**Known deferred items at close:** 4 (UAT gaps in phases 7/12, human verification in phases 9/13)

---
