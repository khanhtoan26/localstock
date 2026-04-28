"""APScheduler integration with FastAPI lifespan (AUTO-01).

Per D-02: Runs daily at configured time (default 15:45 VN time) on weekdays.
Per Research Pattern 1: Uses AsyncIOScheduler bound to FastAPI's lifespan.
Per Pitfall 3: Scheduler initialized inside lifespan, NOT at import time.
Per Pitfall 6: Explicit timezone="Asia/Ho_Chi_Minh" on both scheduler and trigger.
"""

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from loguru import logger

from localstock.config import get_settings

# Module-level scheduler instance (configured in setup_scheduler, started in lifespan)
scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")


def setup_scheduler() -> AsyncIOScheduler:
    """Configure the scheduler with the daily pipeline job and admin job worker.

    Returns:
        Configured (but not started) scheduler instance.
    """
    from localstock.services.admin_service import process_pending_jobs
    from localstock.services.automation_service import AutomationService

    settings = get_settings()

    async def daily_job():
        """Scheduled daily pipeline execution."""
        logger.info("scheduler.daily.start")
        service = AutomationService()
        try:
            result = await service.run_daily_pipeline()
            logger.info("scheduler.daily.result", status=result["status"])
        except Exception:
            logger.exception("scheduler.daily.failed")

    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(
            hour=settings.scheduler_run_hour,
            minute=settings.scheduler_run_minute,
            day_of_week="mon-fri",
            timezone="Asia/Ho_Chi_Minh",
        ),
        id="daily_pipeline",
        name="Daily full pipeline",
        replace_existing=True,
        misfire_grace_time=3600,  # 1hr grace if missed
    )

    # Admin job worker — polls DB for pending jobs every 5 seconds
    scheduler.add_job(
        process_pending_jobs,
        trigger="interval",
        seconds=5,
        id="admin_job_worker",
        name="Admin job worker",
        replace_existing=True,
    )

    logger.info(
        "scheduler.configured",
        hour=settings.scheduler_run_hour,
        minute=settings.scheduler_run_minute,
        tz="Asia/Ho_Chi_Minh",
    )
    return scheduler


@asynccontextmanager
async def get_lifespan(app: FastAPI):
    """FastAPI lifespan context manager that starts/stops the scheduler.

    Usage in app.py:
        app = FastAPI(lifespan=get_lifespan)
    """
    from localstock import configure_ssl, configure_vnstock_api_key
    from localstock.observability.logging import configure_logging

    configure_logging()  # idempotent; defensive — covers CLI / scheduler-only entry points
    configure_ssl()
    configure_vnstock_api_key()
    setup_scheduler()
    scheduler.start()
    logger.info("scheduler.started")
    yield
    scheduler.shutdown()
    logger.complete()  # drain enqueued records (RESEARCH Open Question 3)
    logger.info("scheduler.stopped")
