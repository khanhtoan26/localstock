"""Phase 24-05 — APScheduler EVENT_JOB_ERROR listener (D-06, OBS-16).

On every job failure:
  1. Increments ``localstock_scheduler_job_errors_total{job_id, error_type}``
     (always — counter is the source of truth for alert rate).
  2. Logs ``scheduler_job_failed`` at ERROR level with the full traceback.
  3. Dispatches a Telegram alert via ``asyncio.create_task`` (fire-and-forget),
     rate-limited by a 15-minute in-memory dedup window keyed by
     ``(job_id, error_type)``. Distinct keys are NOT deduped together.

Threading: APScheduler may invoke listeners from a worker thread depending on
the scheduler implementation. ``threading.Lock`` (NOT ``asyncio.Lock``) guards
the dedup cache so concurrent listener invocations remain safe regardless of
which loop / thread they originate from.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TYPE_CHECKING

from loguru import logger
from prometheus_client import REGISTRY

if TYPE_CHECKING:
    from apscheduler.events import JobExecutionEvent

# In-memory dedup state. Keyed by (job_id, error_type) -> last alert timestamp.
_DEDUP_WINDOW = timedelta(minutes=15)
_dedup_cache: dict[tuple[str, str], datetime] = {}
_dedup_lock = Lock()  # threading.Lock — listener may run from a worker thread.


def _should_alert(key: tuple[str, str], now: datetime) -> bool:
    """Atomically check + update the dedup cache. True iff alert should fire."""
    with _dedup_lock:
        last = _dedup_cache.get(key)
        if last is not None and (now - last) < _DEDUP_WINDOW:
            return False
        _dedup_cache[key] = now
        return True


def _suppress_task_exception(task: asyncio.Task) -> None:
    """Callback that swallows exceptions raised inside the fire-and-forget task.

    Without this, Python emits ``Task exception was never retrieved`` warnings
    when ``_send_telegram`` raises (e.g. network blip).
    """
    try:
        exc = task.exception()
    except (asyncio.CancelledError, asyncio.InvalidStateError):
        return
    if exc is not None:
        logger.warning(
            "scheduler.alert.task_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def _send_telegram(
    job_id: str,
    error_type: str,
    exc: BaseException,
    traceback_str: str,
) -> None:
    """Best-effort Telegram dispatch."""
    try:
        from localstock.notifications.telegram import TelegramNotifier

        notifier = TelegramNotifier()
        if not notifier.is_configured:
            return
        tb_snippet = (traceback_str or "")[:500]
        msg = (
            "🚨 <b>Scheduler job failed</b>\n"
            f"Job: <code>{job_id}</code>\n"
            f"Error: <code>{error_type}</code>: {exc}\n"
            f"<pre>{tb_snippet}</pre>"
        )
        await notifier.send_message(msg)
    except Exception:
        logger.exception("scheduler.alert.dispatch_failed", job_id=job_id)


def on_job_error(event: "JobExecutionEvent") -> None:
    """APScheduler ``EVENT_JOB_ERROR`` handler.

    Counter inc + structured ERROR log run unconditionally. Telegram dispatch
    is rate-limited by ``_should_alert``. Telegram itself is fire-and-forget.
    """
    job_id = event.job_id or "<unknown>"
    exc = event.exception
    error_type = type(exc).__name__ if exc is not None else "Unknown"
    traceback_str = event.traceback or ""

    # 1) Counter — always.
    counter = REGISTRY._names_to_collectors.get(
        "localstock_scheduler_job_errors_total"
    )
    if counter is not None:
        counter.labels(job_id=job_id, error_type=error_type).inc()

    # 2) Log — always (full traceback as structured kwarg, no f-string).
    logger.bind(job_id=job_id, error_type=error_type).error(
        "scheduler_job_failed", traceback=traceback_str
    )

    # 3) Telegram — rate-limited.
    key = (job_id, error_type)
    if not _should_alert(key, datetime.now(UTC)):
        return

    coro = _send_telegram(
        job_id, error_type, exc or RuntimeError("unknown"), traceback_str
    )
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro)
        task.add_done_callback(_suppress_task_exception)
    except RuntimeError:
        # Listener fired from a thread without a running loop. Last resort —
        # block briefly to dispatch on a one-shot loop.
        try:
            asyncio.run(coro)
        except Exception:
            logger.exception("scheduler.alert.no_loop", job_id=job_id)
