# Phase 18: Signal Computation - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 4
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/prometheus/src/localstock/analysis/technical.py` | service (method extension) | transform | `apps/prometheus/src/localstock/analysis/technical.py` (existing `compute_volume_analysis`) | exact |
| `apps/prometheus/src/localstock/analysis/signals.py` | utility (standalone function) | transform | `apps/prometheus/src/localstock/analysis/trend.py` (`detect_trend`) | exact |
| `apps/prometheus/tests/test_analysis/test_technical.py` | test | transform | `apps/prometheus/tests/test_analysis/test_technical.py` (existing classes) | exact |
| `apps/prometheus/tests/test_analysis/test_signals.py` | test | transform | `apps/prometheus/tests/test_analysis/test_trend.py` (`TestDetectTrend`) | exact |

---

## Pattern Assignments

### `apps/prometheus/src/localstock/analysis/technical.py` — add `compute_candlestick_patterns()` and `compute_volume_divergence()`

**Analog:** `apps/prometheus/src/localstock/analysis/technical.py` — `compute_volume_analysis()` method (lines 73–108)

**Imports pattern** (lines 1–12 of technical.py):
```python
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pandas_ta as ta
from loguru import logger
```
`pandas_ta as ta`, `logger`, `pd`, `np` are all already imported. New methods require no additional imports.

**Core method structure — copy from `compute_volume_analysis`** (lines 73–108):
```python
def compute_volume_analysis(self, df: pd.DataFrame) -> dict:
    """Compute volume analysis metrics (TECH-02).

    Args:
        df: OHLCV DataFrame (latest date should be last row).

    Returns:
        Dict with keys: avg_volume_20 (int), relative_volume (float),
        volume_trend (str: 'increasing'/'decreasing'/'stable').
    """
    if df.empty or len(df) < 20:
        return {
            "avg_volume_20": None,
            "relative_volume": None,
            "volume_trend": None,
        }

    volumes = df["volume"].astype(float)
    avg_20 = int(volumes.tail(20).mean())
    ...
    return {
        "avg_volume_20": avg_20,
        "relative_volume": round(relative, 4),
        "volume_trend": trend,
    }
```

**Pattern points to copy:**
- Method signature: `def method_name(self, df: pd.DataFrame) -> dict | None:`
- Guard pattern: `if df.empty or len(df) < N: return <safe_default_dict_or_None>`
- Column access pattern: `df["volume"].tail(20).mean()` — same for new methods accessing `df["high"]`, `df["low"]`, `df["close"]`, `df["volume"]`
- Return type: plain dict with named keys (no dataclasses, no Pydantic)

**Per-indicator try/except pattern — copy from `compute_indicators`** (lines 64–70):
```python
for name, params in indicators:
    try:
        method = getattr(result.ta, name)
        method(append=True, **params)
    except Exception as e:
        logger.warning(f"Failed to compute {name}({params}): {e}")
```
New methods must wrap each `ta.cdl_doji()`, `ta.cdl_inside()`, and `ta.mfi()` call in `try/except Exception as e: logger.warning(...)`.

**New method placement:** Add `compute_candlestick_patterns` and `compute_volume_divergence` as instance methods after `compute_volume_analysis` (line 108), before `to_indicator_row`. The new helper functions `_is_hammer`, `_is_shooting_star`, `_detect_engulfing` go as module-level private functions after the class (matching the pattern used in `trend.py` for `_is_valid` and `_all_valid`).

---

### `apps/prometheus/src/localstock/analysis/signals.py` — NEW file with `compute_sector_momentum()`

**Analog:** `apps/prometheus/src/localstock/analysis/trend.py` — `detect_trend()` function (lines 13–75)

**Module docstring pattern** (line 1–6 of trend.py):
```python
"""Trend detection and support/resistance analysis (TECH-03, TECH-04).

Per D-04: Support/resistance via Pivot Points + nearest peaks/troughs.
Trend detection via MA crossovers + ADX + MACD histogram.
Manual peak/trough detection (no scipy dependency, per research recommendation).
"""
```
New file docstring should follow same format: one-line summary + per-decision notes.

**Imports pattern** (lines 1–10 of trend.py):
```python
import numpy as np
import pandas as pd
from loguru import logger
```
`signals.py` only needs standard library (none) — no `numpy`, `pandas`, or `pandas_ta` imports required since `compute_sector_momentum` operates on a plain `dict`.

**Standalone function pattern — copy from `detect_trend`** (lines 13–75 of trend.py):
```python
def detect_trend(latest: pd.Series) -> dict:
    """Classify trend direction using multi-signal approach (TECH-03).

    Args:
        latest: pandas Series with keys: close, SMA_20, SMA_50, SMA_200,
                MACDh_12_26_9, ADX_14.

    Returns:
        Dict with 'trend_direction' ('uptrend'/'downtrend'/'sideways')
        and 'trend_strength' (float, ADX value).
    """
    ...
    return {
        "trend_direction": direction,
        "trend_strength": trend_strength,
    }
```

**Pattern points to copy:**
- Function (not method, no `self`) with typed args: `def compute_sector_momentum(sector_data: dict | None) -> dict | None:`
- Early `None` guard at the top, before any computation
- `.get()` access on dicts (never direct key access that could raise KeyError)
- `round(float(...), 2)` for numeric outputs — same as `detect_trend`'s `round(relative, 4)` in technical.py
- Return plain dict with named keys

**Private helper pattern — copy from `_is_valid` / `_all_valid`** (lines 188–199 of trend.py):
```python
def _is_valid(val) -> bool:
    """Check if a value is not None and not NaN."""
    if val is None:
        return False
    if isinstance(val, float) and np.isnan(val):
        return False
    return True
```
In `signals.py`, the NaN guard for `avg_score_change` can use `if score_change is None: return None` (a float from Postgres will not be NaN, only None). No numpy needed.

**`__init__.py` export:** The existing `apps/prometheus/src/localstock/analysis/__init__.py` contains only a docstring (1 line). No new exports are needed — callers import directly from the module path (consistent with how `detect_trend` is imported in tests: `from localstock.analysis.trend import detect_trend`).

---

### `apps/prometheus/tests/test_analysis/test_technical.py` — extend with new test classes

**Analog:** `apps/prometheus/tests/test_analysis/test_technical.py` — existing `TestComputeVolumeAnalysis` (lines 67–83) and `TestComputeIndicators` (lines 35–64)

**File header and imports pattern** (lines 1–11):
```python
"""Tests for TechnicalAnalyzer — technical indicators and volume analysis.

Covers TECH-01 (core indicators) and TECH-02 (volume analysis).
"""

import numpy as np
import pandas as pd
import pytest

from localstock.analysis.technical import TechnicalAnalyzer
```
New test classes add to the same file. No new imports needed for `TestComputeCandlestickPatterns` and `TestComputeVolumeDivergence` — `numpy`, `pandas`, `pytest`, and `TechnicalAnalyzer` are already imported.

**Shared fixture pattern** (lines 13–32):
```python
@pytest.fixture
def ohlcv_250():
    """250-day OHLCV DataFrame simulating realistic stock data."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 50000 + np.cumsum(np.random.randn(n) * 500)
    return pd.DataFrame({
        "date": dates,
        "open": close - np.random.rand(n) * 200,
        "high": close + np.abs(np.random.randn(n)) * 300,
        "low": close - np.abs(np.random.randn(n)) * 300,
        "close": close,
        "volume": np.random.randint(500_000, 5_000_000, n),
    })

@pytest.fixture
def analyzer():
    return TechnicalAnalyzer()
```
Both new test classes use the same `ohlcv_250` and `analyzer` fixtures — no new fixtures needed for the happy-path tests. Negative-path tests (short DataFrames, low-volume stocks, pure OHLC candles) construct minimal DataFrames inline within the test method, following the style of `TestDetectTrend` in test_trend.py (lines 17–28 — plain `pd.Series` constructed inline).

**Test class structure — copy from `TestComputeVolumeAnalysis`** (lines 67–83):
```python
class TestComputeVolumeAnalysis:
    def test_returns_volume_metrics(self, analyzer, ohlcv_250):
        result = analyzer.compute_volume_analysis(ohlcv_250)
        assert "avg_volume_20" in result
        assert "relative_volume" in result
        assert "volume_trend" in result

    def test_volume_trend_valid_values(self, analyzer, ohlcv_250):
        result = analyzer.compute_volume_analysis(ohlcv_250)
        assert result["volume_trend"] in ("increasing", "decreasing", "stable")
```

**Key patterns to copy:**
- Class method signature: `def test_*(self, analyzer, ohlcv_250):` — methods receive fixtures via pytest injection
- No `async def` — all new signal methods are synchronous (confirmed in RESEARCH.md)
- No `@pytest.mark.*` decorators — existing classes use none
- Dict key presence assertion: `assert "key" in result` for shape tests
- Value boundary assertion: `assert result["key"] in (allowed_values)` for enum-like fields
- `pytest.approx()` for float comparisons (see line 82: `assert result["avg_volume_20"] == pytest.approx(...)`)

**Synthetic DataFrame construction for edge cases — copy inline style from test_trend.py** (lines 17–28):
```python
def test_uptrend_detection(self):
    """Strong uptrend: SMA20 > SMA50 > SMA200, MACD positive, ADX > 25."""
    data = pd.Series({
        "close": 60000,
        "SMA_20": 58000,
        ...
    })
    result = detect_trend(data)
    assert result["trend_direction"] == "uptrend"
```
For candlestick tests, construct minimal 15-row DataFrames inline (using `pd.DataFrame({...})`) with columns `open`, `high`, `low`, `close`, `volume` shaped to trigger the specific pattern. Set `volume` to `>=100_000` for MFI tests that require the liquidity gate to pass.

---

### `apps/prometheus/tests/test_analysis/test_signals.py` — NEW file for `TestComputeSectorMomentum`

**Analog:** `apps/prometheus/tests/test_analysis/test_trend.py` — `TestDetectTrend` class (lines 16–68)

**File header and imports pattern** (lines 1–13 of test_trend.py):
```python
"""Tests for trend detection and support/resistance (TECH-03, TECH-04)."""

import numpy as np
import pandas as pd
import pytest

from localstock.analysis.trend import (
    compute_pivot_points,
    detect_trend,
    find_peaks_manual,
    find_support_resistance,
    find_troughs_manual,
)
```
New test file replaces with:
```python
"""Tests for signal computation functions (SIGNAL-03)."""

import pytest

from localstock.analysis.signals import compute_sector_momentum
```
No `numpy` or `pandas` imports needed — `compute_sector_momentum` takes a plain `dict`.

**Test class with inline dict construction — copy from `TestDetectTrend`** (lines 17–28):
```python
class TestDetectTrend:
    def test_uptrend_detection(self):
        """Strong uptrend: SMA20 > SMA50 > SMA200, MACD positive, ADX > 25."""
        data = pd.Series({
            "close": 60000,
            "SMA_20": 58000,
            ...
        })
        result = detect_trend(data)
        assert result["trend_direction"] == "uptrend"
```
`TestComputeSectorMomentum` follows identical structure but passes a `dict` (not `pd.Series`):
```python
class TestComputeSectorMomentum:
    def test_strong_inflow(self):
        """avg_score_change > 2.0 → label 'strong_inflow'."""
        data = {"avg_score_change": 3.5, "avg_score": 72.0, "group_code": "BKS"}
        result = compute_sector_momentum(data)
        assert result["label"] == "strong_inflow"
```

**Key patterns to copy:**
- No fixtures, no `analyzer` dependency — all tests are self-contained with inline dicts
- Docstring on each test method describing the scenario (lines 18, 30, 37, 44 of test_trend.py)
- No `async def` — function is synchronous
- `None`-return tests: `assert result is None` (compare with test_trend.py's implicit None checks)
- Output shape test: `assert set(result.keys()) == {"label", "score_change", "group_code"}`

---

## Shared Patterns

### Guard-then-compute (empty/short DataFrame)
**Source:** `apps/prometheus/src/localstock/analysis/technical.py`, lines 83–88
**Apply to:** `compute_candlestick_patterns`, `compute_volume_divergence`
```python
if df.empty or len(df) < 20:
    return {
        "avg_volume_20": None,
        "relative_volume": None,
        "volume_trend": None,
    }
```
`compute_candlestick_patterns` uses `len(df) < 2` as the short guard, returning `{k: False for k in patterns}`.
`compute_volume_divergence` uses `len(df) < 20` (avg_volume gate) then `len(df) < 15` (MFI gate), returning `None`.

### try/except + logger.warning per indicator call
**Source:** `apps/prometheus/src/localstock/analysis/technical.py`, lines 64–70
**Apply to:** every `ta.cdl_doji()`, `ta.cdl_inside()`, and `ta.mfi()` call
```python
try:
    method = getattr(result.ta, name)
    method(append=True, **params)
except Exception as e:
    logger.warning(f"Failed to compute {name}({params}): {e}")
```

### None-guard and dict `.get()` for pre-fetched data
**Source:** `apps/prometheus/src/localstock/analysis/trend.py`, lines 33–44
**Apply to:** `compute_sector_momentum` in `signals.py`
```python
sma_20 = latest.get("SMA_20")
sma_50 = latest.get("SMA_50")
sma_200 = latest.get("SMA_200")
if _all_valid(sma_20, sma_50, sma_200):
    ...
```
`compute_sector_momentum` uses `.get()` with None fallback for all dict keys, and returns `None` early if the primary value is absent.

### `_is_valid` / `_all_valid` helpers
**Source:** `apps/prometheus/src/localstock/analysis/trend.py`, lines 188–199
**Apply to:** `signals.py` if float NaN guarding is needed; `technical.py` new methods can call `_is_valid` imported from `trend.py` or duplicate the minimal check inline.
```python
def _is_valid(val) -> bool:
    """Check if a value is not None and not NaN."""
    if val is None:
        return False
    if isinstance(val, float) and np.isnan(val):
        return False
    return True
```
Note: `signals.py` does not need to import `_is_valid` from `trend.py` since `avg_score_change` from Postgres is either a Python float or None, never `np.nan`. A simple `if score_change is None: return None` suffices.

### Return plain dict (no dataclasses/Pydantic)
**Source:** `apps/prometheus/src/localstock/analysis/technical.py` (lines 104–108) and `trend.py` (lines 72–75)
**Apply to:** all new methods and functions
```python
return {
    "avg_volume_20": avg_20,
    "relative_volume": round(relative, 4),
    "volume_trend": trend,
}
```

### Test: inline dict/Series construction for edge cases
**Source:** `apps/prometheus/tests/test_analysis/test_trend.py`, lines 17–28
**Apply to:** `TestComputeCandlestickPatterns` (edge-case candles), `TestComputeVolumeDivergence` (low-liquidity, short DataFrame), `TestComputeSectorMomentum` (all tests)
```python
def test_uptrend_detection(self):
    data = pd.Series({
        "close": 60000,
        "SMA_20": 58000,
        "SMA_50": 55000,
        "SMA_200": 50000,
        "MACDh_12_26_9": 500,
        "ADX_14": 35,
    })
    result = detect_trend(data)
    assert result["trend_direction"] == "uptrend"
```

---

## No Analog Found

All four files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `apps/prometheus/src/localstock/analysis/`, `apps/prometheus/tests/test_analysis/`
**Files scanned:** 6 (technical.py, trend.py, __init__.py, test_technical.py, test_trend.py, test_fundamental.py header)
**Pattern extraction date:** 2026-04-25
