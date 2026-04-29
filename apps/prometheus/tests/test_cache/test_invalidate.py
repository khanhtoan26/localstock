"""Phase 26 / 26-01 — invalidate_namespace contract."""
from __future__ import annotations

import pytest

from localstock.cache import get_or_compute, invalidate_namespace


@pytest.mark.asyncio
async def test_invalidate_purges_namespace():
    async def compute():
        return "x"

    await get_or_compute("scores:ranking", "k1", compute)
    await get_or_compute("scores:ranking", "k2", compute)
    invalidate_namespace("scores:ranking")
    # Next call should miss again
    from localstock.observability.metrics import get_metrics

    m = get_metrics()
    before = m["cache_misses_total"].labels(
        cache_name="scores:ranking"
    )._value.get()
    await get_or_compute("scores:ranking", "k1", compute)
    after = m["cache_misses_total"].labels(
        cache_name="scores:ranking"
    )._value.get()
    assert after - before == 1
