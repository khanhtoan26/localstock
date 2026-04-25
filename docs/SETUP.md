# Hướng dẫn cài đặt LocalStock

## Yêu cầu hệ thống

| Component | Yêu cầu tối thiểu | Khuyến nghị |
|-----------|-------------------|-------------|
| Python | 3.12+ | 3.12 |
| Node.js | 18+ | 20+ LTS |
| PostgreSQL | 15+ | Supabase free tier |
| GPU | Không bắt buộc | RTX 3060 12GB (cho LLM) |
| RAM | 8GB | 16GB |
| Disk | 2GB | 5GB (bao gồm model LLM) |

## 1. Database (Supabase)

### Tạo project Supabase

1. Đăng ký tại [supabase.com](https://supabase.com) (miễn phí)
2. Tạo project mới, chọn region **Singapore** (`ap-southeast-1`)
3. Lấy connection string:
   - Vào **Settings → Database → Connection pooling**
   - Copy 2 URLs và dán trực tiếp vào `.env`:

```env
# Port 6543 = Transaction mode pooler (cho ứng dụng)
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres

# Port 5432 = Session mode (cho Alembic migrations)
DATABASE_URL_MIGRATION=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

> Dán URL trực tiếp — ứng dụng tự xử lý driver và prepared statement settings. Xem giải thích chi tiết tại [DATABASE.md](DATABASE.md).

### Chạy migrations

```bash
# Áp dụng tất cả migrations
cd apps/prometheus && uv run alembic upgrade head

# Kiểm tra migration hiện tại
cd apps/prometheus && uv run alembic current

# Rollback 1 step (nếu cần)
cd apps/prometheus && uv run alembic downgrade -1
```

Migrations tạo các bảng:
- `stocks`, `stock_prices` — Dữ liệu giá/mã
- `financial_statements`, `company_profiles` — BCTC, thông tin công ty
- `technical_indicators`, `financial_ratios` — Chỉ báo phân tích
- `industry_groups`, `industry_averages` — Phân ngành ICB
- `news_articles`, `sentiment_scores` — Tin tức, sentiment
- `stock_scores`, `composite_scores` — Điểm xếp hạng
- `macro_indicators`, `stock_reports` — Vĩ mô, báo cáo AI
- `pipeline_runs`, `sector_snapshots` — Pipeline tự động
- `score_changes`, `notifications_sent` — Alert, thông báo

## 2. Backend (Python)

### Cài đặt

```bash
# Cài uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài dependencies
uv sync

# Chạy tests (326 tests)
uv run pytest
```

### Cấu hình `.env`

```bash
cp .env.example .env
```

Sửa file `.env`:

```env
# === BẮT BUỘC ===
DATABASE_URL=postgresql+asyncpg://...         # Supabase URL (port 6543)
DATABASE_URL_MIGRATION=postgresql+asyncpg://...  # Migration URL (port 5432)

# === TÙY CHỌN (có giá trị mặc định) ===

# Data Sources
VNSTOCK_SOURCE=VCI                            # Nguồn dữ liệu vnstock
CRAWL_DELAY_SECONDS=1.0                       # Delay giữa các request
CRAWL_BATCH_SIZE=50                           # Số mã crawl mỗi batch

# Logging
LOG_LEVEL=INFO                                # DEBUG | INFO | WARNING | ERROR

# LLM (Ollama)
OLLAMA_HOST=http://localhost:11434             # Ollama server URL
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M     # Model LLM
OLLAMA_TIMEOUT=120                            # Timeout (giây)
OLLAMA_KEEP_ALIVE=30m                         # Giữ model trong RAM

# Scoring Weights (tổng = 1.0)
SCORING_WEIGHT_TECHNICAL=0.30                 # Trọng số kỹ thuật
SCORING_WEIGHT_FUNDAMENTAL=0.30               # Trọng số cơ bản
SCORING_WEIGHT_SENTIMENT=0.20                 # Trọng số sentiment
SCORING_WEIGHT_MACRO=0.20                     # Trọng số vĩ mô

# Funnel Settings
FUNNEL_TOP_N=50                               # Top N mã cho LLM sentiment
SENTIMENT_ARTICLES_PER_STOCK=5                # Số bài viết/mã
SENTIMENT_LOOKBACK_DAYS=7                     # Nhìn lại N ngày

# Reports
REPORT_TOP_N=20                               # Số mã tạo báo cáo
REPORT_MAX_TOKENS=4096                        # LLM context window

# Telegram (để trống = tắt notifications)
TELEGRAM_BOT_TOKEN=                           # Token từ @BotFather
TELEGRAM_CHAT_ID=                             # Chat ID của bạn

# Scheduler
SCHEDULER_RUN_HOUR=15                         # Giờ chạy pipeline (VN time)
SCHEDULER_RUN_MINUTE=45                       # Phút chạy pipeline

# Alerts
SCORE_CHANGE_THRESHOLD=15.0                   # Ngưỡng biến động (%)

# SSL
SSL_VERIFY=true                               # false nếu dùng proxy
```

### Khởi động backend

```bash
# Development (auto-reload)
uv run uvicorn localstock.api.app:app --reload --host 0.0.0.0 --port 8000

# Production
uv run uvicorn localstock.api.app:app --host 0.0.0.0 --port 8000 --workers 1
```

> 💡 **workers=1** vì đây là tool cá nhân, APScheduler cần chạy trong 1 process.

Truy cập:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 3. Frontend (Next.js)

### Cài đặt

```bash
cd apps/helios
npm install
```

### Khởi động

```bash
# Development
npm run dev          # http://localhost:3000

# Production build
npm run build
npm run start
```

> Frontend kết nối backend tại `http://localhost:8000`. Backend đã có CORS middleware cho `localhost:3000`.

### Các trang

| URL | Mô tả |
|-----|-------|
| `/` | Trang chủ — redirect đến Rankings |
| `/rankings` | Bảng xếp hạng cổ phiếu theo điểm |
| `/market` | Tổng quan thị trường, macro, sector |
| `/stock/[symbol]` | Chi tiết mã (biểu đồ, phân tích, báo cáo AI) |

## 4. Ollama LLM

### Cài đặt

```bash
# Cài Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Khởi động service
ollama serve

# Tải model (trong terminal khác)
ollama pull qwen2.5:14b-instruct-q4_K_M

# Kiểm tra
curl http://localhost:11434/api/version
```

### Chọn model phù hợp

| Model | VRAM | Chất lượng | Tốc độ |
|-------|------|-----------|--------|
| `qwen2.5:7b-instruct-q4_K_M` | ~5GB | Tốt | Nhanh |
| `qwen2.5:14b-instruct-q4_K_M` | ~10GB | Rất tốt | Trung bình |
| `qwen2.5:32b-instruct-q4_K_M` | ~20GB | Xuất sắc | Chậm |

> Đổi model trong `.env`: `OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M`

### Không có GPU?

LocalStock vẫn chạy được mà không cần Ollama. Các tính năng không dùng LLM:
- ✅ Crawl dữ liệu giá/BCTC/corporate actions
- ✅ Phân tích kỹ thuật (11 indicators)
- ✅ Phân tích cơ bản (P/E, ROE, etc.)
- ✅ Scoring (dựa trên tech + fund)
- ✅ Web dashboard
- ❌ Sentiment analysis (cần LLM)
- ❌ AI reports (cần LLM)

## 5. Telegram Bot

### Tạo bot

1. Mở Telegram, tìm `@BotFather`
2. Gửi `/newbot`, đặt tên và username
3. Copy token (dạng `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Lấy Chat ID

1. Mở bot vừa tạo, gửi `/start`
2. Truy cập: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Tìm `"chat":{"id":123456789}` — đó là chat ID của bạn

### Cấu hình

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Nội dung thông báo

- **Daily Digest** (hàng ngày sau pipeline): Top 10 mã đáng mua với điểm + lý do
- **Score Change Alert**: Khi điểm mã thay đổi >15 điểm so với phiên trước
- **Sector Rotation**: Báo cáo dòng tiền chảy giữa các ngành

## 6. Workflow hàng ngày

### Tự động (mặc định 15:45)

Khi backend chạy, APScheduler tự động trigger pipeline hàng ngày:

```
15:45 → Crawl giá/tin tức → Phân tích kỹ thuật/cơ bản
      → LLM sentiment → Scoring → AI reports → Telegram alert
```

Pipeline chỉ chạy vào **ngày giao dịch** (thứ 2-6, trừ lễ VN).

### Thủ công

```bash
# Chạy full pipeline ngay lập tức
curl -X POST http://localhost:8000/api/automation/run

# Phân tích 1 mã cụ thể
curl -X POST http://localhost:8000/api/automation/run/VNM

# Kiểm tra trạng thái pipeline
curl http://localhost:8000/api/automation/status

# Chỉ crawl tin tức
curl -X POST http://localhost:8000/api/news/crawl

# Chỉ chạy scoring
curl -X POST http://localhost:8000/api/scores/run

# Chỉ tạo reports
curl -X POST http://localhost:8000/api/reports/run
```

### Xem kết quả

```bash
# Top 20 mã theo điểm
curl http://localhost:8000/api/scores/top

# Chi tiết 1 mã
curl http://localhost:8000/api/scores/VNM
curl http://localhost:8000/api/analysis/VNM/technical
curl http://localhost:8000/api/reports/VNM

# Hoặc mở Dashboard: http://localhost:3000
```

## Troubleshooting

### `relation "composite_scores" does not exist`
→ Chưa chạy migrations. Chạy `cd apps/prometheus && uv run alembic upgrade head`

### `Connection refused` khi truy cập API
→ Backend chưa chạy. Chạy `uv run uvicorn localstock.api.app:app --reload`

### Dashboard trắng / lỗi CORS
→ Đảm bảo backend chạy ở port 8000 và frontend ở port 3000

### Ollama timeout
→ Model quá lớn cho GPU. Thử model nhỏ hơn: `OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M`

### vnstock lỗi rate limit
→ Tăng `CRAWL_DELAY_SECONDS=2.0` trong `.env`
