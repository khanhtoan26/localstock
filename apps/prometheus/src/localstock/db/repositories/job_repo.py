"""Job repository — CRUD operations for admin_jobs table."""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import AdminJob


class JobRepository:
    """Repository for AdminJob model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, job_type: str, params: dict | None = None) -> AdminJob:
        """Create a new job record with status='pending'.

        Args:
            job_type: One of 'crawl', 'analyze', 'score', 'report', 'pipeline'.
            params: Optional params dict (e.g., {"symbols": ["VNM"]}).

        Returns:
            Created AdminJob instance with id populated.
        """
        job = AdminJob(
            job_type=job_type,
            status="pending",
            params=params,
            created_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        logger.info(f"Created admin job {job.id}: type={job_type}")
        return job

    async def update_status(
        self,
        job_id: int,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status and optional result/error.

        Args:
            job_id: The job ID to update.
            status: New status ('running', 'completed', 'failed').
            result: Optional result dict (for completed jobs).
            error: Optional error message (for failed jobs).
        """
        values: dict = {"status": status}
        if status == "running":
            values["started_at"] = datetime.now(UTC)
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.now(UTC)
        if result is not None:
            values["result"] = result
        if error is not None:
            values["error"] = error

        stmt = update(AdminJob).where(AdminJob.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Updated job {job_id} status={status}")

    async def list_recent(self, limit: int = 50) -> list[AdminJob]:
        """List recent jobs ordered by created_at descending.

        Args:
            limit: Max number of jobs to return.

        Returns:
            List of AdminJob instances.
        """
        stmt = (
            select(AdminJob)
            .order_by(AdminJob.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, job_id: int) -> AdminJob | None:
        """Get a single job by ID.

        Args:
            job_id: The job ID.

        Returns:
            AdminJob instance or None if not found.
        """
        stmt = select(AdminJob).where(AdminJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
