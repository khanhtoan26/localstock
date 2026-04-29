"""Automation service — orchestrates full daily pipeline with notifications (AUTO-01, AUTO-02).

Runs the 6-step pipeline (crawl→analyze→news→sentiment→score→report),
then detects score changes (SCOR-04), computes sector rotation (SCOR-05),
and sends Telegram notifications (NOTI-01, NOTI-02).

Per D-02: Checks is_trading_day before running on scheduled invocation.
Per Pitfall 2: Checks NotificationRepository.was_sent_today before sending.
Per Pitfall 5: Score changes skip when no previous scoring date exists.
"""

import asyncio
from datetime import UTC, date, datetime

from loguru import logger

from localstock.cache import invalidate_namespace
from localstock.cache.prewarm import prewarm_hot_keys
from localstock.config import get_settings
from localstock.db.database import get_session_factory
from localstock.db.repositories.notification_repo import NotificationRepository
from localstock.notifications.formatters import (
    format_daily_digest,
    format_score_alerts,
    format_sector_rotation,
)
from localstock.notifications.telegram import TelegramNotifier
from localstock.scheduler.calendar import is_trading_day
from localstock.services.analysis_service import AnalysisService
from localstock.services.news_service import NewsService
from localstock.services.pipeline import Pipeline
from localstock.services.report_service import ReportService
from localstock.services.score_change_service import detect_score_changes
from localstock.services.scoring_service import ScoringService
from localstock.services.sector_service import SectorService
from localstock.services.sentiment_service import SentimentService


# Process-level lock to prevent concurrent pipeline runs (per Research Q3)
_pipeline_lock = asyncio.Lock()


class AutomationService:
    """Orchestrates the full daily pipeline with notification delivery."""

    def __init__(self):
        self.session_factory = get_session_factory()
        self.notifier = TelegramNotifier()

    async def run_daily_pipeline(self, force: bool = False) -> dict:
        """Execute full pipeline and send notifications.

        Args:
            force: If True, skip trading day check (for on-demand runs).

        Returns:
            Summary dict with status, pipeline results, changes, rotation.
        """
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "status": "completed",
            "steps": {},
            "score_changes": [],
            "sector_rotation": {},
            "notifications": {"digest": False, "alerts": False},
        }

        # Check trading day (skip for forced/on-demand runs)
        if not force and not is_trading_day():
            logger.info("Non-trading day — skipping pipeline")
            summary["status"] = "skipped"
            summary["reason"] = "non_trading_day"
            return summary

        if _pipeline_lock.locked():
            logger.warning("Pipeline already running — skipping")
            summary["status"] = "skipped"
            summary["reason"] = "already_running"
            return summary

        async with _pipeline_lock:
            # Step 1: Crawl market data
            try:
                async with self.session_factory() as session:
                    pipeline = Pipeline(session)
                    crawl_result = await pipeline.run_full(run_type="daily")
                    summary["steps"]["crawl"] = {
                        "success": crawl_result.symbols_success,
                        "total": crawl_result.symbols_total,
                    }
                    logger.info(
                        "automation.step.completed",
                        step=1,
                        step_name="crawl",
                        success=crawl_result.symbols_success,
                        total=crawl_result.symbols_total,
                    )
            except Exception as e:
                summary["steps"]["crawl"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=1, step_name="crawl")

            # Step 2: Analysis
            try:
                async with self.session_factory() as session:
                    analysis = AnalysisService(session)
                    anal_result = await analysis.run_full()
                    summary["steps"]["analysis"] = anal_result
                    logger.info("Step 2/6: Analysis complete")
                    # Phase 26 / CACHE-03 (D-04) — eager invalidation of
                    # cached indicators after a successful analysis pass.
                    try:
                        invalidate_namespace("indicators")
                    except Exception:
                        logger.exception(
                            "automation.cache.invalidate_failed",
                            phase="analysis",
                        )
            except Exception as e:
                summary["steps"]["analysis"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=2, step_name="analysis")

            # Step 3: News crawl
            try:
                async with self.session_factory() as session:
                    news = NewsService(session)
                    news_result = await news.crawl_and_store()
                    summary["steps"]["news"] = news_result
                    logger.info("Step 3/6: News crawl complete")
            except Exception as e:
                summary["steps"]["news"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=3, step_name="news")

            # Step 4: Sentiment analysis
            try:
                async with self.session_factory() as session:
                    sentiment = SentimentService(session)
                    sent_result = await sentiment.run_full()
                    summary["steps"]["sentiment"] = sent_result
                    logger.info("Step 4/6: Sentiment analysis complete")
            except Exception as e:
                summary["steps"]["sentiment"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=4, step_name="sentiment")

            # Step 5: Scoring
            try:
                async with self.session_factory() as session:
                    scoring = ScoringService(session)
                    score_result = await scoring.run_full()
                    summary["steps"]["scoring"] = score_result
                    logger.info("Step 5/6: Scoring complete")
                    # Phase 26 / CACHE-03 (D-04) — eager invalidation of
                    # ranking + per-symbol score caches after scoring run.
                    try:
                        invalidate_namespace("scores:ranking")
                        invalidate_namespace("scores:symbol")
                    except Exception:
                        logger.exception(
                            "automation.cache.invalidate_failed",
                            phase="scoring",
                        )
            except Exception as e:
                summary["steps"]["scoring"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=5, step_name="scoring")

            # Step 6: Report generation
            settings = get_settings()
            try:
                async with self.session_factory() as session:
                    reports = ReportService(session)
                    report_result = await reports.run_full(top_n=settings.report_top_n)
                    summary["steps"]["reports"] = report_result
                    logger.info("Step 6/6: Reports complete")
            except Exception as e:
                summary["steps"]["reports"] = {"error": str(e)}
                logger.exception("automation.step.failed", step=6, step_name="reports")

            # Post-pipeline: Score change detection (SCOR-04)
            try:
                async with self.session_factory() as session:
                    changes = await detect_score_changes(session)
                    summary["score_changes"] = changes
                    logger.info("automation.score_changes.detected", count=len(changes))
            except Exception:
                logger.exception("automation.score_changes.failed")

            # Post-pipeline: Sector rotation (SCOR-05)
            try:
                async with self.session_factory() as session:
                    sector = SectorService(session)
                    await sector.compute_snapshot()
                    rotation = await sector.get_rotation_summary()
                    summary["sector_rotation"] = rotation
                    logger.info("Sector rotation computed")
                    # Phase 26 / CACHE-03 (D-04) — eager invalidation of
                    # market-summary + version-key caches after rotation.
                    try:
                        invalidate_namespace("market:summary")
                        invalidate_namespace("pipeline:latest_run_id")
                    except Exception:
                        logger.exception(
                            "automation.cache.invalidate_failed",
                            phase="sector_rotation",
                        )
            except Exception:
                logger.exception("automation.sector_rotation.failed")

            # Phase 26 / CACHE-05 (D-05) — pre-warm hot read keys so the
            # first user request after a successful pipeline run logs
            # `cache=hit` (closes ROADMAP SC #4). Best-effort: errors are
            # logged + counted via cache_prewarm_errors_total but NEVER
            # propagate (P-5).
            try:
                await prewarm_hot_keys(self.session_factory)
            except Exception:
                logger.exception("automation.cache.prewarm_failed")

            # Send notifications
            await self._send_notifications(summary)

        summary["completed_at"] = datetime.now(UTC).isoformat()
        return summary

    async def _send_notifications(self, summary: dict) -> None:
        """Send Telegram notifications based on pipeline results.

        Per Pitfall 2: Check was_sent_today before sending to prevent duplicates.
        """
        if not self.notifier.is_configured:
            logger.debug("Telegram not configured — skipping notifications")
            return

        today = date.today()

        # Check dedup
        async with self.session_factory() as session:
            notif_repo = NotificationRepository(session)

            # Daily digest (NOTI-01)
            if not await notif_repo.was_sent_today("daily_digest", today):
                try:
                    # Get top stocks for digest
                    async with self.session_factory() as score_session:
                        scoring = ScoringService(score_session)
                        top_stocks = await scoring.get_top_stocks(limit=10)

                    msg = format_daily_digest(
                        top_stocks=top_stocks,
                        score_changes=summary.get("score_changes"),
                        rotation=summary.get("sector_rotation"),
                        digest_date=today,
                    )
                    sent = await self.notifier.send_message(msg)
                    await notif_repo.log_notification(
                        today, "daily_digest",
                        "sent" if sent else "failed",
                        {"top_count": len(top_stocks)},
                    )
                    summary["notifications"]["digest"] = sent
                    logger.info("notification.daily_digest.sent" if sent else "notification.daily_digest.failed", sent=sent)
                except Exception as e:
                    logger.exception("notification.daily_digest.error")
                    await notif_repo.log_notification(today, "daily_digest", "failed", {"error": str(e)})

            # Score change alerts (NOTI-02)
            changes = summary.get("score_changes", [])
            if changes and not await notif_repo.was_sent_today("score_alert", today):
                try:
                    msg = format_score_alerts(changes, alert_date=today)
                    sent = await self.notifier.send_message(msg)
                    await notif_repo.log_notification(
                        today, "score_alert",
                        "sent" if sent else "failed",
                        {"changes_count": len(changes)},
                    )
                    summary["notifications"]["alerts"] = sent
                    logger.info("notification.score_alert.sent" if sent else "notification.score_alert.failed", sent=sent)
                except Exception as e:
                    logger.exception("notification.score_alert.error")
                    await notif_repo.log_notification(today, "score_alert", "failed", {"error": str(e)})

    async def run_on_demand(self, symbol: str | None = None) -> dict:
        """Run on-demand analysis (AUTO-02).

        Args:
            symbol: If provided, analyze single stock. Otherwise, full pipeline.

        Returns:
            Summary dict with results.
        """
        if symbol:
            return await self._run_single_symbol(symbol)
        else:
            return await self.run_daily_pipeline(force=True)

    async def _run_single_symbol(self, symbol: str) -> dict:
        """Run analysis for a single symbol."""
        summary = {"symbol": symbol, "status": "completed", "steps": {}}

        try:
            async with self.session_factory() as session:
                pipeline = Pipeline(session)
                crawl = await pipeline.run_single(symbol)
                summary["steps"]["crawl"] = crawl
        except Exception as e:
            summary["steps"]["crawl"] = {"error": str(e)}

        try:
            async with self.session_factory() as session:
                analysis = AnalysisService(session)
                result = await analysis.run_full()
                summary["steps"]["analysis"] = result
        except Exception as e:
            summary["steps"]["analysis"] = {"error": str(e)}

        try:
            async with self.session_factory() as session:
                scoring = ScoringService(session)
                result = await scoring.run_full()
                summary["steps"]["scoring"] = result
        except Exception as e:
            summary["steps"]["scoring"] = {"error": str(e)}

        summary["completed_at"] = datetime.now(UTC).isoformat()
        return summary
