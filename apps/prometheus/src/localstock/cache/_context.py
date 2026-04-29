"""Phase 26 / D-08 — ContextVar plumbing for X-Cache header (P-4).

Set by `cache.get_or_compute` on every return path; read by the
`CacheHeaderMiddleware` (added in 26-02) to populate the `X-Cache`
response header.
"""
from __future__ import annotations

from contextvars import ContextVar

cache_outcome_var: ContextVar[str | None] = ContextVar(
    "cache_outcome", default=None
)
