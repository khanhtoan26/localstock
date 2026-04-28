"""Process-wide contextvars for correlation IDs.

Per CONTEXT.md D-02b: contextvars chosen over FastAPI Depends because they survive
asyncio.gather() and are visible inside scheduler/APScheduler jobs without a Request
object. Loguru's contextualize() wraps a stdlib ContextVar internally; using one
ourselves lets the redaction patcher (logging.py) and any non-loguru emitter read
the current correlation IDs.
"""
from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_run_id() -> str | None:
    return run_id_var.get()
