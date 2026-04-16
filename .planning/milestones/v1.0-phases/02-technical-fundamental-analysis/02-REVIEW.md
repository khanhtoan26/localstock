---
phase: 02-technical-fundamental-analysis
reviewed: 2026-04-15T08:25:31Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/localstock/db/models.py
  - src/localstock/db/repositories/indicator_repo.py
  - src/localstock/db/repositories/ratio_repo.py
  - src/localstock/db/repositories/industry_repo.py
  - src/localstock/analysis/__init__.py
  - src/localstock/analysis/technical.py
  - src/localstock/analysis/trend.py
  - src/localstock/analysis/fundamental.py
  - src/localstock/analysis/industry.py
  - src/localstock/services/analysis_service.py
  - src/localstock/api/routes/analysis.py
  - src/localstock/api/app.py
  - pyproject.toml
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-15T08:25:31Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed all 13 source files from Phase 02 (technical & fundamental analysis). The codebase is well-structured overall — clean separation between analysis modules, repositories, service orchestrator, and API routes. The pandas-ta integration, upsert patterns, and financial ratio computations are solid.

Two logic bugs were found: one in trend detection that biases signals toward bearish, and one in industry average computation that silently skips groups when the alphabetically-first symbol lacks data. Four info-level quality items were also identified. No security vulnerabilities or critical issues found.

Bollinger Band column names (`BBU_20_2.0_2.0` etc.) were verified correct against the actual pandas-ta 0.4.71b0 output.

## Warnings

### WR-01: MACD Histogram Zero Treated as Bearish

**File:** `src/localstock/analysis/trend.py:54-56`
**Issue:** When the MACD histogram is exactly 0.0 (MACD line crossing the signal line), the `else` branch fires and subtracts 1 from the signal score, treating a neutral crossover point as bearish. This biases trend detection toward `downtrend`/`sideways` at crossover points.

```python
# Current (buggy):
if macd_h > 0:
    signals += 1
else:
    signals -= 1
```

**Fix:**
```python
if macd_h > 0:
    signals += 1
elif macd_h < 0:
    signals -= 1
# macd_h == 0 is neutral — no signal change
```

### WR-02: Industry Averages Silently Skipped When First Symbol Lacks Data

**File:** `src/localstock/services/analysis_service.py:438-440`
**Issue:** The year/period for industry averages is fetched from `symbols[0]` (the alphabetically first symbol in the group). If that specific symbol has no financial ratio data, `first_ratio` is `None` and the entire group is skipped — even when `group_ratios` is non-empty because other symbols in the group DO have data. The comment says "first ratio with data" but the code queries a fixed symbol.

```python
# Current (buggy):
first_ratio = await self.ratio_repo.get_latest(symbols[0])
if not first_ratio:
    continue
```

**Fix:** Track year/period from an actual ratio found during the loop:
```python
# Replace the group_ratios loop and first_ratio lookup with:
group_ratios = []
reference_year = None
reference_period = None
for symbol in symbols:
    ratio = await self.ratio_repo.get_latest(symbol)
    if ratio:
        if reference_year is None:
            reference_year = ratio.year
            reference_period = ratio.period
        group_ratios.append({
            "pe_ratio": ratio.pe_ratio,
            "pb_ratio": ratio.pb_ratio,
            "roe": ratio.roe,
            "roa": ratio.roa,
            "de_ratio": ratio.de_ratio,
            "revenue_yoy": ratio.revenue_yoy,
            "profit_yoy": ratio.profit_yoy,
        })

if not group_ratios:
    continue

avg = self.industry_analyzer.compute_industry_averages(
    group_code=group_code,
    year=reference_year,
    period=reference_period,
    ratios=group_ratios,
)
await self.industry_repo.upsert_averages([avg])
```

## Info

### IN-01: Misleading Return Key Names in `compute_growth`

**File:** `src/localstock/analysis/fundamental.py:144-147, 208-209`
**Issue:** `compute_growth()` always returns keys `revenue_qoq` and `profit_qoq` regardless of whether it's computing QoQ or YoY growth. In `to_ratio_row`, the YoY mapping reads from these QoQ-named keys (line 208-209: `growth_yoy.get("revenue_qoq")`). This works correctly but is confusing — the comment `# reused key name` acknowledges the smell. Renaming to generic keys like `revenue_growth` and `profit_growth` would improve clarity.

### IN-02: No Concurrency Guard on Analysis Trigger Endpoint

**File:** `src/localstock/api/routes/analysis.py:115-125`
**Issue:** `POST /api/analysis/run` triggers a long-running full analysis for ~400 stocks with no concurrency control. Multiple simultaneous requests would run parallel full analyses, wasting resources. For a personal localhost tool this is low-risk, but a simple in-memory lock or "already running" check would prevent accidental double-triggers.

### IN-03: API Routes Return Raw Dicts Instead of Pydantic Response Models

**File:** `src/localstock/api/routes/analysis.py:26-187`
**Issue:** All six endpoints return hand-built dicts rather than Pydantic response models. This means: no auto-generated response schema in OpenAPI docs, no response validation, and manual field listing that could drift from the ORM models. Defining Pydantic `BaseModel` response schemas would improve API documentation and catch field mismatches at serialization time.

### IN-04: Redundant Index Definitions on StockPrice and TechnicalIndicator Models

**File:** `src/localstock/db/models.py:50-51,63` and `models.py:136-137,186`
**Issue:** Both `StockPrice` and `TechnicalIndicator` define individual `index=True` on the `symbol` and `date` columns AND a composite index on `(symbol, date)` in `__table_args__`. The composite index already serves queries filtering by `symbol` alone (as the leading column), making the individual `symbol` index redundant. The individual `date` index may still be useful for date-only queries. This wastes storage and slows writes slightly. Consider removing the redundant individual `index=True` on `symbol` if no queries filter by symbol without the composite index.

---

_Reviewed: 2026-04-15T08:25:31Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
