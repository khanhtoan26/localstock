# Roadmap: LocalStock

## Overview

LocalStock follows the natural data dependency chain: crawl market data → compute analysis → score with AI → generate reports → automate daily → present in dashboard. Each phase delivers a coherent, verifiable capability that builds on the previous. The pipeline architecture means nothing downstream works without upstream data — so we get data right first, then add intelligence layer by layer.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Data Pipeline** - Crawl and store reliable HOSE market data (~400 tickers, ≥2yr history, financial statements, corporate actions)
- [ ] **Phase 2: Technical & Fundamental Analysis** - Compute technical indicators, volume analysis, trend identification, financial ratios, and industry comparisons
- [ ] **Phase 3: Sentiment Analysis & Scoring Engine** - Set up LLM (Ollama), classify news sentiment, and produce composite stock rankings with configurable weights
- [ ] **Phase 4: AI Reports, Macro Context & T+3 Awareness** - Generate Vietnamese-language analysis reports, collect macro data, and add T+3 settlement context to recommendations
- [ ] **Phase 5: Automation & Notifications** - Run pipeline daily after market close, send Telegram alerts, detect score changes and sector rotation
- [ ] **Phase 6: Web Dashboard** - Visual interface for browsing rankings, stock charts, technical indicators, and AI reports

## Phase Details

### Phase 1: Foundation & Data Pipeline
**Goal**: Reliable data ingestion and storage for all HOSE stocks — the foundation everything else depends on
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. Agent crawls daily OHLCV data for ~400 HOSE tickers and stores it in the database
  2. Database contains ≥2 years of historical price/volume data per ticker
  3. Quarterly and annual financial statements (income statement, balance sheet, cash flow) are stored for each company
  4. Company profiles (industry sector, market cap, shares outstanding) are queryable from the database
  5. Historical price data is correctly adjusted for corporate actions (stock splits, stock dividends) — no false signals from unadjusted prices
**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold, DB models, Alembic migrations, base crawler, test infrastructure
- [ ] 01-02-PLAN.md — Stock listing fetcher, OHLCV price crawler, stock & price repositories
- [ ] 01-03-PLAN.md — Financial statement crawler, company profile crawler, financial repository
- [ ] 01-04-PLAN.md — Corporate event crawler, price adjustment service, pipeline orchestrator, health check

### Phase 2: Technical & Fundamental Analysis
**Goal**: Computed technical indicators and financial ratios for all HOSE stocks — the first two scoring dimensions
**Depends on**: Phase 1
**Requirements**: TECH-01, TECH-02, TECH-03, TECH-04, FUND-01, FUND-02, FUND-03
**Success Criteria** (what must be TRUE):
  1. Core technical indicators (SMA 20/50/200, EMA 12/26, RSI 14, MACD 12/26/9, Bollinger Bands 20/2) are calculated and stored for all tickers
  2. Volume analysis (average volume, relative volume, volume trend) is computed and queryable per ticker
  3. Each stock has an identified trend direction (uptrend/downtrend/sideways) with support and resistance levels
  4. Key financial ratios (P/E, P/B, EPS, ROE, ROA, D/E) are calculated from financial statements for all companies
  5. Revenue and profit growth rates (QoQ, YoY) are computed and each stock's ratios are compared against its ICB industry average
**Plans**: TBD

### Phase 3: Sentiment Analysis & Scoring Engine
**Goal**: AI-powered multi-dimensional stock scoring that produces a ranked recommendation list
**Depends on**: Phase 2
**Requirements**: SENT-01, SENT-02, SENT-03, SCOR-01, SCOR-02, SCOR-03
**Success Criteria** (what must be TRUE):
  1. Agent crawls financial news from Vietnamese sources and uses LLM to classify sentiment (positive/negative/neutral) per ticker
  2. Each stock has an aggregated sentiment score derived from multiple recent news articles
  3. Composite score (0-100) is calculated for each stock combining available analysis dimensions (technical, fundamental, sentiment)
  4. Scoring weights are configurable via config (default: technical 30%, fundamental 30%, sentiment 20%, macro 20%)
  5. User can view a ranked top 10-20 list of recommended stocks with scores and clear buy reasoning via CLI
**Plans**: TBD

### Phase 4: AI Reports, Macro Context & T+3 Awareness
**Goal**: Rich Vietnamese-language analysis reports that explain WHY stocks score high/low, enriched with macro-economic context and T+3 trading awareness
**Depends on**: Phase 3
**Requirements**: REPT-01, REPT-02, MACR-01, MACR-02, T3-01, T3-02
**Success Criteria** (what must be TRUE):
  1. LLM generates Vietnamese reports for top-ranked stocks explaining WHY each scores high/low — covering technical signals, fundamental assessment, news sentiment, and macro impact
  2. Macro-economic data (SBV interest rates, USD/VND exchange rate, CPI, GDP) is collected and stored in the database
  3. Reports link macro conditions to specific sector/stock impact (e.g., rising interest rates → negative for real estate, positive for banks)
  4. Swing trade suggestions include a ≥3-day trend prediction with explicit T+3 settlement warning
  5. Long-term investment and swing trade recommendations are clearly distinguished in reports
**Plans**: TBD

### Phase 5: Automation & Notifications
**Goal**: Fully automated daily pipeline that runs after market close and sends intelligent alerts via Telegram
**Depends on**: Phase 4
**Requirements**: AUTO-01, AUTO-02, NOTI-01, NOTI-02, SCOR-04, SCOR-05
**Success Criteria** (what must be TRUE):
  1. Full pipeline (crawl → analyze → score → report → notify) runs automatically every day after market close (after 15:30) without manual intervention
  2. User can trigger on-demand analysis for a single ticker or full market scan
  3. Telegram bot sends daily digest of top buy suggestions after each automated run
  4. Telegram sends special alerts when significant score changes (>15 points) or strong signals are detected
  5. System detects and reports sector rotation patterns — tracking money flow between industries over time
**Plans**: TBD

### Phase 6: Web Dashboard
**Goal**: Visual web interface for browsing stock rankings, viewing charts with technical indicators, and reading AI analysis reports
**Depends on**: Phase 4 (can develop in parallel with Phase 5)
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Dashboard displays a ranked stock table sortable by composite score with key metrics visible
  2. Stock detail page shows interactive price chart with technical indicators and the full AI analysis report
  3. Dashboard includes a market overview section with macro analysis summary and sector performance
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | 0/TBD | Not started | - |
| 2. Technical & Fundamental Analysis | 0/TBD | Not started | - |
| 3. Sentiment Analysis & Scoring Engine | 0/TBD | Not started | - |
| 4. AI Reports, Macro Context & T+3 | 0/TBD | Not started | - |
| 5. Automation & Notifications | 0/TBD | Not started | - |
| 6. Web Dashboard | 0/TBD | Not started | - |
