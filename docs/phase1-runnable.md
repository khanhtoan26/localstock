# Phase 1 — Những gì có thể chạy

> Tài liệu tập trung vào **các tính năng chạy được** sau khi hoàn thành Phase 1 (Data Pipeline).
> Không cần Ollama, không cần Phase 2/3. Chỉ cần Supabase PostgreSQL + Internet.

---

## Yêu cầu tối thiểu

| Thành phần | Mô tả |
|-----------|-------|
| Python ≥ 3.12 | `python3 --version` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Supabase PostgreSQL | Tạo miễn phí tại [supabase.com](https://supabase.com) |
| Internet | Để gọi vnstock API lấy dữ liệu thị trường |

```bash
# Cài dependencies
cd localstock && uv sync
```

---

## Cấu hình

Tạo file `.env` tại thư mục gốc:

```env
# Bắt buộc — Supabase connection string
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# Cho Alembic migration (dùng driver sync)
DATABASE_URL_MIGRATION=postgresql://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres

# Tùy chọn
VNSTOCK_SOURCE=VCI              # Nguồn dữ liệu (VCI hoặc TCBS)
CRAWL_DELAY_SECONDS=1.0         # Delay giữa các request (tránh rate limit)
CRAWL_BATCH_SIZE=50             # Số mã crawl cùng lúc
LOG_LEVEL=INFO                  # DEBUG / INFO / WARNING / ERROR
```

---

## 1. Khởi tạo Database

```bash
# Chạy migration tạo schema (lần đầu tiên)
uv run alembic upgrade head
```

Schema Phase 1 gồm 5 bảng:
- `stocks` — Danh sách ~400 mã HOSE (symbol, tên, ngành, vốn hóa)
- `stock_prices` — Giá OHLCV hàng ngày (≥2 năm lịch sử)
- `financial_statements` — Báo cáo tài chính quý/năm (BCTC)
- `corporate_events` — Sự kiện doanh nghiệp (chia cổ tức, tách cổ phiếu...)
- `pipeline_runs` — Lịch sử chạy pipeline

---

## 2. Khởi động API Server

```bash
uv run uvicorn localstock.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Truy cập:
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

---

## 3. Chạy được gì?

### 3.1. Health Check

```bash
curl http://localhost:8000/api/health
```

```json
{
  "status": "healthy",
  "stocks": 0,
  "prices": 0,
  "last_pipeline_run": null
}
```

> Lần đầu chạy sẽ trả về `stocks: 0`, `prices: 0` vì chưa crawl dữ liệu.

---

### 3.2. Pipeline toàn bộ HOSE (~400 mã)

Đây là tính năng chính của Phase 1 — crawl toàn bộ dữ liệu thị trường:

```bash
# Chạy qua Python script
uv run python -c "
import asyncio
from localstock.db.database import async_session
from localstock.services.pipeline import Pipeline

async def main():
    async with async_session() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_full(run_type='daily')
        print(f'Status: {result.status}')
        print(f'Total: {result.symbols_total}')
        print(f'Success: {result.symbols_success}')
        print(f'Failed: {result.symbols_failed}')

asyncio.run(main())
"
```

**Pipeline chạy theo thứ tự:**
1. Fetch danh sách ~400 mã HOSE từ vnstock
2. Crawl giá OHLCV cho mỗi mã (incremental — chỉ lấy ngày mới)
3. Crawl báo cáo tài chính (bảng cân đối, kết quả KD, lưu chuyển tiền tệ)
4. Crawl thông tin công ty (ngành ICB, vốn hóa, cổ phiếu lưu hành)
5. Crawl sự kiện doanh nghiệp (chia cổ tức, tách cổ phiếu, phát hành)
6. Tự động điều chỉnh giá lịch sử khi có corporate actions

**Thời gian**: ~30-60 phút lần đầu (backfill 2 năm), ~5-10 phút cho daily update.

**Lưu ý**: Nếu bị rate limit, tăng `CRAWL_DELAY_SECONDS` lên 2.0 hoặc 3.0.

---

### 3.3. Pipeline cho 1 mã cụ thể

```bash
uv run python -c "
import asyncio
from localstock.db.database import async_session
from localstock.services.pipeline import Pipeline

async def main():
    async with async_session() as session:
        pipeline = Pipeline(session)
        result = await pipeline.run_single('ACB')
        print(result)

asyncio.run(main())
"
```

```json
{
  "symbol": "ACB",
  "status": "completed",
  "prices": 500,
  "financials": 3,
  "company": true,
  "events": 12,
  "errors": []
}
```

---

### 3.4. Chạy từng Crawler riêng lẻ

#### PriceCrawler — Giá OHLCV

```python
import asyncio
from localstock.crawlers.price_crawler import PriceCrawler

async def main():
    crawler = PriceCrawler()
    df = await crawler.fetch("VNM", start_date="2024-01-01", end_date="2024-12-31")
    print(df.head())
    print(f"Tổng: {len(df)} phiên giao dịch")

asyncio.run(main())
```

Cột trả về: `time`, `open`, `high`, `low`, `close`, `volume`, `ticker`

#### FinanceCrawler — Báo cáo tài chính

```python
import asyncio
from localstock.crawlers.finance_crawler import FinanceCrawler

async def main():
    crawler = FinanceCrawler()
    reports = await crawler.fetch("VNM")
    for report_type, df in reports.items():
        print(f"\n{report_type}: {len(df)} dòng")
        print(df.head(3))

asyncio.run(main())
```

Trả về 3 loại báo cáo: `balance_sheet`, `income_statement`, `cash_flow`

#### CompanyCrawler — Thông tin công ty

```python
import asyncio
from localstock.crawlers.company_crawler import CompanyCrawler

async def main():
    crawler = CompanyCrawler()
    df = await crawler.fetch("VNM")
    print(df.T)  # Transpose cho dễ đọc

asyncio.run(main())
```

Trả về: tên công ty, ngành ICB, vốn hóa, số cổ phiếu lưu hành, sàn, v.v.

#### EventCrawler — Sự kiện doanh nghiệp

```python
import asyncio
from localstock.crawlers.event_crawler import EventCrawler

async def main():
    crawler = EventCrawler()
    df = await crawler.fetch("VNM")
    print(df[["exright_date", "event_type", "ratio"]].head(10))

asyncio.run(main())
```

Trả về: ngày giao dịch không hưởng quyền, loại sự kiện, tỷ lệ điều chỉnh

#### Crawl hàng loạt (batch)

```python
import asyncio
from localstock.crawlers.price_crawler import PriceCrawler

async def main():
    crawler = PriceCrawler()
    results, failed = await crawler.fetch_batch(["ACB", "VNM", "FPT", "HPG"])
    print(f"Thành công: {len(results)}, Thất bại: {len(failed)}")
    for symbol, df in results.items():
        print(f"  {symbol}: {len(df)} phiên")

asyncio.run(main())
```

---

### 3.5. Truy vấn dữ liệu qua Repository

Sau khi crawl xong, có thể query dữ liệu qua Repository pattern:

```python
import asyncio
from localstock.db.database import async_session
from localstock.db.repositories.stock_repo import StockRepository
from localstock.db.repositories.price_repo import PriceRepository

async def main():
    async with async_session() as session:
        stock_repo = StockRepository(session)
        price_repo = PriceRepository(session)

        # Lấy danh sách tất cả mã HOSE
        symbols = await stock_repo.get_all_hose_symbols()
        print(f"Tổng mã HOSE: {len(symbols)}")

        # Lấy giá mới nhất của ACB
        latest = await price_repo.get_latest_date("ACB")
        print(f"ACB giá mới nhất đến: {latest}")

        # Lấy toàn bộ giá ACB
        prices = await price_repo.get_prices("ACB")
        print(f"ACB có {len(prices)} phiên giá")

asyncio.run(main())
```

Các Repository có sẵn (Phase 1):
| Repository | Dữ liệu | Phương thức chính |
|-----------|---------|-------------------|
| `StockRepository` | Danh sách cổ phiếu | `get_all_hose_symbols()`, `fetch_and_store_listings()` |
| `PriceRepository` | Giá OHLCV | `get_prices(symbol)`, `get_latest_date(symbol)`, `upsert_prices()` |
| `FinancialRepository` | Báo cáo tài chính | `upsert_statement()`, `get_statements(symbol)` |
| `EventRepository` | Sự kiện DN | `get_unprocessed_events()`, `upsert_events()`, `mark_processed()` |

---

### 3.6. Truy vấn SQL trực tiếp

Nếu dùng Supabase Dashboard hoặc `psql`:

```sql
-- Đếm tổng mã cổ phiếu
SELECT COUNT(*) FROM stocks;

-- Top 10 mã có vốn hóa lớn nhất
SELECT symbol, short_name, market_cap
FROM stocks
ORDER BY market_cap DESC NULLS LAST
LIMIT 10;

-- Giá đóng cửa 5 phiên gần nhất của VNM
SELECT date, close, volume
FROM stock_prices
WHERE symbol = 'VNM'
ORDER BY date DESC
LIMIT 5;

-- Báo cáo tài chính mới nhất của ACB
SELECT year, period, report_type
FROM financial_statements
WHERE symbol = 'ACB'
ORDER BY year DESC, period DESC
LIMIT 10;

-- Sự kiện chia cổ tức/tách cổ phiếu gần nhất
SELECT symbol, event_type, exright_date, ratio
FROM corporate_events
WHERE event_type IN ('split', 'stock_dividend', 'cash_dividend')
ORDER BY exright_date DESC
LIMIT 10;

-- Lịch sử chạy pipeline
SELECT id, status, run_type, started_at, symbols_total, symbols_success, symbols_failed
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 5;
```

---

### 3.7. Điều chỉnh giá (Price Adjustment)

Pipeline tự động điều chỉnh giá lịch sử khi phát hiện sự kiện chia tách. Hoặc chạy thủ công:

```python
import asyncio
from localstock.db.database import async_session
from localstock.services.pipeline import Pipeline

async def main():
    async with async_session() as session:
        pipeline = Pipeline(session)
        await pipeline._apply_price_adjustments()
        print("Điều chỉnh giá hoàn tất")

asyncio.run(main())
```

---

## 4. Chạy Tests

```bash
# Chạy tất cả tests (147 tests, tất cả mock-based, không cần DB)
uv run pytest

# Chỉ chạy tests Phase 1
uv run pytest tests/test_crawlers/ tests/test_db/ tests/test_services/test_pipeline.py -v

# Chạy test cho 1 module cụ thể
uv run pytest tests/test_crawlers/test_price_crawler.py -v

# Với coverage
uv run pytest tests/test_crawlers/ --tb=short
```

---

## 5. Linting & Formatting

```bash
# Kiểm tra code style
uv run ruff check src/ tests/

# Tự động sửa lỗi
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/
```

---

## Bảng tổng hợp Phase 1

| Tính năng | Lệnh / Cách chạy | Ghi chú |
|-----------|------------------|---------|
| Health check | `curl localhost:8000/api/health` | Kiểm tra DB connection + data stats |
| Pipeline toàn bộ | `Pipeline(session).run_full()` | ~400 mã, 30-60 phút lần đầu |
| Pipeline 1 mã | `Pipeline(session).run_single("ACB")` | Nhanh, ~30 giây |
| Crawl giá OHLCV | `PriceCrawler().fetch("VNM")` | Incremental, ≥2 năm backfill |
| Crawl tài chính | `FinanceCrawler().fetch("VNM")` | 3 loại báo cáo |
| Crawl công ty | `CompanyCrawler().fetch("VNM")` | Ngành ICB, vốn hóa |
| Crawl sự kiện | `EventCrawler().fetch("VNM")` | Chia cổ tức, tách CP |
| Crawl hàng loạt | `PriceCrawler().fetch_batch([...])` | Tự xử lý lỗi |
| Điều chỉnh giá | Tự động trong pipeline | Split, stock dividend |
| Query dữ liệu | Repository pattern hoặc SQL | Xem mục 3.5, 3.6 |
| Tests | `uv run pytest` | 147 tests, mock-based |
| Linting | `uv run ruff check src/` | Ruff linter |

---

## Kiến trúc Phase 1

```
localstock/
├── api/
│   ├── app.py                 # FastAPI app
│   └── routes/
│       └── health.py          # GET /api/health
├── config.py                  # Settings từ .env
├── crawlers/
│   ├── base.py                # BaseCrawler (fetch_batch, delay)
│   ├── price_crawler.py       # OHLCV từ vnstock
│   ├── finance_crawler.py     # BCTC từ vnstock
│   ├── company_crawler.py     # Thông tin công ty
│   └── event_crawler.py       # Corporate events
├── db/
│   ├── database.py            # AsyncSession factory
│   ├── models.py              # 5 ORM models (Phase 1)
│   └── repositories/
│       ├── stock_repo.py      # Stocks CRUD
│       ├── price_repo.py      # Prices CRUD
│       ├── financial_repo.py  # Financials CRUD
│       └── event_repo.py      # Events CRUD
└── services/
    ├── pipeline.py            # Pipeline orchestrator
    └── price_adjuster.py      # Điều chỉnh giá corporate actions
```

---

*Phase 1 hoàn thành: 5 requirements (DATA-01 → DATA-05) ✅*
*Dữ liệu nền tảng cho Phase 2 (phân tích) và Phase 3 (sentiment + scoring)*
