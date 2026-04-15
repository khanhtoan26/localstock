"""Repository for financial_statements table with upsert semantics."""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import FinancialStatement


class FinancialRepository:
    """Repository for FinancialStatement model operations.

    Provides upsert semantics for financial statements and
    query methods for incremental crawling.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_statement(
        self,
        symbol: str,
        year: int,
        period: str,
        report_type: str,
        data: dict,
        source: str,
        unit: str = "billion_vnd",
    ) -> None:
        """Upsert a single financial statement.

        Uses PostgreSQL INSERT ... ON CONFLICT (symbol, year, period, report_type)
        DO UPDATE for idempotent writes.

        Args:
            symbol: Stock ticker (e.g., 'ACB').
            year: Fiscal year.
            period: 'Q1', 'Q2', 'Q3', 'Q4', or 'annual'.
            report_type: 'balance_sheet', 'income_statement', or 'cash_flow'.
            data: Full report data as dict (stored as JSON).
            source: Data source ('VCI' or 'KBS').
            unit: Normalized unit (default: 'billion_vnd').
        """
        stmt = pg_insert(FinancialStatement).values(
            symbol=symbol,
            year=year,
            period=period,
            report_type=report_type,
            data=data,
            unit=unit,
            source=source,
            fetched_at=datetime.now(UTC),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_financial_stmt",
            set_={
                "data": stmt.excluded.data,
                "unit": stmt.excluded.unit,
                "source": stmt.excluded.source,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def upsert_batch(
        self, symbol: str, statements: list[dict]
    ) -> int:
        """Upsert multiple financial statements for a symbol.

        Each dict should contain: year, period, report_type, data, source, unit.

        Args:
            symbol: Stock ticker.
            statements: List of statement dicts to upsert.

        Returns:
            Count of upserted rows.
        """
        count = 0
        for stmt_data in statements:
            await self.upsert_statement(symbol=symbol, **stmt_data)
            count += 1
        return count

    async def get_latest_period(
        self, symbol: str, report_type: str
    ) -> tuple[int, str] | None:
        """Return (year, period) of the most recent statement for incremental crawl.

        Args:
            symbol: Stock ticker.
            report_type: 'balance_sheet', 'income_statement', or 'cash_flow'.

        Returns:
            Tuple of (year, period) or None if no statements exist.
        """
        stmt = (
            select(FinancialStatement.year, FinancialStatement.period)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.report_type == report_type,
            )
            .order_by(
                FinancialStatement.year.desc(),
                FinancialStatement.period.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row:
            return (row[0], row[1])
        return None
