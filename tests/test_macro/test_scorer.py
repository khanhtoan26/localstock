"""Tests for normalize_macro_score() function."""

import pytest

from localstock.macro.scorer import normalize_macro_score


class TestNormalizeMacroScore:
    """Test normalize_macro_score function."""

    def test_favorable_conditions_above_50(self):
        """Banking + rising interest rates → score > 50."""
        score = normalize_macro_score("BANKING", {"interest_rate": "rising"})
        assert score > 50.0

    def test_unfavorable_conditions_below_50(self):
        """Real estate + rising interest rates → score < 50."""
        score = normalize_macro_score("REAL_ESTATE", {"interest_rate": "rising"})
        assert score < 50.0

    def test_empty_conditions_returns_50(self):
        """No macro conditions → neutral 50.0."""
        score = normalize_macro_score("BANKING", {})
        assert score == 50.0

    def test_none_sector_returns_50(self):
        """None sector → neutral 50.0."""
        score = normalize_macro_score(None, {"interest_rate": "rising"})
        assert score == 50.0

    def test_always_in_0_100_range(self):
        """Score should always be in [0, 100]."""
        conditions_list = [
            {"interest_rate": "rising"},
            {"interest_rate": "falling"},
            {"exchange_rate": "weakening"},
            {"exchange_rate": "strengthening"},
            {"cpi": "rising"},
            {"cpi": "falling"},
            {"gdp": "growing"},
            {"gdp": "slowing"},
            {
                "interest_rate": "rising",
                "exchange_rate": "weakening",
                "cpi": "rising",
                "gdp": "growing",
            },
        ]
        sectors = ["BANKING", "REAL_ESTATE", "STEEL", "SEAFOOD", "OTHER"]
        for sector in sectors:
            for conditions in conditions_list:
                score = normalize_macro_score(sector, conditions)
                assert 0.0 <= score <= 100.0, (
                    f"Out of range: {sector} + {conditions} = {score}"
                )

    def test_neutral_impact_equals_50(self):
        """OTHER sector should always return 50.0 (zero impact)."""
        score = normalize_macro_score("OTHER", {"interest_rate": "rising"})
        assert score == 50.0

    def test_formula_positive_impact(self):
        """Verify formula: score = 50 + impact * 50."""
        # Use a known impact case
        from localstock.macro.impact import get_macro_impact

        impact = get_macro_impact("BANKING", {"interest_rate": "rising"})
        expected = 50 + (impact * 50)
        expected = max(0.0, min(100.0, expected))

        score = normalize_macro_score("BANKING", {"interest_rate": "rising"})
        assert abs(score - expected) < 0.01

    def test_stable_condition_returns_50(self):
        """Stable conditions produce no impact → score 50."""
        score = normalize_macro_score("BANKING", {"interest_rate": "stable"})
        assert score == 50.0
