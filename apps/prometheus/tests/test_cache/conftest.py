"""Cache-test isolation (P-2 mitigation).

Autouse fixture clears the per-key lock map and every namespace cache
between tests so single-flight tests cannot bleed locks/values into
each other.
"""
from __future__ import annotations

import pytest

from localstock.cache import registry as cache_registry
from localstock.cache import single_flight as sf


@pytest.fixture(autouse=True)
def _reset_cache_state():
    # Pre-test: clear locks and all namespace caches
    if hasattr(sf, "_locks"):
        sf._locks.clear()
    for cache in getattr(cache_registry, "_caches", {}).values():
        cache.clear()
    yield
    if hasattr(sf, "_locks"):
        sf._locks.clear()
