"""Perf gate for /api/market/summary — p95 < 50ms across 100 hot calls."""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone

import pytest

from localstock.cache import invalidate_namespace
from localstock.db.models import PipelineRun


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_market_summary_cache_hit_p95_under_50ms(async_client, db_session):
    invalidate_namespace("market:summary")
    invalidate_namespace("pipeline:latest_run_id")

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
        r0 = await async_client.get("/api/market/summary")
        assert r0.status_code == 200
        assert r0.headers.get("X-Cache") == "miss"

        timings_ms: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            r = await async_client.get("/api/market/summary")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert r.status_code == 200
            assert r.headers.get("X-Cache") == "hit"
            timings_ms.append(elapsed_ms)

        p95 = statistics.quantiles(timings_ms, n=20)[18]
        p99 = statistics.quantiles(timings_ms, n=100)[98]
        max_ms = max(timings_ms)
        assert p95 < 50.0, (
            f"p95={p95:.2f}ms exceeds 50ms gate "
            f"(p99={p99:.2f}ms, max={max_ms:.2f}ms)"
        )
    finally:
        await db_session.delete(run)
        await db_session.commit()
        invalidate_namespace("market:summary")
        invalidate_namespace("pipeline:latest_run_id")
