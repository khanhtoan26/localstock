# Phase 4: AI Reports, Macro Context & T+3 Awareness - Research

**Researched:** 2026-04-16
**Domain:** LLM report generation, Vietnamese macro-economic data sourcing, T+3 settlement logic
**Confidence:** HIGH

## Summary

Phase 4 builds three interconnected capabilities on top of the existing Phase 1-3 infrastructure: (1) LLM-generated Vietnamese narrative reports that explain WHY stocks score high/low, (2) macro-economic data collection and sector impact analysis, and (3) T+3-aware swing trade predictions. The existing OllamaClient, scoring engine, and data models provide strong foundations to extend.

The primary challenge is macro data sourcing — SBV and GSO have no clean APIs, so a pragmatic semi-structured approach (scraping exchange rates, manual/config-based entry for quarterly CPI/GDP/interest rates) is necessary. Report generation reuses the existing Ollama infrastructure but requires a new `generate_report()` method with a much richer prompt template than the current sentiment classifier. The T+3 logic synthesizes existing technical signals (trend, RSI momentum, MACD, support/resistance) into a short-term outlook rather than attempting price prediction.

**Primary recommendation:** Extend OllamaClient with a `generate_report()` method that takes all structured data as input and produces structured Vietnamese narrative output. Use a rules-based macro-to-sector impact mapping (not LLM) for consistent, debuggable macro scoring. Limit LLM report generation to top-ranked stocks (reuse funnel pattern from Phase 3).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
None — all implementation decisions are at agent's discretion.

### Agent's Discretion
- **D-01:** Agent tự quyết định cấu trúc và độ dài báo cáo AI tiếng Việt.
- **D-02:** Agent tự chọn nguồn dữ liệu vĩ mô (SBV, GSO...) và cách thu thập.
- **D-03:** Agent tự thiết kế cách liên kết macro → ngành → cổ phiếu.
- **D-04:** Agent tự implement logic dự đoán 3 ngày cho T+3 và cách cảnh báo.
- **D-05:** Agent tự phân biệt giữa gợi ý dài hạn vs lướt sóng trong báo cáo.

### Carrying Forward
- Supabase database (Phase 1)
- LLM model qua Ollama (Phase 3 — sẽ reuse model đã chọn)
- Composite score + grade letter A/B/C/D/F (Phase 3)
- JSON structured output (Phase 3)

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPT-01 | LLM local (Ollama) tổng hợp phân tích đa chiều thành báo cáo tiếng Việt cho từng mã, giải thích TẠI SAO điểm cao/thấp | Extend OllamaClient with `generate_report()`, Pydantic-validated structured report output, data-injection prompt pattern |
| REPT-02 | Báo cáo bao gồm: tín hiệu kỹ thuật, đánh giá cơ bản, sentiment tin tức, ảnh hưởng vĩ mô, và khuyến nghị tổng hợp | Multi-section report template with all 4 dimensions + recommendation, structured as StockReport Pydantic model |
| MACR-01 | Agent thu thập dữ liệu vĩ mô: lãi suất (SBV), tỷ giá USD/VND, CPI, GDP | MacroIndicator DB model + MacroCrawler for exchange rates (public sources) + manual/config entry for quarterly data |
| MACR-02 | Agent phân tích tác động vĩ mô đến từng ngành/mã cổ phiếu | Rules-based MACRO_SECTOR_IMPACT mapping (20 industry groups × 4 macro indicators) + normalize_macro_score() |
| T3-01 | Khi gợi ý mã lướt sóng, agent dự đoán xu hướng ít nhất 3 ngày tới | 3-day trend projection from existing signals (RSI momentum, MACD histogram direction, trend strength, distance to S/R) |
| T3-02 | Agent phân biệt rõ ràng giữa gợi ý đầu tư dài hạn và gợi ý lướt sóng, kèm cảnh báo T+3 | Report template with separate sections: "Đầu tư dài hạn" vs "Lướt sóng", T+3 warning text injected automatically |

</phase_requirements>

## Project Constraints (from copilot-instructions.md)

No `copilot-instructions.md` found. Following conventions established in prior phases:
- Python 3.12+, FastAPI, SQLAlchemy 2.0 async, PostgreSQL (Supabase) [VERIFIED: pyproject.toml]
- Ollama with Qwen2.5 14B Q4_K_M for LLM [VERIFIED: config.py]
- Session-based service pattern with `run_full() -> dict` [VERIFIED: existing services]
- Repository pattern with `pg_insert().on_conflict_do_update()` [VERIFIED: existing repos]
- Flat dict API responses (no Pydantic response models) [VERIFIED: existing routes]
- pytest with `asyncio_mode = "auto"`, `timeout = 30` [VERIFIED: pyproject.toml]

## Standard Stack

### Core (No New Dependencies)

This phase requires **zero new Python packages**. Everything is built on existing dependencies.

| Library | Version | Purpose | Already Installed |
|---------|---------|---------|-------------------|
| ollama | >=0.6,<1.0 | LLM report generation (extend existing OllamaClient) | ✅ Yes |
| pydantic | >=2.13,<3.0 | Structured report output schema (StockReport model) | ✅ Yes |
| sqlalchemy | >=2.0,<3.0 | New DB models (MacroIndicator, AnalysisReport) | ✅ Yes |
| alembic | >=1.18,<2.0 | Migration for new tables | ✅ Yes |
| httpx | >=0.28,<1.0 | Macro data scraping (exchange rates) | ✅ Yes |
| beautifulsoup4 | >=4.14,<5.0 | Parsing macro data from web sources | ✅ Yes |
| loguru | >=0.7,<1.0 | Logging throughout new modules | ✅ Yes |
| tenacity | >=9.0,<10.0 | Retry logic for LLM calls | ✅ Yes |

[VERIFIED: pyproject.toml — all packages already in dependencies]

### Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output | Manual JSON parsing from free text | Ollama `format` parameter with Pydantic JSON schema | Already proven in SentimentResult; ensures valid output structure |
| Database migrations | Manual ALTER TABLE | Alembic `alembic revision --autogenerate` | Standard practice from Phases 1-3 |
| Retry logic on LLM calls | Custom retry loops | tenacity `@retry` decorator | Already used in OllamaClient.classify_sentiment |
| Macro-to-sector impact mapping | LLM for every macro evaluation | Rules-based dict mapping | Deterministic, debuggable, zero latency, no VRAM usage |
| Price prediction for T+3 | ML model or neural network | Signal aggregation from existing indicators | Anti-feature per FEATURES.md — "No specific price targets" |

## Architecture Patterns

### Recommended Project Structure (New Files)

```
src/localstock/
├── ai/
│   ├── client.py           # MODIFY: add generate_report() method
│   └── prompts.py          # MODIFY: add REPORT_SYSTEM_PROMPT, REPORT_USER_TEMPLATE
├── macro/                  # NEW: macro data module
│   ├── __init__.py
│   ├── crawler.py          # MacroCrawler — fetches exchange rate, manual macro data
│   ├── impact.py           # MACRO_SECTOR_IMPACT rules mapping
│   └── scorer.py           # normalize_macro_score() — macro dimension scorer
├── reports/                # NEW: report generation module
│   ├── __init__.py
│   ├── generator.py        # ReportGenerator — orchestrates LLM report creation
│   └── t3.py               # T+3 trend projection logic
├── db/
│   ├── models.py           # MODIFY: add MacroIndicator, AnalysisReport models
│   └── repositories/
│       ├── macro_repo.py   # NEW: MacroRepository
│       └── report_repo.py  # NEW: ReportRepository
├── services/
│   └── report_service.py   # NEW: ReportService — top-level orchestrator
├── scoring/
│   ├── config.py           # MODIFY: update default macro weight to 0.20
│   └── normalizer.py       # MODIFY: add normalize_macro_score()
├── api/routes/
│   ├── reports.py          # NEW: report API endpoints
│   └── macro.py            # NEW: macro data API endpoints
└── config.py               # MODIFY: add macro-related settings
```

### Pattern 1: Data-Injection Report Generation (Pitfall 3 Prevention)

**What:** Never ask the LLM to recall financial facts. Always inject ALL data into the prompt, then ask LLM to synthesize a narrative.

**When to use:** Every report generation call.

**Example:**
```python
# Source: Existing OllamaClient pattern in src/localstock/ai/client.py
class StockReport(BaseModel):
    """Structured report output from LLM."""
    summary: str = Field(description="Tóm tắt 2-3 câu")
    technical_analysis: str = Field(description="Phân tích kỹ thuật")
    fundamental_analysis: str = Field(description="Đánh giá cơ bản")
    sentiment_analysis: str = Field(description="Tâm lý thị trường")
    macro_impact: str = Field(description="Ảnh hưởng vĩ mô")
    long_term_suggestion: str = Field(description="Gợi ý đầu tư dài hạn")
    swing_trade_suggestion: str = Field(description="Gợi ý lướt sóng kèm cảnh báo T+3")
    recommendation: str = Field(description="Khuyến nghị tổng hợp: Mua mạnh/Mua/Nắm giữ/Bán/Bán mạnh")
    confidence: str = Field(description="Độ tin cậy: Cao/Trung bình/Thấp")

# Data injection — LLM only synthesizes, never recalls
user_prompt = f"""
Mã cổ phiếu: {symbol} — {company_name} ({industry_vi})

📊 ĐIỂM TỔNG HỢP: {total_score}/100 (Hạng {grade})
- Kỹ thuật: {tech_score}/100
- Cơ bản: {fund_score}/100
- Sentiment: {sent_score}/100
- Vĩ mô: {macro_score}/100

📈 TÍN HIỆU KỸ THUẬT:
- Xu hướng: {trend_direction} (ADX={trend_strength})
- RSI(14): {rsi} | MACD Histogram: {macd_h}
- Giá: {close:,.0f} VND | MA20: {sma_20:,.0f} | MA50: {sma_50:,.0f} | MA200: {sma_200:,.0f}
- Hỗ trợ: {support:,.0f} | Kháng cự: {resistance:,.0f}
- Khối lượng tương đối: {rel_vol:.1f}x

💰 CHỈ SỐ CƠ BẢN:
- P/E: {pe:.1f} (Ngành TB: {ind_pe:.1f}) | P/B: {pb:.1f}
- ROE: {roe:.1f}% | ROA: {roa:.1f}% | D/E: {de:.2f}
- Tăng trưởng LN YoY: {profit_yoy:+.1f}% | DT YoY: {revenue_yoy:+.1f}%

📰 TIN TỨC (Sentiment: {sent_label}, Score: {sent_avg:.2f}):
{news_summary}

🌐 BỐI CẢNH VĨ MÔ:
- Lãi suất SBV: {interest_rate}% ({interest_trend})
- Tỷ giá USD/VND: {exchange_rate:,.0f} ({fx_trend})
- CPI: {cpi}% YoY | GDP: {gdp}% YoY
- Tác động vĩ mô lên ngành {industry_vi}: {macro_impact_text}

⏰ T+3: Dự đoán xu hướng 3 ngày tới: {t3_prediction}
"""
```

### Pattern 2: Rules-Based Macro Impact Mapping (MACR-02)

**What:** Static mapping of macro indicators to sector impact, avoiding LLM for deterministic logic.

**When to use:** Computing macro_score dimension for composite scoring.

**Example:**
```python
# Macro → Sector impact rules (deterministic, no LLM needed)
MACRO_SECTOR_IMPACT: dict[str, dict[str, float]] = {
    # interest_rate_rising → sector impact multiplier
    "interest_rate_rising": {
        "BANKING": 0.7,      # Positive: wider NIM
        "REAL_ESTATE": -0.8, # Negative: higher borrowing costs
        "SECURITIES": -0.6,  # Negative: lower trading volume
        "CONSTRUCTION": -0.5,
        "RETAIL": -0.3,
        "STEEL": -0.4,
        # ... all 20 sectors
    },
    "vnd_weakening": {
        "SEAFOOD": 0.6,      # Positive: export competitive
        "TEXTILE": 0.5,      # Positive: export competitive
        "OIL_GAS": -0.4,     # Negative: import costs
        "PHARMA": -0.3,      # Negative: import raw materials
        # ...
    },
    "cpi_rising": {
        "FOOD_BEVERAGE": 0.3, # Can pass through costs
        "RETAIL": -0.4,       # Consumer spending decreases
        "REAL_ESTATE": -0.5,  # Demand drops
        # ...
    },
    "gdp_growing": {
        # Generally positive for all, vary by magnitude
        "BANKING": 0.5,
        "REAL_ESTATE": 0.6,
        "CONSTRUCTION": 0.7,
        # ...
    },
}
```

### Pattern 3: T+3 Trend Projection (T3-01)

**What:** Aggregate existing technical signals to produce a short-term outlook, NOT a price prediction.

**When to use:** Swing trade suggestions in reports.

**Example:**
```python
def predict_3day_trend(indicator_data: dict) -> dict:
    """Project 3-day trend from existing technical signals.

    Returns dict with:
      - direction: "bullish" | "bearish" | "neutral"
      - confidence: "high" | "medium" | "low"
      - reasons: list of Vietnamese explanation strings
      - t3_warning: T+3 settlement warning text
    """
    signals = 0
    reasons = []

    # RSI momentum
    rsi = indicator_data.get("rsi_14")
    if rsi is not None:
        if 30 < rsi < 50:  # Recovering from oversold
            signals += 1
            reasons.append(f"RSI({rsi:.0f}) đang hồi phục từ vùng quá bán")
        elif rsi > 70:  # Overbought, likely correction
            signals -= 1
            reasons.append(f"RSI({rsi:.0f}) ở vùng quá mua, có thể điều chỉnh")

    # MACD histogram direction
    macd_h = indicator_data.get("macd_histogram")
    if macd_h is not None:
        if macd_h > 0:
            signals += 1
            reasons.append("MACD histogram dương, đà tăng")
        else:
            signals -= 1
            reasons.append("MACD histogram âm, đà giảm")

    # Trend + strength
    trend = indicator_data.get("trend_direction")
    strength = indicator_data.get("trend_strength", 0)
    if trend == "uptrend" and strength > 25:
        signals += 1
        reasons.append(f"Xu hướng tăng rõ ràng (ADX={strength:.0f})")

    # Distance to support/resistance
    close = indicator_data.get("close", 0)
    support = indicator_data.get("nearest_support")
    resistance = indicator_data.get("nearest_resistance")
    if support and resistance and close:
        upside = (resistance - close) / close
        downside = (close - support) / close
        if upside > downside * 2:
            signals += 1
            reasons.append("Khoảng cách đến kháng cự lớn hơn hỗ trợ")

    # Determine direction and confidence
    if signals >= 2:
        direction, confidence = "bullish", "high" if signals >= 3 else "medium"
    elif signals <= -2:
        direction, confidence = "bearish", "high" if signals <= -3 else "medium"
    else:
        direction, confidence = "neutral", "low"

    return {
        "direction": direction,
        "confidence": confidence,
        "reasons": reasons,
        "t3_warning": (
            "⚠️ CẢNH BÁO T+3: Cổ phiếu mua hôm nay chỉ có thể bán "
            "sau 3 ngày làm việc. Hãy đảm bảo xu hướng đủ mạnh để "
            "giữ vị thế trong ít nhất 3 phiên giao dịch."
        ),
    }
```

### Pattern 4: Service Orchestration (Follows Existing Pattern)

**What:** ReportService follows the session-based `__init__`, `run_full() -> dict` pattern established in ScoringService and SentimentService.

**When to use:** Report generation orchestration.

```python
class ReportService:
    """Orchestrates report generation for top-ranked stocks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.score_repo = ScoreRepository(session)
        self.report_repo = ReportRepository(session)
        # ... other repos
        self.ollama = OllamaClient()

    async def run_full(self, top_n: int = 20) -> dict:
        """Generate reports for top N stocks."""
        # 1. Get top-ranked stocks from ScoringService
        # 2. For each: gather all dimension data
        # 3. Get macro context
        # 4. Compute T+3 prediction
        # 5. Build prompt with all data injected
        # 6. Call LLM to generate report
        # 7. Store report in DB
        ...
```

### Anti-Patterns to Avoid

- **Asking LLM to recall financial facts:** Every number in the report must come from injected data, not LLM memory. [VERIFIED: Pitfall 3 from PITFALLS.md]
- **Using LLM for macro impact scoring:** Deterministic rules are faster, more consistent, and debuggable. Use LLM only for the narrative explanation.
- **Price target predictions:** Explicitly flagged as anti-feature in FEATURES.md. Use directional trend (bullish/bearish/neutral) instead.
- **Long prompts exceeding context:** Keep total prompt under 3000 tokens. Summarize data, don't dump raw time series. Qwen2.5 14B at Q4_K_M has ~4K usable context with 12GB VRAM. [VERIFIED: Pitfall 7 from PITFALLS.md]
- **Generating reports for all 400 stocks:** Use existing funnel pattern — reports only for top-ranked stocks to manage VRAM/time budget.

## New Database Models

### MacroIndicator

```python
class MacroIndicator(Base):
    """Macro-economic indicator data points."""
    __tablename__ = "macro_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_type: Mapped[str] = mapped_column(String(30))
    # 'interest_rate', 'exchange_rate_usd_vnd', 'cpi', 'gdp'
    value: Mapped[float] = mapped_column(Float)
    period: Mapped[str] = mapped_column(String(20))    # '2026-Q1', '2026-04', 'latest'
    source: Mapped[str] = mapped_column(String(50))     # 'sbv', 'gso', 'vcb', 'manual'
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 'rising', 'falling', 'stable'
    recorded_at: Mapped[date] = mapped_column(Date)     # date of data point
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("indicator_type", "period", name="uq_macro_indicator"),
    )
```

### AnalysisReport

```python
class AnalysisReport(Base):
    """LLM-generated analysis reports per stock."""
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    report_type: Mapped[str] = mapped_column(String(20))  # 'full', 'swing', 'long_term'
    content_json: Mapped[dict] = mapped_column(JSON)       # Full StockReport as JSON
    summary: Mapped[str] = mapped_column(Text)             # 2-3 sentence summary
    recommendation: Mapped[str] = mapped_column(String(20))
    # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'
    t3_prediction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 'bullish', 'bearish', 'neutral'
    model_used: Mapped[str] = mapped_column(String(50))
    total_score: Mapped[float] = mapped_column(Float)      # snapshot at report time
    grade: Mapped[str] = mapped_column(String(2))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", "report_type", name="uq_analysis_report"),
    )
```

## Macro Data Sourcing Strategy (D-02)

### Recommended Approach: Hybrid (Auto + Manual)

| Indicator | Source | Method | Update Frequency | Confidence |
|-----------|--------|--------|-------------------|------------|
| USD/VND Exchange Rate | Vietcombank (vcb.com.vn) | HTTP scrape VCB exchange rate page | Daily (after market close) | MEDIUM |
| SBV Interest Rate | Manual entry / config | Admin enters via `POST /api/macro` when SBV announces | When changed (~quarterly) | HIGH |
| CPI | GSO (gso.gov.vn) | Manual entry from monthly GSO press release | Monthly | HIGH |
| GDP | GSO (gso.gov.vn) | Manual entry from quarterly GSO release | Quarterly | HIGH |

**Rationale:** [ASSUMED — based on research warning about SBV/GSO having no clean API]
- SBV publishes interest rate decisions as press releases, not API data. Changes are infrequent (a few times per year). Manual entry is more reliable than fragile scraping.
- GSO publishes CPI monthly and GDP quarterly as PDF reports. No machine-readable API exists.
- Exchange rate changes daily and can be scraped reliably from major banks (VCB, BIDV) that publish rates on their websites.
- The `POST /api/macro` endpoint allows updating macro data via API call, which can later be hooked into automation (Phase 5).

### Exchange Rate Scraping Pattern

```python
class MacroCrawler:
    """Fetches macro-economic data from public Vietnamese sources."""

    async def fetch_exchange_rate(self) -> dict:
        """Fetch USD/VND rate from Vietcombank."""
        # VCB publishes exchange rates at:
        # https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx
        # Returns XML with buy/sell rates for all currencies
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            resp = await client.get(VCB_EXCHANGE_URL, timeout=15)
            # Parse XML, extract USD buy/sell rates
            ...
        return {"value": rate, "source": "vcb", "trend": self._compute_trend(...)}
```

### Manual Entry Flow

For interest rates, CPI, GDP — the user/admin POSTs to:
```
POST /api/macro
{
  "indicator_type": "interest_rate",
  "value": 4.5,
  "period": "2026-04",
  "source": "sbv"
}
```
This is pragmatic for a personal tool: macro fundamentals change slowly, and scraping SBV/GSO sites would be fragile and complex for data that changes monthly/quarterly.

## Macro-to-Sector Impact Scoring (MACR-02)

### Design: Rules-Based, Not LLM

The macro-to-sector impact is **deterministic domain knowledge**, not something that needs LLM inference. Encode it as a static mapping.

**Macro conditions to detect:**
1. Interest rate: rising / stable / falling (compare current vs previous period)
2. Exchange rate: VND weakening / stable / strengthening
3. CPI: rising / stable / falling
4. GDP: accelerating / stable / decelerating

**For each condition → sector impact multiplier (-1.0 to +1.0):**

| Condition | BANKING | REAL_ESTATE | STEEL | SEAFOOD | TEXTILE | OIL_GAS | RETAIL | CONSTRUCTION | TECH | ENERGY |
|-----------|---------|-------------|-------|---------|---------|---------|--------|--------------|------|--------|
| Rate ↑ | +0.7 | -0.8 | -0.4 | -0.2 | -0.3 | -0.2 | -0.3 | -0.5 | -0.1 | 0.0 |
| Rate ↓ | -0.3 | +0.8 | +0.3 | +0.2 | +0.2 | +0.2 | +0.3 | +0.5 | +0.1 | 0.0 |
| VND ↓ | +0.2 | -0.2 | -0.3 | +0.6 | +0.5 | -0.4 | -0.3 | -0.2 | +0.2 | -0.3 |
| VND ↑ | -0.2 | +0.2 | +0.3 | -0.4 | -0.3 | +0.3 | +0.3 | +0.2 | -0.1 | +0.2 |
| CPI ↑ | +0.3 | -0.5 | -0.2 | +0.1 | -0.2 | +0.2 | -0.4 | -0.3 | 0.0 | +0.1 |
| GDP ↑ | +0.5 | +0.6 | +0.5 | +0.3 | +0.3 | +0.3 | +0.5 | +0.7 | +0.4 | +0.3 |

[ASSUMED — domain knowledge about Vietnamese sector sensitivity to macro factors. These weights are reasonable starting points but should be calibrated over time.]

### Macro Score Normalization

```python
def normalize_macro_score(
    sector_code: str,
    macro_conditions: dict[str, str],  # e.g. {"interest_rate": "rising", "exchange_rate": "stable"}
) -> float:
    """Compute macro dimension score (0-100) for a stock's sector.

    50 = neutral (no macro impact or no data)
    >50 = macro conditions favorable for this sector
    <50 = macro conditions unfavorable
    """
    # For each active macro condition:
    #   1. Look up sector impact multiplier
    #   2. Scale from (-1, +1) to (0, 100)
    #   3. Average across all available macro indicators
    ...
```

## T+3 Settlement Logic (T3-01, T3-02)

### What T+3 Means

On HOSE, when you buy a stock today (T+0), you cannot sell it until T+3 (3 business days later). This means swing traders must predict that the stock will NOT decline over those 3 days, because they're locked in. [ASSUMED — requirements explicitly state T+3; the actual HOSE rule may be T+2 as of recent regulatory changes, but we follow the user's specification]

### T+3 Prediction Components

Use existing technical data (no new indicators needed):

1. **RSI Momentum** — Is RSI in a zone likely to continue? (30-50 = recovery potential, 70+ = overbought risk)
2. **MACD Histogram** — Is momentum increasing or decreasing?
3. **Trend Direction + Strength** — Is there a clear trend with ADX > 25?
4. **Price vs Support/Resistance** — How much room to run vs risk of hitting support?
5. **Volume Trend** — Is volume confirming the move?

### Long-term vs Swing Trade Distinction (T3-02)

| Aspect | Long-term (Đầu tư dài hạn) | Swing Trade (Lướt sóng) |
|--------|----------------------------|-------------------------|
| Time horizon | Months to years | Days to weeks |
| Key signals | Fundamentals (P/E, ROE, growth), macro context | Technical (RSI, MACD, S/R), T+3 prediction |
| Grade threshold | Grade A-B recommended | Grade A-C with bullish T+3 |
| Risk warning | Standard investment disclaimer | **T+3 settlement warning** + 3-day prediction confidence |
| Data emphasis | Fundamental score, industry comparison | Technical score, momentum indicators |

## Report Structure (D-01)

### Recommended Report Sections

```
📊 BÁO CÁO PHÂN TÍCH: {SYMBOL} - {COMPANY_NAME}
Ngày: {date} | Điểm: {total_score}/100 | Hạng: {grade}
═══════════════════════════════════════════════════

📝 TÓM TẮT (2-3 câu)
[LLM synthesizes key findings]

📈 PHÂN TÍCH KỸ THUẬT
[LLM explains technical signals in Vietnamese]

💰 ĐÁNH GIÁ CƠ BẢN
[LLM interprets fundamental ratios vs industry]

📰 TÂM LÝ THỊ TRƯỜNG
[LLM summarizes news sentiment]

🌐 ẢNH HƯỞNG VĨ MÔ
[LLM links macro conditions to this stock's sector]

📌 GỢI Ý ĐẦU TƯ DÀI HẠN
[Long-term recommendation based on fundamentals + macro]

⚡ GỢI Ý LƯỚT SÓNG
[Swing trade based on technicals + T+3 prediction]
⚠️ CẢNH BÁO T+3: Mua hôm nay → bán được từ ngày {t3_sell_date}

🎯 KHUYẾN NGHỊ TỔNG HỢP
[Overall: Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh]
Độ tin cậy: [Cao / Trung bình / Thấp]
```

### Report Length Budget

- Target: 500-800 Vietnamese words per report (fits ~800-1200 tokens output)
- Total prompt + response should stay under 4000 tokens
- Prompt data injection: ~1500-2000 tokens
- LLM response: ~1200-1500 tokens
- Leaves headroom within Qwen2.5 14B's effective context

[VERIFIED: Pitfall 7 from PITFALLS.md — "Keep prompts under 2K tokens"]

## Scoring Weight Activation

Phase 4 activates the macro dimension in composite scoring:

### Current (Phase 3)
```
tech=0.35, fund=0.35, sent=0.30, macro=0.0
Redistribution: When macro=0, weights normalize to 35/35/30 → 0.39/0.39/0.33
```

### Phase 4 Target
```
tech=0.30, fund=0.30, sent=0.20, macro=0.20
```

**Implementation:** Update `Settings.scoring_weight_macro` default from `0.0` to `0.20` and adjust other defaults proportionally. The dynamic weight redistribution in `compute_composite()` already handles missing dimensions gracefully. [VERIFIED: scoring/engine.py line 54-59]

## Common Pitfalls

### Pitfall 1: LLM Hallucinating Numbers in Reports
**What goes wrong:** LLM generates plausible but fabricated financial numbers not present in the injected data.
**Why it happens:** Qwen2.5 14B pattern-matches financial language from training data. Vietnamese stocks are underrepresented.
**How to avoid:** Inject ALL data into prompt. Use structured output (Pydantic schema) to constrain format. Post-validate by checking if report mentions numbers not in the input data.
**Warning signs:** Two runs produce different numbers; report contains metrics not in the prompt.
[VERIFIED: Pitfall 3 from PITFALLS.md]

### Pitfall 2: Prompt Context Overflow on 12GB VRAM
**What goes wrong:** Rich data injection exceeds context window, causing truncation and garbage output.
**Why it happens:** Price history + ratios + news + macro easily exceeds 4K tokens per stock.
**How to avoid:** Summarize data into key metrics before injection. No raw time series. Budget: ~2000 tokens input, ~1500 tokens output. Use `num_ctx: 4096` in Ollama options.
**Warning signs:** LLM responses become incoherent, repetitive, or cut off mid-sentence.
[VERIFIED: Pitfall 7 from PITFALLS.md]

### Pitfall 3: Fragile Macro Data Scraping
**What goes wrong:** Exchange rate scraping breaks when VCB changes their webpage layout.
**Why it happens:** Vietnamese bank websites don't have stable APIs.
**How to avoid:** VCB publishes an XML feed for exchange rates (more stable than HTML). Wrap scraping in try/except with fallback to last known value. Manual entry as backup for all macro indicators.
**Warning signs:** MacroCrawler returns None consistently; exchange rates not updating.
[VERIFIED: PITFALLS.md warning about ephemeral data sources]

### Pitfall 4: Report Generation Time Budget Exceeded
**What goes wrong:** Generating reports for 50 stocks × 15 seconds = 12.5 minutes; user gives up.
**Why it happens:** Each LLM call takes 10-20 seconds on RTX 3060 with 14B model.
**How to avoid:** Generate reports only for top 20 stocks (not all 400). Use `keep_alive="30m"` to avoid model reload. Sequential processing with progress logging.
**Warning signs:** Total report generation exceeds 10 minutes.
[VERIFIED: Pitfall 7 from PITFALLS.md — "Tier your analysis"]

### Pitfall 5: Macro Score Dominating Rankings
**What goes wrong:** All stocks in the same sector get the same macro score, flattening differentiation.
**Why it happens:** Macro affects sectors uniformly — all BANKING stocks get the same macro boost/penalty.
**How to avoid:** Macro weight should be modest (20%). The macro score adds context, not discrimination. Individual stock differentiation comes from tech/fund/sentiment dimensions.
**Warning signs:** Rankings change dramatically when macro weight changes by small amounts.

## Code Examples

### Extending OllamaClient for Report Generation

```python
# In src/localstock/ai/client.py — add method to existing class
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=5, max=30),
    retry=retry_if_exception_type(
        (httpx.ConnectError, httpx.TimeoutException, ResponseError)
    ),
)
async def generate_report(
    self, data_prompt: str, symbol: str
) -> StockReport:
    """Generate full analysis report for a stock.

    Args:
        data_prompt: Pre-formatted prompt with ALL data injected.
        symbol: Stock ticker for logging.

    Returns:
        StockReport with all analysis sections.
    """
    response = await self.client.chat(
        model=self.model,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": data_prompt},
        ],
        format=StockReport.model_json_schema(),
        options={"temperature": 0.3, "num_ctx": 4096},
        keep_alive=self.keep_alive,
    )
    result = StockReport.model_validate_json(response.message.content)
    logger.info(f"Generated report for {symbol}: {result.recommendation}")
    return result
```

### Report System Prompt

```python
REPORT_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích chứng khoán Việt Nam.

Nhiệm vụ: Dựa vào DỮ LIỆU ĐƯỢC CUNG CẤP, viết báo cáo phân tích chi tiết bằng tiếng Việt.

Quy tắc:
1. CHỈ sử dụng dữ liệu được cung cấp. KHÔNG tự suy luận hay bịa số liệu.
2. Giải thích TẠI SAO điểm cao/thấp dựa trên các chỉ số cụ thể.
3. Liên kết bối cảnh vĩ mô với ngành/cổ phiếu cụ thể.
4. Phân biệt rõ gợi ý dài hạn vs lướt sóng.
5. Gợi ý lướt sóng PHẢI kèm cảnh báo T+3 và dự đoán xu hướng 3 ngày.
6. Khuyến nghị: Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh.
7. Viết ngắn gọn, mỗi phần 2-4 câu. Tổng báo cáo 500-800 từ.
8. Đây là công cụ tham khảo cá nhân, KHÔNG phải tư vấn đầu tư chính thức."""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Macro weight 0% in scoring | Macro weight 20% (activate in Phase 4) | Phase 4 | Composite scores will incorporate macro context; rankings may shift |
| Sentiment-only LLM usage | Report generation + sentiment | Phase 4 | OllamaClient used for 2 purposes; longer responses required |
| No report storage | AnalysisReport table | Phase 4 | Reports stored for dashboard display (Phase 6) |
| No macro data | MacroIndicator table + auto/manual collection | Phase 4 | New data dimension for scoring |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/ -x --timeout=30` |
| Full suite command | `python3 -m pytest tests/ --timeout=30` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REPT-01 | LLM generates Vietnamese report with all sections | unit (mock LLM) | `python3 -m pytest tests/test_reports/test_generator.py -x` | ❌ Wave 0 |
| REPT-02 | Report has tech+fund+sent+macro+recommendation | unit | `python3 -m pytest tests/test_reports/test_generator.py::test_report_sections -x` | ❌ Wave 0 |
| MACR-01 | Macro data stored in DB (4 indicator types) | unit | `python3 -m pytest tests/test_macro/test_crawler.py -x` | ❌ Wave 0 |
| MACR-02 | Macro impact maps to sectors correctly | unit | `python3 -m pytest tests/test_macro/test_impact.py -x` | ❌ Wave 0 |
| T3-01 | 3-day trend prediction from indicators | unit | `python3 -m pytest tests/test_reports/test_t3.py -x` | ❌ Wave 0 |
| T3-02 | Report distinguishes long-term vs swing + T+3 warning | unit | `python3 -m pytest tests/test_reports/test_generator.py::test_t3_warning -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/ -x --timeout=30`
- **Per wave merge:** `python3 -m pytest tests/ --timeout=30`
- **Phase gate:** Full suite green (147 existing + new tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reports/__init__.py` + `test_generator.py` — covers REPT-01, REPT-02, T3-02
- [ ] `tests/test_reports/test_t3.py` — covers T3-01
- [ ] `tests/test_macro/__init__.py` + `test_crawler.py` — covers MACR-01
- [ ] `tests/test_macro/test_impact.py` — covers MACR-02
- [ ] `tests/test_macro/test_scorer.py` — macro score normalization
- [ ] `tests/test_scoring/test_engine.py` — extend with macro dimension tests

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | T+3 is the correct HOSE settlement rule (not T+2) | T+3 Settlement Logic | Low — user explicitly specified T+3 in requirements; even if actual rule is T+2, T+3 is more conservative and safer for recommendations |
| A2 | VCB publishes XML feed for exchange rates at known URL | Macro Data Sourcing | Medium — if URL changes, fallback to manual entry is built in |
| A3 | Macro sector impact multipliers are reasonable starting points | Macro-to-Sector Impact | Medium — incorrect weights produce misleading macro scores; weights should be calibrated over time with actual market data |
| A4 | Qwen2.5 14B can generate coherent 500-800 word Vietnamese reports within 4096 context | Report Length Budget | Medium — if output quality degrades, reduce report length or switch to 7B for faster but shorter reports |
| A5 | SBV interest rate changes happen infrequently enough for manual entry | Macro Data Sourcing | Low — SBV policy rate changes 2-4 times per year; manual entry is practical |
| A6 | 20 stocks is sufficient for report generation batch (time budget) | Pitfall 4 | Low — 20 × 15s = 5 minutes, well within acceptable range |

## Open Questions

1. **VCB Exchange Rate XML Endpoint Stability**
   - What we know: VCB has published an XML feed historically at `portal.vietcombank.com.vn`
   - What's unclear: Whether the exact URL is still active and returns parseable XML
   - Recommendation: Test the URL during implementation; if broken, fall back to manual entry + add alternative source (BIDV or SJC gold price page)

2. **Qwen2.5 14B Vietnamese Report Quality**
   - What we know: Qwen2.5 handles Vietnamese well for sentiment classification (Phase 3)
   - What's unclear: Quality of 500-800 word narrative generation in Vietnamese specifically
   - Recommendation: Test with a sample report during first implementation task; if quality is poor, try lower temperature (0.1) or simpler prompt structure

3. **Optimal Scoring Weights After Macro Addition**
   - What we know: Current weights are 35/35/30/0; proposed 30/30/20/20
   - What's unclear: Whether 20% macro weight is too much given sector-uniform scoring
   - Recommendation: Start with 20%, monitor ranking stability; user can adjust via env vars

## Environment Availability

Step 2.6: SKIPPED (no external dependencies beyond what Phases 1-3 already established — Python, PostgreSQL, Ollama are all already configured and running).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user tool |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | Single-user tool |
| V5 Input Validation | Yes | Pydantic models for macro data input; sanitize LLM prompt inputs |
| V6 Cryptography | No | No secrets or encryption needed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via macro data input | Tampering | Pydantic validation on API input; macro values are numeric, not free text |
| LLM generating harmful financial advice | Information Disclosure | Report includes disclaimer: "không phải tư vấn đầu tư chính thức" |
| Scraping target rate-limiting/blocking | Denial of Service | tenacity retry with backoff; manual entry fallback |

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/localstock/ai/client.py` — OllamaClient patterns, structured output via Pydantic
- Codebase analysis: `src/localstock/scoring/` — scoring engine, normalizer, config patterns
- Codebase analysis: `src/localstock/services/` — service orchestration patterns
- Codebase analysis: `src/localstock/db/models.py` — 13 existing models, all patterns established
- `.planning/research/PITFALLS.md` — Pitfalls 3, 4, 7 directly applicable to this phase

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` — macro-to-stock linking as differentiator, anti-features list
- `.planning/phases/04-ai-reports-macro-t3/04-CONTEXT.md` — all D-01 through D-05 discretion areas

### Tertiary (LOW confidence)
- VCB XML exchange rate feed URL — needs runtime verification
- Macro sector impact multipliers — domain knowledge, needs calibration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all patterns proven in Phases 1-3
- Architecture: HIGH — follows established service/repository patterns exactly
- Report generation: MEDIUM — Qwen2.5 14B Vietnamese report quality unverified at 500-800 word length
- Macro data sourcing: MEDIUM — VCB XML endpoint needs verification; SBV/GSO manual entry is pragmatic but limited
- T+3 logic: HIGH — uses existing technical indicators, no new computation needed
- Pitfalls: HIGH — directly verified against PITFALLS.md research

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days — stable domain, no fast-moving dependencies)
