"""Phase 25 / DQ-03 — runbook existence smoke test.

Passes immediately on Wave 0 (file is a placeholder with TODO markers).
25-07 fills in Promotion Criteria / Shadow → Strict / Rollback sections.
"""

from __future__ import annotations

from pathlib import Path


def test_tier2_promotion_runbook_exists() -> None:
    # tests/test_docs/<file> -> test_docs -> tests -> prometheus -> apps -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "docs" / "runbook" / "dq-tier2-promotion.md"
    assert path.exists(), f"Missing DQ-03 runbook at {path}"
    text = path.read_text(encoding="utf-8")
    # Required headings (filled in 25-07-PLAN.md); placeholder must mention TODO.
    assert "Promotion Criteria" in text or "TODO" in text
    assert "shadow" in text.lower()
