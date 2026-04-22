<!-- generated-by: gsd-doc-writer -->
# Hướng dẫn cài đặt & chạy lần đầu

Tài liệu này hướng dẫn từng bước để cài đặt, cấu hình và chạy LocalStock từ đầu — bao gồm backend **Prometheus** (Python/FastAPI), frontend **Helios** (Next.js), database (Supabase), và AI engine (Ollama).

> 📌 Xem [CONFIGURATION.md](CONFIGURATION.md) để biết chi tiết đầy đủ về từng biến môi trường.

---

## Yêu cầu hệ thống

| Component | Yêu cầu tối thiểu | Khuyến nghị |
|-----------|-------------------|-------------|
| **Python** | 3.12+ | 3.12 |
| **Node.js** | 18+ | 20+ LTS |
| **PostgreSQL** | 15+ | Supabase free tier |
| **GPU** | Không bắt buộc | RTX 3060 12GB (cho Ollama LLM) |
| **RAM** | 8GB | 16GB |
| **Disk** | 2GB | 5GB (bao gồm model LLM) |

**Công cụ cần cài trước:**

- **[uv](https://docs.astral.sh/uv/)** — Python package manager (thay thế pip/poetry)
- **[Node.js](https://nodejs.org/)** 18+ với npm
- **[Ollama](https://ollama.com/)** — Local LLM runtime *(tùy chọn, cần GPU)*
- Tài khoản **[Supabase](https://supabase.com/)** (free tier) hoặc PostgreSQL local

---

## Bước 1: Clone & cài đặt dependencies

```bash
# Clone repository
git clone https://github.com/khanhtoan26/localstock.git
cd localstock

# Cài uv (nếu chưa có)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài Python dependencies (từ thư mục gốc monorepo)
uv sync

# Cài Frontend dependencies
cd apps/helios
npm install
cd ../..
```

> 💡 `uv sync` sẽ tạo virtual environment tự động và cài toàn bộ dependencies cho workspace `apps/prometheus`.

---

## Bước 2: Cấu hình biến môi trường

```bash
cp .env.example .env
```

Mở file `.env` và cập nhật **ít nhất** các biến bắt buộc:

```env
# === BẮT BUỘC ===
# Port 6543 = PgBouncer transaction pooling (cho ứng dụng)
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0

# Port 5432 = Session mode (cho Alembic migrations)
DATABASE_URL_MIGRATION=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

Các biến còn lại đều có giá trị mặc định hợp lý — xem [CONFIGURATION.md](CONFIGURATION.md) để tùy chỉnh chi tiết.

### Biến quan trọng (tùy chọn)

| Biến | Mặc định | Ghi chú |
|------|----------|---------|
| `OLLAMA_HOST` | `http://localhost:11434` | URL Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:14b-instruct-q4_K_M` | Model AI sử dụng |
| `TELEGRAM_BOT_TOKEN` | *(trống)* | Để trống = tắt thông báo |
| `TELEGRAM_CHAT_ID` | *(trống)* | Để trống = tắt thông báo |

---

## Bước 3: Tạo database Supabase

1. Đăng ký tại [supabase.com](https://supabase.com) (miễn phí)
2. Tạo project mới, chọn region **Singapore** (`ap-southeast-1`) để giảm latency
3. Vào **Settings → Database → Connection string (URI)**
4. Copy 2 connection strings và dán vào `.env`:
   - **Port 6543** (Transaction pooling / PgBouncer) → `DATABASE_URL`
   - **Port 5432** (Session mode / Direct) → `DATABASE_URL_MIGRATION`

> ⚠️ **Quan trọng:** Khi dùng asyncpg qua PgBouncer (port 6543), **phải** thêm `?prepared_statement_cache_size=0` vào cuối connection string.

---

## Bước 4: Chạy database migrations

```bash
uv run python apps/prometheus/bin/init_db.py
```

Kết quả thành công:

```
Initializing database schema...
✅ Database schema initialized successfully!
```

Script này chạy `alembic upgrade head` bên trong `apps/prometheus/`, tạo toàn bộ bảng cần thiết (stocks, prices, indicators, scores, reports, ...).

> ⚠️ **BẮT BUỘC** chạy bước này trước khi khởi động backend. Nếu bỏ qua sẽ gặp lỗi `relation "..." does not exist`.

---

## Bước 5: Cài đặt Ollama + model AI (tùy chọn)

> 💡 Bước này **không bắt buộc**. Hệ thống vẫn hoạt động đầy đủ các tính năng crawl dữ liệu, phân tích kỹ thuật, phân tích cơ bản, scoring và dashboard — chỉ thiếu sentiment analysis và AI reports.

```bash
# Cài Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Khởi động Ollama server
ollama serve

# Tải model (trong terminal khác) — khoảng 9GB
ollama pull qwen2.5:14b-instruct-q4_K_M
```

### Chọn model phù hợp với GPU

| Model | VRAM cần | Chất lượng | Tốc độ |
|-------|----------|-----------|--------|
| `qwen2.5:7b-instruct-q4_K_M` | ~5GB | Tốt | Nhanh |
| `qwen2.5:14b-instruct-q4_K_M` | ~10GB | Rất tốt *(mặc định)* | Trung bình |
| `qwen2.5:32b-instruct-q4_K_M` | ~20GB | Xuất sắc | Chậm |

Đổi model trong `.env`: `OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M`

Kiểm tra Ollama đang chạy:

```bash
curl http://localhost:11434/api/version
```

### Không có GPU?

LocalStock vẫn chạy tốt mà không cần Ollama:

- ✅ Crawl dữ liệu giá / BCTC / corporate actions
- ✅ Phân tích kỹ thuật (11 chỉ báo: SMA, EMA, RSI, MACD, Bollinger Bands, ...)
- ✅ Phân tích cơ bản (P/E, P/B, ROE, ROA, D/E)
- ✅ Scoring tổng hợp (dựa trên tech + fundamental)
- ✅ Web dashboard đầy đủ
- ❌ Sentiment analysis (cần LLM)
- ❌ AI reports tiếng Việt (cần LLM)

---

## Bước 6: Khởi động hệ thống

Cần mở **3 terminal** riêng biệt:

### Terminal 1 — Backend API (port 8000)

```bash
uv run uvicorn localstock.api.app:app --reload
```

Kiểm tra: mở http://localhost:8000/health hoặc http://localhost:8000/docs (Swagger UI)

### Terminal 2 — Frontend (port 3000)

```bash
cd apps/helios
npm run dev
```

Kiểm tra: mở http://localhost:3000

### Terminal 3 — Ollama (port 11434, nếu dùng AI)

```bash
ollama serve
```

> 💡 Nếu Ollama đã chạy từ bước 5, không cần chạy lại.

---

## Bước 7: Chạy pipeline lần đầu

Sau khi cả 3 service đều chạy, bạn có thể trigger pipeline để crawl dữ liệu và phân tích:

### Cách 1: Admin Console (khuyến nghị)

1. Mở http://localhost:3000/admin
2. **Quản lý cổ phiếu:** Thêm/xóa mã cổ phiếu muốn theo dõi
3. **Trigger pipeline:** Nhấn nút để chạy từng bước hoặc chạy full pipeline
4. **Theo dõi trạng thái:** Xem tiến trình job realtime trên giao diện

### Cách 2: API (curl)

```bash
# Trigger toàn bộ pipeline (crawl → analyze → score → report → notify)
curl -X POST http://localhost:8000/api/automation/run

# Kiểm tra trạng thái pipeline
curl http://localhost:8000/api/automation/status
```

> ⏱️ Pipeline đầy đủ mất khoảng 15-30 phút tùy số lượng mã cổ phiếu và tốc độ GPU (cho LLM).

### Xem kết quả

Sau khi pipeline hoàn tất:

- 🌐 **Dashboard:** http://localhost:3000 — Bảng xếp hạng, tổng quan thị trường
- 📊 **Rankings:** http://localhost:3000/rankings — Top cổ phiếu theo điểm số
- 📈 **Chi tiết mã:** http://localhost:3000/stock/VNM — Biểu đồ nến, phân tích, báo cáo AI
- 🏦 **Thị trường:** http://localhost:3000/market — Macro, sector analysis
- 📖 **Trang học:** http://localhost:3000/learn — Giải thích chỉ báo, thuật ngữ
- 🛠️ **Admin:** http://localhost:3000/admin — Quản lý, trigger pipeline
- 📡 **API Docs:** http://localhost:8000/docs — Swagger UI

---

## Pipeline tự động hàng ngày

Khi backend chạy, **APScheduler** tự động trigger pipeline hàng ngày vào **15:45 giờ Việt Nam** (sau khi thị trường đóng cửa):

```
15:45 → Crawl giá/tin tức → Phân tích kỹ thuật/cơ bản
      → LLM sentiment → Scoring → AI reports → Telegram alert
```

Pipeline chỉ chạy vào **ngày giao dịch** (thứ Hai - thứ Sáu, trừ lễ VN). Có thể thay đổi giờ chạy qua `SCHEDULER_RUN_HOUR` và `SCHEDULER_RUN_MINUTE` trong `.env`.

---

## Các lỗi thường gặp

### `relation "..." does not exist`

**Nguyên nhân:** Chưa chạy database migrations.

**Giải pháp:**
```bash
uv run python apps/prometheus/bin/init_db.py
```

### `Connection refused` khi truy cập API

**Nguyên nhân:** Backend chưa khởi động hoặc database URL sai.

**Giải pháp:**
1. Kiểm tra backend đang chạy: `uv run uvicorn localstock.api.app:app --reload`
2. Kiểm tra `DATABASE_URL` trong `.env` đã đúng

### Dashboard trắng hoặc lỗi CORS

**Nguyên nhân:** Backend và frontend không chạy đúng port mặc định.

**Giải pháp:** Đảm bảo backend chạy ở port **8000** và frontend ở port **3000**. Backend đã cấu hình CORS middleware cho `localhost:3000`.

### Ollama timeout khi tạo report

**Nguyên nhân:** Model quá lớn cho GPU hiện tại.

**Giải pháp:** Dùng model nhỏ hơn trong `.env`:
```env
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
```

### vnstock lỗi rate limit

**Nguyên nhân:** Crawl quá nhanh, bị vnstock giới hạn request.

**Giải pháp:** Tăng delay trong `.env`:
```env
CRAWL_DELAY_SECONDS=2.0
```

### `prepared_statement_cache_size` error với Supabase

**Nguyên nhân:** Thiếu parameter khi kết nối qua PgBouncer.

**Giải pháp:** Thêm `?prepared_statement_cache_size=0` vào cuối `DATABASE_URL`:
```env
DATABASE_URL=postgresql+asyncpg://...@....supabase.com:6543/postgres?prepared_statement_cache_size=0
```

---

## Tài liệu tiếp theo

| Tài liệu | Nội dung |
|-----------|----------|
| [CONFIGURATION.md](CONFIGURATION.md) | Chi tiết từng biến môi trường, giá trị mặc định, cấu hình theo môi trường |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc hệ thống, workflow pipeline, design patterns |
| [SETUP.md](SETUP.md) | Hướng dẫn cài đặt chi tiết (legacy — tham khảo thêm) |
