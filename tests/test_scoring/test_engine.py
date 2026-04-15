"""Tests for composite scoring engine — weighted combination with missing dimensions."""

import pytest

from localstock.scoring.config import ScoringConfig
from localstock.scoring.engine import compute_composite


@pytest.fixture
def default_config():
    """Default scoring config matching Settings defaults."""
    return ScoringConfig(
        weight_technical=0.35,
        weight_fundamental=0.35,
        weight_sentiment=0.30,
        weight_macro=0.0,
    )


class TestCompositeScoring:
    """Test compute_composite with various dimension combinations."""

    def test_composite_all_dimensions(self, default_config):
        """tech=80, fund=70, sent=60 → total=70.5, grade=B, dims=3."""
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=70.0, sent=60.0, macro=None,
            config=default_config,
        )
        # 80*0.35 + 70*0.35 + 60*0.30 = 28+24.5+18 = 70.5
        assert total == pytest.approx(70.5)
        assert grade == "B"
        assert dims == 3

    def test_composite_missing_sentiment(self, default_config):
        """tech=80, fund=70, sent=None → redistribute → total=75.0, grade=B, dims=2."""
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=70.0, sent=None, macro=None,
            config=default_config,
        )
        # Redistribute: tech=0.35/0.70=0.50, fund=0.35/0.70=0.50
        # 80*0.5 + 70*0.5 = 40+35 = 75.0
        assert total == pytest.approx(75.0)
        assert grade == "B"
        assert dims == 2

    def test_composite_only_technical(self, default_config):
        """tech=60, fund=None, sent=None → weight=1.0 → total=60.0, grade=B."""
        total, grade, dims, weights = compute_composite(
            tech=60.0, fund=None, sent=None, macro=None,
            config=default_config,
        )
        assert total == pytest.approx(60.0)
        assert grade == "B"
        assert dims == 1

    def test_composite_no_dimensions(self, default_config):
        """All None → total=0.0, grade=F, dims=0."""
        total, grade, dims, weights = compute_composite(
            tech=None, fund=None, sent=None, macro=None,
            config=default_config,
        )
        assert total == pytest.approx(0.0)
        assert grade == "F"
        assert dims == 0
        assert weights == {}

    def test_composite_grade_A(self, default_config):
        """High scores → grade A."""
        total, grade, dims, weights = compute_composite(
            tech=90.0, fund=85.0, sent=80.0, macro=None,
            config=default_config,
        )
        # 90*0.35 + 85*0.35 + 80*0.30 = 31.5+29.75+24 = 85.25
        assert total >= 80
        assert grade == "A"

    def test_composite_grade_F(self, default_config):
        """Low scores → grade F."""
        total, grade, dims, weights = compute_composite(
            tech=10.0, fund=5.0, sent=15.0, macro=None,
            config=default_config,
        )
        # 10*0.35 + 5*0.35 + 15*0.30 = 3.5+1.75+4.5 = 9.75
        assert total <= 19
        assert grade == "F"

    def test_composite_weights_json(self, default_config):
        """Returns actual normalized weights used."""
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=70.0, sent=None, macro=None,
            config=default_config,
        )
        # Only tech and fund used → weights redistributed
        assert "technical" in weights
        assert "fundamental" in weights
        assert "sentiment" not in weights
        assert weights["technical"] == pytest.approx(0.5)
        assert weights["fundamental"] == pytest.approx(0.5)

    def test_composite_custom_weights(self):
        """Custom config with 50/50 tech/fund, no sentiment."""
        config = ScoringConfig(
            weight_technical=0.50,
            weight_fundamental=0.50,
            weight_sentiment=0.0,
            weight_macro=0.0,
        )
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=60.0, sent=None, macro=None,
            config=config,
        )
        # 80*0.5 + 60*0.5 = 70.0
        assert total == pytest.approx(70.0)
        assert grade == "B"
        assert dims == 2

    def test_composite_with_macro(self):
        """Include macro dimension when available."""
        config = ScoringConfig(
            weight_technical=0.30,
            weight_fundamental=0.30,
            weight_sentiment=0.20,
            weight_macro=0.20,
        )
        total, grade, dims, weights = compute_composite(
            tech=80.0, fund=70.0, sent=60.0, macro=50.0,
            config=config,
        )
        # 80*0.3 + 70*0.3 + 60*0.2 + 50*0.2 = 24+21+12+10 = 67.0
        assert total == pytest.approx(67.0)
        assert grade == "B"
        assert dims == 4

    def test_composite_clamp_to_100(self):
        """Score should never exceed 100."""
        config = ScoringConfig(
            weight_technical=1.0,
            weight_fundamental=0.0,
            weight_sentiment=0.0,
            weight_macro=0.0,
        )
        total, grade, dims, weights = compute_composite(
            tech=100.0, fund=None, sent=None, macro=None,
            config=config,
        )
        assert total <= 100.0
