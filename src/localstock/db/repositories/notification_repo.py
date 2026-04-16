"""Repository for notification_logs table — deduplication of sent notifications."""

from datetime import UTC, date as date_type, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import NotificationLog


class NotificationRepository:
    """Repository for NotificationLog model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_notification(
        self,
        target_date: date_type,
        notification_type: str,
        status: str,
        details: dict | None = None,
    ) -> None:
        """Log a notification attempt. Upserts on (date, notification_type)."""
        stmt = pg_insert(NotificationLog).values(
            date=target_date,
            notification_type=notification_type,
            sent_at=datetime.now(UTC),
            status=status,
            details=details,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_notification_log",
            set_={
                "sent_at": stmt.excluded.sent_at,
                "status": stmt.excluded.status,
                "details": stmt.excluded.details,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def was_sent_today(
        self, notification_type: str, target_date: date_type | None = None
    ) -> bool:
        """Check if a notification of given type was already sent for the date."""
        d = target_date or date_type.today()
        stmt = select(NotificationLog).where(
            NotificationLog.date == d,
            NotificationLog.notification_type == notification_type,
            NotificationLog.status == "sent",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
