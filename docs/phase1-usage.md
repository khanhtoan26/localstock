# LocalStock — Hướng dẫn sử dụng (Phase 1, 2 & 3)

> Tài liệu tổng hợp tất cả những gì có thể chạy sau khi hoàn thành Phase 1 (Data Pipeline), Phase 2 (Technical & Fundamental Analysis) và Phase 3 (Sentiment Analysis & Scoring Engine).
> Cập nhật: 2026-04-16

---

## Mục lục

1. [Yêu cầu cài đặt](#1-yêu-cầu-cài-đặt)
2. [Cấu hình môi trường](#2-cấu-hình-môi-trường)
3. [Khởi tạo database](#3-khởi-tạo-database)
4. [API Server](#4-api-server)
5. [Chạy pipeline thu thập dữ liệu](#5-chạy-pipeline-thu-thập-dữ-liệu)
6. [Crawlers riêng lẻ](#6-crawlers-riêng-lẻ)
7. [Phân tích kỹ thuật & cơ bản (Phase 2)](#7-phân-tích-kỹ-thuật--cơ-bản-phase-2)
8. [Tin tức & Cảm xúc thị trường (Phase 3)](#8-tin-tức--cảm-xúc-thị-trường-phase-3)
9. [Xếp hạng & Chấm điểm (Phase 3)](#9-xếp-hạng--chấm-điểm-phase-3)
10. [Truy vấn dữ liệu](#10-truy-vấn-dữ-liệu)
11. [Kiểm thử](#11-kiểm-thử)
12. [Công cụ chất lượng code](#12-công-cụ-chất-lượng-code)
13. [Bảng tổng hợp](#13-bảng-tổng-hợp)

---

## 1. Yêu cầu cài đặt

```bash
# Python >= 3.12
python3 --version

# Cài uv (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài dependencies
cd localstock
uv sync

# Cài dev dependencies (pytest, ruff, mypy)
uv sync --extra dev
```

**Yêu cầu bên ngoài:**
- **Supabase PostgreSQL** — database miễn phí tại [supabase.com](https://supabase.com)
- **Kết nối internet** — để gọi vnstock API lấy dữ liệu thị trường
- **Ollama** — local LLM server cho phân tích cảm xúc (tùy chọn, bỏ qua nếu không có)
  ```bash
  # Cài Ollama + tải model
  curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen2.5:14b-instruct-q4_K_M
  ```

---

## 2. Cấu hình môi trường

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

Nội dung `.env`:

```env
# Supabase PostgreSQL
# Lấy từ: Supabase Dashboard → Settings → Database → Connection string
DATABASE_URL=postgresql+asyncpg://user:password@pooler-host:5432/postgres
DATABASE_URL_MIGRATION=postgresql+asyncpg://user:password@pooler-host:5432/postgres

# Nguồn dữ liệu vnstock (VCI hoặc KBS)
VNSTOCK_SOURCE=VCI

# Cấu hình crawl
CRAWL_DELAY_SECONDS=1.0    # Delay giữa các request (tránh rate limit)
CRAWL_BATCH_SIZE=50         # Kích thước batch

# Logging
LOG_LEVEL=INFO              # INFO, DEBUG, WARNING, ERROR

# Phase 3 — Ollama / Sentiment / Scoring
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M
OLLAMA_TIMEOUT=120
OLLAMA_KEEP_ALIVE=30m
SCORING_WEIGHT_TECHNICAL=0.35
SCORING_WEIGHT_FUNDAMENTAL=0.35
SCORING_WEIGHT_SENTIMENT=0.30
SCORING_WEIGHT_MACRO=0.0
FUNNEL_TOP_N=50
SENTIMENT_ARTICLES_PER_STOCK=5
SENTIMENT_LOOKBACK_DAYS=7
```

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `DATABASE_URL` | ✅ | Connection string async (asyncpg) cho ứng dụng |
| `DATABASE_URL_MIGRATION` | ❌ | Connection string cho Alembic migration (mặc định dùng DATABASE_URL) |
| `VNSTOCK_SOURCE` | ❌ | `VCI` (mặc định) hoặc `KBS` |
| `CRAWL_DELAY_SECONDS` | ❌ | Delay giữa requests, mặc định `1.0` giây |
| `LOG_LEVEL` | ❌ | Mức log, mặc định `INFO` |
| `OLLAMA_HOST` | ❌ | Địa chỉ Ollama server, mặc định `http://localhost:11434` |
| `OLLAMA_MODEL` | ❌ | Model LLM cho sentiment, mặc định `qwen2.5:14b-instruct-q4_K_M` |
| `OLLAMA_TIMEOUT` | ❌ | Timeout gọi LLM (giây), mặc định `120` |
| `SCORING_WEIGHT_*` | ❌ | Trọng số chấm điểm mỗi chiều (tổng = 1.0) |
| `FUNNEL_TOP_N` | ❌ | Số mã top chạy sentiment (tiết kiệm GPU), mặc định `50` |
| `SENTIMENT_LOOKBACK_DAYS` | ❌ | Số ngày lùi lại lấy tin tức, mặc định `7` |

> **Lưu ý SSL:** Nếu mạng có proxy/firewall chặn SSL, thêm biến môi trường:
> ```bash
> export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
> export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
> ```

---

## 3. Khởi tạo database

### Tạo schema (lần đầu)

```bash
# Áp dụng migration — tạo 13 bảng trong Supabase (Phase 1 + Phase 2 + Phase 3)
uv run alembic upgrade head
```

Các bảng được tạo:

**Phase 1 — Data Pipeline:**

| Bảng | Mô tả | Khóa chính |
|------|--------|------------|
| `stocks` | Thông tin mã cổ phiếu (tên, sàn, ngành ICB) | `symbol` |
| `stock_prices` | Dữ liệu giá OHLCV hàng ngày | `id`, unique `(symbol, date)` |
| `financial_statements` | Báo cáo tài chính (JSON linh hoạt) | `id`, unique `(symbol, year, period, report_type)` |
| `corporate_events` | Sự kiện doanh nghiệp (chia tách, cổ tức) | `id`, unique `(symbol, exright_date, event_type)` |
| `pipeline_runs` | Lịch sử chạy pipeline | `id` |

**Phase 2 — Analysis:**

| Bảng | Mô tả | Khóa chính |
|------|--------|------------|
| `technical_indicators` | SMA, EMA, RSI, MACD, BB, volume, trend, S/R | `id`, unique `(symbol, date)` |
| `financial_ratios` | P/E, P/B, EPS, ROE, ROA, D/E, growth rates | `id`, unique `(symbol, year, period)` |
| `industry_groups` | 20 nhóm ngành VN (code, name_vi, name_en) | `code` |
| `stock_industry_mapping` | Mapping mã CK → nhóm ngành (từ ICB Level 3) | `symbol` |
| `industry_averages` | Trung bình ngành theo kỳ (avg_pe, avg_roe, ...) | `id`, unique `(group_code, year, period)` |

**Phase 3 — Sentiment & Scoring:**

| Bảng | Mô tả | Khóa chính |
|------|--------|------------|
| `news_articles` | Tin tức crawl từ CafeF / VnExpress RSS | `id`, unique `(url)` |
| `sentiment_scores` | Kết quả phân tích cảm xúc LLM theo bài viết | `id`, unique `(article_id, symbol)` |
| `composite_scores` | Điểm tổng hợp xếp hạng cổ phiếu theo ngày | `id`, unique `(symbol, date)` |

### Các lệnh Alembic hữu ích

```bash
# Xem migration hiện tại
uv run alembic current

# Xem lịch sử migration
uv run alembic history --verbose

# Tạo migration mới (khi thay đổi models)
uv run alembic revision --autogenerate -m "mô tả thay đổi"

# Rollback 1 migration
uv run alembic downgrade -1

# Rollback về trạng thái ban đầu
uv run alembic downgrade base
```

---

## 4. API Server

### Khởi động

```bash
# Development (auto-reload khi sửa code)
uv run uvicorn localstock.api.app:app --reload --port 8000

# Production
uv run uvicorn localstock.api.app:app --host 0.0.0.0 --port 8000
```

### Endpoints có sẵn

#### `GET /health` — Kiểm tra sức khỏe hệ thống

```bash
curl http://localhost:8000/health
```

Kết quả trả về:

```json
{
  "status": "healthy",
  "stocks": 1,
  "prices": 525,
  "last_pipeline_run": {
    "status": "completed",
    "started_at": "2026-04-15T04:42:32Z",
    "completed_at": "2026-04-15T04:42:59Z",
    "symbols_total": 400,
    "symbols_success": 395,
    "symbols_failed": 5
  }
}
```

#### `GET /docs` — Swagger UI (tự động từ FastAPI)

Truy cập `http://localhost:8000/docs` để xem API documentation tương tác.

#### Phase 2 — API phân tích

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/analysis/{symbol}/technical` | Chỉ số kỹ thuật mới nhất |
| `GET` | `/api/analysis/{symbol}/fundamental` | Tỷ số tài chính mới nhất |
| `GET` | `/api/analysis/{symbol}/trend` | Xu hướng + hỗ trợ/kháng cự |
| `POST` | `/api/analysis/run` | Chạy phân tích toàn bộ HOSE |
| `GET` | `/api/industry/groups` | Danh sách 20 nhóm ngành VN |
| `GET` | `/api/industry/{group_code}/averages` | Trung bình ngành (P/E, ROE, ...) |

#### Phase 3 — API tin tức, cảm xúc & chấm điểm

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/news/crawl` | Crawl tin tức từ CafeF + VnExpress RSS |
| `GET` | `/api/news` | Xem tin tức gần đây (params: `days`, `limit`) |
| `GET` | `/api/news/{symbol}/sentiment` | Xem cảm xúc theo mã (params: `days`) |
| `POST` | `/api/sentiment/run` | Chạy phân tích cảm xúc bằng LLM |
| `POST` | `/api/scores/run` | Chạy pipeline chấm điểm toàn bộ |
| `GET` | `/api/scores/top` | Top cổ phiếu xếp hạng (params: `limit`) |
| `GET` | `/api/scores/{symbol}` | Xem điểm một mã cụ thể |

```bash
# Ví dụ gọi API phân tích
curl http://localhost:8000/api/analysis/VNM/technical
curl http://localhost:8000/api/analysis/VNM/fundamental
curl http://localhost:8000/api/analysis/VNM/trend
curl http://localhost:8000/api/industry/groups
curl http://localhost:8000/api/industry/BANKING/averages

# Chạy phân tích toàn bộ (~3-4 phút)
curl -X POST http://localhost:8000/api/analysis/run
```

---

## 5. Chạy pipeline thu thập dữ liệu

### 5.1. Pipeline toàn bộ (~400 mã HOSE)

Crawl tất cả dữ liệu cho toàn bộ mã HOSE:

```python
# file: run_pipeline.py
import asyncio
from localstock.db.database import get_engine, get_session_factory
from localstock.services.pipeline import Pipeline

async def main():
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        pipeline = Pipeline(session)
        run = await pipeline.run_full(run_type="daily")
        print(f"Trạng thái: {run.status}")
        print(f"Tổng: {run.symbols_total} mã")
        print(f"Thành công: {run.symbols_success}")
        print(f"Thất bại: {run.symbols_failed}")
        if run.errors:
            print(f"Lỗi: {run.errors}")
    await engine.dispose()

asyncio.run(main())
```

```bash
uv run python run_pipeline.py
```

**Quy trình `run_full()` thực hiện (8 bước):**

1. Lấy danh sách ~400 mã HOSE từ vnstock → lưu bảng `stocks`
2. Crawl giá OHLCV (incremental: chỉ lấy từ ngày cuối trong DB) → lưu bảng `stock_prices`
3. Crawl BCTC (cân đối kế toán, KQKD, lưu chuyển tiền tệ) → lưu bảng `financial_statements`
4. Crawl thông tin công ty (ngành ICB, vốn điều lệ) → cập nhật bảng `stocks`
5. Crawl sự kiện doanh nghiệp (chia tách, cổ tức) → lưu bảng `corporate_events`
6. Điều chỉnh giá lịch sử cho các sự kiện chưa xử lý (backward adjustment)

**Tham số `run_type`:**
- `"daily"` — chạy hàng ngày (mặc định, incremental)
- `"backfill"` — lấy lại dữ liệu lịch sử
- `"manual"` — chạy thủ công

**Thời gian ước tính:** ~1-2 giờ cho lần đầu (backfill 2 năm), ~10-20 phút cho daily.

### 5.2. Pipeline cho một mã cụ thể

Crawl nhanh dữ liệu cho 1 mã (on-demand):

```python
# file: run_single.py
import asyncio
from localstock.db.database import get_engine, get_session_factory
from localstock.services.pipeline import Pipeline

async def main():
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_single("VNM")
        print(f"Mã: {result['symbol']}")
        print(f"Trạng thái: {result['status']}")
        print(f"Giá: {result.get('prices', 0)} dòng")
        print(f"BCTC: {result.get('financials', 0)} báo cáo")
        print(f"Công ty: {result.get('company', False)}")
        print(f"Sự kiện: {result.get('events', 0)}")
        if result['errors']:
            print(f"Lỗi: {result['errors']}")
    await engine.dispose()

asyncio.run(main())
```

```bash
uv run python run_single.py
```

**Kết quả mẫu (VNM):**
```
Mã: VNM
Trạng thái: completed
Giá: 525 dòng (2 năm OHLCV)
BCTC: 3 báo cáo (balance_sheet, income_statement, cash_flow)
Công ty: True
Sự kiện: 57 sự kiện
```

---

## 6. Crawlers riêng lẻ

Mỗi crawler có thể chạy độc lập (chỉ fetch, không lưu DB):

### 6.1. PriceCrawler — Giá OHLCV

```python
import asyncio
from localstock.crawlers.price_crawler import PriceCrawler

async def main():
    crawler = PriceCrawler()
    df = await crawler.fetch("VNM", start_date="2024-01-01", end_date="2026-04-15")
    print(f"Cột: {df.columns.tolist()}")  # time, open, high, low, close, volume
    print(df.tail())

asyncio.run(main())
```

### 6.2. FinanceCrawler — Báo cáo tài chính

```python
import asyncio
from localstock.crawlers.finance_crawler import FinanceCrawler

async def main():
    crawler = FinanceCrawler()
    reports = await crawler.fetch("VNM", period="quarter")
    for name, df in reports.items():
        print(f"{name}: {df.shape}")  # (52 quý, 41 cột) v.v.

asyncio.run(main())
```

**Loại báo cáo:** `balance_sheet`, `income_statement`, `cash_flow`
**Nguồn:** KBS (ưu tiên) → VCI (fallback)

### 6.3. CompanyCrawler — Thông tin công ty

```python
import asyncio
from localstock.crawlers.company_crawler import CompanyCrawler

async def main():
    crawler = CompanyCrawler()
    df = await crawler.fetch("VNM")
    print(df[['symbol', 'short_name', 'exchange', 'icb_name3']].to_string())

asyncio.run(main())
```

### 6.4. EventCrawler — Sự kiện doanh nghiệp

```python
import asyncio
from localstock.crawlers.event_crawler import EventCrawler

async def main():
    crawler = EventCrawler()
    df = await crawler.fetch("VNM")
    print(f"Tổng sự kiện: {len(df)}")
    print(df[['event_title', 'exright_date', 'event_list_code', 'ratio']].head(10))

asyncio.run(main())
```

**Loại sự kiện:** `split` (chia tách), `stock_dividend` (cổ tức CP), `cash_dividend` (cổ tức tiền mặt), `rights_issue` (phát hành quyền)

### 6.5. Crawl hàng loạt

Tất cả crawler đều hỗ trợ `fetch_batch()` — crawl nhiều mã với error tolerance:

```python
import asyncio
from localstock.crawlers.price_crawler import PriceCrawler

async def main():
    crawler = PriceCrawler()
    symbols = ["VNM", "ACB", "HPG", "FPT", "MWG"]
    results, failed = await crawler.fetch_batch(symbols)
    print(f"Thành công: {len(results)} mã")
    print(f"Thất bại: {len(failed)} mã")
    for sym, error in failed:
        print(f"  {sym}: {error}")

asyncio.run(main())
```

---

## 7. Phân tích kỹ thuật & cơ bản (Phase 2)

Phase 2 xây dựng engine phân tích cho ~400 cổ phiếu HOSE:
- **Technical Analysis**: SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic, ADX, OBV, volume analysis, trend detection, support/resistance
- **Fundamental Analysis**: P/E, P/B, EPS, ROE, ROA, D/E, growth rates (QoQ, YoY), TTM
- **Industry Analysis**: 20 nhóm ngành VN, mapping ICB Level 3, industry averages

### 7.1. Chạy phân tích toàn bộ HOSE

```bash
# Qua API (yêu cầu server đang chạy)
curl -X POST http://localhost:8000/api/analysis/run
```

**Response mẫu:**
```json
{
  "technical_success": 398,
  "technical_errors": 2,
  "fundamental_success": 395,
  "fundamental_errors": 5,
  "industry_groups_seeded": 20,
  "stocks_mapped": 398
}
```

### 7.2. Chạy phân tích qua Python

```python
# file: run_analysis.py
import asyncio
from localstock.db.database import get_engine, get_session_factory
from localstock.services.analysis_service import AnalysisService

async def main():
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        service = AnalysisService(session)

        # Phân tích toàn bộ HOSE
        result = await service.run_full()
        print(f"Technical: {result['technical_success']} thành công")
        print(f"Fundamental: {result['fundamental_success']} thành công")

        # Hoặc phân tích 1 mã
        single = await service.run_single("VNM")
        print(f"VNM technical: {single.get('technical', {})}")
        print(f"VNM fundamental: {single.get('fundamental', {})}")

    await engine.dispose()

asyncio.run(main())
```

### 7.3. Xem kết quả phân tích

```bash
# Technical indicators cho 1 mã
curl http://localhost:8000/api/analysis/VNM/technical
```

**Response mẫu:**
```json
{
  "symbol": "VNM",
  "date": "2025-01-15",
  "sma_20": 72.5, "sma_50": 71.2, "sma_200": 68.9,
  "ema_12": 73.1, "ema_26": 72.0,
  "rsi_14": 55.3,
  "macd": 1.1, "macd_signal": 0.8, "macd_histogram": 0.3,
  "bb_upper": 76.2, "bb_middle": 72.5, "bb_lower": 68.8,
  "stoch_k": 62.1, "stoch_d": 58.7,
  "adx": 25.4, "obv": 15234567,
  "avg_volume_20": 1250000, "relative_volume": 1.12,
  "volume_trend": "increasing"
}
```

```bash
# Trend + Support/Resistance
curl http://localhost:8000/api/analysis/VNM/trend
```

**Response mẫu:**
```json
{
  "symbol": "VNM",
  "trend_direction": "bullish",
  "trend_strength": 25.4,
  "pivot_point": 72.0,
  "support_1": 70.5, "support_2": 69.0,
  "resistance_1": 73.5, "resistance_2": 75.0,
  "nearest_support": 70.5, "nearest_resistance": 73.5
}
```

```bash
# Financial ratios
curl http://localhost:8000/api/analysis/VNM/fundamental
```

```bash
# 20 nhóm ngành VN
curl http://localhost:8000/api/industry/groups

# Trung bình ngành (VD: ngân hàng)
curl http://localhost:8000/api/industry/BANKING/averages
```

### 7.4. 20 nhóm ngành Việt Nam

| Code | Tên Việt | Tên Anh |
|------|----------|---------|
| BANKING | Ngân hàng | Banking |
| REAL_ESTATE | Bất động sản | Real Estate |
| SECURITIES | Chứng khoán | Securities |
| INSURANCE | Bảo hiểm | Insurance |
| STEEL | Thép | Steel |
| CONSTRUCTION | Xây dựng | Construction |
| RETAIL | Bán lẻ | Retail |
| FOOD_BEVERAGE | Thực phẩm & Đồ uống | Food & Beverage |
| SEAFOOD | Thủy sản | Seafood |
| TEXTILE | Dệt may | Textile & Garment |
| TECHNOLOGY | Công nghệ | Technology |
| POWER | Điện | Power & Utilities |
| OIL_GAS | Dầu khí | Oil & Gas |
| CHEMICALS | Hóa chất | Chemicals |
| LOGISTICS | Vận tải & Logistics | Logistics |
| AVIATION | Hàng không | Aviation |
| PHARMA | Dược phẩm | Pharmaceuticals |
| RUBBER | Cao su | Rubber |
| PLASTICS | Nhựa & Bao bì | Plastics & Packaging |
| OTHER | Khác | Other |

### 7.5. Lưu ý về dữ liệu vnstock

> **Giá cổ phiếu:** vnstock trả giá theo đơn vị **1000 VND** (ví dụ: 61.6 = 61,600 VND). Hệ thống đã tự chuyển đổi khi tính market cap.
>
> **BCTC từ VCI:** Tên cột gốc dạng verbose (`"Revenue (Bn. VND)"`, `"TOTAL ASSETS (Bn. VND)"`). Hệ thống tự normalize về keys đơn giản (`revenue`, `total_assets`).
>
> **Shares outstanding:** Nếu `issue_shares` là null, hệ thống dùng fallback: `charter_capital / 10,000` (mệnh giá cổ phiếu VN = 10,000 VND).

---

## 8. Tin tức & Cảm xúc thị trường (Phase 3)

Phase 3 bổ sung khả năng crawl tin tức tài chính và phân tích cảm xúc (sentiment) bằng LLM chạy local qua Ollama.

### 8.1. Thu thập tin tức (News Crawl)

Crawl tin tức từ CafeF và VnExpress qua RSS:

```bash
# API: Crawl tin tức từ CafeF + VnExpress RSS
curl -X POST http://localhost:8000/api/news/crawl
```

**Response mẫu:**
```json
{
  "status": "completed",
  "articles_found": 85,
  "articles_stored": 62,
  "duplicates_skipped": 23,
  "sources": ["cafef", "vnexpress"]
}
```

```bash
# API: Xem tin tức gần đây
curl "http://localhost:8000/api/news?days=7&limit=10"
```

### 8.2. Phân tích cảm xúc (Sentiment Analysis)

Yêu cầu Ollama đang chạy với model `qwen2.5`:

```bash
# Khởi động Ollama
ollama serve &
ollama pull qwen2.5:14b-instruct-q4_K_M

# API: Chạy phân tích cảm xúc
curl -X POST http://localhost:8000/api/sentiment/run
```

**Response mẫu:**
```json
{
  "status": "completed",
  "ollama_available": true,
  "funnel_candidates": 50,
  "articles_processed": 187,
  "sentiment_scores_stored": 187,
  "duration_seconds": 342
}
```

> **Lưu ý:** Nếu Ollama không khả dụng, API trả `"ollama_available": false` và bỏ qua phân tích — không gây lỗi.

```bash
# API: Xem cảm xúc theo mã
curl "http://localhost:8000/api/news/VNM/sentiment?days=7"
```

**Response mẫu:**
```json
{
  "symbol": "VNM",
  "aggregate_score": 0.65,
  "article_count": 5,
  "scores": [
    {
      "title": "Vinamilk báo lãi kỷ lục quý I/2026",
      "sentiment": "positive",
      "score": 0.85,
      "reason": "Kết quả kinh doanh vượt kỳ vọng, tăng trưởng doanh thu 15%",
      "published_at": "2026-04-14T08:30:00Z"
    },
    {
      "title": "Ngành sữa cạnh tranh khốc liệt từ hàng nhập khẩu",
      "sentiment": "negative",
      "score": -0.40,
      "reason": "Áp lực cạnh tranh từ sữa ngoại nhập, thị phần bị đe dọa",
      "published_at": "2026-04-12T10:15:00Z"
    }
  ]
}
```

### 8.3. Chi tiết kỹ thuật

**Nguồn RSS:**
- **CafeF** (4 feeds): `thi-truong-chung-khoan`, `doanh-nghiep`, `tai-chinh-ngan-hang`, `vi-mo-dau-tu`
- **VnExpress** (1 feed): `kinh-doanh`

**Xử lý LLM:**
- Ollama structured output: `format=SentimentResult.model_json_schema()`
- Anti-prompt-injection: cắt nội dung bài viết ở 2,000 ký tự
- Kết quả: `sentiment` (positive/negative/neutral), `score` (-1.0 đến 1.0), `reason` (giải thích)

**Tổng hợp cảm xúc:**
- Time-weighted aggregation: exponential decay với `half_life=3 ngày`
- Tin mới có trọng số cao hơn tin cũ
- Aggregate score = trung bình có trọng số của tất cả bài viết liên quan

**Chiến lược funnel:**
- Chỉ chạy LLM cho top `FUNNEL_TOP_N` cổ phiếu (mặc định 50) — tiết kiệm GPU
- Top N được chọn dựa trên điểm kỹ thuật + cơ bản từ Phase 2
- Mỗi mã tối đa `SENTIMENT_ARTICLES_PER_STOCK` bài viết (mặc định 5)

---

## 9. Xếp hạng & Chấm điểm (Phase 3)

Hệ thống chấm điểm tổng hợp kết hợp phân tích kỹ thuật, cơ bản và cảm xúc để xếp hạng cổ phiếu.

### 9.1. Chạy chấm điểm

```bash
# API: Chạy pipeline chấm điểm toàn bộ
curl -X POST http://localhost:8000/api/scores/run
```

**Response mẫu:**
```json
{
  "status": "completed",
  "stocks_scored": 398,
  "errors": 2,
  "date": "2026-04-16"
}
```

### 9.2. Xem xếp hạng

```bash
# API: Top 20 cổ phiếu
curl "http://localhost:8000/api/scores/top?limit=20"
```

**Response mẫu:**
```json
{
  "date": "2026-04-16",
  "stocks": [
    {
      "symbol": "FPT",
      "total_score": 82.5,
      "grade": "A",
      "rank": 1,
      "technical_score": 78.3,
      "fundamental_score": 88.1,
      "sentiment_score": 79.4
    },
    {
      "symbol": "ACB",
      "total_score": 76.8,
      "grade": "B",
      "rank": 2,
      "technical_score": 72.1,
      "fundamental_score": 80.5,
      "sentiment_score": 75.2
    }
  ]
}
```

```bash
# API: Xem điểm một mã cụ thể
curl "http://localhost:8000/api/scores/VNM"
```

### 9.3. Hệ thống chấm điểm

| Chiều | Trọng số | Nguồn dữ liệu | Normalize |
|-------|----------|----------------|-----------|
| **Kỹ thuật** | 35% | RSI, MACD, Bollinger Bands, trend, volume | 0-100 |
| **Cơ bản** | 35% | P/E, P/B, ROE, D/E | 0-100 |
| **Cảm xúc** | 30% | LLM sentiment từ tin tức | 0-100 |
| **Vĩ mô** | 0% | Chưa triển khai (Phase 4) | — |

**Tổng điểm:** Composite 0-100, tự động phân bổ lại trọng số nếu thiếu chiều nào (ví dụ: không có sentiment → kỹ thuật 50% + cơ bản 50%).

**Bảng xếp hạng (Grade):**

| Grade | Điểm | Ý nghĩa |
|-------|------|---------|
| **A** | 80-100 | Xuất sắc |
| **B** | 60-79 | Tốt |
| **C** | 40-59 | Trung bình |
| **D** | 20-39 | Yếu |
| **F** | 0-19 | Kém |

---

## 10. Truy vấn dữ liệu

### 10.1. Qua Repository (trong code Python)

```python
import asyncio
from localstock.db.database import get_engine, get_session_factory
from localstock.db.repositories.stock_repo import StockRepository
from localstock.db.repositories.price_repo import PriceRepository
from localstock.db.repositories.financial_repo import FinancialRepository
from localstock.db.repositories.event_repo import EventRepository

async def main():
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        stock_repo = StockRepository(session)
        price_repo = PriceRepository(session)
        fin_repo = FinancialRepository(session)
        event_repo = EventRepository(session)

        # Lấy danh sách mã HOSE
        symbols = await stock_repo.get_all_hose_symbols()
        print(f"Tổng mã HOSE: {len(symbols)}")

        # Lấy ngày giá mới nhất của 1 mã
        latest = await price_repo.get_latest_date("VNM")
        print(f"Giá VNM mới nhất: {latest}")

        # Lấy toàn bộ giá của 1 mã
        prices = await price_repo.get_prices("VNM", start_date="2026-01-01")
        print(f"Số dòng giá VNM từ 2026: {len(prices)}")

        # Lấy BCTC mới nhất
        period = await fin_repo.get_latest_period("VNM", "balance_sheet")
        print(f"BCTC mới nhất VNM: {period}")  # (2025, 'Q4')

        # Lấy sự kiện chưa xử lý
        events = await event_repo.get_unprocessed_events("VNM")
        print(f"Sự kiện chưa xử lý: {len(events)}")

        # --- Phase 2: Analysis repositories ---
        from localstock.db.repositories.indicator_repo import IndicatorRepository
        from localstock.db.repositories.ratio_repo import RatioRepository
        from localstock.db.repositories.industry_repo import IndustryRepository

        ind_repo = IndicatorRepository(session)
        ratio_repo = RatioRepository(session)
        industry_repo = IndustryRepository(session)

        # Lấy chỉ số kỹ thuật mới nhất
        indicator = await ind_repo.get_latest("VNM")
        if indicator:
            print(f"RSI: {indicator.rsi_14}, SMA20: {indicator.sma_20}")

        # Lấy tỷ số tài chính
        ratio = await ratio_repo.get_latest("VNM")
        if ratio:
            print(f"P/E: {ratio.pe_ratio}, ROE: {ratio.roe}")

        # Lấy danh sách nhóm ngành
        groups = await industry_repo.get_all_groups()
        print(f"Số nhóm ngành: {len(groups)}")

    await engine.dispose()

asyncio.run(main())
```

### 10.2. Qua SQL trực tiếp (Supabase Dashboard hoặc psql)

```sql
-- Top 10 mã theo volume trung bình 30 ngày
SELECT symbol, AVG(volume) as avg_vol
FROM stock_prices
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY symbol
ORDER BY avg_vol DESC
LIMIT 10;

-- Giá đóng cửa mới nhất của tất cả mã
SELECT DISTINCT ON (symbol) symbol, date, close, volume
FROM stock_prices
ORDER BY symbol, date DESC;

-- Số kỳ BCTC theo từng mã
SELECT symbol, report_type, COUNT(*) as periods
FROM financial_statements
GROUP BY symbol, report_type
ORDER BY symbol, report_type;

-- Sự kiện chia tách/cổ tức cổ phiếu (ảnh hưởng giá)
SELECT symbol, event_type, exright_date, ratio, processed
FROM corporate_events
WHERE event_type IN ('split', 'stock_dividend')
ORDER BY exright_date DESC;

-- [Phase 2] Top 10 mã theo RSI (quá bán: RSI < 30)
SELECT symbol, date, rsi_14, sma_20, trend_direction
FROM technical_indicators
WHERE rsi_14 < 30
ORDER BY rsi_14 ASC
LIMIT 10;

-- [Phase 2] Top 10 mã theo P/E thấp nhất (undervalued)
SELECT symbol, year, period, pe_ratio, pb_ratio, roe, eps
FROM financial_ratios
WHERE pe_ratio > 0
ORDER BY pe_ratio ASC
LIMIT 10;

-- [Phase 2] So sánh P/E công ty vs trung bình ngành
SELECT fr.symbol, fr.pe_ratio, ia.avg_pe, sim.group_code,
       ROUND((fr.pe_ratio / NULLIF(ia.avg_pe, 0) - 1) * 100, 1) as "% vs ngành"
FROM financial_ratios fr
JOIN stock_industry_mapping sim ON fr.symbol = sim.symbol
JOIN industry_averages ia ON sim.group_code = ia.group_code
  AND fr.year = ia.year AND fr.period = ia.period
WHERE fr.pe_ratio IS NOT NULL
ORDER BY fr.pe_ratio ASC
LIMIT 20;

-- [Phase 3] Tin tức gần đây
SELECT title, source, published_at FROM news_articles
ORDER BY published_at DESC LIMIT 20;

-- [Phase 3] Cảm xúc theo mã
SELECT na.title, ss.sentiment, ss.score, ss.reason
FROM sentiment_scores ss
JOIN news_articles na ON na.id = ss.article_id
WHERE ss.symbol = 'VNM'
ORDER BY ss.computed_at DESC;

-- [Phase 3] Top 10 cổ phiếu xếp hạng cao nhất
SELECT symbol, total_score, grade, rank,
       technical_score, fundamental_score, sentiment_score
FROM composite_scores
WHERE date = CURRENT_DATE
ORDER BY rank ASC
LIMIT 10;

-- [Phase 3] So sánh điểm các chiều
SELECT symbol, grade,
       ROUND(technical_score, 1) as tech,
       ROUND(fundamental_score, 1) as fund,
       ROUND(sentiment_score, 1) as sent,
       ROUND(total_score, 1) as total
FROM composite_scores
WHERE date = CURRENT_DATE
ORDER BY total_score DESC;
```

---

## 11. Kiểm thử

### Chạy tests

```bash
# Tất cả tests (147 tests — Phase 1 + Phase 2 + Phase 3)
uv run pytest

# Với output chi tiết
uv run pytest -v

# Chỉ Phase 1 tests (53 tests)
uv run pytest tests/test_crawlers/ tests/test_db/ tests/test_services/test_pipeline.py tests/test_services/test_price_adjuster.py -v

# Chỉ Phase 2 tests (45 tests)
uv run pytest tests/test_analysis/ tests/test_services/test_analysis_service.py -v

# Chỉ Phase 3 tests (49 tests)
uv run pytest tests/test_scoring/ tests/test_ai/ tests/test_services/test_news_service.py tests/test_services/test_sentiment_service.py tests/test_services/test_scoring_service.py tests/test_crawlers/test_news_crawler.py -v

# Chỉ chạy 1 file
uv run pytest tests/test_services/test_pipeline.py -v

# Chạy tests theo pattern
uv run pytest -k "test_price" -v

# Với coverage
uv run pytest --cov=src/localstock tests/
```

### Phân loại tests

**Phase 1 (53 tests):**

| Nhóm | Số lượng | Thư mục | Nội dung |
|------|----------|---------|----------|
| Crawlers | 23 | `tests/test_crawlers/` | PriceCrawler, FinanceCrawler, CompanyCrawler, EventCrawler |
| Database | 14 | `tests/test_db/` | StockRepository, PriceRepository (upsert, query) |
| Services | 16 | `tests/test_services/` | Pipeline orchestration, PriceAdjuster (splits, dividends) |

**Phase 2 (45 tests):**

| Nhóm | Số lượng | Thư mục | Nội dung |
|------|----------|---------|----------|
| Technical | 8 | `tests/test_analysis/test_technical.py` | TechnicalAnalyzer (pandas-ta indicators) |
| Trend | 9 | `tests/test_analysis/test_trend.py` | Trend detection, pivot points, S/R |
| Fundamental | 13 | `tests/test_analysis/test_fundamental.py` | FundamentalAnalyzer (ratios, growth, TTM) |
| Industry | 12 | `tests/test_analysis/test_industry.py` | IndustryAnalyzer (20 VN groups, ICB mapping) |
| Service | 3 | `tests/test_services/test_analysis_service.py` | AnalysisService orchestrator |

**Phase 3 (49 tests):**

| Nhóm | Số lượng | Thư mục | Nội dung |
|------|----------|---------|----------|
| Scoring | 25 | `tests/test_scoring/` | Normalizers, engine, config, grade |
| AI | 24 | `tests/test_ai/` | OllamaClient, prompts, sentiment pipeline |

### Cấu hình test (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"        # Tự động hỗ trợ async tests
testpaths = ["tests"]         # Thư mục tests
timeout = 30                  # Timeout 30 giây/test
```

> **Lưu ý:** Tất cả tests sử dụng mock — không cần kết nối DB hay internet.

---

## 12. Công cụ chất lượng code

### Ruff — Linting & Formatting

```bash
# Kiểm tra lỗi style
uv run ruff check src/ tests/

# Tự động sửa
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Mypy — Kiểm tra kiểu dữ liệu

```bash
uv run mypy src/localstock/
```

---

## 13. Bảng tổng hợp

| Chức năng | Lệnh | Yêu cầu | Kết quả |
|-----------|-------|----------|---------|
| **Cài đặt** | `uv sync` | Python ≥ 3.12 | Dependencies installed |
| **Migration** | `uv run alembic upgrade head` | `.env` configured | 13 bảng trong Supabase |
| **API Server** | `uv run uvicorn localstock.api.app:app --port 8000` | Migration done | FastAPI tại `:8000` |
| **Health Check** | `curl localhost:8000/health` | API running | JSON stats |
| **Pipeline Full** | `uv run python run_pipeline.py` | DB connected | Crawl ~400 mã HOSE |
| **Pipeline Single** | `uv run python run_single.py` | DB connected | Crawl 1 mã cụ thể |
| **Phân tích Full** | `curl -X POST localhost:8000/api/analysis/run` | Data đã crawl | Phân tích ~400 mã |
| **Technical** | `curl localhost:8000/api/analysis/VNM/technical` | Phân tích xong | Chỉ số kỹ thuật |
| **Fundamental** | `curl localhost:8000/api/analysis/VNM/fundamental` | Phân tích xong | Tỷ số tài chính |
| **Trend** | `curl localhost:8000/api/analysis/VNM/trend` | Phân tích xong | Xu hướng + S/R |
| **Industry** | `curl localhost:8000/api/industry/groups` | Phân tích xong | 20 nhóm ngành VN |
| **News Crawl** | `curl -X POST localhost:8000/api/news/crawl` | API running | Crawl tin tức RSS |
| **Sentiment** | `curl -X POST localhost:8000/api/sentiment/run` | Ollama + tin tức | Phân tích cảm xúc |
| **Scoring** | `curl -X POST localhost:8000/api/scores/run` | Phân tích xong | Chấm điểm ~400 mã |
| **Top Stocks** | `curl localhost:8000/api/scores/top?limit=20` | Chấm điểm xong | Top cổ phiếu |
| **Tests** | `uv run pytest -v` | Dev deps | 147 tests |
| **Lint** | `uv run ruff check src/` | ruff installed | Code issues |
| **Type Check** | `uv run mypy src/` | mypy installed | Type errors |

---

## Kiến trúc LocalStock (Phase 1 + Phase 2 + Phase 3)

```
localstock/
├── src/localstock/
│   ├── api/
│   │   ├── app.py              # FastAPI app factory
│   │   └── routes/
│   │       ├── health.py       # GET /health
│   │       ├── analysis.py     # 6 API phân tích (Phase 2)
│   │       ├── news.py         # 4 news/sentiment endpoints (Phase 3)
│   │       └── scores.py       # 3 scoring endpoints (Phase 3)
│   ├── config.py               # Pydantic Settings (.env loading)
│   ├── crawlers/               # Phase 1
│   │   ├── base.py             # BaseCrawler (fetch, fetch_batch)
│   │   ├── price_crawler.py    # OHLCV từ vnstock Quote API
│   │   ├── finance_crawler.py  # BCTC từ vnstock Finance API
│   │   ├── company_crawler.py  # Profile từ vnstock Company API
│   │   ├── event_crawler.py    # Sự kiện từ vnstock Company.events()
│   │   └── news_crawler.py     # CafeF + VnExpress RSS (Phase 3)
│   ├── ai/                     # Phase 3
│   │   ├── client.py           # OllamaClient (retry, health, structured output)
│   │   └── prompts.py          # Sentiment system prompt (Vietnamese)
│   ├── scoring/                # Phase 3
│   │   ├── __init__.py         # score_to_grade()
│   │   ├── config.py           # ScoringConfig (weights from settings)
│   │   ├── normalizer.py       # 3 normalizers (tech, fund, sentiment)
│   │   └── engine.py           # compute_composite() with weight redistribution
│   ├── analysis/               # Phase 2
│   │   ├── technical.py        # TechnicalAnalyzer (pandas-ta)
│   │   ├── trend.py            # detect_trend(), pivot_points(), S/R
│   │   ├── fundamental.py      # FundamentalAnalyzer (ratios, growth, TTM)
│   │   └── industry.py         # IndustryAnalyzer (20 VN groups, ICB mapping)
│   ├── db/
│   │   ├── database.py         # Engine, session factory, dependency
│   │   ├── models.py           # 13 ORM models (5 Phase 1 + 5 Phase 2 + 3 Phase 3)
│   │   └── repositories/
│   │       ├── stock_repo.py   # CRUD cho stocks
│   │       ├── price_repo.py   # Upsert giá, get_latest_date
│   │       ├── financial_repo.py # Upsert BCTC (JSON flexible)
│   │       ├── event_repo.py   # Upsert sự kiện, mark_processed
│   │       ├── indicator_repo.py # Bulk upsert technical indicators (Phase 2)
│   │       ├── ratio_repo.py   # Bulk upsert financial ratios (Phase 2)
│   │       └── industry_repo.py  # Groups, mappings, averages (Phase 2)
│   └── services/
│       ├── pipeline.py         # Orchestrator crawl (Phase 1)
│       ├── price_adjuster.py   # Điều chỉnh giá corporate actions (Phase 1)
│       ├── analysis_service.py # Orchestrator phân tích (Phase 2)
│       ├── news_service.py     # News crawl orchestrator (Phase 3)
│       ├── sentiment_service.py # LLM sentiment pipeline (Phase 3)
│       └── scoring_service.py  # Composite scoring pipeline (Phase 3)
├── alembic/                    # Database migrations
├── tests/                      # 147 unit tests (mock, no DB needed)
│   ├── test_crawlers/          # 23 tests — Phase 1
│   ├── test_db/                # 14 tests — Phase 1
│   ├── test_services/          # 19 tests — Phase 1 (16) + Phase 2 (3)
│   ├── test_analysis/          # 42 tests — Phase 2
│   ├── test_scoring/           # 25 tests — Phase 3
│   └── test_ai/                # 24 tests — Phase 3
├── docs/                       # Documentation
│   ├── phase1-usage.md         # Tài liệu tổng hợp (file này)
│   └── phase2-guide.md         # Hướng dẫn chi tiết Phase 2
├── .env                        # Biến môi trường (không commit)
└── pyproject.toml              # Dependencies & tool config
```
