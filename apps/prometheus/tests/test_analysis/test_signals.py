"""Tests for signal computation functions (SIGNAL-03).

Covers compute_sector_momentum() — sector momentum scalar for LLM prompt injection.
"""

import json

import pytest

from localstock.analysis.signals import compute_sector_momentum


class TestComputeSectorMomentum:
    """Tests for compute_sector_momentum() (SIGNAL-03)."""

    def test_strong_inflow(self):
        """avg_score_change > 2.0 → label 'strong_inflow'."""
        data = {"avg_score_change": 3.5, "avg_score": 72.0, "group_code": "BKS"}
        result = compute_sector_momentum(data)
        assert result is not None
        assert result["label"] == "strong_inflow"
        assert result["score_change"] == pytest.approx(3.5)
        assert result["group_code"] == "BKS"

    def test_mild_inflow(self):
        """0 < avg_score_change <= 2.0 → label 'mild_inflow'."""
        data = {"avg_score_change": 1.0, "avg_score": 60.0, "group_code": "TCB"}
        result = compute_sector_momentum(data)
        assert result is not None
        assert result["label"] == "mild_inflow"
        assert result["score_change"] == pytest.approx(1.0)

    def test_mild_outflow(self):
        """-2.0 <= avg_score_change < 0 → label 'mild_outflow'."""
        data = {"avg_score_change": -1.0, "avg_score": 55.0, "group_code": "FPT"}
        result = compute_sector_momentum(data)
        assert result is not None
        assert result["label"] == "mild_outflow"
        assert result["score_change"] == pytest.approx(-1.0)

    def test_strong_outflow(self):
        """avg_score_change < -2.0 → label 'strong_outflow'."""
        data = {"avg_score_change": -4.2, "avg_score": 35.0, "group_code": "HPG"}
        result = compute_sector_momentum(data)
        assert result is not None
        assert result["label"] == "strong_outflow"
        assert result["score_change"] == pytest.approx(-4.2)

    def test_none_input(self):
        """Returns None when sector_data is None — no exception raised."""
        result = compute_sector_momentum(None)
        assert result is None

    def test_none_score_change(self):
        """Returns None when avg_score_change is None in sector_data dict."""
        data = {"avg_score_change": None, "avg_score": 60.0, "group_code": "BKS"}
        result = compute_sector_momentum(data)
        assert result is None

    def test_output_shape(self):
        """Output dict has exactly keys: label, score_change, group_code."""
        data = {"avg_score_change": 2.5, "avg_score": 68.0, "group_code": "VCB"}
        result = compute_sector_momentum(data)
        assert result is not None
        assert set(result.keys()) == {"label", "score_change", "group_code"}
        # Values are JSON-serializable (required for LLM prompt injection)
        json_str = json.dumps(result)
        assert len(json_str) > 0
        assert isinstance(result["score_change"], float)
        assert isinstance(result["label"], str)
        assert isinstance(result["group_code"], str)
