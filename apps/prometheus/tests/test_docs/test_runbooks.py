"""Phase 25 / DQ-03 — runbook content test.

After 25-07 lands, the Tier 2 promotion runbook is no longer a
placeholder. This test asserts every required heading/keyword from the
DQ-03 deliverable is present.
"""

from __future__ import annotations

from pathlib import Path


def test_tier2_promotion_runbook_exists() -> None:
    # tests/test_docs/<file> -> test_docs -> tests -> prometheus -> apps -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "docs" / "runbook" / "dq-tier2-promotion.md"
    assert path.exists(), f"Missing DQ-03 runbook at {path}"
    text = path.read_text(encoding="utf-8")
    # Required content per DQ-03 (25-07-PLAN.md must_haves).
    required = (
        "Promotion Criteria",
        "Rollback",
        "Per-Rule Status Table",
        "DQ_TIER2_",
        "shadow",
        "enforce",
        "14-day",
    )
    missing = [r for r in required if r not in text]
    assert not missing, f"Runbook missing required sections: {missing!r}"
