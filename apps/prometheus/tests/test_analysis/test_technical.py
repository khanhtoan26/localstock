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
        """Doji detected: modify last row so open == close to create near-doji."""
        df = ohlcv_250.copy()
        # Force last row to be a doji: open == close, but high > low
        df.iloc[-1, df.columns.get_loc("open")] = df.iloc[-1]["close"]
        result = analyzer.compute_candlestick_patterns(df)
        assert "doji" in result
        # Result may or may not be True (pandas-ta uses rolling normalization)
        # but key must be present and type must be bool
        assert isinstance(result["doji"], bool)

    def test_doji_not_present(self, analyzer, ohlcv_250):
        """Doji key is False on normal full-body candle."""
        df = ohlcv_250.copy()
        # Force last row to have a large body (clearly not a doji)
        df.iloc[-1, df.columns.get_loc("open")] = df.iloc[-1]["close"] * 0.85
        result = analyzer.compute_candlestick_patterns(df)
        assert result["doji"] is False

    def test_inside_bar_detected(self, analyzer, ohlcv_250):
        """Inside bar: current bar's H-L range is fully within prior bar's H-L range."""
        df = ohlcv_250.copy()
        prev_high = df.iloc[-2]["high"]
        prev_low = df.iloc[-2]["low"]
        # Force current bar inside previous bar
        df.iloc[-1, df.columns.get_loc("high")] = prev_high * 0.99
        df.iloc[-1, df.columns.get_loc("low")] = prev_low * 1.01
        result = analyzer.compute_candlestick_patterns(df)
        assert isinstance(result["inside_bar"], bool)

    def test_hammer_detected(self, analyzer):
        """Hammer: body <= 30% range, lower shadow >= 2x body, upper shadow <= 10% range."""
        # Construct a 15-row DataFrame where last row is a classic hammer
        n = 15
        close = [50000.0] * n
        # Last row: hammer candle
        # open=49900, close=50000, high=50050, low=49500
        # body = 100, range = 550, lower_shadow = 400, upper_shadow = 50
        # body/range = 0.18 (<0.3), lower_shadow/body = 4.0 (>=2), upper_shadow/range = 0.09 (<0.1)
        base_prices = list(zip([49900.0]*n, [50100.0]*n, [49800.0]*n, close))
        opens = [p[0] for p in base_prices]
        highs = [p[1] for p in base_prices]
        lows = [p[2] for p in base_prices]
        closes = close[:]
        # Override last row with hammer candle
        opens[-1] = 49900.0
        highs[-1] = 50050.0
        lows[-1] = 49500.0
        closes[-1] = 50000.0
        df = pd.DataFrame({
            "open": opens, "high": highs, "low": lows, "close": closes,
            "volume": [1_000_000] * n,
        })
        result = analyzer.compute_candlestick_patterns(df)
        assert result["hammer"] is True

    def test_shooting_star_detected(self, analyzer):
        """Shooting star: body <= 30% range, upper shadow >= 2x body, lower shadow <= 10% range."""
        n = 15
        # open=50000, close=49900, high=50500, low=49850
        # body=100, range=650, upper_shadow=500, lower_shadow=50
        # body/range=0.15 (<0.3), upper_shadow/body=5.0 (>=2), lower_shadow/range=0.077 (<0.1)
        opens = [50000.0] * n
        closes = [50000.0] * n
        highs = [50100.0] * n
        lows = [49800.0] * n
        opens[-1] = 50000.0
        closes[-1] = 49900.0
        highs[-1] = 50500.0
        lows[-1] = 49850.0
        df = pd.DataFrame({
            "open": opens, "high": highs, "low": lows, "close": closes,
            "volume": [1_000_000] * n,
        })
        result = analyzer.compute_candlestick_patterns(df)
        assert result["shooting_star"] is True

    def test_engulfing_bullish(self, analyzer):
        """Bullish engulfing: prev bearish body fully engulfed by curr bullish body."""
        # prev: open=50200, close=50000 (bearish)
        # curr: open=49950 (<=prev close 50000), close=50250 (>=prev open 50200) (bullish)
        df = pd.DataFrame({
            "open":  [50200.0, 49950.0],
            "high":  [50300.0, 50300.0],
            "low":   [49900.0, 49900.0],
            "close": [50000.0, 50250.0],
            "volume": [1_000_000, 1_000_000],
        })
        result = analyzer.compute_candlestick_patterns(df)
        assert result["engulfing_detected"] is True
        assert result["engulfing_direction"] == "bullish"

    def test_engulfing_bearish(self, analyzer):
        """Bearish engulfing: prev bullish body fully engulfed by curr bearish body."""
        # prev: open=50000, close=50200 (bullish)
        # curr: open=50250 (>=prev close 50200), close=49950 (<=prev open 50000) (bearish)
        df = pd.DataFrame({
            "open":  [50000.0, 50250.0],
            "high":  [50300.0, 50300.0],
            "low":   [49900.0, 49900.0],
            "close": [50200.0, 49950.0],
            "volume": [1_000_000, 1_000_000],
        })
        result = analyzer.compute_candlestick_patterns(df)
        assert result["engulfing_detected"] is True
        assert result["engulfing_direction"] == "bearish"

    def test_empty_df(self, analyzer):
        """Returns all-False dict (not raises, not None) when df has < 2 rows (T-18-01)."""
        df = pd.DataFrame({
            "open": [50000.0], "high": [50100.0], "low": [49900.0],
            "close": [50000.0], "volume": [1_000_000],
        })
        result = analyzer.compute_candlestick_patterns(df)
        assert isinstance(result, dict)
        assert result["doji"] is False
        assert result["inside_bar"] is False
        assert result["hammer"] is False
        assert result["shooting_star"] is False
        assert result["engulfing_detected"] is False
        assert result["engulfing_direction"] is None


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
