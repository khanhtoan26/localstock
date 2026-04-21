"""FastAPI application setup."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from localstock.api.routes.analysis import router as analysis_router
from localstock.api.routes.automation import router as automation_router
from localstock.api.routes.dashboard import router as dashboard_router
from localstock.api.routes.health import router as health_router
from localstock.api.routes.macro import router as macro_router
from localstock.api.routes.news import router as news_router
from localstock.api.routes.prices import router as prices_router
from localstock.api.routes.reports import router as reports_router
from localstock.api.routes.scores import router as scores_router
from localstock.scheduler.scheduler import get_lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with all routes and scheduler lifespan.
    """
    app = FastAPI(
        title="LocalStock API",
        description="AI Stock Agent for Vietnamese Market (HOSE)",
        version="0.1.0",
        lifespan=get_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Ensure unhandled exceptions return JSON with CORS headers."""
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    app.include_router(health_router, tags=["health"])
    app.include_router(analysis_router, tags=["analysis"])
    app.include_router(news_router, tags=["news"])
    app.include_router(scores_router, tags=["scores"])
    app.include_router(reports_router, tags=["reports"])
    app.include_router(macro_router, tags=["macro"])
    app.include_router(automation_router, tags=["automation"])
    app.include_router(prices_router, tags=["prices"])
    app.include_router(dashboard_router, tags=["dashboard"])
    return app


app = create_app()
