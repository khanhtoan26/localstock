"""Tests for MACRO_SECTOR_IMPACT rules dict and get_macro_impact()."""

import pytest

from localstock.analysis.industry import VN_INDUSTRY_GROUPS
from localstock.macro.impact import MACRO_SECTOR_IMPACT, get_macro_impact

# All 20 group codes from industry.py
ALL_SECTOR_CODES = [g["group_code"] for g in VN_INDUSTRY_GROUPS]

# All 8 expected conditions
EXPECTED_CONDITIONS = [
    "interest_rate_rising",
    "interest_rate_falling",
    "vnd_weakening",
    "vnd_strengthening",
    "cpi_rising",
    "cpi_falling",
    "gdp_growing",
    "gdp_slowing",
]


class TestMacroSectorImpactStructure:
    """Test the MACRO_SECTOR_IMPACT dict structure."""

    def test_has_all_8_conditions(self):
        """MACRO_SECTOR_IMPACT should have keys for all 8 conditions."""
        for condition in EXPECTED_CONDITIONS:
            assert condition in MACRO_SECTOR_IMPACT, f"Missing condition: {condition}"

    def test_each_condition_has_all_20_sectors(self):
        """Each condition should contain entries for all 20 VN_INDUSTRY_GROUPS."""
        for condition in EXPECTED_CONDITIONS:
            sector_map = MACRO_SECTOR_IMPACT[condition]
            for code in ALL_SECTOR_CODES:
                assert code in sector_map, (
                    f"Missing sector {code} in condition {condition}"
                )

    def test_all_multipliers_in_valid_range(self):
        """All impact multipliers should be in [-1.0, +1.0]."""
        for condition, sectors in MACRO_SECTOR_IMPACT.items():
            for sector, value in sectors.items():
                assert -1.0 <= value <= 1.0, (
                    f"Out of range: {condition}/{sector} = {value}"
                )

    def test_other_sector_always_zero(self):
        """OTHER sector should always have 0.0 impact."""
        for condition in EXPECTED_CONDITIONS:
            assert MACRO_SECTOR_IMPACT[condition]["OTHER"] == 0.0, (
                f"OTHER should be 0.0 for {condition}"
            )


class TestGetMacroImpact:
    """Test get_macro_impact() function."""

    def test_banking_interest_rate_rising_positive(self):
        """Banking benefits from rising interest rates (wider NIM)."""
        result = get_macro_impact("BANKING", {"interest_rate": "rising"})
        assert result > 0.0

    def test_real_estate_interest_rate_rising_negative(self):
        """Real estate hurt by rising rates (higher borrowing costs)."""
        result = get_macro_impact("REAL_ESTATE", {"interest_rate": "rising"})
        assert result < 0.0

    def test_other_sector_always_neutral(self):
        """OTHER sector should always return 0.0."""
        result = get_macro_impact("OTHER", {"interest_rate": "rising"})
        assert result == 0.0

        result = get_macro_impact(
            "OTHER", {"interest_rate": "rising", "gdp": "growing"}
        )
        assert result == 0.0

    def test_unknown_sector_returns_zero(self):
        """Unknown sector code should return 0.0."""
        result = get_macro_impact("UNKNOWN_SECTOR", {"interest_rate": "rising"})
        assert result == 0.0

    def test_empty_conditions_returns_zero(self):
        """No macro conditions should return 0.0."""
        result = get_macro_impact("BANKING", {})
        assert result == 0.0

    def test_multiple_conditions_aggregate(self):
        """Multiple conditions should sum and clamp to [-1, +1]."""
        result = get_macro_impact(
            "BANKING",
            {"interest_rate": "rising", "gdp": "growing"},
        )
        # Banking benefits from both — should be clamped to <= 1.0
        assert -1.0 <= result <= 1.0

    def test_result_always_clamped(self):
        """Result should always be in [-1.0, +1.0] even with many conditions."""
        # Apply all conditions at once
        all_conditions = {
            "interest_rate": "rising",
            "exchange_rate": "weakening",
            "cpi": "rising",
            "gdp": "growing",
        }
        result = get_macro_impact("BANKING", all_conditions)
        assert -1.0 <= result <= 1.0

    def test_stable_conditions_ignored(self):
        """Stable conditions should not map to any impact key."""
        result = get_macro_impact("BANKING", {"interest_rate": "stable"})
        assert result == 0.0
