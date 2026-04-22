"""Scoring service — orchestrates composite score computation for all stocks.

Pipeline:
1. For each stock: normalize technical + fundamental + sentiment scores
2. Compute composite weighted score with missing dimension handling
3. Assign ranks
4. Store via ScoreRepository
"""

from datetime import UTC, date, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.config import get_settings
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.industry_repo import IndustryRepository
from localstock.db.repositories.macro_repo import MacroRepository
from localstock.db.repositories.ratio_repo import RatioRepository
from localstock.db.repositories.report_repo import ReportRepository
from localstock.db.repositories.score_repo import ScoreRepository
from localstock.db.repositories.stock_repo import StockRepository
from localstock.macro.crawler import MacroCrawler
from localstock.macro.scorer import normalize_macro_score
from localstock.scoring.config import ScoringConfig
from localstock.scoring.engine import compute_composite
from localstock.scoring.normalizer import (
    normalize_fundamental_score,
    normalize_sentiment_score,
    normalize_technical_score,
)
from localstock.services.sentiment_service import SentimentService


class ScoringService:
    """Orchestrates composite scoring for all HOSE stocks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)
        self.indicator_repo = IndicatorRepository(session)
        self.ratio_repo = RatioRepository(session)
        self.score_repo = ScoreRepository(session)
        self.sentiment_service = SentimentService(session)
        self.macro_repo = MacroRepository(session)
        self.industry_repo = IndustryRepository(session)
        self.config = ScoringConfig.from_settings()

    async def run_full(self, symbols: list[str] | None = None) -> dict:
        """Compute composite scores for specified or all HOSE stocks.

        Args:
            symbols: Score only these symbols. If None, scores all HOSE stocks.

        Returns:
            Summary dict with counts and errors.
        """
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "stocks_scored": 0,
            "stocks_failed": 0,
            "errors": [],
        }

        if symbols:
            target_symbols = symbols
        else:
            target_symbols = await self.stock_repo.get_all_hose_symbols()
        today = date.today()
        score_rows = []

        settings = get_settings()

        # Get current macro conditions (once for all stocks)
        macro_indicators = await self.macro_repo.get_all_latest()
        crawler = MacroCrawler()
        macro_conditions = await crawler.determine_macro_conditions(macro_indicators)

        for symbol in target_symbols:
            try:
                # Get latest technical indicator
                indicator = await self.indicator_repo.get_latest(symbol)
                tech_score = None
                if indicator:
                    tech_data = {
                        col.name: getattr(indicator, col.name)
                        for col in indicator.__table__.columns
                        if col.name not in ("id", "computed_at")
                    }
                    tech_score = normalize_technical_score(tech_data)

                # Get latest fundamental ratio
                ratio = await self.ratio_repo.get_latest(symbol)
                fund_score = None
                if ratio:
                    ratio_data = {
                        col.name: getattr(ratio, col.name)
                        for col in ratio.__table__.columns
                        if col.name not in ("id", "computed_at")
                    }
                    fund_score = normalize_fundamental_score(ratio_data)

                # Get aggregated sentiment (0-1 → 0-100)
                sent_avg = await self.sentiment_service.get_aggregated_sentiment(
                    symbol, days=settings.sentiment_lookback_days
                )
                sent_score = None
                if sent_avg is not None:
                    sent_score = normalize_sentiment_score(sent_avg)

                # Macro score based on sector + current conditions
                macro_score = None
                if macro_conditions:
                    sector_code = await self.industry_repo.get_group_for_symbol(symbol)
                    macro_score = normalize_macro_score(sector_code, macro_conditions)

                # Compute composite
                total, grade, dims_used, weights = compute_composite(
                    tech=tech_score,
                    fund=fund_score,
                    sent=sent_score,
                    macro=macro_score,
                    config=self.config,
                )

                score_rows.append({
                    "symbol": symbol,
                    "date": today,
                    "technical_score": tech_score,
                    "fundamental_score": fund_score,
                    "sentiment_score": sent_score,
                    "macro_score": macro_score,
                    "total_score": total,
                    "grade": grade,
                    "dimensions_used": dims_used,
                    "weights_json": weights,
                    "computed_at": datetime.now(UTC),
                })
                summary["stocks_scored"] += 1

            except Exception as e:
                summary["stocks_failed"] += 1
                summary["errors"].append(f"score:{symbol}:{e}")
                logger.warning(f"Scoring failed for {symbol}: {e}")

        # Bulk upsert all scores
        if score_rows:
            # Sort by total_score for ranking
            score_rows.sort(key=lambda x: x["total_score"], reverse=True)
            for rank, row in enumerate(score_rows, start=1):
                row["rank"] = rank

            await self.score_repo.bulk_upsert(score_rows)

        summary["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(
            f"Scoring complete: scored={summary['stocks_scored']}, "
            f"failed={summary['stocks_failed']}"
        )
        return summary

    async def get_top_stocks(self, limit: int = 20) -> list[dict]:
        """Get top-ranked stocks with breakdown for SCOR-03.

        Returns list of dicts with symbol, total_score, grade, rank,
        per-dimension scores, weights used, and latest AI recommendation.
        """
        scores = await self.score_repo.get_top_ranked(limit=limit)
        if not scores:
            return []

        # Enrich with latest recommendation from analysis_reports
        report_repo = ReportRepository(self.session)
        symbols = [s.symbol for s in scores]
        rec_map: dict[str, str | None] = {}
        for sym in symbols:
            report = await report_repo.get_latest(sym)
            rec_map[sym] = report.recommendation if report else None

        return [
            {
                "symbol": s.symbol,
                "date": str(s.date),
                "total_score": round(s.total_score, 1),
                "grade": s.grade,
                "rank": s.rank,
                "technical_score": round(s.technical_score, 1) if s.technical_score else None,
                "fundamental_score": round(s.fundamental_score, 1) if s.fundamental_score else None,
                "sentiment_score": round(s.sentiment_score, 1) if s.sentiment_score else None,
                "macro_score": round(s.macro_score, 1) if s.macro_score else None,
                "dimensions_used": s.dimensions_used,
                "weights": s.weights_json,
                "recommendation": rec_map.get(s.symbol),
            }
            for s in scores
        ]
