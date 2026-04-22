<!-- generated-by: gsd-doc-writer -->
# LocalStock API Reference

**Base URL:** `http://localhost:8000`

**Swagger UI:** `http://localhost:8000/docs`

**Xác thực:** Không yêu cầu — API chạy local, không có authentication middleware.

**CORS:** Chỉ cho phép origin `http://localhost:3000` (frontend Helios).

---

## Tổng quan Endpoints

| Method | Path | Mô tả | Tag |
|--------|------|-------|-----|
| GET | `/health` | Kiểm tra trạng thái hệ thống | health |
| GET | `/api/prices/{symbol}` | Lịch sử giá OHLCV | prices |
| GET | `/api/prices/{symbol}/indicators` | Time-series chỉ báo kỹ thuật | prices |
| GET | `/api/analysis/{symbol}/technical` | Chỉ báo kỹ thuật mới nhất | analysis |
| GET | `/api/analysis/{symbol}/fundamental` | Chỉ số tài chính | analysis |
| GET | `/api/analysis/{symbol}/trend` | Xu hướng giá và hỗ trợ/kháng cự | analysis |
| POST | `/api/analysis/run` | Trigger phân tích toàn bộ | analysis |
| GET | `/api/industry/groups` | Danh sách nhóm ngành | analysis |
| GET | `/api/industry/{group_code}/averages` | Chỉ số trung bình ngành | analysis |
| GET | `/api/scores/top` | Top mã theo điểm tổng hợp | scores |
| GET | `/api/scores/{symbol}` | Điểm tổng hợp 1 mã | scores |
| POST | `/api/scores/run` | Trigger chấm điểm toàn bộ | scores |
| GET | `/api/news` | Tin tức gần đây | news |
| GET | `/api/news/{symbol}/sentiment` | Sentiment cho 1 mã | news |
| POST | `/api/news/crawl` | Trigger crawl tin tức | news |
| POST | `/api/sentiment/run` | Trigger phân tích sentiment | news |
| GET | `/api/macro/latest` | Dữ liệu vĩ mô mới nhất | macro |
| POST | `/api/macro` | Nhập dữ liệu vĩ mô thủ công | macro |
| POST | `/api/macro/fetch-exchange-rate` | Lấy tỷ giá từ VCB | macro |
| GET | `/api/reports/top` | Báo cáo AI mới nhất | reports |
| GET | `/api/reports/{symbol}` | Báo cáo cho 1 mã | reports |
| POST | `/api/reports/run` | Trigger tạo báo cáo AI | reports |
| POST | `/api/automation/run` | Trigger full pipeline | automation |
| POST | `/api/automation/run/{symbol}` | Phân tích 1 mã cụ thể | automation |
| GET | `/api/automation/status` | Trạng thái scheduler | automation |
| GET | `/api/sectors/latest` | Sector snapshots | dashboard |
| GET | `/api/admin/stocks` | Danh sách mã theo dõi | admin |
| POST | `/api/admin/stocks` | Thêm mã vào watchlist | admin |
| DELETE | `/api/admin/stocks/{symbol}` | Xóa mã khỏi watchlist | admin |
| POST | `/api/admin/crawl` | Queue crawl job | admin |
| POST | `/api/admin/analyze` | Queue analysis job | admin |
| POST | `/api/admin/score` | Queue scoring job | admin |
| POST | `/api/admin/report` | Queue report job | admin |
| POST | `/api/admin/pipeline` | Queue full pipeline | admin |
| GET | `/api/admin/jobs` | Danh sách jobs gần đây | admin |
| GET | `/api/admin/jobs/{job_id}` | Chi tiết 1 job | admin |

---

## Health & Status

### `GET /health`

Kiểm tra trạng thái hệ thống, số liệu dữ liệu, và pipeline gần nhất.

**Response:**
```json
{
  "status": "healthy",
  "stocks": 400,
  "prices": 125000,
  "last_pipeline_run": {
    "status": "completed",
    "started_at": "2026-04-16T15:45:00+07:00",
    "completed_at": "2026-04-16T16:10:00+07:00",
    "symbols_total": 400,
    "symbols_success": 398,
    "symbols_failed": 2
  }
}
```

> Nếu chưa có pipeline nào chạy, `last_pipeline_run` sẽ là `null`.

---

## Prices & Indicators

### `GET /api/prices/{symbol}`

Lịch sử giá OHLCV cho 1 mã cổ phiếu (dùng cho candlestick chart).

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `symbol` | path | — | Mã cổ phiếu (VD: `VNM`). Regex: `^[A-Z0-9]+$` |
| `days` | query | 365 | Số ngày lịch sử (30-730) |

**Response:**
```json
{
  "symbol": "VNM",
  "count": 245,
  "prices": [
    {
      "time": "2026-04-16",
      "open": 72.5,
      "high": 73.2,
      "low": 72.0,
      "close": 72.8,
      "volume": 1250000
    }
  ]
}
```

### `GET /api/prices/{symbol}/indicators`

Time-series chỉ báo kỹ thuật (SMA, EMA, BB, MACD, RSI) theo ngày.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `symbol` | path | — | Mã cổ phiếu. Regex: `^[A-Z0-9]+$` |
| `days` | query | 365 | Số ngày lịch sử (30-730) |

**Response:**
```json
{
  "symbol": "VNM",
  "count": 245,
  "indicators": [
    {
      "time": "2026-04-16",
      "sma_20": 72.1,
      "sma_50": 71.5,
      "sma_200": 70.2,
      "ema_12": 72.3,
      "ema_26": 71.8,
      "rsi_14": 55.2,
      "macd": 0.45,
      "macd_signal": 0.32,
      "macd_histogram": 0.13,
      "bb_upper": 74.5,
      "bb_middle": 72.1,
      "bb_lower": 69.7
    }
  ]
}
```

---

## Analysis

### `GET /api/analysis/{symbol}/technical`

Chỉ báo kỹ thuật mới nhất cho 1 mã.

**Response:**
```json
{
  "symbol": "VNM",
  "date": "2026-04-16",
  "sma_20": 72.1,
  "sma_50": 71.5,
  "sma_200": 70.2,
  "ema_12": 72.3,
  "ema_26": 71.8,
  "rsi_14": 55.2,
  "macd": 0.45,
  "macd_signal": 0.32,
  "macd_histogram": 0.13,
  "bb_upper": 74.5,
  "bb_middle": 72.1,
  "bb_lower": 69.7,
  "stoch_k": 65.3,
  "stoch_d": 62.1,
  "adx": 28.4,
  "obv": 15200000,
  "avg_volume_20": 1500000,
  "relative_volume": 0.83,
  "volume_trend": "declining"
}
```

### `GET /api/analysis/{symbol}/fundamental`

Chỉ số tài chính mới nhất.

**Response:**
```json
{
  "symbol": "VNM",
  "year": 2026,
  "period": "Q1",
  "pe_ratio": 18.5,
  "pb_ratio": 4.2,
  "eps": 3920,
  "roe": 0.23,
  "roa": 0.15,
  "de_ratio": 0.35,
  "revenue_qoq": 0.08,
  "revenue_yoy": 0.12,
  "profit_qoq": 0.05,
  "profit_yoy": 0.10,
  "market_cap": 185000000000,
  "current_price": 72800
}
```

### `GET /api/analysis/{symbol}/trend`

Xu hướng giá và mức hỗ trợ/kháng cự.

**Response:**
```json
{
  "symbol": "VNM",
  "date": "2026-04-16",
  "trend_direction": "uptrend",
  "trend_strength": "moderate",
  "pivot_point": 72.8,
  "support_1": 71.2,
  "support_2": 69.8,
  "resistance_1": 74.0,
  "resistance_2": 75.5,
  "nearest_support": 71.2,
  "nearest_resistance": 74.0
}
```

### `POST /api/analysis/run`

Trigger phân tích toàn bộ ~400 mã HOSE. Đây là tác vụ dài — có thể mất vài phút.

### `GET /api/industry/groups`

Danh sách nhóm ngành Việt Nam.

**Response:**
```json
[
  {
    "group_code": "BANK",
    "group_name_vi": "Ngân hàng",
    "group_name_en": "Banking"
  }
]
```

### `GET /api/industry/{group_code}/averages`

Chỉ số trung bình ngành.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `group_code` | path | — | Mã ngành (VD: `BANK`) |
| `year` | query | latest | Năm (nếu không chỉ định, lấy mới nhất) |
| `period` | query | latest | Kỳ (Q1, Q2, Q3, Q4) |

**Response:**
```json
{
  "group_code": "BANK",
  "year": 2026,
  "period": "Q1",
  "avg_pe": 12.5,
  "avg_pb": 1.8,
  "avg_roe": 0.18,
  "avg_roa": 0.02,
  "avg_de": 8.5,
  "avg_revenue_growth_yoy": 0.15,
  "avg_profit_growth_yoy": 0.12,
  "stock_count": 27
}
```

---

## Scoring & Rankings

### `GET /api/scores/top`

Top mã cổ phiếu theo điểm tổng hợp.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `limit` | query | 20 | Số mã trả về (1-100) |

**Response:**
```json
{
  "stocks": [
    {
      "rank": 1,
      "symbol": "FPT",
      "total_score": 85.2,
      "grade": "A",
      "technical_score": 78.0,
      "fundamental_score": 90.5,
      "sentiment_score": 82.0,
      "macro_score": 75.0
    }
  ],
  "count": 20
}
```

> Nếu chưa chấm điểm, trả về `{"stocks": [], "count": 0, "message": "No scores computed yet. Run POST /api/scores/run first."}`.

**Grade scale:**
| Điểm | Grade |
|------|-------|
| 90-100 | A+ |
| 80-89 | A |
| 70-79 | B+ |
| 60-69 | B |
| 50-59 | C |
| 0-49 | D |

### `GET /api/scores/{symbol}`

Điểm tổng hợp cho 1 mã.

**Response:**
```json
{
  "symbol": "FPT",
  "date": "2026-04-16",
  "total_score": 85.2,
  "grade": "A",
  "rank": 1,
  "technical_score": 78.0,
  "fundamental_score": 90.5,
  "sentiment_score": 82.0,
  "macro_score": 75.0,
  "dimensions_used": 4,
  "weights": {"technical": 0.3, "fundamental": 0.3, "sentiment": 0.2, "macro": 0.2}
}
```

### `POST /api/scores/run`

Trigger chấm điểm toàn bộ mã HOSE.

> ⚠️ Có lock — trả về `409 Conflict` nếu đang chạy.

---

## News & Sentiment

### `GET /api/news`

Tin tức tài chính gần đây.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `days` | query | 7 | Số ngày nhìn lại (1-30) |
| `limit` | query | 50 | Số bài trả về (1-200) |

**Response:**
```json
{
  "articles": [
    {
      "id": 1,
      "title": "FPT công bố kết quả kinh doanh Q1/2026",
      "url": "https://cafef.vn/...",
      "source": "cafef",
      "published_at": "2026-04-16T10:00:00+07:00",
      "summary": "FPT ghi nhận doanh thu tăng 20%..."
    }
  ],
  "count": 50
}
```

### `GET /api/news/{symbol}/sentiment`

Điểm sentiment cho 1 mã, bao gồm điểm tổng hợp và chi tiết từng bài viết.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `days` | query | 7 | Số ngày nhìn lại (1-30) |

**Response:**
```json
{
  "symbol": "FPT",
  "aggregate_score": 0.720,
  "article_count": 8,
  "scores": [
    {
      "article_id": 1,
      "sentiment": "positive",
      "score": 0.85,
      "reason": "Doanh thu tăng mạnh, lợi nhuận vượt kỳ vọng",
      "model_used": "qwen2.5:7b",
      "computed_at": "2026-04-16T16:00:00+07:00"
    }
  ]
}
```

### `POST /api/news/crawl`

Trigger crawl tin tức từ RSS feeds.

> ⚠️ Có lock — trả về `409 Conflict` nếu đang crawl.

### `POST /api/sentiment/run`

Trigger phân tích sentiment bằng LLM (Ollama). Yêu cầu Ollama đang chạy.

> ⚠️ Có lock — trả về `409 Conflict` nếu đang phân tích.

---

## Macroeconomic Data

### `GET /api/macro/latest`

Dữ liệu vĩ mô mới nhất.

**Response:**
```json
{
  "indicators": [
    {
      "indicator_type": "interest_rate",
      "value": 4.5,
      "period": "2026-Q1",
      "source": "SBV",
      "trend": "stable",
      "recorded_at": "2026-04-01"
    },
    {
      "indicator_type": "exchange_rate_usd_vnd",
      "value": 25420,
      "period": "2026-04",
      "source": "VCB",
      "trend": "rising",
      "recorded_at": "2026-04-16"
    }
  ],
  "count": 4
}
```

### `POST /api/macro`

Nhập dữ liệu vĩ mô thủ công.

**Body:**
```json
{
  "indicator_type": "interest_rate",
  "value": 4.5,
  "period": "2026-Q1",
  "source": "SBV"
}
```

| Field | Type | Required | Mô tả |
|-------|------|----------|-------|
| `indicator_type` | string | ✅ | Một trong: `interest_rate`, `exchange_rate_usd_vnd`, `cpi`, `gdp` |
| `value` | float | ✅ | Giá trị số |
| `period` | string | ✅ | Kỳ, VD: `2026-Q1`, `2026-04` (4-20 ký tự) |
| `source` | string | — | Nguồn dữ liệu (default: `manual`, max 50 ký tự) |

**Response:**
```json
{
  "status": "ok",
  "indicator": {
    "indicator_type": "interest_rate",
    "value": 4.5,
    "period": "2026-Q1",
    "source": "SBV",
    "trend": "stable",
    "recorded_at": "2026-04-16"
  }
}
```

### `POST /api/macro/fetch-exchange-rate`

Tự động lấy tỷ giá USD/VND (sell rate) từ Vietcombank XML endpoint.

**Response:**
```json
{
  "status": "ok",
  "rate": {
    "indicator_type": "exchange_rate_usd_vnd",
    "value": 25420,
    "source": "VCB",
    "trend": "rising",
    "recorded_at": "2026-04-16"
  }
}
```

---

## Reports

### `GET /api/reports/top`

Báo cáo AI mới nhất.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `limit` | query | 20 | Số báo cáo (1-100) |

**Response:**
```json
{
  "reports": [
    {
      "symbol": "FPT",
      "summary": "FPT đang trong xu hướng tăng mạnh...",
      "technical_analysis": "RSI = 62, MACD cắt lên signal...",
      "fundamental_analysis": "P/E = 18.5 thấp hơn TB ngành...",
      "sentiment_analysis": "5/8 bài viết tích cực...",
      "macro_impact": "Lãi suất ổn định hỗ trợ ngành CNTT...",
      "recommendation": "Mua",
      "confidence": "Cao",
      "long_term_suggestion": "Tích lũy dài hạn...",
      "swing_trade_suggestion": "⚠️ T+3: Xu hướng tăng dự kiến duy trì 5 phiên...",
      "generated_at": "2026-04-16T16:30:00+07:00"
    }
  ],
  "count": 20
}
```

> Nếu chưa có báo cáo, trả về `{"reports": [], "count": 0, "message": "No reports available. Run POST /api/reports/run first."}`.

### `GET /api/reports/{symbol}`

Báo cáo mới nhất cho 1 mã (bao gồm `content_json` và metadata đầy đủ).

### `POST /api/reports/run`

Trigger tạo báo cáo AI cho top mã.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `top_n` | query | 20 | Số mã tạo báo cáo (1-50) |

> ⚠️ Có lock — trả về `409 Conflict` nếu đang tạo báo cáo.

---

## Automation & Pipeline

### `POST /api/automation/run`

Trigger **full pipeline** on-demand:

```
Crawl prices → Crawl news → Technical analysis → Fundamental analysis
→ Sentiment analysis → Scoring → Report generation → Telegram notification
```

> ⚠️ Pipeline có lock — chỉ 1 pipeline chạy cùng lúc. Nếu đang chạy, trả về `409 Conflict`.

### `POST /api/automation/run/{symbol}`

Phân tích 1 mã cụ thể (không chạy full pipeline). Symbol phải viết hoa, regex: `^[A-Z0-9]+$`.

> ⚠️ Có lock — trả về `409 Conflict` nếu pipeline đang chạy.

### `GET /api/automation/status`

Trạng thái scheduler và pipeline.

**Response:**
```json
{
  "scheduler_running": true,
  "pipeline_locked": false,
  "scheduled_jobs": [
    {
      "id": "daily_pipeline",
      "name": "Daily Pipeline",
      "next_run": "2026-04-17T15:45:00+07:00"
    }
  ]
}
```

---

## Dashboard

### `GET /api/sectors/latest`

Sector snapshots mới nhất — điểm trung bình ngành sắp xếp theo `avg_score` giảm dần.

**Response:**
```json
{
  "date": "2026-04-16",
  "count": 15,
  "sectors": [
    {
      "group_code": "BANK",
      "group_name_vi": "Ngân hàng",
      "avg_score": 68.5,
      "stock_count": 27,
      "avg_score_change": 2.3
    }
  ]
}
```

---

## Admin (v1.2)

Quản lý watchlist, trigger pipeline theo mã cụ thể, và theo dõi job status.

Admin endpoints sử dụng **DB-queue pattern**: API tạo job record (status=`pending`) và trả về ngay. Background worker (APScheduler) sẽ pick up job và thực thi.

### Stock Watchlist

#### `GET /api/admin/stocks`

Danh sách tất cả mã cổ phiếu đang theo dõi (`is_tracked=True`).

**Response:**
```json
{
  "stocks": [
    {
      "symbol": "VNM",
      "name": "Vinamilk",
      "exchange": "HOSE",
      "industry": "Thực phẩm & Đồ uống",
      "is_tracked": true
    }
  ],
  "count": 50
}
```

#### `POST /api/admin/stocks`

Thêm 1 mã vào watchlist. Nếu mã đã tồn tại trong DB, set `is_tracked=True`. Nếu chưa, tạo record mới.

**Body:**
```json
{
  "symbol": "VNM"
}
```

| Field | Type | Required | Mô tả |
|-------|------|----------|-------|
| `symbol` | string | ✅ | Mã cổ phiếu, 1-10 ký tự, regex: `^[A-Z0-9]+$` |

**Response:**
```json
{
  "symbol": "VNM",
  "name": "Vinamilk",
  "is_tracked": true,
  "message": "Stock VNM added to watchlist"
}
```

#### `DELETE /api/admin/stocks/{symbol}`

Xóa mã khỏi watchlist (set `is_tracked=False`, không xóa data).

| Parameter | Type | Mô tả |
|-----------|------|-------|
| `symbol` | path | Mã cổ phiếu, 1-10 ký tự, regex: `^[A-Z0-9]+$` |

**Response:**
```json
{
  "symbol": "VNM",
  "is_tracked": false,
  "message": "Stock VNM removed from watchlist"
}
```

> Trả về `404` nếu mã không tồn tại trong DB.

### Pipeline Triggers

Tất cả trigger endpoints nhận `SymbolsRequest` body và trả về `TriggerResponse` với `job_id` để polling.

**Body chung:**
```json
{
  "symbols": ["VNM", "FPT", "HPG"]
}
```

| Field | Type | Required | Mô tả |
|-------|------|----------|-------|
| `symbols` | list[str] | ✅ | Danh sách mã cổ phiếu (ít nhất 1 mã) |

**Response chung (TriggerResponse):**
```json
{
  "job_id": 42,
  "status": "pending",
  "job_type": "crawl",
  "symbols": ["VNM", "FPT", "HPG"]
}
```

#### `POST /api/admin/crawl`

Queue crawl job — lấy dữ liệu giá cho các mã chỉ định.

#### `POST /api/admin/analyze`

Queue analysis job — chạy phân tích kỹ thuật + cơ bản cho các mã chỉ định.

#### `POST /api/admin/score`

Queue scoring job — chấm điểm tổng hợp cho các mã chỉ định.

#### `POST /api/admin/report`

Queue report job — tạo báo cáo AI cho các mã chỉ định.

#### `POST /api/admin/pipeline`

Queue full pipeline (crawl → analyze → score) cho các mã chỉ định.

### Job Monitoring

#### `GET /api/admin/jobs`

Danh sách jobs gần đây.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `limit` | query | 50 | Số jobs trả về |

**Response:**
```json
{
  "jobs": [
    {
      "id": 42,
      "job_type": "crawl",
      "status": "completed",
      "params": {"symbols": ["VNM", "FPT"]},
      "created_at": "2026-04-16T15:00:00+07:00",
      "started_at": "2026-04-16T15:00:05+07:00",
      "completed_at": "2026-04-16T15:02:30+07:00"
    }
  ],
  "count": 10
}
```

#### `GET /api/admin/jobs/{job_id}`

Chi tiết 1 job bao gồm kết quả và lỗi (nếu có).

| Parameter | Type | Mô tả |
|-----------|------|-------|
| `job_id` | path | ID job (số nguyên > 0) |

**Response:**
```json
{
  "id": 42,
  "job_type": "crawl",
  "status": "completed",
  "params": {"symbols": ["VNM", "FPT"]},
  "result": {"stocks_crawled": 2, "duration_seconds": 145},
  "error": null,
  "created_at": "2026-04-16T15:00:00+07:00",
  "started_at": "2026-04-16T15:00:05+07:00",
  "completed_at": "2026-04-16T15:02:30+07:00"
}
```

> Trả về `404` nếu job không tồn tại.

**Job Status Values:**

| Status | Mô tả |
|--------|-------|
| `pending` | Job đã tạo, đang chờ worker pick up |
| `running` | Worker đang thực thi job |
| `completed` | Job hoàn thành thành công |
| `failed` | Job thất bại — xem field `error` để biết chi tiết |

---

## Error Responses

Tất cả endpoint trả về format lỗi chuẩn (FastAPI default):

```json
{
  "detail": "Stock VNM not found"
}
```

| Status Code | Mô tả |
|-------------|-------|
| 200 | Thành công |
| 404 | Không tìm thấy (symbol, report, job, etc.) |
| 409 | Conflict (pipeline/scoring/crawl đang chạy) |
| 422 | Validation error (parameter sai format hoặc giá trị) |
| 500 | Server error |
