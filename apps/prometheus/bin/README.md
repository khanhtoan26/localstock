# LocalStock — CLI Scripts & API Reference

## CLI Scripts

Tất cả scripts chạy bằng `uv run python bin/<script>`.

### Khởi tạo

| Script       | Lệnh                           | Mô tả                                       |
| ------------ | ------------------------------ | ------------------------------------------- |
| `init_db.py` | `uv run python bin/init_db.py` | Khởi tạo DB schema, chạy Alembic migrations |

### Crawl dữ liệu

| Script            | Lệnh                                                      | Mô tả                                                                                       |
| ----------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `crawl_single.py` | `uv run python bin/crawl_single.py <SYMBOL>`              | Crawl 1 mã (giá, BCTC, profile, events)                                                     |
| `crawl_all.py`    | `uv run python bin/crawl_all.py [--type daily\|backfill]` | Crawl ~400 mã HOSE. `backfill` cho lần đầu (~30-60 phút), `daily` cho cập nhật (~5-10 phút) |

### Phân tích & Chấm điểm

| Script             | Lệnh                                         | Mô tả                                                                                     |
| ------------------ | -------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `run_analysis.py`  | `uv run python bin/run_analysis.py`          | Tính 40+ chỉ báo kỹ thuật (SMA, RSI, MACD, BB...) + chỉ số cơ bản (P/E, ROE, D/E...)      |
| `run_sentiment.py` | `uv run python bin/run_sentiment.py`         | Crawl tin tức (CafeF, VnExpress) + phân tích sentiment qua Ollama LLM                     |
| `run_scoring.py`   | `uv run python bin/run_scoring.py`           | Chấm điểm tổng hợp 4 chiều (kỹ thuật 30%, cơ bản 30%, sentiment 20%, vĩ mô 20%), xếp hạng |
| `run_reports.py`   | `uv run python bin/run_reports.py [--top N]` | Tạo báo cáo AI tiếng Việt cho top N mã (mặc định: 10)                                     |

### Pipeline tổng hợp

| Script             | Lệnh                                              | Mô tả                                                                                                     |
| ------------------ | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **`run_daily.py`** | `uv run python bin/run_daily.py [--skip-reports]` | **Master pipeline** — chạy tuần tự: crawl → analysis → news → sentiment → scoring → reports (~10-15 phút) |

### Thứ tự chạy (nếu chạy từng bước)

```
crawl_all.py → run_analysis.py → run_sentiment.py → run_scoring.py → run_reports.py
```

Mỗi bước phụ thuộc vào output bước trước. `run_daily.py` tự động chạy đúng thứ tự.

---

## API Server

### Khởi động

```bash
uv run uvicorn localstock.api.app:create_app --factory --reload --port 8000
```

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### Health

| Method | Endpoint  | Mô tả                                                     |
| ------ | --------- | --------------------------------------------------------- |
| GET    | `/health` | Trạng thái hệ thống, số mã, số giá, pipeline run gần nhất |

#### Analysis (`/api/analysis`)

| Method | Endpoint                              | Mô tả                                                            |
| ------ | ------------------------------------- | ---------------------------------------------------------------- |
| GET    | `/api/analysis/{symbol}/technical`    | Chỉ báo kỹ thuật (SMA, EMA, RSI, MACD, BB, Stochastic, ADX, OBV) |
| GET    | `/api/analysis/{symbol}/fundamental`  | Chỉ số cơ bản (P/E, P/B, EPS, ROE, ROA, D/E, growth)             |
| GET    | `/api/analysis/{symbol}/trend`        | Xu hướng + mức hỗ trợ/kháng cự                                   |
| POST   | `/api/analysis/run`                   | Kích hoạt phân tích toàn bộ ~400 mã                              |
| GET    | `/api/industry/groups`                | Danh sách 20 nhóm ngành Việt Nam                                 |
| GET    | `/api/industry/{group_code}/averages` | Trung bình ngành theo nhóm (param: `year`, `period`)             |

#### News & Sentiment (`/api/news`)

| Method | Endpoint                       | Mô tả                                               |
| ------ | ------------------------------ | --------------------------------------------------- |
| GET    | `/api/news`                    | Tin tức gần đây (param: `days` 1-30, `limit` 1-200) |
| GET    | `/api/news/{symbol}/sentiment` | Điểm sentiment theo mã (param: `days` 1-30)         |
| POST   | `/api/news/crawl`              | Kích hoạt crawl tin tức RSS                         |
| POST   | `/api/sentiment/run`           | Kích hoạt phân tích sentiment qua LLM               |

#### Scores (`/api/scores`)

| Method | Endpoint               | Mô tả                                            |
| ------ | ---------------------- | ------------------------------------------------ |
| GET    | `/api/scores/top`      | Top mã theo điểm tổng hợp (param: `limit` 1-100) |
| GET    | `/api/scores/{symbol}` | Điểm tổng hợp 1 mã                               |
| POST   | `/api/scores/run`      | Kích hoạt scoring pipeline                       |

#### Reports (`/api/reports`)

| Method | Endpoint                | Mô tả                                          |
| ------ | ----------------------- | ---------------------------------------------- |
| GET    | `/api/reports/top`      | Báo cáo AI cho top mã (param: `limit` 1-100)   |
| GET    | `/api/reports/{symbol}` | Báo cáo AI cho 1 mã                            |
| POST   | `/api/reports/run`      | Tạo báo cáo cho top N mã (param: `top_n` 1-50) |

#### Macro (`/api/macro`)

| Method | Endpoint                         | Mô tả                                              |
| ------ | -------------------------------- | -------------------------------------------------- |
| GET    | `/api/macro/latest`              | Chỉ số vĩ mô mới nhất (lãi suất, tỷ giá, CPI, GDP) |
| POST   | `/api/macro`                     | Nhập chỉ số vĩ mô thủ công                         |
| POST   | `/api/macro/fetch-exchange-rate` | Lấy tỷ giá USD/VND từ VCB                          |

---

## Yêu cầu

- **Python 3.12+** với `uv` package manager
- **PostgreSQL** (Supabase) — cấu hình qua `DATABASE_URL` trong `.env`
- **Ollama** đang chạy tại `http://localhost:11434` với model `qwen2.5:14b-instruct-q4_K_M` (cho sentiment + reports)

## Cấu hình

Sao chép `.env.example` → `.env` và chỉnh sửa:

```env
DATABASE_URL=postgresql+asyncpg://...        # Supabase connection
OLLAMA_HOST=http://localhost:11434            # Ollama server
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M    # LLM model
SCORING_WEIGHT_TECHNICAL=0.30                # Trọng số kỹ thuật
SCORING_WEIGHT_FUNDAMENTAL=0.30              # Trọng số cơ bản
SCORING_WEIGHT_SENTIMENT=0.20                # Trọng số sentiment
SCORING_WEIGHT_MACRO=0.20                    # Trọng số vĩ mô
```

## Quick Start

```bash
# 1. Setup
cp .env.example .env    # Chỉnh sửa credentials
uv sync                 # Cài dependencies

# 2. Khởi tạo DB
uv run python bin/init_db.py

# 3. Chạy full pipeline
uv run python bin/run_daily.py

# 4. Xem kết quả qua API
uv run uvicorn localstock.api.app:create_app --factory --reload --port 8000
# Mở http://localhost:8000/docs
```

Đây là tổng hợp tất cả những gì đã build qua 4 phases:

---

🚀 CLI Scripts (8 scripts trong bin/)

┌────────────────────┬──────────────────────────────────────────────────────────┬──────────────────────────────────────────────────┐
│ Script │ Lệnh │ Mô tả │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ init_db.py │ uv run python bin/init_db.py │ Khởi tạo DB, chạy migrations │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ crawl_single.py │ uv run python bin/crawl_single.py ACB │ Crawl 1 mã cổ phiếu │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ crawl_all.py │ uv run python bin/crawl_all.py [--type daily|backfill] │ Crawl ~400 mã HOSE │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ run_analysis.py │ uv run python bin/run_analysis.py │ Tính technical + fundamental │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ run_sentiment.py │ uv run python bin/run_sentiment.py │ Crawl tin tức + phân tích sentiment (cần Ollama) │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ run_scoring.py │ uv run python bin/run_scoring.py │ Chấm điểm tổng hợp + xếp hạng │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ run_reports.py │ uv run python bin/run_reports.py [--top N] │ Tạo báo cáo AI (cần Ollama) │
├────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
│ run_daily.py │ uv run python bin/run_daily.py [--skip-reports] │ Pipeline đầy đủ (tất cả bước trên) │
└────────────────────┴──────────────────────────────────────────────────────────┴──────────────────────────────────────────────────┘

🌐 API Server (15+ endpoints)

# Khởi động server

uv run uvicorn localstock.api.app:create_app --factory --reload --port 8000

# Swagger UI: http://localhost:8000/docs

┌──────────────┬────────────────────────────────────────────────────────────────────────────────────┐
│ Nhóm │ Endpoints chính │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ Health │ GET /health │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ Analysis │ GET /api/analysis/{symbol}/technical|fundamental|trend, POST /api/analysis/run │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ News │ GET /api/news, GET /api/news/{symbol}/sentiment, POST /api/news/crawl │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ Scores │ GET /api/scores/top, GET /api/scores/{symbol}, POST /api/scores/run │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ Reports │ GET /api/reports/top, GET /api/reports/{symbol}, POST /api/reports/run │
├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ Macro │ GET /api/macro/latest, POST /api/macro/fetch-exchange-rate │
└──────────────┴────────────────────────────────────────────────────────────────────────────────────┘

⚡ Quick Start

# Option A: Chạy toàn bộ pipeline 1 lệnh

uv run python bin/run_daily.py

# Option B: Từng bước

uv run python bin/crawl_all.py # 1. Crawl data
uv run python bin/run_analysis.py # 2. Phân tích kỹ thuật + cơ bản
uv run python bin/run_sentiment.py # 3. Tin tức + sentiment (cần Ollama)
uv run python bin/run_scoring.py # 4. Chấm điểm + xếp hạng
uv run python bin/run_reports.py # 5. Tạo báo cáo AI (cần Ollama)

Yêu cầu: PostgreSQL (Supabase), Ollama đang chạy với model qwen2.5:14b-instruct-q4_K_M.
