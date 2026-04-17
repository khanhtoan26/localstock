"""Repository for analysis_reports table with upsert."""

from datetime import date as date_type

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import AnalysisReport


class ReportRepository:
    """Repository for AnalysisReport model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, row: dict) -> None:
        """Upsert a single analysis report. Dedup on (symbol, date, report_type)."""
        stmt = pg_insert(AnalysisReport).values(**row)
        update_cols = {
            col.name: getattr(stmt.excluded, col.name)
            for col in AnalysisReport.__table__.columns
            if col.name not in ("id", "symbol", "date", "report_type")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_analysis_report",
            set_=update_cols,
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Upserted report for {row.get('symbol')} on {row.get('date')}")

    async def get_latest(self, symbol: str) -> AnalysisReport | None:
        """Get the most recent report for a symbol."""
        stmt = (
            select(AnalysisReport)
            .where(AnalysisReport.symbol == symbol)
            .order_by(AnalysisReport.generated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_most_recent(self) -> AnalysisReport | None:
        """Get the single most recent report across all symbols."""
        stmt = (
            select(AnalysisReport)
            .order_by(AnalysisReport.generated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date(self, target_date: date_type) -> list[AnalysisReport]:
        """Get all reports for a specific date, ordered by total_score desc."""
        stmt = (
            select(AnalysisReport)
            .where(AnalysisReport.date == target_date)
            .order_by(AnalysisReport.total_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol_and_date(
        self, symbol: str, target_date: date_type
    ) -> AnalysisReport | None:
        """Get a specific report for symbol on a given date."""
        stmt = (
            select(AnalysisReport)
            .where(AnalysisReport.symbol == symbol)
            .where(AnalysisReport.date == target_date)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
