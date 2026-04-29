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
    """TTLCache that increments cache_evictions_total on each eviction.

    - ``reason='expire'`` is emitted from the overridden ``expire()`` for
      each ``(key, value)`` returned (TTLCache uses ``Cache.__delitem__``
      internally, NOT ``popitem``, so we cannot rely on the popitem hook
      for TTL expirations — this was the latent bug that 26-06 surfaced).
    - ``reason='evict'`` is emitted from the overridden ``popitem`` for
      LRU overflow during ``__setitem__``.

    The ``_in_expire`` flag suppresses the popitem path when expire()
    is the caller (defensive — current cachetools doesn't go through
    popitem during expire, but a future version might).
    """

    def __init__(self, maxsize: int, ttl: int, namespace: str) -> None:
        super().__init__(maxsize=maxsize, ttl=ttl)
        self._namespace = namespace
        self._in_expire = False

    def expire(self, time: float | None = None):  # type: ignore[override]
        self._in_expire = True
        try:
            expired = super().expire(time)
        finally:
            self._in_expire = False
        if expired:
            try:
                counter = get_metrics()["cache_evictions_total"]
                for _ in expired:
                    counter.labels(
                        cache_name=self._namespace, reason="expire",
                    ).inc()
            except Exception:
                # Metric failure must never break cache ops.
                pass
        return expired

    def popitem(self):  # type: ignore[override]
        key, value = super().popitem()
        try:
            # If we're inside expire(), the popitem path would double-count
            # (defensive; current cachetools doesn't use popitem in expire).
            if not self._in_expire:
                get_metrics()["cache_evictions_total"].labels(
                    cache_name=self._namespace, reason="evict",
                ).inc()
        except Exception:
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
