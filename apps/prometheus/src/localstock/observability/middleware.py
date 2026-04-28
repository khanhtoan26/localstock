"""Correlation ID + request logging ASGI middlewares.

Wire order (CRITICAL — Starlette LIFO):
    CORS  →  CorrelationId  →  RequestLog  →  routers
Per CONTEXT.md D-02 / D-02b / D-04 / D-09.
"""
from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from localstock.observability.context import request_id_var

# D-02: trust inbound only if it matches this regex; rejects newlines, control
# chars, quotes — all classic log-injection vectors (RESEARCH Pitfall 6).
_RID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_HEADER = "X-Request-ID"


def _resolve_request_id(inbound: str | None) -> str:
    if inbound and _RID_RE.match(inbound):
        return inbound
    return uuid.uuid4().hex  # 32 hex chars — passes the regex itself


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """OBS-02 — set request_id contextvar + echo X-Request-ID header."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = _resolve_request_id(request.headers.get(_HEADER))
        token = request_id_var.set(rid)
        try:
            with logger.contextualize(request_id=rid):
                response = await call_next(request)
                response.headers[_HEADER] = rid
                return response
        finally:
            request_id_var.reset(token)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """OBS-04 — log {method, path, status, duration_ms} per request.

    Note: Q2 RESOLVED — log /health and /metrics too (no path filter); single-user
    deployment, low traffic, full observability preferred over noise reduction.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.bind(
                method=request.method,
                path=request.url.path,
                status=status,
                duration_ms=round(duration_ms, 2),
            ).info("http.request.completed")
