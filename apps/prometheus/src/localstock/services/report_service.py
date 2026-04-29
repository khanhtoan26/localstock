"""Report service — orchestrates AI report generation for top-ranked stocks.

Pipeline:
1. Health check Ollama (skip if down)
2. Get top-ranked stocks from composite scores
3. Get macro context (shared across all stocks)
4. For each stock: gather data → T+3 prediction → build prompt → generate report → store
"""

from datetime import UTC, date, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.ai.client import OllamaClient
from localstock.config import get_settings
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.industry_repo import IndustryRepository
from localstock.db.repositories.macro_repo import MacroRepository
from localstock.db.repositories.price_repo import PriceRepository
from localstock.db.repositories.ratio_repo import RatioRepository
from localstock.db.repositories.report_repo import ReportRepository
from localstock.db.repositories.score_repo import ScoreRepository
from localstock.db.repositories.sector_repo import SectorSnapshotRepository
from localstock.db.repositories.stock_repo import StockRepository
from localstock.macro.crawler import MacroCrawler
from localstock.analysis.signals import compute_sector_momentum
from localstock.analysis.technical import TechnicalAnalyzer
from localstock.db.repositories.sentiment_repo import SentimentRepository
from localstock.reports.generator import (
    ReportDataBuilder,
    build_report_prompt,
    _normalize_risk_rating,
    _validate_price_levels,
    compute_entry_zone,
    compute_stop_loss,
    compute_target_price,
    detect_signal_conflict,
    enforce_price_ordering,
)
from localstock.reports.t3 import predict_3day_trend
from localstock.services.sentiment_service import SentimentService

# Map Vietnamese recommendation to DB enum
RECOMMENDATION_MAP = {
    "Mua mạnh": "strong_buy",
    "Mua": "buy",
    "Nắm giữ": "hold",
    "Bán": "sell",
    "Bán mạnh": "strong_sell",
}


class ReportService:
    """Orchestrates AI report generation for top-ranked stocks.

    Follows session-based service pattern from ScoringService.
    Gathers all 4 analysis dimensions + macro + T+3 data per stock,
    then generates Vietnamese AI reports via local Ollama LLM.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.score_repo = ScoreRepository(session)
        self.report_repo = ReportRepository(session)
        self.macro_repo = MacroRepository(session)
        self.indicator_repo = IndicatorRepository(session)
        self.ratio_repo = RatioRepository(session)
        self.industry_repo = IndustryRepository(session)
        self.stock_repo = StockRepository(session)
        self.price_repo = PriceRepository(session)
        self.sector_repo = SectorSnapshotRepository(session)
        self.sentiment_service = SentimentService(session)
        self.sentiment_repo = SentimentRepository(session)
        self.ollama = OllamaClient()

    async def run_full(self, top_n: int = 20) -> dict:
        """Generate AI reports for top-ranked stocks.

        Pipeline:
        a. Health check Ollama — if down, return early.
        b. Get top-ranked stocks from composite scores.
        c. Get macro context once (shared across all stocks).
        d. For each stock (with per-stock error isolation):
           - Gather technical, fundamental, sentiment, stock info data
           - Compute T+3 prediction
           - Build prompt and generate LLM report
           - Store report in DB

        Args:
            top_n: Number of top-ranked stocks to generate reports for.

        Returns:
            Summary dict with reports_generated, reports_failed, errors.
        """
        settings = get_settings()
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "reports_generated": 0,
            "reports_failed": 0,
            "errors": [],
        }

        # Step 1: Health check Ollama
        is_healthy = await self.ollama.health_check()
        if not is_healthy:
            logger.warning("Ollama not available — skipping report generation")
            summary["errors"].append("Ollama not available")
            return summary

        # Step 2: Get top-ranked stocks
        scores = await self.score_repo.get_top_ranked(limit=top_n)
        if not scores:
            logger.info("No scored stocks — skipping report generation")
            summary["errors"].append("No scored stocks available")
            return summary

        # Step 3: Get macro context once (shared across all stocks)
        macro_indicators = await self.macro_repo.get_all_latest()
        crawler = MacroCrawler()
        macro_conditions = await crawler.determine_macro_conditions(macro_indicators)

        # Build macro_data dict for prompt
        macro_data = {
            "conditions": ", ".join(
                f"{k}: {v}" for k, v in macro_conditions.items()
            ) if macro_conditions else None,
        }

        today = date.today()

        # Pre-compute previous date scores for catalyst delta (shared across stocks)
        prev_date, prev_scores = await self.score_repo.get_previous_date_scores(today)
        prev_score_map = {s.symbol: s.total_score for s in prev_scores} if prev_scores else {}

        # Step 4: For each scored stock, generate report
        for score in scores:
            symbol = score.symbol
            try:
                # Get technical indicator
                indicator = await self.indicator_repo.get_latest(symbol)
                indicator_data = {}
                if indicator:
                    indicator_data = {
                        col.name: getattr(indicator, col.name)
                        for col in indicator.__table__.columns
                        if col.name not in ("id", "computed_at")
                    }

                # Get latest close price for T+3 support/resistance context
                latest_price = await self.price_repo.get_latest(symbol)
                if latest_price:
                    indicator_data["close"] = latest_price.close

                # Get financial ratio
                ratio = await self.ratio_repo.get_latest(symbol)
                ratio_data = {}
                if ratio:
                    ratio_data = {
                        col.name: getattr(ratio, col.name)
                        for col in ratio.__table__.columns
                        if col.name not in ("id", "computed_at")
                    }

                # Get sentiment data
                sent_avg = await self.sentiment_service.get_aggregated_sentiment(
                    symbol, days=settings.sentiment_lookback_days
                )
                sentiment_data = {}
                if sent_avg is not None:
                    sentiment_label = (
                        "tích cực" if sent_avg > 0.6
                        else "tiêu cực" if sent_avg < 0.4
                        else "trung lập"
                    )
                    sentiment_data = {
                        "summary": f"Điểm sentiment: {sent_avg:.2f} ({sentiment_label})",
                    }

                # Get stock info
                stock = await self.stock_repo.get_by_symbol(symbol)
                stock_info = {}
                if stock:
                    stock_info = {
                        "company_name": stock.name,
                        "industry": stock.industry_icb3,
                        "close_price": latest_price.close if latest_price else None,
                    }

                # Compute Phase 18 signals for prompt injection
                signals_data = {}
                prices = await self.price_repo.get_prices(symbol)
                if prices:
                    import pandas as pd
                    ohlcv_df = pd.DataFrame([{
                        "open": p.open, "high": p.high, "low": p.low,
                        "close": p.close, "volume": p.volume,
                    } for p in prices[-60:]])
                    analyzer = TechnicalAnalyzer()
                    signals_data["candlestick_patterns"] = analyzer.compute_candlestick_patterns(ohlcv_df)
                    signals_data["volume_divergence"] = analyzer.compute_volume_divergence(ohlcv_df)

                # Sector momentum
                sector_data_for_signal = None
                if stock and stock.industry_icb3:
                    sector_snapshot = await self.sector_repo.get_latest(stock.industry_icb3)
                    if sector_snapshot:
                        sector_data_for_signal = {
                            "avg_score_change": sector_snapshot.avg_score_change,
                            "avg_score": sector_snapshot.avg_score,
                            "group_code": sector_snapshot.group_code,
                        }
                signals_data["sector_momentum"] = compute_sector_momentum(sector_data_for_signal)

                # Phase 20: Pre-compute price levels (per D-01, D-07)
                current_close = latest_price.close if latest_price else None
                price_history_count = len(prices) if prices else 0

                entry_lower, entry_upper = compute_entry_zone(
                    nearest_support=indicator_data.get("nearest_support"),
                    bb_upper=indicator_data.get("bb_upper"),
                    close=current_close,
                    price_history_count=price_history_count,
                )
                sl = compute_stop_loss(
                    support_2=indicator_data.get("support_2"),
                    close=current_close,
                )
                tp = compute_target_price(
                    nearest_resistance=indicator_data.get("nearest_resistance"),
                    close=current_close,
                )
                price_levels = {
                    "entry_lower": entry_lower,
                    "entry_upper": entry_upper,
                    "stop_loss": sl,
                    "target_price": tp,
                }

                # Score data for prompt
                score_data = {
                    "total": score.total_score,
                    "grade": score.grade,
                    "technical": score.technical_score,
                    "fundamental": score.fundamental_score,
                    "sentiment": score.sentiment_score,
                    "macro": score.macro_score,
                }

                # Compute T+3 prediction
                t3_data = predict_3day_trend(indicator_data)

                # Phase 20: Signal conflict detection (per D-10, D-11)
                conflict_text = detect_signal_conflict(
                    tech_score=score.technical_score,
                    fund_score=score.fundamental_score,
                )
                conflict_data = {"conflict_text": conflict_text} if conflict_text else {}

                # Phase 20: Catalyst data (per D-13, D-14)
                catalyst_data: dict = {}
                prev_total = prev_score_map.get(symbol)
                if prev_total is not None:
                    delta = score.total_score - prev_total
                    sign = "+" if delta >= 0 else ""
                    catalyst_data["score_delta_text"] = f"{sign}{delta:.1f} điểm so với phiên trước"
                else:
                    catalyst_data["score_delta_text"] = "Chưa có dữ liệu so sánh"

                sentiment_scores = await self.sentiment_repo.get_by_symbol(symbol, days=7, limit=5)
                if sentiment_scores:
                    article_ids = [s.article_id for s in sentiment_scores]
                    from sqlalchemy import select as sa_select
                    from localstock.db.models import NewsArticle
                    stmt = sa_select(NewsArticle.title).where(NewsArticle.id.in_(article_ids)).limit(5)
                    result = await self.session.execute(stmt)
                    titles = [row[0] for row in result.all()]
                    if titles:
                        catalyst_data["news_summary"] = " | ".join(titles[:3])

                # Build prompt
                data = ReportDataBuilder().build(
                    symbol=symbol,
                    score_data=score_data,
                    indicator_data=indicator_data,
                    ratio_data=ratio_data,
                    sentiment_data=sentiment_data,
                    macro_data=macro_data,
                    t3_data=t3_data,
                    stock_info=stock_info,
                    signals_data=signals_data,
                    price_levels=price_levels,
                    conflict_data=conflict_data,
                    catalyst_data=catalyst_data,
                )
                prompt = build_report_prompt(data)

                # Generate report via LLM
                report = await self.ollama.generate_report(prompt, symbol)

                # Inject pre-computed prices into report (per D-01, D-07)
                if entry_lower is not None and entry_upper is not None:
                    report.entry_price = round((entry_lower + entry_upper) / 2, 1)
                if sl is not None:
                    report.stop_loss = sl
                if tp is not None:
                    report.target_price = tp

                # Enforce strict ordering on deterministic prices BEFORE
                # validation — the three compute_* helpers are independent and
                # may produce ties after rounding (e.g. ep=sl=27.5 for HPG)
                # which would otherwise cause _validate_price_levels to null
                # all three prices and silently hide the Trade Plan section.
                enforce_price_ordering(report)

                # Post-generation validation (PROMPT-04)
                if current_close:
                    report = _validate_price_levels(report, current_close)
                report = _normalize_risk_rating(report)

                # Map recommendation to DB enum
                mapped_rec = RECOMMENDATION_MAP.get(
                    report.recommendation, "hold"
                )

                # Store report
                await self.report_repo.upsert({
                    "symbol": symbol,
                    "date": today,
                    "report_type": "full",
                    "content_json": report.model_dump(),
                    "summary": report.summary,
                    "recommendation": mapped_rec,
                    "t3_prediction": t3_data["direction"],
                    "model_used": self.ollama.model,
                    "total_score": score.total_score,
                    "grade": score.grade,
                    "generated_at": datetime.now(UTC),
                })

                summary["reports_generated"] += 1
                logger.info("report.generated", symbol=symbol, recommendation=mapped_rec)

            except Exception as e:
                summary["reports_failed"] += 1
                summary["errors"].append(f"report:{symbol}:{e}")
                logger.warning("report.generation_failed", symbol=symbol, error=str(e))

        summary["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(
            f"Report generation complete: "
            f"generated={summary['reports_generated']}, "
            f"failed={summary['reports_failed']}"
        )
        return summary

    async def generate_for_symbol(self, symbol: str) -> dict:
        """Generate AI report for a single specific symbol.

        Unlike run_full (which targets top-ranked stocks), this generates
        a report for any given symbol regardless of rank.

        Args:
            symbol: Stock ticker symbol (e.g., 'VNM').

        Returns:
            Dict with 'status', 'symbol', and optional 'error'.
        """
        settings = get_settings()

        is_healthy = await self.ollama.health_check()
        if not is_healthy:
            return {"status": "failed", "symbol": symbol, "error": "Ollama not available"}

        try:
            score = await self.score_repo.get_latest(symbol)
            score_data = {}
            if score:
                score_data = {
                    "total": score.total_score,
                    "grade": score.grade,
                    "technical": score.technical_score,
                    "fundamental": score.fundamental_score,
                    "sentiment": score.sentiment_score,
                    "macro": score.macro_score,
                }

            macro_indicators = await self.macro_repo.get_all_latest()
            crawler = MacroCrawler()
            macro_conditions = await crawler.determine_macro_conditions(macro_indicators)
            macro_data = {
                "conditions": ", ".join(
                    f"{k}: {v}" for k, v in macro_conditions.items()
                ) if macro_conditions else None,
            }

            indicator = await self.indicator_repo.get_latest(symbol)
            indicator_data = {}
            if indicator:
                indicator_data = {
                    col.name: getattr(indicator, col.name)
                    for col in indicator.__table__.columns
                    if col.name not in ("id", "computed_at")
                }

            latest_price = await self.price_repo.get_latest(symbol)
            if latest_price:
                indicator_data["close"] = latest_price.close

            ratio = await self.ratio_repo.get_latest(symbol)
            ratio_data = {}
            if ratio:
                ratio_data = {
                    col.name: getattr(ratio, col.name)
                    for col in ratio.__table__.columns
                    if col.name not in ("id", "computed_at")
                }

            sent_avg = await self.sentiment_service.get_aggregated_sentiment(
                symbol, days=settings.sentiment_lookback_days
            )
            sentiment_data = {}
            if sent_avg is not None:
                sentiment_label = (
                    "tích cực" if sent_avg > 0.6
                    else "tiêu cực" if sent_avg < 0.4
                    else "trung lập"
                )
                sentiment_data = {
                    "summary": f"Điểm sentiment: {sent_avg:.2f} ({sentiment_label})",
                }

            stock = await self.stock_repo.get_by_symbol(symbol)
            stock_info = {}
            if stock:
                stock_info = {
                    "company_name": stock.name,
                    "industry": stock.industry_icb3,
                    "close_price": latest_price.close if latest_price else None,
                }

            # Compute Phase 18 signals for prompt injection
            signals_data = {}
            prices = await self.price_repo.get_prices(symbol)
            if prices:
                import pandas as pd
                ohlcv_df = pd.DataFrame([{
                    "open": p.open, "high": p.high, "low": p.low,
                    "close": p.close, "volume": p.volume,
                } for p in prices[-60:]])
                analyzer = TechnicalAnalyzer()
                signals_data["candlestick_patterns"] = analyzer.compute_candlestick_patterns(ohlcv_df)
                signals_data["volume_divergence"] = analyzer.compute_volume_divergence(ohlcv_df)

            # Sector momentum
            sector_data_for_signal = None
            if stock and stock.industry_icb3:
                sector_snapshot = await self.sector_repo.get_latest(stock.industry_icb3)
                if sector_snapshot:
                    sector_data_for_signal = {
                        "avg_score_change": sector_snapshot.avg_score_change,
                        "avg_score": sector_snapshot.avg_score,
                        "group_code": sector_snapshot.group_code,
                    }
            signals_data["sector_momentum"] = compute_sector_momentum(sector_data_for_signal)

            # Phase 20: Pre-compute price levels (per D-01, D-07)
            current_close = latest_price.close if latest_price else None
            price_history_count = len(prices) if prices else 0

            entry_lower, entry_upper = compute_entry_zone(
                nearest_support=indicator_data.get("nearest_support"),
                bb_upper=indicator_data.get("bb_upper"),
                close=current_close,
                price_history_count=price_history_count,
            )
            sl = compute_stop_loss(
                support_2=indicator_data.get("support_2"),
                close=current_close,
            )
            tp = compute_target_price(
                nearest_resistance=indicator_data.get("nearest_resistance"),
                close=current_close,
            )
            price_levels = {
                "entry_lower": entry_lower,
                "entry_upper": entry_upper,
                "stop_loss": sl,
                "target_price": tp,
            }

            t3_data = predict_3day_trend(indicator_data)

            # Phase 20: Signal conflict detection (per D-10, D-11)
            conflict_data: dict = {}
            if score:
                conflict_text = detect_signal_conflict(
                    tech_score=score.technical_score,
                    fund_score=score.fundamental_score,
                )
                conflict_data = {"conflict_text": conflict_text} if conflict_text else {}

            # Phase 20: Catalyst data (per D-13, D-14)
            catalyst_data: dict = {}
            prev_date, prev_scores = await self.score_repo.get_previous_date_scores(date.today())
            prev_score_map = {s.symbol: s.total_score for s in prev_scores} if prev_scores else {}
            prev_total = prev_score_map.get(symbol)
            if prev_total is not None and score:
                delta = score.total_score - prev_total
                sign = "+" if delta >= 0 else ""
                catalyst_data["score_delta_text"] = f"{sign}{delta:.1f} điểm so với phiên trước"
            else:
                catalyst_data["score_delta_text"] = "Chưa có dữ liệu so sánh"

            sentiment_scores = await self.sentiment_repo.get_by_symbol(symbol, days=7, limit=5)
            if sentiment_scores:
                article_ids = [s.article_id for s in sentiment_scores]
                from sqlalchemy import select as sa_select
                from localstock.db.models import NewsArticle
                stmt = sa_select(NewsArticle.title).where(NewsArticle.id.in_(article_ids)).limit(5)
                result = await self.session.execute(stmt)
                titles = [row[0] for row in result.all()]
                if titles:
                    catalyst_data["news_summary"] = " | ".join(titles[:3])

            data = ReportDataBuilder().build(
                symbol=symbol,
                score_data=score_data,
                indicator_data=indicator_data,
                ratio_data=ratio_data,
                sentiment_data=sentiment_data,
                macro_data=macro_data,
                t3_data=t3_data,
                stock_info=stock_info,
                signals_data=signals_data,
                price_levels=price_levels,
                conflict_data=conflict_data,
                catalyst_data=catalyst_data,
            )
            prompt = build_report_prompt(data)
            report = await self.ollama.generate_report(prompt, symbol)

            # Inject pre-computed prices into report (per D-01, D-07)
            if entry_lower is not None and entry_upper is not None:
                report.entry_price = round((entry_lower + entry_upper) / 2, 1)
            if sl is not None:
                report.stop_loss = sl
            if tp is not None:
                report.target_price = tp

            # Enforce strict ordering on deterministic prices BEFORE
            # validation — see run_full() for rationale.
            enforce_price_ordering(report)

            # Post-generation validation (PROMPT-04)
            if current_close:
                report = _validate_price_levels(report, current_close)
            report = _normalize_risk_rating(report)

            mapped_rec = RECOMMENDATION_MAP.get(report.recommendation, "hold")

            today = date.today()
            await self.report_repo.upsert({
                "symbol": symbol,
                "date": today,
                "report_type": "full",
                "content_json": report.model_dump(),
                "summary": report.summary,
                "recommendation": mapped_rec,
                "t3_prediction": t3_data["direction"],
                "model_used": self.ollama.model,
                "total_score": score.total_score if score else 0.0,
                "grade": score.grade if score else "N/A",
                "generated_at": datetime.now(UTC),
            })

            logger.info("report.generated", symbol=symbol, recommendation=mapped_rec)
            return {"status": "completed", "symbol": symbol, "recommendation": mapped_rec}

        except Exception as e:
            logger.warning("report.generation_failed", symbol=symbol, error=str(e))
            return {"status": "failed", "symbol": symbol, "error": str(e)}

    async def get_reports(self, limit: int = 20) -> list[dict]:
        """Get latest generated reports.

        Returns list of flat dicts with key report fields.

        Args:
            limit: Maximum number of reports to return.

        Returns:
            List of report summary dicts.
        """
        today = date.today()
        reports = await self.report_repo.get_by_date(today)
        if not reports:
            # Try most recent date with reports
            latest = await self.report_repo.get_most_recent()
            if latest:
                reports = await self.report_repo.get_by_date(latest.date)

        if not reports:
            return []

        return [
            {
                "symbol": r.symbol,
                "date": str(r.date),
                "summary": r.summary,
                "recommendation": r.recommendation,
                "t3_prediction": r.t3_prediction,
                "total_score": round(r.total_score, 1),
                "grade": r.grade,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            }
            for r in reports[:limit]
        ]

    async def get_report(self, symbol: str) -> dict | None:
        """Get latest report for a specific stock.

        Returns full report content_json plus metadata.

        Args:
            symbol: Stock ticker symbol (e.g., 'VNM').

        Returns:
            Full report dict with content_json and metadata, or None.
        """
        report = await self.report_repo.get_latest(symbol)
        if not report:
            return None

        return {
            "symbol": report.symbol,
            "date": str(report.date),
            "content_json": report.content_json,
            "summary": report.summary,
            "recommendation": report.recommendation,
            "t3_prediction": report.t3_prediction,
            "total_score": round(report.total_score, 1),
            "grade": report.grade,
            "model_used": report.model_used,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        }
