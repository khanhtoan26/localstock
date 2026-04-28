# Phase 18: Signal Computation - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement three new signal computation methods in the analysis engine:
1. Candlestick pattern detection — 5 patterns (doji, inside, hammer, engulfing, shooting star)
2. Volume divergence signal — MFI-based, gated on liquidity
3. Sector momentum scalar — derived from SectorSnapshot, ready for LLM prompt injection

All three methods must be independently unit-testable with synthetic DataFrames — no live DB or network calls required. Output is structured data consumed by Phase 19 (prompt & schema).

</domain>

<decisions>
## Implementation Decisions

### Volume Divergence Signal (SIGNAL-02)

- **D-01:** MFI (Money Flow Index) is the primary indicator for the volume divergence signal. CMF and OBV are not used as primary sources.
- **D-02:** The method returns a dict with three keys: `signal` (str), `value` (float), `indicator` (str). Example: `{"signal": "bullish", "value": 72.3, "indicator": "MFI"}`.
- **D-03:** MFI thresholds: `> 70` → `"bullish"`, `< 30` → `"bearish"`, `30–70` → `"neutral"`. (Consistent with RSI overbought/oversold convention.)
- **D-04:** Stocks with avg_volume < 100k shares/day return `None` for this signal (per SIGNAL-02 requirement). The method must not raise an error on low-liquidity stocks.

### Claude's Discretion

- **Code structure**: Whether new signals extend `TechnicalAnalyzer`, live in a new `SignalComputer` class, or are standalone functions — researcher/planner decides based on best fit with existing patterns.
- **Liquidity threshold window**: Which time window defines avg_volume for the 100k gate (20-day, 60-day, etc.) — researcher/planner decides; must be consistent with existing `compute_volume_analysis` logic.
- **Sector momentum definition**: How `SectorSnapshot.avg_score_change` (or a multi-day trend) is distilled to a named scalar — researcher/planner picks the cleanest representation for LLM injection.
- **Candlestick pattern implementation**: Which of the 5 patterns use pandas-ta CDL functions vs pure OHLC math — researcher decides; TA-Lib must NOT be required.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SIGNAL-01, SIGNAL-02, SIGNAL-03 — exact acceptance criteria for all three signal methods
- `.planning/ROADMAP.md` §Phase 18 — success criteria with synthetic DataFrame testability requirement

### Existing Analysis Code
- `apps/prometheus/src/localstock/analysis/technical.py` — TechnicalAnalyzer (pandas-ta patterns, OBV already computed); integration point for new signals
- `apps/prometheus/src/localstock/analysis/trend.py` — support/resistance, trend detection; reference for standalone-function style

### Data Models
- `apps/prometheus/src/localstock/db/models.py` §SectorSnapshot — fields available: `avg_score`, `avg_score_change`, `group_code`, `date`, `avg_volume`
- `apps/prometheus/src/localstock/db/models.py` §StockIndustryMapping — stock→sector mapping needed for SIGNAL-03 lookup

### Tests
- `apps/prometheus/tests/test_analysis/` — existing test patterns for analysis methods; new tests must follow same style (pytest-asyncio, synthetic DataFrames)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TechnicalAnalyzer.compute_volume_analysis()` — already computes `avg_volume_20` and `relative_volume`; the 100k liquidity gate in SIGNAL-02 should reference this existing logic
- `pandas-ta` already imported and used for OBV, RSI, MACD, BB — MFI can be added with the same `result.ta.mfi(append=True)` pattern
- `SectorSnapshot` DB model already populated by the sector rotation pipeline (SCOR-05)

### Established Patterns
- **pandas-ta individual calls**: indicators are called one at a time with `append=True` and wrapped in try/except — follow this for MFI and CDL patterns
- **Return dicts, not dataclasses**: all analysis methods return plain dicts (consistent with `compute_volume_analysis`, `detect_trend`)
- **Graceful null returns**: when data is insufficient, methods return `None` values in the dict rather than raising — follow for the liquidity gate

### Integration Points
- New signal methods are read by Phase 19's prompt builder — output must be JSON-serializable
- `SectorSnapshot` is read from DB; SIGNAL-03 requires an async DB query (or a pre-loaded dict) — researcher should clarify whether signal computation stays pure-DataFrame or accepts a DB-fetched sector dict

</code_context>

<specifics>
## Specific Ideas

- MFI thresholds (70/30) were chosen to match RSI convention — keeps the mental model consistent for prompt reading by the LLM
- Output dict key `"indicator": "MFI"` makes the source explicit, useful if the indicator strategy changes later

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope
</deferred>

---

*Phase: 18-signal-computation*
*Context gathered: 2026-04-25*
