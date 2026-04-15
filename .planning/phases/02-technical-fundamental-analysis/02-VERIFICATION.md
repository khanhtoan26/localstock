---
phase: 02-technical-fundamental-analysis
verified: 2026-04-15T09:30:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run POST /api/analysis/run with populated database and verify indicators are computed and stored for ~400 stocks"
    expected: "Summary returns technical_success ≈ 400 and fundamental_success ≈ 400, with reasonable error counts"
    why_human: "Requires running FastAPI server with PostgreSQL containing real OHLCV and financial statement data from Phase 1"
  - test: "Query GET /api/analysis/VNM/technical and verify returned values are plausible"
    expected: "SMA/EMA/RSI/MACD/BB values are non-null and within expected ranges (RSI 0-100, SMA near price, etc.)"
    why_human: "Requires real market data in database — cannot validate numerical plausibility from unit tests alone"
  - test: "Query GET /api/industry/BANKING/averages and verify industry averages reflect real sector metrics"
    expected: "avg_pe, avg_pb, avg_roe have non-null values with stock_count > 5 for major sectors"
    why_human: "Industry average computation depends on fundamental ratios being populated for multiple stocks per sector"
---

# Phase 2: Technical & Fundamental Analysis — Verification Report

**Phase Goal:** Computed technical indicators and financial ratios for all HOSE stocks — the first two scoring dimensions
**Verified:** 2026-04-15T09:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Core technical indicators (SMA 20/50/200, EMA 12/26, RSI 14, MACD 12/26/9, Bollinger Bands 20/2) are calculated and stored for all tickers | ✓ VERIFIED | `TechnicalAnalyzer.compute_indicators()` calls `sma(20,50,200)`, `ema(12,26)`, `rsi(14)`, `macd(12,26,9)`, `bbands(20,2)` via pandas-ta. `to_indicator_row()` maps all pandas-ta column names (including corrected `BBL_20_2.0_2.0` suffix) to `TechnicalIndicator` model columns. `IndicatorRepository.bulk_upsert()` persists via `pg_insert ON CONFLICT`. `AnalysisService.run_full()` loops all HOSE symbols. 8 unit tests passing. |
| 2 | Volume analysis (average volume, relative volume, volume trend) is computed and queryable per ticker | ✓ VERIFIED | `TechnicalAnalyzer.compute_volume_analysis()` returns `avg_volume_20` (20-day SMA), `relative_volume` (current/avg), `volume_trend` (increasing/decreasing/stable via 5d vs 20d avg). Stored in `TechnicalIndicator` model columns. API endpoint `GET /api/analysis/{symbol}/technical` returns all three fields. 3 tests verify computation. |
| 3 | Each stock has an identified trend direction (uptrend/downtrend/sideways) with support and resistance levels | ✓ VERIFIED | `detect_trend()` uses 3-signal voting (MA alignment, price vs SMA50, MACD histogram) with ADX<20 sideways override. Returns `trend_direction` + `trend_strength`. `compute_pivot_points()` for PP/S1/S2/R1/R2. `find_support_resistance()` via manual peak/trough detection (no scipy). API endpoint `GET /api/analysis/{symbol}/trend` exposes all S/R fields. 9 tests covering uptrend/downtrend/sideways/ADX/pivots/peaks/S&R. |
| 4 | Key financial ratios (P/E, P/B, EPS, ROE, ROA, D/E) are calculated from financial statements for all companies | ✓ VERIFIED | `FundamentalAnalyzer.compute_ratios()` computes all 6 ratios from `FinancialStatement.data` JSONB. P/E uses `market_cap/share_holder_income` (correct for VN per decision). Edge cases handled: zero denominator → None, negative equity → None. `to_ratio_row()` maps to `FinancialRatio` model. `RatioRepository.bulk_upsert()` persists. API endpoint `GET /api/analysis/{symbol}/fundamental` returns all ratios. 13 tests covering all ratios + edge cases. |
| 5 | Revenue and profit growth rates (QoQ, YoY) are computed and each stock's ratios are compared against its ICB industry average | ✓ VERIFIED | `FundamentalAnalyzer.compute_growth()` computes QoQ/YoY for revenue and profit. `IndustryAnalyzer` defines 20 VN-specific groups with 40+ ICB3 Vietnamese name → group code mappings. `map_icb_to_group()` defaults to OTHER. `compute_industry_averages()` excludes None per metric. `AnalysisService.run_full()` seeds groups → maps stocks → computes averages. API endpoints `GET /api/industry/groups` and `GET /api/industry/{group_code}/averages`. 12 industry + 2 growth tests. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/localstock/db/models.py` | TechnicalIndicator, FinancialRatio, IndustryGroup, StockIndustryMapping, IndustryAverage models | ✓ VERIFIED | 279 lines. All 5 models present (lines 130, 190, 231, 243, 255). TechnicalIndicator has 28 indicator columns. FinancialRatio has 23 columns. Composite unique constraints for upsert. DateTime(timezone=True) for computed_at. |
| `src/localstock/db/repositories/indicator_repo.py` | Bulk upsert and query for technical_indicators | ✓ VERIFIED | 91 lines. IndicatorRepository with `bulk_upsert` (pg_insert ON CONFLICT), `get_latest`, `get_by_date_range`, `get_symbols_with_indicators`, `count_by_symbol`. |
| `src/localstock/db/repositories/ratio_repo.py` | Upsert and query for financial_ratios | ✓ VERIFIED | 102 lines. RatioRepository with `upsert_ratio`, `bulk_upsert`, `get_latest`, `get_by_period`, `get_all_for_symbol`. |
| `src/localstock/db/repositories/industry_repo.py` | CRUD for industry tables | ✓ VERIFIED | 153 lines. IndustryRepository with groups/mappings/averages CRUD including upsert. |
| `src/localstock/analysis/technical.py` | TechnicalAnalyzer class | ✓ VERIFIED | 203 lines. Individual pandas-ta calls for 11 indicators. compute_volume_analysis() with 3 metrics. to_indicator_row() mapping all pandas-ta columns including corrected BB double-suffix. |
| `src/localstock/analysis/trend.py` | Trend detection and S/R computation | ✓ VERIFIED | 199 lines. detect_trend() with 3-signal voting + ADX override. compute_pivot_points() standard formula. find_peaks_manual/find_troughs_manual with strict inequality (no scipy). find_support_resistance() nearest levels. |
| `src/localstock/analysis/fundamental.py` | FundamentalAnalyzer for ratios and growth | ✓ VERIFIED | 211 lines. compute_ratios() for P/E, P/B, EPS, ROE, ROA, D/E. compute_growth() for QoQ/YoY. compute_ttm() for trailing 12 months. to_ratio_row() mapper. |
| `src/localstock/analysis/industry.py` | IndustryAnalyzer with VN groups and ICB mapping | ✓ VERIFIED | 195 lines. 20 VN_INDUSTRY_GROUPS. 40+ ICB_TO_VN_GROUP mappings. map_icb_to_group() with OTHER fallback. compute_industry_averages() with None exclusion. |
| `src/localstock/services/analysis_service.py` | AnalysisService orchestrator | ✓ VERIFIED | 455 lines. run_full() pipeline: seed→map→technical loop→fundamental loop→industry averages. run_single() for on-demand. Per-symbol error isolation. |
| `src/localstock/api/routes/analysis.py` | 6 API endpoints | ✓ VERIFIED | 187 lines. 3 GET per-symbol (technical/fundamental/trend), 1 POST analysis/run, 2 GET industry (groups/averages). |
| `src/localstock/analysis/__init__.py` | Analysis module package init | ✓ VERIFIED | 1 line docstring. Module accessible for imports. |
| `alembic/versions/2cd114a9d495_add_analysis_tables.py` | Migration for 5 analysis tables | ✓ VERIFIED | Creates 5 tables: technical_indicators, financial_ratios, industry_groups, stock_industry_mapping, industry_averages. 6 indexes. |
| `tests/test_analysis/test_technical.py` | Unit tests for TechnicalAnalyzer | ✓ VERIFIED | 8 tests: indicator columns, warmup, RSI bounds, empty DF, volume metrics, trend, relative volume, column mapping. All passing. |
| `tests/test_analysis/test_trend.py` | Unit tests for trend detection/S&R | ✓ VERIFIED | 9 tests: uptrend/downtrend/sideways, ADX strength, pivot formula, peak detection, S/R levels. All passing. |
| `tests/test_analysis/test_fundamental.py` | Unit tests for FundamentalAnalyzer | ✓ VERIFIED | 13 tests: P/E, P/B, EPS, ROE, ROA, D/E, edge cases, growth, TTM. All passing. |
| `tests/test_analysis/test_industry.py` | Unit tests for IndustryAnalyzer | ✓ VERIFIED | 12 tests: group structure, ICB mapping, average computation. All passing. |
| `tests/test_services/test_analysis_service.py` | Unit tests for AnalysisService | ✓ VERIFIED | 3 tests: technical indicator row, short data handling, fundamental ratio row. All passing. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `analysis_service.py` | `technical.py` | `from localstock.analysis.technical import TechnicalAnalyzer` | ✓ WIRED | Line 28. Used in `__init__` (line 58), `analyze_technical_single` (line 209). |
| `analysis_service.py` | `fundamental.py` | `from localstock.analysis.fundamental import FundamentalAnalyzer` | ✓ WIRED | Line 22. Used in `__init__` (line 59), `analyze_fundamental_single` (line 279). |
| `analysis_service.py` | `industry.py` | `from localstock.analysis.industry import IndustryAnalyzer, VN_INDUSTRY_GROUPS, map_icb_to_group` | ✓ WIRED | Lines 23-27. Used in `__init__` (line 60), `map_stock_industries` (line 187), `_compute_all_industry_averages` (line 447). |
| `analysis_service.py` | `trend.py` | `from localstock.analysis.trend import detect_trend, compute_pivot_points, find_support_resistance` | ✓ WIRED | Lines 29-33. Used in `analyze_technical_single` (lines 222, 229, 238). |
| `technical.py` | `pandas_ta` | `import pandas_ta as ta` | ✓ WIRED | Line 11. Used via `result.ta.sma()`, `result.ta.ema()`, etc. in `compute_indicators` (lines 64-69). |
| `indicator_repo.py` | `models.py` | `from localstock.db.models import TechnicalIndicator` | ✓ WIRED | Line 10. Used in bulk_upsert, get_latest, get_by_date_range, etc. |
| `ratio_repo.py` | `models.py` | `from localstock.db.models import FinancialRatio` | ✓ WIRED | Line 8. Used in upsert_ratio, bulk_upsert, get_latest, etc. |
| `industry_repo.py` | `models.py` | `from localstock.db.models import IndustryAverage, IndustryGroup, StockIndustryMapping` | ✓ WIRED | Line 10. Used in all CRUD methods. |
| `app.py` | `analysis.py` | `from localstock.api.routes.analysis import router as analysis_router` + `app.include_router(analysis_router, tags=["analysis"])` | ✓ WIRED | Lines 5, 21. Router mounted in FastAPI app. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `analysis_service.py` → `_run_technical` | `ohlcv_df` | `PriceRepository.get_prices(symbol)` → DB query | Yes — `select(StockPrice)` query | ✓ FLOWING |
| `analysis_service.py` → `_run_fundamental` | `income_stmts` | `select(FinancialStatement).where(...)` → DB query | Yes — real DB query with ORDER BY/LIMIT | ✓ FLOWING |
| `analysis_service.py` → `map_stock_industries` | `stocks` | `select(Stock.symbol, Stock.industry_icb3).where(...)` → DB query | Yes — reads ICB3 from stocks table | ✓ FLOWING |
| `analysis.py` API routes | `indicator`, `ratio` | `IndicatorRepository.get_latest()`, `RatioRepository.get_latest()` → DB queries | Yes — SELECT with ORDER BY/LIMIT | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All analysis modules importable | `uv run python -c "from localstock.analysis.technical import TechnicalAnalyzer; ..."` | All imports succeed | ✓ PASS |
| VN_INDUSTRY_GROUPS has exactly 20 groups | `len(VN_INDUSTRY_GROUPS) == 20` | True | ✓ PASS |
| ICB mapping works (Ngân hàng → BANKING) | `map_icb_to_group('Ngân hàng') == 'BANKING'` | True | ✓ PASS |
| ICB mapping defaults to OTHER | `map_icb_to_group(None) == 'OTHER'` | True | ✓ PASS |
| TechnicalAnalyzer has all key methods | `hasattr(ta, 'compute_indicators/volume/to_row')` | True | ✓ PASS |
| FundamentalAnalyzer has all key methods | `hasattr(fa, 'compute_ratios/growth/ttm/to_row')` | True | ✓ PASS |
| Pivot point formula correct | `compute_pivot_points(110, 90, 100)['pivot_point'] == 100.0` | True | ✓ PASS |
| All 45 tests pass | `uv run python -m pytest tests/test_analysis/ tests/test_services/test_analysis_service.py -v` | 45 passed in 0.60s | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TECH-01 | 02-02 | Chỉ báo kỹ thuật: SMA(20,50,200), EMA(12,26), RSI(14), MACD(12,26,9), BB(20,2) | ✓ SATISFIED | `TechnicalAnalyzer.compute_indicators()` calls all 5 indicator families + Stochastic, ADX, OBV. `to_indicator_row()` maps all columns. 8 tests. |
| TECH-02 | 02-02 | Phân tích khối lượng: avg volume, relative volume, xu hướng volume | ✓ SATISFIED | `compute_volume_analysis()` returns avg_volume_20, relative_volume, volume_trend. 3 tests. |
| TECH-03 | 02-02 | Nhận diện xu hướng: uptrend/downtrend/sideways | ✓ SATISFIED | `detect_trend()` with multi-signal voting + ADX override. 4 tests. |
| TECH-04 | 02-02 | Hỗ trợ/kháng cự: pivot points + đỉnh/đáy | ✓ SATISFIED | `compute_pivot_points()` + `find_support_resistance()` via manual peak/trough. 5 tests. |
| FUND-01 | 02-03 | Chỉ số tài chính: P/E, P/B, EPS, ROE, ROA, D/E | ✓ SATISFIED | `FundamentalAnalyzer.compute_ratios()` for all 6 ratios. Edge cases handled. 9 tests. |
| FUND-02 | 02-03 | Tăng trưởng doanh thu/lợi nhuận QoQ, YoY | ✓ SATISFIED | `compute_growth()` for QoQ and YoY. `compute_ttm()` for trailing 12 months. 4 tests. |
| FUND-03 | 02-03 | So sánh chỉ số với trung bình ngành ICB | ✓ SATISFIED | 20 VN industry groups. 40+ ICB3 Vietnamese mappings. `compute_industry_averages()` with None exclusion. `_compute_all_industry_averages()` in pipeline. 12 tests. |

**Orphaned requirements:** None — all 7 requirement IDs from REQUIREMENTS.md (TECH-01..04, FUND-01..03) mapped to Phase 2 are accounted for in plans.

### Context Decisions Honored

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01: Agent tự chọn bộ chỉ báo (min: SMA, EMA, RSI, MACD, BB + optional Stoch, ADX, OBV) | ✓ HONORED | All minimum + all 3 optional indicators implemented in `compute_indicators()` |
| D-02: Dùng pandas-ta | ✓ HONORED | `import pandas_ta as ta` in technical.py. Listed as main dependency in pyproject.toml |
| D-03: Phân ngành theo đặc thù VN (không dùng ICB chuẩn quốc tế) | ✓ HONORED | 20 VN-specific groups (BANKING, REAL_ESTATE, SECURITIES, etc.) with 40+ Vietnamese ICB3 name mappings |
| D-04: Hỗ trợ/kháng cự bằng Pivot Points + đỉnh/đáy gần nhất | ✓ HONORED | `compute_pivot_points()` for PP/S1/S2/R1/R2 + `find_peaks_manual()`/`find_troughs_manual()` for nearest S/R |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/localstock/analysis/technical.py` | 136 | `return {}` | ℹ️ Info | Guard clause for empty DataFrame in `to_indicator_row()` — appropriate defensive code, not a stub |

No TODOs, FIXMEs, placeholders, or stub implementations found in any phase artifact.

### Human Verification Required

### 1. End-to-End Analysis Pipeline with Real Data

**Test:** Start FastAPI server with populated PostgreSQL (Phase 1 data). Call `POST /api/analysis/run`. Wait for completion.
**Expected:** Response shows `technical_success ≈ 400`, `fundamental_success ≈ 400` (with some expected failures for stocks missing data). Completion within reasonable time (<10 min for ~400 stocks).
**Why human:** Requires running server, populated database, and real HOSE market data. Cannot simulate full pipeline execution in static verification.

### 2. Technical Indicator Plausibility

**Test:** After analysis run, query `GET /api/analysis/VNM/technical` (or any liquid stock).
**Expected:** RSI between 0-100, SMA values near current price, MACD values reasonable, volume metrics non-null, trend_direction is one of uptrend/downtrend/sideways.
**Why human:** Unit tests verify computation logic with synthetic data. Real market data plausibility requires domain knowledge to assess.

### 3. Industry Average Meaningfulness

**Test:** Query `GET /api/industry/BANKING/averages` after full analysis run.
**Expected:** `avg_pe`, `avg_pb`, `avg_roe` are non-null with `stock_count > 5` for major sectors like BANKING, REAL_ESTATE.
**Why human:** Industry averages depend on successful fundamental ratio computation for multiple stocks per sector. Meaningful values require real financial statement data.

### Gaps Summary

No gaps found. All 5 roadmap success criteria verified through code analysis, key link tracing, data flow verification, and behavioral spot-checks. All 7 requirement IDs (TECH-01..04, FUND-01..03) are satisfied with substantive implementations. All 4 context decisions (D-01 through D-04) are honored. 45/45 unit tests pass in 0.60s. All artifacts are present, substantive (2,642 total lines across 15 files), fully wired, and data flows trace to real database queries.

Human verification needed only for runtime integration with real market data — all static checks pass.

---

_Verified: 2026-04-15T09:30:00Z_
_Verifier: the agent (gsd-verifier)_
