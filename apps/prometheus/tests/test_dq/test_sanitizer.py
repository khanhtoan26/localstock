"""Phase 25 / DQ-04 — sanitize_jsonb tests (RED until 25-02 lands).

These tests target ``localstock.dq.sanitizer.sanitize_jsonb`` which today
raises ``NotImplementedError`` (Wave 0 stub). The RED signal proves Wave 0
scaffolding is wired correctly; 25-02 lands the recipe based on the
existing ``services/pipeline.py::_clean_nan`` helper.
"""

from __future__ import annotations

import numpy as np
import pytest

from localstock.dq.sanitizer import sanitize_jsonb


def test_nan_to_none() -> None:
    assert sanitize_jsonb({"x": float("nan")}) == {"x": None}


def test_inf_and_neg_inf_to_none() -> None:
    assert sanitize_jsonb({"a": float("inf"), "b": float("-inf")}) == {
        "a": None,
        "b": None,
    }


def test_recursive_sanitize() -> None:
    payload = {"outer": [{"x": float("nan")}, {"y": [1.0, float("inf"), 3.0]}]}
    out = sanitize_jsonb(payload)
    assert out == {"outer": [{"x": None}, {"y": [1.0, None, 3.0]}]}


def test_numpy_scalars_handled() -> None:
    assert sanitize_jsonb({"a": np.float64("nan"), "b": np.float64(2.5)}) == {
        "a": None,
        "b": 2.5,
    }


def test_idempotent_on_clean_input() -> None:
    clean = {"a": 1, "b": "x", "c": [1, 2, 3], "d": None}
    assert sanitize_jsonb(clean) == clean


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_report_repo_sanitizes_inf() -> None:
    """Integration: writing inf via repo persists null. Wave 1 wires the repo."""
    # This test is RED until 25-02 wires sanitize_jsonb into report_repo.
    # See 25-02-PLAN.md Task 2 for repo wiring.
    pytest.skip("DQ-04 integration: implemented in 25-02-PLAN.md")
