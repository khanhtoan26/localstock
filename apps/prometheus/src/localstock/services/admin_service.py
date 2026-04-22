"""Admin service — orchestrates background admin operations with job tracking.

Each operation runs in a background asyncio task with its own session lifecycle.
Job status is updated to 'running' → 'completed'/'failed' as the task progresses.
"""

import asyncio
from datetime import UTC, datetime

from loguru import logger

from localstock.db.database import get_session_factory
from localstock.db.repositories.job_repo import JobRepository


# Module-level lock to prevent concurrent admin operations
_admin_lock = asyncio.Lock()


class AdminService:
    """Background task runners for admin operations.

    Each run_* method is designed to be called via asyncio.create_task().
    They manage their own database sessions via get_session_factory().
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
