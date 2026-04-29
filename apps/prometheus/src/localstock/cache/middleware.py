"""Phase 26 / 26-02 / D-08 — X-Cache: hit|miss response header (P-4).

Sets ``X-Cache`` on responses whose handler called ``get_or_compute``.
Routes that did NOT touch the cache emit no header (outcome stays None).

**Why pure ASGI, not BaseHTTPMiddleware:**

The plan originally proposed mirroring ``CorrelationIdMiddleware`` (a
``BaseHTTPMiddleware`` subclass). That works for the *parent→child*
direction (middleware sets a ContextVar before ``call_next``, handler
reads it). It does NOT work for the *child→parent* direction we need
here (handler sets, middleware reads after ``call_next``):
``BaseHTTPMiddleware`` runs the downstream app in a separate ``anyio``
task, so ContextVar mutations inside the handler are isolated and not
visible to ``dispatch`` after ``await call_next(request)``. This is the
well-known Starlette boundary issue (RESEARCH §7 P-4).

Pure ASGI middleware avoids the task boundary — ``await self.app(...)``
runs in the same coroutine context as ``send_wrapper``, so the
``cache_outcome_var`` set inside ``get_or_compute`` is visible when we
build the response start message.

We reset the ContextVar to ``None`` BEFORE invoking the inner app so a
non-caching request following a caching one (or any task-pool reuse)
cannot inherit a stale outcome (P-4 boundary, asserted by
``test_contextvar_reset_between_requests``).
"""
from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from localstock.cache._context import cache_outcome_var


class CacheHeaderMiddleware:
    """Emit ``X-Cache: hit|miss`` on responses from cache-aware routes."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = cache_outcome_var.set(None)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                outcome = cache_outcome_var.get()
                if outcome is not None:
                    headers = MutableHeaders(scope=message)
                    headers["X-Cache"] = outcome
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            cache_outcome_var.reset(token)
