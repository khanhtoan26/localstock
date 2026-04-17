# Kiến trúc & Workflow — LocalStock

Tài liệu này giải thích toàn bộ codebase hoạt động như thế nào: từ khởi động ứng dụng, qua pipeline xử lý dữ liệu, đến giao diện web dashboard.

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Khởi động ứng dụng](#2-khởi-động-ứng-dụng)
3. [Pipeline xử lý dữ liệu](#3-pipeline-xử-lý-dữ-liệu)
4. [Data Crawling](#4-data-crawling)
5. [Phân tích kỹ thuật & cơ bản](#5-phân-tích-kỹ-thuật--cơ-bản)
6. [AI & LLM (Ollama)](#6-ai--llm-ollama)
7. [Scoring Engine](#7-scoring-engine)
8. [Thông báo Telegram](#8-thông-báo-telegram)
9. [Scheduler tự động](#9-scheduler-tự-động)
10. [Database Layer](#10-database-layer)
11. [Frontend (Next.js)](#11-frontend-nextjs)
12. [Cấu hình hệ thống](#12-cấu-hình-hệ-thống)
13. [Design Patterns](#13-design-patterns)

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCALSTOCK ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐              │
│  │ Scheduler │───▶│  Pipeline  │───▶│ Telegram │              │
│  │ (15:45)  │    │ Orchestrator│   │   Bot    │              │
│  └──────────┘    └─────┬─────┘    └──────────┘              │
│                        │                                     │
│         ┌──────────────┼──────────────┐                     │
│         ▼              ▼              ▼                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │  Crawlers   │ │  Analysis   │ │  AI/LLM    │              │
│  │ (vnstock)  │ │  (pandas-ta)│ │  (Ollama)  │              │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘              │
│         │              │              │                     │
│         ▼              ▼              ▼                     │
│  ┌──────────────────────────────────────────┐               │
│  │          PostgreSQL (Supabase)            │               │
│  │  18 tables — stocks, prices, indicators,  │               │
│  │  scores, reports, notifications, etc.     │               │
│  └────────────────────┬─────────────────────┘               │
│                       │                                     │
│         ┌─────────────┼─────────────┐                      │
│         ▼                           ▼                      │
│  ┌────────────┐              ┌────────────┐                │
│  │  FastAPI    │◀─── REST ──▶│  Next.js    │                │
│  │  Backend   │    (JSON)    │  Dashboard  │                │
│  │  :8000     │              │  :3000      │                │
│  └────────────┘              └────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Luồng dữ liệu chính:**
```
Crawl (vnstock) → Store (PostgreSQL) → Analyze (pandas-ta)
→ Score (weighted composite) → Report (Ollama LLM) → Notify (Telegram)
→ Display (Next.js Dashboard)
```

---

## 2. Khởi động ứng dụng

### Khi chạy `uv run uvicorn localstock.api.app:app`

```python
# apps/prometheus/src/localstock/api/app.py

def create_app() -> FastAPI:
    app = FastAPI(title="LocalStock API", lifespan=get_lifespan)

    # 1. CORS middleware — chỉ cho phép frontend localhost:3000
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])

    # 2. Đăng ký 9 routers (30+ endpoints)
    app.include_router(health_router)       # GET /health
    app.include_router(analysis_router)     # /api/analysis/*
    app.include_router(news_router)         # /api/news/*
    app.include_router(scores_router)       # /api/scores/*
    app.include_router(reports_router)      # /api/reports/*
    app.include_router(macro_router)        # /api/macro/*
    app.include_router(automation_router)   # /api/automation/*
    app.include_router(prices_router)       # /api/prices/*
    app.include_router(dashboard_router)    # /api/sectors/*

    return app
```

### Lifespan: APScheduler khởi tạo cùng app

```python
@asynccontextmanager
async def get_lifespan(app: FastAPI):
    # Startup: Khởi tạo scheduler
    setup_scheduler()        # Tạo daily job (15:45 VN time)
    scheduler.start()        # Bắt đầu lắng nghe
    yield
    # Shutdown: Tắt scheduler
    scheduler.shutdown()
```

**Thứ tự khởi động:**
1. uvicorn load module `localstock.api.app`
2. `create_app()` tạo FastAPI instance
3. CORS middleware được thêm
4. 9 routers đăng ký endpoints
5. Lifespan bắt đầu → APScheduler start
6. Server sẵn sàng nhận request tại `:8000`

---

## 3. Pipeline xử lý dữ liệu

### Khi gọi `POST /api/automation/run`

Đây là **full pipeline** — toàn bộ quy trình xử lý chạy tuần tự:

```
Step 1: Crawl giá OHLCV (~400 mã)
   ↓
Step 2: Crawl tin tức (RSS feeds)
   ↓
Step 3: Phân tích kỹ thuật + cơ bản
   ↓
Step 4: LLM phân loại sentiment tin tức
   ↓
Step 5: Chấm điểm tổng hợp (scoring)
   ↓
Step 6: LLM tạo báo cáo AI (top 20 mã)
   ↓
Step 7: Phát hiện biến động điểm
   ↓
Step 8: Cập nhật sector rotation
   ↓
Step 9: Gửi thông báo Telegram
```

### Chi tiết code:

```python
# apps/prometheus/src/localstock/services/automation_service.py

class AutomationService:
    async def run_daily_pipeline(self, force=False):

        # Kiểm tra ngày giao dịch (bỏ qua Sat/Sun + lễ VN)
        if not force and not is_trading_day():
            return {"status": "skipped", "reason": "non_trading_day"}

        # Lock — chỉ 1 pipeline chạy cùng lúc
        if _pipeline_lock.locked():
            return {"status": "skipped", "reason": "already_running"}

        async with _pipeline_lock:
            # Mỗi step dùng riêng 1 DB session (tránh leak)

            # Step 1: Crawl market data
            async with session_factory() as session:
                pipeline = Pipeline(session)
                await pipeline.run_full(run_type="daily")

            # Step 2: Technical + Fundamental Analysis
            async with session_factory() as session:
                await AnalysisService(session).run_full()

            # Step 3: News Crawl
            async with session_factory() as session:
                await NewsService(session).crawl_all()

            # Step 4: Sentiment Analysis (LLM)
            async with session_factory() as session:
                await SentimentService(session).run_full()

            # Step 5: Composite Scoring
            async with session_factory() as session:
                await ScoringService(session).run_full()

            # Step 6: Report Generation (LLM)
            async with session_factory() as session:
                await ReportService(session).run_full(top_n=20)

            # Step 7-8: Score changes + Sector rotation
            async with session_factory() as session:
                changes = await detect_score_changes(session)
                await SectorService(session).compute_snapshot()

            # Step 9: Telegram notifications
            await self._send_notifications(summary)
```

### Locking cơ chế

```python
_pipeline_lock = asyncio.Lock()  # Module-level

# Nếu pipeline đang chạy, API trả về 409 Conflict
# Không cho phép chạy song song — tránh duplicate data
```

---

## 4. Data Crawling

### Pipeline Orchestrator (Step 1 chi tiết)

```python
# apps/prometheus/src/localstock/services/pipeline.py

class Pipeline:
    async def run_full(self, run_type="daily"):

        # 1. Lấy danh sách mã HOSE
        symbols = await self.stock_repo.get_all_hose_symbols()  # ~400 mã

        # 2. Crawl giá (incremental — chỉ lấy ngày mới)
        for symbol in symbols:
            latest = await self.price_repo.get_latest_date(symbol)
            if latest and latest >= date.today():
                continue  # Đã có dữ liệu hôm nay, bỏ qua

            start = latest + timedelta(days=1) if latest else date.today() - timedelta(days=730)
            df = await self.price_crawler.fetch(symbol, start_date=start)
            await self.price_repo.upsert_prices(symbol, df)

        # 3. Crawl BCTC (quý)
        for symbol in symbols:
            fin_data = await self.finance_crawler.fetch(symbol)
            await self._store_financials(symbol, fin_data)

        # 4. Crawl corporate events (splits, dividends)
        # 5. Apply price adjustments (backward adjustment)
```

### vnstock Integration: Sync → Async Bridge

vnstock là thư viện **synchronous** → phải dùng `run_in_executor` để không block event loop:

```python
# apps/prometheus/src/localstock/crawlers/price_crawler.py

class PriceCrawler(BaseCrawler):
    async def fetch(self, symbol, **kwargs):
        def _fetch_sync():
            client = Vnstock(source="VCI")
            stock = client.stock(symbol=symbol, source="VCI")
            return stock.quote.history(start=start, end=end, interval="1D")

        # Chạy trong thread pool → không block async pipeline
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _fetch_sync)
        return df
```

### Source Fallback (Finance)

```python
# Thử KBS trước (ổn định hơn), fallback sang VCI
SOURCES = ["KBS", "VCI"]

for source in SOURCES:
    try:
        data = await self._fetch_from_source(symbol, source)
        if data:
            return data
    except Exception:
        continue  # Thử source tiếp
```

### Error Tolerance (BaseCrawler)

```python
# Nếu 1 mã lỗi, bỏ qua và tiếp tục mã khác
for symbol in symbols:
    try:
        df = await self.fetch(symbol)
        results[symbol] = df
    except Exception as e:
        failed.append((symbol, str(e)))  # Log và tiếp tục
    await asyncio.sleep(self.delay_seconds)  # Rate limiting
```

---

## 5. Phân tích kỹ thuật & cơ bản

### Technical Analysis (11 indicators)

```python
# apps/prometheus/src/localstock/analysis/technical.py

class TechnicalAnalyzer:
    def compute_indicators(self, df):
        # Dùng pandas-ta (individual calls, không dùng Study API)
        result = df.copy()
        result.ta.sma(length=20, append=True)    # SMA 20
        result.ta.sma(length=50, append=True)    # SMA 50
        result.ta.sma(length=200, append=True)   # SMA 200
        result.ta.ema(length=12, append=True)    # EMA 12
        result.ta.ema(length=26, append=True)    # EMA 26
        result.ta.rsi(length=14, append=True)    # RSI 14
        result.ta.macd(fast=12, slow=26, signal=9, append=True)  # MACD
        result.ta.bbands(length=20, std=2, append=True)          # Bollinger
        result.ta.stoch(append=True)             # Stochastic
        result.ta.adx(append=True)               # ADX
        result.ta.obv(append=True)               # OBV
        return result

    def compute_volume_analysis(self, df):
        avg_volume = df["volume"].tail(20).mean()
        latest_volume = df["volume"].iloc[-1]
        relative_volume = latest_volume / avg_volume
        # > 1.2 = increasing, < 0.8 = decreasing, else stable
```

### Fundamental Analysis

```python
# P/E, P/B, EPS, ROE, ROA, D/E
# Revenue growth QoQ, YoY
# So sánh với trung bình 20 nhóm ngành VN (ICB classification)
```

### Trend Detection

```python
# Multi-signal voting: MA crossover + price action
# Uptrend: SMA20 > SMA50 > SMA200, price above SMA50
# Manual peak/trough detection (không dùng scipy)
# Pivot points cho support/resistance
```

---

## 6. AI & LLM (Ollama)

### Sentiment Classification

Khi pipeline chạy Step 4, với mỗi bài tin tức:

```python
# apps/prometheus/src/localstock/ai/client.py

class OllamaClient:
    async def classify_sentiment(self, article_text, symbol):
        # 1. Truncate bài viết → 2000 ký tự (bảo mật)
        truncated = article_text[:2000]

        # 2. Gọi Ollama với structured output
        response = await self.client.chat(
            model="qwen2.5:14b-instruct-q4_K_M",
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Mã: {symbol}\n\nBài viết:\n{truncated}"},
            ],
            format=SentimentResult.model_json_schema(),  # JSON schema
            options={"temperature": 0.1},
        )

        # 3. Parse kết quả
        return SentimentResult.model_validate_json(response.message.content)
        # → {"sentiment": "positive", "score": 0.8, "reason": "Doanh thu tăng..."}
```

### Report Generation

Khi pipeline chạy Step 6, với top 20 mã:

```python
    async def generate_report(self, data_prompt, symbol):
        response = await self.client.chat(
            model="qwen2.5:14b-instruct-q4_K_M",
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": data_prompt},  # Dữ liệu indicators + scores
            ],
            format=StockReport.model_json_schema(),
            options={"temperature": 0.3},
        )
        return StockReport.model_validate_json(response.message.content)
```

**StockReport output (9 sections):**
```json
{
  "summary": "Tóm tắt 2-3 câu",
  "technical_analysis": "Phân tích chỉ báo kỹ thuật",
  "fundamental_analysis": "Đánh giá tài chính",
  "sentiment_analysis": "Tâm lý thị trường",
  "macro_impact": "Ảnh hưởng vĩ mô theo ngành",
  "long_term_suggestion": "Gợi ý đầu tư dài hạn",
  "swing_trade_suggestion": "⚠️ T+3: Gợi ý lướt sóng + cảnh báo T+3",
  "recommendation": "Mua mạnh | Mua | Nắm giữ | Bán | Bán mạnh",
  "confidence": "Cao | Trung bình | Thấp"
}
```

### Graceful Degradation

Nếu Ollama không chạy:
- ✅ Pipeline tiếp tục (không crash)
- ✅ Scoring dùng tech + fund + macro (bỏ sentiment)
- ❌ Không có báo cáo AI
- ❌ Không có sentiment analysis

---

## 7. Scoring Engine

### Composite Score (0-100)

```python
# apps/prometheus/src/localstock/scoring/engine.py

def compute_composite(tech, fund, sent, macro, config):
    """
    Mặc định:
      tech=30%, fund=30%, sent=20%, macro=20%

    Nếu thiếu dimension → redistribute trọng số:
      VD: thiếu sentiment → tech=37.5%, fund=37.5%, macro=25%
    """

    # 1. Thu thập dimensions có data
    dimensions = {}
    if tech is not None: dimensions["technical"] = tech
    if fund is not None: dimensions["fundamental"] = fund
    if sent is not None: dimensions["sentiment"] = sent
    if macro is not None: dimensions["macro"] = macro

    # 2. Chuẩn hóa trọng số (tổng = 1.0)
    total_weight = sum(weights.values())
    normalized = {k: v / total_weight for k, v in weights.items()}

    # 3. Tính điểm tổng hợp
    total_score = sum(dimensions[k] * normalized[k] for k in dimensions)

    # 4. Gán grade
    grade = score_to_grade(total_score)
    # 90-100=A+, 80-89=A, 70-79=B+, 60-69=B, 50-59=C, 0-49=D
```

### Technical Score (5 components × 20 điểm)

```
RSI positioning:     0-20 điểm (oversold=18, overbought=2)
Trend alignment:     0-20 điểm (uptrend=18, sideways=10, downtrend=3)
MACD momentum:       0-20 điểm (histogram>0 = 15, else 3)
Bollinger position:  0-20 điểm (near lower=16, upper=8, middle=12)
Volume confirmation: 0-20 điểm (high volume=14, low=5)
────────────────────
Total:               0-100 điểm
```

### Fundamental Score (5 components)

```
P/E valuation:       0-18 điểm (PE<8=18, PE<12=14, PE<18=10, else=3)
P/B valuation:       0-8 điểm
ROE profitability:   0-18 điểm (ROE>20%=18, >15%=15, >10%=12)
Revenue growth YoY:  0-15 điểm
Debt leverage (D/E): 0-15 điểm (D/E<0.5=15, <1.0=10)
```

---

## 8. Thông báo Telegram

### 3 loại thông báo

| Loại | Trigger | Nội dung |
|------|---------|----------|
| **Daily Digest** | Sau mỗi pipeline | Top 10 mã đáng mua với điểm + grade |
| **Score Change Alert** | Điểm thay đổi >15% | Mã cụ thể + điểm trước/sau |
| **Sector Rotation** | Kèm daily digest | Dòng tiền chảy giữa ngành |

### Cách hoạt động

```python
# apps/prometheus/src/localstock/notifications/telegram.py

class TelegramNotifier:
    async def send_message(self, text):
        if not self.is_configured:  # Không có token → skip
            return False

        # Tách message nếu > 4000 ký tự (Telegram limit)
        if len(text) > 4000:
            parts = self._split_message(text, 4000)
            for part in parts:
                await bot.send_message(chat_id, part, parse_mode="HTML")
        else:
            await bot.send_message(chat_id, text, parse_mode="HTML")
```

### Deduplication

```python
# Kiểm tra đã gửi chưa trước khi gửi (tránh duplicate khi restart)
if await notification_repo.was_sent_today("daily_digest", today):
    return  # Đã gửi rồi, bỏ qua

await notifier.send_message(digest)
await notification_repo.log_notification(today, "daily_digest", "sent")
```

---

## 9. Scheduler tự động

### APScheduler CronTrigger

```python
# apps/prometheus/src/localstock/scheduler/scheduler.py

scheduler.add_job(
    daily_job,
    trigger=CronTrigger(
        hour=15, minute=45,              # 15:45 VN time
        day_of_week="mon-fri",           # Thứ 2-6 only
        timezone="Asia/Ho_Chi_Minh",
    ),
    misfire_grace_time=3600,             # Nếu miss, chạy trong 1 giờ
)
```

### Trading Day Calendar

```python
# apps/prometheus/src/localstock/scheduler/calendar.py
import holidays

def is_trading_day(check_date=None):
    d = check_date or date.today()
    if d.weekday() >= 5:  return False          # Weekend
    if d in holidays.Vietnam(years=d.year): return False  # Lễ VN
    return True
```

**holidays.Vietnam** tự động handle:
- Tết Nguyên Đán (lunar calendar, thay đổi mỗi năm)
- 30/4, 1/5, 2/9, 1/1, Giỗ Tổ Hùng Vương
- Ngày nghỉ bù

---

## 10. Database Layer

### 18 bảng (5 nhóm)

```
📦 Master Data
├── stocks              — Danh sách mã (~400 HOSE)
├── stock_prices        — Giá OHLCV hàng ngày
├── corporate_events    — Splits, dividends
└── financial_statements — BCTC (JSON format)

📊 Analysis
├── technical_indicators — 11+ chỉ báo kỹ thuật/mã/ngày
├── financial_ratios     — P/E, ROE, etc./mã
├── industry_groups      — 20 nhóm ngành VN
├── industry_averages    — Trung bình ngành
└── stock_industry_mapping — Mã → ngành

📰 News & Sentiment
├── news_articles       — Bài viết từ RSS
└── sentiment_scores    — Sentiment/bài/mã

🏆 Scoring & Reports
├── composite_scores    — Điểm tổng hợp/mã/ngày
├── stock_reports       — Báo cáo AI (9 sections)
├── macro_indicators    — Lãi suất, tỷ giá, CPI
├── score_changes       — Biến động điểm >15%
└── sector_snapshots    — Snapshot ngành hàng ngày

⚙️ Operations
├── pipeline_runs       — Log pipeline execution
└── notifications_sent  — Log thông báo đã gửi
```

### Repository Pattern

```python
# Tất cả DB operations qua Repository classes
# Upsert pattern — insert hoặc update nếu đã tồn tại

async def upsert_prices(self, symbol, df):
    stmt = insert(StockPrice).values(...)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "date"],  # Unique constraint
        set_={...}                          # Update nếu trùng
    )
    await session.execute(stmt)
```

### Session Management

```python
# Mỗi step trong pipeline dùng riêng 1 session
# Tránh session leak và transaction conflict

async with session_factory() as session:
    service = AnalysisService(session)
    await service.run_full()
    # Session tự commit/rollback khi thoát context
```

---

## 11. Frontend (Next.js)

### Architecture

```
apps/helios/src/
├── app/                    # Pages (App Router)
│   ├── layout.tsx          # Root layout (dark theme, Vietnamese)
│   ├── page.tsx            # Home → redirect to /rankings
│   ├── rankings/page.tsx   # Bảng xếp hạng
│   ├── market/page.tsx     # Tổng quan thị trường
│   └── stock/[symbol]/     # Chi tiết mã
│       └── page.tsx        # Candlestick chart + AI report
├── components/
│   ├── layout/             # Sidebar (240px), AppShell
│   ├── charts/             # Candlestick (lightweight-charts v5)
│   ├── rankings/           # DataTable, GradeBadge
│   ├── market/             # MacroCards, SectorTable
│   └── ui/                 # EmptyState, ErrorState
└── lib/
    ├── api.ts              # apiFetch() → localhost:8000
    ├── queries.ts           # 10 React Query hooks
    ├── types.ts             # 14 TypeScript interfaces
    └── utils.ts             # Vietnamese formatters
```

### Data Flow

```
React Component → useTopScores() hook → React Query cache
                                          ↓ (cache miss)
                                       apiFetch("/api/scores/top")
                                          ↓
                                       FastAPI backend :8000
                                          ↓
                                       PostgreSQL
```

### React Query Hooks

```typescript
// apps/helios/src/lib/queries.ts

useTopScores(limit=20)           // GET /api/scores/top
useStockScore(symbol)            // GET /api/scores/{symbol}
useStockPrices(symbol, days=365) // GET /api/prices/{symbol}
useStockIndicators(symbol)       // GET /api/prices/{symbol}/indicators
useTechnicalAnalysis(symbol)     // GET /api/analysis/{symbol}/technical
useFundamentalAnalysis(symbol)   // GET /api/analysis/{symbol}/fundamental
useStockReport(symbol)           // GET /api/reports/{symbol}
useMacroLatest()                 // GET /api/macro/latest
useSectorSnapshots()             // GET /api/sectors/latest
useTriggerPipeline()             // POST /api/automation/run (mutation)
```

### Chart Implementation

```typescript
// apps/helios/src/components/charts/price-chart.tsx
// Dùng lightweight-charts v5 (TradingView library)

const chart = createChart(container, { width, height });
const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: "#22c55e",      // Xanh = tăng
    downColor: "#ef4444",     // Đỏ = giảm
});
candleSeries.setData(priceData);  // OHLCV from API
```

---

## 12. Cấu hình hệ thống

### Pydantic Settings

```python
# apps/prometheus/src/localstock/config.py

class Settings(BaseSettings):
    # Tự load từ .env file
    model_config = {"env_file": ".env"}

    database_url: str                    # BẮT BUỘC
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    scoring_weight_technical: float = 0.30
    telegram_bot_token: str = ""         # Trống = tắt
    scheduler_run_hour: int = 15
    # ... (xem .env.example cho đầy đủ)

@lru_cache  # Singleton — chỉ load 1 lần
def get_settings() -> Settings:
    return Settings()
```

### Thay đổi config

1. Sửa file `.env`
2. Restart backend (`Ctrl+C` rồi chạy lại)
3. Settings tự load giá trị mới

---

## 13. Design Patterns

| Pattern | Mục đích | Vị trí |
|---------|----------|--------|
| **Async + run_in_executor** | Wrap sync vnstock trong async pipeline | crawlers/*.py |
| **Error Tolerance** | Mã lỗi bỏ qua, tiếp tục crawl mã khác | base.py, pipeline.py |
| **Upsert (ON CONFLICT)** | Insert mới hoặc update cũ — idempotent | repositories/*.py |
| **Repository Pattern** | Tập trung DB operations vào 1 class/bảng | db/repositories/*.py |
| **Lifespan Scheduler** | APScheduler khởi tạo cùng FastAPI, tắt cùng | scheduler.py |
| **Weight Redistribution** | Thiếu dimension → chia lại trọng số | scoring/engine.py |
| **Structured LLM Output** | Pydantic JSON Schema → Ollama format | ai/client.py |
| **Deduplication** | Check `was_sent_today()` trước khi gửi | notifications/ |
| **Incremental Crawl** | Chỉ lấy dữ liệu sau ngày cuối cùng | pipeline.py |
| **Process Lock** | `asyncio.Lock()` ngăn chạy pipeline song song | automation_service.py |
| **Source Fallback** | KBS fail → VCI (cho financial data) | finance_crawler.py |
| **Session-per-step** | Mỗi pipeline step dùng riêng DB session | automation_service.py |
