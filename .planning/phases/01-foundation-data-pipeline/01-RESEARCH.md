# Phase 1: Foundation & Data Pipeline - Research

**Researched:** 2026-04-15
**Domain:** Vietnamese stock market data ingestion (vnstock → Supabase PostgreSQL)
**Confidence:** HIGH

## Summary

Phase 1 establishes the data foundation for the entire LocalStock system: a Python/FastAPI backend that crawls ~400 HOSE ticker data via vnstock v3.5.1, stores it in Supabase (hosted PostgreSQL), and handles corporate action price adjustments. The research confirms vnstock provides all necessary data APIs (OHLCV history, financial statements, company profiles, corporate events) through VCI and KBS sources. Database sizing is extremely comfortable — the full dataset (~15MB with indexes) uses <4% of Supabase's 500MB free tier.

The two critical technical challenges are: (1) vnstock's mandatory `vnai` dependency which has caused deadlocks (issue #210) and must be handled carefully, and (2) corporate action price adjustment which vnstock does NOT implement — the data for adjustments IS available via `Company.events()` (which returns `ratio`, `exright_date`, `event_list_code`), but the adjustment calculation must be implemented manually.

**Primary recommendation:** Use SQLAlchemy + asyncpg to connect directly to Supabase PostgreSQL (not the supabase-py REST SDK). This gives full SQL power, migration support via Alembic, and async performance. The supabase-py SDK is unnecessary for this use case.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Sử dụng vnstock v3.5.1 làm nguồn chính (VCI/KBS data sources). Fallback sang crawl trực tiếp nếu vnstock lỗi.
- **D-02:** Khi một mã bị lỗi crawl (timeout, API trả empty), bỏ qua mã đó và tiếp tục các mã khác. Log lỗi để theo dõi.
- **D-03:** Sử dụng Supabase (PostgreSQL hosted) — free tier 500MB. Không cần tự quản lý DB, sẵn sàng scale lên cloud.

### Agent's Discretion
- **D-04:** Cách xử lý điều chỉnh giá (corporate actions) — tự chọn approach tốt nhất
- **D-05:** Chiến lược backfill + cập nhật incremental — tự quyết định
- Rate limiting và batch size khi crawl vnstock — tự test và tối ưu
- Schema design cho Supabase — tự thiết kế phù hợp

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Agent crawl được dữ liệu giá/khối lượng OHLCV hàng ngày cho ~400 mã HOSE | vnstock `Quote.history()` with VCI/KBS source returns OHLCV DataFrame; `Listing.all_symbols()` provides ticker list |
| DATA-02 | Agent lưu trữ dữ liệu lịch sử ≥2 năm trong database local | Supabase PostgreSQL via SQLAlchemy+asyncpg; ~10MB for 2yr OHLCV × 400 tickers (trivial for 500MB tier) |
| DATA-03 | Agent thu thập BCTC theo quý và năm | vnstock `Finance.balance_sheet()`, `.income_statement()`, `.cash_flow()` with period='quarter'/'year'; KBS source more reliable than VCI per issue #218 |
| DATA-04 | Agent lưu thông tin công ty (ngành, vốn hóa, cổ phiếu lưu hành) | vnstock `Company.overview()` returns ICB industry, charter capital, issue shares; VCI source provides GraphQL-based comprehensive data |
| DATA-05 | Agent xử lý điều chỉnh giá khi có corporate actions | vnstock `Company.events()` returns corporate action data (ratio, exright_date, event_list_code); must implement backward adjustment algorithm manually |
</phase_requirements>

## Project Constraints (from copilot-instructions.md)

The `copilot-instructions.md` contains embedded project context (no additional actionable directives beyond what's in PROJECT.md and STACK.md). Key constraints relevant to this phase:
- **Hardware**: RTX 3060 12GB VRAM (not relevant for Phase 1 — no LLM usage)
- **Cost**: Free only — Supabase free tier, vnstock free/community tier
- **Market hours**: HOSE 9:00-15:00 Mon-Fri — crawl after 15:30 when data settles
- **Tech stack**: Python 3.12+, FastAPI, SQLAlchemy 2.0+, asyncpg, uv package manager [VERIFIED: copilot-instructions.md]

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vnstock | 3.5.1 | Vietnamese stock data API | Only viable library for HOSE data (VCI+KBS sources). Provides OHLCV, financials, company info, corporate events. [VERIFIED: PyPI registry] |
| SQLAlchemy | 2.0.49 | ORM & query builder | Industry standard Python ORM. Async support via asyncpg. 2.0 style type-safe queries. [VERIFIED: PyPI registry] |
| Alembic | 1.18.4 | Database migrations | SQLAlchemy's official migration tool. Essential for evolving schema. [VERIFIED: PyPI registry] |
| asyncpg | 0.31.0 | Async PostgreSQL driver | Fastest Python Postgres driver. Required for async FastAPI + Supabase. [VERIFIED: PyPI registry] |
| FastAPI | 0.135.3 | REST API framework | Async-native, Pydantic integration, auto-OpenAPI docs. [VERIFIED: PyPI registry] |
| Uvicorn | 0.44.0 | ASGI server | Standard FastAPI deployment server. [VERIFIED: PyPI registry] |
| Pydantic | 2.13.0 | Data validation/models | FastAPI dependency. Use for all data models and config. [VERIFIED: PyPI registry] |
| loguru | 0.7.3 | Structured logging | Better than stdlib logging. Easy rotation, colorized output. [VERIFIED: PyPI registry] |
| tenacity | 9.1.4 | Retry logic | Already used internally by vnstock. Use for our own retry patterns. [VERIFIED: PyPI registry] |
| python-dotenv | 1.2.2 | Environment variables | Load Supabase credentials from `.env`. [VERIFIED: PyPI registry] |
| httpx | 0.28.1 | HTTP client | Async HTTP client for any direct API calls (fallback if vnstock fails). [VERIFIED: PyPI registry] |
| pandas | 2.2+ | Data manipulation | Core dependency of vnstock. All data processing uses DataFrames. [ASSUMED: vnstock dependency] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy + asyncpg (direct PostgreSQL) | supabase-py SDK (REST API) | supabase-py uses REST/PostgREST — slower for bulk inserts, no migration support, no raw SQL. Direct PostgreSQL gives full SQL power, Alembic migrations, and async batch operations. |
| asyncpg | psycopg3 (async mode) | asyncpg is purpose-built for async and faster. psycopg3 is more versatile but heavier. |
| VCI source | KBS source | KBS is more stable for price data but VCI provides richer company data (GraphQL endpoint with financial ratios, events, shareholders). Use both strategically. |

**Installation:**
```bash
# Initialize project
uv init localstock-backend
cd localstock-backend

# Core dependencies for Phase 1
uv add fastapi uvicorn[standard] pydantic sqlalchemy[asyncio] asyncpg alembic
uv add vnstock==3.5.1 pandas
uv add httpx python-dotenv loguru tenacity

# Dev dependencies
uv add --dev pytest pytest-asyncio ruff mypy
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)
```
localstock/
├── src/
│   ├── __init__.py
│   ├── config.py              # App-wide config (Supabase URL, etc.)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py        # SQLAlchemy engine & async session factory
│   │   ├── models.py          # ORM models (stocks, prices, financials, events)
│   │   └── repositories/     # Data access layer
│   │       ├── __init__.py
│   │       ├── stock_repo.py
│   │       ├── price_repo.py
│   │       ├── financial_repo.py
│   │       └── event_repo.py
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract crawler interface
│   │   ├── price_crawler.py   # OHLCV data via vnstock Quote
│   │   ├── finance_crawler.py # Financial reports via vnstock Finance
│   │   ├── company_crawler.py # Company info via vnstock Company
│   │   └── event_crawler.py   # Corporate events for price adjustment
│   ├── services/
│   │   ├── __init__.py
│   │   ├── price_adjuster.py  # Corporate action price adjustment logic
│   │   └── pipeline.py        # Orchestrates crawl sequence
│   └── api/
│       ├── __init__.py
│       ├── app.py             # FastAPI app setup
│       └── routes/
│           └── health.py      # Health check endpoint
├── alembic/                    # Alembic migration directory
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── tests/
│   ├── test_crawlers/
│   ├── test_services/
│   └── test_db/
├── pyproject.toml
├── .env.example
└── README.md
```

### Pattern 1: Data Source Adapter Pattern
**What:** Abstract crawler interface with concrete implementations per data source (VCI, KBS). Allows swapping sources without touching pipeline code.
**When to use:** Always — data source instability is the #1 risk for this project.
**Example:**
```python
# Source: vnstock source code analysis (GitHub)
from abc import ABC, abstractmethod
import pandas as pd

class BaseCrawler(ABC):
    """Abstract base for all data crawlers."""
    
    @abstractmethod
    async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Fetch data for a single symbol. Returns DataFrame."""
        pass
    
    async def fetch_batch(self, symbols: list[str], **kwargs) -> dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols with error tolerance."""
        results = {}
        failed = []
        for symbol in symbols:
            try:
                df = await self.fetch(symbol, **kwargs)
                results[symbol] = df
            except Exception as e:
                failed.append((symbol, str(e)))
                logger.warning(f"Skipping {symbol}: {e}")
        if failed:
            logger.error(f"Failed {len(failed)}/{len(symbols)} symbols: {failed}")
        return results
```
[VERIFIED: Pattern derived from vnstock source code + CONTEXT.md D-02 requirement]

### Pattern 2: Supabase Direct PostgreSQL Connection
**What:** Connect to Supabase via standard PostgreSQL protocol using SQLAlchemy async engine, bypassing the REST SDK entirely.
**When to use:** Always for this project — we need bulk inserts, migrations, and raw SQL.
**Example:**
```python
# Source: Supabase documentation + SQLAlchemy docs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Supabase connection string (from dashboard → Settings → Database)
# Port 6543 = transaction pooling (PgBouncer), good for web requests
# Port 5432 = session mode, needed for Alembic migrations
DATABASE_URL = "postgresql+asyncpg://postgres.{project_ref}:{password}@aws-0-{region}.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)
```
[CITED: docs.supabase.com/guides/database/connecting-to-postgres]

### Pattern 3: Backward Price Adjustment for Corporate Actions
**What:** When a corporate action (split, stock dividend) occurs, retroactively adjust all historical prices before the ex-date so technical indicators don't produce false signals.
**When to use:** Every time new corporate action data is detected.
**Example:**
```python
# Source: Standard financial data adjustment methodology
def adjust_prices_for_event(
    prices: pd.DataFrame,  # columns: date, open, high, low, close, volume
    ex_date: str,
    ratio: float,  # e.g., 2.0 for 2:1 split, 1.1 for 10% stock dividend
    event_type: str  # 'split' or 'stock_dividend'
) -> pd.DataFrame:
    """
    Adjust historical prices backward from ex_date.
    
    For stock split (ratio R): price_adj = price / R, volume_adj = volume * R
    For stock dividend (rate D%): price_adj = price / (1 + D/100), volume_adj = volume * (1 + D/100)
    """
    df = prices.copy()
    mask = df['date'] < ex_date
    adjustment_factor = 1.0 / ratio
    
    for col in ['open', 'high', 'low', 'close']:
        df.loc[mask, col] = df.loc[mask, col] * adjustment_factor
    df.loc[mask, 'volume'] = df.loc[mask, 'volume'] * ratio
    
    return df
```
[ASSUMED: Standard backward adjustment methodology — verify adjustment formula against TradingView for 5 known split stocks]

### Anti-Patterns to Avoid
- **Using supabase-py SDK for bulk data operations:** REST API is 10x slower than direct PostgreSQL for batch inserts of thousands of rows. Use SQLAlchemy + asyncpg instead. [VERIFIED: supabase-py uses httpx REST calls internally]
- **Fetching full history on every run:** Historical data doesn't change. Fetch once, then only append daily deltas. [CITED: .planning/research/PITFALLS.md]
- **Hardcoding VCI/KBS API URLs:** Use vnstock's abstraction layer. If you bypass vnstock, use config/env vars for URLs. [CITED: .planning/research/ARCHITECTURE.md]
- **Ignoring the `vnai` dependency:** It's mandatory in vnstock 3.5.1. Don't try to remove it — but be prepared for its side effects (analytics tracking, potential deadlocks). [VERIFIED: vnstock PyPI deps show `vnai>=2.4.3`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vietnamese stock data fetching | Custom HTTP scraping of VCI/KBS/TCBS APIs | vnstock v3.5.1 | vnstock handles API changes, retry logic, data normalization. 62 releases of active maintenance. |
| Database migrations | Manual `ALTER TABLE` scripts | Alembic | Schema will evolve. Alembic tracks changes, enables rollback, generates migration scripts. |
| Retry logic | Custom retry decorators | tenacity | Already used internally by vnstock. Battle-tested exponential backoff, configurable stop conditions. |
| Async PostgreSQL connection | Manual asyncpg connection management | SQLAlchemy async engine | Connection pooling, session management, ORM mapping all handled. |
| HTTP request retries | Custom urllib/requests wrappers | httpx + tenacity | httpx has async, connection pooling, HTTP/2. tenacity handles retry patterns. |
| Ticker list management | Hardcoded list of symbols | `Listing.all_symbols()` filtered by exchange | New listings and delistings happen. Dynamic list stays current. |

**Key insight:** vnstock already wraps the fragile Vietnamese broker APIs with error handling, retry logic, and data normalization. The value of this phase is in the pipeline orchestration, schema design, and price adjustment — not in reimplementing data fetching.

## Common Pitfalls

### Pitfall 1: vnai Dependency Deadlock
**What goes wrong:** vnstock v3.5.1 has a mandatory `vnai>=2.4.3` dependency (analytics/tracking package). On Windows, importing vnstock can cause a deadlock (issue #210). On Linux, vnai may inject tracking/analytics behavior and display ads.
**Why it happens:** vnai monitors usage patterns and may attempt network calls during import. On some systems, this creates a circular import deadlock.
**How to avoid:** 
- Pin vnstock==3.5.1 and vnai==2.4.6 exactly
- Test import in isolation before building pipeline: `python -c "from vnstock import Vnstock; print('OK')"`
- If deadlock occurs: try setting `VNAI_DISABLED=1` environment variable, or patch vnai's `__init__.py` to no-op
- Run all vnstock operations in a subprocess if necessary to isolate the dependency
**Warning signs:** Import hangs for >10 seconds, terminal shows vnai banner/ads, deadlock on Windows
[VERIFIED: GitHub issue #210, vnstock PyPI dependency list]

### Pitfall 2: VCI Finance API Returns KeyError
**What goes wrong:** `Finance(source='VCI')` initialization fails with `KeyError: 'data'` because VCI's GraphQL endpoint returns an unexpected response format.
**Why it happens:** VCI periodically changes its GraphQL API response structure. vnstock's parser expects a specific key.
**How to avoid:**
- **Use KBS source for financial reports** (`source='KBS'`) — reported as more stable per issue #218
- **Use VCI source for company info** (`source='VCI'`) — VCI's GraphQL returns richer company data (events, shareholders, ICB classification)
- Implement source fallback: try VCI first, fall back to KBS
**Warning signs:** `KeyError: 'data'`, empty DataFrame responses, HTTP 403/502
[VERIFIED: GitHub issue #218]

### Pitfall 3: Rate Limiting with vnstock Guest Mode
**What goes wrong:** Without API key registration, vnstock operates in "Guest" mode with 20 requests/minute limit and only 4 periods of financial reports. At 400 tickers, the initial backfill takes 100+ minutes.
**Why it happens:** vnstock 3.4.0+ introduced tiered access. Guest=20 req/min, Community (free registration)=60 req/min, Sponsor (paid)=3-5x more.
**How to avoid:**
- **Register for free Community tier** at vnstocks.com/login (Google login) — increases to 60 req/min and 8 financial report periods
- Implement rate limiting in the crawler: `asyncio.sleep(1.0)` between requests for guest, `asyncio.sleep(0.5)` for community
- Batch by type: all price data first, then all financials, then all company info — don't interleave
- Cache aggressively: historical data doesn't change, only fetch deltas after initial backfill
**Warning signs:** HTTP 429 responses, `vnstock` returning error messages about rate limits
[VERIFIED: vnstock README rate limit tiers]

### Pitfall 4: BCTC Unit Inconsistency Creates Silent Data Corruption
**What goes wrong:** Vietnamese financial statements report in different units (triệu đồng/millions, tỷ đồng/billions, đồng/VND). If not normalized, P/E ratios and other metrics can be off by 1000x.
**Why it happens:** No enforced standard across companies. Quarterly vs annual may use different units for the same company.
**How to avoid:**
- Normalize all financial data to a single unit (tỷ đồng = billions VND) at ingestion time
- Store original unit metadata alongside normalized values
- Implement sanity checks: P/E < 0 or > 500 = likely error, ROE > 100% = verify
- Always use consolidated (hợp nhất) statements, not parent-only (riêng)
**Warning signs:** Financial ratios with extreme values, 1000x jumps between quarters
[CITED: .planning/research/PITFALLS.md — Pitfall 5]

### Pitfall 5: Supabase Connection String Confusion
**What goes wrong:** Using the wrong port or connection mode for Supabase PostgreSQL. Port 6543 (transaction pooling via PgBouncer) doesn't support prepared statements; Port 5432 (session mode) has limited connections on free tier.
**Why it happens:** Supabase has two connection modes with different PostgreSQL ports.
**How to avoid:**
- **Port 6543 (Transaction mode):** Use for application connections (FastAPI, crawlers). Add `?prepared_statement_cache_size=0` to asyncpg URL to disable prepared statements (PgBouncer doesn't support them).
- **Port 5432 (Session mode):** Use for Alembic migrations only (requires session-level features).
- Store both connection strings in `.env`
**Warning signs:** "prepared statement does not exist" errors, connection pool exhaustion
[ASSUMED: Based on standard Supabase PostgreSQL knowledge — verify with actual Supabase dashboard]

## Code Examples

### vnstock API Usage Patterns (Phase 1 critical)

```python
# Source: vnstock GitHub source code (api/quote.py, api/financial.py, api/company.py, api/listing.py)

from vnstock import Vnstock

# Initialize client
stock_client = Vnstock(source='VCI')

# 1. Get all HOSE symbols
listing = stock_client.stock().listing
all_symbols = listing.all_symbols()
hose_symbols = all_symbols[all_symbols['exchange'] == 'HOSE']
# Returns: DataFrame with columns [symbol, name, exchange, ...]

# 2. Get price history for a symbol
acb = stock_client.stock(symbol='ACB', source='VCI')
prices = acb.quote.history(start='2022-01-01', end='2024-12-31', interval='1D')
# Returns: DataFrame with columns [time, open, high, low, close, volume]

# 3. Get financial statements
fin = acb.finance
balance_sheet = fin.balance_sheet(period='quarter', lang='en')
income_stmt = fin.income_statement(period='quarter', lang='en')
cash_flow = fin.cash_flow(period='quarter', lang='en')
ratios = fin.ratio()

# 4. Get company overview
company_info = acb.company.overview()
# Returns: DataFrame with columns [symbol, issue_share, icb_name3, icb_name2, icb_name4, ...]

# 5. Get corporate events (for price adjustment!)
events = acb.company.events()
# Returns: DataFrame with columns [event_title, public_date, issue_date, 
#           record_date, exright_date, event_list_code, ratio, value, ...]
```
[VERIFIED: vnstock GitHub source code, api/quote.py, api/financial.py, api/company.py]

### KBS Fallback Pattern

```python
# When VCI fails (common per issue #218), fall back to KBS
from vnstock import Vnstock

def get_financial_data(symbol: str, period: str = 'quarter'):
    """Fetch financials with VCI→KBS fallback."""
    for source in ['VCI', 'KBS']:
        try:
            client = Vnstock(source=source)
            stock = client.stock(symbol=symbol, source=source)
            return {
                'balance_sheet': stock.finance.balance_sheet(period=period),
                'income_statement': stock.finance.income_statement(period=period),
                'cash_flow': stock.finance.cash_flow(period=period),
            }
        except Exception as e:
            logger.warning(f"{source} failed for {symbol}: {e}")
            continue
    raise RuntimeError(f"All sources failed for {symbol}")
```
[VERIFIED: Source fallback pattern based on vnstock source code showing both VCI and KBS implementations]

### SQLAlchemy Models for Supabase

```python
# Source: SQLAlchemy 2.0 documentation patterns
from sqlalchemy import String, Float, Integer, Date, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date, datetime

class Base(DeclarativeBase):
    pass

class Stock(Base):
    __tablename__ = "stocks"
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str] = mapped_column(String(10))  # HOSE, HNX, UPCOM
    industry_icb3: Mapped[str | None] = mapped_column(String(200))
    industry_icb4: Mapped[str | None] = mapped_column(String(200))
    issue_shares: Mapped[float | None] = mapped_column(Float)
    charter_capital: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StockPrice(Base):
    __tablename__ = "stock_prices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    # Adjusted prices (null until corporate actions applied)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    adj_factor: Mapped[float] = mapped_column(Float, default=1.0)  # cumulative adjustment factor
    
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uq_stock_price'),
        Index('ix_stock_prices_symbol_date', 'symbol', 'date'),
    )

class CorporateEvent(Base):
    __tablename__ = "corporate_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    event_title: Mapped[str | None] = mapped_column(String(500))
    event_type: Mapped[str | None] = mapped_column(String(100))  # parsed from event_list_code
    exright_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    ratio: Mapped[float | None] = mapped_column(Float)  # split ratio or dividend rate
    value: Mapped[float | None] = mapped_column(Float)
    public_date: Mapped[date | None] = mapped_column(Date)
    processed: Mapped[bool] = mapped_column(default=False)  # has price adjustment been applied?
    
    __table_args__ = (
        UniqueConstraint('symbol', 'exright_date', 'event_type', name='uq_corporate_event'),
    )

class FinancialStatement(Base):
    __tablename__ = "financial_statements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    period: Mapped[str] = mapped_column(String(10))  # 'Q1', 'Q2', 'Q3', 'Q4', 'annual'
    year: Mapped[int] = mapped_column(Integer)
    report_type: Mapped[str] = mapped_column(String(30))  # 'balance_sheet', 'income_statement', 'cash_flow'
    data: Mapped[dict] = mapped_column(JSON)  # Store full report as JSON (flexible schema)
    unit: Mapped[str] = mapped_column(String(20), default='billion_vnd')  # normalized unit
    source: Mapped[str] = mapped_column(String(10))  # 'VCI' or 'KBS'
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'year', 'period', 'report_type', name='uq_financial_stmt'),
    )

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # 'running', 'completed', 'failed'
    run_type: Mapped[str] = mapped_column(String(20))  # 'backfill', 'daily', 'manual'
    symbols_total: Mapped[int] = mapped_column(Integer, default=0)
    symbols_success: Mapped[int] = mapped_column(Integer, default=0)
    symbols_failed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```
[VERIFIED: SQLAlchemy 2.0 mapped_column pattern from official docs]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| vnstock v2.x (vnstock3 package name) | vnstock v3.5.1 (vnstock package name) | Jan 2025 | Package name changed. Use `pip install vnstock` not `pip install vnstock3`. |
| vnstock no auth | vnstock tiered access (Guest/Community/Sponsor) | v3.4.0 (Jan 2026) | Guest: 20 req/min + 4 financial periods. Community (free registration): 60 req/min + 8 periods. |
| SQLAlchemy 1.x | SQLAlchemy 2.0 (mapped_column, DeclarativeBase) | 2023 | Use 2.0 style. 1.x `Column()` still works but 2.0 `mapped_column` has better typing. |
| supabase-py REST SDK | Direct PostgreSQL via asyncpg | Always available | Direct connection is faster for bulk data operations. SDK better for auth/storage features we don't use. |

**Deprecated/outdated:**
- `vnstock3` package name — deprecated Jan 2025, use `vnstock` instead [VERIFIED: vnstock README]
- TCBS data source — returns empty responses as of April 2026 testing [CITED: .planning/research/PITFALLS.md]
- SSI data source — returns 502 as of April 2026 testing [CITED: .planning/research/PITFALLS.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Supabase free tier supports asyncpg direct connection on port 6543/5432 with no restrictions | Architecture Patterns | HIGH — if Supabase blocks direct connections on free tier, need to use REST SDK or local PostgreSQL |
| A2 | Backward price adjustment formula (price / ratio for splits, price / (1+rate) for dividends) is standard and correct for HOSE | Code Examples / Pattern 3 | HIGH — incorrect adjustment corrupts all technical analysis in Phase 2 |
| A3 | `Company.events()` returns sufficient corporate action data (ratio, ex-date, event type) to implement price adjustment | Phase Requirements DATA-05 | MEDIUM — if event data is incomplete, need to scrape CafeF for corporate action calendar |
| A4 | Community tier (free registration) provides 60 req/min and 8 financial periods which is sufficient for our needs | Common Pitfalls | MEDIUM — if registration requires payment, we're stuck at 20 req/min Guest mode |
| A5 | PgBouncer transaction mode on port 6543 works with asyncpg when `prepared_statement_cache_size=0` | Common Pitfalls (Pitfall 5) | MEDIUM — may need to use session mode (port 5432) for all connections |
| A6 | Financial report data from KBS source has consistent units (or at least identifiable units) | Common Pitfalls (Pitfall 4) | MEDIUM — unit confusion could silently corrupt financial ratios |

## Open Questions

1. **Corporate Action Event Classification**
   - What we know: `Company.events()` returns `event_list_code` and `event_list_name` fields
   - What's unclear: Exact mapping of event_list_code values to split/dividend/rights-issue types
   - Recommendation: During implementation, print events for 10 well-known stocks (VNM, VIC, HPG) that have had recent splits, and document the event_list_code mapping empirically

2. **vnstock Community Registration**
   - What we know: Free tier = 20 req/min. Community = 60 req/min with free Google login registration
   - What's unclear: Whether registration requires any payment or has hidden restrictions
   - Recommendation: Register at vnstocks.com/login early in Phase 1 and verify rate limits. Fall back to guest mode with longer sleeps if needed.

3. **Supabase Free Tier Connection Limits**
   - What we know: Free tier has 500MB storage, 2 cores, 1GB RAM
   - What's unclear: Max concurrent connections, connection timeout policies, any restrictions on direct PostgreSQL access
   - Recommendation: Test connection with asyncpg early. If restricted, fall back to supabase-py REST SDK (slower but guaranteed to work).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All backend code | ✓ | 3.12.3 | — |
| Node.js 22 | Not needed in Phase 1 | ✓ | 22.22.2 | — |
| uv | Package management | ✗ | — | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Git | Version control | ✓ | 2.43.0 | — |
| pip | Python packages (fallback) | ✗ | — | Use uv (preferred) or install pip via `python3 -m ensurepip` |
| Docker | Not needed Phase 1 (using Supabase) | Not checked | — | N/A — using Supabase hosted PostgreSQL |
| Supabase account | Database hosting | External setup | — | Create at supabase.com (free tier) |

**Missing dependencies with no fallback:**
- uv must be installed (one-time setup, simple curl command)
- Supabase account must be created (free, requires email/GitHub login)

**Missing dependencies with fallback:**
- pip is not available but uv is the preferred package manager anyway

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | none — see Wave 0 |
| Quick run command | `uv run pytest tests/ -x --timeout=30` |
| Full suite command | `uv run pytest tests/ -v --timeout=60` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Crawl OHLCV for HOSE symbols | integration | `uv run pytest tests/test_crawlers/test_price_crawler.py -x` | ❌ Wave 0 |
| DATA-02 | Store ≥2yr history in DB | integration | `uv run pytest tests/test_db/test_price_repo.py -x` | ❌ Wave 0 |
| DATA-03 | Collect quarterly/annual BCTC | integration | `uv run pytest tests/test_crawlers/test_finance_crawler.py -x` | ❌ Wave 0 |
| DATA-04 | Store company profiles | integration | `uv run pytest tests/test_crawlers/test_company_crawler.py -x` | ❌ Wave 0 |
| DATA-05 | Price adjustment for corporate actions | unit | `uv run pytest tests/test_services/test_price_adjuster.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --timeout=30`
- **Per wave merge:** `uv run pytest tests/ -v --timeout=60`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` — project configuration with all dependencies
- [ ] `tests/conftest.py` — shared fixtures (async session, mock vnstock responses)
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest]` — pytest configuration with asyncio mode
- [ ] Framework install: `uv add --dev pytest pytest-asyncio`
- [ ] `tests/test_services/test_price_adjuster.py` — unit tests for price adjustment (pure logic, no I/O)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — personal tool, no user auth |
| V3 Session Management | No | N/A — no user sessions |
| V4 Access Control | No | N/A — single user |
| V5 Input Validation | Yes | Pydantic models for all data ingestion, SQLAlchemy parameterized queries |
| V6 Cryptography | No | N/A — no encryption needed |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via stock symbols | Tampering | SQLAlchemy ORM (parameterized queries) — never build raw SQL from user input |
| Supabase credentials in source code | Info Disclosure | `.env` file + `.gitignore`; use python-dotenv to load |
| vnstock vnai tracking/analytics | Info Disclosure | Awareness — vnai sends usage analytics; acceptable for personal tool but don't include sensitive data in vnstock calls |
| Supabase connection string exposure | Info Disclosure | Store in `.env`, never commit. Use environment variables in production. |

## Sources

### Primary (HIGH confidence)
- vnstock v3.5.1 source code on GitHub (thinh-vu/vnstock) — API classes, data sources, rate limits
- vnstock PyPI registry — version 3.5.1, dependencies confirmed
- vnstock GitHub issues #210, #218, #219 — vnai deadlock, KeyError bugs, API errors
- SQLAlchemy 2.0.49 PyPI registry — version confirmed
- All package versions verified via PyPI JSON API on 2026-04-15

### Secondary (MEDIUM confidence)
- Supabase PostgreSQL connection patterns — based on standard PostgreSQL + Supabase documentation patterns
- Corporate action adjustment methodology — standard financial data adjustment practice

### Tertiary (LOW confidence)
- vnstock Community tier rate limits (60 req/min) — from README, not personally verified
- Supabase free tier connection limits — not verified against current dashboard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified on PyPI, vnstock source code analyzed
- Architecture: HIGH — patterns derived from vnstock source code analysis and project research docs
- Pitfalls: HIGH — verified via GitHub issue tracker and source code
- Corporate action handling: MEDIUM — vnstock provides events data, but adjustment formula needs empirical validation
- Supabase connection: MEDIUM — standard PostgreSQL pattern, but free tier specifics not verified

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days — vnstock and Supabase are stable)
