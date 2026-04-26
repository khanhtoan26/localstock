# Stack Research

**Domain:** AI analysis depth additions — candlestick patterns, volume divergence, sector momentum, structured LLM output
**Researched:** 2026-04-25
**Confidence:** HIGH

## Context: What Already Exists (DO NOT RE-RESEARCH)

This is a subsequent milestone. The following are validated and must NOT be changed:

| Existing | Version | Status |
|----------|---------|--------|
| pandas-ta | 0.4.71b0 | Installed; OBV/MFI/CMF/VWAP all confirmed in volume category |
| ollama (Python SDK) | >=0.6 | Structured output via `format=schema` works in production |
| pydantic | >=2.13 | `model_json_schema()` + `model_validate_json()` proven in `ai/client.py` |
| numpy | >=2.0 | Installed; scipy is NOT installed (and not needed) |
| SectorSnapshot DB table | — | Exists with `avg_score_change` column populated by `SectorService` |
| AnalysisReport DB table | — | `content_json` (JSONB) stores full structured report; add nullable columns for SQL access |
| TechnicalIndicator DB table | — | 26 existing columns; add candlestick JSONB + volume divergence fields via Alembic |

---

## Recommended Stack for v1.4

### No New Libraries Required for Core Features

All four v1.4 capabilities use already-installed packages. The research confirmed this after inspecting the installed pandas-ta 0.4.71b0, the existing Ollama client, and the DB schema.

---

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pandas-ta (existing) | 0.4.71b0 | Candlestick patterns (`cdl_doji`, `cdl_inside`), volume signals (`mfi`, `cmf`, `vwap`) | Verified: MFI/CMF/VWAP confirmed in `ta.Category['volume']`; doji/inside confirmed native without TA-Lib |
| pandas + numpy (existing) | >=2.2, >=2.0 | Hammer, Engulfing, Shooting Star via OHLC math; OBV divergence via rolling correlation | 5 key patterns in <50 lines each; OBV already computed, divergence is pure rolling math |
| pydantic (existing) | >=2.13 | Expand `StockReport` model with `price_levels`, `risk_rating`, `catalysts`, `signal_conflicts` | `Literal` types, nested models, `Optional[float]` all render correctly in JSON schema for Ollama `format=` |
| ollama Python SDK (existing) | >=0.6 | Pass expanded `StockReport.model_json_schema()` as `format=` parameter | Proven with 9-field nested schemas; adding 4 fields changes nothing about the mechanism |
| SQLAlchemy + Alembic (existing) | >=2.0 | Add `candlestick_patterns` JSONB and volume divergence fields to `TechnicalIndicator`; add price/risk columns to `AnalysisReport` | One Alembic migration covers all DB additions; no model redesign needed |

---

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas-ta `cdl_doji` | 0.4.71b0 | Native doji detection (body < 10% of H-L range) | Use directly via `df.ta.cdl_doji(append=True)` — no TA-Lib needed |
| pandas-ta `cdl_inside` | 0.4.71b0 | Native inside bar detection | Use directly via `df.ta.cdl_inside(append=True)` |
| pandas-ta `mfi` | 0.4.71b0 | Money Flow Index (14-period) overbought/oversold | Add to `compute_volume_analysis()` — `df.ta.mfi(append=True)` |
| pandas-ta `cmf` | 0.4.71b0 | Chaikin Money Flow — buying vs selling pressure | Add to `compute_volume_analysis()` alongside MFI |
| pydantic `Literal` | stdlib with pydantic >=2.13 | Constrain `risk_rating` to `"high" | "medium" | "low"` | Already imported in pydantic; Literal renders as `enum` in JSON schema which Ollama respects |

---

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Alembic | Generate and apply DB migration for new columns | `uv run alembic revision --autogenerate -m "v1.4_ai_depth_fields"` then `upgrade head` |
| ruff | Lint new analysis code | `uv run ruff check src/` — no config change needed |
| pytest-asyncio | Test new candlestick and volume methods | Existing `asyncio_mode = "auto"` covers new sync methods called from async context |

---

## Feature-by-Feature Integration Plan

### Feature 1: Candlestick Pattern Detection

**Pattern**: Extend `TechnicalAnalyzer` in `analysis/technical.py` with new method `compute_candlestick_patterns(df)`.

**Approach**: Pure pandas math for 3 patterns + pandas-ta native for 2 patterns. No TA-Lib.

```python
# In TechnicalAnalyzer.compute_candlestick_patterns(df) -> dict[str, int]:

# 1. Doji — use pandas-ta native (more precise than manual)
doji = df.ta.cdl_doji()
CDL_DOJI = int(doji.iloc[-1] != 0) if doji is not None else 0

# 2. Inside Bar — use pandas-ta native
inside = df.ta.cdl_inside()
CDL_INSIDE = int(inside.iloc[-1] != 0) if inside is not None else 0

# 3. Hammer — pure pandas (TA-Lib NOT installed)
body = abs(df['close'] - df['open'])
lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
CDL_HAMMER = int((lower_shadow >= 2 * body) & (upper_shadow <= 0.5 * body) & (body > 0)).iloc[-1]

# 4. Bullish/Bearish Engulfing — pure pandas
bull_eng = (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1)) & (df['close'].shift(1) < df['open'].shift(1))
bear_eng = (df['close'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1)) & (df['close'].shift(1) > df['open'].shift(1))
CDL_ENGULFING = 1 if bull_eng.iloc[-1] else (-1 if bear_eng.iloc[-1] else 0)

# 5. Shooting Star — pure pandas (inverse hammer)
CDL_SHOOTING_STAR = int((upper_shadow >= 2 * body) & (lower_shadow <= 0.5 * body) & (body > 0)).iloc[-1]

return {"CDL_DOJI": CDL_DOJI, "CDL_INSIDE": CDL_INSIDE, "CDL_HAMMER": CDL_HAMMER,
        "CDL_ENGULFING": CDL_ENGULFING, "CDL_SHOOTING_STAR": CDL_SHOOTING_STAR}
```

**Storage**: Add `candlestick_patterns` JSON column to `TechnicalIndicator` via Alembic. JSONB avoids adding 5+ boolean columns; allows future pattern additions without migrations. Example stored value: `{"CDL_HAMMER": 1, "CDL_DOJI": 0, "CDL_ENGULFING": -1, "CDL_INSIDE": 0, "CDL_SHOOTING_STAR": 0}`.

**LLM Integration**: In `reports/generator.py`, format active patterns as human-readable text: `"Phát hiện mô hình nến: Hammer (đảo chiều tăng tiềm năng)"` and inject into prompt.

---

### Feature 2: Volume Divergence Analysis

**Pattern**: Extend `TechnicalAnalyzer.compute_volume_analysis()` to add MFI, CMF, and OBV divergence.

```python
# In compute_volume_analysis(), after existing avg_volume_20 / relative_volume:

# MFI (Money Flow Index) — overbought/oversold
mfi_series = df.ta.mfi(length=14)
mfi = float(mfi_series.iloc[-1]) if mfi_series is not None and not pd.isna(mfi_series.iloc[-1]) else None

# CMF (Chaikin Money Flow) — buying vs selling pressure (-1 to +1)
cmf_series = df.ta.cmf(length=20)
cmf = float(cmf_series.iloc[-1]) if cmf_series is not None and not pd.isna(cmf_series.iloc[-1]) else None

# OBV divergence: compare 5-day OBV trend direction vs 5-day price trend direction
if len(df) >= 10:
    obv_series = df.ta.obv()
    price_rising = df['close'].tail(5).mean() > df['close'].tail(10).head(5).mean()
    obv_rising = obv_series.tail(5).mean() > obv_series.tail(10).head(5).mean()
    if price_rising and not obv_rising:
        volume_divergence = "bearish"   # Price up, volume down = suspect rally
    elif not price_rising and obv_rising:
        volume_divergence = "bullish"   # Price down, volume up = accumulation
    else:
        volume_divergence = "none"
else:
    volume_divergence = None
```

**Storage**: Add `mfi_14` (Float), `cmf_20` (Float), `volume_divergence` (String(10)) to `TechnicalIndicator` via same Alembic migration.

**LLM Integration**: Include in prompt as: `"MFI: {mfi:.0f} | CMF: {cmf:.2f} | Phân kỳ khối lượng: {volume_divergence}"`.

---

### Feature 3: Sector Momentum Signals

**Pattern**: Extend `SectorService` with `get_sector_momentum(group_code)` method. Uses existing `SectorSnapshot` data, no new table.

```python
# In SectorService — new method:
async def get_sector_momentum(self, group_code: str, window: int = 5) -> str:
    """Returns 'rising', 'falling', or 'neutral' based on rolling avg_score_change."""
    snapshots = await self.sector_repo.get_recent(group_code, limit=window)
    if len(snapshots) < 2:
        return "neutral"
    changes = [s.avg_score_change for s in snapshots if s.avg_score_change is not None]
    if not changes:
        return "neutral"
    rolling_mean = sum(changes) / len(changes)
    if rolling_mean > 0.5:
        return "rising"
    elif rolling_mean < -0.5:
        return "falling"
    return "neutral"
```

**LLM Integration**: In `ReportService._generate_for_symbol()`, fetch the stock's industry group code, call `get_sector_momentum()`, and pass result to `ReportDataBuilder.build()` as `sector_momentum`. Add to prompt template: `"Động lực ngành: {sector_momentum} (5 phiên gần nhất)"`.

**No new DB table or migration needed** — reads from existing `sector_snapshots`.

---

### Feature 4: Structured LLM Output (Price Levels, Risk Rating, Catalysts)

**Pattern**: Expand `StockReport` Pydantic model in `ai/client.py`.

```python
from typing import Literal
from pydantic import BaseModel, Field

class PriceLevels(BaseModel):
    entry_price: float | None = Field(None, description="Giá vào lệnh gợi ý (VND)")
    exit_price: float | None = Field(None, description="Giá chốt lời mục tiêu (VND)")
    stop_loss: float | None = Field(None, description="Giá cắt lỗ (VND)")
    rationale: str = Field(description="Cơ sở tính toán các mức giá từ S/R và ATR")

class StockReport(BaseModel):
    # --- Existing 9 fields unchanged ---
    summary: str
    technical_analysis: str
    fundamental_analysis: str
    sentiment_analysis: str
    macro_impact: str
    long_term_suggestion: str
    swing_trade_suggestion: str
    recommendation: str
    confidence: str
    # --- 4 new fields for v1.4 ---
    price_levels: PriceLevels = Field(description="Các mức giá giao dịch cụ thể")
    risk_rating: Literal["high", "medium", "low"] = Field(description="Mức độ rủi ro tổng thể")
    risk_reasoning: str = Field(description="Lý do đánh giá rủi ro (D/E, biến động, tin tức)")
    catalysts: list[str] = Field(description="Yếu tố xúc tác tuần này, tối đa 3 mục")
    signal_conflicts: str = Field(description="Giải thích mâu thuẫn giữa tín hiệu kỹ thuật và cơ bản nếu có, hoặc 'Không có mâu thuẫn'")
```

**Context window**: Adding 4 new output fields increases LLM output by ~200-400 tokens. Current `num_ctx: 4096` covers it. No change to `options` needed.

**DB storage**: `AnalysisReport.content_json` (JSONB) stores the full `StockReport` dict automatically — new fields are included without migration. Add `entry_price` (Float, nullable), `stop_loss` (Float, nullable), `risk_rating` (String(10), nullable) as direct columns for SQL-queryable fast access (add to same Alembic migration).

**Prompt changes**: Update `REPORT_SYSTEM_PROMPT` to explicitly instruct the LLM to compute price levels from support/resistance data (which is already passed in the prompt via `nearest_support`, `nearest_resistance`, `pivot_point`).

---

## Installation

No new Python packages are needed. All dependencies are in `apps/prometheus/pyproject.toml` already.

```bash
# Verify volume indicators are available in installed pandas-ta 0.4.71b0
uv run python -c "import pandas_ta as ta; print([x for x in ta.Category.get('volume', []) if x in ['mfi', 'cmf', 'vwap', 'obv']])"
# Expected: ['cmf', 'mfi', 'obv', 'vwap']

# Verify native candlestick pattern functions
uv run python -c "import pandas_ta as ta; print([x for x in dir(ta) if x.startswith('cdl')])"
# Expected: ['cdl', 'cdl_doji', 'cdl_inside', 'cdl_pattern', 'cdl_z']

# Generate Alembic migration after model changes (run from workspace root)
cd apps/prometheus && uv run alembic revision --autogenerate -m "v1.4_ai_depth_fields"
uv run alembic upgrade head
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| TA-Lib (C library + Python wrapper) | Requires `sudo dpkg -i ta-lib_0.6.4_amd64.deb` on this WSL2/Linux system — adds a C binary dependency and system-level install step for 5 patterns solvable with pandas math | Pure pandas OHLC math for hammer/engulfing/shooting_star; pandas-ta native for doji/inside |
| scipy | Not installed; would only replace the manual peak detection in `trend.py` which already works and has tests | Keep existing `find_peaks_manual` / `find_troughs_manual` in `trend.py` |
| langchain / llm orchestration frameworks | Massive transitive dependency footprint (50+ packages) for a single-model, single-task usage | Direct `OllamaClient.generate_report()` already handles retries, health checks, structured output |
| vector database (chromadb, qdrant, pgvector) | No RAG pattern needed; reports are per-stock daily with fixed context | PostgreSQL JSONB for structured report storage |
| OpenAI/Anthropic API SDK | Explicitly out of scope (paid API, hardware constraint is RTX 3060 local-only) | Ollama local model |
| Second LLM model (smaller/faster) | RTX 3060 12GB VRAM is at capacity with qwen2.5:14b; model switching adds complexity | Improve prompts for existing model — better prompts yield better results than model changes |
| Any new frontend library | v1.4 is backend-only (new signals + new report fields); frontend will render new fields from existing `content_json` | Use existing `content_json` parsing in frontend |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Pure pandas candlestick math (5 patterns) | TA-Lib (60 patterns) | If v2 requires 15+ patterns AND the team accepts a C build dependency |
| JSONB for candlestick storage | Individual Boolean columns per pattern | If SQL filtering `WHERE CDL_HAMMER = 1 AND CDL_DOJI = 0` becomes a query need |
| Expand `StockReport` Pydantic (one LLM call) | Separate LLM call for price levels only | If price-level reasoning needs a fresh context window not shared with narrative |
| Sector momentum from existing `SectorSnapshot` | New crawl for sector index prices | If sector ETF price momentum (not score momentum) is needed for accuracy |
| Rolling `avg_score_change` mean for momentum | MACD-style signal line on score series | If false signal suppression becomes important at v2 level |

---

## Version Compatibility

| Package | Current | Compatibility Note |
|---------|---------|-------------------|
| pandas-ta | 0.4.71b0 | `mfi()`, `cmf()`, `cdl_doji()`, `cdl_inside()` confirmed available in this exact version (verified via `ta.Category` and `dir(ta)`) |
| ollama | >=0.6 | Nested Pydantic models with `Literal` types work as `format=model_json_schema()` — confirmed in Context7 docs with vision/structured output examples |
| pydantic | >=2.13 | `Literal["high", "medium", "low"]` renders as `{"enum": ["high", "medium", "low"]}` in JSON schema — Ollama respects enum constraints |
| SQLAlchemy | >=2.0 | `JSON` column type (used for `content_json`) already in production; adding more `Float`/`String` nullable columns is standard |

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| pandas-ta 0.4.71b0 `mfi`, `cmf`, `vwap`, `obv` in volume category | Direct: `uv run python -c "import pandas_ta as ta; print(ta.Category)"` | HIGH |
| `cdl_doji`, `cdl_inside` native (no TA-Lib); `cdl_pattern` requires TA-Lib | Direct: inspected `cdl_pattern` source via `inspect.getsource`; confirmed `if Imports["talib"]` guard | HIGH |
| TA-Lib requires `.deb` system package on Linux | Context7 `/ta-lib/ta-lib` docs — `sudo dpkg -i ta-lib_0.6.4_amd64.deb` for Debian | HIGH |
| TA-Lib NOT installed on this system | Direct: `uv run python -c "import talib"` → ImportError | HIGH |
| Ollama nested Pydantic schemas with `Literal` work as `format=` | Context7 `/ollama/ollama-python` + `/llmstxt/ollama_llms_txt` structured output docs | HIGH |
| `SectorSnapshot` has `avg_score_change` column | Direct: `db/models.py` line 439, confirmed nullable Float | HIGH |
| `AnalysisReport.content_json` is JSONB (stores arbitrary dict) | Direct: `db/models.py` line 387 — `Mapped[dict] = mapped_column(JSON)` | HIGH |
| OBV already computed in `TechnicalIndicator` | Direct: `db/models.py` line 160, `analysis/technical.py` line 183 | HIGH |

---
*Stack research for: LocalStock v1.4 AI Analysis Depth*
*Researched: 2026-04-25*
