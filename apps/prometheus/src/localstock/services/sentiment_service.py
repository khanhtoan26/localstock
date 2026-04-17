"""Sentiment analysis service — orchestrates LLM classification for stocks.

Pipeline:
1. Check Ollama health (skip if down — Pitfall 4)
2. Get funnel candidates (top N by preliminary tech+fund score)
3. Get unprocessed articles for those stocks
4. Run LLM sentiment classification per article-ticker pair
5. Aggregate per-ticker sentiment scores
6. Store results via SentimentRepository
"""

import asyncio
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.ai.client import OllamaClient
from localstock.analysis.sentiment import aggregate_sentiment
from localstock.config import get_settings
from localstock.crawlers.news_crawler import extract_tickers
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.news_repo import NewsRepository
from localstock.db.repositories.ratio_repo import RatioRepository
from localstock.db.repositories.sentiment_repo import SentimentRepository
from localstock.db.repositories.stock_repo import StockRepository
from localstock.scoring.normalizer import (
    normalize_fundamental_score,
    normalize_technical_score,
)


class SentimentService:
    """Orchestrates LLM sentiment analysis for stock news."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.news_repo = NewsRepository(session)
        self.sentiment_repo = SentimentRepository(session)
        self.indicator_repo = IndicatorRepository(session)
        self.ratio_repo = RatioRepository(session)
        self.stock_repo = StockRepository(session)
        self.ollama = OllamaClient()

    async def run_full(self) -> dict:
        """Run sentiment analysis for funnel-selected stocks.

        Returns:
            Summary dict with stocks_analyzed, articles_processed, errors.
        """
        settings = get_settings()
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "ollama_available": False,
            "funnel_candidates": 0,
            "articles_processed": 0,
            "sentiment_scores_stored": 0,
            "errors": [],
        }

        # Step 1: Check Ollama health
        is_healthy = await self.ollama.health_check()
        summary["ollama_available"] = is_healthy
        if not is_healthy:
            logger.warning("Ollama not available — skipping sentiment analysis")
            return summary

        # Step 2: Get funnel candidates
        candidates = await self._get_funnel_candidates(settings.funnel_top_n)
        summary["funnel_candidates"] = len(candidates)
        if not candidates:
            logger.info("No funnel candidates — skipping sentiment")
            return summary

        valid_symbols = set(candidates)

        # Step 3: Get recent articles
        articles = await self.news_repo.get_recent(
            days=settings.sentiment_lookback_days, limit=200
        )
        if not articles:
            logger.info("No recent articles — skipping sentiment")
            return summary

        # Step 4: Classify sentiment per article-ticker pair
        sentiment_rows = []
        for article in articles:
            text = f"{article.title} {article.summary or ''} {article.content or ''}"
            tickers = extract_tickers(text, valid_symbols)

            if not tickers:
                continue

            # Limit tickers per article to avoid noise (Pitfall 3)
            if len(tickers) > 3:
                tickers = tickers[:3]

            article_text = article.content or article.summary or article.title

            for symbol in tickers:
                try:
                    result = await self.ollama.classify_sentiment(
                        article_text=article_text, symbol=symbol
                    )
                    sentiment_rows.append({
                        "article_id": article.id,
                        "symbol": symbol,
                        "sentiment": result.sentiment,
                        "score": result.score,
                        "reason": result.reason,
                        "model_used": self.ollama.model,
                        "computed_at": datetime.now(UTC),
                    })
                    summary["articles_processed"] += 1
                except Exception as e:
                    summary["errors"].append(f"sentiment:{symbol}:{article.id}:{e}")
                    logger.warning(
                        f"Sentiment classification failed for {symbol} "
                        f"article {article.id}: {e}"
                    )

                # Rate limit LLM calls
                await asyncio.sleep(0.5)

        # Step 5: Store sentiment scores
        if sentiment_rows:
            count = await self.sentiment_repo.bulk_upsert(sentiment_rows)
            summary["sentiment_scores_stored"] = count

        summary["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(
            f"Sentiment analysis: processed={summary['articles_processed']}, "
            f"stored={summary['sentiment_scores_stored']}"
        )
        return summary

    async def _get_funnel_candidates(self, top_n: int) -> list[str]:
        """Get top N stocks by preliminary tech+fund score.

        Simple average of normalized technical + fundamental scores.
        """
        symbols = await self.stock_repo.get_all_hose_symbols()
        prelim_scores = {}

        for symbol in symbols:
            indicator = await self.indicator_repo.get_latest(symbol)
            ratio = await self.ratio_repo.get_latest(symbol)

            tech_score = 0.0
            fund_score = 0.0

            if indicator:
                tech_data = {
                    col.name: getattr(indicator, col.name)
                    for col in indicator.__table__.columns
                    if col.name not in ("id", "computed_at")
                }
                tech_score = normalize_technical_score(tech_data)

            if ratio:
                ratio_data = {
                    col.name: getattr(ratio, col.name)
                    for col in ratio.__table__.columns
                    if col.name not in ("id", "computed_at")
                }
                fund_score = normalize_fundamental_score(ratio_data)

            if indicator or ratio:
                count = (1 if indicator else 0) + (1 if ratio else 0)
                prelim_scores[symbol] = (tech_score + fund_score) / count

        # Sort by prelim score descending, take top N
        ranked = sorted(
            prelim_scores.items(), key=lambda x: x[1], reverse=True
        )
        return [symbol for symbol, _ in ranked[:top_n]]

    async def get_aggregated_sentiment(
        self, symbol: str, days: int = 7
    ) -> float | None:
        """Get aggregated sentiment score for a symbol.

        Returns 0.0-1.0 score or None if no sentiment data.
        """
        scores = await self.sentiment_repo.get_by_symbol(symbol, days=days)
        if not scores:
            return None

        score_dicts = [
            {"score": s.score, "computed_at": s.computed_at} for s in scores
        ]
        return aggregate_sentiment(score_dicts)
