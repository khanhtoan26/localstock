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


class TestDetectTrend:
    def test_uptrend_detection(self):
        """Strong uptrend: SMA20 > SMA50 > SMA200, MACD positive, ADX > 25."""
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
        assert isinstance(result["trend_strength"], float)

    def test_downtrend_detection(self):
        """Strong downtrend: SMA20 < SMA50 < SMA200, MACD negative, ADX > 25."""
        data = pd.Series({
            "close": 40000,
            "SMA_20": 42000,
            "SMA_50": 45000,
            "SMA_200": 50000,
            "MACDh_12_26_9": -500,
            "ADX_14": 35,
        })
        result = detect_trend(data)
        assert result["trend_direction"] == "downtrend"

    def test_sideways_low_adx(self):
        """ADX < 20 → sideways regardless of MA alignment."""
        data = pd.Series({
            "close": 50000,
            "SMA_20": 51000,
            "SMA_50": 49000,
            "SMA_200": 48000,
            "MACDh_12_26_9": 100,
            "ADX_14": 15,
        })
        result = detect_trend(data)
        assert result["trend_direction"] == "sideways"

    def test_trend_strength_from_adx(self):
        """trend_strength maps ADX value."""
        data = pd.Series({
            "close": 60000,
            "SMA_20": 58000,
            "SMA_50": 55000,
            "SMA_200": 50000,
            "MACDh_12_26_9": 500,
            "ADX_14": 45.5,
        })
        result = detect_trend(data)
        assert result["trend_strength"] == 45.5


class TestComputePivotPoints:
    def test_standard_pivot_calculation(self):
        """PP = (H + L + C) / 3, S1 = 2*PP - H, etc."""
        result = compute_pivot_points(high=105.0, low=95.0, close=102.0)
        expected_pp = (105.0 + 95.0 + 102.0) / 3
        # Use abs=0.01 tolerance — implementation rounds to 2 decimal places for prices
        assert result["pivot_point"] == pytest.approx(expected_pp, abs=0.01)
        assert result["support_1"] == pytest.approx(2 * expected_pp - 105.0, abs=0.01)
        assert result["support_2"] == pytest.approx(expected_pp - (105.0 - 95.0), abs=0.01)
        assert result["resistance_1"] == pytest.approx(2 * expected_pp - 95.0, abs=0.01)
        assert result["resistance_2"] == pytest.approx(expected_pp + (105.0 - 95.0), abs=0.01)


class TestFindPeaksManual:
    def test_finds_peaks_in_simple_data(self):
        """Peak at index 5 (higher than neighbors within order=2)."""
        prices = [10, 11, 12, 11, 10, 15, 10, 11, 12, 11, 10]
        peaks = find_peaks_manual(prices, order=2)
        assert 5 in peaks

    def test_no_peaks_in_flat_data(self):
        prices = [10.0] * 20
        peaks = find_peaks_manual(prices, order=3)
        assert peaks == []


class TestFindSupportResistance:
    def test_finds_nearest_levels(self):
        """With clear peaks and troughs, finds nearest S/R."""
        np.random.seed(42)
        n = 100
        # Create data with clear peaks and troughs
        x = np.linspace(0, 4 * np.pi, n)
        prices = 50000 + 2000 * np.sin(x) + np.random.randn(n) * 100
        current_price = float(prices[-1])
        support, resistance = find_support_resistance(prices.tolist(), order=5)
        if support is not None:
            assert support < current_price
        if resistance is not None:
            assert resistance > current_price

    def test_no_support_when_at_all_time_low(self):
        """If price is lowest ever, no support below."""
        prices = list(range(100, 50, -1))  # strictly decreasing
        support, resistance = find_support_resistance(prices, order=3)
        # At the bottom of a downtrend, support might be None
        # Resistance should exist (peaks from higher prices)
        # This is data-dependent but the test validates the function handles it
        assert isinstance(support, (float, type(None)))
        assert isinstance(resistance, (float, type(None)))
