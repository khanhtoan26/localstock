<!-- generated-by: gsd-doc-writer -->
# Cấu hình (Configuration)

Tài liệu này mô tả toàn bộ các biến môi trường và cấu hình cần thiết để vận hành hệ thống LocalStock — bao gồm backend **Prometheus** (Python/FastAPI) và frontend **Helios** (Next.js).

## Tổng quan cơ chế cấu hình

Toàn bộ cấu hình backend được quản lý thông qua **Pydantic BaseSettings** trong file `apps/prometheus/src/localstock/config.py`. Các biến môi trường được tải tự động từ file `.env` tại thư mục gốc của dự án (monorepo root). Hệ thống tự động tìm kiếm file `.env` bằng cách duyệt ngược từ thư mục hiện tại lên thư mục cha cho đến khi tìm thấy hoặc gặp thư mục `.git`.

```python
from localstock.config import get_settings

settings = get_settings()  # Singleton, cached với @lru_cache
```

Frontend Helios sử dụng biến `NEXT_PUBLIC_*` theo chuẩn Next.js.

File mẫu `.env.example` nằm tại thư mục gốc dự án — sao chép làm điểm khởi đầu:

```bash
cp .env.example .env
```

## Biến môi trường

### Database (PostgreSQL / Supabase)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `DATABASE_URL` | Có | `postgresql+asyncpg://localhost:5432/localstock` | Connection string cho ứng dụng. Dùng port **6543** (PgBouncer transaction pooling) khi kết nối Supabase. Cần thêm `?prepared_statement_cache_size=0` cho asyncpg qua PgBouncer. |
| `DATABASE_URL_MIGRATION` | Không | `""` (rỗng — fallback về `DATABASE_URL`) | Connection string cho Alembic migrations. Dùng port **5432** (session mode / kết nối trực tiếp) khi kết nối Supabase. Nếu để trống, Alembic sẽ dùng `DATABASE_URL`. |

**Ví dụ cho Supabase:**

```env
# Port 6543 = transaction pooling (PgBouncer) — cho kết nối ứng dụng
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0

# Port 5432 = session mode — cho Alembic migrations
DATABASE_URL_MIGRATION=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

### vnstock (Nguồn dữ liệu chứng khoán)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `VNSTOCK_SOURCE` | Không | `VCI` | Nguồn dữ liệu chứng khoán (VCI, TCBS, ...). |
| `VNSTOCK_API_KEY` | Không | `""` (rỗng) | API key cho vnstock. Lấy tại https://vnstocks.com/insiders-program. Để trống cho community tier. |

### Crawl (Thu thập dữ liệu)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `CRAWL_DELAY_SECONDS` | Không | `1.0` | Thời gian chờ giữa các request crawl (giây). Tránh bị rate-limit. |
| `CRAWL_BATCH_SIZE` | Không | `50` | Số lượng mã xử lý mỗi batch khi crawl. |

### Logging

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `LOG_LEVEL` | Không | `INFO` | Mức log (DEBUG, INFO, WARNING, ERROR, CRITICAL). |

### Ollama LLM (AI / Trí tuệ nhân tạo)

Hệ thống hoạt động bình thường không cần Ollama — chỉ thiếu các tính năng AI (phân tích sentiment, tạo báo cáo). Client tự động kiểm tra health trước mỗi lời gọi và bỏ qua nếu Ollama không khả dụng.

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `OLLAMA_HOST` | Không | `http://localhost:11434` | URL của Ollama server. |
| `OLLAMA_MODEL` | Không | `qwen2.5:14b-instruct-q4_K_M` | Tên model Ollama sử dụng cho sentiment và report. |
| `OLLAMA_TIMEOUT` | Không | `120` | Timeout cho mỗi request tới Ollama (giây). |
| `OLLAMA_KEEP_ALIVE` | Không | `30m` | Thời gian giữ model trong RAM sau lần gọi cuối. |

### Scoring Weights (Trọng số chấm điểm)

Trọng số của 4 chiều phân tích, **tổng phải bằng 1.0**.

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `SCORING_WEIGHT_TECHNICAL` | Không | `0.30` | Trọng số phân tích kỹ thuật. |
| `SCORING_WEIGHT_FUNDAMENTAL` | Không | `0.30` | Trọng số phân tích cơ bản. |
| `SCORING_WEIGHT_SENTIMENT` | Không | `0.20` | Trọng số phân tích tâm lý thị trường. |
| `SCORING_WEIGHT_MACRO` | Không | `0.20` | Trọng số phân tích vĩ mô. |

Cấu hình này được đọc qua `ScoringConfig.from_settings()` trong `apps/prometheus/src/localstock/scoring/config.py`.

### Funnel Settings (Bộ lọc cổ phiếu)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `FUNNEL_TOP_N` | Không | `50` | Số cổ phiếu top đưa vào phân tích sentiment bằng LLM. |
| `SENTIMENT_ARTICLES_PER_STOCK` | Không | `5` | Số bài báo lấy cho mỗi mã cổ phiếu khi phân tích sentiment. |
| `SENTIMENT_LOOKBACK_DAYS` | Không | `7` | Số ngày nhìn lại khi lấy tin tức cho phân tích sentiment. |

### Report Generation (Tạo báo cáo)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `REPORT_TOP_N` | Không | `20` | Số cổ phiếu top để tạo báo cáo AI chi tiết. |
| `REPORT_MAX_TOKENS` | Không | `4096` | Context window cho LLM khi tạo báo cáo. |

### SSL

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `SSL_VERIFY` | Không | `true` | Bật/tắt xác minh SSL. Đặt `false` nếu đứng sau corporate proxy dùng self-signed cert. Khi tắt, hệ thống patch `requests.Session` và tắt cảnh báo urllib3. |

### Telegram Notifications (Thông báo)

Để trống cả hai biến để tắt thông báo Telegram. Hệ thống tự động bỏ qua nếu không cấu hình.

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `TELEGRAM_BOT_TOKEN` | Không | `""` (rỗng) | Token của Telegram Bot. Lấy từ @BotFather. |
| `TELEGRAM_CHAT_ID` | Không | `""` (rỗng) | ID chat/group nhận thông báo. |

### Scheduler (Lịch chạy tự động)

Pipeline chạy tự động hàng ngày vào các ngày trong tuần (thứ Hai - thứ Sáu) theo múi giờ `Asia/Ho_Chi_Minh`.

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `SCHEDULER_RUN_HOUR` | Không | `15` | Giờ chạy pipeline hàng ngày (0-23, múi giờ VN). |
| `SCHEDULER_RUN_MINUTE` | Không | `45` | Phút chạy pipeline hàng ngày (0-59). |

Mặc định chạy lúc **15:45 giờ Việt Nam** — sau khi thị trường đóng cửa phiên chiều (14:45).

### Score Change Alert (Cảnh báo biến động)

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `SCORE_CHANGE_THRESHOLD` | Không | `15.0` | Ngưỡng thay đổi điểm số (%) để kích hoạt cảnh báo. |

### Frontend — Helios (Next.js)

Biến môi trường frontend được đặt trong file `.env.local` tại `apps/helios/`.

| Biến | Bắt buộc | Giá trị mặc định | Mô tả |
|------|----------|-------------------|-------|
| `NEXT_PUBLIC_API_URL` | Không | `http://localhost:8000` | URL gốc của Prometheus API backend. |

## Cài đặt bắt buộc vs tùy chọn

### Bắt buộc để hệ thống hoạt động

| Cài đặt | Lý do |
|---------|-------|
| `DATABASE_URL` | Không có database, ứng dụng không thể khởi động. Giá trị mặc định chỉ hoạt động nếu có PostgreSQL local. |

### Tùy chọn nhưng khuyến nghị

| Cài đặt | Tác động khi thiếu |
|---------|-------------------|
| `DATABASE_URL_MIGRATION` | Alembic migration dùng `DATABASE_URL` thay thế. Với Supabase, cần port 5432 riêng cho migration. |
| `OLLAMA_HOST` + `OLLAMA_MODEL` | Không có tính năng AI: phân tích sentiment trả về null, không tạo được báo cáo. |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Không gửi thông báo. Pipeline vẫn chạy bình thường. |
| `VNSTOCK_API_KEY` | Dùng community tier với giới hạn request. |

## Giá trị mặc định

Tất cả giá trị mặc định được định nghĩa trực tiếp trong class `Settings` tại `apps/prometheus/src/localstock/config.py`:

```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/localstock"
    database_url_migration: str = ""
    vnstock_source: str = "VCI"
    vnstock_api_key: str = ""
    crawl_delay_seconds: float = 1.0
    crawl_batch_size: int = 50
    log_level: str = "INFO"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    ollama_timeout: int = 120
    ollama_keep_alive: str = "30m"
    scoring_weight_technical: float = 0.30
    scoring_weight_fundamental: float = 0.30
    scoring_weight_sentiment: float = 0.20
    scoring_weight_macro: float = 0.20
    funnel_top_n: int = 50
    sentiment_articles_per_stock: int = 5
    sentiment_lookback_days: int = 7
    report_top_n: int = 20
    report_max_tokens: int = 4096
    ssl_verify: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    scheduler_run_hour: int = 15
    scheduler_run_minute: int = 45
    score_change_threshold: float = 15.0
```

## Cấu hình theo môi trường

### Development (Phát triển)

1. Sao chép file mẫu:
   ```bash
   cp .env.example .env
   ```
2. Cập nhật `DATABASE_URL` trỏ tới PostgreSQL local hoặc Supabase dev project.
3. Cài Ollama local nếu muốn test tính năng AI:
   ```bash
   ollama pull qwen2.5:14b-instruct-q4_K_M
   ```
4. Bỏ trống `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` để tắt thông báo.

### Production (Sản xuất)

- Đặt `DATABASE_URL` trỏ tới Supabase production (port 6543 với PgBouncer).
- Đặt `DATABASE_URL_MIGRATION` trỏ tới port 5432 (direct connection).
- Cấu hình `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` để nhận thông báo hàng ngày.
- Giữ `SSL_VERIFY=true` (mặc định).
- Điều chỉnh `SCHEDULER_RUN_HOUR` / `SCHEDULER_RUN_MINUTE` nếu cần thay đổi giờ chạy pipeline.
- Đặt `NEXT_PUBLIC_API_URL` cho frontend Helios trỏ tới URL API production.
- Cân nhắc điều chỉnh scoring weights theo chiến lược đầu tư.

### Cấu hình Supabase connection

Supabase cung cấp hai loại connection string:

| Port | Chế độ | Dùng cho | Biến |
|------|--------|----------|------|
| **6543** | Transaction pooling (PgBouncer) | Kết nối ứng dụng (nhiều kết nối đồng thời) | `DATABASE_URL` |
| **5432** | Session mode (Direct) | Alembic migrations (cần persistent connection) | `DATABASE_URL_MIGRATION` |

> **Lưu ý:** Khi dùng asyncpg qua PgBouncer (port 6543), cần thêm `?prepared_statement_cache_size=0` vào connection string để tránh lỗi prepared statement.
