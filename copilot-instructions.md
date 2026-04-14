<!-- GSD:project-start source:PROJECT.md -->
## Project

**LocalStock**

LocalStock là một AI Stock Agent cá nhân cho thị trường chứng khoán Việt Nam (HOSE). Agent tự động crawl dữ liệu ~400 mã cổ phiếu, phân tích đa chiều (kỹ thuật, cơ bản, sentiment, vĩ mô), xếp hạng và đưa ra gợi ý mã đáng mua kèm báo cáo chi tiết. Chạy trên máy cá nhân với LLM local miễn phí qua Ollama (RTX 3060).

**Core Value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

### Constraints

- **Hardware**: RTX 3060 12GB VRAM — giới hạn model LLM ≤ 13B parameters
- **Cost**: Miễn phí hoàn toàn — không dùng paid API, chỉ local LLM + free data sources
- **Market hours**: Sàn HOSE giao dịch 9:00-15:00 thứ 2-6 — crawl dữ liệu theo lịch này
- **Data availability**: Phụ thuộc vào nguồn dữ liệu free/public — có thể bị rate limit hoặc thay đổi API
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Architecture Overview
### Core Runtime
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Python** | 3.12+ | Primary language | All data/ML/AI libraries are Python-native. vnstock, pandas-ta, Ollama client all require Python. No contest. | HIGH |
| **Node.js** | 22 LTS | Dashboard frontend | Required for Next.js. Use LTS for stability. | HIGH |
### Backend Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **FastAPI** | 0.135+ | REST API server | Async-native, auto-generates OpenAPI docs, Pydantic integration for data validation, excellent performance. Uvicorn ASGI server handles concurrent requests from dashboard + scheduler + Telegram bot. | HIGH |
| **Uvicorn** | 0.44+ | ASGI server | Standard FastAPI deployment. Use `--workers` for multi-process in production. | HIGH |
| **Pydantic** | 2.13+ | Data validation/models | Already a FastAPI dependency. Use for all data models: stock data, analysis results, LLM output parsing. Pydantic v2 is 5-50x faster than v1. | HIGH |
### Database
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **PostgreSQL** | 16+ | Primary data store | Cloud-ready (every cloud provider has managed Postgres). Handles concurrent writes from crawler + reads from API. Full-text search for news. JSON columns for flexible financial report storage. ~400 stocks × daily OHLCV is trivially small for Postgres. | HIGH |
| **SQLAlchemy** | 2.0+ | ORM & query builder | Industry standard Python ORM. Async support via `asyncpg`. Alembic for migrations. Type-safe queries with 2.0 style. | HIGH |
| **Alembic** | 1.18+ | DB migrations | SQLAlchemy's official migration tool. Essential for evolving schema without data loss. | HIGH |
| **asyncpg** | 0.31+ | Async Postgres driver | Fastest Python Postgres driver. Native async for FastAPI. | HIGH |
### Vietnamese Stock Data
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **vnstock** | 3.5+ | Stock data API | **The** library for Vietnamese stock market data. Provides: price/volume (OHLCV), financial statements (balance sheet, income, cash flow), financial ratios (P/E, EPS, ROE), company info, market indices. Sources: VCI (Viet Capital Securities) and KBS (KB Securities). Free for personal use. Active development (updated Jan 2026). No other library comes close for VN market. | HIGH |
### Technical Analysis
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pandas-ta** | 0.4.71b0 | Technical indicators | Pure Python, no C compilation needed (unlike TA-Lib). 130+ indicators including MA, EMA, RSI, MACD, Bollinger Bands, VWAP, OBV, Stochastic. Works directly on pandas DataFrames. Active community. | HIGH |
### AI / LLM
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Ollama** | latest | LLM inference server | Simplest way to run local LLMs. GPU auto-detection, model management, REST API. Runs as a service on localhost:11434. | HIGH |
| **ollama** (Python) | 0.6+ | Ollama client | Official Python client. Simple API: `ollama.chat()`, `ollama.generate()`. Supports streaming, JSON mode for structured output. | HIGH |
| **Qwen2.5 14B Q4_K_M** | — | Primary LLM model | Best fit for 12GB VRAM: ~9-10GB at Q4_K_M quantization. Excellent multilingual support (Vietnamese included). Strong reasoning for financial analysis. Outperforms Llama 3.1 8B on reasoning tasks while fitting in VRAM budget. | MEDIUM |
| **Qwen2.5 7B Q8_0** | — | Fallback LLM model | If 14B is too slow or VRAM-tight during concurrent use, 7B at Q8 quantization (~7GB) gives better quality-per-parameter with room for context. | MEDIUM |
### Web Scraping & News
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **httpx** | 0.28+ | HTTP client | Async-native, HTTP/2 support, connection pooling. Superior to `requests` for concurrent crawling. | HIGH |
| **BeautifulSoup4** | 4.14+ | HTML parsing | Mature, battle-tested. Use with `lxml` parser for speed. Perfect for CafeF, VnExpress, VnDirect news pages. | HIGH |
| **newspaper4k** | 0.9+ | Article extraction | Extracts article text, authors, publish date from news URLs. Supports Vietnamese language. Use for clean text extraction from financial news sites. | MEDIUM |
| **trafilatura** | 2.0+ | Web content extraction | Better than newspaper4k for some sites. Use as fallback when newspaper4k fails on Vietnamese news layout. | MEDIUM |
### Vietnamese NLP
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **underthesea** | 9.4+ | Vietnamese NLP | Word segmentation, POS tagging, NER, sentiment analysis. Essential for pre-processing Vietnamese financial news before LLM analysis. Tokenization improves LLM prompt quality for Vietnamese text. | HIGH |
### Frontend Dashboard
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Next.js** | 16+ | Dashboard framework | App Router for file-based routing, Server Components for fast initial load, API routes if needed. Cloud-ready with Vercel/Docker deployment. | HIGH |
| **React** | 19+ | UI library | Next.js dependency. Use hooks + server components. | HIGH |
| **TypeScript** | 5.x+ | Type safety | Catches bugs at compile time. Essential for data-heavy dashboard. | HIGH |
| **Tailwind CSS** | 4+ | Styling | Utility-first, fast iteration. v4 has better performance. | HIGH |
| **shadcn/ui** | (CLI 4.2+) | UI components | Copy-paste components, not a dependency. Tables, cards, dialogs — everything needed for a stock dashboard. Fully customizable. | HIGH |
| **lightweight-charts** | 5.1+ | Stock charts | TradingView's open-source charting library. Candlestick, line, area, volume charts. Professional quality. Tiny bundle (~45KB). Purpose-built for financial data. | HIGH |
| **Recharts** | 3.8+ | General charts | Bar charts, pie charts, radar charts for analysis breakdown (scoring radar, sector distribution). Use alongside lightweight-charts. | HIGH |
| **@tanstack/react-query** | 5.99+ | Data fetching | Caching, refetching, loading states. Perfect for polling stock data. Prevents unnecessary re-renders. | HIGH |
### Scheduling & Automation
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **APScheduler** | 3.11+ | Job scheduler | In-process scheduler with cron-like syntax. Schedule daily crawl at market close (15:00 VN time), periodic news crawl, weekly fundamental analysis. v3 is stable (v4 still alpha). | HIGH |
### Notifications
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **python-telegram-bot** | 22.7+ | Telegram alerts | Most popular Python Telegram library. Async-native (v20+). Send formatted messages with stock recommendations, charts as images. Supports inline keyboards for quick actions. | HIGH |
### DevOps & Infrastructure
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Docker** | 24+ | Containerization | PostgreSQL in container for localhost. Full app containerization for cloud deployment. | HIGH |
| **Docker Compose** | 2.x | Multi-container orchestration | Define Postgres + Backend + Frontend + Ollama in one file. `docker compose up` for one-command startup. | HIGH |
| **uv** | latest | Python package manager | 10-100x faster than pip. Lockfile support. Replaces pip + virtualenv + pip-tools. | HIGH |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pandas** | 2.2+ | Data manipulation | Core dependency of vnstock and pandas-ta. All data processing. |
| **numpy** | 2.x | Numerical computing | Pandas dependency. Used in scoring calculations. |
| **lxml** | 5.x | Fast XML/HTML parser | BeautifulSoup parser backend. 10x faster than html.parser. |
| **Pillow** | 11+ | Image processing | Generate chart images for Telegram notifications. |
| **python-dotenv** | 1.x | Environment variables | Load config from `.env` files. Telegram token, DB URL, Ollama host. |
| **loguru** | 0.7+ | Logging | Better than stdlib logging. Structured, colorized, easy rotation. |
| **tenacity** | 9+ | Retry logic | Retry failed API calls, crawl requests. Already used by vnstock internally. |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| **Stock Data** | vnstock | Direct TCBS/SSI API calls | vnstock wraps these APIs with error handling, retry, data normalization. Reinventing this is wasted effort. |
| **Tech Analysis** | pandas-ta | TA-Lib (via ta-lib wrapper) | TA-Lib requires C library compilation (`apt install ta-lib` or build from source). Breaks in Docker, CI. pandas-ta is pure Python, same indicators. |
| **Tech Analysis** | pandas-ta | `ta` library | `ta` (0.11.0) has fewer indicators, less active development. pandas-ta has 130+ vs ~40. |
| **Database** | PostgreSQL | SQLite | SQLite can't handle concurrent writes from scheduler + API + dashboard. No full-text search. Not cloud-ready (file-based). |
| **Database** | PostgreSQL | MongoDB | Stock data is tabular (OHLCV, ratios). Relational model is natural fit. MongoDB adds complexity for no benefit here. |
| **ORM** | SQLAlchemy | Tortoise ORM / Prisma | SQLAlchemy is industry standard with the largest ecosystem. Tortoise is less mature. Prisma is Node.js-focused. |
| **Backend** | FastAPI | Django | Django is heavier, synchronous by default. FastAPI's async + auto-docs + Pydantic integration is ideal for this API-first project. |
| **Backend** | FastAPI | Flask | Flask has no async, no auto-docs, no built-in validation. FastAPI is strictly superior for new projects. |
| **LLM Client** | ollama (direct) | LangChain | LangChain adds massive abstraction overhead for what is "send prompt → parse JSON response." Direct ollama client is simpler, faster, debuggable. If you need chains/agents later, add LangChain then. |
| **LLM Model** | Qwen2.5 14B | Llama 3.1 8B | Llama 3.1 8B has weaker Vietnamese language support. Qwen2.5 was trained on more multilingual data including Vietnamese. 14B > 8B for reasoning quality. |
| **LLM Model** | Qwen2.5 14B | Mistral 7B | Mistral has minimal Vietnamese training data. Poor for Vietnamese financial text. |
| **Dashboard** | Next.js | Streamlit | Streamlit is faster to prototype but: no customization, poor UX for non-data-scientists, can't deploy as standalone web app easily, not cloud-ready. Next.js is more work upfront but better long-term. |
| **Dashboard** | Next.js | Gradio | Same issues as Streamlit. Built for ML demos, not production dashboards. |
| **Charts** | lightweight-charts | Apache ECharts | ECharts is 10x larger bundle. lightweight-charts is purpose-built for financial data by TradingView team. |
| **Charts** | lightweight-charts | Plotly | Plotly is Python-centric (great for Jupyter). For a React dashboard, lightweight-charts gives native JS performance. |
| **Scheduler** | APScheduler | Celery | Celery requires Redis/RabbitMQ broker. Overkill for single-machine. APScheduler is in-process, zero dependencies. |
| **Scheduler** | APScheduler | cron (system) | cron can't be containerized easily, no programmatic control, no error handling/retry. APScheduler is Python-native. |
| **HTTP Client** | httpx | requests | requests has no async support, no HTTP/2. httpx is the modern replacement with full async. |
| **Scraping** | httpx + BS4 | Scrapy | Scrapy is a full framework — overkill for crawling 5-10 news sites. httpx + BS4 is simpler, more flexible. |
| **Scraping** | httpx + BS4 | Playwright | Playwright (headless browser) is 10x slower and heavier. Only use if sites require JavaScript rendering. Most Vietnamese news sites serve HTML directly. |
| **Vietnamese NLP** | underthesea | PhoBERT / VnCoreNLP | PhoBERT requires GPU for inference (competing with LLM for VRAM). VnCoreNLP requires Java. underthesea is pure Python, lightweight. |
| **Package Manager** | uv | pip + venv | uv is 10-100x faster, has lockfile, replaces multiple tools. pip is legacy. |
## Anti-Stack: What NOT to Use
| Technology | Why Not |
|------------|---------|
| **LangChain** | Massive abstraction layer for simple LLM calls. Adds 50+ transitive dependencies. Use raw ollama client instead. Add LangChain only if you build multi-step agent chains later. |
| **Jupyter Notebooks** | Not production code. Use for exploration only. All production logic goes in Python modules. |
| **MongoDB** | Stock data is inherently tabular. MongoDB adds complexity for data that fits naturally in rows/columns. |
| **Redis** | Not needed unless you add Celery. PostgreSQL handles all caching needs for a personal tool. |
| **Selenium/Playwright** | 10x slower than httpx. Only resort to these if a specific site blocks non-browser requests. |
| **TensorFlow/PyTorch** | You're not training custom ML models. The LLM handles analysis. Don't build a stock prediction neural network — it won't beat the market. |
| **Kafka/RabbitMQ** | Message queues for distributed systems. This is a single-machine tool. |
## Installation
### Backend (Python)
# Create project with uv
# Core
# Stock data & analysis
# AI / LLM
# Scraping & NLP
# Scheduling & notifications
# Utilities
# Dev dependencies
### Frontend (Next.js)
# Create Next.js app
# UI components
# Charts & data fetching
### Infrastructure (Docker Compose)
# docker-compose.yml
### Ollama Setup
# Install Ollama (Linux)
# Pull recommended model
# Fallback smaller model
# Verify
## Version Pinning Strategy
# pyproject.toml
## Sources
- **vnstock:** PyPI (v3.5.1), GitHub (thinh-vu/vnstock), verified 2025-07-17 — HIGH confidence
- **vnstock license:** Custom non-commercial license, verified from GitHub LICENSE.md — HIGH confidence
- **pandas-ta:** PyPI (v0.4.71b0) — HIGH confidence
- **FastAPI:** PyPI (v0.135.3) — HIGH confidence
- **Ollama Python:** PyPI (v0.6.1) — HIGH confidence
- **Qwen2.5 VRAM requirements:** Based on quantization math (14B × 4bit ÷ 8 ≈ 7GB + overhead ≈ 9-10GB) — MEDIUM confidence, verify empirically
- **python-telegram-bot:** PyPI (v22.7) — HIGH confidence
- **lightweight-charts:** npm (v5.1.0) — HIGH confidence
- **Next.js:** npm (v16.2.3) — HIGH confidence
- **APScheduler:** PyPI (v3.11.2, v4 still alpha) — HIGH confidence
- **underthesea:** PyPI (v9.4.0), GitHub README — HIGH confidence
- **newspaper4k:** PyPI (v0.9.5), GitHub README — MEDIUM confidence
- **All other versions:** Verified via PyPI/npm JSON API on 2025-07-17
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.github/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
