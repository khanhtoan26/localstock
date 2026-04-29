"""Phase 26 / CACHE-02 — PipelineRunRepository RED tests (D-01)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from localstock.db.models import PipelineRun
from localstock.db.repositories.pipeline_run_repo import PipelineRunRepository

pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]


async def _purge(db_session):
    """Delete all pipeline_runs rows so the test starts from a clean slate.

    db_session is transactional-rollback at fixture teardown, but tests
    inside the fixture share the same connection so we still need to
    isolate per-test state from any pre-existing rows in the DB.
    """
    from sqlalchemy import delete

    await db_session.execute(delete(PipelineRun))
    await db_session.flush()


async def test_returns_none_when_no_completed_runs(db_session):
    await _purge(db_session)
    repo = PipelineRunRepository(db_session)
    assert await repo.get_latest_completed() is None


async def test_returns_latest_completed_id(db_session):
    await _purge(db_session)
    now = datetime.now(timezone.utc)
    older = PipelineRun(
        started_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=2),
        status="completed",
        run_type="daily",
    )
    newer = PipelineRun(
        started_at=now - timedelta(hours=1),
        completed_at=now - timedelta(hours=1),
        status="completed",
        run_type="daily",
    )
    running = PipelineRun(
        started_at=now,
        completed_at=None,
        status="running",
        run_type="daily",
    )
    db_session.add_all([older, newer, running])
    await db_session.flush()

    repo = PipelineRunRepository(db_session)
    latest = await repo.get_latest_completed()

    expected = (
        await db_session.execute(
            select(PipelineRun.id)
            .where(PipelineRun.status == "completed")
            .order_by(PipelineRun.completed_at.desc())
            .limit(1)
        )
    ).scalar_one()

    assert latest == expected
    assert latest == newer.id


async def test_ignores_failed_and_running_runs(db_session):
    await _purge(db_session)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            PipelineRun(
                started_at=now,
                completed_at=now,
                status="failed",
                run_type="daily",
            ),
            PipelineRun(
                started_at=now,
                completed_at=None,
                status="running",
                run_type="daily",
            ),
        ]
    )
    await db_session.flush()

    repo = PipelineRunRepository(db_session)
    assert await repo.get_latest_completed() is None
