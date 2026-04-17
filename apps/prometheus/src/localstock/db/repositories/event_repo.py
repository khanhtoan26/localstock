"""Repository for corporate_events table with upsert semantics."""

from datetime import date

import pandas as pd
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import CorporateEvent


class EventRepository:
    """Repository for CorporateEvent model operations.

    Provides upsert semantics for corporate events and tracking of
    which events have had price adjustments applied (processed flag).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_events(self, symbol: str, events_df: pd.DataFrame) -> int:
        """Upsert corporate events for a symbol.

        Uses PostgreSQL INSERT ... ON CONFLICT (symbol, exright_date, event_type)
        DO UPDATE for idempotent writes.

        Maps vnstock event_list_code to canonical event_type via
        EventCrawler.parse_event_type().

        Args:
            symbol: Stock ticker (e.g., 'ACB').
            events_df: DataFrame from vnstock Company.events() with columns:
                event_title, exright_date, record_date, event_list_code,
                ratio, value, public_date.

        Returns:
            Count of upserted rows.
        """
        from localstock.crawlers.event_crawler import EventCrawler

        if events_df is None or events_df.empty:
            return 0

        rows = []
        for _, row in events_df.iterrows():
            # Parse exright_date
            exright_date = row.get("exright_date")
            if isinstance(exright_date, str):
                exright_date = date.fromisoformat(exright_date)
            elif not isinstance(exright_date, date):
                exright_date = None

            # Parse record_date
            record_date = row.get("record_date")
            if isinstance(record_date, str):
                record_date = date.fromisoformat(record_date)
            elif not isinstance(record_date, date):
                record_date = None

            # Parse public_date
            public_date = row.get("public_date")
            if isinstance(public_date, str):
                public_date = date.fromisoformat(public_date)
            elif not isinstance(public_date, date):
                public_date = None

            event_type = EventCrawler.parse_event_type(
                row.get("event_list_code")
            )

            rows.append(
                {
                    "symbol": symbol,
                    "event_title": str(row.get("event_title", ""))[:500]
                    if row.get("event_title")
                    else None,
                    "event_type": event_type,
                    "exright_date": exright_date,
                    "record_date": record_date,
                    "ratio": float(row["ratio"])
                    if pd.notna(row.get("ratio"))
                    else None,
                    "value": float(row["value"])
                    if pd.notna(row.get("value"))
                    else None,
                    "public_date": public_date,
                    "processed": False,
                }
            )

        if not rows:
            return 0

        # Deduplicate rows by constraint key (symbol, exright_date, event_type)
        # to avoid "ON CONFLICT DO UPDATE cannot affect row a second time"
        seen = set()
        unique_rows = []
        for row in rows:
            key = (row["symbol"], row["exright_date"], row["event_type"])
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)

        stmt = pg_insert(CorporateEvent).values(unique_rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_corporate_event",
            set_={
                "event_title": stmt.excluded.event_title,
                "ratio": stmt.excluded.ratio,
                "value": stmt.excluded.value,
                "record_date": stmt.excluded.record_date,
                "public_date": stmt.excluded.public_date,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Upserted {len(rows)} corporate events for {symbol}")
        return len(rows)

    async def get_unprocessed_events(
        self, symbol: str | None = None
    ) -> list[CorporateEvent]:
        """Return events where processed=False, optionally filtered by symbol.

        ORDER BY exright_date ASC (process oldest first).

        Args:
            symbol: Optional symbol filter. If None, returns all unprocessed.

        Returns:
            List of CorporateEvent model instances.
        """
        stmt = (
            select(CorporateEvent)
            .where(CorporateEvent.processed == False)  # noqa: E712
            .order_by(CorporateEvent.exright_date.asc())
        )

        if symbol is not None:
            stmt = stmt.where(CorporateEvent.symbol == symbol)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_processed(self, event_id: int) -> None:
        """Set processed=True for an event after price adjustment is applied.

        Args:
            event_id: Primary key of the CorporateEvent to mark.
        """
        stmt = (
            update(CorporateEvent)
            .where(CorporateEvent.id == event_id)
            .values(processed=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        logger.info(f"Marked corporate event {event_id} as processed")
