# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Instructions for GSD

- Use the get-shit-done skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.

# General Instructions

- **All questions to the user MUST use decision UI** (the `ask_user` / `vscode_askQuestions` tool with selectable options). NEVER end a message with a plain-text question and wait for the user to type a reply. Always present choices via the decision UI so the user can click to answer.
- This applies to every context: chat, CLI, GSD workflows, and subagents.
- **After completing ANY task** (GSD command, feature, bug fix, tests, docs, or any other deliverable), ALWAYS prompt the user via decision UI with at least these options: (1) "Kết thúc tại đây" (end), (2) suggested next actions relevant to the context. Always allow freeform text input so the user can type a custom request.

## Project Overview

LocalStock is a **monorepo** containing an AI-powered Vietnamese stock analysis agent. It crawls ~400 stocks from HOSE daily, applies multi-dimensional analysis (technical, fundamental, sentiment, macro), and generates AI-powered reports and trading recommendations — all running locally.

- **Backend (Prometheus)**: Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, Ollama LLM, APScheduler
- **Frontend (Helios)**: Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query
- **Data**: vnstock 3.5.1, pandas, pandas-ta for indicators
- **Automation**: Daily pipeline at 15:45 via APScheduler; Telegram notifications

## Monorepo Structure

```
apps/prometheus/          # 🔥 Backend Python package
├── src/localstock/       # Main package
│   ├── api/routes/       # FastAPI routers (30+ endpoints across 9 routers)
│   ├── ai/               # Ollama integration & prompt templates
│   ├── crawlers/         # vnstock data crawlers (OHLCV, financials, news)
│   ├── db/               # SQLAlchemy ORM models + async repositories
│   ├── services/         # Business logic (analysis, scoring, reporting)
│   ├── notifications/    # Telegram bot integration
│   ├── scheduler/        # APScheduler daily pipeline orchestration
│   └── config.py         # Pydantic settings (env-based)
├── bin/                  # CLI entry scripts (crawl.py, analyze.py, score.py)
├── alembic/              # Database migrations
├── tests/                # 326+ unit tests (pytest-asyncio)
└── pyproject.toml        # Dependencies & test config

apps/helios/              # ☀️ Frontend Next.js app
├── src/
│   ├── app/              # Pages (rankings, market, stock/[symbol])
│   ├── components/       # Reusable React components (charts, tables, layout)
│   └── lib/              # API client, types, hooks (TanStack Query)
└── package.json

docs/                     # Architecture, setup, API docs (Vietnamese)
.env.example              # Environment template
pyproject.toml            # uv workspace root config
```

## Building, Testing, Lint Commands

### Python Backend (apps/prometheus)

All Python commands use `uv` (fast package manager). Dependency management is workspace-aware via uv.

```bash
# Install dependencies (from workspace root)
uv sync

# Run backend API server (port 8000, hot reload)
uv run uvicorn localstock.api.app:app --reload

# Run all tests (326+ tests, async-aware via pytest-asyncio)
uv run pytest

# Run specific test file
uv run pytest tests/test_services/test_analysis_service.py

# Run single test
uv run pytest tests/test_services/test_analysis_service.py::test_calculate_rsi

# Lint with ruff
uv run ruff check src/ tests/

# Format with ruff
uv run ruff format src/ tests/

# Type check with mypy
uv run mypy src/ --strict

# Initialize/migrate database (required before first run)
uv run python apps/prometheus/bin/init_db.py
```

### Frontend (apps/helios)

```bash
# Install dependencies (from apps/helios)
npm install

# Dev server (port 3000, hot reload)
npm run dev

# Build for production
npm build

# Start production server
npm start

# Lint with ESLint
npm run lint
```

## Key Architecture Patterns

### Data Layer (Database-Centric)

- **SQLAlchemy 2.0 async ORM** with explicit `async with` sessions for concurrency
- **18 tables** covering stocks, prices, indicators, analysis, scores, reports, notifications
- **Alembic migrations** in `apps/prometheus/alembic/` — run via `init_db.py` on startup
- **Repository pattern** in `src/localstock/db/` — stateless query builders that return domain objects
- All DB queries are **async-first** (`asyncpg` driver, `await` everywhere)

### Service Layer Architecture

**Three-tier organization:**

1. **Crawlers** (`src/localstock/crawlers/`) — fetch raw data from vnstock + web sources
2. **Services** (`src/localstock/services/`) — orchestrate analysis, scoring, reporting
   - `AnalysisService` — computes 11+ technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
   - `ScoreService` — weighted composite scoring (0-100)
   - `ReportService` — generates Vietnamese AI reports via Ollama
   - `MacroService` — fetches macro data (rates, FX, CPI impact)
   - `NewsService` — sentiment analysis on crawled news
3. **API Routes** (`src/localstock/api/routes/`) — thin HTTP adapters exposing services
   - Each router handles a domain (analysis, scores, reports, news, macro, automation, prices, sectors, health)
   - Requests validate via Pydantic, call service, return JSON

**Key invariant:** Services are domain-agnostic and injectable, API routes are stateless.

### Async/Concurrency Model

- **No blocking I/O** — all network calls use `httpx` async client
- **Concurrent crawling** — crawlers run in parallel via `asyncio.gather()`
- **Async db sessions** — `AsyncSession` context managers, never sync calls
- **Task timeouts** — pytest configured with 30s timeout to catch hangs
- Ensure functions declared `async def` if they `await` anything

### Configuration (Pydantic)

- `src/localstock/config.py` reads from `.env` via `pydantic_settings.BaseSettings`
- Settings include: DB URL, API keys, Ollama endpoint, Telegram token, stock list
- **No hardcoded secrets** — all config via environment variables

### API Design

- **RESTful** with JSON in/out
- **Swagger docs** at `/docs` (FastAPI default)
- 9 routers, ~30 endpoints covering:
  - Analysis (GET /api/analysis/{symbol}, POST /api/analysis/batch)
  - Scores (GET /api/scores/ranking, GET /api/scores/{symbol})
  - Reports (GET /api/reports/{symbol})
  - News & sentiment (GET /api/news/{symbol})
  - Macro (GET /api/macro/indicators)
  - Automation (POST /api/automation/run, GET /api/automation/status)
  - Prices (GET /api/prices/{symbol}, /api/prices/{symbol}/history)
  - Sectors (GET /api/sectors)
  - Health (GET /health)

### AI Integration (Ollama LLM)

- **Offline local model** — Ollama `qwen2.5:14b-instruct-q4_K_M` (no API calls)
- **Structured outputs** — LLM returns JSON, parsed via Pydantic
- **Prompts in code** — Vietnamese-language system prompts in `src/localstock/ai/prompts.py`
- **Failure handling** — graceful degradation if Ollama unavailable

### Automation & Scheduling

- **APScheduler** with CronTrigger set to run daily at **15:45** (post-market)
- Orchestrated via `src/localstock/scheduler/` — single point of coordination
- Pipeline: `crawl() → analyze() → score() → generate_reports() → notify_telegram() → save_results()`
- Also exposed as HTTP POST `/api/automation/run` for manual trigger
- Results cached in DB to avoid redundant computation

### Notifications (Telegram)

- **python-telegram-bot** integration in `src/localstock/notifications/`
- Triggered after scoring/reporting phase
- Filters: top-performing stocks, macro alerts, large price movements
- Token from `.env`

### Frontend (Next.js + React Query)

- **App Router** (not Pages Router)
- **TanStack Query (React Query)** for data fetching, caching, background sync
- **Tailwind CSS 4** with shadcn/ui components for UI
- **lightweight-charts v5** for candlestick charts (financial grade)
- API client in `src/lib/api.ts` wraps `fetch` with types from backend
- Pages: rankings dashboard, sector analysis, individual stock detail page with charts + analysis

## Testing Patterns

- **pytest** with `pytest-asyncio` mode `auto` for async test functions
- **30s timeout** on all tests (configured in pyproject.toml)
- **conftest.py** provides fixtures (DB fixtures are not in shared code, tests use real async DB or mocks)
- Test location: `tests/test_services/`, `tests/test_crawlers/`, etc. mirrors `src/localstock/` structure
- Async tests use `async def test_...` without decorators (pytest-asyncio auto mode)

Example:
```python
async def test_calculate_rsi():
    result = await analysis_service.calculate_rsi(prices, period=14)
    assert 0 <= result.rsi <= 100
```

## Environment Setup

Required `.env` variables (copy from `.env.example`):
- `DATABASE_URL` — PostgreSQL connection string (Supabase)
- `OLLAMA_BASE_URL` — Ollama API endpoint (default: `http://localhost:11434`)
- `TELEGRAM_BOT_TOKEN` — Telegram Bot API token
- `TELEGRAM_CHAT_ID` — Telegram recipient chat ID
- `STOCK_SYMBOLS` — Comma-separated list of symbols to analyze (~400 for full HOSE)

## Important Notes

1. **Database migrations are required** — run `uv run python apps/prometheus/bin/init_db.py` before first backend start. New schema changes require `alembic revision --autogenerate` + commit.

2. **Separate processes** — Backend (port 8000), Frontend (port 3000), Ollama (port 11434) must all be running; they do not auto-start.

3. **Async-first codebase** — no blocking I/O or sync calls to database. If adding a new service, use `async def` and inject `AsyncSession` or repositories.

4. **Vietnamese content** — code comments, prompts, reports, and docs are predominantly Vietnamese. Maintain this for consistency.

5. **Performance-sensitive** — Analysis on 400 stocks is CPU-intensive (pandas-ta indicators, LLM inference). Tests timeout at 30s; integration tests on large datasets may need adjustment.

6. **Next.js version** — This codebase uses Next.js 16, which has breaking changes from prior versions. See `apps/helios/AGENTS.md` for guidance.

7. **Monorepo coordination** — Both apps share version numbers (0.1.0); coordinate dependency upgrades across `apps/prometheus/pyproject.toml` and `apps/helios/package.json`.

8. **No external API calls for core analysis** — all inference is local (Ollama), all data via vnstock or local crawling. Telegram is the only external dependency (notifications only).
