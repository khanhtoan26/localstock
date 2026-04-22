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
        logger.info("Scheduled daily pipeline starting...")
        service = AutomationService()
        try:
            result = await service.run_daily_pipeline()
            logger.info(f"Scheduled pipeline result: status={result['status']}")
        except Exception as e:
            logger.error(f"Scheduled pipeline failed: {e}")

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
        f"Scheduler configured: daily pipeline at "
        f"{settings.scheduler_run_hour}:{settings.scheduler_run_minute:02d} VN time"
    )
    return scheduler


@asynccontextmanager
async def get_lifespan(app: FastAPI):
    """FastAPI lifespan context manager that starts/stops the scheduler.

    Usage in app.py:
        app = FastAPI(lifespan=get_lifespan)
    """
    setup_scheduler()
    scheduler.start()
    logger.info("APScheduler started")
    yield
    scheduler.shutdown()
    logger.info("APScheduler stopped")
