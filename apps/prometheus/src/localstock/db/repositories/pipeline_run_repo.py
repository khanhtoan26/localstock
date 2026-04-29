"""Phase 26 / CACHE-02 — PipelineRunRepository (D-01).

Read-side queries against ``pipeline_runs``. The integer PK returned by
``get_latest_completed`` is the version key composed into cache keys
(e.g. ``scores:ranking:run={id}``); a new completed run advances the
key, so old keys are never addressed by composers (ROADMAP SC #2).

Pipeline writes still go through ``Pipeline.run_full`` /
``AutomationService.run_daily_pipeline`` — this repository is read-only.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import PipelineRun


class PipelineRunRepository:
    """Read-only repository for ``pipeline_runs``."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_completed(self) -> int | None:
        """Return the integer PK of the most recent completed run, or None.

        Filters ``status == 'completed'`` (T-26-03-02 — running rows
        would yield empty downstream data) and orders by
        ``completed_at DESC``. Wrapped by
        ``cache.version.resolve_latest_run_id`` with a 5s TTL (D-02) to
        avoid hot-loop DB hits on every cached read (T-26-03-03).
        """
        stmt = (
            select(PipelineRun.id)
            .where(PipelineRun.status == "completed")
            .order_by(PipelineRun.completed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
