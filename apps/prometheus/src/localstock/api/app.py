"""FastAPI application setup."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_client import REGISTRY as _PROM_REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator

from localstock.api.routes.admin import router as admin_router
from localstock.api.routes.analysis import router as analysis_router
from localstock.api.routes.automation import router as automation_router
from localstock.api.routes.dashboard import router as dashboard_router
from localstock.api.routes.health import router as health_router
from localstock.api.routes.macro import router as macro_router
from localstock.api.routes.market import router as market_router
from localstock.api.routes.news import router as news_router
from localstock.api.routes.prices import router as prices_router
from localstock.api.routes.reports import router as reports_router
from localstock.api.routes.scores import router as scores_router
from localstock.observability.logging import configure_logging
from localstock.observability.metrics import init_metrics
from localstock.observability.middleware import (
    CorrelationIdMiddleware,
    RequestLogMiddleware,
)
from localstock.cache.middleware import CacheHeaderMiddleware
from localstock.scheduler.scheduler import get_lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with all routes and scheduler lifespan.
    """
    configure_logging()  # OBS-01 — must run before FastAPI emits any startup logs
    init_metrics()  # OBS-08, OBS-10 — idempotent registry init on default REGISTRY (D-04)
    app = FastAPI(
        title="LocalStock API",
        description="AI Stock Agent for Vietnamese Market (HOSE)",
        version="0.1.0",
        lifespan=get_lifespan,
    )
    # Phase 23 — Prometheus instrumentation.
    # Anchored regex (^...$) prevents accidental matches like /metrics-foo
    # (per 23-RESEARCH.md §"Common Pitfalls" Pitfall 3). /health/live is a
    # forward-compatible exclusion for Phase 25 (OBS-14) — harmless if absent.
    #
    # Idempotency guard (D-04, OBS-10): Instrumentator's __init__ registers the
    # ``http_requests_inprogress`` Gauge on the default REGISTRY, and the
    # default histogram ``http_request_duration_seconds`` is registered lazily
    # on first request. Both raise ``Duplicated timeseries`` if create_app() is
    # called more than once in the same process (e.g. integration tests). We
    # proactively unregister any prior collectors with these names so create_app()
    # is safe to call repeatedly. No-op on the first call (production path).
    for _name in (
        "http_requests_inprogress",
        "http_requests_total",
        "http_request_duration_seconds",
        "http_request_duration_highr_seconds",
        "http_request_size_bytes",
        "http_response_size_bytes",
    ):
        _existing = _PROM_REGISTRY._names_to_collectors.get(_name)
        if _existing is not None:
            _PROM_REGISTRY.unregister(_existing)

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["^/metrics$", "^/health/live$"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=False,
    )

    # Starlette middleware ordering is LIFO — LAST added is OUTERMOST.
    # Desired runtime order:
    #   CORS (outer) → CorrelationId → Prometheus → RequestLog → CacheHeader (inner) → routers
    # `instrument(app)` is added BETWEEN RequestLogMiddleware and
    # CorrelationIdMiddleware so request_id is set when metrics fire (forward
    # compat for exemplars). See 23-RESEARCH.md §"App Wiring".
    #
    # Phase 26 / 26-02 fix-forward — CacheHeaderMiddleware must sit INSIDE
    # all ``BaseHTTPMiddleware`` subclasses (RequestLog, CorrelationId).
    # ``BaseHTTPMiddleware`` runs the downstream app in a separate ``anyio``
    # task, so a ``cache_outcome_var`` set inside the route handler is
    # invisible to any pure-ASGI middleware sitting OUTSIDE such a
    # boundary. Adding CacheHeader FIRST makes it innermost (LIFO of
    # ``add_middleware``), keeping it in the same task as the handler.
    app.add_middleware(CacheHeaderMiddleware)
    app.add_middleware(RequestLogMiddleware)
    instrumentator.instrument(app)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Expose /metrics. include_in_schema=False keeps OpenAPI clean (per
    # planning brief — avoids polluting the public API surface).
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Ensure unhandled exceptions return JSON with CORS headers."""
        logger.exception(
            "api.unhandled_exception",
            path=request.url.path,
            method=request.method,
        )
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
    app.include_router(market_router, tags=["market"])
    app.include_router(automation_router, tags=["automation"])
    app.include_router(prices_router, tags=["prices"])
    app.include_router(dashboard_router, tags=["dashboard"])
    app.include_router(admin_router, tags=["admin"])
    return app


app = create_app()
