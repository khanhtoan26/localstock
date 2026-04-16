"""Tests for scoring normalizers — convert raw indicators to 0-100 scores."""

import pytest

from localstock.scoring.normalizer import (
    normalize_fundamental_score,
    normalize_sentiment_score,
    normalize_technical_score,
)


class TestNormalizeTechnicalScore:
    """Test normalize_technical_score with various indicator combinations."""

    def test_normalize_tech_oversold_uptrend(self):
        """RSI oversold + uptrend + positive MACD + near BB lower + high volume → bullish ≥ 75."""
        data = {
            "rsi_14": 28.0,
            "trend_direction": "uptrend",
            "trend_strength": 60.0,
            "macd_histogram": 1.5,
            "bb_upper": 110.0,
            "bb_lower": 90.0,
            "bb_middle": 100.0,
            "close": 91.0,  # near bb_lower
            "relative_volume": 1.5,
            "volume_trend": "increasing",
        }
        score = normalize_technical_score(data)
        assert score >= 75, f"Expected ≥ 75 for bullish setup, got {score}"

    def test_normalize_tech_overbought_downtrend(self):
        """RSI overbought + downtrend + negative MACD + near BB upper + low volume → bearish ≤ 30."""
        data = {
            "rsi_14": 75.0,
            "trend_direction": "downtrend",
            "trend_strength": 60.0,
            "macd_histogram": -2.0,
            "bb_upper": 110.0,
            "bb_lower": 90.0,
            "bb_middle": 100.0,
            "close": 109.0,  # near bb_upper
            "relative_volume": 0.5,
            "volume_trend": "decreasing",
        }
        score = normalize_technical_score(data)
        assert score <= 30, f"Expected ≤ 30 for bearish setup, got {score}"

    def test_normalize_tech_neutral(self):
        """Neutral RSI + sideways + zero MACD + mid-BB + avg volume → 40-60."""
        data = {
            "rsi_14": 50.0,
            "trend_direction": "sideways",
            "trend_strength": 30.0,
            "macd_histogram": 0.0,
            "bb_upper": 110.0,
            "bb_lower": 90.0,
            "bb_middle": 100.0,
            "close": 100.0,  # at mid-BB
            "relative_volume": 1.0,
            "volume_trend": "stable",
        }
        score = normalize_technical_score(data)
        assert 40 <= score <= 60, f"Expected 40-60 for neutral setup, got {score}"

    def test_normalize_tech_all_none(self):
        """All indicator values None → returns 0.0 (not crash)."""
        data = {
            "rsi_14": None,
            "trend_direction": None,
            "trend_strength": None,
            "macd_histogram": None,
            "bb_upper": None,
            "bb_lower": None,
            "bb_middle": None,
            "close": None,
            "relative_volume": None,
            "volume_trend": None,
        }
        score = normalize_technical_score(data)
        assert score == 0.0

    def test_normalize_tech_empty_dict(self):
        """Empty dict → returns 0.0."""
        score = normalize_technical_score({})
        assert score == 0.0


class TestNormalizeFundamentalScore:
    """Test normalize_fundamental_score with various ratio combinations."""

    def test_normalize_fund_strong(self):
        """Low P/E, high ROE, high growth, low D/E → score ≥ 70."""
        data = {
            "pe_ratio": 8.0,
            "roe": 25.0,
            "roa": 15.0,
            "profit_yoy": 30.0,
            "revenue_yoy": 25.0,
            "de_ratio": 0.3,
        }
        score = normalize_fundamental_score(data)
        assert score >= 70, f"Expected ≥ 70 for strong fundamentals, got {score}"

    def test_normalize_fund_weak(self):
        """High P/E, low ROE, negative growth, high D/E → score ≤ 30."""
        data = {
            "pe_ratio": 50.0,
            "roe": 3.0,
            "roa": 1.0,
            "profit_yoy": -20.0,
            "revenue_yoy": -10.0,
            "de_ratio": 3.0,
        }
        score = normalize_fundamental_score(data)
        assert score <= 30, f"Expected ≤ 30 for weak fundamentals, got {score}"

    def test_normalize_fund_all_none(self):
        """All ratio values None → returns 0.0."""
        data = {
            "pe_ratio": None,
            "roe": None,
            "roa": None,
            "profit_yoy": None,
            "revenue_yoy": None,
            "de_ratio": None,
        }
        score = normalize_fundamental_score(data)
        assert score == 0.0

    def test_normalize_fund_empty_dict(self):
        """Empty dict → returns 0.0."""
        score = normalize_fundamental_score({})
        assert score == 0.0


class TestNormalizeSentimentScore:
    """Test normalize_sentiment_score linear scaling."""

    def test_normalize_sentiment_to_100(self):
        """Sentiment 0.8 → 80.0."""
        assert normalize_sentiment_score(0.8) == pytest.approx(80.0)

    def test_normalize_sentiment_zero(self):
        """Sentiment 0.0 → 0.0."""
        assert normalize_sentiment_score(0.0) == pytest.approx(0.0)

    def test_normalize_sentiment_one(self):
        """Sentiment 1.0 → 100.0."""
        assert normalize_sentiment_score(1.0) == pytest.approx(100.0)

    def test_normalize_sentiment_mid(self):
        """Sentiment 0.5 → 50.0."""
        assert normalize_sentiment_score(0.5) == pytest.approx(50.0)


class TestScoringConfig:
    """Test ScoringConfig dataclass."""

    def test_scoring_config_from_settings(self):
        """ScoringConfig reads weights from Settings defaults correctly."""
        from localstock.scoring.config import ScoringConfig

        config = ScoringConfig.from_settings()
        assert config.weight_technical == pytest.approx(0.30)
        assert config.weight_fundamental == pytest.approx(0.30)
        assert config.weight_sentiment == pytest.approx(0.20)
        assert config.weight_macro == pytest.approx(0.20)

    def test_scoring_config_manual(self):
        """ScoringConfig can be created manually."""
        from localstock.scoring.config import ScoringConfig

        config = ScoringConfig(
            weight_technical=0.50,
            weight_fundamental=0.30,
            weight_sentiment=0.20,
            weight_macro=0.0,
        )
        assert config.weight_technical == 0.50
        assert config.weight_fundamental == 0.30
