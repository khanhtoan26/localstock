# LocalStock

**AI Stock Agent cho thị trường chứng khoán Việt Nam (HOSE)**

LocalStock là một AI agent cá nhân tự động phân tích ~400 mã cổ phiếu trên sàn HOSE. Hệ thống crawl dữ liệu hàng ngày, phân tích đa chiều (kỹ thuật, cơ bản, sentiment, vĩ mô), xếp hạng và đưa ra gợi ý mã đáng mua kèm báo cáo tiếng Việt chi tiết — tất cả chạy local, miễn phí.

## Tính năng chính

- 📊 **Data Pipeline** — Crawl OHLCV, BCTC, corporate actions cho ~400 mã HOSE
- 📈 **Technical Analysis** — 11 chỉ báo (SMA, EMA, RSI, MACD, Bollinger Bands, ...)
- 💰 **Fundamental Analysis** — P/E, P/B, ROE, ROA, D/E + so sánh ngành ICB
- 📰 **Sentiment Analysis** — Crawl tin tức tài chính, phân loại sentiment bằng LLM local
- 🏦 **Macro Analysis** — Lãi suất, tỷ giá USD/VND, CPI, GDP + tác động theo ngành
- 🤖 **AI Scoring** — Chấm điểm tổng hợp 0-100, trọng số tùy chỉnh
- 📝 **AI Reports** — Báo cáo tiếng Việt giải thích TẠI SAO mã đáng mua/bán
- ⏰ **Automation** — Pipeline chạy tự động hàng ngày sau phiên (15:45)
- 📱 **Telegram Bot** — Gửi alert khi có gợi ý tốt hoặc biến động lớn
- 🖥️ **Web Dashboard** — Bảng xếp hạng, biểu đồ nến, phân tích sector

## Quick Start

### Yêu cầu

- Python 3.12+
- Node.js 18+
- PostgreSQL (Supabase free tier)
- Ollama + GPU (RTX 3060 12GB trở lên khuyến nghị)

### 1. Clone & cài đặt

```bash
git clone https://github.com/khanhtoan26/localstock.git
cd localstock

# Cài uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài Python dependencies
uv sync
```

### 2. Cấu hình

```bash
cp .env.example .env
# Sửa .env với thông tin Supabase của bạn
```

Xem [docs/SETUP.md](docs/SETUP.md) để biết chi tiết cấu hình từng service.

### 3. Database

```bash
# Chạy migrations (BẮT BUỘC trước khi chạy backend)
uv run alembic upgrade head
```

### 4. Khởi động

```bash
# Terminal 1: Backend API (port 8000)
uv run uvicorn localstock.api.app:app --reload

# Terminal 2: Frontend (port 3000)
cd web && npm install && npm run dev

# Terminal 3: Ollama LLM (nếu cần AI features)
ollama serve
ollama pull qwen2.5:14b-instruct-q4_K_M
```

### 5. Sử dụng

- 🌐 **Dashboard:** http://localhost:3000
- 📡 **API:** http://localhost:8000
- 📖 **API Docs:** http://localhost:8000/docs (Swagger UI)

Để chạy pipeline lần đầu:
```bash
# Trigger toàn bộ pipeline (crawl → analyze → score → report → notify)
curl -X POST http://localhost:8000/api/automation/run
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| **Database** | PostgreSQL (Supabase), Alembic migrations |
| **Data** | vnstock 3.5.1, pandas, pandas-ta |
| **AI/LLM** | Ollama (qwen2.5:14b), structured JSON output |
| **Frontend** | Next.js 16, React 19, TypeScript 5 |
| **UI** | Tailwind CSS 4, shadcn/ui, lightweight-charts v5 |
| **Automation** | APScheduler (CronTrigger) |
| **Notifications** | python-telegram-bot |

## Tài liệu

- [**SETUP.md**](docs/SETUP.md) — Hướng dẫn cài đặt chi tiết
- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) — Kiến trúc, workflow, giải thích toàn bộ codebase
- [**API.md**](docs/API.md) — Tài liệu API endpoints

## Cấu trúc dự án

```
localstock/
├── src/localstock/           # Backend Python
│   ├── api/routes/           # FastAPI endpoints (9 routers, ~30 routes)
│   ├── ai/                   # Ollama LLM client & prompts
│   ├── crawlers/             # Data crawlers (price, finance, news)
│   ├── db/                   # SQLAlchemy models & repositories
│   ├── services/             # Business logic (scoring, analysis, reports)
│   ├── notifications/        # Telegram bot
│   ├── scheduler/            # APScheduler daily pipeline
│   └── config.py             # Pydantic settings
├── web/                      # Frontend Next.js
│   └── src/
│       ├── app/              # Pages (rankings, market, stock/[symbol])
│       ├── components/       # UI components (charts, tables, layout)
│       └── lib/              # API client, types, React Query hooks
├── alembic/                  # Database migrations
├── tests/                    # 326 unit tests
└── docs/                     # Documentation
```

## License

Private — Personal use only.
