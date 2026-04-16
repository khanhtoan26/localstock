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
