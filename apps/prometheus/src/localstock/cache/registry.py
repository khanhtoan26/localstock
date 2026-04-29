"""Phase 26 / D-02 + D-07 — Namespace → InstrumentedTTLCache registry (stub).

Full implementation lands in 26-01 Task 2. Module-level imports must
succeed so RED tests can collect; behaviour calls raise NotImplementedError.
"""
from __future__ import annotations

# Placeholders so test conftest cleanup (`for cache in _caches.values(): cache.clear()`)
# can import this module without exploding at collection time.
_caches: dict = {}
REGISTERED_NAMESPACES: frozenset = frozenset()


def get_cache(namespace: str):  # pragma: no cover - stub
    raise NotImplementedError("26-01 Task 2 fills this in")

