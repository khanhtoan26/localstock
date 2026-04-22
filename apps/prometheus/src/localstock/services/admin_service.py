"""Admin service — orchestrates background admin operations with job tracking.

Job execution uses a DB-queue pattern:
1. API endpoints create job records (status=pending) and return immediately.
2. A scheduler worker polls for pending jobs every few seconds.
3. Worker picks up the oldest pending job and executes it.
4. This decouples execution from the API process — failures don't crash the server.
"""

import asyncio
from datetime import UTC, datetime

from loguru import logger

from localstock.db.database import get_session_factory
from localstock.db.repositories.job_repo import JobRepository


# Module-level lock to prevent concurrent admin operations
_admin_lock = asyncio.Lock()

# Must keep strong references to background tasks to prevent GC
_background_tasks: set[asyncio.Task] = set()


async def process_pending_jobs() -> None:
    """Poll DB for pending jobs and execute the oldest one.

    Called periodically by APScheduler. Skips if a job is already running
    (lock held) or if no pending jobs exist.
    """
    if _admin_lock.locked():
        return  # A job is already running

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = JobRepository(session)
        job = await repo.get_oldest_pending()
        if not job:
            return

    job_id = job.id
    job_type = job.job_type
    params = job.params or {}

    logger.info(f"Worker picked up job {job_id}: type={job_type}")

    # Mark as running immediately to prevent re-pickup on next poll
    async with session_factory() as session:
        repo = JobRepository(session)
        await repo.update_status(job_id, "running")

    # Execute in background task so the poller returns immediately.
    # Must save reference to prevent garbage collection before completion.
    task = asyncio.create_task(_execute_job(job_id, job_type, params))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _execute_job(job_id: int, job_type: str, params: dict) -> None:
    """Execute a single admin job (called via create_task from the poller)."""
    service = AdminService()
    try:
        match job_type:
            case "crawl":
                await service.run_crawl(job_id, params.get("symbols", []))
            case "analyze":
                await service.run_analyze(job_id, params.get("symbols"))
            case "score":
                await service.run_score(job_id)
            case "report":
                await service.run_report(job_id, params.get("symbol", ""))
            case "pipeline":
                await service.run_pipeline(job_id)
            case _:
                logger.warning(f"Unknown job type: {job_type}")
                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = JobRepository(session)
                    await repo.update_status(job_id, "failed", error=f"Unknown job type: {job_type}")
    except Exception as e:
        logger.error(f"Job {job_id} ({job_type}) unhandled error: {e}")
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = JobRepository(session)
                await repo.update_status(job_id, "failed", error=str(e))
        except Exception:
            logger.error(f"Failed to mark job {job_id} as failed")


class AdminService:
    """Executes admin pipeline operations with job tracking.

    Each run_* method acquires the _admin_lock, updates job status in DB,
    and executes the operation. Called by process_pending_jobs() worker.
    """

    def __init__(self):
        self.session_factory = get_session_factory()

    async def run_crawl(self, job_id: int, symbols: list[str]) -> None:
        """Background: crawl specified symbols."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                async with self.session_factory() as session:
                    from localstock.services.pipeline import Pipeline
                    pipeline = Pipeline(session)
                    results = {}
                    for symbol in symbols:
                        try:
                            result = await pipeline.run_single(symbol)
                            results[symbol] = result
                        except Exception as e:
                            results[symbol] = {"error": str(e)}
                            logger.warning(f"Crawl failed for {symbol}: {e}")
                await self._update_job(job_id, "completed", result=results)
            except Exception as e:
                logger.error(f"Crawl job {job_id} failed: {e}")
                await self._update_job(job_id, "failed", error=str(e))

    async def run_analyze(self, job_id: int, symbols: list[str] | None = None) -> None:
        """Background: run analysis for specified symbols (or all tracked)."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                async with self.session_factory() as session:
                    from localstock.services.analysis_service import AnalysisService
                    service = AnalysisService(session)
                    if symbols and len(symbols) == 1:
                        result = await service.run_single(symbols[0])
                    else:
                        result = await service.run_full()
                await self._update_job(job_id, "completed", result=result)
            except Exception as e:
                logger.error(f"Analyze job {job_id} failed: {e}")
                await self._update_job(job_id, "failed", error=str(e))

    async def run_score(self, job_id: int) -> None:
        """Background: run scoring for all tracked stocks."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                async with self.session_factory() as session:
                    from localstock.services.scoring_service import ScoringService
                    service = ScoringService(session)
                    result = await service.run_full()
                await self._update_job(job_id, "completed", result=result)
            except Exception as e:
                logger.error(f"Score job {job_id} failed: {e}")
                await self._update_job(job_id, "failed", error=str(e))

    async def run_report(self, job_id: int, symbol: str) -> None:
        """Background: generate AI report for a specific symbol."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                async with self.session_factory() as session:
                    from localstock.services.report_service import ReportService
                    service = ReportService(session)
                    result = await service.generate_for_symbol(symbol)
                await self._update_job(job_id, "completed", result=result)
            except Exception as e:
                logger.error(f"Report job {job_id} failed: {e}")
                await self._update_job(job_id, "failed", error=str(e))

    async def run_pipeline(self, job_id: int) -> None:
        """Background: run full daily pipeline (crawl→analyze→score→report)."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                from localstock.services.automation_service import AutomationService
                service = AutomationService()
                result = await service.run_daily_pipeline(force=True)
                await self._update_job(job_id, "completed", result=result)
            except Exception as e:
                logger.error(f"Pipeline job {job_id} failed: {e}")
                await self._update_job(job_id, "failed", error=str(e))

    async def _update_job(
        self, job_id: int, status: str,
        result: dict | None = None, error: str | None = None,
    ) -> None:
        """Update job status using a fresh session."""
        async with self.session_factory() as session:
            repo = JobRepository(session)
            await repo.update_status(job_id, status, result=result, error=error)
