"""Tests for signal computation functions (SIGNAL-03).

Covers compute_sector_momentum() — sector momentum scalar for LLM prompt injection.
"""

import pytest

from localstock.analysis.signals import compute_sector_momentum


class TestComputeSectorMomentum:
    """Tests for compute_sector_momentum() (SIGNAL-03)."""

    def test_strong_inflow(self):
        """avg_score_change > 2.0 → label 'strong_inflow'."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_mild_inflow(self):
        """0 < avg_score_change <= 2.0 → label 'mild_inflow'."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_mild_outflow(self):
        """-2.0 <= avg_score_change < 0 → label 'mild_outflow'."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_strong_outflow(self):
        """avg_score_change < -2.0 → label 'strong_outflow'."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_none_input(self):
        """Returns None when sector_data is None — no exception raised."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_none_score_change(self):
        """Returns None when avg_score_change is None in sector_data dict."""
        pytest.skip("Not yet implemented — Wave 2")

    def test_output_shape(self):
        """Output dict has exactly keys: label, score_change, group_code."""
        pytest.skip("Not yet implemented — Wave 2")
