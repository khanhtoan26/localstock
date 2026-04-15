"""Pipeline orchestrator — runs the full data ingestion sequence.

Sequence (per D-05 backfill + incremental strategy):
1. Fetch and store HOSE stock listings
2. Crawl OHLCV prices for all HOSE symbols (incremental: only after latest stored date)
3. Crawl financial statements for all HOSE symbols
4. Crawl company profiles for all HOSE symbols
5. Crawl corporate events for all HOSE symbols
6. Apply price adjustments for unprocessed corporate events

Error handling per D-02: failed symbols are skipped and logged.
Pipeline continues even if individual symbols fail.
"""

from datetime import UTC, date, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.crawlers.company_crawler import CompanyCrawler
from localstock.crawlers.event_crawler import EventCrawler
from localstock.crawlers.finance_crawler import FinanceCrawler
from localstock.crawlers.price_crawler import PriceCrawler
from localstock.db.models import PipelineRun
from localstock.db.repositories.event_repo import EventRepository
from localstock.db.repositories.financial_repo import FinancialRepository
from localstock.db.repositories.price_repo import PriceRepository
from localstock.db.repositories.stock_repo import StockRepository
from localstock.services.price_adjuster import adjust_prices_for_event


class Pipeline:
    """Orchestrates the full data ingestion pipeline.

    Runs all crawlers in sequence, stores results, and applies
    price adjustments for corporate actions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)
        self.price_repo = PriceRepository(session)
        self.financial_repo = FinancialRepository(session)
        self.event_repo = EventRepository(session)
        self.price_crawler = PriceCrawler()
        self.finance_crawler = FinanceCrawler()
        self.company_crawler = CompanyCrawler()
        self.event_crawler = EventCrawler()

    async def run_full(self, run_type: str = "daily") -> PipelineRun:
        """Run the complete pipeline. Returns PipelineRun with status.

        Args:
            run_type: 'backfill', 'daily', or 'manual'.

        Returns:
            PipelineRun model instance with status and error details.
        """
        run = PipelineRun(
            started_at=datetime.now(UTC),
            status="running",
            run_type=run_type,
        )
        self.session.add(run)
        await self.session.commit()

        try:
            # Step 1: Fetch stock listings
            count = await self.stock_repo.fetch_and_store_listings()
            logger.info(f"Step 1: Stored {count} HOSE stock listings")

            # Step 2: Get all HOSE symbols
            symbols = await self.stock_repo.get_all_hose_symbols()
            run.symbols_total = len(symbols)

            # Step 3: Crawl prices (incremental)
            price_results, price_failed = await self._crawl_prices(symbols)

            # Step 4: Crawl financials
            fin_results, fin_failed = await self.finance_crawler.fetch_batch(
                symbols
            )

            # Step 5: Crawl company profiles
            company_results, company_failed = (
                await self.company_crawler.fetch_batch(symbols)
            )

            # Step 6: Crawl corporate events
            event_results, event_failed = (
                await self.event_crawler.fetch_batch(symbols)
            )

            # Step 7: Store event results in DB
            for symbol, events_df in event_results.items():
                try:
                    await self.event_repo.upsert_events(symbol, events_df)
                except Exception as e:
                    logger.warning(
                        f"Failed to store events for {symbol}: {e}"
                    )

            # Step 8: Apply price adjustments for unprocessed events
            await self._apply_price_adjustments()

            # Update run status
            all_failed = {
                f[0]
                for f in price_failed
                + fin_failed
                + company_failed
                + event_failed
            }
            run.symbols_success = len(symbols) - len(all_failed)
            run.symbols_failed = len(all_failed)
            run.errors = (
                {"failed_symbols": sorted(all_failed)} if all_failed else None
            )
            run.status = "completed"
            run.completed_at = datetime.now(UTC)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            run.status = "failed"
            run.completed_at = datetime.now(UTC)
            run.errors = {"error": str(e)}

        await self.session.commit()
        return run

    async def _crawl_prices(
        self, symbols: list[str]
    ) -> tuple[dict, list]:
        """Crawl prices with incremental strategy per D-05.

        For each symbol, check latest date in DB and only fetch new data.
        Uses 2-year backfill (730 days) for symbols with no existing data
        (per DATA-02).

        Returns:
            Tuple of (results_dict, failed_list).
        """
        results = {}
        failed = []
        for symbol in symbols:
            try:
                latest = await self.price_repo.get_latest_date(symbol)
                start = (
                    (latest + timedelta(days=1)).isoformat()
                    if latest
                    else (date.today() - timedelta(days=730)).isoformat()
                )
                end = date.today().isoformat()

                if latest and latest >= date.today():
                    logger.debug(
                        f"Skipping {symbol}: already up to date"
                    )
                    continue

                df = await self.price_crawler.fetch(
                    symbol, start_date=start, end_date=end
                )
                await self.price_repo.upsert_prices(symbol, df)
                results[symbol] = df
            except Exception as e:
                failed.append((symbol, str(e)))
                logger.warning(f"Price crawl failed for {symbol}: {e}")
        return results, failed

    async def _apply_price_adjustments(self) -> None:
        """Apply backward price adjustment for all unprocessed corporate events.

        Per T-01-10: logs all adjustments with ratio and symbol.
        Only processes events with valid ratio and exright_date,
        and only known event types (split/stock_dividend) per T-01-11.
        """
        unprocessed = await self.event_repo.get_unprocessed_events()
        adjustable_types = {"split", "stock_dividend"}

        for event in unprocessed:
            if (
                event.ratio
                and event.exright_date
                and event.ratio != 1.0
                and event.event_type in adjustable_types
            ):
                try:
                    # Fetch all prices for this symbol
                    prices = await self.price_repo.get_prices(event.symbol)
                    if prices:
                        import pandas as pd

                        price_df = pd.DataFrame(
                            [
                                {
                                    "date": p.date,
                                    "open": p.open,
                                    "high": p.high,
                                    "low": p.low,
                                    "close": p.close,
                                    "volume": p.volume,
                                }
                                for p in prices
                            ]
                        )
                        adjusted_df = adjust_prices_for_event(
                            price_df,
                            ex_date=event.exright_date,
                            ratio=event.ratio,
                        )
                        await self.price_repo.upsert_prices(
                            event.symbol, adjusted_df.rename(
                                columns={"date": "time"}
                            )
                        )
                    await self.event_repo.mark_processed(event.id)
                    logger.info(
                        f"Applied price adjustment for {event.symbol}: "
                        f"ratio={event.ratio}, ex_date={event.exright_date}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to adjust prices for {event.symbol} "
                        f"event {event.id}: {e}"
                    )
            elif event.ratio and event.exright_date:
                # Mark non-adjustable events as processed (cash dividends, etc.)
                await self.event_repo.mark_processed(event.id)
                logger.info(
                    f"Skipped adjustment for {event.symbol} "
                    f"({event.event_type}): not an adjustable event type"
                )

    async def run_single(self, symbol: str) -> dict:
        """Run pipeline for a single symbol (on-demand analysis).

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Returns:
            Summary dict with status and counts.
        """
        logger.info(f"Running single-symbol pipeline for {symbol}")
        summary: dict = {
            "symbol": symbol,
            "status": "completed",
            "errors": [],
        }

        try:
            # Price
            df = await self.price_crawler.fetch(symbol)
            await self.price_repo.upsert_prices(symbol, df)
            summary["prices"] = len(df)
        except Exception as e:
            summary["errors"].append(f"prices: {e}")

        try:
            # Financials
            fin_data = await self.finance_crawler.fetch(symbol)
            summary["financials"] = (
                len(fin_data) if isinstance(fin_data, dict) else 0
            )
        except Exception as e:
            summary["errors"].append(f"financials: {e}")

        try:
            # Company
            company_df = await self.company_crawler.fetch(symbol)
            summary["company"] = not company_df.empty
        except Exception as e:
            summary["errors"].append(f"company: {e}")

        try:
            # Events
            events_df = await self.event_crawler.fetch(symbol)
            summary["events"] = len(events_df)
        except Exception as e:
            summary["errors"].append(f"events: {e}")

        if summary["errors"]:
            summary["status"] = "partial"
        return summary
