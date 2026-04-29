"""Phase 26 / D-04 — Eager-purge invalidation."""
from __future__ import annotations

from loguru import logger

from localstock.cache.registry import _caches


def invalidate_namespace(namespace: str) -> int:
    """Purge an entire namespace; returns count of entries cleared.

    Idempotent. Synchronous (no await) — see CONTEXT P-6: this keeps
    the invalidate→prewarm sequence atomic w.r.t. user requests.
    """
    cache = _caches.get(namespace)
    if cache is None:
        logger.warning("cache.invalidate.unknown_namespace", namespace=namespace)
        return 0
    n = len(cache)
    cache.clear()
    logger.info("cache.invalidate", namespace=namespace, cleared=n)
    return n
