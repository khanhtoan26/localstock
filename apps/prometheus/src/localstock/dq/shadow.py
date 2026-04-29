"""Phase 25 / DQ-03 — Per-rule Tier 2 mode dispatcher (D-06).

Implemented in 25-07. Resolves a Tier 2 rule's mode (`shadow` or
`enforce`) by reading per-rule env flag overrides on top of the global
`dq_default_tier2_mode` (defaults to ``"shadow"``).

Per CONTEXT D-06: per-rule env flags `DQ_TIER2_<RULE>_MODE` override
the global `DQ_DEFAULT_TIER2_MODE` setting.
"""
from __future__ import annotations

from typing import Any, Literal

from localstock.config import get_settings

Mode = Literal["shadow", "enforce"]


class Tier2Violation(Exception):
    """Raised by ``evaluate_tier2`` when a Tier 2 rule is in ``enforce`` mode.

    Carries the rule name and the offending payload (typically a
    DataFrame of rows that failed the predicate). The outer per-symbol
    try/except added in 25-06 catches this exception and routes the
    symbol into ``PipelineRun.stats.failed_symbols`` (D-03 + D-06).
    """

    def __init__(self, rule: str, offending: Any) -> None:
        try:
            count = len(offending)
        except TypeError:
            count = 0
        super().__init__(f"Tier 2 rule {rule!r} violated by {count} rows")
        self.rule = rule
        self.offending = offending


def get_tier2_mode(rule_name: str) -> Mode:
    """Return the configured mode for a Tier 2 rule.

    Resolution order (D-06):
      1. ``Settings.dq_tier2_<rule_name>_mode`` (per-rule explicit override).
      2. ``Settings.dq_default_tier2_mode`` (global default).
      3. Hard fallback ``"shadow"`` (safe default — never block).

    Unknown values fall back to ``"shadow"`` (defensive).
    """
    settings = get_settings()
    explicit = getattr(settings, f"dq_tier2_{rule_name}_mode", None)
    default = getattr(settings, "dq_default_tier2_mode", None) or "shadow"
    raw = (explicit or default or "shadow")
    mode = str(raw).strip().lower()
    if mode not in ("shadow", "enforce"):
        mode = "shadow"
    return mode  # type: ignore[return-value]
