# Architecture Research

**Domain:** AI analysis depth — adding structured trade plans to existing Vietnamese stock agent
**Researched:** 2026-04-25
**Confidence:** HIGH (based on full codebase read, not training data speculation)

## Standard Architecture

### System Overview

Current pipeline (v1.3, unchanged structurally by v1.4):

```
┌─────────────────────────────────────────────────────────────────┐
│  DAILY SCHEDULER (APScheduler 15:45)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Pipeline │→ │Analysis  │→ │ Scoring  │→ │ Report   │        │
│  │(crawlers)│  │ Service  │  │ Service  │  │ Service  │        │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘        │
│                                                  ↓              │
│                                          Telegram notify        │
└─────────────────────────────────────────────────────────────────┘
           ↓ stores to                         ↓ reads from
┌─────────────────────────────────────────────────────────────────┐
│  POSTGRESQL (Supabase)                                          │
│  stock_prices | technical_indicators | financial_ratios         │
│  composite_scores | analysis_reports | sector_snapshots         │
└─────────────────────────────────────────────────────────────────┘
           ↑ reads                             ↑ reads
┌─────────────────────────────────────────────────────────────────┐
│  FASTAPI (9 routers, ~30 endpoints)                             │
│  /api/reports | /api/scores | /api/analysis | /api/prices ...   │
└─────────────────────────────────────────────────────────────────┘
           ↑ fetches via TanStack Query
┌─────────────────────────────────────────────────────────────────┐
│  NEXT.JS 16 FRONTEND (Helios)                                   │
│  /stock/[symbol] → AIReportPanel | ScoreBreakdown | PriceChart  │
└─────────────────────────────────────────────────────────────────┘
```

### v1.4 Target: What Changes vs What Is New

v1.4 is a _vertical enrichment_ of the existing pipeline, not a structural change. The
pipeline shape stays the same. Changes happen at two insertion points:

**Insertion point 1 — AnalysisService / TechnicalAnalyzer** (signal computation):
- New signal methods added to `TechnicalAnalyzer`: candlestick pattern detection,
  volume divergence analysis
- Sector momentum derived from existing `SectorSnapshotRepository` (no new data)
- These signals flow into the `indicator_data` dict that already feeds `ReportDataBuilder.build()`

**Insertion point 2 — ReportService / OllamaClient** (LLM layer):
- `StockReport` Pydantic model in `ai/client.py` gains new fields:
  `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, `signal_conflicts`
- `REPORT_SYSTEM_PROMPT` and `REPORT_USER_TEMPLATE` in `ai/prompts.py` are restructured
  to request the new fields and provide the signal data to reason from
- `analysis_reports.content_json` JSONB column stores the richer `StockReport` dump —
  **no Alembic migration needed** (it is already JSONB)

**Frontend** (display layer):
- `StockReport` TypeScript interface in `lib/types.ts` gains new optional fields
- `AIReportPanel` component gets a `TradePlanSection` to render the new structured fields

### Component Responsibilities (v1.4)

| Component | Responsibility | Changes in v1.4? |
|-----------|---------------|------------------|
| `TechnicalAnalyzer` (`analysis/technical.py`) | Compute indicators from OHLCV via pandas-ta | ADD: `detect_candlestick_patterns()`, `compute_volume_divergence()` |
| `AnalysisService` (`services/analysis_service.py`) | Orchestrate technical + fundamental analysis | No change needed — new signals injected by ReportService separately |
| `SectorService` (`services/sector_service.py`) | Compute sector avg_score, avg_score_change | NO CHANGE — read-only consumer added in ReportService |
| `ScoringService` (`services/scoring_service.py`) | Normalize and composite-weight dimension scores | NO CHANGE |
| `ReportService` (`services/report_service.py`) | Gather data, build prompt, call LLM, store | MODIFY: inject new signals before `ReportDataBuilder.build()` |
| `ReportDataBuilder` (`reports/generator.py`) | Assemble flat dict for prompt template | MODIFY: add new signal keys |
| `StockReport` (`ai/client.py`) | Pydantic model that is the Ollama `format` parameter | ADD: 6 new fields |
| `OllamaClient.generate_report()` (`ai/client.py`) | Send prompt to Ollama, parse response | NO CHANGE — format picks up schema automatically |
| `REPORT_SYSTEM_PROMPT` + `REPORT_USER_TEMPLATE` (`ai/prompts.py`) | Instruct LLM and inject data | REWRITE: request price levels, conflict explanation, catalyst, risk |
| `analysis_reports` table (`db/models.py`) | Store generated report as JSONB | NO CHANGE — `content_json` JSONB absorbs new fields automatically |
| `GET /api/reports/{symbol}` (`api/routes/reports.py`) | Return report JSON | NO CHANGE — returns `content_json` verbatim |
| `StockReport` TypeScript type (`lib/types.ts`) | Frontend type contract | ADD: optional new fields |
| `AIReportPanel` (`components/stock/ai-report-panel.tsx`) | Render AI report | ADD: `TradePlanSection` sub-component |

## Recommended Project Structure

No new top-level modules needed. All changes are surgical within existing files:

```
apps/prometheus/src/localstock/
├── analysis/
│   └── technical.py        # MODIFY: add detect_candlestick_patterns(),
│                           #         compute_volume_divergence()
├── ai/
│   ├── client.py           # MODIFY: expand StockReport Pydantic model (+6 fields)
│   └── prompts.py          # MODIFY: rewrite REPORT_SYSTEM_PROMPT + REPORT_USER_TEMPLATE
├── reports/
│   └── generator.py        # MODIFY: add new signal keys to ReportDataBuilder.build()
└── services/
    └── report_service.py   # MODIFY: inject new signals into indicator_data before build()

apps/helios/src/
├── lib/
│   └── types.ts             # MODIFY: expand StockReport interface (+6 optional fields)
└── components/stock/
    └── ai-report-panel.tsx  # MODIFY: add TradePlanSection rendering
```

### Structure Rationale

- **No new Python files**: candlestick detection and volume divergence are signal computation
  methods — same domain as existing `TechnicalAnalyzer`. No separate module warranted.
- **No new API endpoints**: `GET /api/reports/{symbol}` returns `content_json` verbatim;
  new fields appear in the JSON response automatically once the LLM generates them.
- **No Alembic migration**: `analysis_reports.content_json` is already JSONB. New fields in
  `StockReport.model_dump()` are stored without schema changes. An optional migration to add
  typed columns (e.g., `entry_price FLOAT`, `risk_rating VARCHAR`) is worth doing only if
  server-side filtering by those fields is needed (e.g., ranking by risk_rating).
- **No new frontend pages**: the `/stock/[symbol]` page already hosts `AIReportPanel`. The
  trade plan is a section within that panel, not a separate page.

## Architectural Patterns

### Pattern 1: New Signal via indicator_data Dict (not a new table)

**What:** New signals (candlestick patterns, volume divergence, sector momentum) are added
as keys to the `indicator_data` dict that `ReportDataBuilder.build()` already accepts.
They do not get their own DB table, repo, or API endpoint.

**When to use:** When the signal is consumed only by the LLM prompt and not needed for
independent querying, filtering, or historical tracking.

**Trade-offs:** Simpler (zero DB changes), but signals are not queryable in isolation.
If a future milestone wants "show all stocks where hammer pattern detected today," a
`CandlestickSignal` table would be needed. For v1.4, the dict approach is correct.

**Example:**
```python
# In ReportService.run_full(), inside the per-stock loop:
prices = await self.price_repo.get_prices(symbol)
ohlcv_df = pd.DataFrame([...])  # same as AnalysisService uses

patterns = self.tech_analyzer.detect_candlestick_patterns(ohlcv_df)
# returns: {"hammer": True, "doji": False, "engulfing": False, "summary": "Hammer"}

vol_divergence = self.tech_analyzer.compute_volume_divergence(ohlcv_df)
# returns: {"signal": "bullish", "detail": "volume rising while RSI diverging"}

sector_code = await self.industry_repo.get_group_for_symbol(symbol)
sector_snap = await self.sector_repo.get_latest(sector_code)
sector_momentum = _derive_sector_label(sector_snap)
# returns: "tăng mạnh (+3.2)" or "giảm mạnh (-4.1)" or "ổn định (+0.5)"

indicator_data.update(patterns)
indicator_data["volume_divergence"] = vol_divergence.get("signal")
indicator_data["sector_momentum"] = sector_momentum
```

### Pattern 2: Expand StockReport Pydantic Model (Ollama format constraint)

**What:** `StockReport` is passed as `format=StockReport.model_json_schema()` to Ollama.
Adding fields to the model automatically constrains the LLM to generate those fields in its
JSON output. `OllamaClient.generate_report()` requires zero changes.

**When to use:** Any time new structured outputs are needed from the LLM.

**Trade-offs:** More JSON fields = more tokens = ~15-25% longer generation time on RTX 3060.
Keep new fields as short targeted strings/floats, not open-ended paragraphs.

**Example:**
```python
class StockReport(BaseModel):
    # --- existing 9 fields unchanged ---
    summary: str = ...
    technical_analysis: str = ...
    fundamental_analysis: str = ...
    sentiment_analysis: str = ...
    macro_impact: str = ...
    long_term_suggestion: str = ...
    swing_trade_suggestion: str = ...
    recommendation: str = ...
    confidence: str = ...
    # --- 6 new fields ---
    entry_price: float | None = Field(None, description="Giá vào lệnh gợi ý (VND). Null nếu không đủ cơ sở.")
    stop_loss: float | None = Field(None, description="Giá cắt lỗ (VND). Null nếu không đủ cơ sở.")
    target_price: float | None = Field(None, description="Giá mục tiêu (VND). Null nếu không đủ cơ sở.")
    risk_rating: str = Field(description="Cao / Trung bình / Thấp — kèm lý do ngắn gọn 1 câu")
    catalyst: str = Field(description="Catalyst/sự kiện quan trọng nhất gần đây ảnh hưởng khuyến nghị")
    signal_conflicts: str = Field(description="Mô tả xung đột tín hiệu kỹ thuật vs cơ bản. 'Không có xung đột đáng kể' nếu đồng nhất.")
```

### Pattern 3: Prompt Data Injection — Tell LLM What It Has, What to Produce

**What:** The existing prompt architecture separates _data_ (user template, injected at
generation time) from _instructions_ (system prompt, static). New signals go into the
user template as data sections; new output requirements go into the system prompt as rules.

**When to use:** Always. Never ask the LLM to invent data. Provide data, ask for analysis.

**Critical:** `entry_price`, `stop_loss`, `target_price` must be grounded in existing
support/resistance data. The `TechnicalIndicator` model already stores: `support_1`,
`support_2`, `resistance_1`, `resistance_2`, `nearest_support`, `nearest_resistance`,
`pivot_point`. These are already passed through `indicator_data` to the prompt. The system
prompt must explicitly instruct the LLM to derive price levels from those anchors.

**Example additions to REPORT_USER_TEMPLATE:**
```
🕯️ CANDLESTICK & PHÂN KỲ KHỐI LƯỢNG
Mẫu nến gần đây: {candlestick_summary}
Phân kỳ khối lượng: {volume_divergence}

📊 ĐỘNG LƯỢNG NGÀNH ({industry})
Xu hướng ngành: {sector_momentum}

📐 CÁC MỨC GIÁ THAM CHIẾU
Hỗ trợ gần nhất: {nearest_support} | Kháng cự gần nhất: {nearest_resistance}
Hỗ trợ 1/2: {support_1}/{support_2} | Kháng cự 1/2: {resistance_1}/{resistance_2}
Pivot Point: {pivot_point}
```

**Example additions to REPORT_SYSTEM_PROMPT:**
```
9. entry_price: Gợi ý mức vào lệnh CỤ THỂ dựa trên support/resistance được cung cấp.
   entry_price phải nằm giữa nearest_support và close_price (hoặc ngay tại support).
   Nếu không có dữ liệu support/resistance, trả về null.
10. stop_loss: = nearest_support trừ 3-5% buffer. Nếu không có, trả về null.
11. target_price: = nearest_resistance hoặc resistance_1. Nếu không có, trả về null.
12. risk_rating: Cao/Trung bình/Thấp + 1 câu lý do. Cao = D/E > 2 HOẶC RSI > 75 HOẶC trend không rõ.
13. catalyst: Yếu tố/sự kiện quan trọng nhất trong bối cảnh đã cung cấp ảnh hưởng đến khuyến nghị.
    Ví dụ: "Ngành ngân hàng đang trong đà tăng mạnh (+3.2 điểm)" hoặc "Sentiment tích cực từ tin tức".
14. signal_conflicts: Nếu kỹ thuật gợi ý mua nhưng cơ bản yếu (hoặc ngược lại), giải thích rõ.
    Nếu đồng nhất: "Không có xung đột đáng kể."
```

## Data Flow

### v1.4 Enhanced Report Generation Flow

```
[ReportService.run_full() — per stock loop]

PriceRepo.get_prices(symbol)
    ↓ ohlcv_df
TechnicalAnalyzer.detect_candlestick_patterns(ohlcv_df)   [NEW METHOD]
TechnicalAnalyzer.compute_volume_divergence(ohlcv_df)      [NEW METHOD]
    ↓
SectorSnapshotRepository.get_latest(group_code)            [EXISTING REPO, NEW USAGE]
    → derive sector_momentum label from avg_score_change
    ↓
indicator_data dict (from IndicatorRepo.get_latest):
  existing: rsi_14, macd, trend_direction, support_1/2, resistance_1/2,
            nearest_support, nearest_resistance, pivot_point, ...
  new keys: candlestick_summary, volume_divergence, sector_momentum
    ↓
ReportDataBuilder.build(... indicator_data ...)            [MODIFIED: new keys]
    ↓
build_report_prompt(data)                                   [uses MODIFIED template]
    ↓
OllamaClient.generate_report(prompt, symbol)               [UNCHANGED]
  → Ollama enforces MODIFIED StockReport JSON schema
  → LLM generates 15 fields (9 existing + 6 new)
    ↓
StockReport instance
  → .model_dump() → content_json JSONB               [NO MIGRATION NEEDED]
  → .recommendation → mapped to DB enum
  → .entry_price, .stop_loss, .target_price          [optional: store in typed columns]
    ↓
GET /api/reports/{symbol}                                   [UNCHANGED]
  → returns full content_json dict
    ↓
Frontend: StockReport TypeScript type                       [MODIFIED: optional new fields]
  → AIReportPanel.TradePlanSection renders:          [NEW sub-component]
      entry/stop/target prices, risk badge, catalyst, conflicts
```

### Sector Momentum Signal Derivation

The existing `SectorSnapshot` table (`sector_snapshots`) already stores `avg_score_change`
(score delta vs previous day) computed by `SectorService`. `ReportService` can read this
directly without new data crawling:

```python
# In ReportService, needs SectorSnapshotRepository (add to __init__):
from localstock.db.repositories.sector_repo import SectorSnapshotRepository

# In run_full() and generate_for_symbol(), per-stock:
sector_code = await self.industry_repo.get_group_for_symbol(symbol)
if sector_code:
    sector_snap = await self.sector_repo.get_latest(sector_code)
    if sector_snap and sector_snap.avg_score_change is not None:
        delta = sector_snap.avg_score_change
        if delta > 2.0:
            sector_momentum = f"tăng mạnh (+{delta:.1f} điểm)"
        elif delta < -2.0:
            sector_momentum = f"giảm mạnh ({delta:.1f} điểm)"
        else:
            sector_momentum = f"ổn định ({delta:+.1f} điểm)"
    else:
        sector_momentum = "Không có dữ liệu"
```

This requires zero new DB queries beyond what SectorService already writes. The only code
change is `ReportService.__init__` adding `self.sector_repo = SectorSnapshotRepository(session)`.

## Integration Points

### Backend Integration Map

| Component | Change Type | Risk | Notes |
|-----------|------------|------|-------|
| `analysis/technical.py` | ADDITIVE (2 new methods) | Low | Pure functions on DataFrame, easy to unit test |
| `ai/client.py` (StockReport) | ADDITIVE (6 new Pydantic fields) | Low | All existing tests still pass; new fields have defaults or are nullable |
| `ai/prompts.py` (both prompts) | REPLACEMENT | Medium | Prompt changes affect all report quality; needs testing with real LLM |
| `reports/generator.py` | ADDITIVE (new keys in build()) | Low | Same dict pattern, same null-safety helpers |
| `services/report_service.py` | ADDITIVE (signal injection) | Low | New repo init + new dict keys before build() |
| `db/repositories/sector_repo.py` | READ-ONLY (new consumer) | None | SectorSnapshotRepository.get_latest() already exists |
| `db/models.py` (AnalysisReport) | OPTIONAL typed columns | Low | JSONB already sufficient; typed columns only needed for server-side filtering |
| `api/routes/reports.py` | NO CHANGE | None | Returns content_json verbatim |

### Frontend Integration Map

| Component | Change Type | Risk | Notes |
|-----------|------------|------|-------|
| `lib/types.ts` (StockReport) | ADDITIVE (optional fields) | None | TypeScript optional fields are backward compatible |
| `components/stock/ai-report-panel.tsx` | ADDITIVE (TradePlanSection) | Low | New section conditional on field presence |
| `lib/queries.ts` | NO CHANGE | None | Same endpoint, same hook |
| `app/stock/[symbol]/page.tsx` | NO CHANGE | None | Already passes report to AIReportPanel |

### Internal Boundaries

| Boundary | Communication Pattern | v1.4 Notes |
|----------|----------------------|-----------|
| TechnicalAnalyzer → AnalysisService | Method return dicts | New methods return dicts; AnalysisService need not call them |
| TechnicalAnalyzer → ReportService | Direct call on ohlcv_df | ReportService calls new methods separately (signals are LLM-only) |
| ReportService → SectorSnapshotRepo | Async DB read | Add repo to ReportService.__init__; read in per-stock loop |
| ReportDataBuilder → OllamaClient | String prompt | New keys in dict map to new template sections |
| OllamaClient → AnalysisReport.content_json | model_dump() → JSONB | New fields stored automatically |
| FastAPI → Frontend | JSON response | content_json new fields flow through without endpoint change |

## Suggested Build Order

Dependencies drive the order. Each step unlocks the next.

### Step 1: New Signal Methods (Backend, analysis layer)

Add `detect_candlestick_patterns()` and `compute_volume_divergence()` to `TechnicalAnalyzer`
in `analysis/technical.py`.

These are pure functions on a DataFrame — no DB, no LLM, no service dependencies.
Unit tests can be written immediately against known OHLCV fixtures.

Deliverable: Two methods returning dicts. Tests pass.

### Step 2: Expand StockReport + Rewrite Prompts (Backend, AI layer)

Add 6 new fields to `StockReport` in `ai/client.py`. Rewrite `REPORT_SYSTEM_PROMPT`
and `REPORT_USER_TEMPLATE` in `ai/prompts.py` to:
- Provide new signal data in the user template (candlestick, volume divergence, sector momentum, S/R levels)
- Instruct LLM to produce the new fields in the system prompt

Deliverable: Manually test with one symbol to verify LLM generates sensible price levels.
This is the highest-risk step — prompt quality directly determines output quality.

### Step 3: Wire Signals into ReportService + ReportDataBuilder (Backend, orchestration)

Modify `ReportService.__init__` to add `SectorSnapshotRepository`. Modify `run_full()` and
`generate_for_symbol()` to call new signal methods and inject results into `indicator_data`.
Modify `ReportDataBuilder.build()` to expose new keys using existing `_safe()` helpers.

Deliverable: Full pipeline run generates reports with all new fields populated.

### Step 4 (Optional): DB Typed Columns

If the ranking page or notifications need to filter/sort by `risk_rating` or display
`entry_price` without parsing `content_json` in the API layer, add typed columns to
`analysis_reports` and an Alembic migration. Skip entirely if the frontend parses
`content_json` directly (simpler, and sufficient for v1.4 scope).

Deliverable (if done): Migration file, model columns, ReportService stores new fields.

### Step 5: Frontend Display (Frontend)

Update `StockReport` TypeScript interface. Add `TradePlanSection` inside `AIReportPanel`
that conditionally renders entry/stop/target prices, risk badge, catalyst, and conflicts
only when those fields are present (they will be null for reports generated before v1.4).

Deliverable: `/stock/[symbol]` shows structured trade plan section when data available.

## Anti-Patterns

### Anti-Pattern 1: New Signals as a Separate Table

**What people do:** Create a `CandlestickSignal` table, new repo, new service, new
endpoint for pattern data.

**Why it's wrong:** The signals are consumed only by the LLM prompt for this milestone.
A new table adds a migration, repo, and endpoint surface for data that logically belongs
in `indicator_data`. Over-engineering for v1.4.

**Do this instead:** Compute patterns inline in TechnicalAnalyzer, pass through
`indicator_data` dict. If a future milestone needs queryable pattern history, add the
table then.

### Anti-Pattern 2: Modify OllamaClient.generate_report() Signature

**What people do:** Add explicit `candlestick_data`, `sector_momentum` parameters to
`generate_report()` to make signal injection "more explicit."

**Why it's wrong:** Signal injection is a prompt-level concern, not a client-level concern.
The client's job is generic: string in, StockReport out. Leaking domain knowledge into
the client couples it to analysis semantics it should not own.

**Do this instead:** All signal injection happens in `ReportDataBuilder.build()` and the
prompt template strings. `generate_report()` stays unchanged.

### Anti-Pattern 3: Ask the LLM to Invent entry_price Without Data Anchors

**What people do:** Add `entry_price` to StockReport, add "Generate an entry price" to
the system prompt. LLM hallucinates a number.

**Why it's wrong:** The LLM should reason about data provided, not invent it. The
`TechnicalIndicator` model already stores `support_1`, `support_2`, `resistance_1`,
`resistance_2`, `nearest_support`, `nearest_resistance`, `pivot_point` — all of which are
already available in `indicator_data` and can be surfaced in the prompt.

**Do this instead:** Expose the support/resistance values explicitly in `REPORT_USER_TEMPLATE`.
Instruct in the system prompt: "entry_price = level between nearest_support and close_price.
stop_loss = nearest_support - buffer. target_price = nearest_resistance." The LLM then
computes grounded, defensible price levels.

### Anti-Pattern 4: Replace ReportDataBuilder with Inline Dict in ReportService

**What people do:** Since `build()` "just returns a dict," inline the dict construction
into `ReportService` to reduce the abstraction layer.

**Why it's wrong:** `ReportDataBuilder.build()` is the single place that normalizes
None-safety with `_safe()`, `_safe_float()`, `_safe_pct()`. Inlining scatters null-safety
logic across ReportService, making it untestable and fragile.

**Do this instead:** Add new keys to `ReportDataBuilder.build()` following the exact
same `_safe()` / `_safe_float()` pattern already established. Test the builder separately.

### Anti-Pattern 5: Rewrite Existing StockReport Fields

**What people do:** Decide the existing 9 fields are "poorly named" and rename/restructure
them while adding the 6 new ones.

**Why it's wrong:** Existing `content_json` in DB stores `model_dump()` output. Renaming
fields invalidates all historical reports (they will not parse with the new schema). The
existing fields work correctly.

**Do this instead:** Only ADD new fields. Do not modify existing field names or types.

## Scaling Considerations

This is a single-user personal tool (~400 stocks, daily run). The relevant constraint
is LLM inference time on RTX 3060 (12GB VRAM, Qwen2.5 14B Q4_K_M).

| Concern | Current (v1.3) | After v1.4 |
|---------|---------------|------------|
| LLM inference per report | ~3-5 min | ~4-6 min (+15-25% for 6 new fields) |
| Report pipeline for top 20 | ~60-100 min | ~80-120 min |
| DB storage per report | ~2-5KB JSONB | ~2-7KB JSONB |
| API response size | Same | Same |
| DB query overhead per stock | n queries | n+1 (add SectorSnapshotRepo.get_latest) |

If generation time becomes unacceptable, reduce `top_n` default from 20 to 10.
The RTX 3060 can generate structured JSON stably at these field counts — confirmed by
existing 9-field StockReport working reliably.

## Sources

Findings are 100% based on direct codebase read (HIGH confidence):

- `apps/prometheus/src/localstock/ai/client.py` — StockReport (9 fields), OllamaClient
- `apps/prometheus/src/localstock/ai/prompts.py` — REPORT_SYSTEM_PROMPT, REPORT_USER_TEMPLATE
- `apps/prometheus/src/localstock/analysis/technical.py` — TechnicalAnalyzer (existing methods)
- `apps/prometheus/src/localstock/db/models.py` — TechnicalIndicator (S/R columns), AnalysisReport (content_json JSONB)
- `apps/prometheus/src/localstock/reports/generator.py` — ReportDataBuilder, _safe helpers
- `apps/prometheus/src/localstock/services/analysis_service.py` — AnalysisService orchestration
- `apps/prometheus/src/localstock/services/report_service.py` — ReportService full implementation
- `apps/prometheus/src/localstock/services/scoring_service.py` — ScoringService
- `apps/prometheus/src/localstock/services/sector_service.py` — SectorService, avg_score_change
- `apps/prometheus/src/localstock/services/pipeline.py` — Pipeline orchestrator
- `apps/helios/src/app/stock/[symbol]/page.tsx` — StockDetailPage, AIReportPanel usage
- `apps/helios/src/components/stock/ai-report-panel.tsx` — AIReportPanel, content_json fallback
- `apps/helios/src/lib/types.ts` — StockReport TypeScript interface
- `apps/helios/src/lib/queries.ts` — useStockReport hook, cache invalidation

---
*Architecture research for: LocalStock v1.4 AI Analysis Depth*
*Researched: 2026-04-25*
