"""Phase 26 / CACHE-06 / D-08 — APScheduler cache_janitor (60s TTL sweep).

Iterates the namespace registry, calls ``cache.expire()`` on each
:class:`localstock.cache.registry.InstrumentedTTLCache`, and logs the
per-namespace swept count. Eviction telemetry is emitted by the
overridden ``popitem`` (RESEARCH §1 Q-2): expired pops increment
``cache_evictions_total{cache_name, reason='expire'}``.

P-8: sweep is sub-millisecond in expected operation. If profiling
ever shows >50ms cost, wrap the body with ``asyncio.to_thread``.
"""
from __future__ import annotations

from loguru import logger

from localstock.cache.registry import _caches
from localstock.observability.decorators import observe
from localstock.observability.metrics import get_metrics


@observe("cache.janitor.sweep")
async def cache_janitor() -> dict[str, int]:
    """Sweep TTL-expired entries across every registered namespace.

    Returns a ``{namespace: swept_count}`` dict and logs the same at INFO
    (CACHE-06 verbatim SC requirement: "log số entries swept"). Failures
    on any single namespace are caught so other namespaces still sweep.

    Per-namespace count is derived from the eviction-counter delta around
    ``cache.expire()`` rather than ``len()`` deltas, because
    :class:`cachetools.TTLCache.__len__` itself triggers expiration and
    would zero the *before* reading (RESEARCH §1 Q-2).
    """
    metrics = get_metrics()
    evictions = metrics["cache_evictions_total"]
    swept: dict[str, int] = {}
    for namespace, cache in _caches.items():
        counter = evictions.labels(cache_name=namespace, reason="expire")
        before = counter._value.get()
        try:
            cache.expire()
        except Exception:
            # T-26-06-02: per-namespace failure must not abort the rest.
            logger.exception(
                "cache.janitor.namespace_failed", namespace=namespace
            )
            swept[namespace] = 0
            continue
        after = counter._value.get()
        swept[namespace] = int(max(0, after - before))

    logger.info(
        "cache.janitor.sweep",
        swept=swept,
        total=sum(swept.values()),
    )
    return swept
