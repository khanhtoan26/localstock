# Kết nối Database — Hướng dẫn chi tiết

Tài liệu này giải thích toàn bộ cơ chế kết nối database của LocalStock: tại sao có 2 URL, tại sao dùng PgBouncer, cách code xử lý tự động, và cách debug khi có lỗi.

---

## Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                        LocalStock App                        │
│                                                             │
│  FastAPI + APScheduler          Alembic migrations          │
│         │                              │                    │
│  DATABASE_URL (port 6543)   DATABASE_URL_MIGRATION (5432)   │
└──────────┼──────────────────────────────┼───────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│  Supabase Supavisor  │    │  Supabase Supavisor          │
│  Transaction Mode    │    │  Session Mode                │
│  Port 6543           │    │  Port 5432                   │
│  (connection pool)   │    │  (persistent connection)     │
└──────────┬───────────┘    └──────────────┬───────────────┘
           │                               │
           └──────────────┬────────────────┘
                          ▼
               ┌──────────────────┐
               │  PostgreSQL 17   │
               │  Supabase Cloud  │
               └──────────────────┘
```

---

## Tại sao cần 2 URL khác nhau?

### `DATABASE_URL` — Port 6543 (Transaction mode)

Dùng cho **ứng dụng chạy thực tế** (FastAPI + APScheduler).

- Kết nối qua **Supavisor** (connection pooler của Supabase)
- Nhiều request chia sẻ ít connection thực tới PostgreSQL
- Tiết kiệm tài nguyên: app có thể tạo 100 async requests nhưng chỉ dùng 3–8 connection thực
- **Hạn chế:** không hỗ trợ prepared statements qua các connection khác nhau (xem bên dưới)

### `DATABASE_URL_MIGRATION` — Port 5432 (Session mode)

Dùng riêng cho **Alembic migrations**.

- Kết nối trực tiếp, session liên tục không bị gián đoạn
- Alembic cần session mode vì dùng DDL statements (`CREATE TABLE`, `ALTER TABLE`) không tương thích với transaction pooling
- Nếu bỏ trống, Alembic fallback về `DATABASE_URL` (không khuyến nghị)

---

## Vấn đề Prepared Statements với PgBouncer

### Vấn đề là gì?

asyncpg (Python PostgreSQL driver) mặc định dùng **prepared statements** để tối ưu tốc độ:

```
App → "PREPARE stmt_1 AS SELECT * FROM stocks WHERE symbol = $1"
App → "EXECUTE stmt_1('VNM')"
```

Prepared statement được lưu trong PostgreSQL **session**. Khi dùng PgBouncer transaction mode, mỗi query có thể đi qua connection khác nhau — session cũ không còn prepared statement → lỗi `DuplicatePreparedStatementError`.

### Cách LocalStock xử lý

`database.py` tắt hoàn toàn prepared statement cache khi tạo engine:

```python
create_async_engine(
    settings.database_url,
    connect_args={
        "prepared_statement_cache_size": 0,  # tắt SQLAlchemy cache
        "statement_cache_size": 0,           # tắt asyncpg native cache
    },
)
```

**Bạn không cần làm gì thêm.** Chỉ cần dán URL từ Supabase vào `.env` là xong.

> ⚠️ Các tài liệu cũ hướng dẫn thêm `?prepared_statement_cache_size=0` vào cuối URL — cách này đã lỗi thời, không cần thiết nữa.

---

## Cách lấy URL từ Supabase Dashboard

### Bước 1: Vào phần Connection Pooling

1. Đăng nhập **app.supabase.com**
2. Chọn project
3. Vào **Settings → Database → Connection pooling**

### Bước 2: Copy Transaction mode URL (port 6543)

```
Mode: Transaction
Host: aws-X-ap-southeast-X.pooler.supabase.com
Port: 6543
```

Copy connection string URI → dán vào `DATABASE_URL`.

### Bước 3: Copy Session mode URL (port 5432)

```
Mode: Session
Host: aws-X-ap-southeast-X.pooler.supabase.com
Port: 5432
```

Copy connection string URI → dán vào `DATABASE_URL_MIGRATION`.

### Kết quả trong `.env`

```env
# Paste trực tiếp từ Supabase — không cần sửa gì thêm
DATABASE_URL=postgresql://postgres.abcdefgh:your-password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
DATABASE_URL_MIGRATION=postgresql://postgres.abcdefgh:your-password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

> `postgresql://` (không có `+asyncpg`) là đúng — `config.py` tự động convert sang driver chuẩn khi load.

---

## Cách code xử lý URL tự động

### 1. `config.py` — Validator tự động convert driver

```python
@field_validator("database_url", mode="before")
def ensure_asyncpg_driver(cls, v: str) -> str:
    if v.startswith("postgresql://") or v.startswith("postgres://"):
        v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
    return v
```

Dán `postgresql://...` → tự động thành `postgresql+asyncpg://...`.

### 2. `database.py` — Engine với cấu hình PgBouncer-safe

```python
_engine = create_async_engine(
    settings.database_url,
    pool_size=3,           # 3 connection trong pool
    max_overflow=5,        # thêm tối đa 5 khi quá tải
    pool_recycle=300,      # recycle connection sau 5 phút
    pool_pre_ping=True,    # kiểm tra connection trước khi dùng
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)
```

### 3. `alembic/env.py` — Migration URL fallback

```python
url = settings.database_url_migration or settings.database_url
# Cũng tự convert postgresql:// → postgresql+asyncpg://
```

---

## Troubleshooting

### `Circuit breaker open: Unable to establish connection to upstream database`

Supabase Supavisor không thể kết nối tới PostgreSQL upstream. Nguyên nhân phổ biến:

| Nguyên nhân | Kiểm tra | Giải pháp |
|-------------|----------|-----------|
| Project bị pause | app.supabase.com → xem banner | Nhấn "Resume project" |
| Supabase downtime | status.supabase.com | Chờ hoặc dùng direct connection |
| Connection pool cạn kiệt | Dashboard → Database → Connections | Restart app, giảm `pool_size` |

**Test nhanh:**
```bash
uv run python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import sqlalchemy as sa

async def test():
    engine = create_async_engine(
        'postgresql+asyncpg://USER:PASS@HOST:6543/postgres',
        connect_args={'statement_cache_size': 0, 'prepared_statement_cache_size': 0}
    )
    async with engine.connect() as c:
        print(await c.scalar(sa.text('SELECT 1')))
    await engine.dispose()

asyncio.run(test())
"
```

### `DuplicatePreparedStatementError: prepared statement already exists`

asyncpg prepared statement xung đột với PgBouncer transaction mode.

**Nguyên nhân:** `statement_cache_size=0` chưa được set trong engine config.

**Giải pháp:** Đảm bảo `database.py` có đủ cả 2 params:
```python
connect_args={
    "prepared_statement_cache_size": 0,
    "statement_cache_size": 0,
}
```

### `relation "stocks" does not exist` (hoặc bảng bất kỳ)

Migration chưa chạy.

```bash
uv run python apps/prometheus/bin/init_db.py
```

### `InvalidCatalogNameError: database "postgres" does not exist`

Sai database name trong URL. Supabase dùng `postgres` (không phải `localstock`).

### Supabase free tier bị pause

Free tier **tự động pause** sau 7 ngày không có query. Sau khi resume, DB mất khoảng 30–60 giây để cold start.

Để tránh bị pause: chạy 1 query đơn giản định kỳ, hoặc upgrade lên Pro tier ($25/tháng).

---

## Kiểm tra kết nối

Script kiểm tra nhanh toàn bộ stack:

```bash
uv run python3 - <<'EOF'
import asyncio, sys
sys.path.insert(0, 'apps/prometheus/src')

async def main():
    from localstock.db.database import get_engine
    import sqlalchemy as sa

    engine = get_engine()
    try:
        async with engine.connect() as conn:
            db = await conn.scalar(sa.text('SELECT current_database()'))
            ver = await conn.scalar(sa.text('SELECT version()'))
            tables = await conn.scalar(sa.text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))
            print(f"✅ DB: {db}")
            print(f"✅ Version: {ver[:40]}")
            print(f"✅ Tables: {tables} bảng trong schema public")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
    finally:
        await engine.dispose()

asyncio.run(main())
EOF
```

---

## Tóm tắt nhanh

| Việc cần làm | Hành động |
|--------------|-----------|
| Lần đầu setup | Copy 2 URL từ Supabase → paste vào `.env` → chạy `init_db.py` |
| DB lỗi circuit breaker | Vào Supabase Dashboard → kiểm tra project có bị pause không |
| Lỗi prepared statement | Kiểm tra `database.py` có `statement_cache_size=0` |
| Thêm bảng mới | Tạo Alembic migration → `uv run alembic upgrade head` |
| Xem schema hiện tại | `cd apps/prometheus && uv run alembic current` |
