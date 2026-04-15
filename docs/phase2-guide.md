# Phase 2 — Technical & Fundamental Analysis

## Tổng quan

Phase 2 xây dựng engine phân tích kỹ thuật và cơ bản cho ~400 cổ phiếu HOSE:

- **Technical Analysis**: SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic, ADX, OBV, volume analysis, trend detection, support/resistance
- **Fundamental Analysis**: P/E, P/B, EPS, ROE, ROA, D/E, growth rates (QoQ, YoY), TTM
- **Industry Analysis**: 20 nhóm ngành VN, mapping ICB Level 3, industry averages

---

## Cách chạy

### 1. Khởi động server

```bash
# Đảm bảo có file .env với DATABASE_URL (Supabase PostgreSQL)
uv run uvicorn localstock.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
```

### 2. Chạy phân tích toàn bộ (~400 cổ phiếu)

```bash
# POST request — chạy full pipeline (mất ~3-4 phút)
curl -X POST http://localhost:8000/api/analysis/run
```

**Response mẫu:**
```json
{
  "technical_success": 398,
  "technical_errors": 2,
  "fundamental_success": 395,
  "fundamental_errors": 5,
  "industry_groups_seeded": 20,
  "stocks_mapped": 398
}
```

### 3. Xem kết quả phân tích

```bash
# Technical indicators cho 1 mã
curl http://localhost:8000/api/analysis/VNM/technical

# Financial ratios cho 1 mã
curl http://localhost:8000/api/analysis/VNM/fundamental

# Trend + Support/Resistance
curl http://localhost:8000/api/analysis/VNM/trend

# Danh sách 20 nhóm ngành VN
curl http://localhost:8000/api/industry/groups

# Industry averages (VD: ngành ngân hàng)
curl http://localhost:8000/api/industry/BANKING/averages
```

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/analysis/{symbol}/technical` | Chỉ số kỹ thuật mới nhất |
| `GET` | `/api/analysis/{symbol}/fundamental` | Tỷ số tài chính mới nhất |
| `GET` | `/api/analysis/{symbol}/trend` | Xu hướng + hỗ trợ/kháng cự |
| `POST` | `/api/analysis/run` | Chạy phân tích toàn bộ HOSE |
| `GET` | `/api/industry/groups` | Danh sách 20 nhóm ngành VN |
| `GET` | `/api/industry/{group_code}/averages` | Trung bình ngành (P/E, ROE, ...) |

### Response chi tiết

**GET /api/analysis/{symbol}/technical:**
```json
{
  "symbol": "VNM",
  "date": "2025-01-15",
  "sma_20": 72.5,
  "sma_50": 71.2,
  "sma_200": 68.9,
  "ema_12": 73.1,
  "ema_26": 72.0,
  "rsi_14": 55.3,
  "macd": 1.1,
  "macd_signal": 0.8,
  "macd_histogram": 0.3,
  "bb_upper": 76.2,
  "bb_middle": 72.5,
  "bb_lower": 68.8,
  "stoch_k": 62.1,
  "stoch_d": 58.7,
  "adx": 25.4,
  "obv": 15234567,
  "avg_volume_20": 1250000,
  "relative_volume": 1.12,
  "volume_trend": "increasing"
}
```

**GET /api/analysis/{symbol}/trend:**
```json
{
  "symbol": "VNM",
  "date": "2025-01-15",
  "trend_direction": "bullish",
  "trend_strength": 25.4,
  "pivot_point": 72.0,
  "support_1": 70.5,
  "support_2": 69.0,
  "resistance_1": 73.5,
  "resistance_2": 75.0,
  "nearest_support": 70.5,
  "nearest_resistance": 73.5
}
```

---

## Chạy Tests

```bash
# Chạy tất cả tests (98 tests — Phase 1 + Phase 2)
uv run pytest tests/ -v

# Chỉ chạy tests Phase 2
uv run pytest tests/test_analysis/ tests/test_services/test_analysis_service.py -v

# Chạy từng module riêng
uv run pytest tests/test_analysis/test_technical.py -v      # 8 tests — TechnicalAnalyzer
uv run pytest tests/test_analysis/test_trend.py -v           # 9 tests — Trend detection + S/R
uv run pytest tests/test_analysis/test_fundamental.py -v     # 13 tests — FundamentalAnalyzer
uv run pytest tests/test_analysis/test_industry.py -v        # 12 tests — IndustryAnalyzer
uv run pytest tests/test_services/test_analysis_service.py -v # 3 tests — AnalysisService
```

### Danh sách test Phase 2 (45 tests)

#### Technical Analysis (8 tests)
| Test | Kiểm tra |
|------|----------|
| `test_returns_dataframe_with_indicator_columns` | pandas-ta trả đúng columns |
| `test_sma_20_warmup_period` | SMA(20) cần ≥20 rows |
| `test_rsi_values_bounded` | RSI nằm trong 0-100 |
| `test_empty_dataframe` | Xử lý data rỗng |
| `test_returns_volume_metrics` | avg_volume_20, relative_volume, volume_trend |
| `test_volume_trend_valid_values` | volume_trend ∈ {increasing, decreasing, stable} |
| `test_relative_volume_calculation` | relative_volume = latest_vol / avg_vol |
| `test_maps_columns_to_model_keys` | Mapping pandas-ta columns → DB model |

#### Trend Detection & S/R (9 tests)
| Test | Kiểm tra |
|------|----------|
| `test_uptrend_detection` | Close > SMA, MACD > 0 → bullish |
| `test_downtrend_detection` | Close < SMA, MACD < 0 → bearish |
| `test_sideways_low_adx` | ADX < 20 → sideways |
| `test_trend_strength_from_adx` | ADX value = trend_strength |
| `test_standard_pivot_calculation` | Pivot = (H+L+C)/3, S1/R1 formulas |
| `test_finds_peaks_in_simple_data` | Peak detection algorithm |
| `test_no_peaks_in_flat_data` | Flat data → no peaks |
| `test_finds_nearest_levels` | Nearest S/R relative to price |
| `test_no_support_when_at_all_time_low` | Edge case: giá thấp nhất |

#### Fundamental Analysis (13 tests)
| Test | Kiểm tra |
|------|----------|
| `test_returns_all_ratio_keys` | Output có đủ keys |
| `test_pe_ratio` | P/E = price × shares / earnings |
| `test_pb_ratio` | P/B = price × shares / equity |
| `test_eps` | EPS = earnings / shares |
| `test_roe` | ROE = earnings / equity |
| `test_roa` | ROA = earnings / total_assets |
| `test_de_ratio` | D/E = liabilities / equity |
| `test_negative_equity_de_none` | Equity < 0 → D/E = None |
| `test_zero_earnings_pe_none` | Earnings = 0 → P/E = None |
| `test_qoq_growth` | Growth QoQ tính đúng |
| `test_growth_previous_zero_returns_none` | Mẫu số = 0 → None |
| `test_sums_four_quarters` | TTM = tổng 4 quý |
| `test_ttm_with_missing_quarter_returns_none` | Thiếu quý → None |

#### Industry Analysis (12 tests)
| Test | Kiểm tra |
|------|----------|
| `test_has_20_groups` | Đúng 20 nhóm ngành VN |
| `test_each_group_has_required_fields` | Mỗi group có code, name_vi, name_en |
| `test_banking_group_exists` | Nhóm BANKING tồn tại |
| `test_other_group_exists` | Nhóm OTHER (fallback) tồn tại |
| `test_ngan_hang_to_banking` | ICB "Ngân hàng" → BANKING |
| `test_bat_dong_san_to_real_estate` | ICB "Bất động sản" → REAL_ESTATE |
| `test_map_icb_to_group_known` | Mapping ICB3 → group code |
| `test_map_icb_to_group_none` | ICB None → OTHER |
| `test_map_icb_to_group_unknown` | ICB lạ → OTHER |
| `test_averages_ratios` | Tính trung bình đúng |
| `test_excludes_none_from_average` | Bỏ qua None khi tính avg |
| `test_empty_ratios` | Ratios rỗng → all None |

#### AnalysisService (3 tests)
| Test | Kiểm tra |
|------|----------|
| `test_produces_indicator_row` | Pipeline technical → indicator dict |
| `test_handles_short_data` | Data < 200 rows vẫn chạy |
| `test_produces_ratio_row` | Pipeline fundamental → ratio dict |

---

## Kiến trúc Module

```
src/localstock/
├── analysis/                        # NEW — Phase 2
│   ├── __init__.py
│   ├── technical.py                 # TechnicalAnalyzer (pandas-ta)
│   ├── trend.py                     # detect_trend(), pivot_points(), S/R
│   ├── fundamental.py               # FundamentalAnalyzer (ratios, growth, TTM)
│   └── industry.py                  # IndustryAnalyzer (20 VN groups, ICB mapping)
├── services/
│   ├── analysis_service.py          # NEW — AnalysisService orchestrator
│   └── pipeline_service.py          # Phase 1
├── api/routes/
│   ├── analysis.py                  # NEW — 6 API endpoints
│   └── health.py                    # Phase 1
├── db/
│   ├── models.py                    # 5 new models (10 total)
│   └── repositories/
│       ├── indicator_repo.py        # NEW — bulk upsert indicators
│       ├── ratio_repo.py            # NEW — bulk upsert ratios
│       └── industry_repo.py         # NEW — groups, mappings, averages
```

## Database Tables (Phase 2)

| Table | Mục đích |
|-------|----------|
| `technical_indicators` | SMA, EMA, RSI, MACD, BB, volume metrics, trend, S/R |
| `financial_ratios` | P/E, P/B, EPS, ROE, ROA, D/E, growth rates |
| `industry_groups` | 20 nhóm ngành VN (code, name_vi, name_en) |
| `stock_industry_mapping` | Mapping mã CK → nhóm ngành (từ ICB Level 3) |
| `industry_averages` | Trung bình ngành theo kỳ (avg_pe, avg_roe, ...) |

## 20 Nhóm ngành Việt Nam

| Code | Tên Việt | Tên Anh |
|------|----------|---------|
| BANKING | Ngân hàng | Banking |
| REAL_ESTATE | Bất động sản | Real Estate |
| SECURITIES | Chứng khoán | Securities |
| INSURANCE | Bảo hiểm | Insurance |
| STEEL | Thép | Steel |
| CONSTRUCTION | Xây dựng | Construction |
| RETAIL | Bán lẻ | Retail |
| FOOD_BEVERAGE | Thực phẩm & Đồ uống | Food & Beverage |
| SEAFOOD | Thủy sản | Seafood |
| TEXTILE | Dệt may | Textile & Garment |
| TECHNOLOGY | Công nghệ | Technology |
| POWER | Điện | Power & Utilities |
| OIL_GAS | Dầu khí | Oil & Gas |
| CHEMICALS | Hóa chất | Chemicals |
| LOGISTICS | Vận tải & Logistics | Logistics |
| AVIATION | Hàng không | Aviation |
| PHARMA | Dược phẩm | Pharmaceuticals |
| RUBBER | Cao su | Rubber |
| PLASTICS | Nhựa & Bao bì | Plastics & Packaging |
| OTHER | Khác | Other |
