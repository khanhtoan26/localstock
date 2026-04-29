"""Phase 24 / OBS-17 — pipeline step timing tests.

Two-tier coverage for ``Pipeline._step_timer`` (per 24-06-PLAN, RESEARCH §6,
CONTEXT D-08):

1. Unit tests — exercise the async context manager directly on a fresh
   ``PipelineRun`` instance. Verify duration is recorded on BOTH the happy
   path and the exception path (RESEARCH Pitfall 7: ``finally`` must run
   before the ``raise`` propagates).

2. Integration test — stub all crawler / repo calls inside ``run_full`` so
   the body executes end-to-end against an ``AsyncMock`` session, then
   assert the resulting ``PipelineRun`` has ``crawl_duration_ms`` and
   ``analyze_duration_ms`` populated and ``score_duration_ms`` /
   ``report_duration_ms`` left as ``None`` (Q-3 placeholders).

The integration test does not need Postgres because the timer's contract is
to ``setattr`` on the in-memory ``PipelineRun`` row — SQLAlchemy persists it
automatically on commit. We verify the column write directly.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from localstock.db.models import PipelineRun
from localstock.services.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Unit tests — _step_timer in isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_step_timer_records_duration_on_exception() -> None:
    """RESEARCH Pitfall 7: timer MUST record duration BEFORE re-raise.

    The whole point of using a try/finally instead of a decorator is so the
    column write happens even when the wrapped block raises.
    """
    pipe = Pipeline.__new__(Pipeline)  # bypass __init__ — no session needed
    run = PipelineRun(
        started_at=datetime.now(UTC),
        status="running",
        run_type="manual",
    )

    with pytest.raises(RuntimeError, match="step failed"):
        async with pipe._step_timer("crawl", run):
            await asyncio.sleep(0.05)
            raise RuntimeError("step failed")

    assert run.crawl_duration_ms is not None, (
        "crawl_duration_ms must be set even when the wrapped block raises"
    )
    assert run.crawl_duration_ms >= 50, (
        f"expected >=50ms, got {run.crawl_duration_ms}"
    )


@pytest.mark.asyncio
async def test_step_timer_records_duration_on_success() -> None:
    """Happy-path: clean exit also writes the column."""
    pipe = Pipeline.__new__(Pipeline)
    run = PipelineRun(
        started_at=datetime.now(UTC),
        status="running",
        run_type="manual",
    )

    async with pipe._step_timer("analyze", run):
        await asyncio.sleep(0.02)

    assert run.analyze_duration_ms is not None
    assert run.analyze_duration_ms >= 20


@pytest.mark.asyncio
async def test_step_timer_writes_dynamic_column_name() -> None:
    """``setattr(run, f'{step_name}_duration_ms', ...)`` works for any of
    the four step names defined by the 24-02 migration."""
    pipe = Pipeline.__new__(Pipeline)
    run = PipelineRun(
        started_at=datetime.now(UTC),
        status="running",
        run_type="manual",
    )

    for step in ("crawl", "analyze", "score", "report"):
        async with pipe._step_timer(step, run):
            await asyncio.sleep(0.001)
        assert getattr(run, f"{step}_duration_ms") is not None


# ---------------------------------------------------------------------------
# Integration test — run_full populates the per-stage columns
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_run_persists_step_durations() -> None:
    """``Pipeline.run_full`` wraps the crawl block + ``_apply_price_adjustments``
    with ``_step_timer``; score/report remain NULL per Q-3."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    pipe = Pipeline(session=session)

    # Stub all I/O — make crawl + analyze each take ~10ms.
    async def _slow_listings() -> int:
        await asyncio.sleep(0.01)
        return 0

    async def _empty_symbols() -> list[str]:
        return []

    async def _slow_adjust() -> None:
        await asyncio.sleep(0.01)

    async def _empty_batch(_symbols: list[str]) -> tuple[dict, list]:
        return {}, []

    pipe.stock_repo.fetch_and_store_listings = AsyncMock(side_effect=_slow_listings)
    pipe.stock_repo.get_all_hose_symbols = AsyncMock(side_effect=_empty_symbols)
    pipe._crawl_prices = AsyncMock(return_value=({}, []))
    pipe.finance_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.company_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.event_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe._apply_price_adjustments = AsyncMock(side_effect=_slow_adjust)

    run = await pipe.run_full(run_type="manual")

    assert run.status == "completed", f"expected completed, got {run.status}"
    assert run.crawl_duration_ms is not None and run.crawl_duration_ms >= 10, (
        f"crawl_duration_ms={run.crawl_duration_ms}"
    )
    assert run.analyze_duration_ms is not None and run.analyze_duration_ms >= 10, (
        f"analyze_duration_ms={run.analyze_duration_ms}"
    )
    # Q-3: score + report are placeholders until AutomationService integration.
    assert run.score_duration_ms is None
    assert run.report_duration_ms is None
