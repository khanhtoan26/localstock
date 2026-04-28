# Phase 20: Service Wiring & Report Content - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the full report content pipeline so that every generated stock report contains: entry zone (price range), stop-loss, target price, risk rating with Vietnamese reasoning, signal conflict explanation (when applicable), and recent catalyst — all pre-computed in Python, injected into the LLM prompt, and persisted via content_json.

Requirements covered: REPORT-01, REPORT-02, REPORT-03, REPORT-04, REPORT-05.

</domain>

<decisions>
## Implementation Decisions

### Entry Zone Computation (REPORT-01)
- **D-01:** Entry zone is **pre-computed in Python** before LLM call. The computed values are injected into the prompt as hard numbers — the LLM does NOT decide prices.
- **D-02:** Entry zone is a **price range**: lower bound = `nearest_support`, upper bound = Bollinger upper band. Both come from `indicator_data` already computed by `TechnicalAnalyzer`.
- **D-03:** Fallback: when stock has < 40 price history rows (insufficient for Bollinger bands), use `close ± 2%` as the entry range.
- **D-04:** How to store the range in `entry_price: Optional[float]` — **Agent's Discretion**. Options: midpoint, lower bound, or add a second field. Agent picks the most pragmatic approach.

### Stop-Loss & Target Price (REPORT-02)
- **D-05:** Stop-loss = `max(support_2, close × 0.93)` — exactly per REPORT-02. Uses HOSE ±7% daily limit awareness (0.93 = one day's max downside).
- **D-06:** Target price = `nearest_resistance` if available, otherwise `close × 1.10` — per REPORT-02.
- **D-07:** Both values are pre-computed in Python and injected into the prompt.

### Risk Rating (REPORT-03)
- **D-08:** Risk rating is **LLM-generated** (already in StockReport schema from Phase 19). The LLM outputs "high"/"medium"/"low" based on the full analysis context. `_normalize_risk_rating()` from Phase 19 handles variant normalization post-generation.
- **D-09:** The LLM also generates Vietnamese reasoning text explaining the rating — this is part of the existing prompt output structure.

### Signal Conflict Detection (REPORT-04)
- **D-10:** Python pre-computes a boolean gate: `has_conflict = abs(tech_score - fund_score) > 25`. When True, conflict data is injected into the prompt.
- **D-11:** Inject into prompt: both scores + gap direction. Example: "Xung đột tín hiệu: Tech=72, Fund=41, gap=+31 (kỹ thuật > cơ bản)".
- **D-12:** The LLM generates `signal_conflicts` text explaining the conflicting signals and its resolution. When `has_conflict` is False, `signal_conflicts` = None in the output.

### Catalyst Synthesis (REPORT-05)
- **D-13:** **Agent's Discretion** for catalyst implementation. Requirements: synthesize from 7-day news articles + composite score delta since prior run. The LLM generates the `catalyst` field text.
- **D-14:** News data comes from `SentimentService.get_aggregated_sentiment()` (already used in report_service.py). Score delta comes from comparing current vs previous `CompositeScore` for the symbol.

### content_json Persistence
- **D-15:** **Agent's Discretion** for persistence approach. The 6 new StockReport fields (entry_price, stop_loss, target_price, risk_rating, catalyst, signal_conflicts) must be included in the `content_json` dict stored in `AnalysisReport.content_json`. Currently `content_json` is populated from `StockReport.model_dump()` — extending StockReport in Phase 19 should make this automatic.

### Agent's Discretion
- Exact location of entry zone computation function (new module or extend generator.py)
- How to handle Bollinger band data unavailability beyond the <40 rows fallback
- News article retrieval for catalyst (direct DB query or via existing crawlers)
- Score delta computation (query previous day's score or store delta in pipeline)
- Prompt template additions for conflict section layout

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §REPORT-01, REPORT-02, REPORT-03, REPORT-04, REPORT-05 — exact acceptance criteria for all five requirements

### Prior Phase Context
- `.planning/phases/19-prompt-schema-restructuring/19-CONTEXT.md` — StockReport schema decisions (D-01 through D-11), validation logic, prompt structure
- `.planning/phases/18-signal-computation/18-CONTEXT.md` — Signal output formats (candlestick, volume, sector momentum)

### Source Files
- `apps/prometheus/src/localstock/services/report_service.py` — Main orchestration point; already has signal wiring from Phase 19
- `apps/prometheus/src/localstock/reports/generator.py` — ReportDataBuilder, signal formatters, validation functions
- `apps/prometheus/src/localstock/ai/client.py` — StockReport model (15 fields), OllamaClient
- `apps/prometheus/src/localstock/ai/prompts.py` — REPORT_SYSTEM_PROMPT, REPORT_USER_TEMPLATE
- `apps/prometheus/src/localstock/analysis/technical.py` — TechnicalAnalyzer (S/R anchors, Bollinger bands in indicator_data)
- `apps/prometheus/src/localstock/db/models.py` §AnalysisReport — content_json column (JSON type)
- `apps/prometheus/src/localstock/db/repositories/score_repo.py` — CompositeScore queries for score delta

### Data Flow
- `apps/prometheus/src/localstock/services/sentiment_service.py` — `get_aggregated_sentiment()` for news-based sentiment
- `apps/prometheus/src/localstock/db/repositories/report_repo.py` — ReportRepository for storing reports

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `indicator_data` dict in report_service.py already contains: `pivot_point`, `support_1`, `support_2`, `resistance_1`, `resistance_2`, `nearest_support`, `nearest_resistance`, `bb_upper`, `bb_lower` — all needed for entry zone and SL/TP computation
- `_validate_price_levels(report, current_close)` — already validates price ordering and ±30% range
- `_normalize_risk_rating(report)` — already normalizes Vietnamese/cased variants
- `ReportDataBuilder.build()` with `signals_data` parameter — extend to accept pre-computed price levels
- `StockReport.model_dump()` — already used for content_json, new fields auto-included

### Established Patterns
- Score data retrieved via `self.score_repo.get_top_ranked()` → each `score` has `.technical_score`, `.fundamental_score`, `.composite_score`
- Per-stock error isolation with try/except in the main loop — continue on individual failures
- `_safe()` and `_safe_float()` for None-safe prompt rendering

### Integration Points
- Entry zone / SL / TP computation should happen between indicator data gathering and prompt building in report_service.py
- Conflict detection uses scores already available in the main loop (`score.technical_score`, `score.fundamental_score`)
- content_json population happens at report storage time — StockReport.model_dump() flows to AnalysisReport.content_json

</code_context>

<specifics>
## Specific Ideas

- Entry zone range: nearest_support → bb_upper gives a meaningful "buy zone" — support is the floor, Bollinger upper is the ceiling of normal volatility
- Stop-loss at max(support_2, close × 0.93) prevents stop-loss from sitting below two support levels while respecting HOSE daily limit
- Signal conflict prompt format: "Xung đột tín hiệu: Tech=72, Fund=41, gap=+31 (kỹ thuật > cơ bản)" — gives LLM enough context to explain the divergence

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 20-service-wiring-report-content*
*Context gathered: 2026-04-28*
