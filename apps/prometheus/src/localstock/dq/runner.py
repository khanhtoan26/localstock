"""Phase 25 / DQ-01 + DQ-02 — Validation runner (Tier 1 partition + Tier 2 dispatch).

Implementations land in 25-05 (Tier 1) and 25-07 (Tier 2). Wave 0 stub.
"""
from __future__ import annotations

from typing import Any


def partition_valid_invalid(df: Any, schema: Any) -> tuple[Any, list[dict], Any]:
    """Run a pandera schema and split rows into (valid_df, invalid_rows, errors). (Wave 2)"""
    raise NotImplementedError("DQ-01: implemented in 25-05-PLAN.md")


def evaluate_tier2(
    rule: str,
    df: Any,
    predicate: Any,
    *,
    symbol: str | None = None,
) -> None:
    """Evaluate a Tier 2 advisory rule under shadow/enforce dispatch. (Wave 3)"""
    raise NotImplementedError("DQ-02: implemented in 25-07-PLAN.md")
