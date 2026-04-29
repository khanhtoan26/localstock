"""Phase 25 / DQ-03 — Per-rule Tier 2 mode dispatcher (D-06).

Implementation lands in 25-07. Wave 0 stub.
"""
from __future__ import annotations

from typing import Literal

Mode = Literal["shadow", "enforce"]


def get_tier2_mode(rule_name: str) -> Mode:  # noqa: ARG001
    """Return the configured mode (shadow|enforce) for a Tier 2 rule. (Wave 3)"""
    raise NotImplementedError("DQ-03: implemented in 25-07-PLAN.md")
