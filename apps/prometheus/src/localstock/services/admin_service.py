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
from localstock.services.pipeline import _truncate_error


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

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_oldest_pending()
            if not job:
                return
    except Exception as e:
        logger.debug("admin.worker.db_unavailable", error_type=e.__class__.__name__)
        return

    job_id = job.id
    job_type = job.job_type
    params = job.params or {}

    logger.info("admin.job.picked_up", job_id=job_id, job_type=job_type)

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
                await service.run_score(job_id, params.get("symbols"))
            case "report":
                await service.run_report(job_id, params.get("symbols"))
            case "pipeline":
                await service.run_pipeline(job_id, params.get("symbols"))
            case _:
                logger.warning("admin.job.unknown_type", job_type=job_type)
                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = JobRepository(session)
                    await repo.update_status(job_id, "failed", error=f"Unknown job type: {job_type}")
    except Exception as e:
        logger.exception("admin.job.unhandled_error", job_id=job_id, job_type=job_type)
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = JobRepository(session)
                await repo.update_status(job_id, "failed", error=str(e))
        except Exception:
            logger.exception("admin.job.mark_failed_error", job_id=job_id)


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
                            results[symbol] = {"error": _truncate_error(e)}
                            logger.warning(
                                "admin.crawl.symbol_failed",
                                symbol=symbol,
                                step="admin.crawl",
                                exception_class=type(e).__name__,
                                message=str(e)[:200],
                            )
                await self._update_job(job_id, "completed", result=results)
            except Exception as e:
                logger.exception("admin.crawl.job_failed", job_id=job_id)
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
                logger.exception("admin.analyze.job_failed", job_id=job_id)
                await self._update_job(job_id, "failed", error=str(e))

    async def run_score(self, job_id: int, symbols: list[str] | None = None) -> None:
        """Background: run scoring for specified stocks (or all tracked)."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                async with self.session_factory() as session:
                    from localstock.services.scoring_service import ScoringService
                    service = ScoringService(session)
                    result = await service.run_full(symbols=symbols)
                await self._update_job(job_id, "completed", result=result)
            except Exception as e:
                logger.exception("admin.score.job_failed", job_id=job_id)
                await self._update_job(job_id, "failed", error=str(e))

    async def run_report(self, job_id: int, symbols: list[str] | None = None) -> None:
        """Background: generate AI reports for specified symbols."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                results: dict = {}
                for symbol in (symbols or []):
                    try:
                        async with self.session_factory() as session:
                            from localstock.services.report_service import ReportService
                            service = ReportService(session)
                            r = await service.generate_for_symbol(symbol)
                            results[symbol] = r
                    except Exception as e:
                        results[symbol] = {"error": _truncate_error(e)}
                        logger.warning(
                            "admin.report.symbol_failed",
                            symbol=symbol,
                            step="admin.report",
                            exception_class=type(e).__name__,
                            message=str(e)[:200],
                        )
                await self._update_job(job_id, "completed", result=results)
            except Exception as e:
                logger.exception("admin.report.job_failed", job_id=job_id)
                await self._update_job(job_id, "failed", error=str(e))

    async def run_pipeline(self, job_id: int, symbols: list[str] | None = None) -> None:
        """Background: run pipeline (crawl→analyze→score) for specified symbols."""
        async with _admin_lock:
            await self._update_job(job_id, "running")
            try:
                results: dict = {"crawl": {}, "analyze": {}, "score": {}}

                # Step 1: Crawl
                async with self.session_factory() as session:
                    from localstock.services.pipeline import Pipeline
                    pipeline = Pipeline(session)
                    target = symbols or []
                    for symbol in target:
                        try:
                            result = await pipeline.run_single(symbol)
                            results["crawl"][symbol] = result
                        except Exception as e:
                            results["crawl"][symbol] = {"error": _truncate_error(e)}
                            logger.warning(
                                "admin.pipeline.crawl_failed",
                                symbol=symbol,
                                step="admin.pipeline.crawl",
                                exception_class=type(e).__name__,
                                message=str(e)[:200],
                            )
                logger.info("admin.pipeline.crawl_done", symbols=len(target))

                # Step 2: Analyze
                async with self.session_factory() as session:
                    from localstock.services.analysis_service import AnalysisService
                    service = AnalysisService(session)
                    if symbols and len(symbols) == 1:
                        results["analyze"] = await service.run_single(symbols[0])
                    elif symbols:
                        for symbol in symbols:
                            try:
                                r = await service.run_single(symbol)
                                results["analyze"][symbol] = r
                            except Exception as e:
                                results["analyze"][symbol] = {"error": _truncate_error(e)}
                                logger.warning(
                                    "admin.pipeline.analyze_failed",
                                    symbol=symbol,
                                    step="admin.pipeline.analyze",
                                    exception_class=type(e).__name__,
                                    message=str(e)[:200],
                                )
                    else:
                        results["analyze"] = await service.run_full()
                logger.info("Pipeline analyze done")

                # Step 3: Score
                async with self.session_factory() as session:
                    from localstock.services.scoring_service import ScoringService
                    service = ScoringService(session)
                    results["score"] = await service.run_full(symbols=symbols)
                logger.info("Pipeline score done")

                # Step 4: Report
                results["report"] = {}
                target_symbols = symbols or []
                for symbol in target_symbols:
                    try:
                        async with self.session_factory() as session:
                            from localstock.services.report_service import ReportService
                            service = ReportService(session)
                            r = await service.generate_for_symbol(symbol)
                            results["report"][symbol] = r
                    except Exception as e:
                        results["report"][symbol] = {"error": _truncate_error(e)}
                        logger.warning(
                            "admin.pipeline.report_failed",
                            symbol=symbol,
                            step="admin.pipeline.report",
                            exception_class=type(e).__name__,
                            message=str(e)[:200],
                        )
                logger.info("admin.pipeline.report_done", symbols=len(target_symbols))

                await self._update_job(job_id, "completed", result=results)
            except Exception as e:
                logger.exception("admin.pipeline.job_failed", job_id=job_id)
                await self._update_job(job_id, "failed", error=str(e))

    async def _update_job(
        self, job_id: int, status: str,
        result: dict | None = None, error: str | None = None,
    ) -> None:
        """Update job status using a fresh session."""
        async with self.session_factory() as session:
            repo = JobRepository(session)
            await repo.update_status(job_id, status, result=result, error=error)
