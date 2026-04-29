"""Phase 25 / DQ-04 — JSONB write-boundary NaN/Inf sanitizer (D-04).

Replaces the inlined ``_clean_nan`` helper that was previously duplicated in
``services/pipeline.py:_store_financials``. Every JSONB-bound repo write
must call this on its payload at method entry — see RESEARCH §Audit List D-04.

Closes ROADMAP Success Criterion #2: JSONB write boundary converts ±Inf and
NaN to SQL NULL.
"""

from __future__ import annotations

import math
from typing import Any


def sanitize_jsonb(value: Any) -> Any:
    """Replace NaN / +Inf / -Inf with None; recurse into dict/list/tuple.

    Idempotent. Safe on None. Handles numpy scalar floats (``np.float64`` etc.)
    via ``isinstance(value, float)`` (numpy scalars subclass float) and a
    duck-typed ``float()`` cast fallback for other numeric types. Tuples are
    normalized to lists (JSON has no tuple).

    Per CONTEXT D-04 + RESEARCH Pitfall 10.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: sanitize_jsonb(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_jsonb(v) for v in value]
    if isinstance(value, bool):
        # bool is a subclass of int — short-circuit before numeric branch.
        return value
    if isinstance(value, float):
        # Covers builtin float and numpy.float64 (subclass of float).
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, int):
        # int / numpy int — never NaN/Inf, return as-is.
        return value
    # Last resort: duck-type other numeric scalars (e.g. Decimal, pandas NA)
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return value
    if math.isnan(f) or math.isinf(f):
        return None
    return value
