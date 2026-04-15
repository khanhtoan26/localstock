# LocalStock

AI Stock Agent for Vietnamese Market (HOSE).

LocalStock là một AI Stock Agent cá nhân cho thị trường chứng khoán Việt Nam.
Agent tự động crawl dữ liệu ~400 mã cổ phiếu, phân tích đa chiều, xếp hạng
và đưa ra gợi ý mã đáng mua kèm báo cáo chi tiết.

## Setup

1. Install [uv](https://docs.astral.sh/uv/):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Copy `.env.example` to `.env` and fill in your Supabase credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase connection details
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Run tests:
   ```bash
   uv run pytest
   ```

## Tech Stack

- **Python 3.12+** — Primary language
- **FastAPI** — REST API server
- **SQLAlchemy 2.0** — Async ORM with asyncpg
- **PostgreSQL (Supabase)** — Primary data store
- **vnstock** — Vietnamese stock market data
- **Ollama** — Local LLM inference
