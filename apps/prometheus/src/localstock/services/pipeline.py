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

import time
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta

from loguru import logger
from prometheus_client import REGISTRY
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
from localstock.dq import MAX_ERROR_CHARS
from localstock.dq.quarantine_repo import QuarantineRepository
from localstock.dq.runner import partition_valid_invalid
from localstock.dq.sanitizer import sanitize_jsonb
from localstock.dq.schemas.ohlcv import OHLCVSchema
from localstock.observability.context import run_id_var
from localstock.services.price_adjuster import adjust_prices_for_event


def _truncate_error(exc: BaseException) -> str:
    """Format an exception as ``'{ExcClass}: {str(exc)[:MAX_ERROR_CHARS]}'``.

    Phase 25 / DQ-06 + DQ-05 — bounded error string for ``failed_symbols``
    JSONB entries (CONTEXT D-07 + RESEARCH Pitfall G). Truncates at
    ``MAX_ERROR_CHARS`` to keep ``PipelineRun.stats`` row size bounded even
    when a 400-symbol pipeline produces large exception messages. Only
    ``str(exc)`` is captured — never the traceback (T-25-04-01 mitigation).

    Used both by ``_write_stats`` (to format pre-existing failed-symbol
    tuples) and by the per-symbol isolation wrappers landing in 25-06.
    """
    msg = str(exc)
    if len(msg) > MAX_ERROR_CHARS:
        msg = msg[:MAX_ERROR_CHARS] + "..."
    return f"{type(exc).__name__}: {msg}"


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

    @asynccontextmanager
    async def _step_timer(self, step_name: str, run: PipelineRun):
        """Phase 24 / OBS-17 — time a pipeline step.

        Records the elapsed milliseconds onto
        ``run.<step_name>_duration_ms`` AND emits the
        ``localstock_op_duration_seconds`` histogram with labels
        ``(domain="pipeline", subsystem="step", action=<step_name>,
        outcome={"success","fail"})`` — even when the wrapped block raises.

        D-08 / RESEARCH Pitfall 7: ordering is
        ``try / yield / except (set fail outcome, re-raise) / finally
        (record column + observe metric)``. The ``finally`` block runs before
        the exception propagates, guaranteeing the duration column is written.

        D-08 boundary note: ``services/pipeline.py`` is the documented
        exception that may call ``.observe()`` directly on a
        ``observability/metrics.py`` primitive (the ``@observe`` decorator
        cannot write the per-stage column). See 24-CONTEXT.md.
        """
        t0 = time.perf_counter()
        outcome = "success"
        try:
            yield
        except Exception:
            outcome = "fail"
            raise
        finally:
            elapsed = time.perf_counter() - t0
            duration_ms = int(elapsed * 1000)
            setattr(run, f"{step_name}_duration_ms", duration_ms)
            hist = REGISTRY._names_to_collectors.get(
                "localstock_op_duration_seconds"
            )
            if hist is not None:
                hist.labels(
                    "pipeline", "step", step_name, outcome
                ).observe(elapsed)

    def _write_stats(
        self,
        run: PipelineRun,
        *,
        succeeded: int,
        failed: int,
        skipped: int,
        failed_symbols: list[dict],
    ) -> None:
        """Phase 25 / DQ-06 — write ``PipelineRun.stats`` JSONB + dual-write scalars.

        Per CONTEXT D-07 (LOCKED): writes the structured ``stats`` JSONB
        column AND continues to populate the legacy scalar columns
        (``symbols_total``/``symbols_success``/``symbols_failed``) through
        v1.5 for back-compat with ``automation_service`` and the health
        probes (RESEARCH §Audit List — Readers). Scalars deprecated and
        dropped in v1.6.

        ``failed_symbols`` shape: ``[{"symbol": str, "step": str, "error": str}, ...]``
        with errors pre-truncated by callers via :func:`_truncate_error`
        (T-25-04-01 mitigation — bounded message, no traceback).

        The stats dict is funneled through :func:`sanitize_jsonb` before
        assignment as a defence-in-depth step (T-25-04-03 mitigation —
        any rogue NaN/Inf counter would otherwise hit the JSONB encoder).
        ``run.errors`` is preserved with the legacy ``{"failed_symbols": [...]}``
        shape for the rescue path lower in ``run_full`` and for any callers
        still reading the older column.
        """
        stats = sanitize_jsonb(
            {
                "succeeded": succeeded,
                "failed": failed,
                "skipped": skipped,
                "failed_symbols": failed_symbols,
            }
        )
        run.stats = stats
        # Dual-write scalars — through v1.5 (CONTEXT D-07 LOCKED).
        run.symbols_total = succeeded + failed + skipped
        run.symbols_success = succeeded
        run.symbols_failed = failed
        # Keep legacy ``errors`` populated for back-compat with the rescue
        # commit path (run_full) + any external readers still on the old
        # column. Only set it if the caller hasn't already populated it.
        if failed_symbols and run.errors is None:
            run.errors = sanitize_jsonb(
                {"failed_symbols": [fs["symbol"] for fs in failed_symbols]}
            )

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
                    # ──────────────────────────────────────────────────────
                    # crawl stage — Steps 1-7 (listings + 4 crawlers + storage)
                    # Q-3: wrap the entire crawl block in one timer so the
                    # column reflects total wall time of data ingestion.
                    # ──────────────────────────────────────────────────────
                    async with self._step_timer("crawl", run):
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

                    # ──────────────────────────────────────────────────────
                    # analyze stage — price adjustments (Q-3: only analytic
                    # work in pipeline.py today; score/report happen in
                    # AutomationService and remain placeholders).
                    # ──────────────────────────────────────────────────────
                    async with self._step_timer("analyze", run):
                        await self._apply_price_adjustments()

                    # Q-3 placeholders — explicit None so the contract is clear.
                    # Future plan will wrap AutomationService.score() and
                    # AutomationService.generate_report() with _step_timer.
                    run.score_duration_ms = None
                    run.report_duration_ms = None

                    # Update run status — Phase 25 / DQ-06 + DQ-05 dual-write path.
                    # DQ-05 (D-03) AGGREGATION CONTRACT:
                    #   The four per-step ``failed`` lists below come from
                    #   crawler / pipeline isolated loops. Analysis / scoring /
                    #   sentiment / report services maintain their OWN
                    #   per-symbol ``_failed_symbols`` buffers (drained via
                    #   ``svc.get_failed_symbols(reset=True)``) — those are
                    #   aggregated by ``AutomationService`` (caller side) which
                    #   constructs the full PipelineRun.stats payload across
                    #   stages. ``Pipeline.run_full`` itself only invokes
                    #   crawl + ``_apply_price_adjustments`` (Q-3 scope), so
                    #   the failed-symbol aggregation here is crawl-only.
                    # Each crawl-step failure becomes a ``{symbol, step, error}``
                    # entry; deduped on (symbol, step) — one symbol failing in
                    # multiple steps records once per step (CONTEXT D-03
                    # step-level granularity).
                    all_failed_items: list[dict] = []
                    seen_pairs: set[tuple[str, str]] = set()
                    failed_symbol_set: set[str] = set()
                    for step_name, step_failed in (
                        ("crawl", price_failed),
                        ("crawl", fin_failed),
                        ("crawl", company_failed),
                        ("crawl", event_failed),
                    ):
                        for sym, err in step_failed:
                            key = (sym, step_name)
                            if key in seen_pairs:
                                continue
                            seen_pairs.add(key)
                            failed_symbol_set.add(sym)
                            all_failed_items.append(
                                {
                                    "symbol": sym,
                                    "step": step_name,
                                    "error": str(err)[:MAX_ERROR_CHARS],
                                }
                            )
                    self._write_stats(
                        run,
                        succeeded=len(symbols) - len(failed_symbol_set),
                        failed=len(failed_symbol_set),
                        skipped=0,
                        failed_symbols=all_failed_items,
                    )
                    run.status = "completed"
                    run.completed_at = datetime.now(UTC)

                except Exception as e:
                    logger.exception("pipeline.run.errored")
                    run.status = "failed"
                    run.completed_at = datetime.now(UTC)
                    run.errors = sanitize_jsonb({"error": str(e)})
                    # Phase 25 / DQ-06 — leave a structured stats trail even
                    # on hard-fail so dashboards / reports never see NULL
                    # stats on a row with status="failed". `symbols` may be
                    # unbound if the exception fired before Step 2; fall
                    # back to an empty list in that case.
                    try:
                        sym_count = len(symbols)  # type: ignore[name-defined]
                    except NameError:
                        sym_count = 0
                    self._write_stats(
                        run,
                        succeeded=0,
                        failed=sym_count,
                        skipped=0,
                        failed_symbols=[
                            {
                                "symbol": "*",
                                "step": "pipeline",
                                "error": _truncate_error(e),
                            }
                        ],
                    )
                finally:
                    logger.info("pipeline.run.completed", status=run.status)

            # Defensive terminal commit — ensures status leaves "running" even if
            # the inner block raised something the inner try/except didn't catch.
            # Wrapped in try/except so a commit failure can't leave the row stuck:
            # we rollback and retry once with status='failed' on a fresh transaction.
            if run.status == "running":
                run.status = "failed"
                run.completed_at = datetime.now(UTC)
                run.errors = sanitize_jsonb(
                    {"error": "pipeline exited without setting terminal status"}
                )
            try:
                await self.session.commit()
            except Exception:
                logger.exception("pipeline.run.commit_failed")
                await self.session.rollback()
                # Best-effort rescue: open a fresh transaction just to mark the row failed
                try:
                    from sqlalchemy import update

                    await self.session.execute(
                        update(PipelineRun)
                        .where(PipelineRun.id == run.id)
                        .values(
                            status="failed",
                            completed_at=datetime.now(UTC),
                            errors=sanitize_jsonb(
                                {"error": "commit failed; status forcibly reset"}
                            ),
                        )
                    )
                    await self.session.commit()
                except Exception:
                    logger.exception("pipeline.run.rescue_commit_failed")
                    await self.session.rollback()
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
        import pandas as pd

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
                        data = sanitize_jsonb(row.to_dict())
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
                    data = sanitize_jsonb(df.to_dict(orient="records"))
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
                if df is None or (hasattr(df, "empty") and df.empty):
                    continue

                # DQ-01 (CONTEXT D-01) — Tier 1 strict partition. Bad rows
                # divert to quarantine_rows; never reach stock_prices.
                # Build a validation-shaped frame: the crawler returns
                # ``time`` (mapped to ``date`` in the schema) and lacks
                # the per-row ``symbol`` column the schema requires.
                import pandas as pd

                validation_df = df.copy()
                if (
                    "time" in validation_df.columns
                    and "date" not in validation_df.columns
                ):
                    validation_df = validation_df.rename(columns={"time": "date"})
                if (
                    "date" in validation_df.columns
                    and validation_df["date"].dtype != "datetime64[ns]"
                ):
                    validation_df["date"] = pd.to_datetime(
                        validation_df["date"], errors="coerce"
                    )
                if "symbol" not in validation_df.columns:
                    validation_df["symbol"] = symbol

                valid_df, invalid_rows, _ = partition_valid_invalid(
                    validation_df, OHLCVSchema
                )

                if invalid_rows:
                    qrepo = QuarantineRepository(self.session)
                    rule_counts: dict[str, int] = {}
                    for item in invalid_rows:
                        rule = item["rule"]
                        rule_counts[rule] = rule_counts.get(rule, 0) + 1
                        await qrepo.insert(
                            source="ohlcv",
                            symbol=symbol,
                            payload=item["row"],
                            reason=item["reason"],
                            rule=rule,
                            tier="strict",
                        )
                    # Tier 1 metric (CONTEXT D-06 — tier label always present).
                    try:
                        coll = REGISTRY._names_to_collectors.get(
                            "localstock_dq_violations_total"
                        )
                        if coll is not None:
                            for r_name, n in rule_counts.items():
                                coll.labels(rule=r_name, tier="strict").inc(n)
                    except Exception:
                        logger.debug("dq.metric.lookup_failed")
                    logger.warning(
                        "dq.tier1.quarantined",
                        symbol=symbol,
                        count=len(invalid_rows),
                        rules=sorted(rule_counts.keys()),
                    )

                # Drop quarantined indices from the original frame (which
                # still has the ``time`` column upsert_prices expects).
                bad_indices = set(df.index) - set(valid_df.index)
                if bad_indices:
                    df = df.drop(index=list(bad_indices), errors="ignore")
                if df.empty:
                    continue

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
