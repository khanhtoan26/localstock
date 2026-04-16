---
phase: 04-ai-reports-macro-t3
plan: 03
subsystem: reports-ai
tags: [t3-prediction, stock-report, llm-prompts, report-generation]
dependency_graph:
  requires: [04-01]
  provides: [predict_3day_trend, StockReport-model, REPORT_SYSTEM_PROMPT, generate_report, ReportDataBuilder]
  affects: [ai-client, prompts]
tech_stack:
  added: []
  patterns: [signal-aggregation, pydantic-structured-output, data-injection-prompts]
key_files:
  created:
    - src/localstock/reports/t3.py
    - src/localstock/reports/generator.py
    - tests/test_reports/test_t3.py
    - tests/test_reports/test_generator.py
  modified:
    - src/localstock/ai/client.py
    - src/localstock/ai/prompts.py
decisions:
  - "StockReport model defined in ai/client.py alongside SentimentResult — colocated with Ollama format usage"
  - "predict_3day_trend uses 5-signal aggregation with Vietnamese reason strings per signal"
  - "REPORT_USER_TEMPLATE uses emoji section headers for visual clarity to LLM"
  - "generate_report() uses temperature=0.3 for more deterministic analysis output"
  - "ReportDataBuilder None-safe with N/A and Vietnamese fallback strings"
metrics:
  duration: 5min
  completed: "2026-04-16T04:14:39Z"
  tasks: 2
  files: 6
---

# Phase 04 Plan 03: T+3 Prediction & AI Report Generation Summary

predict_3day_trend() with 5-signal aggregation (RSI/MACD/trend/support-resistance/volume), StockReport 9-field Pydantic model, REPORT_SYSTEM_PROMPT with Vietnamese instructions and T+3/swing/disclaimer, OllamaClient.generate_report() with structured JSON output, and ReportDataBuilder for prompt data assembly.

## Tasks Completed

### Task 1: T+3 prediction logic and StockReport model (TDD)
- **Commit:** `c1d80dc` (RED), `16620ec` (GREEN)
- Created `predict_3day_trend()` — aggregates 5 technical signal types: RSI momentum (recovering/overbought), MACD histogram sign, trend direction+ADX strength, support/resistance upside ratio, volume confirmation
- Direction: signals ≥ 2 → bullish, ≤ -2 → bearish, else neutral
- Confidence: |signals| ≥ 3 → high, ≥ 2 → medium, else low
- Vietnamese reason strings for each signal, always includes T+3 warning
- Handles None/missing indicator values gracefully (skip signal, neutral fallback)
- Created `StockReport` Pydantic model with 9 fields: summary, technical_analysis, fundamental_analysis, sentiment_analysis, macro_impact, long_term_suggestion, swing_trade_suggestion, recommendation, confidence
- Created `ReportDataBuilder.build()` — assembles scoring, indicator, ratio, sentiment, macro, T+3 data into flat dict with None-safe fallbacks
- Created `build_report_prompt()` — formats data dict using REPORT_USER_TEMPLATE
- Created `REPORT_USER_TEMPLATE` with emoji section headers (📊📈💰📰🌐⏰)
- 27 tests covering bullish/bearish/neutral scenarios, None handling, Vietnamese reasons, T+3 warning

### Task 2: Report prompts and OllamaClient.generate_report() (TDD)
- **Commit:** `9c0b71b` (RED), `52b83df` (GREEN)
- Added `REPORT_SYSTEM_PROMPT` — Vietnamese instructions for data-only analysis, T+3 warnings, long-term vs swing trade distinction, disclaimer (T-04-07)
- Added `StockReport` model to `ai/client.py` (colocated with SentimentResult for Ollama format usage)
- Added `OllamaClient.generate_report()` — calls chat with REPORT_SYSTEM_PROMPT, StockReport schema as format, temperature=0.3, num_ctx=4096
- Retry: 2 attempts with exponential backoff (5-30s) for ConnectError/TimeoutException/ResponseError
- Parses response via `StockReport.model_validate_json()`
- 16 additional tests: prompt content validation, StockReport importability, mock-based generate_report() verification

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- ✅ Report tests pass: 38 tests in `tests/test_reports/` (0.11s)
- ✅ AI tests pass: 5 tests in `tests/test_ai/` (0.29s)
- ✅ Full test suite green: 260 tests pass (1.86s)
- ✅ StockReport has all 9 fields with descriptions for Ollama guidance
- ✅ predict_3day_trend handles bullish/bearish/neutral/None scenarios correctly
- ✅ T+3 warning always present in prediction output
- ✅ REPORT_SYSTEM_PROMPT mentions T+3, lướt sóng, dài hạn, disclaimer
- ✅ build_report_prompt output under 3000 characters

## Decisions Made

1. **StockReport in ai/client.py** — colocated with SentimentResult since both are Ollama format schemas used by the same client. Also exported from reports/generator.py for convenience.
2. **5-signal aggregation** — RSI, MACD, trend+ADX, support/resistance ratio, volume confirmation. Each contributes ±1, aggregated for direction and confidence.
3. **Emoji section headers in template** — 📊📈💰📰🌐⏰ improve LLM's ability to parse distinct data sections in the prompt.
4. **temperature=0.3 for reports** — lower than sentiment (0.1) but still deterministic enough for consistent analysis quality. Reports need some creative phrasing.
5. **ReportDataBuilder None-safe** — all fields use fallback strings ("N/A", "Không có dữ liệu") to prevent template formatting errors with missing data.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-04-06 | Numeric data formatted as values in REPORT_USER_TEMPLATE; news text goes through sentiment_summary (pre-processed, not raw) |
| T-04-07 | REPORT_SYSTEM_PROMPT includes "không phải tư vấn đầu tư chính thức" disclaimer |

## Self-Check: PASSED
