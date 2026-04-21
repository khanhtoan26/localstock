"""Stock repository — CRUD operations for the stocks table."""

from datetime import UTC, datetime

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import Stock


class StockRepository:
    """Repository for Stock model operations.

    Provides upsert semantics for stock listings and
    query methods for HOSE ticker symbols.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_stocks(self, stocks_df: pd.DataFrame) -> int:
        """Upsert stock listings from a DataFrame.

        Expected columns from vnstock Listing.all_symbols():
            symbol, organ_name (or name), exchange, icb_name3, icb_name4,
            issue_share, charter_capital.

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for idempotent upserts.

        Returns:
            Count of upserted rows.
        """
        if stocks_df.empty:
            return 0

        # Map DataFrame columns to model columns
        # vnstock uses 'organ_name' for company name
        name_col = "organ_name" if "organ_name" in stocks_df.columns else "name"

        rows = []
        for _, row in stocks_df.iterrows():
            rows.append(
                {
                    "symbol": str(row["symbol"]).strip(),
                    "name": str(row.get(name_col, "")).strip(),
                    "exchange": str(row.get("exchange", "")).strip(),
                    "industry_icb3": str(row.get("icb_name3", "")) if pd.notna(row.get("icb_name3")) else None,
                    "industry_icb4": str(row.get("icb_name4", "")) if pd.notna(row.get("icb_name4")) else None,
                    "issue_shares": float(row["issue_share"]) if pd.notna(row.get("issue_share")) else None,
                    "charter_capital": float(row["charter_capital"]) if pd.notna(row.get("charter_capital")) else None,
                    "updated_at": datetime.now(UTC),
                }
            )

        stmt = pg_insert(Stock).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": stmt.excluded.name,
                "exchange": stmt.excluded.exchange,
                "industry_icb3": stmt.excluded.industry_icb3,
                "industry_icb4": stmt.excluded.industry_icb4,
                "issue_shares": stmt.excluded.issue_shares,
                "charter_capital": stmt.excluded.charter_capital,
                "updated_at": datetime.now(UTC),
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Upserted {len(rows)} stock listings")
        return len(rows)

    async def get_by_symbol(self, symbol: str) -> Stock | None:
        """Get a Stock by its ticker symbol.

        Args:
            symbol: Stock ticker (e.g., 'VNM').

        Returns:
            Stock instance or None if not found.
        """
        stmt = select(Stock).where(Stock.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_hose_symbols(self) -> list[str]:
        """Return all symbols where exchange='HOSE', ordered alphabetically."""
        stmt = select(Stock.symbol).where(Stock.exchange == "HOSE").order_by(Stock.symbol)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def fetch_and_store_listings(self, source: str = "VCI") -> int:
        """Fetch all symbols from vnstock and store HOSE listings in DB.

        Uses VCI Listing.symbols_by_exchange() directly to avoid the
        broken Vnstock.stock() initializer (VCI Company.__init__ crashes).
        Filters to HSX exchange (VCI's name for HOSE), maps to 'HOSE'.

        Args:
            source: vnstock data source (currently only VCI has exchange data).

        Returns:
            Count of HOSE stocks stored.
        """
        import asyncio

        from localstock.crawlers import suppress_vnstock_output

        def _sync_fetch():
            with suppress_vnstock_output():
                from vnstock.explorer.vci.listing import Listing as VCIListing
                listing = VCIListing()
                return listing.symbols_by_exchange()

        loop = asyncio.get_event_loop()
        all_symbols_df = await loop.run_in_executor(None, _sync_fetch)

        # VCI uses 'HSX' for HOSE exchange
        hose_df = all_symbols_df[all_symbols_df["exchange"] == "HSX"].copy()
        hose_df["exchange"] = "HOSE"

        # Map VCI columns to expected format
        if "organ_name" not in hose_df.columns and "organ_short_name" in hose_df.columns:
            hose_df["organ_name"] = hose_df["organ_short_name"]

        if hose_df.empty:
            logger.warning("No HOSE symbols found from vnstock listing")
            return 0

        count = await self.upsert_stocks(hose_df)
        logger.info(f"Fetched and stored {count} HOSE listings from vnstock (VCI)")
        return count
