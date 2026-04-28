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
from localstock.observability.context import run_id_var
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

        run_id = str(run.id)
        token = run_id_var.set(run_id)
        try:
            with logger.contextualize(run_id=run_id, pipeline_run_id=run.id):
                logger.info("pipeline.run.started", run_type=run_type)
                try:
                    # Step 1: Fetch stock listings (non-critical — fall back to DB)
                    try:
                        count = await self.stock_repo.fetch_and_store_listings()
                        logger.info("pipeline.listings.stored", step=1, count=count)
                    except Exception as e:
                        logger.warning(
                            "pipeline.listings.fetch_failed",
                            step=1,
                            error=str(e),
                        )

                    # Step 2: Get all HOSE symbols
                    symbols = await self.stock_repo.get_all_hose_symbols()
                    run.symbols_total = len(symbols)

                    # Step 3: Crawl prices (incremental)
                    price_results, price_failed = await self._crawl_prices(symbols)

                    # Step 4: Crawl financials
                    fin_results, fin_failed = await self.finance_crawler.fetch_batch(
                        symbols
                    )

                    # Step 4b: Store financial statements in DB
                    for symbol, reports in fin_results.items():
                        await self._store_financials(symbol, reports)

                    # Step 5: Crawl company profiles
                    company_results, company_failed = (
                        await self.company_crawler.fetch_batch(symbols)
                    )

                    # Step 5b: Store company profiles in DB
                    for symbol, overview_df in company_results.items():
                        try:
                            stock_dict = self.company_crawler.overview_to_stock_dict(
                                overview_df
                            )
                            import pandas as pd

                            await self.stock_repo.upsert_stocks(
                                pd.DataFrame([stock_dict])
                            )
                        except Exception as e:
                            logger.warning(
                                "pipeline.company.store_failed",
                                symbol=symbol,
                                error=str(e),
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
                                "pipeline.events.store_failed",
                                symbol=symbol,
                                error=str(e),
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
                    logger.exception("pipeline.run.errored")
                    run.status = "failed"
                    run.completed_at = datetime.now(UTC)
                    run.errors = {"error": str(e)}
                finally:
                    logger.info("pipeline.run.completed", status=run.status)

            await self.session.commit()
            return run
        finally:
            run_id_var.reset(token)

    async def _store_financials(
        self, symbol: str, reports: dict
    ) -> None:
        """Store financial statement DataFrames to the database.

        Handles both vnstock 3.x format (rows with yearReport/lengthReport)
        and vnstock 4.x wide format (rows are line items, columns are quarters).

        Args:
            symbol: Stock ticker.
            reports: Dict mapping report_type to DataFrame.
        """
        import math
        import pandas as pd

        def _clean_nan(obj):
            """Recursively replace NaN/inf with None in nested structures."""
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            if isinstance(obj, dict):
                return {k: _clean_nan(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_clean_nan(v) for v in obj]
            return obj

        for report_type, df in reports.items():
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                continue
            try:
                if "yearReport" in df.columns:
                    # vnstock 3.x long format: one row per year/period
                    for _, row in df.iterrows():
                        year = int(row.get("yearReport", 0))
                        length = row.get("lengthReport", "")
                        period = (
                            f"Q{length}" if str(length).isdigit() else str(length)
                        )
                        data = _clean_nan(row.to_dict())
                        await self.financial_repo.upsert_statement(
                            symbol=symbol,
                            year=year,
                            period=period,
                            report_type=report_type,
                            data=data,
                            source="VCI",
                        )
                else:
                    # vnstock 4.x wide format: rows are line items, columns are quarters
                    # Store entire report as single record per report_type
                    data = _clean_nan(df.to_dict(orient="records"))
                    await self.financial_repo.upsert_statement(
                        symbol=symbol,
                        year=0,
                        period="latest",
                        report_type=report_type,
                        data={"items": data, "format": "wide"},
                        source="VCI",
                    )
            except Exception as e:
                await self.session.rollback()
                logger.warning(
                    "pipeline.financials.store_failed",
                    report_type=report_type,
                    symbol=symbol,
                    error=str(e),
                )

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
                        "pipeline.prices.skip_up_to_date", symbol=symbol
                    )
                    continue

                df = await self.price_crawler.fetch(
                    symbol, start_date=start, end_date=end
                )
                await self.price_repo.upsert_prices(symbol, df)
                results[symbol] = df
            except Exception as e:
                failed.append((symbol, str(e)))
                logger.warning(
                    "pipeline.prices.crawl_failed",
                    symbol=symbol,
                    error=str(e),
                )
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
                        "pipeline.adjustment.applied",
                        symbol=event.symbol,
                        ratio=event.ratio,
                        ex_date=str(event.exright_date),
                    )
                except Exception:
                    logger.exception(
                        "pipeline.adjustment.failed",
                        symbol=event.symbol,
                        event_id=event.id,
                    )
            elif event.ratio and event.exright_date:
                # Mark non-adjustable events as processed (cash dividends, etc.)
                await self.event_repo.mark_processed(event.id)
                logger.info(
                    "pipeline.adjustment.skipped",
                    symbol=event.symbol,
                    event_type=event.event_type,
                )

    async def run_single(self, symbol: str) -> dict:
        """Run pipeline for a single symbol (on-demand analysis).

        Args:
            symbol: Stock ticker (e.g., 'ACB').

        Returns:
            Summary dict with status and counts.
        """
        logger.info("pipeline.run_single.start", symbol=symbol)
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
            await self._store_financials(symbol, fin_data)
            summary["financials"] = (
                len(fin_data) if isinstance(fin_data, dict) else 0
            )
        except Exception as e:
            summary["errors"].append(f"financials: {e}")

        try:
            # Company
            company_df = await self.company_crawler.fetch(symbol)
            import pandas as pd

            stock_dict = self.company_crawler.overview_to_stock_dict(company_df)
            await self.stock_repo.upsert_stocks(pd.DataFrame([stock_dict]))
            summary["company"] = not company_df.empty
        except Exception as e:
            summary["errors"].append(f"company: {e}")

        try:
            # Events
            events_df = await self.event_crawler.fetch(symbol)
            await self.event_repo.upsert_events(symbol, events_df)
            summary["events"] = len(events_df)
        except Exception as e:
            summary["errors"].append(f"events: {e}")

        if summary["errors"]:
            summary["status"] = "partial"
        return summary
