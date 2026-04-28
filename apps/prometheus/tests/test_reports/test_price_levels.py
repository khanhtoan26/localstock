"""Tests for pure computation functions: entry zone, stop-loss, target price, signal conflict.

TDD RED phase — all tests expected to fail until functions are implemented.
"""

import pytest

from localstock.reports.generator import (
    compute_entry_zone,
    compute_stop_loss,
    compute_target_price,
    detect_signal_conflict,
)


class TestComputeEntryZone:
    def test_normal_case(self):
        lower, upper = compute_entry_zone(90000, 100000, 95000, 60)
        assert lower == pytest.approx(90000, abs=0.1)
        assert upper == pytest.approx(100000, abs=0.1)

    def test_fallback_low_history(self):
        lower, upper = compute_entry_zone(90000, 100000, 95000, 30)
        assert lower == pytest.approx(93100.0, abs=0.1)
        assert upper == pytest.approx(96900.0, abs=0.1)

    def test_fallback_none_indicators(self):
        lower, upper = compute_entry_zone(None, None, 95000, 60)
        assert lower == pytest.approx(93100.0, abs=0.1)
        assert upper == pytest.approx(96900.0, abs=0.1)

    def test_none_close(self):
        lower, upper = compute_entry_zone(90000, 100000, None, 60)
        assert lower is None
        assert upper is None

    def test_lower_ge_upper_triggers_fallback(self):
        lower, upper = compute_entry_zone(100000, 90000, 95000, 60)
        assert lower == pytest.approx(93100.0, abs=0.1)
        assert upper == pytest.approx(96900.0, abs=0.1)

    def test_partial_none_support(self):
        lower, upper = compute_entry_zone(None, 100000, 95000, 60)
        assert lower == pytest.approx(93100.0, abs=0.1)
        assert upper == pytest.approx(100000, abs=0.1)

    def test_partial_none_bb_upper(self):
        lower, upper = compute_entry_zone(90000, None, 95000, 60)
        assert lower == pytest.approx(90000, abs=0.1)
        assert upper == pytest.approx(96900.0, abs=0.1)


class TestComputeStopLoss:
    def test_with_support_2(self):
        result = compute_stop_loss(90000, 95000)
        assert result == pytest.approx(90000, abs=0.1)

    def test_without_support_2(self):
        result = compute_stop_loss(None, 95000)
        assert result == pytest.approx(88350.0, abs=0.1)

    def test_support_2_below_floor(self):
        result = compute_stop_loss(80000, 95000)
        assert result == pytest.approx(88350.0, abs=0.1)

    def test_none_close(self):
        result = compute_stop_loss(90000, None)
        assert result is None


class TestComputeTargetPrice:
    def test_with_resistance(self):
        result = compute_target_price(105000, 95000)
        assert result == pytest.approx(105000, abs=0.1)

    def test_without_resistance(self):
        result = compute_target_price(None, 95000)
        assert result == pytest.approx(104500.0, abs=0.1)

    def test_none_close(self):
        result = compute_target_price(105000, None)
        assert result is None


class TestDetectSignalConflict:
    def test_conflict_tech_higher(self):
        result = detect_signal_conflict(72, 41)
        assert result is not None
        assert "Tech=72" in result
        assert "Fund=41" in result
        assert "gap=+31" in result
        assert "kỹ thuật > cơ bản" in result

    def test_conflict_fund_higher(self):
        result = detect_signal_conflict(30, 70)
        assert result is not None
        assert "cơ bản > kỹ thuật" in result
        assert "gap=-40" in result

    def test_no_conflict_equal(self):
        result = detect_signal_conflict(50, 50)
        assert result is None

    def test_no_conflict_small_gap(self):
        result = detect_signal_conflict(60, 45)
        assert result is None

    def test_boundary_25(self):
        result = detect_signal_conflict(75, 50)
        assert result is None

    def test_boundary_26(self):
        result = detect_signal_conflict(76, 50)
        assert result is not None
        assert "gap=+26" in result

    def test_none_tech(self):
        result = detect_signal_conflict(None, 50)
        assert result is None

    def test_none_fund(self):
        result = detect_signal_conflict(72, None)
        assert result is None
