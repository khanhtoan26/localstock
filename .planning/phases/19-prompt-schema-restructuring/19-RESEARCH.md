# Phase 19: Prompt & Schema Restructuring - Research

**Researched:** 2026-04-26
**Domain:** Pydantic model extension, Ollama prompt engineering, post-generation validation
**Confidence:** HIGH

## Summary

Phase 19 restructures three files (`ai/client.py`, `ai/prompts.py`, `reports/generator.py`) to add trade guidance fields to the LLM output schema, expand the context window, inject new signal data into prompts, and validate LLM-generated price levels post-generation. All changes are purely code-level — no new dependencies, no DB migrations, no API changes.

The codebase is well-structured for this work. `StockReport.model_json_schema()` is already used as the Ollama `format` parameter, so adding Optional fields automatically updates the schema sent to the LLM. The `ReportDataBuilder.build()` + `REPORT_USER_TEMPLATE.format(**safe_data)` pattern means new prompt variables only require adding keys to the builder and placeholders to the template. The Phase 18 signal functions (`compute_candlestick_patterns`, `compute_volume_divergence`, `compute_sector_momentum`) are already implemented and return well-defined dict shapes.

**Primary recommendation:** Implement in order: (1) context window change, (2) schema extension, (3) prompt restructuring, (4) post-generation validation. Each is independently testable and the order matches dependency flow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Set `num_ctx` to 8192 in `generate_report()`. Leave `classify_sentiment()` at 4096.
- **D-03:** Add six new `Optional` fields to `StockReport`: `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, `signal_conflicts`. All default to `None`.
- **D-04:** `risk_rating` uses `Optional[str]` (not `Literal`). Post-hoc normalization maps Vietnamese/capitalized variants to canonical English lowercase.
- **D-05:** Add `🔔 TÍN HIỆU BỔ SUNG` section at end of `REPORT_USER_TEMPLATE`, before final instruction line.
- **D-06:** Render `None` signal values as `"N/A"` — never omit fields from the prompt.
- **D-07:** Specific prompt section format with Vietnamese labels for S/R anchors, candlestick patterns, volume divergence, sector momentum.
- **D-08:** Update `REPORT_SYSTEM_PROMPT` with instructions for price fields as numeric VND and `risk_rating` as English lowercase.
- **D-09:** Add `_validate_price_levels(report, current_close)` in `reports/generator.py` with two checks: price ordering and ±30% range.
- **D-10:** Fallback nulls only price fields; keep `risk_rating`, `catalyst`, `signal_conflicts`.
- **D-11:** Log warning when validation nulls price fields.

### Claude's Discretion
- String formatting of new prompt section (spacing, Vietnamese labels vs English)
- Candlestick patterns dict serialization (e.g., "doji, hammer" or "patterns detected: doji")
- Volume divergence dict serialization (e.g., "bullish (MFI=72.3)")
- Sector momentum dict serialization (e.g., "mild_inflow (+0.5, nhóm BKS)")

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROMPT-01 | Ollama context window raised from 4096 to 6144+ tokens | Direct code change in `generate_report()` options dict; verified current value is 4096 at line 205 of `client.py` |
| PROMPT-02 | StockReport extended with 6 Optional fields for backward compat | Pydantic v2.13.1 Optional[T] = None verified: generates `anyOf` schema, backward-compatible deserialization confirmed |
| PROMPT-03 | Prompts inject S/R anchors, candlestick, volume divergence, sector momentum | Phase 18 signal functions return well-defined dicts; S/R values already in `indicator_data`; `ReportDataBuilder.build()` pattern supports adding new keys |
| PROMPT-04 | Post-generation validation: price ordering + ±30% range check | New `_validate_price_levels()` function; called after `model_validate_json()` succeeds |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema extension (StockReport) | API / Backend | — | Pydantic model in `ai/client.py` defines LLM output contract |
| Context window config | API / Backend | — | Ollama client option, server-side only |
| Prompt restructuring | API / Backend | — | Template strings formatted server-side before LLM call |
| Post-generation validation | API / Backend | — | Price validation runs server-side after LLM response |
| Signal data threading | API / Backend | — | `report_service.py` gathers data, passes to `ReportDataBuilder` |

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.13.1 | Schema definition + JSON validation | Already used for StockReport; `model_json_schema()` feeds Ollama `format` param |
| ollama (Python) | 0.6.1 | LLM client | Already used; `num_ctx` is an option in `chat()` call |
| loguru | 0.7+ | Logging | Already used for per-stock error isolation pattern |

[VERIFIED: `uv pip show pydantic` → 2.13.1, `uv pip show ollama` → 0.6.1]

**No new dependencies needed.** All changes use existing packages.

## Architecture Patterns

### System Architecture Diagram

```
report_service.py                    generator.py                    client.py
┌─────────────────┐                 ┌──────────────────┐           ┌────────────────────┐
│ Gather data:    │                 │ ReportDataBuilder │           │ generate_report()  │
│ - indicator_data│──signals_data──▶│ .build()          │──prompt──▶│ num_ctx=8192       │
│ - candlestick   │                 │ + format signals  │           │ StockReport schema │
│ - volume_div    │                 │ + REPORT_USER_    │           │ (15 fields)        │
│ - sector_mom    │                 │   TEMPLATE.format │           │                    │
└─────────────────┘                 └──────────────────┘           │ model_validate_json│
                                                                    │        │           │
                                                                    │   ┌────▼────┐      │
                                                                    │   │validate │      │
                                                                    │   │price    │      │
                                                                    │   │levels   │      │
                                                                    │   └────┬────┘      │
                                                                    │        │           │
                                                                    │   StockReport     │
                                                                    │   (validated)     │
                                                                    └────────────────────┘
```

### Data Flow: Signal → Prompt → LLM → Validation

1. **`report_service.py`** calls Phase 18 signal functions, builds `signals_data` dict
2. **`ReportDataBuilder.build()`** receives `signals_data`, formats into prompt-safe strings
3. **`REPORT_USER_TEMPLATE`** includes `🔔 TÍN HIỆU BỔ SUNG` section with formatted signals
4. **`generate_report()`** sends prompt to Ollama with `num_ctx=8192` and 15-field schema
5. **`_validate_price_levels()`** checks price ordering and range after LLM response
6. **Return** StockReport with potentially nulled price fields

### Pattern 1: Optional Field Extension (Backward Compatible)
**What:** Add `Optional[T] = None` fields to existing Pydantic model
**When to use:** When extending LLM output schema without breaking existing serialized data

```python
# Verified: Pydantic 2.13.1 behavior
class StockReport(BaseModel):
    summary: str = Field(description="...")  # existing required field
    entry_price: Optional[float] = Field(default=None, description="Giá vào lệnh (VND)")
```

**Key behavior verified** [VERIFIED: local Python test]:
- `model_json_schema()` generates `anyOf: [{type: number}, {type: null}]` for Optional fields
- `model_validate_json('{"summary": "old"}')` succeeds — old data without new fields works
- New fields appear in schema sent to Ollama via `format` parameter automatically

### Pattern 2: Post-Generation Validation (Non-Crashing)
**What:** Validate LLM output after Pydantic parse succeeds, null invalid fields instead of raising
**When to use:** When LLM outputs may be structurally valid JSON but semantically wrong

```python
def _validate_price_levels(report: StockReport, current_close: float) -> StockReport:
    """Null price fields if ordering or range violated."""
    ep, sl, tp = report.entry_price, report.stop_loss, report.target_price
    
    if ep is not None and sl is not None and tp is not None:
        if not (sl < ep < tp):
            report.entry_price = report.stop_loss = report.target_price = None
            return report
    
    # Range check: each non-None price within ±30% of close
    for field in ['entry_price', 'stop_loss', 'target_price']:
        val = getattr(report, field)
        if val is not None and abs(val - current_close) / current_close > 0.30:
            report.entry_price = report.stop_loss = report.target_price = None
            return report
    
    return report
```

### Pattern 3: Signal Serialization for Prompt
**What:** Convert Phase 18 dict outputs to compact prompt strings
**When to use:** Formatting structured data for LLM consumption

```python
# Candlestick: {"doji": True, "hammer": False, ...} → "doji" or "không phát hiện"
def _format_candlestick(patterns: dict | None) -> str:
    if not patterns:
        return "N/A"
    detected = [k for k, v in patterns.items() if v and k != "engulfing_direction"]
    if not detected:
        return "không phát hiện"
    # Include engulfing direction if detected
    if patterns.get("engulfing_detected") and patterns.get("engulfing_direction"):
        detected = [d if d != "engulfing_detected" else f"engulfing ({patterns['engulfing_direction']})" for d in detected]
    return ", ".join(detected)

# Volume divergence: {"signal": "bullish", "value": 72.3, "indicator": "MFI"} → "bullish (MFI=72.3)"
def _format_volume_divergence(div: dict | None) -> str:
    if not div:
        return "N/A"
    return f"{div['signal']} ({div['indicator']}={div['value']})"

# Sector momentum: {"label": "mild_inflow", "score_change": 0.5, "group_code": "BKS"} → "mild_inflow (+0.5, nhóm BKS)"
def _format_sector_momentum(mom: dict | None) -> str:
    if not mom:
        return "N/A"
    sign = "+" if mom["score_change"] >= 0 else ""
    return f"{mom['label']} ({sign}{mom['score_change']}, nhóm {mom['group_code']})"
```

### Anti-Patterns to Avoid
- **Using `Literal` for LLM string outputs:** LLMs produce unpredictable casing and language variants. Use `Optional[str]` with post-hoc normalization instead of `Literal["high","medium","low"]` which causes `ValidationError` on Vietnamese output like "Cao".
- **Omitting None fields from prompt:** If a field is absent, the LLM doesn't know it exists and may hallucinate. Always render `"N/A"` per D-06.
- **Raising exceptions on validation failure:** Price validation should null fields gracefully, not crash the entire report pipeline. Per D-10, non-price fields remain valid.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema for Ollama | Manual schema dict | `StockReport.model_json_schema()` | Already established pattern; auto-updates when model changes |
| None-safe formatting | Manual `if x is not None` everywhere | `_safe()` / `_safe_float()` helpers | Already exist in `generator.py`; reuse for new signal fields |
| Retry logic | Custom retry loop | `@retry` from tenacity | Already on `generate_report()` with proper config |

## Common Pitfalls

### Pitfall 1: Pydantic `anyOf` Schema with Ollama Structured Output
**What goes wrong:** Pydantic v2 generates `anyOf: [{type: number}, {type: null}]` for `Optional[float]`. Some older Ollama versions or models may not handle `anyOf` correctly in structured output mode, producing malformed JSON.
**Why it happens:** JSON Schema `anyOf` is more complex than simple `{type: number}`. The LLM's constrained generation may struggle with union types.
**How to avoid:** Test with actual Ollama + Qwen2.5 after implementation. If `anyOf` causes issues, override `model_json_schema()` to simplify. The current codebase uses Ollama 0.6.1 which should handle this. [ASSUMED — needs empirical validation]
**Warning signs:** `ValidationError` on `model_validate_json()` despite LLM appearing to produce valid JSON; null fields always appearing as `0` or empty string instead of `null`.

### Pitfall 2: Existing Test Assertions Break
**What goes wrong:** `test_exactly_9_fields` asserts `len(props) == 9`. Adding 6 fields changes this to 15.
**Why it happens:** Hard-coded field count in test.
**How to avoid:** Update the test to assert `len(props) == 15` and add the 6 new fields to `REQUIRED_FIELDS` list (but as Optional, they won't be in `required` — need to check `properties` keys instead).
**Warning signs:** Test `test_exactly_9_fields` fails immediately.

### Pitfall 3: `num_ctx` Test Assertion
**What goes wrong:** `test_calls_chat_with_correct_params` asserts `num_ctx == 4096` (line 342 of test file). This will fail after changing to 8192.
**Why it happens:** Existing test verifies the old value.
**How to avoid:** Update assertion to `num_ctx == 8192`.

### Pitfall 4: `build_report_prompt` KeyError on New Placeholders
**What goes wrong:** Adding `{nearest_support}` etc. to `REPORT_USER_TEMPLATE` without adding corresponding keys to `ReportDataBuilder.build()` causes `KeyError` at runtime.
**Why it happens:** Template and data builder must stay in sync.
**How to avoid:** Add all new placeholder keys to `build()` return dict BEFORE updating the template. Test `build_report_prompt` with sample data to catch missing keys.

### Pitfall 5: Prompt Character Budget
**What goes wrong:** Existing test `test_under_3000_chars` may fail after adding the `🔔 TÍN HIỆU BỔ SUNG` section.
**Why it happens:** New section adds ~300-400 chars to the prompt.
**How to avoid:** Raise the assertion threshold (e.g., to 4000 chars). With `num_ctx=8192`, the prompt budget is much larger.

### Pitfall 6: `report_service.py` Data Threading
**What goes wrong:** Phase 18 signal functions exist but are NOT called in `report_service.py`. Forgetting to add these calls means signals are never computed for report generation.
**Why it happens:** Signal functions were added in Phase 18 but were only tested in isolation, not wired into the report pipeline.
**How to avoid:** Add calls to `compute_candlestick_patterns()`, `compute_volume_divergence()`, `compute_sector_momentum()` in `report_service.py`'s per-stock loop, then pass results through to `ReportDataBuilder.build()`.

### Pitfall 7: Validation Mutability
**What goes wrong:** `StockReport` is a Pydantic model. By default in Pydantic v2, models are **immutable** (frozen). Setting `report.entry_price = None` raises `ValidationError`.
**Why it happens:** Pydantic v2 defaults to `model_config = ConfigDict(frozen=False)` actually — BUT if someone adds `frozen=True`, mutation fails.
**How to avoid:** Check current StockReport config. Current code has no `model_config`, so mutation works by default. Alternatively, use `report.model_copy(update={"entry_price": None, ...})` for immutable-safe approach.
**Warning signs:** `ValidationError: "StockReport" is immutable` at runtime.

## Code Examples

### Example 1: Extended StockReport Model
```python
# Source: Current ai/client.py + D-03/D-04 decisions
class StockReport(BaseModel):
    # Existing 9 fields (unchanged)
    summary: str = Field(description="Tóm tắt 2-3 câu về mã cổ phiếu")
    technical_analysis: str = Field(description="Phân tích tín hiệu kỹ thuật")
    fundamental_analysis: str = Field(description="Đánh giá chỉ số cơ bản")
    sentiment_analysis: str = Field(description="Phân tích tâm lý thị trường từ tin tức")
    macro_impact: str = Field(description="Ảnh hưởng bối cảnh vĩ mô lên ngành/cổ phiếu")
    long_term_suggestion: str = Field(description="Gợi ý đầu tư dài hạn với lý do")
    swing_trade_suggestion: str = Field(description="Gợi ý lướt sóng kèm cảnh báo T+3")
    recommendation: str = Field(description="Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh")
    confidence: str = Field(description="Cao / Trung bình / Thấp")

    # New 6 fields (PROMPT-02, D-03)
    entry_price: Optional[float] = Field(default=None, description="Giá vào lệnh (VND, số)")
    stop_loss: Optional[float] = Field(default=None, description="Giá cắt lỗ (VND, số)")
    target_price: Optional[float] = Field(default=None, description="Giá mục tiêu (VND, số)")
    risk_rating: Optional[str] = Field(default=None, description="high / medium / low")
    catalyst: Optional[str] = Field(default=None, description="Chất xúc tác gần đây")
    signal_conflicts: Optional[str] = Field(default=None, description="Xung đột tín hiệu kỹ thuật-cơ bản")
```

### Example 2: Updated REPORT_SYSTEM_PROMPT Addition (D-08)
```python
# Append to existing REPORT_SYSTEM_PROMPT rules:
"""
9. Trả về entry_price, stop_loss, target_price dưới dạng số VND (không có dấu chấm phân cách hàng nghìn, ví dụ: 45200 thay vì "45.200đ").
10. risk_rating PHẢI là một trong: "high", "medium", "low" (tiếng Anh, chữ thường).
"""
```

### Example 3: Updated REPORT_USER_TEMPLATE Section (D-05, D-07)
```python
# Insert before "Hãy viết báo cáo phân tích chi tiết..."
"""
🔔 TÍN HIỆU BỔ SUNG
Hỗ trợ gần nhất: {nearest_support} | Kháng cự gần nhất: {nearest_resistance}
Pivot: {pivot_point} | S1: {support_1} | S2: {support_2} | R1: {resistance_1} | R2: {resistance_2}
Mô hình nến: {candlestick_patterns}
Phân kỳ khối lượng (MFI): {volume_divergence}
Động lực ngành: {sector_momentum}
"""
```

### Example 4: ReportDataBuilder New Keys
```python
# Add to ReportDataBuilder.build() return dict:
# S/R anchors from indicator_data (already computed by technical.py)
"nearest_support": _safe_float(indicator_data.get("nearest_support"), ".0f"),
"nearest_resistance": _safe_float(indicator_data.get("nearest_resistance"), ".0f"),
"pivot_point": _safe_float(indicator_data.get("pivot_point"), ".0f"),
"support_1": _safe_float(indicator_data.get("support_1"), ".0f"),
"support_2": _safe_float(indicator_data.get("support_2"), ".0f"),
"resistance_1": _safe_float(indicator_data.get("resistance_1"), ".0f"),
"resistance_2": _safe_float(indicator_data.get("resistance_2"), ".0f"),
# New signals (formatted by helper functions)
"candlestick_patterns": _format_candlestick(signals_data.get("candlestick")),
"volume_divergence": _format_volume_divergence(signals_data.get("volume_divergence")),
"sector_momentum": _format_sector_momentum(signals_data.get("sector_momentum")),
```

### Example 5: risk_rating Normalization (D-04)
```python
RISK_RATING_MAP = {
    "high": "high", "medium": "medium", "low": "low",
    "High": "high", "Medium": "medium", "Low": "low",
    "HIGH": "high", "MEDIUM": "medium", "LOW": "low",
    "cao": "high", "trung bình": "medium", "thấp": "low",
    "Cao": "high", "Trung bình": "medium", "Thấp": "low",
}

def _normalize_risk_rating(report: StockReport) -> StockReport:
    if report.risk_rating is not None:
        report.risk_rating = RISK_RATING_MAP.get(report.risk_rating, report.risk_rating)
    return report
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 9-field StockReport | 15-field StockReport with trade guidance | Phase 19 | LLM outputs actionable entry/exit/risk data |
| 4096 num_ctx | 8192 num_ctx for reports | Phase 19 | Room for expanded prompt with signal data |
| No post-generation validation | Price level validation | Phase 19 | Prevents hallucinated/nonsensical prices |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ollama 0.6.1 handles `anyOf` in JSON schema for structured output | Pitfall 1 | LLM may output `0` or `""` instead of `null` for Optional fields; workaround: override schema |
| A2 | StockReport is mutable by default (no `frozen=True` config) | Pitfall 7 | Validation function can't set fields to None; workaround: use `model_copy(update=...)` |

**A2 verified:** Checked current `StockReport` class — no `model_config` override, Pydantic v2 defaults to mutable. [VERIFIED: codebase inspection]

## Open Questions

1. **Ollama `anyOf` handling**
   - What we know: Pydantic v2 generates `anyOf` for `Optional[float]`. Ollama 0.6.1 uses JSON Schema for constrained generation.
   - What's unclear: Whether Qwen2.5 14B Q4_K_M correctly produces `null` values via `anyOf` schema. May always output `0.0` instead of `null`.
   - Recommendation: Test empirically after implementation. If fails, use `json_schema_extra` or manual schema override to simplify Optional representation.

2. **Signal data availability in `report_service.py`**
   - What we know: `compute_candlestick_patterns()` and `compute_volume_divergence()` require the OHLCV DataFrame, which is NOT currently loaded in `report_service.py` (it only loads the latest indicator row).
   - What's unclear: Whether to load the full OHLCV DataFrame in report_service or pre-compute and store candlestick/volume signals in the indicator row.
   - Recommendation: Pre-compute signals during the indicator computation step and store results. Then `report_service.py` reads them from `indicator_data` dict. **OR** the simplest approach: call signal functions in `report_service.py` after loading price history (which `price_repo` already provides). Check if price history is already loaded.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd apps/prometheus && python -m pytest tests/test_reports/test_generator.py tests/test_ai/test_client.py -q` |
| Full suite command | `cd apps/prometheus && python -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROMPT-01 | num_ctx=8192 in generate_report | unit | `pytest tests/test_ai/test_client.py -k "test_calls_chat_with_correct_params" -x` | ✅ (update assertion 4096→8192) |
| PROMPT-02 | StockReport has 15 fields, new fields Optional with None default | unit | `pytest tests/test_reports/test_generator.py -k "TestStockReportModel" -x` | ✅ (update count 9→15, add new fields) |
| PROMPT-02 | Backward compat: old JSON without new fields deserializes | unit | `pytest tests/test_reports/test_generator.py -k "backward" -x` | ❌ Wave 0 |
| PROMPT-03 | Prompt contains signal section with all named variables | unit | `pytest tests/test_reports/test_generator.py -k "test_contains_section_markers" -x` | ✅ (add 🔔 check) |
| PROMPT-03 | ReportDataBuilder includes signal keys | unit | `pytest tests/test_reports/test_generator.py -k "TestReportDataBuilder" -x` | ✅ (extend) |
| PROMPT-04 | Validation nulls prices when stop_loss >= entry_price | unit | `pytest tests/test_reports/test_generator.py -k "validate_price" -x` | ❌ Wave 0 |
| PROMPT-04 | Validation nulls prices outside ±30% of close | unit | `pytest tests/test_reports/test_generator.py -k "validate_price" -x` | ❌ Wave 0 |
| PROMPT-04 | Validation keeps non-price fields intact | unit | `pytest tests/test_reports/test_generator.py -k "validate_price" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/prometheus && python -m pytest tests/test_reports/test_generator.py tests/test_ai/test_client.py -q`
- **Per wave merge:** `cd apps/prometheus && python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reports/test_generator.py::TestStockReportBackwardCompat` — covers PROMPT-02 backward compat
- [ ] `tests/test_reports/test_generator.py::TestValidatePriceLevels` — covers PROMPT-04 (ordering, range, partial null)
- [ ] `tests/test_reports/test_generator.py::TestFormatSignals` — covers signal serialization helpers
- [ ] Update `test_exactly_9_fields` → `test_exactly_15_fields`
- [ ] Update `test_calls_chat_with_correct_params` assertion: `num_ctx == 8192`
- [ ] Update `test_under_3000_chars` threshold to ~4000

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Post-generation price validation; Pydantic schema enforcement |
| V6 Cryptography | no | — |

### Known Threat Patterns for LLM Output

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM price hallucination | Tampering | `_validate_price_levels()` rejects out-of-range prices |
| Prompt injection via signal data | Tampering | Signal data is numeric/dict — no user-controlled text injected into prompt |
| Model output bypass (non-JSON) | Tampering | Pydantic `model_validate_json()` rejects malformed output; tenacity retries |

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `ai/client.py`, `ai/prompts.py`, `reports/generator.py`, `analysis/technical.py`, `analysis/signals.py`, `services/report_service.py` — current code structure and patterns
- Local Python verification: Pydantic v2.13.1 `Optional[T]` schema generation, backward compatibility, mutation behavior
- Existing test suite: 29 tests passing in `test_reports/test_generator.py` + `test_ai/test_client.py`

### Secondary (MEDIUM confidence)
- Phase 18 signal function signatures: `compute_candlestick_patterns()` returns `{doji, inside_bar, hammer, shooting_star, engulfing_detected, engulfing_direction}`, `compute_volume_divergence()` returns `{signal, value, indicator}` or None, `compute_sector_momentum()` returns `{label, score_change, group_code}` or None

### Tertiary (LOW confidence)
- Ollama `anyOf` schema handling — not verified against actual LLM; based on assumption that Ollama 0.6.1 supports JSON Schema union types

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, verified installed versions
- Architecture: HIGH — all files inspected, patterns understood, data flow mapped
- Pitfalls: HIGH — identified 7 concrete pitfalls from code inspection and test analysis

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (stable — no external dependency changes expected)
