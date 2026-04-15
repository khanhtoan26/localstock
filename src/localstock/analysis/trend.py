"""Trend detection and support/resistance analysis (TECH-03, TECH-04).

Per D-04: Support/resistance via Pivot Points + nearest peaks/troughs.
Trend detection via MA crossovers + ADX + MACD histogram.
Manual peak/trough detection (no scipy dependency, per research recommendation).
"""

import numpy as np
import pandas as pd
from loguru import logger


def detect_trend(latest: pd.Series) -> dict:
    """Classify trend direction using multi-signal approach (TECH-03).

    Signals:
    1. MA Alignment: SMA20 > SMA50 > SMA200 = bullish
    2. Price vs SMA50: above = bullish, below = bearish
    3. MACD Histogram: positive = bullish, negative = bearish
    4. ADX: < 20 = sideways (overrides MA signals)

    Args:
        latest: pandas Series with keys: close, SMA_20, SMA_50, SMA_200,
                MACDh_12_26_9, ADX_14.

    Returns:
        Dict with 'trend_direction' ('uptrend'/'downtrend'/'sideways')
        and 'trend_strength' (float, ADX value).
    """
    signals = 0

    # Signal 1: MA Alignment
    sma_20 = latest.get("SMA_20")
    sma_50 = latest.get("SMA_50")
    sma_200 = latest.get("SMA_200")
    if _all_valid(sma_20, sma_50, sma_200):
        if sma_20 > sma_50 > sma_200:
            signals += 1
        elif sma_20 < sma_50 < sma_200:
            signals -= 1

    # Signal 2: Price vs SMA50
    close = latest.get("close")
    if _all_valid(close, sma_50):
        if close > sma_50:
            signals += 1
        elif close < sma_50:
            signals -= 1

    # Signal 3: MACD Histogram
    macd_h = latest.get("MACDh_12_26_9")
    if _is_valid(macd_h):
        if macd_h > 0:
            signals += 1
        elif macd_h < 0:
            signals -= 1

    # Signal 4: ADX for trend strength
    adx = latest.get("ADX_14")
    trend_strength = float(adx) if _is_valid(adx) else 0.0

    # ADX < 20 = no clear trend → sideways
    if trend_strength < 20:
        direction = "sideways"
    elif signals >= 2:
        direction = "uptrend"
    elif signals <= -2:
        direction = "downtrend"
    else:
        direction = "sideways"

    return {
        "trend_direction": direction,
        "trend_strength": trend_strength,
    }


def compute_pivot_points(high: float, low: float, close: float) -> dict:
    """Calculate standard (floor) pivot points from previous day's HLC (TECH-04).

    Formulas:
        PP  = (H + L + C) / 3
        S1  = 2 * PP - H
        S2  = PP - (H - L)
        R1  = 2 * PP - L
        R2  = PP + (H - L)

    Args:
        high: Previous day's high price.
        low: Previous day's low price.
        close: Previous day's close price.

    Returns:
        Dict with pivot_point, support_1, support_2, resistance_1, resistance_2.
    """
    pp = (high + low + close) / 3
    return {
        "pivot_point": round(pp, 2),
        "support_1": round(2 * pp - high, 2),
        "support_2": round(pp - (high - low), 2),
        "resistance_1": round(2 * pp - low, 2),
        "resistance_2": round(pp + (high - low), 2),
    }


def find_peaks_manual(prices: list[float], order: int = 20) -> list[int]:
    """Find local maxima indices using rolling comparison (no scipy).

    A point is a peak if it's >= all points within `order` distance
    on both sides.

    Args:
        prices: List of price values.
        order: Number of points on each side to compare.

    Returns:
        List of indices that are local maxima.
    """
    peaks = []
    for i in range(order, len(prices) - order):
        if all(prices[i] >= prices[i - j] for j in range(1, order + 1)) and \
           all(prices[i] >= prices[i + j] for j in range(1, order + 1)):
            # Strict inequality: skip if equal to all neighbors (flat)
            if any(prices[i] > prices[i - j] for j in range(1, order + 1)) or \
               any(prices[i] > prices[i + j] for j in range(1, order + 1)):
                peaks.append(i)
    return peaks


def find_troughs_manual(prices: list[float], order: int = 20) -> list[int]:
    """Find local minima indices using rolling comparison (no scipy).

    Args:
        prices: List of price values.
        order: Number of points on each side to compare.

    Returns:
        List of indices that are local minima.
    """
    troughs = []
    for i in range(order, len(prices) - order):
        if all(prices[i] <= prices[i - j] for j in range(1, order + 1)) and \
           all(prices[i] <= prices[i + j] for j in range(1, order + 1)):
            # Strict inequality: skip if equal to all neighbors (flat)
            if any(prices[i] < prices[i - j] for j in range(1, order + 1)) or \
               any(prices[i] < prices[i + j] for j in range(1, order + 1)):
                troughs.append(i)
    return troughs


def find_support_resistance(
    prices: list[float], order: int = 20
) -> tuple[float | None, float | None]:
    """Find nearest support and resistance from peaks/troughs (TECH-04).

    Args:
        prices: List of close prices (chronological).
        order: Window size for peak/trough detection.

    Returns:
        Tuple of (nearest_support, nearest_resistance).
        Either can be None if no level found.
    """
    if len(prices) < 2 * order + 1:
        return None, None

    current_price = prices[-1]

    # Find resistance candidates (peaks)
    peak_indices = find_peaks_manual(prices, order=order)
    peak_prices = [prices[i] for i in peak_indices]

    # Find support candidates (troughs)
    trough_indices = find_troughs_manual(prices, order=order)
    trough_prices = [prices[i] for i in trough_indices]

    # Nearest support: highest trough below current price
    supports_below = [p for p in trough_prices if p < current_price]
    nearest_support = max(supports_below) if supports_below else None

    # Nearest resistance: lowest peak above current price
    resistances_above = [p for p in peak_prices if p > current_price]
    nearest_resistance = min(resistances_above) if resistances_above else None

    return nearest_support, nearest_resistance


def _is_valid(val) -> bool:
    """Check if a value is not None and not NaN."""
    if val is None:
        return False
    if isinstance(val, float) and np.isnan(val):
        return False
    return True


def _all_valid(*vals) -> bool:
    """Check if all values are valid (not None/NaN)."""
    return all(_is_valid(v) for v in vals)
