"""Phase 26 / CACHE-02 — Versioning RED tests.

Closes ROADMAP Success Criterion #2 verbatim:
    "Cache key cho scoring outputs include `pipeline_run_id` — verified
     bằng test: ghi pipeline mới → key cũ không bao giờ trả stale data,
     không cần đợi TTL"
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete

from localstock.cache import (
    get_or_compute,
    invalidate_namespace,
    resolve_latest_run_id,
)
from localstock.db.models import PipelineRun
from localstock.observability.metrics import get_metrics

pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]


def _make_factory(db_session):
    """Wrap a live AsyncSession in an async-context-manager factory.

    `resolve_latest_run_id` accepts a zero-arg callable returning an
    ``async with`` context manager. We yield the *same* db_session
    so changes from the test are visible to the repository call
    (without committing — the fixture rolls back at teardown).
    """

    @asynccontextmanager
    async def factory():
        yield db_session

    return factory


async def _purge(db_session):
    await db_session.execute(delete(PipelineRun))
    await db_session.flush()


async def test_new_pipeline_run_invalidates_old_keys(db_session):
    """SC #2 verbatim — old key never serves stale data after new run."""
    await _purge(db_session)
    # Cache state must start empty for this test.
    invalidate_namespace("pipeline:latest_run_id")
    invalidate_namespace("scores:ranking")

    now = datetime.now(timezone.utc)
    run1 = PipelineRun(
        started_at=now - timedelta(hours=1),
        completed_at=now - timedelta(hours=1),
        status="completed",
        run_type="daily",
    )
    db_session.add(run1)
    await db_session.flush()
    factory = _make_factory(db_session)

    # 1. Resolve initial run_id → run1.id
    rid_a = await resolve_latest_run_id(factory)
    assert rid_a == run1.id

    # 2. Populate scoring cache under that version key
    async def compute_old():
        return {"snapshot": "from_run_1"}

    v_old = await get_or_compute(
        "scores:ranking", f"limit=50:run={rid_a}", compute_old,
    )
    assert v_old == {"snapshot": "from_run_1"}

    # 3. New completed run lands
    run2 = PipelineRun(
        started_at=now,
        completed_at=now,
        status="completed",
        run_type="daily",
    )
    db_session.add(run2)
    await db_session.flush()

    # 4. Pipeline finalize hook (26-05) invalidates these namespaces.
    invalidate_namespace("pipeline:latest_run_id")
    invalidate_namespace("scores:ranking")

    # 5. Composer now resolves the NEW run_id without waiting for 5s TTL.
    rid_b = await resolve_latest_run_id(factory)
    assert rid_b == run2.id, "version key did not advance after new run"
    assert rid_b != rid_a

    # 6. New key is composed and miss-then-fill works.
    async def compute_new():
        return {"snapshot": "from_run_2"}

    v_new = await get_or_compute(
        "scores:ranking", f"limit=50:run={rid_b}", compute_new,
    )
    assert v_new == {"snapshot": "from_run_2"}

    # SC #2 invariant: composers will only ever address `run={rid_b}`
    # going forward, so the old `run={rid_a}` key — even if its TTL has
    # not yet expired — is unreachable. Old key never serves stale data.


async def test_resolve_uses_5s_cache_namespace(db_session):
    """5s TTL cache (D-02) wraps the lookup — second call within TTL is a hit."""
    await _purge(db_session)
    invalidate_namespace("pipeline:latest_run_id")

    now = datetime.now(timezone.utc)
    run = PipelineRun(
        started_at=now,
        completed_at=now,
        status="completed",
        run_type="daily",
    )
    db_session.add(run)
    await db_session.flush()
    factory = _make_factory(db_session)

    metrics = get_metrics()
    hits = metrics["cache_hits_total"].labels(cache_name="pipeline:latest_run_id")
    misses = metrics["cache_misses_total"].labels(cache_name="pipeline:latest_run_id")

    before_hits = hits._value.get()
    before_misses = misses._value.get()

    # First call: cold → miss.
    await resolve_latest_run_id(factory)
    # Second call within 5s TTL: hit.
    await resolve_latest_run_id(factory)

    assert hits._value.get() - before_hits == 1
    assert misses._value.get() - before_misses == 1
