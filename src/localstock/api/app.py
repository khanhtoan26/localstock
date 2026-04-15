"""FastAPI application setup."""

from fastapi import FastAPI

from localstock.api.routes.analysis import router as analysis_router
from localstock.api.routes.health import router as health_router
from localstock.api.routes.news import router as news_router
from localstock.api.routes.scores import router as scores_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with all routes included.
    """
    app = FastAPI(
        title="LocalStock API",
        description="AI Stock Agent for Vietnamese Market (HOSE)",
        version="0.1.0",
    )
    app.include_router(health_router, tags=["health"])
    app.include_router(analysis_router, tags=["analysis"])
    app.include_router(news_router, tags=["news"])
    app.include_router(scores_router, tags=["scores"])
    return app


app = create_app()
