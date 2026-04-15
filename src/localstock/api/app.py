"""FastAPI application setup."""

from fastapi import FastAPI

from localstock.api.routes.health import router as health_router


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
    return app


app = create_app()
