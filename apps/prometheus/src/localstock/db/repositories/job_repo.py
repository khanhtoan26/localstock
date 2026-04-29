"""Job repository — CRUD operations for admin_jobs table."""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import AdminJob
from localstock.dq.sanitizer import sanitize_jsonb


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
        params = sanitize_jsonb(params)  # DQ-04 (D-04)
        job = AdminJob(
            job_type=job_type,
            status="pending",
            params=params,
            created_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        logger.info("job_repo.created", job_id=job.id, job_type=job_type)
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
            values["result"] = sanitize_jsonb(result)  # DQ-04 (D-04)
        if error is not None:
            values["error"] = error

        stmt = update(AdminJob).where(AdminJob.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info("job_repo.status_updated", job_id=job_id, status=status)

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

    async def get_oldest_pending(self) -> AdminJob | None:
        """Get the oldest pending job for worker processing.

        Returns:
            Oldest pending AdminJob or None if queue is empty.
        """
        stmt = (
            select(AdminJob)
            .where(AdminJob.status == "pending")
            .order_by(AdminJob.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_pending(self) -> int:
        """Count pending jobs in the queue."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(AdminJob).where(AdminJob.status == "pending")
        result = await self.session.execute(stmt)
        return result.scalar_one()

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
