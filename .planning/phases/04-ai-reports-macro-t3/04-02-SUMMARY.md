---
phase: 04-ai-reports-macro-t3
plan: 02
subsystem: macro-scoring
tags: [macro, crawler, impact-rules, scoring, exchange-rate]
dependency_graph:
  requires: [04-01]
  provides: [MacroCrawler, MACRO_SECTOR_IMPACT, normalize_macro_score, macro-scoring-integration]
  affects: [scoring-service, composite-scores]
tech_stack:
  added: []
  patterns: [rules-based-impact-mapping, condition-to-key-dispatch, xml-parsing]
key_files:
  created:
    - src/localstock/macro/crawler.py
    - src/localstock/macro/impact.py
    - src/localstock/macro/scorer.py
    - tests/test_macro/test_crawler.py
    - tests/test_macro/test_impact.py
    - tests/test_macro/test_scorer.py
  modified:
    - src/localstock/scoring/normalizer.py
    - src/localstock/services/scoring_service.py
    - tests/test_scoring/test_normalizer.py
    - tests/test_scoring/test_engine.py
decisions:
  - "MACRO_SECTOR_IMPACT uses 8 conditions × 20 sectors with multipliers in [-1,+1] — domain knowledge starting points for calibration"
  - "get_macro_impact aggregates across conditions and clamps to [-1,+1] to prevent extreme scores"
  - "VCB XML rate validation in 20000-30000 VND/USD range per T-04-03 threat mitigation"
  - "unittest.mock used instead of pytest-mock (not installed) — same functionality via stdlib"
  - "ScoringService fetches macro conditions once before symbol loop (shared across all stocks)"
  - "normalize_macro_score re-exported from scoring.normalizer for import consistency"
metrics:
  duration: 5min
  completed: "2026-04-16T04:08:00Z"
  tasks: 2
  files: 10
---

# Phase 04 Plan 02: Macro Crawler, Impact Rules & Scoring Integration Summary

MacroCrawler for VCB USD/VND exchange rates with XML parsing and rate validation, rules-based MACRO_SECTOR_IMPACT mapping (8 conditions × 20 sectors), normalize_macro_score() with 50-neutral baseline, and ScoringService integration using per-stock sector lookup.

## Tasks Completed

### Task 1: MacroCrawler, impact rules, and macro scorer (TDD)
- **Commit:** `422f4de` (RED), `e0fa8fd` (GREEN)
- Created `MacroCrawler.fetch_exchange_rate()` — parses VCB XML for USD/VND sell rate, computes trend vs previous value, validates rate in 20000-30000 range (T-04-03)
- Created `MacroCrawler.determine_macro_conditions()` — maps MacroIndicator trends to condition dict (e.g., `{"interest_rate": "rising", "exchange_rate": "falling"}`)
- Created `MACRO_SECTOR_IMPACT` — 8 macro conditions × 20 VN industry sectors with impact multipliers in [-1.0, +1.0], based on research domain knowledge
- Created `get_macro_impact()` — aggregates sector impact across active conditions with [-1,+1] clamping
- Created `normalize_macro_score()` — maps impact to 0-100 score (50=neutral), formula: `50 + impact*50`
- 30 tests covering crawler parsing, error handling, impact structure, known sector impacts, and scorer range

### Task 2: Integrate macro scoring into ScoringService (TDD)
- **Commit:** `e08a0be` (RED), `77c857a` (GREEN)
- Added `normalize_macro_score` re-export from `scoring.normalizer` for consistent import pattern
- Updated `ScoringService.__init__` to include `MacroRepository` and `IndustryRepository`
- Updated `ScoringService.run_full()` to fetch macro indicators and compute macro conditions once before symbol loop
- Replaced Phase 4 placeholder (`macro_score = None`) with actual macro scoring using `IndustryRepository.get_group_for_symbol()` → `normalize_macro_score()`
- macro_score=None when no macro conditions exist (graceful weight redistribution via existing engine)
- 4 new integration tests: normalizer import, macro=65 composite calculation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced pytest-mock with unittest.mock**
- **Found during:** Task 1 RED phase
- **Issue:** `mocker` fixture requires `pytest-mock` which is not installed
- **Fix:** Rewrote test_crawler.py to use `unittest.mock.AsyncMock` and `unittest.mock.patch` instead
- **Files modified:** tests/test_macro/test_crawler.py
- **Commit:** e0fa8fd

## Verification Results

- ✅ Macro module tests pass: 30 tests in `tests/test_macro/` (0.15s)
- ✅ Scoring tests pass: 28 tests in `tests/test_scoring/` (0.26s)
- ✅ Full test suite green: 222 tests pass (1.70s)
- ✅ MACRO_SECTOR_IMPACT covers 8 conditions × 20 sectors
- ✅ All multipliers in [-1.0, +1.0] range
- ✅ normalize_macro_score returns [0, 100] with 50 as neutral

## Decisions Made

1. **MACRO_SECTOR_IMPACT as domain knowledge starting points** — multipliers are reasonable estimates from Vietnamese market analysis; should be calibrated over time with actual market data (tagged [ASSUMED] in code)
2. **VCB XML rate validation 20000-30000** — mitigates T-04-03 tampering threat; rates outside this range are rejected as invalid
3. **Macro conditions fetched once per run_full() call** — conditions are the same for all stocks (macro is market-wide), avoiding redundant DB queries per symbol
4. **ScoringService uses get_group_for_symbol()** — returns group_code string directly, simpler than full mapping object; None handled by normalize_macro_score returning 50 (neutral)
5. **unittest.mock over pytest-mock** — stdlib provides same functionality; avoids adding dev dependency

## Self-Check: PASSED
