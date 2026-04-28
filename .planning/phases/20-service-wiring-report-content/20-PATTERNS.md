# Phase 20: Service Wiring & Report Content - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 6 new/modified files + 2 new test files
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/prometheus/src/localstock/reports/generator.py` (modify — add pure computation functions) | utility | transform | Self — existing `_safe_float()`, `_format_candlestick()` | exact |
| `apps/prometheus/src/localstock/services/report_service.py` (modify — wire computations into pipeline) | service | request-response | Self — existing signal wiring at lines 179-202 | exact |
| `apps/prometheus/src/localstock/ai/prompts.py` (modify — extend REPORT_USER_TEMPLATE) | config | transform | Self — existing template sections | exact |
| `apps/prometheus/tests/test_reports/test_price_levels.py` (new — unit tests for computation functions) | test | transform | `tests/test_reports/test_generator.py` | exact |
| `apps/prometheus/tests/test_services/test_report_service.py` (modify — add integration tests) | test | request-response | Self — existing mock patterns | exact |

## Pattern Assignments

### `reports/generator.py` — New Pure Computation Functions (utility, transform)

**Analog:** Self (`reports/generator.py` lines 1-37, 39-89)

**Imports pattern** (lines 1-4):
```python
"""Report data assembly and prompt building."""
from loguru import logger
from localstock.ai.prompts import REPORT_USER_TEMPLATE
```

**Safe value helper pattern** (lines 12-36) — new functions should follow this style:
```python
def _safe_float(value, fmt: str = ".1f", fallback: str = "N/A") -> str:
    """Format float value, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):{fmt}}"
    except (ValueError, TypeError):
        return fallback
```

**Signal formatter pattern** (lines 39-89) — new `compute_*` functions should mirror this structure (private function, clear docstring, None guard → formatted output):
```python
def _format_candlestick(patterns: dict | None) -> str:
    """Format candlestick pattern dict to compact prompt string.

    Args:
        patterns: Dict from compute_candlestick_patterns() with bool values.

    Returns:
        Comma-separated detected pattern names, or "không phát hiện" if none,
        or "N/A" if input is None.
    """
    if not patterns:
        return "N/A"
    # ... processing ...
```

**ReportDataBuilder.build() pattern** (lines 239-300) — extend with new keys following established naming:
```python
return {
    # ... existing keys ...
    # S/R anchors (from indicator_data)
    "nearest_support": _safe_float(indicator_data.get("nearest_support"), ".0f"),
    "nearest_resistance": _safe_float(indicator_data.get("nearest_resistance"), ".0f"),
    # Phase 18 signals (from signals_data)
    "candlestick_patterns": _format_candlestick(
        (signals_data or {}).get("candlestick_patterns")
    ),
}
```

**Key pattern for new functions:** Pure functions that take `float | None` inputs, return computed values, and handle None gracefully. NOT methods on a class — standalone module-level functions like `_format_candlestick()`.

---

### `services/report_service.py` — Wiring Computations (service, request-response)

**Analog:** Self (`services/report_service.py` lines 126-228)

**Imports pattern** (lines 1-36):
```python
from datetime import UTC, date, datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.reports.generator import (
    ReportDataBuilder,
    build_report_prompt,
    _normalize_risk_rating,
    _validate_price_levels,
)
```

**Data gathering pattern** (lines 128-177) — new wiring should follow same style:
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

**Signal computation wiring pattern** (lines 179-202) — model for inserting price level computation:
```python
# Compute Phase 18 signals for prompt injection
signals_data = {}
prices = await self.price_repo.get_prices(symbol)
if prices:
    import pandas as pd
    ohlcv_df = pd.DataFrame([{...} for p in prices[-60:]])
    analyzer = TechnicalAnalyzer()
    signals_data["candlestick_patterns"] = analyzer.compute_candlestick_patterns(ohlcv_df)
```

**Score data assembly pattern** (lines 204-212):
```python
score_data = {
    "total": score.total_score,
    "grade": score.grade,
    "technical": score.technical_score,
    "fundamental": score.fundamental_score,
    "sentiment": score.sentiment_score,
    "macro": score.macro_score,
}
```

**Post-generation validation pattern** (lines 234-238):
```python
current_close = latest_price.close if latest_price else None
if current_close:
    report = _validate_price_levels(report, current_close)
report = _normalize_risk_rating(report)
```

**Per-stock error isolation pattern** (lines 263-266):
```python
except Exception as e:
    summary["reports_failed"] += 1
    summary["errors"].append(f"report:{symbol}:{e}")
    logger.warning(f"Report generation failed for {symbol}: {e}")
```

**CRITICAL: Dual-method pattern** — both `run_full()` (lines 70-274) and `generate_for_symbol()` (lines 276-430) have duplicated logic. ALL new wiring must be applied to BOTH methods.

---

### `ai/prompts.py` — Prompt Template Extension (config, transform)

**Analog:** Self (`ai/prompts.py` lines 41-71)

**Template section pattern** (lines 41-71) — new sections should follow this structure:
```python
REPORT_USER_TEMPLATE = """📊 THÔNG TIN CỔ PHIẾU: {symbol} - {company_name}
Ngành: {industry} | Giá đóng cửa: {close_price}
Điểm tổng hợp: {total_score}/100 (Hạng {grade})

📈 PHÂN TÍCH KỸ THUẬT (Điểm: {technical_score}/100)
RSI(14): {rsi_14} | MACD Histogram: {macd_histogram}
Xu hướng: {trend_direction} (Strength: {trend_strength})

🔔 TÍN HIỆU BỔ SUNG
Hỗ trợ gần nhất: {nearest_support} | Kháng cự gần nhất: {nearest_resistance}
...

Hãy viết báo cáo phân tích chi tiết dựa trên dữ liệu trên."""
```

**Pattern:** Each section has an emoji header, Vietnamese section title, and `{placeholder}` keys matching `ReportDataBuilder.build()` dict keys exactly.

---

### `tests/test_reports/test_price_levels.py` — New Unit Tests (test, transform)

**Analog:** `tests/test_reports/test_generator.py` (lines 1-29, 52-76)

**Test file structure pattern:**
```python
"""Tests for StockReport model, ReportDataBuilder, prompts, and OllamaClient.generate_report()."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.ai.client import StockReport
from localstock.reports.generator import (
    ReportDataBuilder,
    build_report_prompt,
    _validate_price_levels,
    _normalize_risk_rating,
)


class TestStockReportModel:
    """Test StockReport Pydantic model structure."""

    def test_has_all_required_fields(self):
        schema = StockReport.model_json_schema()
        # ...
```

**Test method naming:** `test_<function>_<scenario>` e.g., `test_entry_zone_fallback`, `test_stop_loss_none_close`

**Mock fixture pattern** (from `test_report_service.py` lines 57-103):
```python
@pytest.fixture
def mock_indicator():
    """Create a mock TechnicalIndicator object."""
    ind = MagicMock()
    ind.rsi_14 = 45.0
    ind.nearest_support = 90000.0
    ind.bb_upper = 100000.0
    ind.support_2 = 89000.0
    ind.nearest_resistance = 105000.0
    # ...
```

---

### `tests/test_services/test_report_service.py` — Integration Test Extension (test, request-response)

**Analog:** Self (existing patterns lines 1-55)

**Mock setup pattern:**
```python
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.services.report_service import ReportService


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_score():
    """Create a mock CompositeScore object."""
    score = MagicMock()
    score.symbol = "VNM"
    score.total_score = 85.0
    score.technical_score = 80.0
    score.fundamental_score = 90.0
    # ...
```

---

## Shared Patterns

### None-Safe Value Handling
**Source:** `reports/generator.py` lines 12-36
**Apply to:** All new computation functions (entry zone, stop-loss, target price, conflict detection)
```python
def _safe_float(value, fmt: str = ".1f", fallback: str = "N/A") -> str:
    """Format float value, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):{fmt}}"
    except (ValueError, TypeError):
        return fallback
```

### Pure Function Pattern (No Side Effects)
**Source:** `reports/generator.py` lines 39-89 (`_format_candlestick`, `_format_volume_divergence`, `_format_sector_momentum`)
**Apply to:** `compute_entry_zone()`, `compute_stop_loss()`, `compute_target_price()`, `detect_signal_conflict()`
- Module-level function (not class method)
- None check as first line → return None/fallback
- Clear docstring with Args/Returns
- Pure computation — no I/O, no DB calls, no logging

### ReportDataBuilder Extension
**Source:** `reports/generator.py` lines 210-300
**Apply to:** Adding new keys for price levels, conflict, catalyst data
- New keys added to the return dict in the `build()` method
- Use `_safe_float()` for numeric formatting
- Use `_safe()` for string formatting
- Each new template placeholder MUST have a matching key here

### Score Repository Delta Query
**Source:** `db/repositories/score_repo.py` lines 83-105
**Apply to:** Catalyst score delta in `report_service.py`
```python
async def get_previous_date_scores(
    self, before_date: date_type
) -> tuple[date_type | None, list[CompositeScore]]:
    """Get all scores from the most recent scoring date BEFORE before_date."""
    max_date_stmt = (
        select(func.max(CompositeScore.date))
        .where(CompositeScore.date < before_date)
    )
    max_result = await self.session.execute(max_date_stmt)
    prev_date = max_result.scalar()
    if prev_date is None:
        return None, []
    scores = await self.get_by_date(prev_date)
    return prev_date, scores
```

### Post-Generation Validation Chain
**Source:** `services/report_service.py` lines 234-238
**Apply to:** After LLM report generation, before storage
```python
# Post-generation validation (PROMPT-04)
current_close = latest_price.close if latest_price else None
if current_close:
    report = _validate_price_levels(report, current_close)
report = _normalize_risk_rating(report)
```

### Error Handling — Per-Stock Isolation
**Source:** `services/report_service.py` lines 263-266
**Apply to:** Any new async operations in the per-stock loop
```python
except Exception as e:
    summary["reports_failed"] += 1
    summary["errors"].append(f"report:{symbol}:{e}")
    logger.warning(f"Report generation failed for {symbol}: {e}")
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All files have exact analogs (self-references or sibling files in same package) |

## Metadata

**Analog search scope:** `apps/prometheus/src/localstock/`, `apps/prometheus/tests/`
**Files scanned:** 8 source files + 2 test files
**Pattern extraction date:** 2026-04-28
