"""Phase 26 — In-process cache (stub re-exports; full body in Task 2)."""
from __future__ import annotations

from localstock.cache._context import cache_outcome_var  # noqa: F401
from localstock.cache.invalidate import invalidate_namespace  # noqa: F401


async def get_or_compute(*a, **kw):  # pragma: no cover - stub
    raise NotImplementedError("26-01 Task 2 fills this in")
