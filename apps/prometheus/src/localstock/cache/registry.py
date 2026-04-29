"""Phase 26 / D-02 + D-07 — Namespace → InstrumentedTTLCache registry.

See RESEARCH §1 Q-2 for eviction-counter rationale and CONTEXT D-02 for
the TTL table. ``cachetools.TTLCache`` is NOT thread-safe (RESEARCH P-1)
but FastAPI + uvicorn + asyncio is single-threaded under v1.5; the audit
in CONTEXT confirms there is no offload to thread pools that would
mutate these caches concurrently. If that assumption ever breaks (e.g.,
``run_in_executor`` writers), wrap each cache with an ``asyncio.Lock``
or switch to a thread-safe variant — TODO(26+).
"""
from __future__ import annotations

from cachetools import TTLCache

from localstock.config import get_settings
from localstock.observability.metrics import get_metrics


class InstrumentedTTLCache(TTLCache):
    """TTLCache that increments cache_evictions_total on each ``popitem``.

    Distinguishes ``reason='expire'`` (popped from inside the overridden
    ``expire()``) vs ``reason='evict'`` (popped from ``__setitem__``
    overflow) via a one-shot ``_in_expire`` flag. RESEARCH §1 Q-2.
    """

    def __init__(self, maxsize: int, ttl: int, namespace: str) -> None:
        super().__init__(maxsize=maxsize, ttl=ttl)
        self._namespace = namespace
        self._in_expire = False

    def expire(self, time: float | None = None):  # type: ignore[override]
        self._in_expire = True
        try:
            return super().expire(time)
        finally:
            self._in_expire = False

    def popitem(self):  # type: ignore[override]
        key, value = super().popitem()
        try:
            reason = "expire" if self._in_expire else "evict"
            get_metrics()["cache_evictions_total"].labels(
                cache_name=self._namespace, reason=reason,
            ).inc()
        except Exception:
            # Metric failure must never break cache ops.
            pass
        return key, value


def _build_caches() -> dict[str, InstrumentedTTLCache]:
    s = get_settings()
    return {
        "scores:ranking":         InstrumentedTTLCache(200, s.cache_ranking_ttl_seconds,    "scores:ranking"),
        "scores:symbol":          InstrumentedTTLCache(600, s.cache_ranking_ttl_seconds,    "scores:symbol"),
        "market:summary":         InstrumentedTTLCache(50,  s.cache_market_ttl_seconds,     "market:summary"),
        "indicators":             InstrumentedTTLCache(s.cache_indicators_maxsize, s.cache_indicators_ttl_seconds, "indicators"),
        "pipeline:latest_run_id": InstrumentedTTLCache(8,   s.cache_latest_run_id_ttl_seconds, "pipeline:latest_run_id"),
    }


_caches: dict[str, InstrumentedTTLCache] = _build_caches()
REGISTERED_NAMESPACES = frozenset(_caches.keys())


def get_cache(namespace: str) -> InstrumentedTTLCache:
    try:
        return _caches[namespace]
    except KeyError as e:
        raise KeyError(
            f"Unknown cache namespace {namespace!r}. "
            f"Registered: {sorted(REGISTERED_NAMESPACES)}"
        ) from e
