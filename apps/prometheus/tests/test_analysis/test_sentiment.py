"""Unit tests for sentiment aggregation and score_to_grade mapping."""

from datetime import UTC, datetime, timedelta

import pytest

from localstock.analysis.sentiment import aggregate_sentiment
from localstock.scoring import score_to_grade


class TestAggregateSentiment:
    """Tests for aggregate_sentiment() with exponential time decay."""

    def test_aggregate_sentiment_weighted(self):
        """Scores weighted by exponential decay — recent articles weight higher.

        With half_life=3 days:
        - age 0 days: weight = 1.0
        - age 2 days: weight = exp(-ln(2)/3 * 2) ≈ 0.63
        - age 5 days: weight = exp(-ln(2)/3 * 5) ≈ 0.315
        """
        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
        scores = [
            {"score": 0.8, "computed_at": now},  # age 0 days
            {"score": 0.6, "computed_at": now - timedelta(days=2)},  # age 2 days
            {"score": 0.3, "computed_at": now - timedelta(days=5)},  # age 5 days
        ]

        result = aggregate_sentiment(scores, now=now, half_life_days=3.0)

        assert result is not None
        # Recent (0.8) should pull average higher than simple mean (0.567)
        assert result > 0.567
        # But not as high as 0.8 since other scores pull down
        assert result < 0.8
        # Verify it's a reasonable value
        assert 0.6 < result < 0.75

    def test_aggregate_sentiment_empty(self):
        """Empty list returns None."""
        assert aggregate_sentiment([]) is None

    def test_aggregate_sentiment_single(self):
        """Single score returns that score regardless of age."""
        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
        scores = [{"score": 0.7, "computed_at": now}]
        result = aggregate_sentiment(scores, now=now)
        assert result == pytest.approx(0.7)

    def test_aggregate_sentiment_all_same_age(self):
        """Scores with same age give simple average."""
        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
        scores = [
            {"score": 0.8, "computed_at": now},
            {"score": 0.6, "computed_at": now},
            {"score": 0.4, "computed_at": now},
        ]
        result = aggregate_sentiment(scores, now=now)
        assert result == pytest.approx(0.6, abs=0.01)

    def test_aggregate_sentiment_old_articles_low_weight(self):
        """Very old article has negligible weight compared to recent ones."""
        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
        scores = [
            {"score": 0.9, "computed_at": now},  # age 0
            {"score": 0.1, "computed_at": now - timedelta(days=30)},  # age 30 days
        ]
        result = aggregate_sentiment(scores, now=now, half_life_days=3.0)
        assert result is not None
        # With 30-day-old article and 3-day half-life, old article weight ≈ 0.001
        # Result should be very close to 0.9
        assert result > 0.85


class TestScoreToGrade:
    """Tests for score_to_grade() mapping."""

    def test_score_to_grade_mapping(self):
        """Standard score values map to expected grades."""
        assert score_to_grade(85) == "A"
        assert score_to_grade(65) == "B"
        assert score_to_grade(45) == "C"
        assert score_to_grade(25) == "D"
        assert score_to_grade(10) == "F"

    def test_score_to_grade_boundaries(self):
        """Boundary values map correctly (A≥80, B≥60, C≥40, D≥20, F<20)."""
        assert score_to_grade(100) == "A"
        assert score_to_grade(80) == "A"
        assert score_to_grade(79.9) == "B"
        assert score_to_grade(60) == "B"
        assert score_to_grade(59.9) == "C"
        assert score_to_grade(40) == "C"
        assert score_to_grade(39.9) == "D"
        assert score_to_grade(20) == "D"
        assert score_to_grade(19.9) == "F"
        assert score_to_grade(0) == "F"
