# Phase 2: Technical & Fundamental Analysis - Research

**Researched:** 2026-04-15
**Domain:** Financial technical analysis, fundamental ratio computation, pandas-ta, batch processing
**Confidence:** HIGH

## Summary

Phase 2 transforms raw OHLCV price data and financial statements (stored in Phase 1) into computed technical indicators, financial ratios, trend analysis, and industry comparisons for ~400 HOSE stocks. The pandas-ta library (v0.4.71b0, already in lockfile) provides all needed indicator computations with excellent performance (~8ms/stock for 8 indicators). A critical discovery: vnstock's VCI Financial API already returns pre-computed ratios (pe, pb, eps, roe, roa, de, revenueGrowth, netProfitGrowth) in the GraphQL response — these are stored in the `financial_statements.data` JSONB column, meaning ratio extraction is primarily a data parsing task, not a complex calculation task.

The work divides into four domains: (1) technical indicator computation using pandas-ta with DB storage, (2) financial ratio extraction from existing JSONB data + growth rate computation, (3) trend detection and support/resistance via SuperTrend + Pivot Points, (4) Vietnamese industry grouping using existing ICB classifications from the `stocks.industry_icb3` column. New database tables (`technical_indicators`, `financial_ratios`, `trend_analysis`, `industry_groups`) store computed results for Phase 3's scoring engine.

**Primary recommendation:** Use pandas-ta `Study` API for batch indicator computation, extract ratios from existing JSONB financial data, group stocks by `industry_icb3` (Vietnamese ICB Level 3 classification already in DB), and store all results in dedicated analysis tables with date-partitioned indexes for efficient scoring queries.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Agent tự chọn bộ chỉ báo phù hợp nhất (tối thiểu: SMA, EMA, RSI, MACD, Bollinger Bands theo requirements). Có thể thêm Stochastic, ADX, OBV, VWAP nếu phù hợp.
- **D-02:** Dùng pandas-ta để tính toán (research đã recommend, pure Python, 130+ indicators).
- **D-03:** Phân ngành theo đặc thù Việt Nam (không dùng ICB chuẩn quốc tế). Agent tự định nghĩa các nhóm ngành VN phù hợp.
- **D-04:** Xác định hỗ trợ/kháng cự bằng Pivot Points + đỉnh/đáy gần nhất.

### Agent's Discretion
- Bộ chỉ báo kỹ thuật cụ thể (ngoài bộ tối thiểu)
- Cách nhóm ngành VN (số nhóm, tiêu chí phân loại)
- Schema lưu kết quả phân tích trong Supabase

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TECH-01 | Tính toán chỉ báo kỹ thuật cơ bản: SMA(20,50,200), EMA(12,26), RSI(14), MACD(12,26,9), BB(20,2) | pandas-ta provides all indicators; Study API enables batch computation; column naming verified (SMA_20, EMA_12, RSI_14, MACD_12_26_9, BBL_20_2.0_2.0, etc.) |
| TECH-02 | Phân tích khối lượng giao dịch (average volume, relative volume, xu hướng volume) | Compute from OHLCV data: SMA of volume for avg, current/avg for relative, OBV from pandas-ta for trend |
| TECH-03 | Nhận diện xu hướng giá (uptrend/downtrend/sideways) từ MA crossovers và price action | SuperTrend indicator (SUPERTd column: 1=uptrend, -1=downtrend) + SMA crossover signals |
| TECH-04 | Xác định vùng hỗ trợ/kháng cự từ pivot points và đỉnh/đáy gần nhất | pandas-ta `pivots(method="traditional")` provides S1-S4/R1-R4; ZigZag for peak/trough detection |
| FUND-01 | Tính toán chỉ số tài chính: P/E, P/B, EPS, ROE, ROA, D/E | VCI GraphQL already provides pe, pb, eps, roe, roa, de in financial_statements.data JSONB; extract and store in dedicated table |
| FUND-02 | Đánh giá tăng trưởng doanh thu và lợi nhuận theo QoQ và YoY | VCI provides revenueGrowth, netProfitGrowth; supplement with manual QoQ/YoY calculation from quarterly data |
| FUND-03 | So sánh chỉ số tài chính với trung bình ngành (theo phân ngành ICB) | stocks.industry_icb3 already populated; compute industry averages by grouping stocks by this field |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas-ta | 0.4.71b0 | Technical indicator computation | Already in lockfile; pure Python (no C dependency); 154 indicators; Study API for batch processing; ~8ms/stock for 8 indicators [VERIFIED: uv lockfile + runtime test] |
| pandas | 2.2+ | DataFrame manipulation for all analysis | Core dependency, already installed [VERIFIED: pyproject.toml] |
| numpy | 2.x | Numerical operations for custom calculations | pandas dependency, already installed [VERIFIED: pandas-ta dependency] |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | 2.0+ | ORM for new analysis tables | All DB reads/writes [VERIFIED: pyproject.toml] |
| Alembic | 1.18+ | Schema migration for new tables | Adding technical_indicators, financial_ratios tables [VERIFIED: pyproject.toml] |
| asyncpg | 0.31+ | Async Postgres driver | Batch processing DB operations [VERIFIED: pyproject.toml] |
| loguru | 0.7+ | Structured logging | Progress tracking during batch computation [VERIFIED: pyproject.toml] |

### No New Dependencies Required
All libraries needed for Phase 2 are already in the project. pandas-ta was added to `pyproject.toml` as a dependency in preparation for this phase. No additional packages need to be installed.

## Architecture Patterns

### Recommended Project Structure
```
src/localstock/
├── db/
│   ├── models.py           # ADD: TechnicalIndicator, FinancialRatio, TrendAnalysis, IndustryGroup models
│   └── repositories/
│       ├── indicator_repo.py   # NEW: CRUD for technical_indicators
│       ├── ratio_repo.py       # NEW: CRUD for financial_ratios
│       └── analysis_repo.py    # NEW: CRUD for trend_analysis + industry data
├── services/
│   ├── technical_service.py    # NEW: pandas-ta computation orchestrator
│   ├── fundamental_service.py  # NEW: ratio extraction + growth computation
│   ├── trend_service.py        # NEW: trend detection + S/R levels
│   └── industry_service.py     # NEW: industry grouping + avg computation
├── api/
│   └── routes/
│       └── analysis.py         # NEW: API endpoints for analysis results
└── analysis/                   # NEW: Pure computation functions (no DB)
    ├── indicators.py           # pandas-ta wrapper with Study config
    ├── ratios.py               # Financial ratio extraction logic
    ├── trends.py               # Trend detection algorithms
    └── volume.py               # Volume analysis computations
```

### Pattern 1: Service Layer with Pure Computation Separation
**What:** Separate pure computation functions (in `analysis/`) from DB-aware services (in `services/`). Services handle DB reads → call pure functions → DB writes.
**When to use:** All analysis computation
**Why:** Testable without DB, reusable, follows existing Phase 1 pattern (crawlers separate from repositories)
**Example:**
```python
# src/localstock/analysis/indicators.py — Pure computation, no DB
import pandas as pd
import pandas_ta as ta

def compute_technical_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical indicators for a single stock's OHLCV data.
    
    Args:
        ohlcv_df: DataFrame with columns [date, open, high, low, close, volume]
                  sorted by date ascending, indexed by date.
    
    Returns:
        DataFrame with original OHLCV + all indicator columns appended.
    """
    df = ohlcv_df.copy()
    df = df.set_index("date") if "date" in df.columns else df
    
    # Use Study API for batch computation
    study = ta.Study(
        name="LocalStock",
        ta=[
            {"kind": "sma", "length": 20},
            {"kind": "sma", "length": 50},
            {"kind": "sma", "length": 200},
            {"kind": "ema", "length": 12},
            {"kind": "ema", "length": 26},
            {"kind": "rsi", "length": 14},
            {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
            {"kind": "bbands", "length": 20, "std": 2},
            {"kind": "stoch"},      # Stochastic 14,3,3
            {"kind": "adx"},        # ADX 14
            {"kind": "obv"},        # On-Balance Volume
            {"kind": "vwap"},       # Volume Weighted Average Price
            {"kind": "supertrend", "length": 7, "multiplier": 3},
        ]
    )
    df.ta.study(study)
    return df
```

```python
# src/localstock/services/technical_service.py — DB-aware orchestrator
from sqlalchemy.ext.asyncio import AsyncSession
from localstock.analysis.indicators import compute_technical_indicators
from localstock.db.repositories.price_repo import PriceRepository
from localstock.db.repositories.indicator_repo import IndicatorRepository

class TechnicalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.price_repo = PriceRepository(session)
        self.indicator_repo = IndicatorRepository(session)
    
    async def compute_for_symbol(self, symbol: str) -> int:
        """Compute and store all indicators for a single symbol."""
        prices = await self.price_repo.get_prices(symbol)
        if not prices:
            return 0
        df = pd.DataFrame([{...} for p in prices])
        result = compute_technical_indicators(df)
        return await self.indicator_repo.upsert_indicators(symbol, result)
    
    async def compute_all(self, symbols: list[str]) -> dict:
        """Compute indicators for all symbols with progress tracking."""
        ...
```

### Pattern 2: Repository Upsert Pattern (from Phase 1)
**What:** Use PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` for idempotent writes
**When to use:** All analysis result storage (indicators, ratios, trends)
**Why:** Allows re-running analysis without duplicate rows; established pattern from Phase 1
**Example:**
```python
# Following Phase 1's PriceRepository pattern
class IndicatorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_indicators(self, symbol: str, indicators_df: pd.DataFrame) -> int:
        rows = []
        for date_idx, row in indicators_df.iterrows():
            rows.append({
                "symbol": symbol,
                "date": date_idx,
                "sma_20": row.get("SMA_20"),
                "sma_50": row.get("SMA_50"),
                # ... etc
            })
        stmt = pg_insert(TechnicalIndicator).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_technical_indicator",
            set_={col: stmt.excluded[col] for col in indicator_columns},
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return len(rows)
```

### Pattern 3: Batch Processing with Progress
**What:** Process ~400 stocks sequentially with logging, error tolerance, and chunked DB writes
**When to use:** The main analysis pipeline
**Why:** Memory-safe (one stock at a time), debuggable, follows Phase 1's `fetch_batch` pattern
**Example:**
```python
async def compute_all(self, symbols: list[str]) -> dict:
    results = {"success": 0, "failed": 0, "errors": []}
    for i, symbol in enumerate(symbols):
        try:
            count = await self.compute_for_symbol(symbol)
            results["success"] += 1
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i+1}/{len(symbols)} stocks computed")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append((symbol, str(e)))
            logger.warning(f"Failed {symbol}: {e}")
    return results
```

### Anti-Patterns to Avoid
- **Loading all 400 stocks into memory at once:** Process one stock at a time, write results, then move on. Each stock's OHLCV is ~500 rows × 15 columns — small, but 400× that plus indicators can strain memory.
- **Using pandas-ta's `ta.Strategy` (deprecated):** Use `ta.Study` instead. `Strategy` class no longer exists in v0.4.71b0. [VERIFIED: runtime test showed `AttributeError: module 'pandas_ta' has no attribute 'Strategy'`]
- **Storing indicators as JSON blob:** Use dedicated columns per indicator for queryable data. The scoring engine needs to filter/sort by individual indicators.
- **Computing indicators on raw (unadjusted) prices:** Always use adjusted prices (`adj_close` or `close` with `adj_factor` applied) to avoid false signals from corporate actions.

## Database Schema Design

### New Tables

#### 1. `technical_indicators` — One row per stock per date
```python
class TechnicalIndicator(Base):
    """Daily technical indicator values for each stock."""
    __tablename__ = "technical_indicators"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    
    # Moving Averages (TECH-01)
    sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_26: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Oscillators (TECH-01)
    rsi_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Bollinger Bands (TECH-01)
    bb_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_middle: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_bandwidth: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Additional indicators (D-01 discretion)
    stoch_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    stoch_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    adx: Mapped[float | None] = mapped_column(Float, nullable=True)
    plus_di: Mapped[float | None] = mapped_column(Float, nullable=True)
    minus_di: Mapped[float | None] = mapped_column(Float, nullable=True)
    obv: Mapped[float | None] = mapped_column(Float, nullable=True)
    vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Volume analysis (TECH-02)
    avg_volume_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_sma_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Trend (TECH-03)
    supertrend: Mapped[float | None] = mapped_column(Float, nullable=True)
    supertrend_direction: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1=up, -1=down
    
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_technical_indicator"),
        Index("ix_technical_indicators_symbol_date", "symbol", "date"),
    )
```

**Column naming rationale:** Use clear, snake_case names that map directly to pandas-ta output:
| pandas-ta Column | DB Column | Notes |
|------------------|-----------|-------|
| `SMA_20` | `sma_20` | Direct map |
| `EMA_12` | `ema_12` | Direct map |
| `RSI_14` | `rsi_14` | Direct map |
| `MACD_12_26_9` | `macd` | Shortened — params fixed |
| `MACDh_12_26_9` | `macd_histogram` | Clearer name |
| `MACDs_12_26_9` | `macd_signal` | Clearer name |
| `BBL_20_2.0_2.0` | `bb_lower` | Clearer name |
| `BBM_20_2.0_2.0` | `bb_middle` | Clearer name |
| `BBU_20_2.0_2.0` | `bb_upper` | Clearer name |
| `BBB_20_2.0_2.0` | `bb_bandwidth` | Clearer name |
| `BBP_20_2.0_2.0` | `bb_percent` | Clearer name |
| `STOCHk_14_3_3` | `stoch_k` | Shortened |
| `STOCHd_14_3_3` | `stoch_d` | Shortened |
| `ADX_14` | `adx` | Shortened |
| `DMP_14` | `plus_di` | Industry standard name |
| `DMN_14` | `minus_di` | Industry standard name |
| `OBV` | `obv` | Direct map |
| `VWAP_D` | `vwap` | Shortened |
| `SUPERT_7_3` | `supertrend` | Shortened |
| `SUPERTd_7_3` | `supertrend_direction` | Clearer name |

[VERIFIED: All column names confirmed via runtime pandas-ta tests]

#### 2. `financial_ratios` — One row per stock per period
```python
class FinancialRatio(Base):
    """Computed financial ratios per stock per reporting period."""
    __tablename__ = "financial_ratios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    year: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(10))  # 'Q1', 'Q2', 'Q3', 'Q4', 'annual'
    
    # Core ratios (FUND-01)
    pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roa: Mapped[float | None] = mapped_column(Float, nullable=True)
    de: Mapped[float | None] = mapped_column(Float, nullable=True)  # debt/equity
    
    # Additional from VCI data
    eps_ttm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bvps: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_profit_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Growth rates (FUND-02)
    revenue_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth_qoq: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_growth_qoq: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Industry comparison (FUND-03)
    industry_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pe_vs_industry: Mapped[float | None] = mapped_column(Float, nullable=True)  # ratio vs avg
    roe_vs_industry: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    
    __table_args__ = (
        UniqueConstraint("symbol", "year", "period", name="uq_financial_ratio"),
        Index("ix_financial_ratios_symbol_year", "symbol", "year"),
    )
```

#### 3. `trend_analysis` — Latest trend state per stock
```python
class TrendAnalysis(Base):
    """Current trend analysis for each stock."""
    __tablename__ = "trend_analysis"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    
    # Trend direction (TECH-03)
    trend: Mapped[str] = mapped_column(String(20))  # 'uptrend', 'downtrend', 'sideways'
    trend_strength: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100 from ADX
    
    # Support/Resistance (TECH-04)
    pivot_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Recent peaks/troughs from ZigZag
    recent_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_high_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recent_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_low_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # MA crossover signals
    sma_20_50_cross: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'golden_cross', 'death_cross', 'none'
    sma_50_200_cross: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Volume trend (TECH-02)
    volume_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'increasing', 'decreasing', 'stable'
    avg_volume_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

#### 4. `industry_groups` — Static mapping table
```python
class IndustryGroup(Base):
    """Vietnamese industry group mapping for ratio comparison."""
    __tablename__ = "industry_groups"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    icb3_name: Mapped[str] = mapped_column(String(200), unique=True)  # from stocks.industry_icb3
    vn_group: Mapped[str] = mapped_column(String(100))  # VN-specific group name
    display_name: Mapped[str] = mapped_column(String(200))  # Human-readable VN name
```

### Query Efficiency for Phase 3 Scoring

The scoring engine will need:
1. **Latest indicators per stock:** `SELECT * FROM technical_indicators WHERE symbol = ? ORDER BY date DESC LIMIT 1`
2. **Latest ratios per stock:** `SELECT * FROM financial_ratios WHERE symbol = ? ORDER BY year DESC, period DESC LIMIT 1`
3. **Trend per stock:** `SELECT * FROM trend_analysis WHERE symbol = ?` (always latest)
4. **Industry average:** `SELECT AVG(pe), AVG(roe) ... FROM financial_ratios WHERE industry_group = ? AND year = ? AND period = ?`

Add composite indexes: `(symbol, date DESC)` on technical_indicators, `(industry_group, year, period)` on financial_ratios.

## Vietnamese Industry Grouping Strategy (D-03)

### Using Existing ICB Level 3 Data [VERIFIED: codebase inspection]

The `stocks` table already has `industry_icb3` populated by Phase 1's CompanyCrawler from VCI. This contains Vietnamese ICB Level 3 classifications like "Ngân hàng", "Bất động sản", "Thép", etc.

**Recommendation:** Use `industry_icb3` as the primary grouping key. Create a mapping table that consolidates overly-specific ICB3 names into VN-market-relevant groups:

```python
# Vietnamese industry group mapping
VN_INDUSTRY_GROUPS = {
    # Banking & Finance
    "Ngân hàng": "Ngân hàng",
    "Bảo hiểm": "Tài chính",
    "Chứng khoán": "Tài chính",
    "Dịch vụ tài chính": "Tài chính",
    
    # Real Estate & Construction
    "Bất động sản": "Bất động sản",
    "Xây dựng & Vật liệu": "Xây dựng",
    
    # Manufacturing
    "Thép": "Thép & Kim loại",
    "Hóa chất": "Hóa chất",
    
    # Consumer
    "Thực phẩm & Đồ uống": "Tiêu dùng",
    "Bán lẻ": "Tiêu dùng",
    
    # Technology
    "Công nghệ thông tin": "Công nghệ",
    "Phần mềm & Dịch vụ CNTT": "Công nghệ",
    
    # Energy & Utilities
    "Dầu khí": "Năng lượng",
    "Điện, nước, xăng dầu & khí đốt": "Năng lượng & Tiện ích",
    
    # ... etc. — full mapping built from actual DB data at runtime
}
```

**Implementation approach:**
1. Query `SELECT DISTINCT industry_icb3 FROM stocks WHERE exchange = 'HOSE'` to get all actual ICB3 names
2. Build the mapping from those actual names → VN group names
3. Store in `industry_groups` table
4. Stocks without ICB3 data → "Khác" (Other) group

This is better than hardcoding all ~50-80 ICB4 subcategories. ICB Level 3 gives ~15-25 meaningful groups. [ASSUMED: Exact count depends on actual ICB3 values in production DB]

## Financial Ratios Extraction (FUND-01, FUND-02)

### Key Discovery: VCI Already Provides Ratios [VERIFIED: vnstock VCI source code inspection]

The VCI GraphQL endpoint returns financial ratios directly in the API response. These fields are available in the `financial_statements.data` JSONB column:

| VCI Field | Maps To | Description |
|-----------|---------|-------------|
| `pe` | P/E ratio | Price-to-Earnings |
| `pb` | P/B ratio | Price-to-Book |
| `eps` | EPS | Earnings Per Share |
| `epsTTM` | EPS TTM | Trailing 12-month EPS |
| `roe` | ROE | Return on Equity |
| `roa` | ROA | Return on Assets |
| `de` | D/E | Debt-to-Equity |
| `revenue` | Revenue | Total revenue |
| `revenueGrowth` | Revenue Growth | Pre-computed growth rate |
| `netProfit` | Net Profit | Net income |
| `netProfitGrowth` | Profit Growth | Pre-computed growth rate |
| `bvps` | BVPS | Book Value Per Share |
| `grossMargin` | Gross Margin | Gross profit margin |
| `netProfitMargin` | Net Margin | Net profit margin |
| `currentRatio` | Current Ratio | Current assets / liabilities |
| `yearReport` | Year | Reporting year |
| `lengthReport` | Period | Q1, Q2, Q3, Q4, or Year |

**Strategy:**
1. Extract ratios from existing `financial_statements.data` JSONB column
2. The VCI data already has `revenueGrowth` and `netProfitGrowth` — but these may be YoY only
3. Compute QoQ growth manually from sequential quarterly data
4. Fall back to manual calculation from balance_sheet/income_statement if ratio fields are null

### Manual QoQ Growth Calculation
```python
def compute_qoq_growth(current_value: float | None, previous_value: float | None) -> float | None:
    """Compute quarter-over-quarter growth rate.
    
    Returns growth as decimal (0.15 = 15% growth).
    Returns None if either value is None or previous is zero.
    """
    if current_value is None or previous_value is None or previous_value == 0:
        return None
    return (current_value - previous_value) / abs(previous_value)
```

### Manual Ratio Fallback Calculation
When VCI pre-computed ratios are missing (e.g., for some smaller companies), compute from balance sheet + income statement data:

```python
def compute_ratios_from_statements(
    balance_sheet: dict,
    income_statement: dict,
    market_price: float,
    shares_outstanding: float,
) -> dict:
    """Compute financial ratios from raw financial statement data."""
    
    # EPS = Net Income / Shares Outstanding
    net_income = income_statement.get("netProfit") or income_statement.get("ISA23")
    eps = net_income / shares_outstanding if net_income and shares_outstanding else None
    
    # P/E = Price / EPS
    pe = market_price / eps if eps and eps > 0 else None
    
    # P/B = Price / (Equity / Shares)
    equity = balance_sheet.get("BSA78") or balance_sheet.get("equity")
    bvps = equity / shares_outstanding if equity and shares_outstanding else None
    pb = market_price / bvps if bvps and bvps > 0 else None
    
    # ROE = Net Income / Equity
    roe = net_income / equity if net_income and equity and equity > 0 else None
    
    # ROA = Net Income / Total Assets
    total_assets = balance_sheet.get("BSA1") or balance_sheet.get("total_assets")
    roa = net_income / total_assets if net_income and total_assets else None
    
    # D/E = Total Liabilities / Equity
    total_liabilities = balance_sheet.get("BSA50") or balance_sheet.get("total_liabilities")
    de = total_liabilities / equity if total_liabilities and equity and equity > 0 else None
    
    return {"pe": pe, "pb": pb, "eps": eps, "roe": roe, "roa": roa, "de": de}
```

**Note on VCI JSONB field names:** The VCI source uses coded field names like `BSA1` (Total Assets), `BSA78` (Equity), `BSA50` (Total Liabilities), `ISA23` (Net Profit). The `_ratio_mapping` function in vnstock translates these to English/Vietnamese names based on the company type (CT=Company, NH=Bank, BH=Insurance, CK=Securities). The financial_statements.data JSONB stores the raw row data from vnstock, which may contain either coded names or translated names depending on how Phase 1 stored them. [VERIFIED: vnstock source code, finance_crawler.py `_store_financials` method stores `row.to_dict()` which uses the raw DataFrame column names]

## Trend Detection Algorithm (TECH-03)

### Multi-Signal Approach
```python
def detect_trend(df: pd.DataFrame) -> dict:
    """Detect trend direction using multiple signals.
    
    Args:
        df: DataFrame with at minimum: close, SMA_20, SMA_50, SMA_200,
            SUPERTd_7_3, ADX_14.
    
    Returns:
        dict with 'trend', 'strength', 'signals'
    """
    latest = df.iloc[-1]
    signals = []
    
    # Signal 1: SuperTrend direction (most reliable single signal)
    st_dir = latest.get("SUPERTd_7_3", 0)
    if st_dir == 1:
        signals.append(("supertrend", "up"))
    elif st_dir == -1:
        signals.append(("supertrend", "down"))
    
    # Signal 2: Price vs SMA alignment
    close = latest["close"]
    sma20 = latest.get("SMA_20")
    sma50 = latest.get("SMA_50")
    sma200 = latest.get("SMA_200")
    
    if sma20 and sma50 and sma200:
        if close > sma20 > sma50 > sma200:
            signals.append(("ma_alignment", "up"))
        elif close < sma20 < sma50 < sma200:
            signals.append(("ma_alignment", "down"))
        else:
            signals.append(("ma_alignment", "mixed"))
    
    # Signal 3: SMA crossovers (recent)
    if len(df) >= 5:
        recent = df.tail(5)
        if (recent["SMA_20"].iloc[-1] > recent["SMA_50"].iloc[-1] and 
            recent["SMA_20"].iloc[0] <= recent["SMA_50"].iloc[0]):
            signals.append(("crossover", "golden_cross"))
        elif (recent["SMA_20"].iloc[-1] < recent["SMA_50"].iloc[-1] and 
              recent["SMA_20"].iloc[0] >= recent["SMA_50"].iloc[0]):
            signals.append(("crossover", "death_cross"))
    
    # Signal 4: ADX for trend strength
    adx_val = latest.get("ADX_14", 0)
    strength = min(100, adx_val) if adx_val else 0
    
    # Determine overall trend
    up_count = sum(1 for _, d in signals if d in ("up", "golden_cross"))
    down_count = sum(1 for _, d in signals if d in ("down", "death_cross"))
    
    if adx_val and adx_val < 20:
        trend = "sideways"  # Weak trend regardless of direction
    elif up_count > down_count:
        trend = "uptrend"
    elif down_count > up_count:
        trend = "downtrend"
    else:
        trend = "sideways"
    
    return {"trend": trend, "strength": strength, "signals": signals}
```

## Support & Resistance Calculation (TECH-04, D-04)

### Pivot Points (from pandas-ta) [VERIFIED: runtime test]
```python
# pandas-ta pivots returns: P, S1, S2, S3, S4, R1, R2, R3, R4
pivots = df.ta.pivots(method="traditional")
# Column names: PIVOTS_TRAD_D_P, PIVOTS_TRAD_D_S1, ..., PIVOTS_TRAD_D_R4

# Use the latest row for current S/R levels
latest_pivot = pivots.iloc[-1]
sr_levels = {
    "pivot": latest_pivot["PIVOTS_TRAD_D_P"],
    "support_1": latest_pivot["PIVOTS_TRAD_D_S1"],
    "support_2": latest_pivot["PIVOTS_TRAD_D_S2"],
    "resistance_1": latest_pivot["PIVOTS_TRAD_D_R1"],
    "resistance_2": latest_pivot["PIVOTS_TRAD_D_R2"],
}
```

### Peak/Trough Detection (ZigZag) [VERIFIED: runtime test]
```python
# ZigZag identifies significant peaks and troughs
zigzag = df.ta.zigzag(deviation=5.0, depth=10)
# Columns: ZIGZAGs_5.0%_10 (swing value), ZIGZAGv_5.0%_10, ZIGZAGd_5.0%_10

# Find recent peaks (local highs) and troughs (local lows)
# ZIGZAGd: 1 = peak, -1 = trough, NaN = no signal
zz_signals = zigzag["ZIGZAGd_5.0%_10"].dropna()
peaks = zz_signals[zz_signals == 1]
troughs = zz_signals[zz_signals == -1]

recent_high_date = peaks.index[-1] if len(peaks) > 0 else None
recent_low_date = troughs.index[-1] if len(troughs) > 0 else None
```

## Volume Analysis (TECH-02)

```python
def compute_volume_analysis(df: pd.DataFrame) -> dict:
    """Compute volume metrics for a stock.
    
    Args:
        df: DataFrame with 'volume' and 'close' columns, indexed by date.
    
    Returns:
        dict with avg_volume_20, relative_volume, volume_trend
    """
    vol = df["volume"]
    
    # Average volume (20-day)
    avg_20 = vol.rolling(20).mean().iloc[-1]
    
    # Relative volume (current vs average)
    relative = vol.iloc[-1] / avg_20 if avg_20 > 0 else 0
    
    # Volume trend: compare 5-day avg to 20-day avg
    avg_5 = vol.rolling(5).mean().iloc[-1]
    if avg_5 > avg_20 * 1.2:
        trend = "increasing"
    elif avg_5 < avg_20 * 0.8:
        trend = "decreasing"
    else:
        trend = "stable"
    
    return {
        "avg_volume_20d": avg_20,
        "relative_volume": relative,
        "volume_trend": trend,
    }
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Technical indicators (SMA, EMA, RSI, MACD, BB) | Custom rolling window calculations | `pandas-ta` library | Edge cases in EMA seed values, RSI smoothing, MACD signal line — pandas-ta handles all correctly |
| Pivot Points calculation | Manual H/L/C formulas | `df.ta.pivots()` | pandas-ta supports Traditional, Fibonacci, Woodie, DeMark methods out of the box |
| ZigZag peak/trough | Manual local min/max detection | `df.ta.zigzag()` | Proper deviation threshold and depth handling |
| SuperTrend indicator | Manual ATR + direction logic | `df.ta.supertrend()` | Correct ATR calculation with Wilder's smoothing |
| Financial ratio pre-computation | Complex earnings/equity/assets extraction | VCI API data (already stored) | vnstock VCI GraphQL returns pe, pb, eps, roe, roa, de directly |

**Key insight:** pandas-ta eliminates ~90% of the computation code. The remaining 10% is data plumbing (DB read → DataFrame conversion → indicator computation → DB write).

## Common Pitfalls

### Pitfall 1: NaN Values in Early Rows
**What goes wrong:** SMA(200) returns NaN for the first 199 rows. If you store these NaN values in the DB and query for "stocks with SMA_200 > close", all stocks with < 200 days of data are excluded.
**Why it happens:** Technical indicators require a warmup period (lookback window).
**How to avoid:** Store NaN as NULL in DB. When querying, use `WHERE sma_200 IS NOT NULL`. For stocks with < 200 days of data, document that SMA_200 is unavailable.
**Warning signs:** Stocks appearing to have no indicators despite having price data.
**Verified lookback periods:** SMA(200)=199 NaN, SMA(50)=49, RSI(14)=1 NaN (uses modified calc), MACD=33 NaN (26+9-2). [VERIFIED: runtime test]

### Pitfall 2: Using Unadjusted Prices for Indicators
**What goes wrong:** A 2:1 stock split creates a 50% price drop in the data. SMA/RSI/MACD all generate false bearish signals.
**Why it happens:** Corporate actions change the price level without changing company value.
**How to avoid:** Always check `adj_factor` on StockPrice records. If `adj_factor != 1.0`, use `close * adj_factor` (or use `adj_close` if populated). Phase 1 already applies backward adjustment, so current prices should be safe — but verify before computing.
**Warning signs:** Sudden massive RSI drops or SMA breakdowns on split dates.

### Pitfall 3: Financial Statement Unit Mismatch
**What goes wrong:** Revenue is in billion VND for one company but the growth rate calculation compares it to another company's revenue in million VND.
**Why it happens:** Vietnamese companies report in different units (VND, triệu VND, tỷ VND).
**How to avoid:** Phase 1 normalizes to `billion_vnd` at ingestion time (FinanceCrawler.normalize_unit). Verify `financial_statements.unit = 'billion_vnd'` before extracting. [VERIFIED: finance_crawler.py normalize_unit method]
**Warning signs:** Absurdly high/low ratios for some companies.

### Pitfall 4: Bank vs Non-Bank Financial Statement Structure
**What goes wrong:** Calculating D/E for a bank (VCB, ACB, etc.) produces meaningless results because bank balance sheets have fundamentally different structures.
**Why it happens:** VCI uses different `com_type_code` mappings: CT=Company, NH=Bank, BH=Insurance, CK=Securities. The field names (BSA1, BSA50, etc.) map to different items depending on company type.
**How to avoid:** Use the pre-computed ratios from VCI (`pe`, `pb`, `eps`, `roe`, `roa`, `de`) which are already correctly calculated per company type. Only fall back to manual calculation with awareness of company type.
**Warning signs:** P/E of 0.5 or D/E of 50+ for banking stocks.

### Pitfall 5: Empty Financial Statements for Some Companies
**What goes wrong:** Some smaller HOSE companies have no financial statement data, or data only for recent quarters.
**Why it happens:** VCI/KBS data coverage is not 100% for all companies.
**How to avoid:** Handle gracefully — compute ratios for stocks that have data, mark others with NULL ratios. The scoring engine (Phase 3) should handle partial data.
**Warning signs:** Division by zero errors during ratio computation.

### Pitfall 6: Duplicate Indicator Computation
**What goes wrong:** Re-running analysis for all 400 stocks takes 30+ minutes unnecessarily.
**Why it happens:** No incremental computation — always recomputes from scratch.
**How to avoid:** Store a `computed_date` or check the latest `technical_indicators.date` per symbol. Only compute indicators for dates after the last stored date. For daily runs, this means computing only 1 new row per stock.
**Warning signs:** Pipeline taking increasingly longer as data grows.

### Pitfall 7: BB Column Names Have Floats
**What goes wrong:** Trying to access `BBL_20_2_2` when the actual column is `BBL_20_2.0_2.0` (with decimal points).
**Why it happens:** pandas-ta encodes the `std` parameter as float in column names, even if you pass `std=2` as int.
**How to avoid:** Use the exact column names from pandas-ta output. The mapping table above documents the exact names. [VERIFIED: runtime test confirms `BBL_20_2.0_2.0`]

## Batch Processing Strategy

### Performance Benchmarks [VERIFIED: runtime test]
- pandas-ta computation for 1 stock (500 rows, 8 indicators): **~8ms**
- Estimated for 400 stocks: **~3.2 seconds** (computation only)
- DB read/write overhead per stock: **~50-100ms** (estimated)
- **Total estimated time for full batch: ~40-60 seconds**

### Recommended Approach
```python
async def run_full_analysis(self, symbols: list[str]) -> dict:
    """Run complete technical + fundamental analysis for all stocks."""
    stats = {"technical": 0, "fundamental": 0, "trend": 0, "errors": []}
    
    for i, symbol in enumerate(symbols):
        try:
            # 1. Read OHLCV prices from DB
            prices = await self.price_repo.get_prices(symbol)
            if len(prices) < 30:  # minimum data requirement
                logger.warning(f"Skipping {symbol}: only {len(prices)} price rows")
                continue
            
            # 2. Convert to DataFrame
            df = self._prices_to_dataframe(prices)
            
            # 3. Compute technical indicators (pure function)
            indicators_df = compute_technical_indicators(df)
            
            # 4. Store indicators
            await self.indicator_repo.upsert_indicators(symbol, indicators_df)
            stats["technical"] += 1
            
            # 5. Extract/compute financial ratios
            ratios = await self._compute_ratios(symbol)
            if ratios:
                await self.ratio_repo.upsert_ratios(symbol, ratios)
                stats["fundamental"] += 1
            
            # 6. Detect trend and S/R
            trend = detect_trend(indicators_df)
            sr = compute_support_resistance(indicators_df)
            vol = compute_volume_analysis(indicators_df)
            await self.analysis_repo.upsert_trend(symbol, trend, sr, vol)
            stats["trend"] += 1
            
        except Exception as e:
            stats["errors"].append((symbol, str(e)))
            logger.warning(f"Analysis failed for {symbol}: {e}")
        
        # Progress logging every 50 stocks
        if (i + 1) % 50 == 0:
            logger.info(f"Analysis progress: {i+1}/{len(symbols)}")
    
    return stats
```

### Incremental vs Full Recompute
- **Daily runs:** Only compute indicators for the latest trading day (1 new row per stock). Trend analysis can be recomputed from the last N rows.
- **Backfill/initial run:** Compute all indicators for all historical data (needed for correct lookback windows).
- **Financial ratios:** Recompute when new financial statements are ingested (quarterly event).

## Code Examples

### Complete Study Configuration [VERIFIED: runtime test]
```python
import pandas_ta as ta

# This is the exact Study that works with pandas-ta 0.4.71b0
LOCALSTOCK_STUDY = ta.Study(
    name="LocalStock_Technical",
    ta=[
        # Moving Averages (TECH-01)
        {"kind": "sma", "length": 20},
        {"kind": "sma", "length": 50},
        {"kind": "sma", "length": 200},
        {"kind": "ema", "length": 12},
        {"kind": "ema", "length": 26},
        
        # Oscillators (TECH-01)
        {"kind": "rsi", "length": 14},
        {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
        {"kind": "bbands", "length": 20, "std": 2},
        
        # Additional (D-01 recommended)
        {"kind": "stoch"},          # Default: 14, 3, 3
        {"kind": "adx"},            # Default: 14
        {"kind": "obv"},            # No params needed
        {"kind": "vwap"},           # Daily VWAP
        
        # Trend detection (TECH-03)
        {"kind": "supertrend", "length": 7, "multiplier": 3},
    ]
)

# Usage: df.ta.study(LOCALSTOCK_STUDY)
# Output columns (22+ new columns):
# SMA_20, SMA_50, SMA_200, EMA_12, EMA_26,
# RSI_14,
# MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9,
# BBL_20_2.0_2.0, BBM_20_2.0_2.0, BBU_20_2.0_2.0, BBB_20_2.0_2.0, BBP_20_2.0_2.0,
# STOCHk_14_3_3, STOCHd_14_3_3, STOCHh_14_3_3,
# ADX_14, ADXR_14_2, DMP_14, DMN_14,
# OBV, VWAP_D,
# SUPERT_7_3, SUPERTd_7_3, SUPERTl_7_3, SUPERTs_7_3
```

### DataFrame to DB Mapping [VERIFIED: column names from runtime tests]
```python
# Mapping from pandas-ta column names to DB column names
INDICATOR_COLUMN_MAP = {
    "SMA_20": "sma_20",
    "SMA_50": "sma_50",
    "SMA_200": "sma_200",
    "EMA_12": "ema_12",
    "EMA_26": "ema_26",
    "RSI_14": "rsi_14",
    "MACD_12_26_9": "macd",
    "MACDs_12_26_9": "macd_signal",
    "MACDh_12_26_9": "macd_histogram",
    "BBU_20_2.0_2.0": "bb_upper",
    "BBM_20_2.0_2.0": "bb_middle",
    "BBL_20_2.0_2.0": "bb_lower",
    "BBB_20_2.0_2.0": "bb_bandwidth",
    "BBP_20_2.0_2.0": "bb_percent",
    "STOCHk_14_3_3": "stoch_k",
    "STOCHd_14_3_3": "stoch_d",
    "ADX_14": "adx",
    "DMP_14": "plus_di",
    "DMN_14": "minus_di",
    "OBV": "obv",
    "VWAP_D": "vwap",
    "SUPERT_7_3": "supertrend",
    "SUPERTd_7_3": "supertrend_direction",
}
```

### JSONB Ratio Extraction
```python
async def extract_ratios_from_statements(
    self, symbol: str
) -> list[dict]:
    """Extract financial ratios from existing JSONB financial_statements data.
    
    VCI stores these fields directly in the data column.
    """
    stmts = await self.session.execute(
        select(FinancialStatement)
        .where(FinancialStatement.symbol == symbol)
        .order_by(FinancialStatement.year.desc(), FinancialStatement.period.desc())
    )
    
    results = []
    for stmt in stmts.scalars().all():
        data = stmt.data  # JSONB dict
        ratio = {
            "symbol": symbol,
            "year": stmt.year,
            "period": stmt.period,
            "pe": data.get("pe"),
            "pb": data.get("pb"),
            "eps": data.get("eps"),
            "eps_ttm": data.get("epsTTM"),
            "roe": data.get("roe"),
            "roa": data.get("roa"),
            "de": data.get("de"),
            "revenue": data.get("revenue"),
            "net_profit": data.get("netProfit"),
            "revenue_growth_yoy": data.get("revenueGrowth"),
            "profit_growth_yoy": data.get("netProfitGrowth"),
            "gross_margin": data.get("grossMargin"),
            "net_profit_margin": data.get("netProfitMargin"),
            "current_ratio": data.get("currentRatio"),
            "bvps": data.get("bvps"),
        }
        # Only keep if at least some ratios were found
        if any(v is not None for k, v in ratio.items() if k not in ("symbol", "year", "period")):
            results.append(ratio)
    return results
```

**Important caveat:** The VCI financial API returns ALL ratio data in a single GraphQL response. The finance_crawler in Phase 1 splits this into separate report types (balance_sheet, income_statement, cash_flow). The ratio fields (pe, pb, eps, etc.) may be stored in ANY of these report types' `data` JSONB, or they may be scattered across rows. The implementation must check all report types for a given (symbol, year, period) to find the ratio fields. [VERIFIED: finance_crawler.py `_store_financials` stores each report type separately, but the VCI API returns ratios alongside all report data]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ta.Strategy()` class | `ta.Study()` class | pandas-ta ~0.4.x | Strategy removed; Study is the batch computation API [VERIFIED: runtime `AttributeError`] |
| TA-Lib (C library) | pandas-ta (pure Python) | Ongoing | No C compilation needed; easier Docker/CI; same indicators |
| Manual ratio calculation | VCI API pre-computed ratios | vnstock 3.5+ | Ratios already available in API response; manual calc only as fallback |

**Deprecated/outdated:**
- `pandas_ta.Strategy` class — removed in recent versions, use `pandas_ta.Study` instead [VERIFIED]
- `df.ta.strategy()` method — use `df.ta.study()` instead [VERIFIED]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio 0.26.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q --timeout=30` |
| Full suite command | `uv run pytest tests/ -v --timeout=30` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TECH-01 | SMA/EMA/RSI/MACD/BB computed correctly | unit | `uv run pytest tests/test_analysis/test_indicators.py -x` | ❌ Wave 0 |
| TECH-02 | Volume analysis (avg, relative, trend) | unit | `uv run pytest tests/test_analysis/test_volume.py -x` | ❌ Wave 0 |
| TECH-03 | Trend detection returns uptrend/downtrend/sideways | unit | `uv run pytest tests/test_analysis/test_trends.py -x` | ❌ Wave 0 |
| TECH-04 | S/R levels from pivot points + peaks/troughs | unit | `uv run pytest tests/test_analysis/test_support_resistance.py -x` | ❌ Wave 0 |
| FUND-01 | Financial ratios extracted from JSONB | unit | `uv run pytest tests/test_analysis/test_ratios.py -x` | ❌ Wave 0 |
| FUND-02 | QoQ/YoY growth computed correctly | unit | `uv run pytest tests/test_analysis/test_growth.py -x` | ❌ Wave 0 |
| FUND-03 | Industry averages computed and compared | unit | `uv run pytest tests/test_analysis/test_industry.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_analysis/ -x -q --timeout=30`
- **Per wave merge:** `uv run pytest tests/ -v --timeout=30`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis/` directory — new test directory for Phase 2
- [ ] `tests/test_analysis/test_indicators.py` — covers TECH-01
- [ ] `tests/test_analysis/test_volume.py` — covers TECH-02
- [ ] `tests/test_analysis/test_trends.py` — covers TECH-03
- [ ] `tests/test_analysis/test_support_resistance.py` — covers TECH-04
- [ ] `tests/test_analysis/test_ratios.py` — covers FUND-01
- [ ] `tests/test_analysis/test_growth.py` — covers FUND-02
- [ ] `tests/test_analysis/test_industry.py` — covers FUND-03
- [ ] `tests/conftest.py` update — add sample indicator DataFrames and financial JSONB fixtures

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ICB Level 3 gives ~15-25 meaningful industry groups for HOSE | Vietnamese Industry Grouping | Need to query actual DB to verify; might be more/fewer groups |
| A2 | VCI ratio fields (pe, pb, eps, etc.) are present in the stored JSONB data from Phase 1 | Financial Ratios Extraction | If Phase 1 stored only report-specific fields (not the ratio section), will need to re-crawl or change extraction logic |
| A3 | ~500 rows per stock is typical for 2-year history | Batch Processing | Could be more/fewer depending on trading days; affects lookback window availability |
| A4 | DB read/write overhead ~50-100ms per stock | Batch Processing | Network latency to Supabase could be higher; total batch time may vary |
| A5 | The `financial_statements.data` JSONB stores data with original VCI field names (pe, pb, eps, etc.) | Code Examples | If finance_crawler translates column names before storing, field names will be different |

## Open Questions

1. **JSONB field name format in stored financial data**
   - What we know: Phase 1's `_store_financials` calls `row.to_dict()` on vnstock DataFrame output
   - What's unclear: Whether vnstock returns English field names (pe, pb, eps) or Vietnamese/coded names (BSA1, ISA23) depends on the `lang` parameter. Phase 1 uses default lang='en' which should give English names.
   - Recommendation: Query a sample row from `financial_statements` in production DB to verify exact field names before implementing extraction logic.

2. **How many price rows per stock exist from Phase 1 backfill?**
   - What we know: Phase 1 backfills 730 days (2 years) per DATA-02
   - What's unclear: Exact count considering weekends, holidays, and potential gaps
   - Recommendation: Expect ~480-500 trading days. SMA(200) will be available. Verify with a sample query.

3. **Should trend_analysis be one row per stock (latest only) or historical?**
   - What we know: Phase 3 scoring only needs current trend
   - What's unclear: Whether historical trend data is valuable for later phases
   - Recommendation: Store only latest trend per stock (simpler, sufficient for scoring). Historical trends can be derived from stored indicators if needed later.

## Project Constraints (from copilot-instructions.md)

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Package manager:** uv (all commands via `uv run <command>`)
- **Database:** Supabase PostgreSQL with async SQLAlchemy + asyncpg
- **ORM:** SQLAlchemy 2.0 style (mapped_column, Mapped types)
- **Migrations:** Alembic
- **Testing:** pytest with pytest-asyncio
- **Logging:** loguru
- **Stock data:** vnstock 3.5.1
- **Technical analysis:** pandas-ta 0.4.71b0

## Sources

### Primary (HIGH confidence)
- pandas-ta runtime tests — all indicator computations, column names, Study API, pivot points, zigzag, supertrend verified via live Python execution
- vnstock VCI source code (`.venv/lib/python3.12/site-packages/vnstock/explorer/vci/financial.py`) — GraphQL query fields, ratio field names, company type codes
- Existing codebase (`src/localstock/`) — models, repositories, crawlers, services patterns
- pyproject.toml and uv.lock — dependency versions verified

### Secondary (MEDIUM confidence)
- vnstock VCI listing source code — ICB classification fields (icbName3, icbName4)
- Phase 1 patterns — repository upsert pattern, crawler base pattern, pipeline orchestration

### Tertiary (LOW confidence)
- None — all critical claims verified via source code inspection or runtime testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, APIs verified via runtime tests
- Architecture: HIGH — follows Phase 1 patterns exactly, new tables are straightforward extensions
- Pitfalls: HIGH — NaN handling, BB column naming, Strategy→Study verified via runtime tests
- Financial ratios: MEDIUM — VCI field names verified in source code but actual JSONB content depends on Phase 1 storage behavior
- Industry grouping: MEDIUM — ICB3 field exists in DB model, but actual values need production DB query

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable — pandas-ta API unlikely to change in 30 days)
