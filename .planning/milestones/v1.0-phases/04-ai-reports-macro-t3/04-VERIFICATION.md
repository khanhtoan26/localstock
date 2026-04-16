---
phase: 04-ai-reports-macro-t3
verified: 2026-04-16T05:00:00Z
status: human_needed
score: 5/5
overrides_applied: 0
human_verification:
  - test: "Run POST /api/reports/run with Ollama running and scored stocks in DB. Read a generated report."
    expected: "Vietnamese report with all 9 sections filled, explaining WHY scores are high/low with specific numbers. long_term_suggestion and swing_trade_suggestion are distinct. swing_trade_suggestion includes T+3 warning."
    why_human: "LLM output quality, Vietnamese language fluency, and report coherence cannot be verified without running the full pipeline with a real LLM."
  - test: "Run POST /api/macro/fetch-exchange-rate against the live VCB endpoint."
    expected: "Returns JSON with status: ok and a valid USD/VND rate (20000-30000 range), trend computed if previous value exists."
    why_human: "VCB XML endpoint availability and response format can only be verified with a live network request."
---

# Phase 4: AI Reports, Macro Context & T+3 Awareness Verification Report

**Phase Goal:** Rich Vietnamese-language analysis reports that explain WHY stocks score high/low, enriched with macro-economic context and T+3 trading awareness
**Verified:** 2026-04-16T05:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LLM generates Vietnamese reports for top-ranked stocks explaining WHY each scores high/low — covering technical signals, fundamental assessment, news sentiment, and macro impact | ✓ VERIFIED | `ReportService.run_full()` gathers all 4 dimensions → `ReportDataBuilder.build()` → `build_report_prompt()` → `OllamaClient.generate_report()` → `ReportRepository.upsert()`. `StockReport` has 9 fields covering all dimensions. `REPORT_SYSTEM_PROMPT` rule 2: "Giải thích TẠI SAO điểm cao/thấp". Pipeline fully wired end-to-end. |
| 2 | Macro-economic data (SBV interest rates, USD/VND exchange rate, CPI, GDP) is collected and stored in the database | ✓ VERIFIED | `MacroIndicator` model with `indicator_type` constrained to 4 values. `MacroCrawler.fetch_exchange_rate()` parses VCB XML. `POST /api/macro` accepts manual entry with Pydantic regex validation. `MacroRepository.bulk_upsert()` stores with `uq_macro_indicator` constraint. Alembic migration creates `macro_indicators` table. |
| 3 | Reports link macro conditions to specific sector/stock impact (e.g., rising interest rates → negative for real estate, positive for banks) | ✓ VERIFIED | `MACRO_SECTOR_IMPACT`: 8 conditions × 20 sectors. Spot-check: BANKING + interest_rate rising = +0.7 (>50 score), REAL_ESTATE + interest_rate rising = -0.8 (<50 score). `get_macro_impact()` → `normalize_macro_score()` → `ScoringService` per-stock sector lookup → `ReportDataBuilder` macro_conditions in prompt → LLM `macro_impact` section. |
| 4 | Swing trade suggestions include a ≥3-day trend prediction with explicit T+3 settlement warning | ✓ VERIFIED | `predict_3day_trend()`: 5-signal aggregation (RSI/MACD/trend+ADX/support-resistance/volume), returns direction/confidence/reasons/t3_warning. `T3_WARNING` constant: "⚠️ CẢNH BÁO T+3: ...". `StockReport.swing_trade_suggestion` field: "Gợi ý lướt sóng kèm cảnh báo T+3". `REPORT_SYSTEM_PROMPT` rule 5 enforces T+3 warning in swing suggestions. |
| 5 | Long-term investment and swing trade recommendations are clearly distinguished in reports | ✓ VERIFIED | `StockReport` has separate fields: `long_term_suggestion` ("Gợi ý đầu tư dài hạn với lý do") and `swing_trade_suggestion` ("Gợi ý lướt sóng kèm cảnh báo T+3"). `REPORT_SYSTEM_PROMPT` rule 4: "Phân biệt rõ gợi ý dài hạn vs lướt sóng." These are distinct sections in the structured LLM output schema. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/localstock/db/models.py` | MacroIndicator + AnalysisReport models | ✓ VERIFIED | Both models present with all fields, constraints `uq_macro_indicator` and `uq_analysis_report` |
| `src/localstock/db/repositories/macro_repo.py` | MacroRepository CRUD | ✓ VERIFIED | `bulk_upsert`, `get_latest_by_type`, `get_all_latest` (subquery+join pattern). 72 lines, substantive. |
| `src/localstock/db/repositories/report_repo.py` | ReportRepository CRUD | ✓ VERIFIED | `upsert`, `get_latest`, `get_most_recent`, `get_by_date`, `get_by_symbol_and_date`. 78 lines, substantive. |
| `src/localstock/config.py` | Updated scoring weights + report config | ✓ VERIFIED | Weights 0.30/0.30/0.20/0.20. `report_top_n=20`, `report_max_tokens=4096`. |
| `src/localstock/macro/crawler.py` | MacroCrawler with fetch_exchange_rate() | ✓ VERIFIED | VCB XML parsing, rate validation (20000-30000), trend computation, `determine_macro_conditions()`. 125 lines. |
| `src/localstock/macro/impact.py` | MACRO_SECTOR_IMPACT rules + get_macro_impact() | ✓ VERIFIED | 8 conditions × 20 sectors, all multipliers in [-1.0, +1.0], `_CONDITION_TO_KEY` dispatch, clamped aggregation. 241 lines. |
| `src/localstock/macro/scorer.py` | normalize_macro_score() | ✓ VERIFIED | Formula `50 + impact*50`, clamped [0,100], None-safe. 37 lines. |
| `src/localstock/reports/t3.py` | predict_3day_trend() | ✓ VERIFIED | 5-signal aggregation, Vietnamese reasons, T3_WARNING constant. 128 lines. |
| `src/localstock/reports/generator.py` | ReportDataBuilder + build_report_prompt() | ✓ VERIFIED | None-safe `_safe`/`_safe_float`/`_safe_pct` helpers. Builder produces flat dict. `build_report_prompt` formats via template. 135 lines. |
| `src/localstock/ai/client.py` | OllamaClient + StockReport + generate_report() | ✓ VERIFIED | `StockReport` 9-field Pydantic model. `generate_report()` with retry(2), temperature=0.3, num_ctx=4096, structured JSON output. 212 lines. |
| `src/localstock/ai/prompts.py` | REPORT_SYSTEM_PROMPT + REPORT_USER_TEMPLATE | ✓ VERIFIED | Vietnamese instructions mentioning T+3/lướt sóng/dài hạn/disclaimer. Template with emoji headers (📊📈💰📰🌐⏰) and all data placeholders. |
| `src/localstock/services/report_service.py` | ReportService orchestrator | ✓ VERIFIED | Full pipeline: health check → top scores → macro context → per-stock data → T+3 → prompt → LLM → DB. Error isolation per stock. RECOMMENDATION_MAP. 298 lines. |
| `src/localstock/api/routes/reports.py` | Report API endpoints | ✓ VERIFIED | GET /api/reports/top, GET /api/reports/{symbol}, POST /api/reports/run with asyncio.Lock. |
| `src/localstock/api/routes/macro.py` | Macro data API endpoints | ✓ VERIFIED | GET /api/macro/latest, POST /api/macro (MacroInput validation), POST /api/macro/fetch-exchange-rate. |
| `src/localstock/api/app.py` | Updated with report + macro routes | ✓ VERIFIED | `reports_router` and `macro_router` included. 24 total routes registered. |
| `alembic/versions/add_phase4_macro_report_tables.py` | Alembic migration | ✓ VERIFIED | Creates `macro_indicators` and `analysis_reports` tables with all columns, constraints, and indexes. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `macro_repo.py` | `models.py` | `from localstock.db.models import MacroIndicator` | ✓ WIRED | Line 10 of macro_repo.py |
| `report_repo.py` | `models.py` | `from localstock.db.models import AnalysisReport` | ✓ WIRED | Line 10 of report_repo.py |
| `macro/scorer.py` | `macro/impact.py` | `from localstock.macro.impact import get_macro_impact` | ✓ WIRED | Line 7 of scorer.py, called line 33 |
| `scoring_service.py` | `macro/scorer.py` | `from localstock.macro.scorer import normalize_macro_score` | ✓ WIRED | Line 23, called line 108 |
| `ai/client.py` | `ai/prompts.py` | `from localstock.ai.prompts import REPORT_SYSTEM_PROMPT` | ✓ WIRED | Line 20, used line 201 |
| `reports/generator.py` | `ai/prompts.py` | `from localstock.ai.prompts import REPORT_USER_TEMPLATE` | ✓ WIRED | Line 7, used line 53 |
| `report_service.py` | `ai/client.py` | `self.ollama.generate_report` | ✓ WIRED | Line 15 import, line 197 call |
| `report_service.py` | `reports/t3.py` | `predict_3day_trend` | ✓ WIRED | Line 27 import, line 181 call |
| `report_service.py` | `reports/generator.py` | `ReportDataBuilder + build_report_prompt` | ✓ WIRED | Line 26 imports, lines 184-194 usage |
| `api/app.py` | `api/routes/reports.py` | `include_router(reports_router)` | ✓ WIRED | Line 9 import, line 28 include |
| `api/app.py` | `api/routes/macro.py` | `include_router(macro_router)` | ✓ WIRED | Line 8 import, line 29 include |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `report_service.py` | scores | `score_repo.get_top_ranked()` | DB query (select from composite_scores ordered by total_score) | ✓ FLOWING |
| `report_service.py` | macro_indicators | `macro_repo.get_all_latest()` | DB query (subquery+join on macro_indicators) | ✓ FLOWING |
| `report_service.py` | indicator_data | `indicator_repo.get_latest(symbol)` | DB query (select from technical_indicators) | ✓ FLOWING |
| `report_service.py` | ratio_data | `ratio_repo.get_latest(symbol)` | DB query (select from financial_ratios) | ✓ FLOWING |
| `report_service.py` | report (LLM output) | `ollama.generate_report(prompt, symbol)` | LLM call (requires running Ollama) | ⚠️ EXTERNAL — needs Ollama running |
| `api/routes/reports.py` | reports | `service.get_reports(limit)` → `report_repo.get_by_date()` | DB query (select from analysis_reports) | ✓ FLOWING |
| `api/routes/macro.py` | indicators | `repo.get_all_latest()` | DB query (select from macro_indicators) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| predict_3day_trend bullish scenario | Python: 5 signals → bullish, high confidence | direction=bullish, confidence=high, 5 reasons | ✓ PASS |
| predict_3day_trend neutral (empty input) | Python: {} → neutral, low | direction=neutral, confidence=low | ✓ PASS |
| normalize_macro_score sector impacts | Python: BANKING rising > 50, REAL_ESTATE rising < 50 | 85.0, 10.0 respectively | ✓ PASS |
| StockReport schema completeness | Python: Check 9 fields in schema | All 9 fields present | ✓ PASS |
| REPORT_SYSTEM_PROMPT content | Python: Check T+3, lướt sóng, dài hạn, disclaimer | All keywords present | ✓ PASS |
| ReportDataBuilder end-to-end | Python: Build data → build_report_prompt | 697 chars, includes VNM and T+3 | ✓ PASS |
| API routes registration | Python: Check 6 Phase 4 routes exist in app | All 6 routes found (24 total) | ✓ PASS |
| Full test suite | pytest tests/ --timeout=30 | 267 passed in 1.76s | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REPT-01 | 04-01, 04-03, 04-04 | LLM tổng hợp phân tích đa chiều thành báo cáo tiếng Việt cho từng mã, giải thích TẠI SAO điểm cao/thấp | ✓ SATISFIED | ReportService pipeline → OllamaClient.generate_report() → StockReport. REPORT_SYSTEM_PROMPT explicitly requires WHY explanation. |
| REPT-02 | 04-03, 04-04 | Báo cáo bao gồm: tín hiệu kỹ thuật, đánh giá cơ bản, sentiment tin tức, ảnh hưởng vĩ mô, và khuyến nghị tổng hợp | ✓ SATISFIED | StockReport has: technical_analysis, fundamental_analysis, sentiment_analysis, macro_impact, recommendation, confidence — all 9 fields covering required content. |
| MACR-01 | 04-01, 04-02 | Agent thu thập dữ liệu vĩ mô: lãi suất (SBV), tỷ giá USD/VND, CPI, GDP | ✓ SATISFIED | MacroIndicator model stores 4 types. MacroCrawler fetches USD/VND from VCB. POST /api/macro accepts manual entry for all 4 types with Pydantic validation. |
| MACR-02 | 04-02 | Agent phân tích tác động vĩ mô đến từng ngành/mã cổ phiếu | ✓ SATISFIED | MACRO_SECTOR_IMPACT: 8 conditions × 20 sectors. get_macro_impact() aggregates. normalize_macro_score() produces 0-100. ScoringService integrates via per-stock sector lookup. |
| T3-01 | 04-03, 04-04 | Khi gợi ý mã lướt sóng, agent dự đoán xu hướng ít nhất 3 ngày tới | ✓ SATISFIED | predict_3day_trend(): 5-signal aggregation → direction (bullish/bearish/neutral) + confidence + Vietnamese reasons. T3_WARNING always included. ReportService calls it per stock. |
| T3-02 | 04-03, 04-04 | Agent phân biệt rõ ràng giữa gợi ý đầu tư dài hạn và gợi ý lướt sóng, kèm cảnh báo T+3 | ✓ SATISFIED | StockReport.long_term_suggestion vs StockReport.swing_trade_suggestion — two separate fields. REPORT_SYSTEM_PROMPT rule 4 + 5 enforce distinction and T+3 warning in swing. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No anti-patterns found | — | — |

No TODO/FIXME/placeholder/stub patterns detected across all 16 Phase 4 files. The `return []` in report_service.py:255 is legitimate (empty reports response). The "Ollama not available" in report_service.py:91-92 is proper error handling.

### Human Verification Required

### 1. End-to-End LLM Report Quality

**Test:** With Ollama running and scored stocks in DB, run `POST /api/reports/run?top_n=3`. Then `GET /api/reports/top` and read the generated reports.
**Expected:** Each report contains all 9 sections in Vietnamese, referencing actual stock data. `summary` explains why the stock scored high/low. `technical_analysis` mentions specific RSI/MACD values. `macro_impact` links current macro conditions to the stock's sector. `swing_trade_suggestion` contains T+3 warning. `long_term_suggestion` is distinct from swing. Reports are 500-800 words per REPORT_SYSTEM_PROMPT.
**Why human:** LLM output quality, Vietnamese language fluency, factual grounding in provided data, and report coherence require human evaluation.

### 2. VCB Exchange Rate Live Fetch

**Test:** Run `POST /api/macro/fetch-exchange-rate` against the live VCB endpoint during Vietnam business hours.
**Expected:** Returns `{"status": "ok", "rate": {...}}` with a USD/VND sell rate in the 20000-30000 range.
**Why human:** Network connectivity, VCB endpoint availability, and XML response format stability can only be verified with a live request.

### Gaps Summary

No implementation gaps found. All 5 roadmap success criteria are verified at the code level. All 6 requirement IDs (REPT-01, REPT-02, MACR-01, MACR-02, T3-01, T3-02) are satisfied by the implementation. All 267 tests pass. All key artifacts exist, are substantive, are wired, and data flows through the pipeline.

Two items require human verification: (1) end-to-end LLM report quality with a running Ollama instance, and (2) live VCB exchange rate endpoint fetch. These cannot be tested without external services.

---

_Verified: 2026-04-16T05:00:00Z_
_Verifier: the agent (gsd-verifier)_
