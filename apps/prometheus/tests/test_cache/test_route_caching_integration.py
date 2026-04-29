"""Integration: route → get_or_compute → middleware → X-Cache header.

Asserts the full miss → hit → miss-after-invalidate cycle and the
no-completed-run bypass path (T-26-04-04: empty shape must NOT be
cached under a versioned key).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from localstock.cache import invalidate_namespace
from localstock.db.models import PipelineRun


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_invalidate_forces_next_call_to_miss(async_client, db_session):
    invalidate_namespace("scores:ranking")
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
        r1 = await async_client.get("/api/scores/top?limit=20")
        assert r1.headers.get("X-Cache") == "miss"

        r2 = await async_client.get("/api/scores/top?limit=20")
        assert r2.headers.get("X-Cache") == "hit"

        invalidate_namespace("scores:ranking")
        r3 = await async_client.get("/api/scores/top?limit=20")
        assert r3.headers.get("X-Cache") == "miss"
    finally:
        await db_session.delete(run)
        await db_session.commit()
        invalidate_namespace("scores:ranking")
        invalidate_namespace("pipeline:latest_run_id")


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_no_completed_run_bypasses_cache(async_client, db_session):
    """When run_id is None, route must NOT touch the scoring cache.

    No PipelineRun seeded in this test → ``resolve_latest_run_id``
    returns None → handler computes directly. The scoring cache stays
    empty (no versioned-key poisoning, T-26-04-04). The X-Cache header
    may still appear due to the run_id resolution itself going through
    ``get_or_compute`` on the ``pipeline:latest_run_id`` namespace, but
    the *scoring* namespace must remain untouched.
    """
    invalidate_namespace("scores:ranking")
    invalidate_namespace("pipeline:latest_run_id")

    # Defensive: clear any stragglers from prior tests by deleting all
    # completed runs in this DB session (can't rely on rollback because
    # other tests commit). Use a SELECT/DELETE through the session.
    from sqlalchemy import delete
    await db_session.execute(delete(PipelineRun).where(PipelineRun.status == "completed"))
    await db_session.commit()

    try:
        r = await async_client.get("/api/scores/top?limit=20")
        assert r.status_code == 200
        # Scoring cache should be empty — verifies T-26-04-04 mitigation.
        from localstock.cache.registry import get_cache
        scoring_cache = get_cache("scores:ranking")
        assert len(scoring_cache) == 0, (
            f"empty-shape response was cached under a versioned key — "
            f"poison risk; cache keys: {list(scoring_cache.keys())}"
        )
    finally:
        invalidate_namespace("scores:ranking")
        invalidate_namespace("pipeline:latest_run_id")
