"""Tests for TechnicalAnalyzer — technical indicators and volume analysis.

Covers TECH-01 (core indicators) and TECH-02 (volume analysis).
"""

import numpy as np
import pandas as pd
import pytest

from localstock.analysis.technical import TechnicalAnalyzer


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


class TestComputeIndicators:
    def test_returns_dataframe_with_indicator_columns(self, analyzer, ohlcv_250):
        result = analyzer.compute_indicators(ohlcv_250)
        # Use actual pandas-ta column names (verified at runtime)
        expected_cols = [
            "SMA_20", "SMA_50", "SMA_200",
            "EMA_12", "EMA_26", "RSI_14",
            "MACD_12_26_9", "MACDh_12_26_9", "MACDs_12_26_9",
            "BBL_20_2.0_2.0", "BBM_20_2.0_2.0", "BBU_20_2.0_2.0",
            "STOCHk_14_3_3", "STOCHd_14_3_3",
            "ADX_14", "OBV",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_sma_20_warmup_period(self, analyzer, ohlcv_250):
        result = analyzer.compute_indicators(ohlcv_250)
        assert result["SMA_20"].iloc[:19].isna().all()
        assert result["SMA_20"].iloc[19:].notna().any()

    def test_rsi_values_bounded(self, analyzer, ohlcv_250):
        result = analyzer.compute_indicators(ohlcv_250)
        rsi = result["RSI_14"].dropna()
        assert (rsi >= 0).all()
        assert (rsi <= 100).all()

    def test_empty_dataframe(self, analyzer):
        empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        result = analyzer.compute_indicators(empty)
        assert result.empty


class TestComputeVolumeAnalysis:
    def test_returns_volume_metrics(self, analyzer, ohlcv_250):
        result = analyzer.compute_volume_analysis(ohlcv_250)
        assert "avg_volume_20" in result
        assert "relative_volume" in result
        assert "volume_trend" in result

    def test_volume_trend_valid_values(self, analyzer, ohlcv_250):
        result = analyzer.compute_volume_analysis(ohlcv_250)
        assert result["volume_trend"] in ("increasing", "decreasing", "stable")

    def test_relative_volume_calculation(self, analyzer, ohlcv_250):
        result = analyzer.compute_volume_analysis(ohlcv_250)
        expected_avg = int(ohlcv_250["volume"].tail(20).mean())
        expected_rel = ohlcv_250["volume"].iloc[-1] / expected_avg
        assert result["avg_volume_20"] == pytest.approx(expected_avg, rel=0.01)
        assert result["relative_volume"] == pytest.approx(expected_rel, rel=0.01)


class TestToIndicatorRow:
    def test_maps_columns_to_model_keys(self, analyzer, ohlcv_250):
        indicators_df = analyzer.compute_indicators(ohlcv_250)
        vol = analyzer.compute_volume_analysis(ohlcv_250)
        row = analyzer.to_indicator_row("VNM", ohlcv_250, indicators_df, vol)
        assert row["symbol"] == "VNM"
        assert "sma_20" in row
        assert "rsi_14" in row
        assert "macd" in row
        assert "bb_upper" in row
        assert "avg_volume_20" in row
        assert "relative_volume" in row


class TestComputeCandlestickPatterns:
    """Tests for TechnicalAnalyzer.compute_candlestick_patterns() (SIGNAL-01).

    Covers: doji, inside_bar, hammer, shooting_star, engulfing_detected, engulfing_direction.
    """

    def test_doji_detected(self, analyzer, ohlcv_250):
        """Doji detected when body is very small relative to candle range."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_doji_not_present(self, analyzer, ohlcv_250):
        """Doji absent on normal full-body candle."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_inside_bar_detected(self, analyzer, ohlcv_250):
        """Inside bar detected when current H-L is within prior bar H-L."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_hammer_detected(self, analyzer):
        """Hammer detected when lower shadow >= 2x body and upper shadow <= 10% range."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_shooting_star_detected(self, analyzer):
        """Shooting star detected when upper shadow >= 2x body and lower shadow <= 10% range."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_engulfing_bullish(self, analyzer):
        """Bullish engulfing: prev bearish body fully contained by curr bullish body."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_engulfing_bearish(self, analyzer):
        """Bearish engulfing: prev bullish body fully contained by curr bearish body."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_empty_df(self, analyzer):
        """Returns all-False dict (not None, not raises) when df has < 2 rows (T-18-01 guard)."""
        pytest.skip("Not yet implemented — Wave 1")


class TestComputeVolumeDivergence:
    """Tests for TechnicalAnalyzer.compute_volume_divergence() (SIGNAL-02).

    Covers: MFI thresholds, liquidity gate, short-df guard, output shape.
    """

    def test_bullish_signal(self, analyzer):
        """Returns dict with signal='bullish' when MFI > 70."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_bearish_signal(self, analyzer):
        """Returns dict with signal='bearish' when MFI < 30."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_neutral_signal(self, analyzer):
        """Returns dict with signal='neutral' when 30 <= MFI <= 70."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_low_liquidity_gate(self, analyzer):
        """Returns None when avg_volume_20 < 100_000 (D-04)."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_short_df(self, analyzer):
        """Returns None when df has < 20 rows (can't compute avg_volume_20)."""
        pytest.skip("Not yet implemented — Wave 1")

    def test_output_shape(self, analyzer):
        """Output dict has exactly keys: signal, value, indicator (D-02)."""
        pytest.skip("Not yet implemented — Wave 1")
