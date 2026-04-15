"""Unit tests for OllamaClient SentimentResult Pydantic model.

Tests schema structure and validation — does NOT require a running Ollama server.
"""

import pytest
from pydantic import ValidationError

from localstock.ai.client import SentimentResult


class TestSentimentResultModel:
    """Tests for SentimentResult Pydantic model schema and validation."""

    def test_sentiment_result_model_schema(self):
        """SentimentResult.model_json_schema() contains required keys."""
        schema = SentimentResult.model_json_schema()
        properties = schema.get("properties", {})
        assert "sentiment" in properties
        assert "score" in properties
        assert "reason" in properties

    def test_sentiment_result_validation_valid(self):
        """Valid SentimentResult construction succeeds."""
        result = SentimentResult(sentiment="positive", score=0.8, reason="Tốt")
        assert result.sentiment == "positive"
        assert result.score == 0.8
        assert result.reason == "Tốt"

    def test_sentiment_result_score_boundaries(self):
        """Score at boundaries (0.0 and 1.0) are valid."""
        low = SentimentResult(sentiment="negative", score=0.0, reason="Xấu")
        assert low.score == 0.0

        high = SentimentResult(sentiment="positive", score=1.0, reason="Rất tốt")
        assert high.score == 1.0

    def test_sentiment_result_score_out_of_range(self):
        """Score outside 0.0-1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            SentimentResult(sentiment="positive", score=1.5, reason="Too high")

        with pytest.raises(ValidationError):
            SentimentResult(sentiment="negative", score=-0.1, reason="Too low")

    def test_sentiment_result_neutral(self):
        """Neutral sentiment with 0.5 score is valid."""
        result = SentimentResult(sentiment="neutral", score=0.5, reason="Không liên quan")
        assert result.sentiment == "neutral"
        assert result.score == 0.5
