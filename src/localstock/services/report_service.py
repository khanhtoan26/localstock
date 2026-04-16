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
from localstock.db.repositories.stock_repo import StockRepository
from localstock.macro.crawler import MacroCrawler
from localstock.reports.generator import ReportDataBuilder, build_report_prompt
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
        self.sentiment_service = SentimentService(session)
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
                )
                prompt = build_report_prompt(data)

                # Generate report via LLM
                report = await self.ollama.generate_report(prompt, symbol)

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
                logger.info(f"Generated report for {symbol}: {mapped_rec}")

            except Exception as e:
                summary["reports_failed"] += 1
                summary["errors"].append(f"report:{symbol}:{e}")
                logger.warning(f"Report generation failed for {symbol}: {e}")

        summary["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(
            f"Report generation complete: "
            f"generated={summary['reports_generated']}, "
            f"failed={summary['reports_failed']}"
        )
        return summary

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
