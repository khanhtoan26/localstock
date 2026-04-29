"""Phase 25 / DQ-04 — JSONB write-boundary NaN/Inf sanitizer (D-04).

Implementation lands in 25-02. This stub exists so RED tests in 25-01
fail with NotImplementedError, not ModuleNotFoundError.
"""
from __future__ import annotations

from typing import Any


def sanitize_jsonb(value: Any) -> Any:  # noqa: ARG001 — stub
    """Replace NaN/+Inf/-Inf with None; recurse into dict/list. (Wave 1)"""
    raise NotImplementedError("DQ-04: implemented in 25-02-PLAN.md")
