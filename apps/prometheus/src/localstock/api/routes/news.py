"""API endpoints for news articles and sentiment.

Endpoints:
- GET /api/news — Recent news articles
- GET /api/news/{symbol}/sentiment — Sentiment scores for a stock
- POST /api/news/crawl — Trigger news crawl
- POST /api/sentiment/run — Trigger sentiment analysis
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.news_repo import NewsRepository
from localstock.db.repositories.sentiment_repo import SentimentRepository
from localstock.services.news_service import NewsService
from localstock.services.sentiment_service import SentimentService

router = APIRouter(prefix="/api")
_crawl_lock = asyncio.Lock()
_sentiment_lock = asyncio.Lock()


@router.get("/news")
async def get_news(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get recent news articles."""
    repo = NewsRepository(session)
    articles = await repo.get_recent(days=days, limit=limit)
    return {
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "summary": a.summary[:200] if a.summary else None,
            }
            for a in articles
        ],
        "count": len(articles),
    }


@router.get("/news/{symbol}/sentiment")
async def get_symbol_sentiment(
    symbol: str,
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    """Get sentiment scores for a specific stock symbol."""
    repo = SentimentRepository(session)
    scores = await repo.get_by_symbol(symbol.upper(), days=days)
    if not scores:
        raise HTTPException(
            status_code=404,
            detail=f"No sentiment data for {symbol}",
        )

    # Also compute aggregate
    service = SentimentService(session)
    agg = await service.get_aggregated_sentiment(symbol.upper(), days=days)

    return {
        "symbol": symbol.upper(),
        "aggregate_score": round(agg, 3) if agg is not None else None,
        "article_count": len(scores),
        "scores": [
            {
                "article_id": s.article_id,
                "sentiment": s.sentiment,
                "score": s.score,
                "reason": s.reason,
                "model_used": s.model_used,
                "computed_at": s.computed_at.isoformat(),
            }
            for s in scores
        ],
    }


@router.post("/news/crawl")
async def trigger_news_crawl(
    session: AsyncSession = Depends(get_session),
):
    """Trigger news crawl from RSS feeds."""
    if _crawl_lock.locked():
        raise HTTPException(status_code=409, detail="News crawl already in progress")
    async with _crawl_lock:
        service = NewsService(session)
        result = await service.crawl_and_store()
        return result


@router.post("/sentiment/run")
async def trigger_sentiment(
    session: AsyncSession = Depends(get_session),
):
    """Trigger LLM sentiment analysis for funnel-selected stocks.

    Requires Ollama to be running. Will skip gracefully if unavailable.
    """
    if _sentiment_lock.locked():
        raise HTTPException(status_code=409, detail="Sentiment analysis already in progress")
    async with _sentiment_lock:
        service = SentimentService(session)
        result = await service.run_full()
        return result
