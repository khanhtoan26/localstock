"""Closes ROADMAP SC #1 verbatim — /api/scores/top hot p95 < 50ms.

100 hot calls after a cold miss; ``time.perf_counter`` + ``statistics.quantiles``
(no pytest-benchmark dep — Q-4 ratification). The X-Cache header transition
miss→hit is asserted in addition to the timing gate so a regression in
either layer fails the test deterministically.
"""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone

import pytest

from localstock.cache import invalidate_namespace
from localstock.db.models import PipelineRun


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_ranking_cache_hit_p95_under_50ms(async_client, db_session):
    """SC #1 verbatim: /api/scores/top second call < 50ms p95 with X-Cache: hit."""
    # Cold-start the in-process caches so prior tests can't leak state.
    invalidate_namespace("scores:ranking")
    invalidate_namespace("pipeline:latest_run_id")

    # Seed a completed run so the route enters the cached path.
    now = datetime.now(timezone.utc)
    run = PipelineRun(
        started_at=now,
        completed_at=now,
        status="completed",
        run_type="daily",
    )
    db_session.add(run)
    await db_session.commit()

    try:
        # Cold call — must report miss.
        r0 = await async_client.get("/api/scores/top?limit=50")
        assert r0.status_code == 200
        assert r0.headers.get("X-Cache") == "miss", (
            f"first call X-Cache header was {r0.headers.get('X-Cache')!r}"
        )

        # 100 hot calls — must all be hits and clear the 50ms p95 gate.
        timings_ms: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            r = await async_client.get("/api/scores/top?limit=50")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert r.status_code == 200
            assert r.headers.get("X-Cache") == "hit", (
                f"hot call X-Cache header was {r.headers.get('X-Cache')!r}"
            )
            timings_ms.append(elapsed_ms)

        p95 = statistics.quantiles(timings_ms, n=20)[18]
        p99 = statistics.quantiles(timings_ms, n=100)[98]
        max_ms = max(timings_ms)
        assert p95 < 50.0, (
            f"p95={p95:.2f}ms exceeds 50ms gate "
            f"(p99={p99:.2f}ms, max={max_ms:.2f}ms)"
        )
    finally:
        # Test-data cleanup — fixture's rollback won't reach an already
        # committed row.
        await db_session.delete(run)
        await db_session.commit()
        invalidate_namespace("scores:ranking")
        invalidate_namespace("pipeline:latest_run_id")
