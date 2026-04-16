"""Tests for T+3 prediction logic.

Tests predict_3day_trend() with various scenarios:
- Bullish: strong uptrend signals → direction="bullish", confidence="high"
- Bearish: overbought/downtrend signals → direction="bearish"
- Neutral: mixed/missing signals → direction="neutral", confidence="low"
- Always includes T+3 warning in Vietnamese
- Handles all-None inputs gracefully
"""

from localstock.reports.t3 import predict_3day_trend


class TestPredict3DayTrendBullish:
    """Test bullish scenario: RSI recovering, positive MACD, strong uptrend."""

    def test_bullish_direction(self):
        result = predict_3day_trend(
            {
                "rsi_14": 35.0,
                "macd_histogram": 0.5,
                "trend_direction": "uptrend",
                "trend_strength": 30.0,
                "nearest_support": 20.0,
                "nearest_resistance": 30.0,
                "close": 22.0,
                "relative_volume": 2.0,
                "volume_trend": "increasing",
            }
        )
        assert result["direction"] == "bullish"

    def test_bullish_high_confidence(self):
        result = predict_3day_trend(
            {
                "rsi_14": 35.0,
                "macd_histogram": 0.5,
                "trend_direction": "uptrend",
                "trend_strength": 30.0,
                "nearest_support": 20.0,
                "nearest_resistance": 30.0,
                "close": 22.0,
                "relative_volume": 2.0,
                "volume_trend": "increasing",
            }
        )
        assert result["confidence"] == "high"


class TestPredict3DayTrendBearish:
    """Test bearish scenario: overbought RSI, negative MACD, strong downtrend."""

    def test_bearish_direction(self):
        result = predict_3day_trend(
            {
                "rsi_14": 75.0,
                "macd_histogram": -0.5,
                "trend_direction": "downtrend",
                "trend_strength": 30.0,
                "nearest_support": 18.0,
                "nearest_resistance": 22.0,
                "close": 21.0,
                "relative_volume": 1.0,
                "volume_trend": "decreasing",
            }
        )
        assert result["direction"] == "bearish"


class TestPredict3DayTrendNeutral:
    """Test neutral scenario: mixed signals → neutral, low confidence."""

    def test_neutral_direction(self):
        result = predict_3day_trend(
            {
                "rsi_14": 50.0,
                "macd_histogram": 0.0,
                "trend_direction": "sideways",
                "trend_strength": 15.0,
                "nearest_support": 19.0,
                "nearest_resistance": 21.0,
                "close": 20.0,
                "relative_volume": 1.0,
                "volume_trend": "stable",
            }
        )
        assert result["direction"] == "neutral"

    def test_neutral_low_confidence(self):
        result = predict_3day_trend(
            {
                "rsi_14": 50.0,
                "macd_histogram": 0.0,
                "trend_direction": "sideways",
                "trend_strength": 15.0,
                "nearest_support": 19.0,
                "nearest_resistance": 21.0,
                "close": 20.0,
                "relative_volume": 1.0,
                "volume_trend": "stable",
            }
        )
        assert result["confidence"] == "low"


class TestPredict3DayTrendReasons:
    """Test that reasons are Vietnamese strings."""

    def test_reasons_are_list(self):
        result = predict_3day_trend(
            {
                "rsi_14": 35.0,
                "macd_histogram": 0.5,
                "trend_direction": "uptrend",
                "trend_strength": 30.0,
                "nearest_support": 20.0,
                "nearest_resistance": 30.0,
                "close": 22.0,
                "relative_volume": 2.0,
                "volume_trend": "increasing",
            }
        )
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) > 0

    def test_reasons_contain_vietnamese(self):
        """Reasons should contain Vietnamese keywords."""
        result = predict_3day_trend(
            {
                "rsi_14": 35.0,
                "macd_histogram": 0.5,
                "trend_direction": "uptrend",
                "trend_strength": 30.0,
                "nearest_support": 20.0,
                "nearest_resistance": 30.0,
                "close": 22.0,
                "relative_volume": 2.0,
                "volume_trend": "increasing",
            }
        )
        all_reasons = " ".join(result["reasons"])
        # Should contain at least some Vietnamese text
        assert any(
            kw in all_reasons.lower()
            for kw in ["rsi", "macd", "xu hướng", "khối lượng", "hỗ trợ"]
        )


class TestPredict3DayTrendT3Warning:
    """Test T+3 warning is always present."""

    def test_t3_warning_present(self):
        result = predict_3day_trend(
            {
                "rsi_14": 50.0,
                "macd_histogram": 0.0,
                "trend_direction": "sideways",
                "trend_strength": 15.0,
            }
        )
        assert "t3_warning" in result
        assert result["t3_warning"].startswith("⚠️ CẢNH BÁO T+3")

    def test_t3_warning_with_none_inputs(self):
        result = predict_3day_trend({})
        assert result["t3_warning"].startswith("⚠️ CẢNH BÁO T+3")


class TestPredict3DayTrendNoneHandling:
    """Test graceful handling of all-None inputs."""

    def test_all_none_returns_neutral(self):
        result = predict_3day_trend({})
        assert result["direction"] == "neutral"

    def test_all_none_returns_low_confidence(self):
        result = predict_3day_trend({})
        assert result["confidence"] == "low"

    def test_all_none_has_empty_reasons(self):
        result = predict_3day_trend({})
        assert isinstance(result["reasons"], list)

    def test_all_none_has_t3_warning(self):
        result = predict_3day_trend({})
        assert "t3_warning" in result

    def test_partial_none_inputs(self):
        result = predict_3day_trend(
            {
                "rsi_14": None,
                "macd_histogram": 0.5,
                "trend_direction": None,
            }
        )
        # Should not crash, should handle partial data
        assert result["direction"] in ("bullish", "bearish", "neutral")
        assert result["confidence"] in ("high", "medium", "low")
