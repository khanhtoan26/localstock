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
    """Closes ROADMAP SC #2 verbatim: report.content_json never contains
    'NaN' or 'Infinity' after a write that included those float values.
    """
    from datetime import UTC, date, datetime

    from sqlalchemy import text

    from localstock.db.database import get_session_factory
    from localstock.db.models import AnalysisReport
    from localstock.db.repositories.report_repo import ReportRepository

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = ReportRepository(session)
        bad_payload = {
            "metrics": {
                "pe": float("inf"),
                "rsi": float("nan"),
                "vol": -float("inf"),
                "nested": [1.0, float("nan"), {"k": float("inf")}],
            }
        }
        symbol = "TST_DQ04"
        today = date.today()
        await repo.upsert(
            {
                "symbol": symbol,
                "date": today,
                "report_type": "daily",
                "content_json": bad_payload,
                "summary": "DQ-04 boundary test",
                "recommendation": "hold",
                "model_used": "test",
                "total_score": 0.0,
                "grade": "C",
                "generated_at": datetime.now(UTC),
            }
        )
        try:
            result = await session.execute(
                text(
                    "SELECT content_json::text FROM analysis_reports "
                    "WHERE symbol = :s AND date = :d AND report_type = 'daily'"
                ),
                {"s": symbol, "d": today},
            )
            persisted = result.scalar_one()
            assert "NaN" not in persisted, (
                f"content_json still contains NaN: {persisted!r}"
            )
            assert "Infinity" not in persisted, (
                f"content_json still contains Infinity: {persisted!r}"
            )
            assert "null" in persisted.lower()
        finally:
            # cleanup
            await session.execute(
                text(
                    "DELETE FROM analysis_reports WHERE symbol = :s AND date = :d"
                ),
                {"s": symbol, "d": today},
            )
            await session.commit()
