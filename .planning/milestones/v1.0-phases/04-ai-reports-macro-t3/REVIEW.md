---
phase: 04-ai-reports-macro-t3
reviewed: 2026-04-16T04:25:43Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - src/localstock/macro/__init__.py
  - src/localstock/macro/crawler.py
  - src/localstock/macro/impact.py
  - src/localstock/macro/scorer.py
  - src/localstock/reports/__init__.py
  - src/localstock/reports/t3.py
  - src/localstock/reports/generator.py
  - src/localstock/services/report_service.py
  - src/localstock/api/routes/reports.py
  - src/localstock/api/routes/macro.py
  - src/localstock/db/repositories/macro_repo.py
  - src/localstock/db/repositories/report_repo.py
  - src/localstock/db/models.py
  - src/localstock/config.py
  - src/localstock/ai/client.py
  - src/localstock/ai/prompts.py
  - src/localstock/scoring/normalizer.py
  - src/localstock/services/scoring_service.py
  - src/localstock/api/app.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-16T04:25:43Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 04 adds macro-economic scoring, T+3 trend prediction, and AI report generation. The code is generally well-structured with good error isolation, input validation, and defensive programming. However, there is a **critical data mapping bug** in the exchange rate macro impact path that silently causes all exchange rate macro impacts to evaluate to zero. There are also several logic bugs in the report service fallback path and a bullish bias in the T+3 prediction model.

## Critical Issues

### CR-01: Exchange Rate Trend-to-Impact Mapping Mismatch — Macro Impact Always Zero

**File:** `src/localstock/macro/impact.py:196-201` / `src/localstock/macro/crawler.py:69-76`
**Issue:** The macro crawler produces trend values `"rising"` / `"falling"` for exchange rate (lines 71-76 in `crawler.py`). The manual entry endpoint in `macro.py:88-93` also uses `"rising"` / `"falling"`. However, the `_CONDITION_TO_KEY` mapping in `impact.py:199` expects `"weakening"` / `"strengthening"`:

```python
# impact.py:199 — expects "weakening"/"strengthening"
"exchange_rate": {"weakening": "vnd_weakening", "strengthening": "vnd_strengthening"},
```

When `get_macro_impact()` is called, `key_map.get("rising")` returns `None`, so the exchange rate condition is silently skipped. **Exchange rate never contributes to macro scoring.** This defeats one of the 4 macro dimensions.

**Fix:** Update `_CONDITION_TO_KEY` to match the trend values actually produced by the crawler and manual entry:

```python
_CONDITION_TO_KEY: dict[str, dict[str, str]] = {
    "interest_rate": {"rising": "interest_rate_rising", "falling": "interest_rate_falling"},
    "exchange_rate": {"rising": "vnd_weakening", "falling": "vnd_strengthening"},
    "cpi": {"rising": "cpi_rising", "falling": "cpi_falling"},
    "gdp": {"growing": "gdp_growing", "slowing": "gdp_slowing"},
}
```

This maps USD/VND rate "rising" → VND weakening (correct semantics per the comment on `crawler.py:72`).

## Warnings

### WR-01: Report Fallback Path Broken — `get_latest(None)` Never Matches

**File:** `src/localstock/services/report_service.py:250`
**Issue:** When no reports exist for today, the fallback calls `self.report_repo.get_latest(None)`. The `ReportRepository.get_latest()` method (report_repo.py:35) has signature `get_latest(self, symbol: str)` and builds a query `.where(AnalysisReport.symbol == None)`, which generates SQL `WHERE symbol IS NULL`. Since `symbol` is a non-nullable column in the `AnalysisReport` model, this query will **never return results**. The fallback to display the most recent date's reports is dead code.

**Fix:** Add a dedicated method to `ReportRepository` for getting the most recent report across all symbols:

```python
# In report_repo.py
async def get_most_recent(self) -> AnalysisReport | None:
    """Get the single most recent report across all symbols."""
    stmt = (
        select(AnalysisReport)
        .order_by(AnalysisReport.generated_at.desc())
        .limit(1)
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

Then in `report_service.py:250`:
```python
latest = await self.report_repo.get_most_recent()
```

### WR-02: Inconsistent Error Keys in Report Summary Dict

**File:** `src/localstock/services/report_service.py:92,99`
**Issue:** The summary dict initializes `"errors": []` (line 85, plural) for per-stock failures, but early-exit paths set `summary["error"]` (singular, lines 92 and 99). API consumers will receive different error shapes depending on the failure mode — `{"error": "..."}` for early exits vs `{"errors": [...]}` for partial failures. The `"error"` key is also never consumed downstream, creating silent data loss.

**Fix:** Use the existing `errors` list consistently:

```python
# Line 92
summary["errors"].append("Ollama not available")

# Line 99
summary["errors"].append("No scored stocks available")
```

### WR-03: T+3 Prediction Has Bullish Bias — Volume Signal Is Asymmetric

**File:** `src/localstock/reports/t3.py:92-98`
**Issue:** The volume confirmation signal (signal #5) only contributes `+1` for bullish confirmation (high volume + uptrend) but never `-1` for bearish confirmation (high volume + downtrend). This creates an asymmetric scoring range: maximum bullish = +5, maximum bearish = -4. Over a large portfolio, this systematically skews predictions toward "bullish" and inflates confidence.

**Fix:** Add the bearish volume signal:

```python
# 5. Volume confirmation
rel_vol = indicator_data.get("relative_volume")
if rel_vol is not None and trend is not None:
    if rel_vol > 1.5 and trend == "uptrend":
        signals += 1
        reasons.append(
            f"Khối lượng giao dịch cao (relative_volume = {rel_vol:.1f}x) xác nhận xu hướng tăng"
        )
    elif rel_vol > 1.5 and trend == "downtrend":
        signals -= 1
        reasons.append(
            f"Khối lượng giao dịch cao (relative_volume = {rel_vol:.1f}x) xác nhận xu hướng giảm"
        )
```

## Info

### IN-01: Duplicate `StockReport` Pydantic Model — Dead Code in generator.py

**File:** `src/localstock/reports/generator.py:15-41`
**Issue:** `StockReport` is defined in both `reports/generator.py` (lines 15-41) and `ai/client.py` (lines 40-66) with identical fields. The version in `generator.py` is never imported or used anywhere — `OllamaClient.generate_report()` uses the `ai/client.py` version. The `generator.py` copy is dead code.

**Fix:** Remove the `StockReport` class from `generator.py` entirely (lines 15-41). If needed for type reference, import from `ai.client`.

### IN-02: Model Comment Contradicts Actual Trend Values

**File:** `src/localstock/db/models.py:365`
**Issue:** The `MacroIndicator.trend` column comment says `'increasing', 'decreasing', 'stable'` but all code that writes to this field (`crawler.py`, `macro.py` routes) uses `'rising'`, `'falling'`, `'stable'`. The comment is misleading for future developers.

**Fix:** Update the column comment:

```python
trend: Mapped[str | None] = mapped_column(
    String(20), nullable=True
)  # 'rising', 'falling', 'stable'
```

### IN-03: `_report_lock` Only Protects Single-Process Deployment

**File:** `src/localstock/api/routes/reports.py:18`
**Issue:** `_report_lock = asyncio.Lock()` is a per-process lock. If the app is deployed with multiple Uvicorn workers (`--workers N`), each worker has its own lock instance, and concurrent report generation can occur across workers. This is fine for the current single-machine personal tool use case, but worth documenting as a limitation if multi-worker deployment is ever used.

**Fix:** Add a comment documenting the limitation:

```python
# NOTE: This lock only prevents concurrent generation within a single worker process.
# For multi-worker deployment, use a database-level advisory lock instead.
_report_lock = asyncio.Lock()
```

---

_Reviewed: 2026-04-16T04:25:43Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
