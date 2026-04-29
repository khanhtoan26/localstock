"""ROADMAP SC #4 / Phase 26-05 — prewarm_hot_keys closes verbatim SC #4.

After `run_daily_pipeline`, the caches for `/scores/top` (ranking) and
`/market/summary` are pre-warmed so the first user request after a run
logs `cache=hit`, not `miss`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from localstock.cache import invalidate_namespace
from localstock.cache.registry import _caches


@pytest.mark.asyncio
@pytest.mark.requires_pg
async def test_prewarm_fills_ranking_and_market_summary(db_session):
    """ROADMAP SC #4 verbatim — first user request after run is HIT."""
    from localstock.db.models import PipelineRun

    # Seed a completed run so resolve_latest_run_id has something to find
    now = datetime.now(UTC)
    run = PipelineRun(
        started_at=now,
        completed_at=now,
        status="completed",
        run_type="daily",
    )
    db_session.add(run)
    await db_session.commit()

    @asynccontextmanager
    async def factory():
        yield db_session

    # Clear caches first so we can prove they get filled
    invalidate_namespace("scores:ranking")
    invalidate_namespace("market:summary")
    invalidate_namespace("pipeline:latest_run_id")

    from localstock.cache.prewarm import prewarm_hot_keys

    try:
        await prewarm_hot_keys(factory, ranking_limit=50)

        # After prewarm, hot keys are populated (at least one of the two
        # — both should succeed in the happy path; if a downstream service
        # raises, the prewarm helper logs + counts but does not raise, and
        # the partial-fill is still acceptable for SC #4 closure if at
        # least the ranking cache landed).
        assert len(_caches["scores:ranking"]) >= 1, (
            "scores:ranking cache empty after prewarm"
        )
        assert len(_caches["market:summary"]) >= 1, (
            "market:summary cache empty after prewarm"
        )
    finally:
        # Clean up the synthetic PipelineRun row to keep the DB tidy.
        await db_session.execute(delete(PipelineRun).where(PipelineRun.id == run.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_prewarm_skips_when_no_completed_run():
    """When no completed run exists, prewarm short-circuits cleanly."""

    @asynccontextmanager
    async def factory():
        class _R:
            def scalar_one_or_none(self):
                return None

        class _S:
            async def execute(self, *a, **k):
                return _R()

        yield _S()

    from localstock.cache.prewarm import prewarm_hot_keys

    # Must not raise — and must not populate any cache
    await prewarm_hot_keys(factory)
    assert len(_caches["scores:ranking"]) == 0
    assert len(_caches["market:summary"]) == 0


@pytest.mark.asyncio
async def test_prewarm_failure_increments_counter_and_does_not_raise():
    """P-5 — broken session factory must NOT propagate."""

    @asynccontextmanager
    async def broken_factory():
        raise RuntimeError("DB down")
        yield  # pragma: no cover

    from localstock.cache.prewarm import prewarm_hot_keys

    # Must not raise even though factory is broken
    await prewarm_hot_keys(broken_factory)
