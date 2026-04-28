# Phase 19: Prompt & Schema Restructuring - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 4 files to modify + 2 test files to update
**Analogs found:** 4 / 4 (all files are modifications of existing code — self-analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/prometheus/src/localstock/ai/client.py` | model + service | request-response | self (existing code) | exact |
| `apps/prometheus/src/localstock/ai/prompts.py` | config (templates) | transform | self (existing code) | exact |
| `apps/prometheus/src/localstock/reports/generator.py` | utility + service | transform | self (existing code) | exact |
| `apps/prometheus/src/localstock/services/report_service.py` | service | CRUD / orchestration | self (existing code) | exact |
| `apps/prometheus/tests/test_reports/test_generator.py` | test | — | self (existing code) | exact |
| `apps/prometheus/tests/test_ai/test_client.py` | test | — | self (existing code) | exact |

## Pattern Assignments

### `ai/client.py` — StockReport Schema Extension + num_ctx Change

**Analog:** Self (lines 40-67 for StockReport, lines 198-211 for generate_report)

**Pydantic model pattern** (lines 40-67):
```python
class StockReport(BaseModel):
    """Structured report output from LLM for stock analysis."""

    summary: str = Field(description="Tóm tắt 2-3 câu về mã cổ phiếu")
    technical_analysis: str = Field(description="Phân tích tín hiệu kỹ thuật")
    # ... 7 more required str fields
    confidence: str = Field(description="Cao / Trung bình / Thấp")
```
**What to add:** 6 new Optional fields after `confidence` (per D-03):
```python
    entry_price: Optional[float] = Field(default=None, description="Giá vào lệnh (VND, số)")
    stop_loss: Optional[float] = Field(default=None, description="Giá cắt lỗ (VND, số)")
    target_price: Optional[float] = Field(default=None, description="Giá mục tiêu (VND, số)")
    risk_rating: Optional[str] = Field(default=None, description="high / medium / low")
    catalyst: Optional[str] = Field(default=None, description="Chất xúc tác gần đây")
    signal_conflicts: Optional[str] = Field(default=None, description="Xung đột tín hiệu kỹ thuật-cơ bản")
```
**Import to add:** `from typing import Optional` (if not already imported)

**num_ctx change** (line 205):
```python
# Current:
options={"temperature": 0.3, "num_ctx": 4096},
# Change to:
options={"temperature": 0.3, "num_ctx": 8192},
```

**Post-validation call site** (after line 209):
```python
result = StockReport.model_validate_json(response.message.content)
# Insert validation + normalization here, before return
```

---

### `ai/prompts.py` — System Prompt + User Template Extension

**Analog:** Self (lines 25-62)

**System prompt pattern** (lines 25-37):
```python
REPORT_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích chứng khoán Việt Nam.
# ...rules 1-8...
8. Đây là công cụ tham khảo cá nhân, không phải tư vấn đầu tư chính thức."""
```
**What to add:** Two new rules (D-08):
```
9. Trả về entry_price, stop_loss, target_price dưới dạng số VND (không có dấu chấm phân cách hàng nghìn, ví dụ: 45200 thay vì "45.200đ").
10. risk_rating PHẢI là một trong: "high", "medium", "low" (tiếng Anh, chữ thường).
```

**User template pattern** (lines 39-62):
```python
REPORT_USER_TEMPLATE = """📊 THÔNG TIN CỔ PHIẾU: {symbol} - {company_name}
# ...sections with emoji headers...
⏰ DỰ ĐOÁN XU HƯỚNG T+3
Hướng: {t3_direction} | Độ tin cậy: {t3_confidence}
Lý do: {t3_reasons}
{t3_warning}

Hãy viết báo cáo phân tích chi tiết dựa trên dữ liệu trên."""
```
**What to add:** New `🔔 TÍN HIỆU BỔ SUNG` section BEFORE the final "Hãy viết..." line (D-05, D-07):
```python
🔔 TÍN HIỆU BỔ SUNG
Hỗ trợ gần nhất: {nearest_support} | Kháng cự gần nhất: {nearest_resistance}
Pivot: {pivot_point} | S1: {support_1} | S2: {support_2} | R1: {resistance_1} | R2: {resistance_2}
Mô hình nến: {candlestick_patterns}
Phân kỳ khối lượng (MFI): {volume_divergence}
Động lực ngành: {sector_momentum}
```

---

### `reports/generator.py` — Signal Formatting + Validation + Builder Extension

**Analog:** Self (lines 1-135)

**Safe formatting helpers pattern** (lines 10-34):
```python
def _safe(value, fallback: str = "N/A") -> str:
    """Return value as string, or fallback if None."""
    if value is None:
        return fallback
    return str(value)

def _safe_float(value, fmt: str = ".1f", fallback: str = "N/A") -> str:
    """Format float value, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):{fmt}}"
    except (ValueError, TypeError):
        return fallback
```
**New functions to add (same pattern):**
- `_format_candlestick(patterns: dict | None) -> str`
- `_format_volume_divergence(div: dict | None) -> str`
- `_format_sector_momentum(mom: dict | None) -> str`
- `_validate_price_levels(report, current_close: float) -> StockReport`
- `_normalize_risk_rating(report) -> StockReport`
- `RISK_RATING_MAP` dict constant

**ReportDataBuilder.build() pattern** (lines 64-134):
```python
def build(
    self,
    symbol: str,
    score_data: dict,
    indicator_data: dict,
    ratio_data: dict,
    sentiment_data: dict,
    macro_data: dict,
    t3_data: dict,
    stock_info: dict,
) -> dict:
    return {
        # Stock info
        "symbol": symbol,
        "company_name": _safe(stock_info.get("company_name"), "Không rõ"),
        # ... more keys using _safe / _safe_float / _safe_pct ...
    }
```
**What to modify:**
1. Add `signals_data: dict` parameter to `build()`
2. Add new keys to return dict for S/R anchors (from `indicator_data`) and signal formatting (from `signals_data`)

---

### `services/report_service.py` — Signal Data Threading

**Analog:** Self (lines 117-194 for `run_full()` per-stock loop, lines 253-357 for `generate_for_symbol()`)

**Data gathering pattern** (lines 120-131):
```python
# Get technical indicator
indicator = await self.indicator_repo.get_latest(symbol)
indicator_data = {}
if indicator:
    indicator_data = {
        col.name: getattr(indicator, col.name)
        for col in indicator.__table__.columns
        if col.name not in ("id", "computed_at")
    }
```
**What to add:** After gathering indicator_data, compute signal data:
```python
# Compute Phase 18 signals
from localstock.analysis.signals import compute_sector_momentum
# Call compute_candlestick_patterns, compute_volume_divergence, compute_sector_momentum
# Build signals_data dict and pass to ReportDataBuilder.build()
```

**Builder call pattern** (lines 184-194):
```python
data = ReportDataBuilder().build(
    symbol=symbol,
    score_data=score_data,
    indicator_data=indicator_data,
    ratio_data=ratio_data,
    sentiment_data=sentiment_data,
    macro_data=macro_data,
    t3_data=t3_data,
    stock_info=stock_info,
)
```
**What to modify:** Add `signals_data=signals_data` parameter

**Post-generation pattern** (lines 197-198):
```python
report = await self.ollama.generate_report(prompt, symbol)
# Map recommendation...
```
**What to add:** After `generate_report()`, call `_validate_price_levels()` and `_normalize_risk_rating()`

**Error logging pattern** (lines 222-225):
```python
except Exception as e:
    summary["reports_failed"] += 1
    summary["errors"].append(f"report:{symbol}:{e}")
    logger.warning(f"Report generation failed for {symbol}: {e}")
```
**Same pattern for price validation warnings** (D-11):
```python
logger.warning(f"Price validation failed for {symbol}: stop_loss={sl}, entry={ep}, target={tp}, close={close}")
```

---

### Test Files — Updates Required

**Test analog:** `tests/test_reports/test_generator.py` (lines 28-78) + `tests/test_ai/test_client.py`

**Model field count test** (test_generator.py line 49-52):
```python
def test_exactly_9_fields(self):
    schema = StockReport.model_json_schema()
    props = schema.get("properties", {})
    assert len(props) == 9
```
**Change:** `9` → `15`, add 6 new fields to `REQUIRED_FIELDS` list (lines 31-41)

**num_ctx assertion** (test_generator.py line 342):
```python
assert call_kwargs.kwargs["options"]["num_ctx"] == 4096
```
**Change:** `4096` → `8192`

**Prompt char limit** (test_generator.py line 138):
```python
assert len(result) < 3000, f"Prompt is {len(result)} chars, exceeds 3000"
```
**Change:** `3000` → `4000` (new signal section adds ~300-400 chars)

**Section markers test** (test_generator.py lines 125-132):
```python
assert "📊" in result  # Stock info
# ...
assert "⏰" in result  # T+3
```
**Add:** `assert "🔔" in result  # Tín hiệu bổ sung`

**Mock response** (test_generator.py lines 278-293):
```python
report_json = json.dumps({
    "summary": "VNM tổng quan",
    # ... 9 fields
})
```
**Add:** 6 new fields to mock response JSON (optional, since they default to None)

**New test classes to add:**
- `TestValidatePriceLevels` — price ordering, range check, partial nulling
- `TestFormatSignals` — candlestick, volume divergence, sector momentum formatting
- `TestStockReportBackwardCompat` — old JSON without new fields deserializes
- `TestNormalizeRiskRating` — Vietnamese/English/casing variants

---

## Shared Patterns

### None-Safe Formatting
**Source:** `reports/generator.py` lines 10-34
**Apply to:** All new signal formatting functions
```python
def _safe(value, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    return str(value)
```

### Per-Stock Error Isolation
**Source:** `services/report_service.py` lines 119, 222-225
**Apply to:** Signal computation calls in `run_full()` and `generate_for_symbol()`
```python
try:
    # per-stock work
except Exception as e:
    summary["reports_failed"] += 1
    summary["errors"].append(f"report:{symbol}:{e}")
    logger.warning(f"Report generation failed for {symbol}: {e}")
```

### Pydantic Optional Field Convention
**Source:** `ai/client.py` lines 40-67 (existing StockReport)
**Apply to:** 6 new fields
```python
# Pattern: Optional[T] = Field(default=None, description="...")
entry_price: Optional[float] = Field(default=None, description="Giá vào lệnh (VND, số)")
```

### Logger Warning Pattern
**Source:** `services/report_service.py` line 91
**Apply to:** Price validation fallback (D-11)
```python
logger.warning("Ollama not available — skipping report generation")
# Same pattern for:
logger.warning(f"Price validation failed for {symbol}: stop_loss={sl}, entry={ep}, target={tp}, close={close}")
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All files are modifications of existing code; no greenfield files in this phase |

## Metadata

**Analog search scope:** `apps/prometheus/src/localstock/ai/`, `apps/prometheus/src/localstock/reports/`, `apps/prometheus/src/localstock/services/`, `apps/prometheus/tests/`
**Files scanned:** 6 source + 2 test files
**Pattern extraction date:** 2026-04-26
