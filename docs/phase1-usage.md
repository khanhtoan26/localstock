# Phase 1: Foundation & Data Pipeline — Hướng dẫn sử dụng

> Tài liệu này mô tả tất cả những gì có thể chạy sau khi hoàn thành Phase 1.
> Cập nhật: 2026-04-15

---

## Mục lục

1. [Yêu cầu cài đặt](#1-yêu-cầu-cài-đặt)
2. [Cấu hình môi trường](#2-cấu-hình-môi-trường)
3. [Khởi tạo database](#3-khởi-tạo-database)
4. [API Server](#4-api-server)
5. [Chạy pipeline thu thập dữ liệu](#5-chạy-pipeline-thu-thập-dữ-liệu)
6. [Crawlers riêng lẻ](#6-crawlers-riêng-lẻ)
7. [Truy vấn dữ liệu](#7-truy-vấn-dữ-liệu)
8. [Kiểm thử](#8-kiểm-thử)
9. [Công cụ chất lượng code](#9-công-cụ-chất-lượng-code)
10. [Bảng tổng hợp](#10-bảng-tổng-hợp)

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
```

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `DATABASE_URL` | ✅ | Connection string async (asyncpg) cho ứng dụng |
| `DATABASE_URL_MIGRATION` | ❌ | Connection string cho Alembic migration (mặc định dùng DATABASE_URL) |
| `VNSTOCK_SOURCE` | ❌ | `VCI` (mặc định) hoặc `KBS` |
| `CRAWL_DELAY_SECONDS` | ❌ | Delay giữa requests, mặc định `1.0` giây |
| `LOG_LEVEL` | ❌ | Mức log, mặc định `INFO` |

> **Lưu ý SSL:** Nếu mạng có proxy/firewall chặn SSL, thêm biến môi trường:
> ```bash
> export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
> export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
> ```

---

## 3. Khởi tạo database

### Tạo schema (lần đầu)

```bash
# Áp dụng migration — tạo 5 bảng trong Supabase
uv run alembic upgrade head
```

Các bảng được tạo:

| Bảng | Mô tả | Khóa chính |
|------|--------|------------|
| `stocks` | Thông tin mã cổ phiếu (tên, sàn, ngành ICB) | `symbol` |
| `stock_prices` | Dữ liệu giá OHLCV hàng ngày | `id`, unique `(symbol, date)` |
| `financial_statements` | Báo cáo tài chính (JSON linh hoạt) | `id`, unique `(symbol, year, period, report_type)` |
| `corporate_events` | Sự kiện doanh nghiệp (chia tách, cổ tức) | `id`, unique `(symbol, exright_date, event_type)` |
| `pipeline_runs` | Lịch sử chạy pipeline | `id` |

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

## 7. Truy vấn dữ liệu

### 7.1. Qua Repository (trong code Python)

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

    await engine.dispose()

asyncio.run(main())
```

### 7.2. Qua SQL trực tiếp (Supabase Dashboard hoặc psql)

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
```

---

## 8. Kiểm thử

### Chạy tests

```bash
# Tất cả tests (53 tests)
uv run pytest

# Với output chi tiết
uv run pytest -v

# Chỉ chạy 1 file
uv run pytest tests/test_services/test_pipeline.py -v

# Chạy tests theo pattern
uv run pytest -k "test_price" -v

# Với coverage
uv run pytest --cov=src/localstock tests/
```

### Phân loại tests

| Nhóm | Số lượng | Thư mục | Nội dung |
|------|----------|---------|----------|
| Crawlers | 23 | `tests/test_crawlers/` | PriceCrawler, FinanceCrawler, CompanyCrawler, EventCrawler |
| Database | 14 | `tests/test_db/` | StockRepository, PriceRepository (upsert, query) |
| Services | 16 | `tests/test_services/` | Pipeline orchestration, PriceAdjuster (splits, dividends) |

### Cấu hình test (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"        # Tự động hỗ trợ async tests
testpaths = ["tests"]         # Thư mục tests
timeout = 30                  # Timeout 30 giây/test
```

> **Lưu ý:** Tất cả tests sử dụng mock — không cần kết nối DB hay internet.

---

## 9. Công cụ chất lượng code

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

## 10. Bảng tổng hợp

| Chức năng | Lệnh | Yêu cầu | Kết quả |
|-----------|-------|----------|---------|
| **Cài đặt** | `uv sync` | Python ≥ 3.12 | Dependencies installed |
| **Migration** | `uv run alembic upgrade head` | `.env` configured | 5 bảng trong Supabase |
| **API Server** | `uv run uvicorn localstock.api.app:app --port 8000` | Migration done | FastAPI tại `:8000` |
| **Health Check** | `curl localhost:8000/health` | API running | JSON stats |
| **Pipeline Full** | `uv run python run_pipeline.py` | DB connected | Crawl ~400 mã HOSE |
| **Pipeline Single** | `uv run python run_single.py` | DB connected | Crawl 1 mã cụ thể |
| **Tests** | `uv run pytest -v` | Dev deps | 53 tests |
| **Lint** | `uv run ruff check src/` | ruff installed | Code issues |
| **Type Check** | `uv run mypy src/` | mypy installed | Type errors |

---

## Kiến trúc Phase 1

```
localstock/
├── src/localstock/
│   ├── api/
│   │   ├── app.py              # FastAPI app factory
│   │   └── routes/
│   │       └── health.py       # GET /health
│   ├── config.py               # Pydantic Settings (.env loading)
│   ├── crawlers/
│   │   ├── base.py             # BaseCrawler (fetch, fetch_batch)
│   │   ├── price_crawler.py    # OHLCV từ vnstock Quote API
│   │   ├── finance_crawler.py  # BCTC từ vnstock Finance API
│   │   ├── company_crawler.py  # Profile từ vnstock Company API
│   │   └── event_crawler.py    # Sự kiện từ vnstock Company.events()
│   ├── db/
│   │   ├── database.py         # Engine, session factory, dependency
│   │   ├── models.py           # 5 ORM models (Stock, StockPrice, ...)
│   │   └── repositories/
│   │       ├── stock_repo.py   # CRUD cho stocks
│   │       ├── price_repo.py   # Upsert giá, get_latest_date
│   │       ├── financial_repo.py # Upsert BCTC (JSON flexible)
│   │       └── event_repo.py   # Upsert sự kiện, mark_processed
│   └── services/
│       ├── pipeline.py         # Orchestrator (run_full, run_single)
│       └── price_adjuster.py   # Điều chỉnh giá cho corporate actions
├── alembic/                    # Database migrations
├── tests/                      # 53 unit tests (mock, no DB needed)
├── .env                        # Biến môi trường (không commit)
└── pyproject.toml              # Dependencies & tool config
```
