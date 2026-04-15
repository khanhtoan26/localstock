# Phase 2: Technical & Fundamental Analysis — Research

**Researched:** 2025-07-17
**Status:** Complete

## 1. pandas-ta Library Usage

### Installation
Already in `pyproject.toml` dev dependency group: `pandas-ta>=0.4.71b0`. Move to main dependencies since it's needed at runtime.

```bash
uv add pandas-ta
```

### API Patterns

**Individual indicator calls:**
```python
import pandas_ta as ta

# df must have OHLCV columns: open, high, low, close, volume
df.ta.sma(length=20, append=True)   # adds SMA_20 column
df.ta.ema(length=12, append=True)   # adds EMA_12 column
df.ta.rsi(length=14, append=True)   # adds RSI_14 column
df.ta.macd(fast=12, slow=26, signal=9, append=True)  # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
df.ta.bbands(length=20, std=2, append=True)  # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
df.ta.stoch(append=True)            # STOCHk_14_3_3, STOCHd_14_3_3
df.ta.adx(append=True)              # ADX_14, DMP_14, DMN_14
df.ta.obv(append=True)              # OBV
df.ta.vwap(append=True)             # VWAP_D (requires high, low, close, volume)
```

**Strategy approach (batch all at once):**
```python
# Custom strategy — compute all indicators in one call
custom = ta.Strategy(
    name="localstock",
    ta=[
        {"kind": "sma", "length": 20},
        {"kind": "sma", "length": 50},
        {"kind": "sma", "length": 200},
        {"kind": "ema", "length": 12},
        {"kind": "ema", "length": 26},
        {"kind": "rsi", "length": 14},
        {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
        {"kind": "bbands", "length": 20, "std": 2},
        {"kind": "stoch"},
        {"kind": "adx"},
        {"kind": "obv"},
    ]
)
df.ta.strategy(custom)
```

### Known Pitfalls
- pandas-ta requires DataFrame index NOT be the date column — use `df.set_index('date')` or reset
- NaN values in early rows (warm-up period): SMA(200) needs 200 rows → first 199 rows are NaN
- Column naming convention: `{INDICATOR}_{params}` (e.g., `SMA_20`, `RSI_14`, `MACD_12_26_9`)
- `vwap` requires intraday-style data or at minimum OHLCV; for daily data VWAP is less meaningful
- Version 0.4.71b0 is a beta — stable enough for production use but pin the version

### Recommendation
Use **individual indicator calls** rather than Strategy for clarity and error handling per indicator. Wrap each in try/except so one failing indicator doesn't block the rest.

## 2. Database Schema Design

### New Tables

#### `technical_indicators`
Stores computed technical indicators per stock per date. One row per symbol per date.

```sql
CREATE TABLE technical_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    -- Moving Averages
    sma_20 FLOAT,
    sma_50 FLOAT,
    sma_200 FLOAT,
    ema_12 FLOAT,
    ema_26 FLOAT,
    -- Momentum
    rsi_14 FLOAT,
    macd FLOAT,           -- MACD line
    macd_signal FLOAT,    -- Signal line
    macd_histogram FLOAT, -- Histogram
    -- Bollinger Bands
    bb_upper FLOAT,
    bb_middle FLOAT,
    bb_lower FLOAT,
    -- Additional
    stoch_k FLOAT,
    stoch_d FLOAT,
    adx FLOAT,
    obv BIGINT,
    -- Volume Analysis (TECH-02)
    avg_volume_20 BIGINT,   -- 20-day average volume
    relative_volume FLOAT,  -- today_vol / avg_vol_20
    volume_sma_20 BIGINT,   -- redundant with avg_volume_20 but explicit
    -- Trend (TECH-03)
    trend_direction VARCHAR(20),  -- 'uptrend', 'downtrend', 'sideways'
    trend_strength FLOAT,         -- 0-100 based on ADX
    -- Support/Resistance (TECH-04)
    pivot_point FLOAT,
    support_1 FLOAT,
    support_2 FLOAT,
    resistance_1 FLOAT,
    resistance_2 FLOAT,
    nearest_support FLOAT,     -- from peak/trough detection
    nearest_resistance FLOAT,  -- from peak/trough detection
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, date)
);

CREATE INDEX ix_tech_indicators_symbol_date ON technical_indicators(symbol, date);
CREATE INDEX ix_tech_indicators_symbol ON technical_indicators(symbol);
```

#### `financial_ratios`
Stores computed financial ratios per stock per period.

```sql
CREATE TABLE financial_ratios (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    year INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL,  -- 'Q1'..'Q4', 'TTM'
    -- Core ratios (FUND-01)
    pe_ratio FLOAT,        -- Price / EPS
    pb_ratio FLOAT,        -- Price / Book Value per share
    eps FLOAT,             -- Earnings per Share (VND)
    roe FLOAT,             -- Return on Equity (%)
    roa FLOAT,             -- Return on Assets (%)
    de_ratio FLOAT,        -- Debt / Equity
    -- Growth metrics (FUND-02)
    revenue_qoq FLOAT,    -- Revenue growth QoQ (%)
    revenue_yoy FLOAT,    -- Revenue growth YoY (%)
    profit_qoq FLOAT,     -- Net profit growth QoQ (%)
    profit_yoy FLOAT,     -- Net profit growth YoY (%)
    -- Raw values for ratio computation
    revenue FLOAT,         -- in billion VND
    net_profit FLOAT,      -- in billion VND
    total_assets FLOAT,    -- in billion VND
    total_equity FLOAT,    -- in billion VND
    total_debt FLOAT,      -- in billion VND
    book_value_per_share FLOAT,
    market_cap FLOAT,      -- in billion VND
    shares_outstanding BIGINT,
    current_price FLOAT,   -- closing price used for P/E, P/B
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, year, period)
);

CREATE INDEX ix_fin_ratios_symbol ON financial_ratios(symbol);
```

#### `industry_groups`
Vietnamese-specific industry grouping for FUND-03 comparison.

```sql
CREATE TABLE industry_groups (
    id SERIAL PRIMARY KEY,
    group_code VARCHAR(20) NOT NULL UNIQUE,  -- e.g., 'BANKING', 'REAL_ESTATE'
    group_name_vi VARCHAR(200) NOT NULL,     -- e.g., 'Ngân hàng'
    group_name_en VARCHAR(200),              -- e.g., 'Banking'
    description TEXT
);

-- Mapping table: which stock belongs to which group
CREATE TABLE stock_industry_mapping (
    symbol VARCHAR(10) PRIMARY KEY,
    group_code VARCHAR(20) NOT NULL REFERENCES industry_groups(group_code),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `industry_averages`
Precomputed industry average ratios for FUND-03.

```sql
CREATE TABLE industry_averages (
    id SERIAL PRIMARY KEY,
    group_code VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    period VARCHAR(10) NOT NULL,
    -- Average ratios
    avg_pe FLOAT,
    avg_pb FLOAT,
    avg_roe FLOAT,
    avg_roa FLOAT,
    avg_de FLOAT,
    avg_revenue_growth_yoy FLOAT,
    avg_profit_growth_yoy FLOAT,
    -- Metadata
    stock_count INTEGER,  -- how many stocks in this average
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(group_code, year, period)
);
```

### Design Rationale
- **Flat columns over JSONB** for indicators: Supabase/PostgreSQL queries benefit from typed columns (WHERE rsi_14 > 70). JSONB would require `->>` extraction.
- **Separate tables** for technical vs fundamental: Different granularity (daily vs quarterly), different update frequencies.
- **Industry groups as separate table**: Allows manual curation of VN-specific groupings without schema changes.
- **TTM period**: Special period value for Trailing Twelve Months computation of annual ratios.

## 3. Financial Ratio Calculations

### Data Source: JSONB in `financial_statements`
The `data` column in `financial_statements` contains vnstock VCI output as a JSON dict. From UAT testing with VNM, the format is:

```python
# income_statement data keys (VCI source, no lang param):
# - 'revenue', 'year_revenue_growth', 'quarter_revenue_growth'
# - 'cost_of_good_sold', 'gross_profit'
# - 'operating_expense', 'operating_profit'
# - 'net_profit', 'share_holder_income'
# - 'invest_profit', 'service_profit', 'other_profit'
# - 'ebit', 'ebitda'

# balance_sheet data keys:
# - 'asset', 'short_asset', 'long_asset'
# - 'debt', 'short_debt', 'long_debt'
# - 'equity', 'charter_capital', 'un_distributed_income'
# - 'minor_share_holder_profit'

# cash_flow data keys:
# - 'invest_cost', 'from_invest', 'from_financial', 'from_sale'
# - 'free_cash_flow'
```

### Ratio Formulas

| Ratio | Formula | Data Source |
|-------|---------|-------------|
| **P/E** | current_price × shares_outstanding / TTM net_profit | stock_prices.close × stocks.issue_shares / income_statement.share_holder_income |
| **P/B** | market_cap / total_equity | (close × issue_shares) / balance_sheet.equity |
| **EPS** | TTM net_profit / shares_outstanding | income_statement.share_holder_income / stocks.issue_shares |
| **ROE** | TTM net_profit / avg_equity × 100 | income_statement.share_holder_income / balance_sheet.equity |
| **ROA** | TTM net_profit / avg_total_assets × 100 | income_statement.share_holder_income / balance_sheet.asset |
| **D/E** | total_debt / total_equity | balance_sheet.debt / balance_sheet.equity |

### TTM (Trailing Twelve Months) Calculation
For quarterly data, sum the last 4 quarters:
```python
def compute_ttm(symbol: str, current_year: int, current_quarter: int, metric: str) -> float:
    """Sum last 4 quarters of a metric for TTM computation."""
    quarters = []
    y, q = current_year, current_quarter
    for _ in range(4):
        quarters.append((y, f"Q{q}"))
        q -= 1
        if q == 0:
            q = 4
            y -= 1
    # Query financial_statements for these 4 periods
    # Sum the metric value across all 4
    return sum(values)
```

### Edge Cases
- **Negative equity**: D/E becomes meaningless → set to None or flag as "negative_equity"
- **Zero earnings**: P/E becomes infinite → cap at 999 or None
- **Missing quarters**: If < 4 quarters available, use annualized (quarterly × 4) with a flag
- **Different fiscal years**: Most VN companies use calendar year → safe assumption
- **Unit normalization**: All values already in billion_vnd from Phase 1 `FinanceCrawler.normalize_unit()`

## 4. Growth Rate Computation (FUND-02)

### QoQ Growth
```python
growth_qoq = (current_quarter_value - previous_quarter_value) / abs(previous_quarter_value) * 100
```

### YoY Growth
```python
growth_yoy = (current_quarter_value - same_quarter_last_year) / abs(same_quarter_last_year) * 100
```

### Edge Cases
- Previous period value = 0 → growth = None (undefined)
- Both values negative → growth calculation still valid but needs sign handling
- First available period → no growth available, set to None

## 5. Vietnamese Industry Grouping (FUND-03)

### Proposed VN-Specific Groups

| Code | Vietnamese | English | Example Tickers |
|------|-----------|---------|----------------|
| BANKING | Ngân hàng | Banking | VCB, BID, CTG, TCB, MBB, ACB, VPB, TPB, HDB |
| REAL_ESTATE | Bất động sản | Real Estate | VHM, VIC, NVL, KDH, DXG, PDR, NLG |
| SECURITIES | Chứng khoán | Securities/Brokerage | SSI, VCI, HCM, VND, SHS, MBS |
| INSURANCE | Bảo hiểm | Insurance | BVH, BMI, PVI |
| STEEL | Thép | Steel | HPG, HSG, NKG, TLH |
| SEAFOOD | Thủy sản | Seafood | VHC, IDI, ANV, ACL |
| RETAIL | Bán lẻ | Retail | MWG, FRT, PNJ, DGW |
| CONSTRUCTION | Xây dựng | Construction | CTD, HBC, ROS, FCN |
| ENERGY | Năng lượng | Energy/Power | GAS, POW, PPC, NT2, REE |
| OIL_GAS | Dầu khí | Oil & Gas | PLX, PVD, PVS, BSR |
| TECH | Công nghệ | Technology | FPT, CMG, ELC |
| FOOD_BEVERAGE | Thực phẩm & Đồ uống | Food & Beverage | VNM, MSN, SAB, QNS |
| TEXTILE | Dệt may | Textile/Garment | TCM, TNG, STK, GMC |
| PHARMA | Dược phẩm | Pharma/Healthcare | DHG, DMC, IMP, DVN |
| LOGISTICS | Vận tải & Logistics | Transport/Logistics | GMD, VSC, HAH, VTP |
| RUBBER | Cao su | Rubber/Plantation | PHR, DPR, TRC |
| FERTILIZER | Phân bón | Fertilizer/Chemicals | DPM, DCM, LAS, BFC |
| AVIATION | Hàng không | Aviation | HVN, VJC, ACV |
| UTILITIES | Tiện ích | Utilities | BWE, TDM, AWC |
| OTHER | Khác | Other | (catch-all) |

### Industry Assignment Strategy
1. **Primary source**: `stocks.industry_icb3` / `stocks.industry_icb4` from vnstock company profile
2. **Manual mapping**: Map ICB subcategories to VN groups
3. **Fallback**: Manual assignment for stocks with missing ICB data

```python
ICB_TO_VN_GROUP = {
    "Ngân hàng": "BANKING",
    "Bất động sản": "REAL_ESTATE",
    "Dịch vụ tài chính": "SECURITIES",  # may need finer mapping
    "Bảo hiểm": "INSURANCE",
    "Thép": "STEEL",
    "Thủy sản": "SEAFOOD",
    # ... complete mapping
}
```

Note from UAT: ICB3/ICB4 fields may be None for some stocks (VNM had None). Fallback: query vnstock `company.overview()` which returns `icb_name3`/`icb_name4` keys, or use a hardcoded mapping file.

## 6. Trend Detection (TECH-03)

### Algorithm: Multi-Signal Trend Classification

```python
def detect_trend(df: pd.DataFrame) -> str:
    """Classify trend using MA crossovers and price action."""
    latest = df.iloc[-1]
    
    signals = {
        "ma_alignment": 0,  # +1 bullish, -1 bearish
        "price_vs_ma": 0,
        "macd_signal": 0,
        "adx_trend": 0,
    }
    
    # 1. MA Alignment: SMA20 > SMA50 > SMA200 = strong uptrend
    if latest['SMA_20'] > latest['SMA_50'] > latest['SMA_200']:
        signals['ma_alignment'] = 1
    elif latest['SMA_20'] < latest['SMA_50'] < latest['SMA_200']:
        signals['ma_alignment'] = -1
    
    # 2. Price vs MA: close above/below SMA50
    if latest['close'] > latest['SMA_50']:
        signals['price_vs_ma'] = 1
    elif latest['close'] < latest['SMA_50']:
        signals['price_vs_ma'] = -1
    
    # 3. MACD: histogram positive/negative
    if latest['MACDh_12_26_9'] > 0:
        signals['macd_signal'] = 1
    else:
        signals['macd_signal'] = -1
    
    # 4. ADX: trend strength
    # ADX > 25 = trending, < 20 = sideways
    adx = latest['ADX_14']
    
    score = sum(signals.values())
    
    if adx < 20:
        return 'sideways'
    elif score >= 2:
        return 'uptrend'
    elif score <= -2:
        return 'downtrend'
    else:
        return 'sideways'
```

### Trend Strength
- Use ADX value directly: 0-20 (weak/sideways), 20-40 (moderate), 40-60 (strong), 60+ (extreme)

## 7. Support & Resistance (TECH-04)

### Pivot Points Calculation
Standard (Floor) Pivot Points:
```python
def pivot_points(high: float, low: float, close: float) -> dict:
    """Calculate standard pivot points from previous day's HLC."""
    pp = (high + low + close) / 3
    return {
        'pivot_point': pp,
        'support_1': 2 * pp - high,
        'support_2': pp - (high - low),
        'resistance_1': 2 * pp - low,
        'resistance_2': pp + (high - low),
    }
```

### Peak/Trough Detection
Use scipy or custom rolling window approach:
```python
from scipy.signal import argrelextrema
import numpy as np

def find_support_resistance(df: pd.DataFrame, order: int = 20) -> tuple[float, float]:
    """Find nearest support and resistance from peaks/troughs.
    
    Args:
        df: OHLCV DataFrame with 'close' column
        order: Number of points on each side to compare (default 20 trading days)
    
    Returns:
        (nearest_support, nearest_resistance)
    """
    close = df['close'].values
    current_price = close[-1]
    
    # Find local maxima (resistance candidates)
    max_idx = argrelextrema(close, np.greater, order=order)[0]
    # Find local minima (support candidates)
    min_idx = argrelextrema(close, np.less, order=order)[0]
    
    resistances = close[max_idx]
    supports = close[min_idx]
    
    # Nearest support below current price
    below = supports[supports < current_price]
    nearest_support = float(below.max()) if len(below) > 0 else None
    
    # Nearest resistance above current price
    above = resistances[resistances > current_price]
    nearest_resistance = float(above.min()) if len(above) > 0 else None
    
    return nearest_support, nearest_resistance
```

**Note:** scipy is not in current dependencies — add it or implement a simpler manual approach without scipy. Recommendation: use a manual rolling window to avoid extra dependency.

### Manual Peak/Trough (No scipy)
```python
def find_peaks_manual(prices: list[float], order: int = 20) -> list[int]:
    """Find local maxima indices using rolling comparison."""
    peaks = []
    for i in range(order, len(prices) - order):
        if all(prices[i] >= prices[i-j] for j in range(1, order+1)) and \
           all(prices[i] >= prices[i+j] for j in range(1, order+1)):
            peaks.append(i)
    return peaks
```

## 8. Batch Processing Strategy

### Architecture: Service Layer Pattern

```
AnalysisService
├── TechnicalAnalyzer
│   ├── compute_indicators(symbol) → DataFrame
│   ├── detect_trend(symbol) → TrendResult
│   └── find_support_resistance(symbol) → SRResult
├── FundamentalAnalyzer
│   ├── compute_ratios(symbol) → RatioResult
│   └── compute_growth(symbol) → GrowthResult
├── IndustryAnalyzer
│   ├── assign_industries() → None
│   └── compute_averages(period) → None
└── run_analysis(symbols?) → AnalysisResult
```

### Processing Flow for ~400 Stocks

1. **Load all prices at once** (batch query for all symbols with all dates)
   - ~400 symbols × ~500 days ≈ 200K rows → fits in memory (~50-100MB as DataFrame)
   - Single DB query: `SELECT * FROM stock_prices ORDER BY symbol, date`
   - Group by symbol: `df.groupby('symbol')`

2. **Compute indicators per symbol** (CPU-bound, synchronous)
   - pandas-ta operates on a single symbol's DataFrame
   - Process sequentially — pandas-ta is fast (< 1s per symbol for 500 days)
   - Total: ~400 symbols × 0.5s ≈ 3-4 minutes

3. **Bulk upsert results** (async, batched)
   - Batch INSERT with ON CONFLICT DO UPDATE
   - Batch size: 1000 rows per INSERT

4. **Financial ratios** (lighter — one per quarter)
   - Load all financial_statements
   - Compute ratios per symbol
   - Much less data than indicators

### Memory Considerations
- 200K price rows at ~8 columns × 8 bytes ≈ 13MB raw
- pandas overhead 3-5x ≈ 50-65MB
- Indicator columns add ~20 more columns ≈ another 30MB
- Total peak memory: ~100-150MB — well within typical server limits

### Error Handling
- Per-symbol try/except — one failing stock shouldn't block others
- Log failures, continue processing
- Track success/failure counts in `pipeline_runs`

## 9. Integration with Existing Code

### File Structure

```
src/localstock/
├── analysis/
│   ├── __init__.py
│   ├── technical.py        # TechnicalAnalyzer class
│   ├── fundamental.py      # FundamentalAnalyzer class
│   ├── industry.py         # IndustryAnalyzer + VN group definitions
│   └── trend.py            # Trend detection + S/R algorithms
├── db/
│   ├── models.py           # ADD: TechnicalIndicator, FinancialRatio, IndustryGroup, StockIndustryMapping, IndustryAverage
│   └── repositories/
│       ├── indicator_repo.py   # NEW: CRUD for technical_indicators
│       ├── ratio_repo.py       # NEW: CRUD for financial_ratios
│       └── industry_repo.py    # NEW: CRUD for industry tables
├── services/
│   └── analysis_service.py     # NEW: Orchestrates full analysis pipeline
└── api/
    └── routes/
        └── analysis.py         # NEW: API endpoints for analysis results
```

### API Endpoints (new)
```
GET /api/analysis/{symbol}/technical   → latest technical indicators
GET /api/analysis/{symbol}/fundamental → latest financial ratios
GET /api/analysis/{symbol}/trend       → trend direction + S/R levels
GET /api/analysis/run                  → POST trigger analysis run
GET /api/industry/groups               → list industry groups
GET /api/industry/{group}/averages     → industry average ratios
```

### Integration Points
- **Reads from**: `stock_prices`, `financial_statements`, `stocks` (existing Phase 1 tables)
- **Writes to**: `technical_indicators`, `financial_ratios`, `industry_groups`, `stock_industry_mapping`, `industry_averages` (new tables)
- **Reuses**: `database.py` (engine/session factory), `config.py` (settings), repository pattern from Phase 1

## 10. Alembic Migration

### Migration for Phase 2 Tables

Need one migration file adding all 5 new tables:
1. `technical_indicators` — daily technical indicator values
2. `financial_ratios` — quarterly/TTM financial ratios
3. `industry_groups` — VN industry group definitions
4. `stock_industry_mapping` — stock-to-industry assignment
5. `industry_averages` — precomputed industry averages

```bash
uv run alembic revision --autogenerate -m "add analysis tables"
uv run alembic upgrade head
```

### Important
- Migration must use `DateTime(timezone=True)` for all timestamp columns (learned from Phase 1 UAT)
- Use the same async migration env pattern from Phase 1 (`alembic/env.py` with URL scheme conversion)

## 11. Validation Architecture

### Requirement Verification Matrix

| Requirement | Validation Method | Expected Output |
|-------------|------------------|-----------------|
| TECH-01 | Query `technical_indicators` WHERE sma_20 IS NOT NULL | All symbols have at least 200 rows with indicators |
| TECH-02 | Query `technical_indicators` WHERE avg_volume_20 IS NOT NULL | Volume analysis computed for all symbols |
| TECH-03 | Query `technical_indicators` WHERE trend_direction IS NOT NULL | Trend classified for all symbols |
| TECH-04 | Query `technical_indicators` WHERE pivot_point IS NOT NULL | S/R levels computed for all symbols |
| FUND-01 | Query `financial_ratios` WHERE pe_ratio IS NOT NULL | Ratios computed for all symbols with financial data |
| FUND-02 | Query `financial_ratios` WHERE revenue_yoy IS NOT NULL | Growth rates computed |
| FUND-03 | Query `industry_averages` JOIN on group_code | Industry averages available for comparison |

### Test Strategy
- Unit tests: Each analyzer function with mock DataFrames
- Integration tests: Full pipeline run for a single symbol (VNM)
- Validation: Count of symbols with computed indicators vs total symbols

---

## RESEARCH COMPLETE

Key decisions for planning:
1. **pandas-ta** for indicator calculation (already researched, move to main deps)
2. **Flat columns** for indicator storage (not JSONB) for efficient querying
3. **5 new tables**: technical_indicators, financial_ratios, industry_groups, stock_industry_mapping, industry_averages
4. **VN-specific industry groups** (~20 groups) with manual ICB mapping
5. **Sequential processing** per symbol (CPU-bound, no async benefit for computation)
6. **Bulk upsert** for DB writes (async, batched)
7. **Manual peak/trough** detection (avoid scipy dependency)
8. **New `analysis/` module** following existing service+repository pattern
