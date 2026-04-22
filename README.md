<!-- generated-by: gsd-doc-writer -->
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
- 🏷️ **Recommendation Badges** — Nhãn gợi ý (Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh) trên trang cổ phiếu và bảng xếp hạng
- ⏰ **Automation** — Pipeline chạy tự động hàng ngày sau phiên (15:45)
- 📱 **Telegram Bot** — Gửi alert khi có gợi ý tốt hoặc biến động lớn
- 🖥️ **Web Dashboard** — Bảng xếp hạng, biểu đồ nến, phân tích sector
- 🎨 **Theme System** — Giao diện Claude warm-light (cream + orange) mặc định + dark mode toggle, lưu trữ trong localStorage
- 📖 **Academic/Learning Page** — Giải thích chỉ báo kỹ thuật, tỷ số cơ bản, khái niệm vĩ mô bằng tiếng Việt
- 🔗 **Interactive Glossary** — Thuật ngữ trong báo cáo AI liên kết tới định nghĩa trên trang học
- 🛠️ **Admin Console** — Quản lý cổ phiếu theo dõi, trigger crawl/analyze/score/report từ giao diện, theo dõi trạng thái job

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

Xem [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) để biết chi tiết cài đặt và [docs/CONFIGURATION.md](docs/CONFIGURATION.md) cho cấu hình từng service.

### 3. Database

```bash
# Chạy migrations (BẮT BUỘC trước khi chạy backend)
uv run python apps/prometheus/bin/init_db.py
```

### 4. Khởi động

```bash
# Terminal 1: Backend API (port 8000)
uv run uvicorn localstock.api.app:app --reload

# Terminal 2: Frontend (port 3000)
cd apps/helios && npm install && npm run dev

# Terminal 3: Ollama LLM (nếu cần AI features)
ollama serve
ollama pull qwen2.5:14b-instruct-q4_K_M
```

### 5. Sử dụng

- 🌐 **Dashboard:** http://localhost:3000
- 🛠️ **Admin Console:** http://localhost:3000/admin
- 📖 **Trang học:** http://localhost:3000/learn
- 📡 **API:** http://localhost:8000
- 📖 **API Docs:** http://localhost:8000/docs (Swagger UI)

Để chạy pipeline lần đầu:
```bash
# Trigger toàn bộ pipeline (crawl → analyze → score → report → notify)
curl -X POST http://localhost:8000/api/automation/run
```

Hoặc sử dụng Admin Console tại http://localhost:3000/admin để trigger từng bước từ giao diện.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) |
| **Database** | PostgreSQL (Supabase), Alembic migrations |
| **Data** | vnstock 3.5.1, pandas, pandas-ta |
| **AI/LLM** | Ollama (qwen2.5:14b), structured JSON output |
| **Frontend** | Next.js 16, React 19, TypeScript 5 |
| **UI** | Tailwind CSS 4, shadcn/ui, lightweight-charts v5, next-themes |
| **Automation** | APScheduler (CronTrigger) |
| **Notifications** | python-telegram-bot |
| **Testing** | pytest (353+ unit tests), Playwright (29 E2E tests) |

## Tài liệu

- [**GETTING-STARTED.md**](docs/GETTING-STARTED.md) — Hướng dẫn cài đặt & chạy lần đầu
- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) — Kiến trúc, workflow, giải thích toàn bộ codebase
- [**DEVELOPMENT.md**](docs/DEVELOPMENT.md) — Hướng dẫn phát triển, build commands, code style
- [**TESTING.md**](docs/TESTING.md) — Test framework, chạy tests, coverage
- [**CONFIGURATION.md**](docs/CONFIGURATION.md) — Biến môi trường, cấu hình chi tiết
- [**API.md**](docs/API.md) — Tài liệu API endpoints
- [**SETUP.md**](docs/SETUP.md) — Hướng dẫn cài đặt chi tiết (legacy)

## Cấu trúc dự án

```
localstock/                          # Monorepo root
├── apps/
│   ├── prometheus/                  # 🔥 Backend — AI engine & data processing
│   │   ├── src/localstock/          # Python package
│   │   │   ├── api/routes/          # FastAPI endpoints (10 routers bao gồm admin)
│   │   │   ├── ai/                  # Ollama LLM client & prompts
│   │   │   ├── crawlers/            # Data crawlers (price, finance, news)
│   │   │   ├── db/                  # SQLAlchemy models & repositories
│   │   │   ├── services/            # Business logic (scoring, analysis, reports)
│   │   │   ├── notifications/       # Telegram bot
│   │   │   ├── scheduler/           # APScheduler daily pipeline
│   │   │   └── config.py            # Pydantic settings
│   │   ├── alembic/                 # Database migrations
│   │   ├── bin/                     # CLI scripts (crawl, analyze, score)
│   │   ├── tests/                   # 353+ unit tests
│   │   └── pyproject.toml           # Python dependencies
│   └── helios/                      # ☀️ Frontend — Web dashboard
│       ├── src/
│       │   ├── app/
│       │   │   ├── rankings/        # Bảng xếp hạng cổ phiếu
│       │   │   ├── market/          # Tổng quan thị trường
│       │   │   ├── stock/[symbol]/  # Trang chi tiết cổ phiếu
│       │   │   ├── learn/           # 📖 Trang học thuật / kiến thức
│       │   │   └── admin/           # 🛠️ Admin Console
│       │   ├── components/
│       │   │   ├── admin/           # Pipeline control, job monitor, stock table
│       │   │   ├── charts/          # Biểu đồ nến, recharts
│       │   │   ├── glossary/        # Interactive glossary linking
│       │   │   ├── learn/           # Glossary entry cards, search
│       │   │   ├── stock/           # AI report panel, recommendation badges, score breakdown
│       │   │   ├── theme/           # Theme provider & toggle (warm-light/dark)
│       │   │   └── ui/              # shadcn/ui components
│       │   └── lib/                 # API client, types, React Query hooks
│       ├── e2e/                     # 29 Playwright E2E tests
│       └── package.json             # Node.js dependencies
├── docs/                            # Documentation
├── .env.example                     # Environment template
└── pyproject.toml                   # uv workspace config
```

## License

Private — Personal use only.
