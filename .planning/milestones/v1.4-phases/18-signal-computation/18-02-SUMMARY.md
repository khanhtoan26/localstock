---
phase: 18-signal-computation
plan: "02"
subsystem: analysis
tags: [candlestick-patterns, technical-analysis, pandas-ta, signal-computation, tdd]
dependency_graph:
  requires: [18-01]
  provides: [compute_candlestick_patterns, _is_hammer, _is_shooting_star, _detect_engulfing]
  affects: [phase-19-llm-prompt-injection]
tech_stack:
  added: []
  patterns: [pure-ohlc-math, pandas-ta-native-cdl, module-level-helpers, numpy-bool-cast]
key_files:
  created: []
  modified:
    - apps/prometheus/src/localstock/analysis/technical.py
    - apps/prometheus/tests/test_analysis/test_technical.py
decisions:
  - "Use bool() cast on return values from _is_hammer and _is_shooting_star to prevent np.bool_ identity failures in pytest (is True)"
  - "Return 6-key dict always (including engulfing_direction: None) so Phase 19 never needs key existence checks"
  - "ta.cdl_doji and ta.cdl_inside used for pandas-ta native patterns; pure OHLC math for hammer, shooting_star, engulfing (no TA-Lib)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-26T01:45:50Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 18 Plan 02: Candlestick Pattern Detection Summary

Implemented `TechnicalAnalyzer.compute_candlestick_patterns()` (SIGNAL-01) using pandas-ta native CDL functions for doji/inside_bar and pure OHLC math for hammer, shooting_star, and engulfing; replaced all 8 `pytest.skip()` stubs with real assertions, achieving 16 PASSED + 6 SKIPPED.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement compute_candlestick_patterns() and helper functions | 74dda1f | technical.py |
| 2 | Replace test stubs with real assertions | 3e22bbb | test_technical.py, technical.py (bug fix) |

## Implementation Details

### compute_candlestick_patterns() method (TechnicalAnalyzer)

- Inserted after `compute_volume_analysis()` (line 110), before `to_indicator_row()`
- Empty/1-row guard: returns all-False dict with `engulfing_direction: None` without raising (T-18-01)
- `ta.cdl_doji()` and `ta.cdl_inside()` wrapped in try/except with `logger.warning` fallback (T-18-02)
- Returns exactly 6 keys: `doji`, `inside_bar`, `hammer`, `shooting_star`, `engulfing_detected`, `engulfing_direction`

### Module-level helpers (after class definition)

- `_is_hammer(row)`: body <= 30% range, lower_shadow >= 2x body, upper_shadow <= 10% range; `candle_range == 0` guard (T-18-03)
- `_is_shooting_star(row)`: body <= 30% range, upper_shadow >= 2x body, lower_shadow <= 10% range; same zero-range guard
- `_detect_engulfing(prev, curr)`: returns `"bullish"`, `"bearish"`, or `None` based on 2-bar OHLC body comparison

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] numpy bool_ identity failure in _is_hammer and _is_shooting_star**
- **Found during:** Task 2 test run — `assert np.True_ is True` fails
- **Issue:** Comparison expressions on pandas Series values return `np.bool_`, not Python `bool`; `is True` identity check fails even though the value is truthy
- **Fix:** Wrapped return expressions in `bool()` in both `_is_hammer` and `_is_shooting_star`
- **Files modified:** `apps/prometheus/src/localstock/analysis/technical.py`
- **Commit:** 3e22bbb

## Final Verification

```
tests/test_analysis/test_technical.py::TestComputeIndicators (4) PASSED
tests/test_analysis/test_technical.py::TestComputeVolumeAnalysis (3) PASSED
tests/test_analysis/test_technical.py::TestToIndicatorRow (1) PASSED
tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns (8) PASSED
tests/test_analysis/test_technical.py::TestComputeVolumeDivergence (6) SKIPPED

======================== 16 passed, 6 skipped in 0.50s =========================
```

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All computation is pure in-memory pandas DataFrame processing.

## Self-Check: PASSED

- `apps/prometheus/src/localstock/analysis/technical.py` — EXISTS, contains `def compute_candlestick_patterns`, `def _is_hammer`, `def _is_shooting_star`, `def _detect_engulfing`
- `apps/prometheus/tests/test_analysis/test_technical.py` — EXISTS, contains 8 real test methods in `TestComputeCandlestickPatterns`, no `pytest.skip()` in that class
- Commit 74dda1f — EXISTS (feat: implement compute_candlestick_patterns)
- Commit 3e22bbb — EXISTS (feat: replace test stubs with real assertions)
- `grep "ta.cdl_pattern" apps/prometheus/src/localstock/analysis/technical.py` — NO MATCH (TA-Lib forbidden pattern absent)
