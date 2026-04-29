"""Phase 24 / OBS-16 — scheduler error listener tests."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from prometheus_client import REGISTRY

from localstock.scheduler.error_listener import _dedup_cache, on_job_error


def _make_event(
    job_id: str = "boom_job",
    exc: BaseException | None = None,
    tb: str = "Traceback (most recent call last):\n  ...\nValueError: test boom",
) -> JobExecutionEvent:
    if exc is None:
        exc = ValueError("test boom")
    return JobExecutionEvent(
        code=EVENT_JOB_ERROR,
        job_id=job_id,
        jobstore="default",
        scheduled_run_time=datetime.now(UTC),
        retval=None,
        exception=exc,
        traceback=tb,
    )


def _counter_value(job_id: str, error_type: str) -> float:
    val = REGISTRY.get_sample_value(
        "localstock_scheduler_job_errors_total",
        {"job_id": job_id, "error_type": error_type},
    )
    return val if val is not None else 0.0


@pytest.fixture(autouse=True)
def _clear_dedup():
    _dedup_cache.clear()
    yield
    _dedup_cache.clear()


def test_job_error_increments_counter():
    """OBS-16 — counter goes up by exactly 1 with (job_id, error_type) labels."""
    before = _counter_value("boom_job", "ValueError")
    on_job_error(_make_event())
    after = _counter_value("boom_job", "ValueError")
    assert after == before + 1


@pytest.mark.asyncio
async def test_job_error_sends_telegram_alert(mock_telegram_send):
    """OBS-16 — first occurrence dispatches Telegram via fire-and-forget task."""
    on_job_error(_make_event())
    # Drain pending tasks (await the fire-and-forget create_task).
    await asyncio.sleep(0.05)
    assert mock_telegram_send.await_count == 1
    msg = mock_telegram_send.await_args.args[0]
    assert "boom_job" in msg
    assert "ValueError" in msg


@pytest.mark.asyncio
async def test_job_error_dedup_within_window(mock_telegram_send):
    """OBS-16 / D-06 — same (job_id, error_type) within 15 min: only ONE alert,
    counter still increments twice."""
    before = _counter_value("boom_job", "ValueError")
    on_job_error(_make_event())
    on_job_error(_make_event())
    await asyncio.sleep(0.05)
    after = _counter_value("boom_job", "ValueError")
    assert after == before + 2
    assert mock_telegram_send.await_count == 1


@pytest.mark.asyncio
async def test_different_error_types_not_deduped(mock_telegram_send):
    """OBS-16 — distinct error_type values get separate alerts (key includes type)."""
    on_job_error(_make_event(exc=ValueError("v")))
    on_job_error(_make_event(exc=KeyError("k")))
    await asyncio.sleep(0.05)
    assert mock_telegram_send.await_count == 2
