# LocalStock API Reference

**Base URL:** `http://localhost:8000`

**Swagger UI:** `http://localhost:8000/docs`

## Health & Status

### `GET /health`

Kiểm tra trạng thái hệ thống và pipeline gần nhất.

**Response:**
```json
{
  "status": "healthy",
  "latest_pipeline_run": {
    "id": 1,
    "status": "completed",
    "started_at": "2026-04-16T15:45:00+07:00",
    "completed_at": "2026-04-16T16:10:00+07:00"
  }
}
```

---

## Prices & Indicators

### `GET /api/prices/{symbol}`

Lịch sử giá OHLCV cho 1 mã cổ phiếu.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `symbol` | path | — | Mã cổ phiếu (VD: `VNM`) |
| `days` | query | 90 | Số ngày lịch sử (30-730) |

**Response:**
```json
[
  {
    "date": "2026-04-16",
    "open": 72.5,
    "high": 73.2,
    "low": 72.0,
    "close": 72.8,
    "volume": 1250000
  }
]
```

### `GET /api/prices/{symbol}/indicators`

Time-series chỉ báo kỹ thuật.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `symbol` | path | — | Mã cổ phiếu |
| `days` | query | 90 | Số ngày lịch sử |

**Response:**
```json
[
  {
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
    "bb_lower": 69.7
  }
]
```

---

## Analysis

### `GET /api/analysis/{symbol}/technical`

Chỉ báo kỹ thuật mới nhất.

**Response:**
```json
{
  "symbol": "VNM",
  "computed_at": "2026-04-16T16:00:00+07:00",
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
  "avg_volume_20": 1500000,
  "relative_volume": 0.83,
  "volume_trend": "declining"
}
```

### `GET /api/analysis/{symbol}/fundamental`

Chỉ số tài chính.

**Response:**
```json
{
  "symbol": "VNM",
  "pe_ratio": 18.5,
  "pb_ratio": 4.2,
  "eps": 3920,
  "roe": 0.23,
  "roa": 0.15,
  "de_ratio": 0.35,
  "revenue_growth_qoq": 0.08,
  "revenue_growth_yoy": 0.12,
  "profit_growth_qoq": 0.05,
  "profit_growth_yoy": 0.10
}
```

### `GET /api/analysis/{symbol}/trend`

Xu hướng giá và hỗ trợ/kháng cự.

**Response:**
```json
{
  "symbol": "VNM",
  "trend_direction": "uptrend",
  "trend_strength": "moderate",
  "support_level": 70.5,
  "resistance_level": 75.0,
  "pivot_point": 72.8
}
```

### `POST /api/analysis/run`

Trigger phân tích toàn bộ ~400 mã HOSE.

**Response:**
```json
{
  "status": "completed",
  "stocks_analyzed": 400,
  "duration_seconds": 45
}
```

### `GET /api/industry/groups`

Danh sách nhóm ngành Việt Nam.

**Response:**
```json
[
  {"group_code": "BANK", "group_name": "Ngân hàng", "stock_count": 27},
  {"group_code": "REAL", "group_name": "Bất động sản", "stock_count": 45}
]
```

### `GET /api/industry/{group_code}/averages`

Chỉ số trung bình ngành.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `group_code` | path | — | Mã ngành (VD: `BANK`) |
| `year` | query | current | Năm |
| `period` | query | latest | Kỳ (Q1, Q2, Q3, Q4) |

---

## Scoring & Rankings

### `GET /api/scores/top`

Top mã cổ phiếu theo điểm tổng hợp.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `limit` | query | 20 | Số mã trả về (1-100) |

**Response:**
```json
[
  {
    "rank": 1,
    "symbol": "FPT",
    "total_score": 85.2,
    "grade": "A",
    "technical_score": 78.0,
    "fundamental_score": 90.5,
    "sentiment_score": 82.0,
    "macro_score": 75.0,
    "score_change": 5.2,
    "computed_at": "2026-04-16T16:00:00+07:00"
  }
]
```

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

### `POST /api/scores/run`

Trigger chấm điểm toàn bộ.

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
[
  {
    "id": 1,
    "title": "FPT công bố kết quả kinh doanh Q1/2026",
    "source": "cafef",
    "url": "https://cafef.vn/...",
    "published_at": "2026-04-16T10:00:00+07:00",
    "symbols": ["FPT"]
  }
]
```

### `GET /api/news/{symbol}/sentiment`

Điểm sentiment cho 1 mã.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `days` | query | 7 | Số ngày nhìn lại (1-30) |

**Response:**
```json
{
  "symbol": "FPT",
  "sentiment_score": 0.72,
  "sentiment_label": "positive",
  "article_count": 8,
  "positive": 5,
  "negative": 1,
  "neutral": 2
}
```

### `POST /api/news/crawl`

Trigger crawl tin tức từ RSS feeds.

### `POST /api/sentiment/run`

Trigger phân tích sentiment bằng LLM.

---

## Macroeconomic Data

### `GET /api/macro/latest`

Dữ liệu vĩ mô mới nhất.

**Response:**
```json
{
  "interest_rate": {
    "value": 4.5,
    "unit": "%",
    "source": "SBV",
    "date": "2026-04-01"
  },
  "exchange_rate_usd_vnd": {
    "value": 25420,
    "unit": "VND/USD",
    "source": "VCB",
    "date": "2026-04-16"
  },
  "cpi": {
    "value": 3.2,
    "unit": "%",
    "source": "GSO",
    "date": "2026-03-01"
  }
}
```

### `POST /api/macro`

Nhập dữ liệu vĩ mô thủ công.

**Body:**
```json
{
  "indicator_type": "interest_rate",
  "value": 4.5,
  "source": "SBV",
  "date": "2026-04-01"
}
```

### `POST /api/macro/fetch-exchange-rate`

Tự động lấy tỷ giá USD/VND từ Vietcombank.

---

## Reports

### `GET /api/reports/top`

Báo cáo AI mới nhất.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `limit` | query | 20 | Số báo cáo (1-100) |

**Response:**
```json
[
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
]
```

### `GET /api/reports/{symbol}`

Báo cáo mới nhất cho 1 mã.

### `POST /api/reports/run`

Trigger tạo báo cáo AI.

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `top_n` | query | 20 | Số mã tạo báo cáo (1-50) |

---

## Automation & Pipeline

### `POST /api/automation/run`

Trigger **full pipeline** on-demand:

```
Crawl prices → Crawl news → Technical analysis → Fundamental analysis
→ Sentiment analysis → Scoring → Report generation → Telegram notification
```

**Response:**
```json
{
  "status": "completed",
  "pipeline_run_id": 42,
  "steps_completed": 8,
  "duration_seconds": 300
}
```

> ⚠️ Pipeline có lock — chỉ 1 pipeline chạy cùng lúc. Nếu đang chạy, trả về `409 Conflict`.

### `POST /api/automation/run/{symbol}`

Phân tích 1 mã cụ thể (không chạy full pipeline).

### `GET /api/automation/status`

Trạng thái scheduler và pipeline.

**Response:**
```json
{
  "scheduler_running": true,
  "next_run": "2026-04-17T15:45:00+07:00",
  "pipeline_locked": false,
  "latest_run": {
    "status": "completed",
    "started_at": "2026-04-16T15:45:00+07:00",
    "completed_at": "2026-04-16T16:10:00+07:00"
  }
}
```

---

## Dashboard

### `GET /api/sectors/latest`

Sector snapshots mới nhất.

**Response:**
```json
[
  {
    "group_code": "BANK",
    "group_name": "Ngân hàng",
    "stock_count": 27,
    "avg_score": 68.5,
    "avg_score_change": 2.3,
    "top_stock": "VCB",
    "top_score": 82.0
  }
]
```

---

## Error Responses

Tất cả endpoint trả về format lỗi chuẩn:

```json
{
  "detail": "Stock VNM not found"
}
```

| Status Code | Mô tả |
|-------------|-------|
| 200 | Thành công |
| 404 | Không tìm thấy (symbol, report, etc.) |
| 409 | Conflict (pipeline đang chạy) |
| 422 | Validation error (parameter sai) |
| 500 | Server error |
