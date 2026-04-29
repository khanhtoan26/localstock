"""Phase 26 — In-process cache with single-flight, version keys, eager purge.

Public API:
  - ``get_or_compute(namespace, key, compute_fn, ttl=None) -> value``
  - ``invalidate_namespace(namespace) -> int``
  - ``cache_outcome_var: ContextVar[str | None]``  (read by middleware)

See CONTEXT.md D-01..D-08 and RESEARCH §1 (Pattern 1).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from loguru import logger

from localstock.cache._context import cache_outcome_var
from localstock.cache.invalidate import invalidate_namespace
from localstock.cache.registry import get_cache
from localstock.cache.single_flight import get_lock
from localstock.observability.metrics import get_metrics

__all__ = [
    "get_or_compute",
    "invalidate_namespace",
    "cache_outcome_var",
    "resolve_latest_run_id",
    "prewarm_hot_keys",
]


async def get_or_compute(
    namespace: str,
    key: str,
    compute_fn: Callable[[], Awaitable[Any]],
    ttl: int | None = None,
) -> Any:
    """Look up ``key`` in ``namespace``; on miss, single-flight ``compute_fn``.

    Implements D-03 + RESEARCH P-9. ``cache_outcome_var`` is set on every
    return path (read by ``CacheHeaderMiddleware`` in 26-02). The ``ttl``
    parameter is accepted for API compatibility but the per-namespace
    TTL from the registry always wins (D-02).
    """
    cache = get_cache(namespace)
    full_key = f"{namespace}:{key}"

    cached = cache.get(full_key)
    if cached is not None:
        cache_outcome_var.set("hit")
        _safe_inc("cache_hits_total", cache_name=namespace)
        return cached

    # P-2: allocate lock inside coroutine (current loop)
    # P-3: hold strong local ref `lock` across the async with
    lock = get_lock(full_key)
    async with lock:
        # double-check after acquiring the lock
        cached = cache.get(full_key)
        if cached is not None:
            cache_outcome_var.set("hit")
            _safe_inc("cache_hits_total", cache_name=namespace)
            return cached

        cache_outcome_var.set("miss")
        _safe_inc("cache_misses_total", cache_name=namespace)
        _safe_inc("cache_compute_total", cache_name=namespace)  # P-9: SC #3 gate

        value = await compute_fn()
        cache[full_key] = value
        return value


def _safe_inc(metric_name: str, **labels: str) -> None:
    """Increment a Prometheus counter, tolerating absence (defensive).

    ``cache_compute_total`` is now declared canonically in
    ``observability/metrics.py`` (B1: 26-01 owns it), so this guard is
    purely defensive against unrelated registry hiccups.
    """
    try:
        get_metrics()[metric_name].labels(**labels).inc()
    except Exception as e:  # noqa: BLE001
        logger.debug("cache.metric.missing", metric=metric_name, error=str(e))


# Re-export the version-key resolver. Imported AFTER ``get_or_compute`` is
# defined so ``cache.version`` can resolve the public callable lazily inside
# its body without circular-import issues at module-load time.
from localstock.cache.version import resolve_latest_run_id  # noqa: E402,F401
from localstock.cache.prewarm import prewarm_hot_keys  # noqa: E402,F401
