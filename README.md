<!-- generated-by: gsd-doc-writer -->
# LocalStock

**Personal AI stock analysis agent for the Vietnamese HOSE market**

LocalStock is a local-first stock analysis system that crawls roughly 400 HOSE tickers, runs multi-factor analysis (technical, fundamental, sentiment, and macro), ranks opportunities, and generates detailed Vietnamese reports. The system is designed to run on a personal machine with a local Ollama model, so the core workflow does not depend on paid LLM APIs.

## Highlights

- **Data pipeline** - Crawl OHLCV, financial statements, corporate actions, news, and macro inputs
- **Technical analysis** - SMA, EMA, RSI, MACD, Bollinger Bands, and other indicators
- **Fundamental analysis** - P/E, P/B, ROE, ROA, D/E, and sector comparison
- **Sentiment analysis** - Financial news ingestion with local AI-assisted classification
- **AI scoring** - Composite 0-100 ranking across multiple factors
- **AI reports** - Vietnamese stock reports that explain why a ticker looks attractive or risky
- **Recommendation badges** - Strong Buy / Buy / Hold / Sell / Strong Sell labels in the UI
- **Automation** - Daily pipeline after market close
- **Telegram notifications** - Alerts for strong candidates and major movements
- **Web dashboard** - Rankings, charts, stock detail pages, market overview, and learning content
- **Theme system** - Warm-light default theme with dark mode toggle and persisted preference
- **Learning and glossary** - Vietnamese explanations for indicators, ratios, and macro concepts
- **Admin console** - Manage tracked stocks, run pipeline operations, and monitor job history from the UI

## Current Status

The project is currently in the **v1.2 Admin Console** milestone.

- **Shipped**: stock management, pipeline control, job monitoring, dashboard improvements, learning page, glossary linking, warm-light theme system
- **Next**: Phase 13 - generate AI reports directly from the admin console

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/)
- A local GPU is recommended for report generation workloads

### 1. Clone and install dependencies

```bash
git clone https://github.com/khanhtoan26/localstock.git
cd localstock
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with your database, Ollama, and Telegram settings.

- Setup guide: [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)
- Configuration reference: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

### 3. Initialize the database

```bash
uv run python apps/prometheus/bin/init_db.py
```

### 4. Start the services

```bash
# Terminal 1: backend API
uv run uvicorn localstock.api.app:app --reload

# Terminal 2: frontend
cd apps/helios
npm install
npm run dev

# Terminal 3: Ollama
ollama serve
ollama pull qwen2.5:14b-instruct-q4_K_M
```

### 5. Open the app

- Dashboard: http://localhost:3000
- Admin console: http://localhost:3000/admin
- Learning page: http://localhost:3000/learn
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

To trigger the full pipeline manually:

```bash
curl -X POST http://localhost:8000/api/automation/run
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async |
| Database | PostgreSQL, Alembic |
| Data | vnstock 3.5.1, pandas, pandas-ta |
| AI/LLM | Ollama with structured JSON outputs |
| Frontend | Next.js 16, React 19, TypeScript |
| UI | Tailwind CSS 4, shadcn/ui, lightweight-charts v5 |
| Automation | APScheduler |
| Notifications | python-telegram-bot |
| Testing | pytest, Playwright |

## Documentation

- [**GETTING-STARTED.md**](docs/GETTING-STARTED.md) - installation and first run
- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) - system design and codebase walkthrough
- [**DEVELOPMENT.md**](docs/DEVELOPMENT.md) - development workflow and commands
- [**TESTING.md**](docs/TESTING.md) - testing approach and test commands
- [**CONFIGURATION.md**](docs/CONFIGURATION.md) - environment variables and service configuration
- [**API.md**](docs/API.md) - backend API reference
- [**SETUP.md**](docs/SETUP.md) - legacy setup notes

## Repository Structure

```text
localstock/
├── apps/
│   ├── prometheus/          # Backend API, crawlers, services, scheduler, tests
│   └── helios/              # Next.js frontend and Playwright E2E tests
├── docs/                    # Project documentation
├── .planning/               # GSD planning and milestone artifacts
├── .env.example             # Environment template
└── pyproject.toml           # uv workspace configuration
```

## License

Private - personal use only.
