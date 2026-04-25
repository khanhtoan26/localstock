# Phase 18: Signal Computation - Research

**Researched:** 2026-04-25
**Domain:** pandas-ta candlestick detection, MFI volume divergence, SectorSnapshot sector momentum
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** MFI (Money Flow Index) is the primary indicator for the volume divergence signal. CMF and OBV are not used as primary sources.
- **D-02:** The method returns a dict with three keys: `signal` (str), `value` (float), `indicator` (str). Example: `{"signal": "bullish", "value": 72.3, "indicator": "MFI"}`.
- **D-03:** MFI thresholds: `> 70` → `"bullish"`, `< 30` → `"bearish"`, `30–70` → `"neutral"`. (Consistent with RSI overbought/oversold convention.)
- **D-04:** Stocks with avg_volume < 100k shares/day return `None` for this signal (per SIGNAL-02 requirement). The method must not raise an error on low-liquidity stocks.

### Claude's Discretion

- **Code structure**: Whether new signals extend `TechnicalAnalyzer`, live in a new `SignalComputer` class, or are standalone functions — researcher/planner decides based on best fit with existing patterns.
- **Liquidity threshold window**: Which time window defines avg_volume for the 100k gate (20-day, 60-day, etc.) — researcher/planner decides; must be consistent with existing `compute_volume_analysis` logic.
- **Sector momentum definition**: How `SectorSnapshot.avg_score_change` (or a multi-day trend) is distilled to a named scalar — researcher/planner picks the cleanest representation for LLM injection.
- **Candlestick pattern implementation**: Which of the 5 patterns use pandas-ta CDL functions vs pure OHLC math — researcher decides; TA-Lib must NOT be required.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIGNAL-01 | Detect 5 candlestick patterns (doji, inside, hammer, engulfing, shooting star) from OHLCV data using pandas-ta native functions + pure OHLC math (no TA-Lib) | pandas-ta provides native cdl_doji and cdl_inside; hammer, engulfing, shooting_star require pure OHLC math (TA-Lib needed for cdl_pattern) |
| SIGNAL-02 | Compute volume divergence signal (MFI-based), gated on avg_volume ≥ 100k shares/day — returns null for low-liquidity stocks | pandas-ta MFI: `ta.mfi(high, low, close, volume)` returns `MFI_14` Series; warmup=14 rows; existing `avg_volume_20` from `compute_volume_analysis()` provides the gate |
| SIGNAL-03 | Read sector momentum from SectorSnapshot for injection into LLM prompt per stock | `SectorSnapshot.avg_score_change` is the primary scalar; method must accept pre-fetched dict to stay pure/testable without live DB |
</phase_requirements>

---

## Summary

Phase 18 adds three new signal computation methods to the analysis engine. The primary research findings are:

**SIGNAL-01 (Candlestick patterns):** pandas-ta provides two native CDL functions that do NOT require TA-Lib — `cdl_doji` and `cdl_inside`. The remaining three patterns (hammer, engulfing, shooting_star) all require TA-Lib when called via `ta.cdl_pattern(name=...)`, and return `None` without TA-Lib installed. These three must be implemented as pure OHLC math using canonical TA formulas. All five patterns return a bool-style scalar (100=detected, 0=not detected) suitable for LLM injection.

**SIGNAL-02 (Volume divergence):** `ta.mfi(high, low, close, volume)` is the correct standalone call, returning a Series named `MFI_14`. The df.ta accessor variant (`df.ta.mfi(append=True)`) also works and appends a `MFI_14` column. Warmup period is 14 rows (index 0–13 are NaN; first valid value is at index 14). The 20-day avg_volume already computed in `compute_volume_analysis()` is the correct source for the 100k liquidity gate.

**SIGNAL-03 (Sector momentum):** `SectorSnapshot.avg_score_change` is a `Float | None` that represents the day-over-day change in sector avg composite score. The existing `SectorService.get_rotation_summary()` already uses thresholds `>2.0` (inflow) and `<-2.0` (outflow). The signal method must accept a pre-fetched `dict | None` rather than a live DB session, to remain unit-testable with no DB dependency.

**Primary recommendation:** Implement all three signals as new methods on `TechnicalAnalyzer` (SIGNAL-01, SIGNAL-02) and as a standalone pure function (SIGNAL-03), following the existing `detect_trend()` / `compute_volume_analysis()` patterns. Place SIGNAL-03 in `analysis/trend.py` or a new `analysis/signals.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Candlestick pattern detection | Python analysis layer | — | Pure CPU computation on OHLCV DataFrame; no I/O |
| Volume divergence (MFI) | Python analysis layer | — | Requires OHLCV columns + volume; pure pandas-ta computation |
| Liquidity gate (100k check) | Python analysis layer | — | Reuses avg_volume_20 from existing TechnicalAnalyzer output |
| Sector momentum | Python analysis layer | DB (read-only) | DB read at service layer; signal function stays pure via pre-fetched dict |
| Signal output persistence | Not in scope for Phase 18 | — | Phase 18 outputs dicts consumed by Phase 19 prompts; not persisted in DB |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas-ta | 0.4.71b0 [VERIFIED: installed] | cdl_doji, cdl_inside, ta.mfi | Already imported in TechnicalAnalyzer; project dependency |
| pandas | (project dep) | DataFrame operations for OHLC math | Core data layer |
| numpy | (project dep) | NaN guards, type checks | Used in technical.py already |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | (project dep) | Warning on computation failure | Follow existing try/except + logger.warning pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pure OHLC math for hammer/engulfing/shooting_star | ta.cdl_pattern(name=...) | cdl_pattern requires TA-Lib — returns None without it. Pure OHLC is correct approach. |
| ta.mfi standalone | df.ta.mfi(append=True) | Either works; standalone is more explicit and easier to test with Series inputs directly |

---

## Architecture Patterns

### System Architecture Diagram

```
OHLCV DataFrame
    │
    ├──► cdl_doji(open, high, low, close) ──────────────► CDL_DOJI_10_0.1 Series (100/0)
    │         (pandas-ta native, no TA-Lib)
    │
    ├──► cdl_inside(open, high, low, close) ────────────► CDL_INSIDE Series (100/0)
    │         (pandas-ta native, no TA-Lib)
    │
    ├──► pure OHLC math (last 2 rows)
    │    ├── hammer check ────────────────────────────► bool
    │    ├── shooting_star check ──────────────────────► bool
    │    └── engulfing check (bullish/bearish) ────────► str | None
    │
    ├──► avg_volume check (avg_volume_20 from compute_volume_analysis)
    │    └── < 100k? ──► return None (SIGNAL-02 gate)
    │         └── else: ta.mfi(high, low, close, volume)
    │                   └── MFI_14 last value ─────────► {"signal": str, "value": float, "indicator": "MFI"}
    │
    └──► sector_data dict (pre-fetched by caller from SectorSnapshot)
              avg_score_change
              └── None ──────────────────────────────► return None
              └── classify by threshold ──────────────► {"label": str, "score_change": float, "group_code": str}
```

### Recommended Project Structure

```
apps/prometheus/src/localstock/analysis/
├── technical.py          # TechnicalAnalyzer: add compute_candlestick_patterns(), compute_volume_divergence()
├── trend.py              # Standalone functions: keep existing; SIGNAL-03 can go here or signals.py
├── signals.py            # NEW: compute_sector_momentum() standalone function
└── __init__.py           # No changes needed

apps/prometheus/tests/test_analysis/
├── test_technical.py     # Existing: add TestComputeCandlestickPatterns, TestComputeVolumeDivergence
├── test_trend.py         # Existing: no changes needed for phase 18
└── test_signals.py       # NEW: TestComputeSectorMomentum
```

### Pattern 1: pandas-ta CDL Native Function Call

**What:** Call `ta.cdl_doji` or `ta.cdl_inside` with explicit Series arguments. Returns a Series where 100.0 = pattern detected on that bar, 0.0 = not detected.

**When to use:** For doji and inside bar patterns (the only two that work without TA-Lib).

```python
# Source: verified via pandas-ta 0.4.71b0 direct testing
import pandas_ta as ta

def compute_candlestick_patterns(self, df: pd.DataFrame) -> dict:
    """Detect 5 candlestick patterns on the last row of the DataFrame.

    Returns:
        Dict with keys: doji, inside_bar, hammer, shooting_star, engulfing
        Each value is bool (True = pattern detected on latest bar).
    """
    if df.empty or len(df) < 2:
        return {k: False for k in ["doji", "inside_bar", "hammer", "shooting_star", "engulfing"]}

    result = {}

    # 1. Doji — pandas-ta native (no TA-Lib required)
    try:
        doji = ta.cdl_doji(df["open"], df["high"], df["low"], df["close"])
        result["doji"] = bool(doji.iloc[-1] == 100.0) if doji is not None else False
    except Exception as e:
        logger.warning(f"cdl_doji failed: {e}")
        result["doji"] = False

    # 2. Inside bar — pandas-ta native (no TA-Lib required)
    try:
        inside = ta.cdl_inside(df["open"], df["high"], df["low"], df["close"])
        result["inside_bar"] = bool(inside.iloc[-1] == 100.0) if inside is not None else False
    except Exception as e:
        logger.warning(f"cdl_inside failed: {e}")
        result["inside_bar"] = False

    # 3-5. Pure OHLC math (TA-Lib NOT available)
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    result["hammer"] = _is_hammer(curr)
    result["shooting_star"] = _is_shooting_star(curr)
    result["engulfing"] = _detect_engulfing(prev, curr)  # "bullish"|"bearish"|None -> bool

    return result
```

### Pattern 2: Pure OHLC Math for Hammer / Shooting Star

**What:** Structural candle analysis using body/shadow ratios. No library dependency.

**When to use:** Hammer, shooting_star (single-bar patterns that TA-Lib requires but pandas-ta won't do without it).

```python
# Source: canonical TA formula + verified with synthetic test data

def _is_hammer(row: pd.Series) -> bool:
    """Hammer: small body in upper half, long lower shadow, tiny upper shadow."""
    body = abs(row["close"] - row["open"])
    candle_range = row["high"] - row["low"]
    if candle_range == 0:
        return False
    lower_shadow = min(row["open"], row["close"]) - row["low"]
    upper_shadow = row["high"] - max(row["open"], row["close"])
    return (
        body <= 0.3 * candle_range
        and lower_shadow >= 2.0 * body
        and upper_shadow <= 0.1 * candle_range
    )


def _is_shooting_star(row: pd.Series) -> bool:
    """Shooting star: small body at bottom, long upper shadow, tiny lower shadow."""
    body = abs(row["close"] - row["open"])
    candle_range = row["high"] - row["low"]
    if candle_range == 0:
        return False
    lower_shadow = min(row["open"], row["close"]) - row["low"]
    upper_shadow = row["high"] - max(row["open"], row["close"])
    return (
        body <= 0.3 * candle_range
        and upper_shadow >= 2.0 * body
        and lower_shadow <= 0.1 * candle_range
    )
```

### Pattern 3: Pure OHLC Math for Engulfing (2-Bar)

**What:** Two-bar pattern requiring prev and curr candle. Returns "bullish"/"bearish"/None.

```python
# Source: canonical TA formula + verified with synthetic test data

def _detect_engulfing(prev: pd.Series, curr: pd.Series) -> str | None:
    """Detect bullish or bearish engulfing pattern.

    Returns: 'bullish', 'bearish', or None.
    """
    # Bullish engulfing: prev bearish, curr bullish, curr body engulfs prev body
    prev_bearish = prev["close"] < prev["open"]
    curr_bullish = curr["close"] > curr["open"]
    if prev_bearish and curr_bullish:
        if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
            return "bullish"

    # Bearish engulfing: prev bullish, curr bearish, curr body engulfs prev body
    prev_bullish = prev["close"] > prev["open"]
    curr_bearish = curr["close"] < curr["open"]
    if prev_bullish and curr_bearish:
        if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
            return "bearish"

    return None
```

### Pattern 4: MFI Volume Divergence Signal

**What:** pandas-ta MFI via standalone call, with 20-day avg_volume liquidity gate.

```python
# Source: verified via pandas-ta 0.4.71b0 direct testing
# Column name after call: MFI_14

def compute_volume_divergence(self, df: pd.DataFrame) -> dict | None:
    """Compute MFI-based volume divergence signal (SIGNAL-02).

    Returns None for low-liquidity stocks (avg_volume_20 < 100k).
    Returns {"signal": str, "value": float, "indicator": "MFI"} otherwise.
    """
    # Liquidity gate: use same 20-day avg_volume as compute_volume_analysis
    if df.empty or len(df) < 20:
        return None

    avg_volume_20 = df["volume"].tail(20).mean()
    if avg_volume_20 < 100_000:
        return None  # Low liquidity — no signal (D-04)

    if len(df) < 15:  # MFI needs 15 rows for first valid value
        return None

    try:
        mfi = ta.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)
        last_mfi = mfi.iloc[-1]
        if pd.isna(last_mfi):
            return None

        mfi_value = round(float(last_mfi), 2)

        if mfi_value > 70:
            signal = "bullish"
        elif mfi_value < 30:
            signal = "bearish"
        else:
            signal = "neutral"

        return {"signal": signal, "value": mfi_value, "indicator": "MFI"}

    except Exception as e:
        logger.warning(f"MFI computation failed: {e}")
        return None
```

### Pattern 5: Sector Momentum — Pure Function, Pre-Fetched Dict

**What:** Standalone pure function that accepts a pre-fetched sector dict. No DB session required.

**When to use:** SIGNAL-03. Caller (ReportService) fetches SectorSnapshot from DB, converts to dict, passes in.

```python
# Source: SectorSnapshot model fields + SectorService existing threshold logic (>2.0 inflow, <-2.0 outflow)

def compute_sector_momentum(sector_data: dict | None) -> dict | None:
    """Convert SectorSnapshot data to a named scalar for LLM injection.

    Args:
        sector_data: Pre-fetched dict with keys avg_score_change (float|None),
                     avg_score (float), group_code (str).
                     Pass None if sector mapping unavailable.

    Returns:
        {"label": str, "score_change": float, "group_code": str} or None.
        Labels: "strong_inflow", "mild_inflow", "mild_outflow", "strong_outflow".
    """
    if sector_data is None:
        return None

    score_change = sector_data.get("avg_score_change")
    if score_change is None:
        return None

    if score_change > 2.0:
        label = "strong_inflow"
    elif score_change > 0:
        label = "mild_inflow"
    elif score_change < -2.0:
        label = "strong_outflow"
    else:
        label = "mild_outflow"

    return {
        "label": label,
        "score_change": round(float(score_change), 2),
        "group_code": sector_data.get("group_code", ""),
    }
```

### Anti-Patterns to Avoid

- **Using `ta.cdl_pattern(name="hammer")`:** Returns `None` on this environment — TA-Lib not installed. [VERIFIED]
- **Using `ta.cdl_pattern(name="engulfing")`:** Same — requires TA-Lib. [VERIFIED]
- **Using `ta.cdl_pattern(name="shootingstar")`:** Same — requires TA-Lib. [VERIFIED]
- **Accessing `df.ta.cdl_doji()`:** Method does not exist on df.ta accessor — use `ta.cdl_doji(df["open"], ...)` instead. [VERIFIED]
- **Making sector momentum method async with DB session:** Breaks testability. Pass pre-fetched dict instead.
- **Not guarding MFI on short DataFrames:** MFI(14) produces NaN for first 14 rows; guard `len(df) < 15` before reading `mfi.iloc[-1]`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Doji detection | Custom body/range ratio | `ta.cdl_doji(open, high, low, close)` | pandas-ta uses 10-bar rolling avg H-L for normalization — harder to replicate correctly |
| Inside bar detection | Custom H-L comparison | `ta.cdl_inside(open, high, low, close)` | Already handles edge cases (equal bars) |
| MFI calculation | Custom money flow math | `ta.mfi(high, low, close, volume)` | Typical money flow calculation with proper rounding/drift |
| NaN handling | Custom isnan checks | `_is_valid()` helper from trend.py | Already defined in `analysis/trend.py` — import and reuse |

**Key insight:** Only hammer, shooting_star, and engulfing require pure OHLC math — and these are the simplest structural formulas in technical analysis. Doji and inside bar have normalization complexity (rolling averages, edge cases) that pandas-ta handles correctly.

---

## Common Pitfalls

### Pitfall 1: Assuming All CDL Patterns Are Native in pandas-ta

**What goes wrong:** `ta.cdl_pattern(name="hammer")` returns `None` silently with a log message `[i] Requires TA-Lib to use hammer.` — no exception raised, just None. If caller does `result.iloc[-1]` it crashes with `AttributeError: 'NoneType' object has no attribute 'iloc'`.

**Why it happens:** pandas-ta wraps TA-Lib for most CDL patterns. Only `cdl_doji`, `cdl_inside`, `cdl_z`, and `candle_*` functions are native.

**How to avoid:** Use `ta.cdl_doji()` and `ta.cdl_inside()` directly. Implement hammer, shooting_star, engulfing as pure OHLC math. [VERIFIED]

**Warning signs:** `[i] Requires TA-Lib to use <name>` in logs.

### Pitfall 2: MFI Warmup Period Not Guarded

**What goes wrong:** For stocks with fewer than 15 rows of OHLCV data, `mfi.iloc[-1]` returns NaN. If the caller converts to float without NaN check, it silently passes `nan` to the LLM prompt.

**Why it happens:** MFI(14) needs 14 complete periods before producing a value — first valid index is 14 (not 0).

**How to avoid:** Check `len(df) >= 15` before calling MFI and guard `if pd.isna(last_mfi): return None`. [VERIFIED]

**Warning signs:** MFI value is NaN despite having data.

### Pitfall 3: 5-Row DataFrame for cdl_doji Returns None (Not False)

**What goes wrong:** `ta.cdl_doji` called on fewer than ~10 rows returns `None` (not a Series), because the 10-bar rolling H-L average has no meaningful window. Caller does `result.iloc[-1]` and gets AttributeError.

**Why it happens:** cdl_doji uses a rolling 10-bar lookback for normalization. Below 10 bars the function exits early returning None.

**How to avoid:** Guard `len(df) >= 11` for doji detection, or check `if doji is not None` before reading `.iloc[-1]`. The try/except pattern in `compute_indicators()` handles this correctly.

**Warning signs:** `None` returned from `ta.cdl_doji` on short DataFrames.

### Pitfall 4: Sector Momentum Function Depends on Async DB Session

**What goes wrong:** If `compute_sector_momentum` takes an `AsyncSession` and queries the DB, it cannot be unit-tested with a synthetic dict. The CONTEXT.md and success criteria require pure testability without live DB.

**Why it happens:** SIGNAL-03 needs to look up sector data for a stock — it's tempting to pass the DB session directly.

**How to avoid:** Design the function to accept a pre-fetched `dict | None`. The caller (ReportService) owns the DB query. This is consistent with how `detect_trend()` accepts a pre-computed Series rather than fetching raw OHLCV.

### Pitfall 5: Engulfing Returns String vs Bool Inconsistency

**What goes wrong:** The 5-pattern output dict returns bool for 4 patterns but str/None for engulfing, causing type inconsistency in downstream LLM prompt injection.

**How to avoid:** Convert engulfing to bool for the patterns dict output, OR return `"bullish"/"bearish"/None` and document it as intentional. The planner must decide the canonical output type — recommended: include both `engulfing_detected: bool` and `engulfing_direction: str | None`.

---

## Code Examples

### Full MFI call with liquidity gate

```python
# Source: verified pattern — pandas-ta 0.4.71b0, tested 2026-04-25
import pandas_ta as ta

mfi_series = ta.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)
# Column name: MFI_14
# Values: float, range 0–100
# Warmup: first 14 values are NaN
# Last value: mfi_series.iloc[-1]
```

### cdl_doji return value format

```python
# Source: verified 2026-04-25
doji = ta.cdl_doji(df["open"], df["high"], df["low"], df["close"])
# Series name: CDL_DOJI_10_0.1
# Values: 100.0 (detected) or 0.0 (not detected)
# No -100 values — doji has no bullish/bearish direction
```

### cdl_inside return value format

```python
# Source: verified 2026-04-25
inside = ta.cdl_inside(df["open"], df["high"], df["low"], df["close"])
# Series name: CDL_INSIDE
# Values: 100.0 (inside bar on this candle) or 0.0
# Needs minimum 2 rows to detect pattern
```

### SectorSnapshot dict structure (pre-fetched)

```python
# Source: SectorSnapshot model in db/models.py [VERIFIED]
# Fields available on SectorSnapshot ORM object:
# date, group_code, avg_score, avg_volume, total_volume, stock_count, avg_score_change

# Convert to dict for pure function call:
sector_dict = {
    "avg_score_change": snapshot.avg_score_change,  # Float | None
    "avg_score": snapshot.avg_score,                # Float
    "group_code": snapshot.group_code,              # str
}
```

---

## Validation Architecture

> nyquist_validation is enabled (config.json: `"nyquist_validation": true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (auto mode) |
| Config file | `apps/prometheus/pyproject.toml` |
| Quick run command | `uv run pytest tests/test_analysis/test_technical.py tests/test_analysis/test_signals.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIGNAL-01 | doji detected when open≈close | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_doji_detected -x` | ❌ Wave 0 |
| SIGNAL-01 | doji absent on normal candle | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_doji_not_present -x` | ❌ Wave 0 |
| SIGNAL-01 | inside bar detected when H-L within prev H-L | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_inside_bar_detected -x` | ❌ Wave 0 |
| SIGNAL-01 | hammer detected with synthetic candle (long lower shadow) | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_hammer_detected -x` | ❌ Wave 0 |
| SIGNAL-01 | shooting star detected with synthetic candle (long upper shadow) | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_shooting_star_detected -x` | ❌ Wave 0 |
| SIGNAL-01 | bullish engulfing detected on 2-bar synthetic data | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_engulfing_bullish -x` | ❌ Wave 0 |
| SIGNAL-01 | bearish engulfing detected on 2-bar synthetic data | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_engulfing_bearish -x` | ❌ Wave 0 |
| SIGNAL-01 | returns all-false dict on DataFrame with < 2 rows | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_empty_df -x` | ❌ Wave 0 |
| SIGNAL-02 | returns bullish dict when MFI > 70 | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_bullish_signal -x` | ❌ Wave 0 |
| SIGNAL-02 | returns bearish dict when MFI < 30 | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_bearish_signal -x` | ❌ Wave 0 |
| SIGNAL-02 | returns neutral dict when 30 ≤ MFI ≤ 70 | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_neutral_signal -x` | ❌ Wave 0 |
| SIGNAL-02 | returns None when avg_volume_20 < 100k | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_low_liquidity_gate -x` | ❌ Wave 0 |
| SIGNAL-02 | returns None when df has < 15 rows | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_short_df -x` | ❌ Wave 0 |
| SIGNAL-02 | output dict has exactly keys signal, value, indicator | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_output_shape -x` | ❌ Wave 0 |
| SIGNAL-03 | returns strong_inflow for avg_score_change > 2.0 | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_strong_inflow -x` | ❌ Wave 0 |
| SIGNAL-03 | returns mild_inflow for avg_score_change in (0, 2] | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_mild_inflow -x` | ❌ Wave 0 |
| SIGNAL-03 | returns mild_outflow for avg_score_change in [-2, 0) | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_mild_outflow -x` | ❌ Wave 0 |
| SIGNAL-03 | returns strong_outflow for avg_score_change < -2.0 | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_strong_outflow -x` | ❌ Wave 0 |
| SIGNAL-03 | returns None when sector_data is None | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_none_input -x` | ❌ Wave 0 |
| SIGNAL-03 | returns None when avg_score_change is None | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_none_score_change -x` | ❌ Wave 0 |
| SIGNAL-03 | output dict has keys label, score_change, group_code | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_output_shape -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_analysis/test_technical.py tests/test_analysis/test_signals.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_analysis/test_technical.py` — extend with `TestComputeCandlestickPatterns` and `TestComputeVolumeDivergence` classes
- [ ] `tests/test_analysis/test_signals.py` — new file, `TestComputeSectorMomentum` class
- [ ] `apps/prometheus/src/localstock/analysis/signals.py` — new file for `compute_sector_momentum()`

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 18 |
|-----------|-------------------|
| No TA-Lib dependency | Confirmed: hammer, engulfing, shooting_star must be pure OHLC math |
| No new Python dependencies | All features use pandas-ta (already installed) + pandas + numpy |
| No new API endpoints | Signal methods are internal — consumed by analysis pipeline, not exposed via HTTP |
| No new DB tables | Signals are transient computation results passed to prompt builder (Phase 19) |
| pandas-ta already imported in TechnicalAnalyzer | New methods should follow same `try/except + logger.warning` pattern |
| pytest-asyncio auto mode | Test functions: `def test_*` (not async) since all new signal methods are synchronous |
| Return dicts, not dataclasses | All new methods return plain dicts or None |
| Async-first codebase | Signal computation methods are synchronous CPU work — no async needed |

---

## Implementation Decision: Code Structure (Claude's Discretion)

**Recommendation: New methods on TechnicalAnalyzer + new standalone module for SIGNAL-03.**

**Reasoning:**
- `compute_candlestick_patterns(df)` and `compute_volume_divergence(df)` both take only an OHLCV DataFrame — identical call signature to `compute_volume_analysis(df)`. Natural fit as TechnicalAnalyzer methods.
- `compute_sector_momentum(sector_data)` has no OHLCV dependency. It mirrors `detect_trend(latest_series)` in conceptual role — a pure function over already-fetched data. It belongs in a standalone module (new `analysis/signals.py` or appended to `analysis/trend.py`).
- A separate `SignalComputer` class adds abstraction without benefit — the signals are not cohesive with each other, and TechnicalAnalyzer is already the right home for DataFrame-based signals.

**Liquidity gate window:** Use 20-day avg_volume (`df["volume"].tail(20).mean()`). Rationale: `compute_volume_analysis()` already computes `avg_volume_20` using this exact window. Using the same window ensures the gate is consistent with the volume trend reported in indicator_data. [ASSUMED — 20-day is the most coherent choice but the project constraint says to be consistent with existing logic, which uses 20-day.]

**Sector momentum labels:** Use 4-label scheme (`strong_inflow`, `mild_inflow`, `mild_outflow`, `strong_outflow`) aligned with SectorService inflow/outflow thresholds (>2.0 and <-2.0). Rationale: reuses existing business-layer thresholds that are already calibrated to the composite score scale (0–100). [ASSUMED — 4-label scheme is a clean LLM-injectable format; user has not specified exact labels.]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TA-Lib CDL patterns (60 patterns, C binary) | pandas-ta native (doji, inside) + pure OHLC math | Project constraint from day 1 | Limited to 5 specific patterns; accurate for phase needs |
| OBV as volume signal | MFI as primary (D-01) | Phase 18 design discussion | MFI captures both price AND volume; OBV is pure accumulation |

**Deprecated/outdated:**
- `ta.cdl_pattern(name="hammer/engulfing/shootingstar")`: These appear in CDL_PATTERN_NAMES but require TA-Lib — confirmed by runtime testing.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 20-day avg_volume window is the correct liquidity gate window (vs 60-day) | Implementation Decision | Low — any window ≥20 days would work; 20-day is already computed, using it avoids redundant calculation |
| A2 | 4-label sector momentum scheme (strong/mild inflow/outflow) is correct LLM-injection format | Pattern 5 | Low — Phase 19 prompt builder can remap labels; changing from 4 to 2 labels is trivial |
| A3 | `compute_sector_momentum` belongs in new `analysis/signals.py` (vs appended to `trend.py`) | Architecture | Very low — either location works; signals.py is cleaner for Phase 19+ additions |
| A4 | engulfing output should preserve direction string ("bullish"/"bearish") vs collapsing to bool | Pattern 3 | Medium — planner must decide whether to expose direction or just bool to Phase 19 prompt |

---

## Open Questions

1. **Engulfing direction exposure**
   - What we know: `_detect_engulfing()` returns "bullish"/"bearish"/None — directional.
   - What's unclear: Should `compute_candlestick_patterns()` return `{"engulfing": bool}` or `{"engulfing": "bullish" | "bearish" | None}`? Phase 19 may want the direction for prompt context.
   - Recommendation: Return `{"engulfing_detected": bool, "engulfing_direction": str | None}` — both values; Phase 19 can use both.

2. **Minimum DataFrame size for production use**
   - What we know: cdl_doji needs ≥11 rows for meaningful results; MFI needs ≥15.
   - What's unclear: Should `compute_candlestick_patterns()` return all-False or None for short DataFrames?
   - Recommendation: Return `{k: False for k in patterns}` (all-False dict) so callers don't need None handling — consistent with how `compute_volume_analysis()` returns nulls-filled dict rather than None.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas-ta | SIGNAL-01, SIGNAL-02 | ✓ | 0.4.71b0 | — |
| TA-Lib | CDL patterns for hammer/engulfing/shooting_star | ✗ | — | Pure OHLC math (this research confirms the pure math approach) |
| pandas | All signals | ✓ | (project dep) | — |
| numpy | NaN guards | ✓ | (project dep) | — |

**Missing dependencies with no fallback:** None — pure OHLC math is the correct fallback for TA-Lib-dependent patterns.

**Missing dependencies with fallback:** TA-Lib → pure OHLC math (hammer, shooting_star, engulfing).

---

## Security Domain

> security_enforcement not set to false — included per policy.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Guard empty/short DataFrames before computation; return safe None/False dict rather than raising |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| NaN injection into LLM prompt | Tampering | Check `pd.isna()` before including MFI value in output dict |
| Empty DataFrame crash | Denial of Service | Guard `if df.empty or len(df) < N: return safe_default` in all signal methods |

---

## Sources

### Primary (HIGH confidence)
- pandas-ta 0.4.71b0 installed in project venv — `CDL_PATTERN_NAMES`, `cdl_doji`, `cdl_inside`, `ta.mfi` tested directly [VERIFIED: runtime testing 2026-04-25]
- `apps/prometheus/src/localstock/analysis/technical.py` — existing TechnicalAnalyzer patterns [VERIFIED: file read]
- `apps/prometheus/src/localstock/analysis/trend.py` — standalone function style reference [VERIFIED: file read]
- `apps/prometheus/src/localstock/db/models.py` §SectorSnapshot — field list [VERIFIED: file read]
- `apps/prometheus/src/localstock/services/sector_service.py` — inflow/outflow thresholds (>2.0, <-2.0) [VERIFIED: file read]
- `apps/prometheus/tests/test_analysis/test_technical.py` — test fixture and class patterns [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- pandas-ta CDL function behavior (100=detected, 0=not detected, no -100 for single-bar patterns) [VERIFIED: runtime]
- MFI warmup period of 14 NaN rows (first valid at index 14, needs 15 rows) [VERIFIED: runtime]

### Tertiary (LOW confidence)
- None — all claims verified by runtime or file inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pandas-ta 0.4.71b0 installed and tested; all functions verified by runtime
- Architecture: HIGH — mirrors existing TechnicalAnalyzer patterns precisely; SectorSnapshot fields confirmed
- Pitfalls: HIGH — all pitfalls discovered through actual runtime testing, not assumption
- Test scenarios: HIGH — directly derived from SIGNAL-01/02/03 acceptance criteria

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable library; 30-day window)
