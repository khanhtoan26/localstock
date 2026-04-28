"""Loguru configuration — idempotent, JSON-stdout, redaction-aware.

PII policy (per CONTEXT.md D-10):
- Sensitive (redacted): token, api_key, password, secret, authorization,
                         database_url, telegram_bot_token, bot_token + URL credentials
- Non-sensitive (logged plainly): stock symbols, telegram chat_id, user IP
  (single-user app, no GDPR surface).
"""
from __future__ import annotations

import logging
import os
import re
import sys
from typing import Any

from loguru import logger

from localstock.config import get_settings
from localstock.observability.context import request_id_var, run_id_var

_SENSITIVE_KEYS = {
    "token",
    "api_key",
    "password",
    "secret",
    "authorization",
    "database_url",
    "telegram_bot_token",
    "bot_token",
}
_URL_CRED_RE = re.compile(r"(://)([^/\s:]+):([^@\s]+)(@)")
_REDACTED = "***REDACTED***"

_configured = False  # idempotency guard (Pitfall 5)


def _redact_url_creds(text: str) -> str:
    return _URL_CRED_RE.sub(r"\1***:***\4", text)


def _redact_extra(extra: dict[str, Any]) -> None:
    for k in list(extra.keys()):
        if k.lower() in _SENSITIVE_KEYS:
            extra[k] = _REDACTED


def _redaction_patcher(record: dict) -> None:
    # Redact extra dict keys
    _redact_extra(record["extra"])
    # Redact URL credentials in message
    if isinstance(record.get("message"), str):
        record["message"] = _redact_url_creds(record["message"])
    # Bind contextvars (loguru contextualize handles this, but stdlib bridge
    # may emit before contextualize wrap — defensive fallback)
    rid = request_id_var.get()
    if rid and "request_id" not in record["extra"]:
        record["extra"]["request_id"] = rid
    run_id = run_id_var.get()
    if run_id and "run_id" not in record["extra"]:
        record["extra"]["run_id"] = run_id


def _stdout_sink(message: Any) -> None:
    """Write to the *current* sys.stdout (resolved at call time).

    Loguru's `logger.add(sys.stdout, ...)` would freeze the reference at add-time.
    Pytest's capsys replaces sys.stdout per-test, so a frozen reference would
    leak output to the first test's buffer forever. Resolving lazily here keeps
    the idempotent contract intact while remaining capsys-compatible.
    """
    sys.stdout.write(message)


class InterceptHandler(logging.Handler):
    """Bridge stdlib logging → loguru. Recipe from loguru docs."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller frame skipping logging internals
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging() -> None:
    """Configure loguru singleton. Idempotent (Pitfall 5).

    - JSON to stdout in prod (or non-TTY); pretty to stderr if TTY (dev).
    - enqueue=True except under pytest (Pitfall 16, D-08).
    - Stdlib root logger replaced with InterceptHandler (D-09).
    - Redaction patcher installed (Pitfall 17, D-04).
    """
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = settings.log_level.upper()
    in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    enqueue = not in_pytest

    logger.remove()  # idempotency anchor (Pitfall 5)

    if sys.stderr.isatty() and not in_pytest:
        # Dev DX: pretty colored format
        logger.add(
            sys.stderr,
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=enqueue,
        )
    else:
        # Prod / CI: JSON to stdout (12-factor)
        logger.add(
            _stdout_sink,
            level=level,
            serialize=True,  # OBS-01 — newline-delimited JSON
            enqueue=enqueue,  # Pitfall 16 — async-safe
            backtrace=True,
            diagnose=False,  # diagnose=True can leak local vars (PII) — Pitfall 17
        )

    logger.configure(patcher=_redaction_patcher)

    # Stdlib bridge (D-09)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
        "apscheduler",
        "httpx",
        "httpcore",
        "asyncpg",
    ):
        std = logging.getLogger(noisy)
        std.handlers = [InterceptHandler()]
        std.propagate = False

    _configured = True
