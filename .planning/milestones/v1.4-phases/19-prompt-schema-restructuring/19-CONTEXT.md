# Phase 19: Prompt & Schema Restructuring - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the `StockReport` Pydantic model and Ollama prompt to accommodate six new trade guidance fields, enlarge the Ollama context window, and add post-generation price validation. No new API endpoints, no new DB tables — all changes live in `ai/client.py`, `ai/prompts.py`, and `reports/generator.py`.

Requirements covered: PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04.

</domain>

<decisions>
## Implementation Decisions

### Context Window (PROMPT-01)
- **D-01:** Set `num_ctx` to **8192** in `generate_report()`. Rationale: Qwen2.5 14B Q4_K_M uses ~8GB VRAM; 8192 context adds ~1.5GB → ~9.5GB total, comfortably within RTX 3060 12GB. Provides 33% headroom over the 6144 minimum for the expanded prompt.
- **D-02:** Leave `classify_sentiment()` at 4096 — sentiment prompts are short and don't need expansion.

### StockReport Schema Extension (PROMPT-02)
- **D-03:** Add six new `Optional` fields to `StockReport` in `ai/client.py`. All default to `None`:
  ```python
  entry_price: Optional[float] = None
  stop_loss: Optional[float] = None
  target_price: Optional[float] = None
  risk_rating: Optional[str] = None       # "high" | "medium" | "low" — str, not Literal
  catalyst: Optional[str] = None
  signal_conflicts: Optional[str] = None
  ```
- **D-04:** `risk_rating` uses `Optional[str]` (not `Literal["high","medium","low"]`). Post-hoc normalization maps Vietnamese and capitalized variants to canonical English lowercase: `{"cao": "high", "trung bình": "medium", "thấp": "low", "High": "high", ...}`. This prevents LLM output variation from crashing the entire report via Pydantic `ValidationError`.

### Prompt Restructuring (PROMPT-03)
- **D-05:** Add a dedicated new section `🔔 TÍN HIỆU BỔ SUNG` at the end of `REPORT_USER_TEMPLATE`, immediately before the final instruction line ("Hãy viết báo cáo..."). This section groups all new signal data: S/R anchors, candlestick patterns, volume divergence, sector momentum.
- **D-06:** When a signal value is `None` (e.g., sector momentum unavailable for the stock), render it as `"N/A"` in the prompt — do NOT omit the field. Omitting would make the LLM unaware that the field exists, causing it to hallucinate or ignore it.
- **D-07:** The new section format:
  ```
  🔔 TÍN HIỆU BỔ SUNG
  Hỗ trợ gần nhất: {nearest_support} | Kháng cự gần nhất: {nearest_resistance}
  Pivot: {pivot_point} | S1: {support_1} | S2: {support_2} | R1: {resistance_1} | R2: {resistance_2}
  Mô hình nến: {candlestick_patterns}
  Phân kỳ khối lượng (MFI): {volume_divergence}
  Động lực ngành: {sector_momentum}
  ```
- **D-08:** Update `REPORT_SYSTEM_PROMPT` to add explicit instructions: the LLM must output `entry_price`, `stop_loss`, `target_price` as numeric VND prices (not formatted strings), and `risk_rating` as exactly `"high"`, `"medium"`, or `"low"` in English lowercase.

### Post-Generation Validation (PROMPT-04)
- **D-09:** Add a `_validate_price_levels(report, current_close)` function in `reports/generator.py` that checks:
  1. `stop_loss < entry_price < target_price` — if violated, null only the 3 price fields
  2. All non-None price values within ±30% of `current_close` — if violated, null only the out-of-range price fields
- **D-10:** Fallback is price-fields-only: set `entry_price = stop_loss = target_price = None` when any price relationship is invalid. Keep `risk_rating`, `catalyst`, and `signal_conflicts` — they are valid LLM outputs unrelated to price failure.
- **D-11:** Log a warning when validation nulls price fields: `logger.warning(f"Price validation failed for {symbol}: stop_loss={sl}, entry={ep}, target={tp}, close={close}")`.

### Claude's Discretion
- Exact string formatting of the new prompt section (spacing, Vietnamese labels vs English)
- How candlestick patterns dict is serialized to the prompt string (e.g., "doji: True, hammer: False" or "patterns detected: doji, hammer")
- How volume divergence dict is serialized (e.g., "bullish (MFI=72.3)" or just the signal label)
- How sector momentum dict is serialized (e.g., "mild_inflow (+0.5)" )

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04 — exact acceptance criteria for all four prompt/schema requirements

### Source Files to Modify
- `apps/prometheus/src/localstock/ai/client.py` — `StockReport` model + `OllamaClient.generate_report()` (num_ctx, structured output)
- `apps/prometheus/src/localstock/ai/prompts.py` — `REPORT_SYSTEM_PROMPT`, `REPORT_USER_TEMPLATE`
- `apps/prometheus/src/localstock/reports/generator.py` — `build_report_prompt()`, `ReportDataBuilder.build()` (add new signal keys)

### Existing Analysis Code (Signal Sources)
- `apps/prometheus/src/localstock/analysis/technical.py` lines 296-301 — S/R anchors already in `indicator_data` dict: `pivot_point`, `support_1`, `support_2`, `resistance_1`, `resistance_2`, `nearest_support`, `nearest_resistance`
- `apps/prometheus/src/localstock/analysis/signals.py` — Phase 18 signal output formats: `compute_sector_momentum()` returns `{label, score_change, group_code}` or `None`
- `apps/prometheus/src/localstock/services/report_service.py` — how `indicator_data`, `score_data`, `ratio_data` etc. are assembled before prompt building; Phase 19 must thread candlestick/volume/sector data through the same pipeline

### Prior Phase Context
- `.planning/phases/18-signal-computation/18-CONTEXT.md` — Phase 18 signal output dict shapes (mandatory read before planning prompt injection)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StockReport.model_json_schema()` already used as Ollama `format` parameter — extending the model automatically updates the JSON schema passed to Ollama
- `_safe()` and `_safe_float()` helpers in `reports/generator.py` — reuse for None-safe rendering of new signal fields in the prompt template
- `logger.warning()` pattern already established in `report_service.py` for per-stock error isolation — use same pattern for validation warnings

### Established Patterns
- `options={"temperature": 0.3, "num_ctx": 4096}` in `generate_report()` — just change 4096 → 8192
- `REPORT_USER_TEMPLATE.format(**safe_data)` — add new keys to `safe_data` dict in `ReportDataBuilder.build()`; template picks them up automatically
- `model_validate_json(response.message.content)` — this is a single call with no try/except; the validation fallback function runs AFTER this succeeds (Pydantic parse must not fail)

### Integration Points
- `ReportDataBuilder.build()` receives separate dicts from `report_service.py` — a new `signals_data` dict param (or extend `indicator_data`) is needed for candlestick/volume/sector signals
- The 3 signal methods from Phase 18 (`compute_candlestick_patterns`, `compute_volume_divergence`, `compute_sector_momentum`) must be called in `report_service.py` before `build_report_prompt()` and their outputs passed through
- `_validate_price_levels()` should be called in `generate_report()` in `client.py` immediately after `model_validate_json()` succeeds

</code_context>

<specifics>
## Specific Ideas

- MFI-based volume divergence dict from Phase 18: `{"signal": "bullish", "value": 72.3, "indicator": "MFI"}` — format in prompt as "bullish (MFI=72.3)" for compactness
- Sector momentum from Phase 18: `{"label": "mild_inflow", "score_change": 0.5, "group_code": "BKS"}` — format in prompt as "mild_inflow (+0.5, nhóm BKS)"
- Candlestick patterns are a dict of booleans — format as comma-separated list of detected patterns (or "không phát hiện" if all False)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-prompt-schema-restructuring*
*Context gathered: 2026-04-26*
