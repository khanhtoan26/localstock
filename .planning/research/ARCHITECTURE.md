# Architecture Research

**Domain:** Stock Analysis AI Agent (Vietnamese Market — HOSE)
**Researched:** 2025-07-18
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│  ┌──────────────────┐  ┌──────────────────┐                         │
│  │  Web Dashboard   │  │  Telegram Bot    │                         │
│  │  (FastAPI +      │  │  (Notifications  │                         │
│  │   Static HTML)   │  │   + On-demand)   │                         │
│  └────────┬─────────┘  └────────┬─────────┘                         │
├───────────┴────────────────────┴────────────────────────────────────┤
│                         API LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              FastAPI REST API (Internal)                      │   │
│  │   /stocks  /rankings  /reports  /analysis  /triggers         │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
├─────────────────────────┴───────────────────────────────────────────┤
│                      ORCHESTRATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐          │
│  │  Scheduler   │  │  Pipeline    │  │  On-Demand       │          │
│  │  (APScheduler│  │  Coordinator │  │  Trigger         │          │
│  │   daily run) │  │  (run steps) │  │  (API/Telegram)  │          │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘          │
├─────────┴─────────────────┴───────────────────┴─────────────────────┤
│                       ANALYSIS LAYER                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐     │
│  │ Technical │  │Fundamental│  │ Sentiment │  │   Macro      │     │
│  │ Analysis  │  │ Analysis  │  │ Analysis  │  │  Analysis    │     │
│  │(pandas-ta)│  │(ratios)   │  │(Ollama)   │  │(indicators)  │     │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘     │
│        └───────────────┴──────────────┴───────────────┘             │
│                         ↓                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Scoring Engine (Aggregator)                      │   │
│  │   Weights: Technical 30% + Fundamental 30% +                 │   │
│  │            Sentiment 20% + Macro 20%                         │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         ↓                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              AI Synthesis (Ollama LLM)                        │   │
│  │   Generate human-readable report + recommendation            │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      DATA INGESTION LAYER                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐     │
│  │  Price    │  │ Financial │  │   News    │  │   Macro      │     │
│  │  Crawler  │  │  Report   │  │  Crawler  │  │   Data       │     │
│  │ (vnstock) │  │  Crawler  │  │(httpx/bs4)│  │  Collector   │     │
│  │          │  │ (vnstock) │  │           │  │ (manual/API) │     │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘     │
├────────┴──────────────┴──────────────┴───────────────┴──────────────┤
│                      STORAGE LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SQLite Database                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │   │
│  │  │ prices   │ │financials│ │  news    │ │  macro_data  │    │   │
│  │  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────────┤    │   │
│  │  │ stocks   │ │  scores  │ │ reports  │ │  run_history │    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Price Crawler** | Fetch daily OHLCV data for ~400 HOSE stocks | `vnstock.Quote` with source `KBS` or `VCI` |
| **Financial Report Crawler** | Fetch balance sheet, income statement, ratios | `vnstock.Finance` — balance_sheet, income_statement, ratio |
| **News Crawler** | Scrape financial news articles from Vietnamese sources | `httpx` + `beautifulsoup4` against CafeF, VnExpress Finance |
| **Macro Data Collector** | Gather interest rates, exchange rates, CPI, GDP | Mix of web scraping + manual CSV updates (SBV, GSO) |
| **Technical Analysis** | Calculate MA, RSI, MACD, Bollinger Bands, etc. | `pandas-ta` (150+ indicators, numba-accelerated) |
| **Fundamental Analysis** | Compute P/E, EPS, ROE, debt ratios from reports | Pure Python/pandas calculations from crawled financials |
| **Sentiment Analysis** | Classify news as positive/negative/neutral per stock | Ollama LLM with structured JSON output |
| **Macro Analysis** | Assess market environment from macro indicators | Rule-based scoring + LLM context synthesis |
| **Scoring Engine** | Aggregate multi-dimensional scores into final ranking | Weighted average with configurable weights |
| **AI Synthesis** | Generate human-readable report per stock | Ollama LLM — takes all analysis as context, outputs report |
| **Pipeline Coordinator** | Orchestrate crawl → analyze → score → report sequence | Python function chain, sequential execution |
| **Scheduler** | Trigger daily automated runs (after market close) | `APScheduler` with cron trigger (e.g., 15:30 daily) |
| **REST API** | Expose data to dashboard + accept on-demand triggers | `FastAPI` with JSON endpoints |
| **Web Dashboard** | Display rankings, charts, stock detail views | FastAPI serving static HTML/JS + Jinja2 templates, or lightweight React |
| **Telegram Bot** | Send alerts for top-ranked stocks, accept commands | `python-telegram-bot` library |

## Recommended Project Structure

```
localstock/
├── src/
│   ├── crawlers/              # Data ingestion layer
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract crawler interface
│   │   ├── price_crawler.py   # Stock price data via vnstock
│   │   ├── finance_crawler.py # Financial reports via vnstock
│   │   ├── news_crawler.py    # News scraping from CafeF/VnExpress
│   │   └── macro_crawler.py   # Macro economic data
│   │
│   ├── analysis/              # Analysis engine
│   │   ├── __init__.py
│   │   ├── technical.py       # Technical indicators (pandas-ta)
│   │   ├── fundamental.py     # Fundamental ratio calculations
│   │   ├── sentiment.py       # LLM-based sentiment analysis
│   │   └── macro.py           # Macro environment scoring
│   │
│   ├── scoring/               # Scoring & ranking
│   │   ├── __init__.py
│   │   ├── scorer.py          # Multi-dimensional score aggregation
│   │   └── config.py          # Scoring weights & thresholds
│   │
│   ├── ai/                    # LLM integration
│   │   ├── __init__.py
│   │   ├── client.py          # Ollama client wrapper
│   │   ├── prompts.py         # Prompt templates
│   │   └── synthesizer.py     # Report generation
│   │
│   ├── pipeline/              # Orchestration
│   │   ├── __init__.py
│   │   ├── coordinator.py     # Pipeline execution logic
│   │   └── scheduler.py       # APScheduler setup
│   │
│   ├── api/                   # FastAPI application
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI app setup
│   │   ├── routes/            # API route handlers
│   │   │   ├── stocks.py
│   │   │   ├── rankings.py
│   │   │   ├── reports.py
│   │   │   └── triggers.py
│   │   └── deps.py            # Dependencies (DB session, etc.)
│   │
│   ├── notifications/         # Alert system
│   │   ├── __init__.py
│   │   └── telegram.py        # Telegram bot integration
│   │
│   ├── db/                    # Database layer
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── database.py        # Engine & session setup
│   │   └── migrations/        # Alembic migrations (optional)
│   │
│   └── config.py              # App-wide configuration
│
├── dashboard/                  # Frontend static files
│   ├── index.html
│   ├── css/
│   └── js/
│
├── data/                       # Local data directory
│   └── localstock.db          # SQLite database file
│
├── tests/
│   ├── test_crawlers/
│   ├── test_analysis/
│   ├── test_scoring/
│   └── test_ai/
│
├── pyproject.toml              # Project config & dependencies
├── .env.example                # Environment variables template
└── README.md
```

### Structure Rationale

- **src/crawlers/:** Each data source is isolated — if one API changes or breaks, only its crawler needs updating. The `base.py` defines a common interface so crawlers are interchangeable.
- **src/analysis/:** Each analysis dimension is a standalone module. They all take DataFrames in and produce scored results out. No cross-dependencies between analysis modules.
- **src/scoring/:** Separated from analysis because it's the aggregation point. Scoring weights are configurable in `config.py`, making it easy to tune without touching analysis logic.
- **src/ai/:** Ollama integration is isolated behind a clean interface. If you ever switch to a different LLM backend (or add cloud LLM), only this module changes.
- **src/pipeline/:** The coordinator knows the order of operations but delegates actual work to crawlers, analyzers, and scorers. This separation means you can run any individual step independently.
- **src/db/:** Repository pattern with SQLAlchemy ORM. The database is a detail, not the architecture — switching from SQLite to PostgreSQL means changing one connection string.

## Architectural Patterns

### Pattern 1: Pipeline Architecture (ETL + Analysis)

**What:** The system is a data pipeline with clear stages: Ingest → Store → Analyze → Score → Present. Each stage produces output consumed by the next stage.

**When to use:** Data processing systems where steps are sequential and each step enriches the data.

**Trade-offs:**
- ✅ Simple mental model, easy to debug (inspect data at any stage)
- ✅ Each stage can be run independently for testing
- ✅ Natural fit for batch processing (daily runs)
- ❌ Not great for real-time — but we don't need real-time

**Example:**
```python
# pipeline/coordinator.py
class PipelineCoordinator:
    def __init__(self, db, crawlers, analyzers, scorer, synthesizer):
        self.db = db
        self.crawlers = crawlers
        self.analyzers = analyzers
        self.scorer = scorer
        self.synthesizer = synthesizer

    async def run_full_pipeline(self, date: str = None):
        """Execute the complete analysis pipeline."""
        run_id = self.db.create_run(date or today())

        # Stage 1: Ingest
        symbols = await self.crawlers.price.fetch_all_hose()
        await self.crawlers.finance.fetch_reports(symbols)
        articles = await self.crawlers.news.fetch_latest()
        macro = await self.crawlers.macro.fetch_current()

        # Stage 2: Analyze
        tech_scores = self.analyzers.technical.analyze(symbols)
        fund_scores = self.analyzers.fundamental.analyze(symbols)
        sent_scores = await self.analyzers.sentiment.analyze(articles)
        macro_score = self.analyzers.macro.analyze(macro)

        # Stage 3: Score & Rank
        rankings = self.scorer.aggregate(
            tech_scores, fund_scores, sent_scores, macro_score
        )

        # Stage 4: Synthesize reports (LLM)
        for stock in rankings.top(20):
            report = await self.synthesizer.generate_report(stock)
            self.db.save_report(run_id, stock.symbol, report)

        # Stage 5: Notify
        await self.notify_top_picks(rankings)

        return run_id
```

### Pattern 2: Repository Pattern for Data Access

**What:** Abstract database access behind repository classes. Business logic never touches SQL directly.

**When to use:** Any project where you want testability and the ability to swap storage backends.

**Trade-offs:**
- ✅ Easy to test (mock the repository)
- ✅ SQLite → PostgreSQL migration is trivial
- ✅ Clear data access boundaries
- ❌ Slight overhead for a single-user tool (acceptable)

**Example:**
```python
# db/models.py
from sqlalchemy import Column, Integer, Float, String, Date, DateTime
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class StockPrice(Base):
    __tablename__ = "stock_prices"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True)
    date = Column(Date, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

class StockScore(Base):
    __tablename__ = "stock_scores"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, index=True)
    symbol = Column(String(10), index=True)
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    macro_score = Column(Float)
    total_score = Column(Float)
    rank = Column(Integer)
```

### Pattern 3: LLM as a Service (Internal)

**What:** Treat the local Ollama LLM as an internal microservice. Wrap it in a client class with retries, structured output parsing, and prompt management. Separate prompt templates from business logic.

**When to use:** Any LLM integration where you need reliable, structured outputs.

**Trade-offs:**
- ✅ Prompt changes don't require code changes
- ✅ Structured JSON output via Ollama's `format` parameter ensures parseable results
- ✅ Easy to swap models (Qwen2.5 → Llama 3.1 → Mistral)
- ❌ LLM inference is the slowest step (mitigate with batch processing)

**Example:**
```python
# ai/client.py
from ollama import chat
from pydantic import BaseModel

class SentimentResult(BaseModel):
    sentiment: str  # "positive", "negative", "neutral"
    confidence: float
    key_factors: list[str]
    summary: str

class OllamaClient:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model

    async def analyze_sentiment(self, article: str, symbol: str) -> SentimentResult:
        response = chat(
            model=self.model,
            messages=[{
                "role": "system",
                "content": SENTIMENT_SYSTEM_PROMPT,
            }, {
                "role": "user",
                "content": f"Analyze sentiment for {symbol}:\n{article}",
            }],
            format=SentimentResult.model_json_schema(),  # Structured output
        )
        return SentimentResult.model_validate_json(response.message.content)
```

### Pattern 4: Configurable Scoring Weights

**What:** Scoring weights and thresholds are configuration, not code. Store them in a YAML/JSON config file or dataclass so users can tune without modifying analysis logic.

**When to use:** Any scoring/ranking system where the weighting formula is subjective.

**Trade-offs:**
- ✅ Easy to experiment with different weightings
- ✅ Can have presets (conservative, aggressive, balanced)
- ❌ Users need to understand what the weights mean

**Example:**
```python
# scoring/config.py
from dataclasses import dataclass

@dataclass
class ScoringConfig:
    # Dimension weights (must sum to 1.0)
    technical_weight: float = 0.30
    fundamental_weight: float = 0.30
    sentiment_weight: float = 0.20
    macro_weight: float = 0.20

    # Score thresholds
    buy_threshold: float = 75.0    # Score >= 75 → "Buy" signal
    watch_threshold: float = 60.0  # Score 60-75 → "Watch"
    # Below 60 → "Avoid"

    # Technical indicator settings
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ma_short_period: int = 20
    ma_long_period: int = 50
```

## Data Flow

### Daily Pipeline Flow

```
[Market Close 15:00]
        ↓
[Scheduler triggers at 15:30]
        ↓
┌─── INGEST ──────────────────────────────────────────┐
│                                                      │
│  vnstock API ──→ Price data (400 symbols)            │
│                  ~2-5 min (rate-limited)              │
│                         ↓                            │
│  vnstock API ──→ Financial reports (quarterly)       │
│                  ~5-10 min (cached, not daily)        │
│                         ↓                            │
│  HTTP scrape ──→ News articles (CafeF, VnExpress)   │
│                  ~2-3 min                            │
│                         ↓                            │
│  HTTP/manual ──→ Macro data (rates, CPI, FX)        │
│                  ~1 min (infrequent updates)         │
│                                                      │
│  ALL DATA ──→ SQLite DB                             │
└──────────────────────────────────────────────────────┘
        ↓
┌─── ANALYZE ─────────────────────────────────────────┐
│                                                      │
│  Price data ──→ pandas-ta ──→ Technical scores       │
│                 (MA, RSI, MACD, BB per symbol)       │
│                 ~1-2 min for 400 symbols             │
│                         ↓                            │
│  Financial data ──→ Ratio calc ──→ Fundamental scores│
│                     (P/E, EPS, ROE, debt)            │
│                     ~30 sec                          │
│                         ↓                            │
│  News articles ──→ Ollama LLM ──→ Sentiment scores  │
│                    (per-article classification)       │
│                    ~10-20 min (LLM bottleneck)       │
│                         ↓                            │
│  Macro data ──→ Rule engine ──→ Macro score          │
│                 (environment assessment)             │
│                 ~instant                             │
│                                                      │
│  ALL SCORES ──→ SQLite DB                           │
└──────────────────────────────────────────────────────┘
        ↓
┌─── SCORE & RANK ────────────────────────────────────┐
│                                                      │
│  Weighted aggregation ──→ Total score per symbol     │
│  Sort by score ──→ Rankings                          │
│  ~instant                                            │
│                                                      │
│  RANKINGS ──→ SQLite DB                             │
└──────────────────────────────────────────────────────┘
        ↓
┌─── SYNTHESIZE (Top 20 only) ────────────────────────┐
│                                                      │
│  All analysis data ──→ Ollama LLM ──→ Report text   │
│  (structured prompt with all dimensions)             │
│  ~5-10 min for top 20 stocks                        │
│                                                      │
│  REPORTS ──→ SQLite DB                              │
└──────────────────────────────────────────────────────┘
        ↓
┌─── NOTIFY ──────────────────────────────────────────┐
│                                                      │
│  Top-ranked stocks ──→ Telegram message              │
│  Score changes ──→ Alert if significant              │
│                                                      │
└──────────────────────────────────────────────────────┘
        ↓
[Dashboard reads from DB — always current]
```

### On-Demand Flow

```
[User triggers via Dashboard or Telegram]
        ↓
[API receives request]
        ↓
[Pipeline Coordinator runs targeted analysis]
  - Single stock: full analysis for 1 symbol (~2-3 min)
  - Refresh all: full pipeline (~30-40 min)
        ↓
[Results returned immediately or via notification]
```

### Key Data Flows

1. **Price ingestion:** vnstock API → pandas DataFrame → SQLite `stock_prices` table. Append-only, partitioned by date. Historical data fetched once, daily data appended.

2. **Technical analysis:** Read price history from DB → pandas-ta computes indicators → scores normalized to 0-100 → saved to `stock_scores` with dimension breakdown.

3. **Sentiment pipeline:** News crawler → raw articles stored in `news` table → batch of articles sent to Ollama one-by-one → sentiment result (positive/negative/neutral + confidence) stored back → aggregated per symbol.

4. **Report generation:** All scores + raw data for a stock assembled into a structured prompt → Ollama generates human-readable Vietnamese report → stored in `reports` table → served via API to dashboard.

5. **Notification:** After pipeline completes, scorer identifies stocks crossing thresholds (new entries in top 10, big score changes) → formats Telegram message → sends via bot API.

## Database Schema (Key Tables)

```sql
-- Core reference
stocks (symbol PK, name, industry, exchange, listed_date)

-- Price data (append-only, daily)
stock_prices (id PK, symbol FK, date, open, high, low, close, volume)
  INDEX: (symbol, date) UNIQUE

-- Financial reports (quarterly)
financials (id PK, symbol FK, period, year, quarter,
            revenue, net_income, total_assets, equity,
            eps, pe, roe, roa, debt_to_equity)
  INDEX: (symbol, year, quarter) UNIQUE

-- News articles
news (id PK, title, url UNIQUE, source, published_at,
      content_snippet, symbols_mentioned JSON)

-- Sentiment results
sentiments (id PK, news_id FK, symbol, sentiment, confidence,
            key_factors JSON, analyzed_at)

-- Macro indicators
macro_data (id PK, indicator, value, date, source)
  INDEX: (indicator, date) UNIQUE

-- Analysis results per run
stock_scores (id PK, run_id, symbol FK, date,
              technical_score, fundamental_score,
              sentiment_score, macro_score,
              total_score, rank)
  INDEX: (run_id, symbol) UNIQUE

-- AI-generated reports
reports (id PK, run_id, symbol FK, date,
         report_text, recommendation, created_at)

-- Pipeline run history
pipeline_runs (id PK, started_at, completed_at, status,
               symbols_processed, errors JSON)
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1 user, localhost** (target) | SQLite, single-process pipeline, synchronous execution. This is the target. No scaling needed. |
| **1-5 users, cloud** | Switch SQLite → PostgreSQL (change connection string). Add basic auth. Deploy as single Docker container. APScheduler still works. |
| **5-50 users, cloud** | Add Redis for caching frequently-accessed rankings. Consider Celery for pipeline execution (non-blocking). Separate API server from pipeline worker. |
| **50+ users** | Out of scope for this project. Would need proper task queue, read replicas, and CDN for dashboard. |

### Scaling Priorities (when moving to cloud)

1. **First bottleneck: LLM inference speed.** Sentiment analysis of many articles is slow on RTX 3060. Mitigation: batch smartly, only analyze new articles, cache results. On cloud, use a larger GPU or cloud LLM API.
2. **Second bottleneck: Rate limiting from data sources.** vnstock wraps broker APIs that may throttle. Mitigation: respect rate limits, cache aggressively, fetch only changed data.

## Anti-Patterns

### Anti-Pattern 1: Real-Time Architecture for a Batch Problem

**What people do:** Build WebSocket-based real-time dashboards, event-driven architectures, streaming pipelines for a tool that fundamentally runs once per day after market close.

**Why it's wrong:** Massive over-engineering. HOSE trades 9:00-15:00 Mon-Fri. You need results once daily. Real-time adds complexity (state management, connection handling, backpressure) with zero value for this use case.

**Do this instead:** Simple batch pipeline triggered by scheduler. Dashboard reads from DB. Polling or manual refresh is perfectly fine. The data changes once per day.

### Anti-Pattern 2: Microservices for a Single-User Tool

**What people do:** Split crawlers, analyzers, scorers, and API into separate services with message queues between them.

**Why it's wrong:** Deployment complexity explodes (Docker Compose with 6+ services, message broker, service discovery). For a localhost single-user tool, this is absurd. A monolith that runs as one Python process is simpler, faster, and easier to debug.

**Do this instead:** Monolith with clean module boundaries. The module structure (`crawlers/`, `analysis/`, `scoring/`) provides the separation. If you ever need to split, the clean boundaries make it possible — but you won't need to.

### Anti-Pattern 3: Raw LLM Calls Without Structure

**What people do:** Send free-form prompts to the LLM and parse the text output with regex or hope-based string matching.

**Why it's wrong:** LLM text output is unpredictable. "Positive" vs "positive" vs "Tích cực" vs "The sentiment is generally positive" — parsing is fragile.

**Do this instead:** Use Ollama's `format` parameter with a JSON Schema (or Pydantic model schema). The LLM is constrained to output valid JSON matching your schema. Parse with `model_validate_json()`. Zero ambiguity.

### Anti-Pattern 4: Analyzing All 400 Stocks with LLM

**What people do:** Send every stock through the full LLM synthesis pipeline, generating detailed reports for all 400 symbols.

**Why it's wrong:** At ~30 seconds per LLM call on RTX 3060, analyzing all 400 stocks takes 3+ hours. Most of these stocks won't be interesting.

**Do this instead:** Use a funnel approach. Technical + Fundamental scoring (fast, no LLM) filters 400 stocks down to ~50 candidates. Sentiment analysis runs on news mentioning those ~50 stocks. Full LLM report generation only for the top 15-20 ranked stocks. Total LLM time: ~15-20 minutes instead of hours.

### Anti-Pattern 5: Storing Computed Indicators in the Database

**What people do:** Store every computed technical indicator (RSI values, MACD lines, all MAs) as separate columns in the database.

**Why it's wrong:** Creates a wide, rigid schema. Adding a new indicator means a migration. The raw data (prices) is the source of truth — indicators are derived and cheap to recompute.

**Do this instead:** Store raw price data. Compute indicators on-the-fly when needed using pandas-ta. Cache the final scores (not intermediate indicators) for the rankings. If you need historical indicator values for charting, store them as JSON blobs, not separate columns.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **vnstock (KBS/VCI API)** | Python library call → returns pandas DataFrame | Rate limited. Add 0.5-1s delay between symbol requests. KBS source is more stable than VCI based on community reports. Catch and retry on HTTP 429. |
| **CafeF** | HTTP scrape with httpx + bs4 | HTML structure changes periodically. Build resilient selectors. Cache articles by URL (dedup). Respect robots.txt. |
| **VnExpress Finance** | HTTP scrape with httpx + bs4 | Similar to CafeF. Use both for broader coverage. |
| **Ollama (localhost:11434)** | Python client library (`ollama` package) | Must be running before pipeline starts. Health check at pipeline start. Model must be pre-pulled. Use `format` param for structured output. |
| **Telegram Bot API** | `python-telegram-bot` library | Create bot via @BotFather. Store bot token in `.env`. Simple: send message to configured chat_id. |
| **SBV / GSO** (macro data) | HTTP scrape or manual CSV | State Bank of Vietnam and General Statistics Office. Data updates infrequently (monthly/quarterly). Semi-automated collection is fine. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Crawlers ↔ DB | SQLAlchemy ORM | Crawlers write raw data. They don't know about analysis. |
| Analysis ↔ DB | SQLAlchemy ORM read + write scores | Analyzers read raw data, write scores. They don't know about each other. |
| Scoring ↔ Analysis | In-memory (function calls) | Scorer reads from analysis results (either DB or passed directly). No network boundary. |
| AI ↔ Ollama | HTTP (localhost:11434) | Only boundary with network I/O besides web crawling. Wrap in retry logic. |
| API ↔ DB | SQLAlchemy ORM (read-mostly) | Dashboard API is read-heavy. The pipeline writes. No concurrency issue with SQLite WAL mode. |
| Pipeline ↔ All modules | Direct Python imports | Coordinator imports and calls modules. No IPC, no message queue. Simple. |

## Build Order (Dependencies)

The build order follows the data dependency chain. You can't analyze data you haven't crawled, and you can't score analysis you haven't computed.

```
Phase 1: Foundation
  └── DB schema + models (everything depends on storage)
  └── Configuration system (.env, scoring config)
  └── Project scaffolding (pyproject.toml, structure)

Phase 2: Data Ingestion
  └── Price crawler (vnstock) ← most critical data
  └── Stock listing (symbol registry)
  └── Basic CLI to trigger crawl manually

Phase 3: Technical Analysis
  └── Technical indicators (pandas-ta) ← depends on price data
  └── Technical scoring logic
  └── This phase has NO LLM dependency — pure computation

Phase 4: Fundamental Analysis
  └── Financial report crawler (vnstock Finance)
  └── Ratio calculations (P/E, EPS, ROE)
  └── Fundamental scoring logic
  └── Also NO LLM dependency

Phase 5: AI Integration
  └── Ollama client wrapper
  └── Sentiment analysis (news crawler + LLM classification)
  └── Prompt templates
  └── This is the first phase requiring Ollama running

Phase 6: Scoring & Synthesis
  └── Score aggregator (combines all dimensions)
  └── Ranking engine
  └── LLM report generation (top stocks only)
  └── Macro analysis (can be added here or deferred)

Phase 7: Presentation
  └── FastAPI REST API
  └── Web dashboard
  └── Telegram notifications

Phase 8: Automation
  └── APScheduler integration
  └── Pipeline coordinator (full daily run)
  └── Error handling & monitoring
```

**Build order rationale:**
- DB first because everything reads/writes to it.
- Price data first because technical analysis (Phase 3) needs it immediately — and technical analysis is the quickest win (no LLM needed).
- Fundamental analysis (Phase 4) is independent of technical — could be parallel, but sequencing gives early usable output.
- AI integration (Phase 5) is deferred because it's the most complex and least predictable component. By this point, you already have a useful tool (technical + fundamental scoring).
- Dashboard comes late because you need data to display. Building UI before the pipeline is running is wasted effort.
- Scheduler comes last because manual triggering works fine during development.

## Sources

- vnstock v3.5.1 — PyPI metadata + GitHub README (https://github.com/thinh-vu/vnstock) — **HIGH confidence**
- Ollama Python client v0.6.1 — PyPI + GitHub README (https://github.com/ollama/ollama-python) — **HIGH confidence**
- Ollama API structured output — Official API docs (https://github.com/ollama/ollama/blob/main/docs/api.md) — **HIGH confidence** — `format` parameter supports JSON Schema
- pandas-ta — PyPI description, 150+ indicators, numba-accelerated — **HIGH confidence**
- APScheduler v3.11.2 — PyPI — **HIGH confidence** — standard Python scheduling library
- FastAPI v0.135.3 — PyPI — **HIGH confidence** — standard async Python web framework
- python-telegram-bot v22.7 — PyPI — **HIGH confidence**
- SQLAlchemy v2.0.49 — PyPI — **HIGH confidence**
- Architecture patterns — training data synthesis of financial data pipeline best practices — **MEDIUM confidence** (general patterns, not Vietnamese-market-specific case studies)

---
*Architecture research for: Vietnamese Stock Analysis AI Agent (LocalStock)*
*Researched: 2025-07-18*
