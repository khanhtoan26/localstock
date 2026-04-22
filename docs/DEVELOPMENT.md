<!-- generated-by: gsd-doc-writer -->
# Hướng Dẫn Phát Triển (Development Guide)

Tài liệu này dành cho developer tham gia phát triển LocalStock — hướng dẫn thiết lập môi trường, quy trình build/test, coding style, và cách thêm tính năng mới.

## Mục Lục

- [Thiết lập môi trường phát triển](#thiết-lập-môi-trường-phát-triển)
- [Lệnh Build & Dev](#lệnh-build--dev)
- [Code Style](#code-style)
- [Quy trình thêm tính năng mới](#quy-trình-thêm-tính-năng-mới)
- [Database Migrations](#database-migrations)
- [Branch Conventions](#branch-conventions)
- [Quy trình Pull Request](#quy-trình-pull-request)

---

## Thiết lập môi trường phát triển

### Yêu cầu hệ thống

- **Python** >= 3.12
- **Node.js** >= 20
- **uv** — Python package manager (cài đặt: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **PostgreSQL** — Supabase hoặc PostgreSQL local
- **Ollama** — (tùy chọn) để chạy tính năng AI local. Cài đặt tại [ollama.com](https://ollama.com)

### Clone & cài đặt

```bash
# 1. Clone repo
git clone https://github.com/khanhtoan26/localstock.git
cd localstock

# 2. Copy file environment
cp .env.example .env
# Chỉnh sửa .env với thông tin database và API keys của bạn

# 3. Cài đặt backend dependencies (từ thư mục root)
uv sync

# 4. Cài đặt frontend dependencies
cd apps/helios
npm install
cd ../..
```

### Khởi tạo database

```bash
# Chạy migration lần đầu (bắt buộc trước khi start backend)
uv run python apps/prometheus/bin/init_db.py
```

### Chạy 3 services

LocalStock gồm 3 process riêng biệt — cần chạy đồng thời:

| Service | Port | Lệnh |
|---------|------|-------|
| Backend (Prometheus) | 8000 | `uv run uvicorn localstock.api.app:app --reload` |
| Frontend (Helios) | 3000 | `cd apps/helios && npm run dev` |
| Ollama (LLM) | 11434 | `ollama serve` (tùy chọn) |

> **Lưu ý:** Backend và Frontend không tự khởi động lẫn nhau. Bạn cần mở 3 terminal riêng biệt.

---

## Lệnh Build & Dev

### Python Backend (`apps/prometheus`)

Mọi lệnh Python chạy qua `uv` từ thư mục root của monorepo:

| Lệnh | Mô tả |
|-------|--------|
| `uv sync` | Cài đặt/đồng bộ dependencies |
| `uv run uvicorn localstock.api.app:app --reload` | Chạy API server (port 8000, hot reload) |
| `uv run pytest` | Chạy toàn bộ test suite |
| `uv run pytest tests/test_services/test_analysis_service.py` | Chạy test file cụ thể |
| `uv run pytest tests/test_services/test_analysis_service.py::test_calculate_rsi` | Chạy single test |
| `uv run ruff check src/ tests/` | Lint Python code |
| `uv run ruff format src/ tests/` | Format Python code |
| `uv run mypy src/ --strict` | Type check (strict mode) |
| `uv run python apps/prometheus/bin/init_db.py` | Khởi tạo/migrate database |

#### CLI scripts (`apps/prometheus/bin/`)

| Script | Mô tả |
|--------|--------|
| `bin/init_db.py` | Khởi tạo database và chạy migrations |
| `bin/crawl_all.py` | Crawl dữ liệu toàn bộ cổ phiếu |
| `bin/crawl_single.py` | Crawl dữ liệu một cổ phiếu |
| `bin/run_analysis.py` | Chạy phân tích kỹ thuật |
| `bin/run_scoring.py` | Chạy tính điểm tổng hợp |
| `bin/run_sentiment.py` | Chạy phân tích cảm xúc tin tức |
| `bin/run_reports.py` | Tạo báo cáo AI |
| `bin/run_daily.py` | Chạy toàn bộ pipeline hàng ngày |

### Frontend (`apps/helios`)

Mọi lệnh frontend chạy từ thư mục `apps/helios`:

| Lệnh | Mô tả |
|-------|--------|
| `npm install` | Cài đặt dependencies |
| `npm run dev` | Dev server (port 3000, hot reload) |
| `npm run build` | Build production |
| `npm start` | Chạy production server |
| `npm run lint` | Lint với ESLint |

---

## Code Style

### Python — Ruff

Backend sử dụng [Ruff](https://docs.astral.sh/ruff/) cho cả linting và formatting.

```bash
# Kiểm tra lỗi lint
uv run ruff check src/ tests/

# Tự động sửa lỗi lint
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/
```

**Quy tắc quan trọng:**

- **Async-first** — Mọi function có I/O phải dùng `async def`. Không dùng blocking I/O.
- **AsyncSession** — Database queries luôn dùng `AsyncSession` qua `asyncpg` driver.
- **`httpx` async client** — Network calls dùng `httpx` async, không dùng `requests`.
- **Type hints** — mypy strict mode (`uv run mypy src/ --strict`).
- **Tiếng Việt** — Comments, docstrings, và prompt templates viết bằng tiếng Việt.

### Frontend — ESLint

Frontend sử dụng ESLint với cấu hình `eslint-config-next` (core-web-vitals + TypeScript) tại `apps/helios/eslint.config.mjs`.

```bash
# Chạy lint
cd apps/helios
npm run lint
```

**Quy tắc quan trọng:**

- **Next.js 16** — Codebase dùng Next.js 16 với breaking changes so với phiên bản cũ. Tham khảo `apps/helios/AGENTS.md` trước khi viết code.
- **App Router** — Sử dụng App Router (thư mục `src/app/`), không dùng Pages Router.
- **React 19** — Sử dụng React 19 với các API mới.
- **Tailwind CSS 4** — Styling qua Tailwind CSS 4 và shadcn/ui components.
- **TanStack Query** — Data fetching qua `@tanstack/react-query`, không dùng `useEffect` + `fetch`.

---

## Quy trình thêm tính năng mới

### Thêm API endpoint mới

1. **Tạo route** trong `apps/prometheus/src/localstock/api/routes/`:
   ```python
   # apps/prometheus/src/localstock/api/routes/my_feature.py
   from fastapi import APIRouter

   router = APIRouter(prefix="/api/my-feature")

   @router.get("/{symbol}")
   async def get_my_feature(symbol: str):
       # Gọi service layer
       ...
   ```

2. **Đăng ký router** trong `apps/prometheus/src/localstock/api/app.py`:
   ```python
   from localstock.api.routes.my_feature import router as my_feature_router

   app.include_router(my_feature_router, tags=["my-feature"])
   ```

3. **Thêm service method** trong `apps/prometheus/src/localstock/services/` — business logic tách biệt khỏi route.

4. **Viết tests** trong `apps/prometheus/tests/` — mirror cấu trúc thư mục `src/localstock/`.

### Thêm crawler mới

1. **Tạo file** trong `apps/prometheus/src/localstock/crawlers/`:
   ```python
   # apps/prometheus/src/localstock/crawlers/my_crawler.py
   import pandas as pd
   from localstock.crawlers.base import BaseCrawler

   class MyCrawler(BaseCrawler):
       async def fetch(self, symbol: str, **kwargs) -> pd.DataFrame:
           # Implement async data fetching
           ...
   ```

2. **Kế thừa `BaseCrawler`** — lớp cơ sở cung cấp `fetch_batch()` với error-tolerant processing (skip lỗi, tiếp tục crawl các mã khác).

3. **Async required** — method `fetch()` phải là `async def`, sử dụng `httpx` cho network calls.

### Thêm trang frontend mới

1. **Tạo page** trong `apps/helios/src/app/`:
   ```
   apps/helios/src/app/my-page/
   └── page.tsx
   ```

2. **Thêm navigation** — cập nhật `navItems` trong `apps/helios/src/components/layout/sidebar.tsx`:
   ```tsx
   const navItems = [
     // ... existing items
     { href: "/my-page", label: t("myPage"), icon: MyIcon },
   ];
   ```

3. **Thêm i18n translations** — cập nhật cả 2 file:
   - `apps/helios/messages/vi.json` — bản tiếng Việt
   - `apps/helios/messages/en.json` — bản tiếng Anh

### Thêm shadcn/ui component

```bash
cd apps/helios
npx shadcn@latest add <component-name>
```

Components được cài vào `apps/helios/src/components/ui/`. Style sử dụng `base-nova` với Tailwind CSS variables. Cấu hình tại `apps/helios/components.json`.

Các UI components hiện có: `badge`, `button`, `card`, `checkbox`, `collapsible`, `empty-state`, `error-state`, `input`, `scroll-area`, `separator`, `skeleton`, `sonner`, `table`, `tabs`.

---

## Database Migrations

LocalStock sử dụng **Alembic** cho database migrations. Files migration nằm tại `apps/prometheus/alembic/`.

### Tạo migration mới

Khi thay đổi ORM models trong `apps/prometheus/src/localstock/db/models.py`:

```bash
# Từ thư mục apps/prometheus
cd apps/prometheus

# Tạo migration tự động từ model changes
uv run alembic revision --autogenerate -m "mô tả thay đổi"

# Áp dụng migration
uv run alembic upgrade head
```

### Lưu ý quan trọng

- **Migration URL** — Alembic sử dụng `DATABASE_URL_MIGRATION` (port 5432, session mode) thay vì `DATABASE_URL` (port 6543, pooling mode). Xem `.env.example` để cấu hình.
- **Async engine** — `alembic/env.py` sử dụng `async_engine_from_config` với asyncpg driver.
- **Luôn commit migration files** — files trong `alembic/versions/` phải được commit vào git.
- **Kiểm tra migration** — chạy `uv run alembic upgrade head` sau khi tạo migration mới để đảm bảo không có lỗi.

---

## Branch Conventions

Không có quy ước branch chính thức được tài liệu hóa. Dựa trên git history, project sử dụng:

- **`master`** — branch chính (default branch)
- **Commit messages** — theo format Conventional Commits: `feat:`, `fix:`, `chore:`, v.v.
  - Ví dụ: `feat(helios): show recommendation in AI report panel`
  - Ví dụ: `fix(admin): make job poller non-blocking`
- **Scope** — dùng `(helios)` hoặc `(admin)` hoặc `(prometheus)` để chỉ rõ app bị ảnh hưởng

---

## Quy trình Pull Request

Chưa có PR template chính thức (`.github/PULL_REQUEST_TEMPLATE.md`). Khi tạo PR, hãy tuân thủ các bước sau:

- **Mô tả rõ ràng** — giải thích tính năng/bug fix, kèm context và lý do thay đổi.
- **Chạy tests** — đảm bảo `uv run pytest` pass toàn bộ (326+ tests, async-aware, timeout 30s).
- **Chạy lint** — `uv run ruff check src/ tests/` cho backend, `npm run lint` cho frontend.
- **Commit messages** — sử dụng Conventional Commits format (`feat:`, `fix:`, `chore:`).
- **Async compliance** — mọi I/O mới phải dùng `async def`, không blocking calls.
- **Tiếng Việt** — giữ nhất quán ngôn ngữ trong comments, prompts, và tài liệu.

---

## Tài liệu liên quan

- [README.md](../README.md) — Tổng quan project
- [ARCHITECTURE.md](./ARCHITECTURE.md) — Kiến trúc hệ thống và component diagram
- [CONFIGURATION.md](./CONFIGURATION.md) — Chi tiết cấu hình environment variables
