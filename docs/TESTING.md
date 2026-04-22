<!-- generated-by: gsd-doc-writer -->

# Testing

Hướng dẫn kiểm thử cho dự án LocalStock — bao gồm backend Python (Prometheus) và frontend Next.js (Helios).

## Tổng quan Test Framework

### Backend (Prometheus)

| Công cụ | Phiên bản | Mục đích |
|---|---|---|
| **pytest** | `>=8.0` | Framework kiểm thử chính |
| **pytest-asyncio** | `>=0.24` | Hỗ trợ test async (`asyncio_mode = "auto"`) |
| **pytest-timeout** | `>=2.0` | Timeout 30s cho mỗi test case |

Cấu hình nằm trong `apps/prometheus/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
timeout = 30
```

- **`asyncio_mode = "auto"`** — Các hàm `async def test_...()` tự động được nhận diện là async test, **không cần decorator** `@pytest.mark.asyncio`.
- **`timeout = 30`** — Mỗi test tối đa 30 giây, giúp phát hiện deadlock hoặc hang.

### Frontend (Helios)

| Công cụ | Phiên bản | Mục đích |
|---|---|---|
| **Playwright** | `>=1.59` | E2E testing trên trình duyệt |
| **Vitest** | `>=4.1` | Unit testing (cấu hình sẵn, chưa có test files) |
| **ESLint** | `>=9` | Lint kiểm tra code style |

Cấu hình Playwright trong `apps/helios/playwright.config.ts`:

```typescript
{
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: undefined, // Server phải chạy sẵn trước khi test
}
```

## Chạy test

### Backend — Toàn bộ test suite

```bash
# Chạy tất cả tests (353+ test functions, từ thư mục gốc workspace)
uv run pytest

# Chạy với output chi tiết
uv run pytest -v

# Chạy với coverage report
uv run pytest --cov=localstock
```

### Backend — Chạy test cụ thể

```bash
# Chạy một thư mục test
uv run pytest tests/test_services/

# Chạy một file test cụ thể
uv run pytest tests/test_services/test_analysis_service.py

# Chạy một test function cụ thể
uv run pytest tests/test_services/test_analysis_service.py::test_calculate_rsi

# Chạy một test class cụ thể
uv run pytest tests/test_scoring/test_engine.py::TestCompositeScoring

# Chạy test khớp keyword
uv run pytest -k "rsi"
```

### Frontend — E2E tests

```bash
# Cài Playwright browsers (lần đầu)
cd apps/helios && npx playwright install

# Chạy E2E tests (cần dev server đang chạy trên port 3000)
cd apps/helios && npx playwright test

# Chạy với UI mode
cd apps/helios && npx playwright test --ui

# Xem test report
cd apps/helios && npx playwright show-report
```

> **Lưu ý:** Playwright yêu cầu frontend dev server (`npm run dev`) chạy sẵn tại `http://localhost:3000` trước khi chạy E2E test. Backend API server cũng cần chạy tại `http://localhost:8000` để frontend fetch dữ liệu.

### Frontend — Lint & Build check

```bash
# Lint kiểm tra code style
cd apps/helios && npm run lint

# Build check (đảm bảo TypeScript compile thành công)
cd apps/helios && npx next build
```

## Cấu trúc thư mục test

### Backend (`apps/prometheus/tests/`)

Cấu trúc test mirror theo `src/localstock/`:

```
tests/
├── conftest.py                     # Shared fixtures (sample_ohlcv_df, sample_company_overview, ...)
├── test_admin.py                   # Admin API routes & request models
├── test_api_dashboard.py           # Dashboard API, CORS middleware, prices router
├── test_ai/
│   └── test_client.py              # OllamaClient, SentimentResult model
├── test_analysis/
│   ├── test_fundamental.py         # Phân tích cơ bản
│   ├── test_industry.py            # Phân tích ngành
│   ├── test_sentiment.py           # Phân tích tâm lý thị trường
│   ├── test_technical.py           # Chỉ báo kỹ thuật (SMA, EMA, RSI, MACD, BB, ...)
│   └── test_trend.py               # Phát hiện xu hướng
├── test_crawlers/
│   ├── test_company_crawler.py     # Crawl thông tin doanh nghiệp
│   ├── test_finance_crawler.py     # Crawl dữ liệu tài chính
│   ├── test_news_crawler.py        # Crawl tin tức
│   └── test_price_crawler.py       # Crawl giá OHLCV từ vnstock
├── test_db/
│   ├── test_models_phase4.py       # SQLAlchemy ORM models
│   ├── test_price_repo.py          # Price repository
│   └── test_stock_repo.py          # Stock repository
├── test_macro/
│   ├── test_crawler.py             # Crawl dữ liệu vĩ mô (VCB exchange rates)
│   ├── test_impact.py              # Phân tích tác động vĩ mô
│   └── test_scorer.py              # Chấm điểm vĩ mô
├── test_notifications/
│   ├── test_formatters.py          # Format tin nhắn Telegram
│   └── test_telegram.py            # TelegramNotifier send/config
├── test_phase5/
│   └── test_task1.py               # Feature-specific tests
├── test_reports/
│   ├── test_generator.py           # ReportDataBuilder, prompts, StockReport model
│   └── test_t3.py                  # T+3 report logic
├── test_scheduler/
│   └── test_calendar.py            # Lịch giao dịch (trading calendar)
├── test_scoring/
│   ├── test_engine.py              # Composite scoring engine
│   └── test_normalizer.py          # Score normalization
└── test_services/
    ├── test_analysis_service.py    # AnalysisService orchestration
    ├── test_automation_service.py  # Automation pipeline service
    ├── test_pipeline.py            # Pipeline end-to-end flow
    ├── test_price_adjuster.py      # Điều chỉnh giá
    ├── test_report_service.py      # Report generation service
    ├── test_score_changes.py       # Score change tracking
    └── test_sector_rotation.py     # Sector rotation analysis
```

**Tổng cộng:** 33 test files, 353+ test functions (bao gồm 75+ async tests).

### Frontend (`apps/helios/e2e/`)

```
e2e/
└── app.spec.ts     # 19 E2E test cases, 10 test groups
```

Các trang được test E2E: Homepage (`/`), Rankings (`/rankings`), Market (`/market`), Stock Detail (`/stock/VNM`), Learn Hub (`/learn`), Learn Categories (`/learn/technical`, `/learn/fundamental`, `/learn/macro`), 404 Page, Navigation, Theme Toggle, Console Errors.

## Viết test mới

### Quy ước đặt tên file

- **Backend:** `test_<module>.py` trong thư mục tương ứng (ví dụ: `tests/test_services/test_my_service.py`)
- **Frontend E2E:** `<feature>.spec.ts` trong `apps/helios/e2e/`

### Pattern cho async test (Backend)

Nhờ `asyncio_mode = "auto"`, chỉ cần khai báo `async def` — **không cần decorator**:

```python
# ✅ Đúng — tự động nhận diện async
async def test_fetch_returns_data(mock_settings, mock_kbs_quote):
    crawler = PriceCrawler(delay_seconds=0)
    df = await crawler.fetch("ACB", start_date="2024-01-01", end_date="2024-01-04")
    assert not df.empty
    assert "close" in df.columns

# ✅ Đúng — sync test vẫn hoạt động bình thường
def test_router_has_correct_prefix():
    assert admin_router.prefix == "/api/admin"
```

### Pattern cho mock external services

Dự án mock tất cả external dependencies (Ollama, vnstock, Telegram, HTTP calls):

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock vnstock API
@pytest.fixture
def mock_kbs_quote(sample_ohlcv_df):
    with patch("vnstock.explorer.kbs.quote.Quote") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_ohlcv_df
        mock_cls.return_value = mock_instance
        yield mock_cls

# Mock Telegram Bot
@patch("localstock.notifications.telegram.Bot")
async def test_send_message_calls_bot(self, MockBot):
    mock_bot = AsyncMock()
    MockBot.return_value = mock_bot
    notifier = TelegramNotifier(bot_token="tok123", chat_id="chat456")
    notifier._bot = mock_bot
    result = await notifier.send_message("<b>Hello</b>")
    assert result is True

# Mock HTTP client (httpx)
mock_response = AsyncMock()
mock_response.status_code = 200
mock_response.text = VCB_XML_VALID
```

### Sử dụng shared fixtures

File `tests/conftest.py` cung cấp các fixture dùng chung:

| Fixture | Mô tả |
|---|---|
| `sample_ohlcv_df` | DataFrame OHLCV 3 ngày (format vnstock Quote.history()) |
| `sample_company_overview` | DataFrame thông tin doanh nghiệp (ACB) |
| `sample_corporate_events` | DataFrame sự kiện doanh nghiệp |
| `sample_financial_data` | Dict chứa balance_sheet & income_statement |

Ngoài ra, các file test riêng tạo thêm fixtures cụ thể, ví dụ `ohlcv_250` (250 ngày dữ liệu cho test kỹ thuật), `mock_session` (mock AsyncSession cho DB tests).

### Pattern cho test class

```python
class TestCompositeScoring:
    """Test compute_composite với nhiều tổ hợp dimension."""

    def test_composite_all_dimensions(self, default_config):
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=70.0, sent=60.0, macro=None,
            config=default_config,
        )
        assert total == pytest.approx(70.5)
        assert grade == "B"
        assert dims == 3
```

## Coverage

### Backend

Chạy coverage report:

```bash
# Coverage report dạng terminal
uv run pytest --cov=localstock

# Coverage report dạng HTML
uv run pytest --cov=localstock --cov-report=html

# Coverage với chi tiết từng file
uv run pytest --cov=localstock --cov-report=term-missing
```

> **Lưu ý:** Hiện tại chưa cấu hình coverage threshold tối thiểu trong `pyproject.toml`. Coverage report được tạo theo yêu cầu (on-demand).

### Frontend

Vitest đã được cấu hình trong `apps/helios/vitest.config.ts` nhưng chưa có test files. Khi thêm unit test cho frontend:

```bash
cd apps/helios && npx vitest
cd apps/helios && npx vitest --coverage
```

## CI Integration

Hiện tại dự án **chưa có CI/CD pipeline** (không có `.github/workflows/`). Tests được chạy thủ công trong quá trình phát triển.

**Quy trình kiểm thử khuyến nghị trước khi commit:**

1. Chạy toàn bộ backend tests: `uv run pytest`
2. Chạy lint backend: `uv run ruff check src/ tests/`
3. Chạy lint frontend: `cd apps/helios && npm run lint`
4. Build check frontend: `cd apps/helios && npx next build`
5. (Tùy chọn) Chạy E2E tests nếu thay đổi frontend: `cd apps/helios && npx playwright test`

## Xem thêm

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Kiến trúc hệ thống và các component
- [CONFIGURATION.md](./CONFIGURATION.md) — Biến môi trường và cấu hình
- [SETUP.md](./SETUP.md) — Hướng dẫn cài đặt ban đầu
