"""Phase 24-05 — health_self_probe APScheduler job (D-05, OBS-15).

Runs every 30s via IntervalTrigger to populate 4 self-probe gauges:
  - localstock_db_pool_size
  - localstock_db_pool_checked_out
  - localstock_last_pipeline_age_seconds
  - localstock_last_crawl_success_count

Defensive: the entire body is wrapped in try/except so a probe failure
never crashes the scheduler (Pitfall 6 — NullPool / DB outage). On
failure a structured WARNING `health_probe_failed` is emitted via loguru.
"""
from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from prometheus_client import REGISTRY
from sqlalchemy import select


async def health_self_probe() -> None:
    """Populate self-probe gauges. Never raises."""
    try:
        # Lazy imports — keep module import cheap and let tests monkeypatch.
        from localstock.db.database import get_engine, get_session_factory
        from localstock.db.models import PipelineRun

        n2c = REGISTRY._names_to_collectors
        pool_size = n2c.get("localstock_db_pool_size")
        pool_co = n2c.get("localstock_db_pool_checked_out")
        age = n2c.get("localstock_last_pipeline_age_seconds")
        last_ok = n2c.get("localstock_last_crawl_success_count")

        # Pool stats (sync — no DB round-trip).
        engine = get_engine()
        pool = engine.pool
        if pool_size is not None:
            try:
                pool_size.set(pool.size())
            except (AttributeError, TypeError):
                # NullPool / non-QueuePool — gauge stays at last value.
                pass
        if pool_co is not None:
            try:
                pool_co.set(pool.checkedout())
            except (AttributeError, TypeError):
                pass

        # Latest completed run (single round-trip).
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(PipelineRun)
                .where(PipelineRun.status == "completed")
                .order_by(PipelineRun.completed_at.desc())
                .limit(1)
            )
            run = result.scalar_one_or_none()
            if run is not None and getattr(run, "completed_at", None) is not None:
                if age is not None:
                    age.set((datetime.now(UTC) - run.completed_at).total_seconds())
                if last_ok is not None:
                    last_ok.set(run.symbols_success or 0)
    except Exception as exc:  # noqa: BLE001 — defensive guard, must never raise.
        logger.warning(
            "health_probe_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
