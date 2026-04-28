# Phase 22: Logging Foundation — Research

**Researched:** 2026-04-28
**Domain:** Observability — structured logging in async FastAPI + APScheduler
**Confidence:** HIGH (loguru patterns are standard; codebase already imports loguru in 41 files; CONTEXT.md locked all 10 implementation decisions)

## Summary

Phase 22 turns LocalStock's existing free-form `logger.info(f"...")` calls into structured, JSON-serialized log lines that carry `request_id` (HTTP) and `run_id` (pipeline) through `contextvars`, redact secrets, and bridge stdlib loggers (uvicorn / SQLAlchemy / APScheduler / httpx) into a single sink. No new dependencies — `loguru>=0.7,<1.0` is already pinned in `apps/prometheus/pyproject.toml` [VERIFIED: pyproject.toml lines 6-29].

The work is **mechanical**: ~150 LOC of new infrastructure under `apps/prometheus/src/localstock/observability/`, plus a sweep of **33 files / 103 f-string log calls** [VERIFIED: `grep -rEln 'logger\.[a-z]+\(\s*f["\x27]' apps/prometheus/src`] converted to loguru positional / keyword form. Pitfalls 4, 5, 16, 17, 20 [CITED: .planning/research/PITFALLS.md] dictate the non-obvious safety patterns: idempotent `logger.remove()` before `add()`, `enqueue=True` (but disabled under pytest), JSON serializer with `default=str` fallback, and a deny-list patcher.

**Primary recommendation:** Land the foundation (`observability/` package + middleware wiring + scheduler `contextualize`) in early waves before the f-string migration, so every new log line lands on the structured sink the moment it's converted. Land the lint gate **last** so the migration sweep doesn't hit a pre-commit wall mid-flight.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Log Output**
- **D-01 Sinks:** stdout JSON-only in production (`logger.add(sys.stdout, serialize=True, enqueue=True, level=...)`); pretty colored format when stderr is TTY (`sys.stderr.isatty()`). **NO file rotation** — process supervisor / Docker / systemd captures stdout, 12-factor compliant.
- **D-06 Log level:** `LOG_LEVEL` env var via Pydantic Settings (default `INFO`; tests pin `DEBUG` via fixture). No runtime endpoint — single-user app, restart suffices.

**Correlation IDs**
- **D-02 Request ID:** `CorrelationIdMiddleware` sets contextvar `request_id`. Source priority: (1) trust inbound `X-Request-ID` header **only if it matches `^[A-Za-z0-9-]{8,64}$`**, (2) fallback `uuid.uuid4().hex`. Echo back via response header `X-Request-ID`. Helios is same-origin → CORS-safe.
- **D-03 Pipeline run_id:** Wrap `Pipeline.run_full` body (after `PipelineRun` row commit) in `with logger.contextualize(run_id=str(pipeline_run.id))`. **Reuse `PipelineRun.id`** (already persisted), do NOT mint a separate uuid4.
- **D-02b Contextvar over Depends:** `contextvars.ContextVar` survives `asyncio.gather`, visible in scheduler jobs, no FastAPI `Depends` injection needed.

**Redaction**
- **D-04 Strategy:** Deny-list patcher via `logger.patch(...)`. Scan `record["extra"]` keys + record message:
  - Sensitive keys (case-insensitive): `token`, `api_key`, `password`, `secret`, `authorization`, `database_url`, `telegram_bot_token`, `bot_token`
  - Regex over message: URL credentials `://[^/\s]+:[^@\s]+@` → `://***:***@`
  - Replace with literal `***REDACTED***`
- **D-10 PII clarification:** Telegram `chat_id`, stock `symbol`, user IP are **non-sensitive** in this app (single-user, no GDPR/PII surface). Document in `observability/logging.py` module docstring so future contributors don't over-redact.

**Migration & Lint**
- **D-05 Existing call sites:** Hard-cut day one. Audit + fix all ~33 files using `from loguru import logger` to remove f-string violations. Loguru supports positional args (`logger.info("user {} did {}", user, action)`) — easy fix.
- **D-07 CI enforcement:** `grep`-based check, **not** Ruff custom rule. Two layers:
  1. Pre-commit hook in `.pre-commit-config.yaml` — fast-fail on commit
  2. GitHub Actions step — PR gate
  Pattern (negated success): `! grep -rE 'logger\.(debug|info|warning|error|critical|exception|trace|success)\(\s*f["\x27]' apps/prometheus/src/ apps/prometheus/tests/`. Escape: `# noqa: log-fstring`.

**Test Environment**
- **D-08 enqueue + pytest:** `enqueue=True` runs logger in background thread → can hang teardown. Detect `os.environ.get("PYTEST_CURRENT_TEST")` in init; if present → `enqueue=False`. Backup: conftest finalizer calls `logger.complete()`.
- **D-08b Capturing logs in tests:** Loguru `LogCapture`-style fixture. Document pattern in `tests/conftest.py`.

**Stdlib Logging Bridge**
- **D-09 InterceptHandler:** uvicorn / SQLAlchemy / APScheduler / asyncpg emit via stdlib `logging`. Install loguru `InterceptHandler` on root stdlib logger → all logs flow through one loguru sink. Applied in `observability/logging.py:configure_logging()` called from `create_app()` lifespan + scheduler startup.

### the agent's Discretion
- File layout inside `localstock/observability/` (planner decides: `logging.py`, `middleware.py`, or split further).
- Exact decorator/helper function names (signatures must stay stable).
- Pre-commit hook implementation detail (inline bash vs script file).
- Test fixture naming conventions.

### Deferred Ideas (OUT OF SCOPE)
- Log shipping to external service (Loki, Grafana Cloud, Datadog).
- Log sampling for high-volume endpoints.
- Distributed trace IDs (W3C Trace Context).
- PII compliance audit (GDPR/CCPA).
- Log replay / time-travel debugging.
- Per-route log level overrides.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBS-01 | Backend logs emitted as structured JSON (loguru `serialize=True` + `enqueue=True`) | §1 Logging Configuration — concrete `configure_logging()` block |
| OBS-02 | Each HTTP request tagged `request_id` via CorrelationIdMiddleware, propagated via contextvar | §3 Request ID Middleware — full FastAPI middleware code |
| OBS-03 | Each pipeline run tagged `run_id` via `logger.contextualize(run_id=...)` | §4 Pipeline run_id Propagation — wrap point in `pipeline.py` / `automation_service.py` |
| OBS-04 | Request log middleware records method, path, status, duration_ms per request | §3 — `RequestLogMiddleware` after CorrelationIdMiddleware |
| OBS-05 | Secret/PII redaction patcher — no token/API key/credential URL in logs | §5 Redaction Patcher — patcher function + regex |
| OBS-06 | CI lint rule: zero f-string log lines | §7 CI Lint Rule — pre-commit + GHA snippet |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JSON serialization & sinks | Backend (process-level) | — | Pure cross-cutting infra; no DB or client involvement |
| Correlation ID generation | Backend HTTP middleware | Frontend (Helios sends `X-Request-ID` if available) | Server is authoritative; frontend may pre-tag for end-to-end trace |
| Pipeline run_id binding | Backend scheduler | DB (`PipelineRun.id` is the source) | Reuse persisted UUID, no second identity |
| Secret redaction | Backend logger patcher | — | Defense-in-depth at emit boundary; cannot rely on call-sites |
| Stdlib bridge | Backend (root stdlib logger) | — | Library code (uvicorn/sqlalchemy/apscheduler/httpx/asyncpg) cannot be modified |
| F-string lint | CI pipeline + pre-commit | Backend src/tests source tree | Compile-time gate; not a runtime check |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `loguru` | `>=0.7,<1.0` (already pinned) | Structured JSON logger + contextvar binding via `contextualize()` + `patcher` | Already used in 41 source files [VERIFIED: grep]. `serialize=True`, `enqueue=True`, `contextualize()` are stable since 0.6 [CITED: STACK.md §"Already-installed"]. Avoids dual-logging-system limbo. |
| `pydantic-settings` | `>=2.0,<3.0` (already pinned) | `LOG_LEVEL` env var + validation | Existing `Settings` class extension only. |
| `fastapi` | `>=0.135,<1.0` (already pinned) | Middleware host (`BaseHTTPMiddleware` or pure ASGI) | Existing dependency. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `contextvars` | stdlib (Python 3.12) | `ContextVar` for `request_id_var`, `run_id_var` | Loguru's `contextualize()` wraps a stdlib `ContextVar` internally; using one ourselves works in repository code without imports of loguru. |
| `logging` | stdlib | InterceptHandler bridge target | Required to capture uvicorn/sqlalchemy/apscheduler/httpx/asyncpg loggers. |
| `uuid` | stdlib | Fallback request id generation | `uuid4().hex` (32-char hex; matches the `[A-Za-z0-9-]{8,64}` validation regex). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `loguru` | `structlog + python-json-logger` | Cleaner native API, but rewriting all 41 import sites is high-churn; benefit marginal for single-user app [CITED: STACK.md line 66]. |
| Custom `BaseHTTPMiddleware` | `asgi-correlation-id` PyPI library | One less dep; we need redaction-aware contextvar binding anyway; ~30 LOC saves nothing. [ASSUMED — based on package size review] |
| Loguru `patcher` for redaction | Subclass `JSONFormatter` | Patcher composes; can chain run-id enricher + redactor; matches pitfall-recommended pattern [CITED: PITFALLS.md Pitfall 17]. |
| Ruff custom rule | Plain `grep` | Ruff has no native rule for loguru f-string; custom rule = `astral-sh/ruff` plugin authoring overhead. Grep + pre-commit + GHA covers it in 5 lines [CITED: CONTEXT.md D-07]. |

**Installation:** No new deps. Only Phase 22 *dev* surface area is `pre-commit` (optional) — runtime stack unchanged.

**Version verification:**
```bash
$ grep loguru apps/prometheus/pyproject.toml
    "loguru>=0.7,<1.0",
```
[VERIFIED: pyproject.toml line 18]. Latest stable `loguru` is `0.7.3` (PyPI, Dec 2024) — within range. `serialize`, `enqueue`, `contextualize`, `patch`, `complete` APIs all stable since 0.6.x [CITED: https://loguru.readthedocs.io/en/stable/api/logger.html].

## Architecture Patterns

### System Architecture Diagram

```
                              ┌──────────────────────────────────────────────────┐
                              │  configure_logging()  (idempotent; called once   │
                              │  in lifespan + once at module import for CLI)   │
                              │   1. logger.remove()                             │
                              │   2. logger.add(sink, serialize, enqueue, level)│
                              │   3. logger.configure(patcher=redaction_patcher)│
                              │   4. logging.root.handlers = [InterceptHandler]│
                              └────────────┬─────────────────────────────────────┘
                                           │
                                           ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │                      Loguru Singleton (logger)                       │
       │   ┌────────────────┐                                                 │
       │   │ patcher chain  │  redact(record["extra"]) → redact(message)     │
       │   └──────┬─────────┘                                                 │
       │          ▼                                                           │
       │   sink: sys.stdout (JSON via serialize=True, enqueue=True)           │
       └────────────────────────────▲────────────────────────────────────────┘
                                    │
   ┌────────────────────────────────┼─────────────────────────────────────────┐
   │                                │                                         │
   │  HTTP path                     │       Pipeline path                     │
   │                                │                                         │
   │  Request ──► CorrelationId    │       APScheduler daily_job             │
   │           middleware           │           │                              │
   │     reads X-Request-ID         │           ▼                              │
   │     (validates regex)          │       Pipeline.run_full()                │
   │     or generates uuid4         │       creates PipelineRun row, commits  │
   │           │                    │           │                              │
   │           ▼                    │           ▼                              │
   │   contextvars.ContextVar       │   logger.contextualize(                 │
   │   request_id_var.set(rid)      │       run_id=str(run.id))               │
   │   logger.contextualize(        │       │                                  │
   │       request_id=rid):         │       ▼                                  │
   │       │                        │   crawl/analyze/score/report             │
   │       ▼                        │   (every nested logger.info inherits   │
   │   RequestLogMiddleware times   │    run_id via contextvar)               │
   │   call → emits {method, path,  │                                         │
   │   status, duration_ms}         │                                         │
   │       │                        │                                         │
   │       ▼                        │                                         │
   │   Response.headers[            │                                         │
   │     "X-Request-ID"] = rid      │                                         │
   └────────────────────────────────┴─────────────────────────────────────────┘

   Stdlib bridge:
       uvicorn / sqlalchemy / apscheduler / httpx / asyncpg
            │  (all use stdlib logging.Logger)
            ▼
       logging.root  ─────►  InterceptHandler  ─────►  loguru.logger
                              (frame inspection         same JSON sink,
                               + level mapping)         same patchers
```

### Recommended Project Structure

```
apps/prometheus/src/localstock/
├── observability/                        # NEW package
│   ├── __init__.py                       # exports configure_logging, contextvars
│   ├── logging.py                        # configure_logging(), redaction patcher,
│   │                                     #   InterceptHandler, JSON serializer
│   ├── context.py                        # contextvars: request_id_var, run_id_var
│   │                                     #   + helpers: get_request_id(), bind_run_id()
│   └── middleware.py                     # CorrelationIdMiddleware,
│                                         #   RequestLogMiddleware
├── api/app.py                            # MODIFY — wire middlewares + call
│                                         #   configure_logging() in lifespan
├── scheduler/scheduler.py                # MODIFY — daily_job: contextualize run_id
├── services/pipeline.py                  # MODIFY — wrap run_full body in
│                                         #   contextualize(run_id=str(run.id))
├── config.py                             # MODIFY — already has log_level, may add
│                                         #   validation
└── …~33 files…                           # MODIFY — convert f-string log calls
```

### Pattern 1: Idempotent `configure_logging()`

**What:** Single entry point; safe to call multiple times (lifespan + tests + CLI bin scripts).
**When to use:** Top of every process entry: `create_app()` lifespan, `bin/*.py` scripts, conftest.

```python
# apps/prometheus/src/localstock/observability/logging.py
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
    "token", "api_key", "password", "secret", "authorization",
    "database_url", "telegram_bot_token", "bot_token",
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


class InterceptHandler(logging.Handler):
    """Bridge stdlib logging → loguru. Recipe from loguru docs."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
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
            sys.stdout,
            level=level,
            serialize=True,         # OBS-01 — newline-delimited JSON
            enqueue=enqueue,        # Pitfall 16 — async-safe
            backtrace=True,
            diagnose=False,         # diagnose=True can leak local vars (PII)
        )

    logger.configure(patcher=_redaction_patcher)

    # Stdlib bridge (D-09)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access",
                  "sqlalchemy.engine", "apscheduler", "httpx", "httpcore", "asyncpg"):
        std = logging.getLogger(noisy)
        std.handlers = [InterceptHandler()]
        std.propagate = False

    _configured = True
```

**Why `diagnose=False` in prod:** loguru's `diagnose=True` prints local-variable values in tracebacks — that may include `Settings` instances or DB URL strings. Redaction patcher only touches `record["message"]` and `record["extra"]`, **not** the diagnose-rendered traceback. [CITED: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add — "diagnose"] [VERIFIED: confirms PII risk in Pitfall 17].

### Pattern 2: ContextVars + binding helper

```python
# apps/prometheus/src/localstock/observability/context.py
"""Process-wide contextvars for correlation IDs.

These survive asyncio.gather() and are read by:
- loguru contextualize() wrappers (preferred)
- redaction patcher (fallback enrichment)
"""
from __future__ import annotations
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_run_id() -> str | None:
    return run_id_var.get()
```

### Anti-Patterns to Avoid

- ❌ `logger = logging.getLogger(__name__)` — loguru is global singleton; never per-module factory.
- ❌ Multiple unguarded `logger.add(...)` calls — duplicates lines (Pitfall 5).
- ❌ Sync sink without `enqueue=True` — blocks event loop on slow stdout/disk (Pitfall 16).
- ❌ `logger.debug(settings)` or `logger.exception` on a Pydantic ValidationError that includes `Settings` — leaks tokens (Pitfall 17).
- ❌ `default=None` JSON serializer — datetime/Decimal/UUID raise; lose batch (Pitfall 20). Loguru's `serialize=True` uses `default=str` internally [CITED: loguru source `_handler.py`], so we're covered for stdlib types — verify with a unit test (see §10).
- ❌ Echoing untrusted `X-Request-ID` verbatim — log injection / forwarded request smuggling. **Always validate against `^[A-Za-z0-9-]{8,64}$`** (D-02).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON log serialization | Custom `JSONFormatter` | `loguru.add(..., serialize=True)` | Built-in; handles unicode, exc_info, extra, level — one line. |
| Stdlib → loguru bridge | Custom handler enumerating all libraries | `InterceptHandler` recipe [CITED: loguru docs] | Frame-walking + level mapping is non-trivial; recipe is canonical. |
| Correlation propagation across `asyncio.gather` | Threading kwarg through every coroutine | `contextvars.ContextVar` | Python's official primitive for async-task-local state; loguru `contextualize` is built on it. |
| Async-safe sink | Asyncio-native sink + queue | `enqueue=True` | Loguru offloads emission to a worker thread + multiprocessing.Queue — battle-tested. |
| Secret redaction | Per-call-site `**kwargs` filtering | `logger.configure(patcher=...)` | Patcher runs **once** at emit; cannot be forgotten by call-sites; defense-in-depth. |
| F-string lint | AST-based ruff plugin | Plain `grep -rE` in pre-commit + GHA | Pattern is unambiguous (8 method names, `f"` opener); 5-line shell rule; D-07 explicitly chooses this. |

**Key insight:** Every pattern above is documented in loguru's recipe section. Resist the urge to wrap loguru — its API *is* the wrapper.

## Runtime State Inventory

> Phase 22 is partially a refactor (rename f-string → positional/kwarg loguru calls). Inventory included.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — logs are stdout-only, no file rotation, no DB-backed log table | None |
| Live service config | None — Helios is same-origin; no external log shipper | None (Helios may optionally start sending `X-Request-ID`; not required) |
| OS-registered state | None — no systemd / launchd unit names embed log strings | None |
| Secrets / env vars | New: `LOG_LEVEL` env var (already present in `Settings.log_level`, default `INFO`) | None — no secret rotation |
| Build artifacts | None — pure-Python additions to existing package | None (no `egg-info` / wheels affected) |

**Code-level migration state (the actual lift):**
- 33 files with f-string log calls [VERIFIED: grep, see §6 file list]
- 103 individual log call rewrites [VERIFIED: `grep -rEcn` sum]
- 0 test files affected [VERIFIED]

## Common Pitfalls

### Pitfall 1: F-string logs flatten structure (Pitfall 4 from PITFALLS.md)

**What goes wrong:** `logger.info(f"Processed {symbol} score={score}")` produces `{"message": "Processed VNM score=78"}` — `symbol` and `score` are stringified into `message`, not searchable as JSON fields.
**Why it happens:** f-strings interpolate before loguru sees the call. Loguru gets a fully-rendered string; can't decompose.
**How to avoid:** Convert to one of:
- Positional: `logger.info("score computed for {symbol} = {score}", symbol=symbol, score=score)`
- Or extra dict: `logger.bind(symbol=symbol, score=score).info("score computed")`
- Standardize event names: `pipeline.stage.started`, `crawl.symbol.failed` — searchable.

**Warning signs:** "show all failures for VNM today" requires regex against `message`.

### Pitfall 2: Loguru double-init (Pitfall 5)

**What goes wrong:** `logger.add()` is *additive*. Each lifespan re-init in tests stacks handlers; by test 50 every line emits 50×.
**Why it happens:** Module-level singleton; FastAPI `TestClient` re-imports app; conftest fixture not session-scoped.
**How to avoid:** `_configured` module-flag guard + `logger.remove()` first thing in `configure_logging()` (already in §1 code). Pytest fixture **session-scoped**.
**Warning signs:** CI suite I/O 5–10× slower than local; "Duplicated handler" log noise.

### Pitfall 3: enqueue + pytest hangs (Pitfall 16 + D-08)

**What goes wrong:** `enqueue=True` runs a background thread + `multiprocessing.Queue`. Pytest collects → exits → main thread doesn't `logger.complete()` → queue thread keeps pending records → test process hangs in atexit.
**Why it happens:** Async sink lifecycle outlives pytest's idea of "test done".
**How to avoid:** Detect `PYTEST_CURRENT_TEST` env var; force `enqueue=False`. Belt-and-suspenders: conftest finalizer calls `logger.complete()`.

### Pitfall 4: Un-serializable fields (Pitfall 20)

**What goes wrong:** `logger.info("ran", started_at=datetime.utcnow(), price=Decimal("100"))` → loguru `serialize=True` internally uses `json.dumps(..., default=str)` so this works for **stdlib** types. Custom classes (e.g., a SQLAlchemy ORM instance) still raise `TypeError`. One bad line **drops the whole batch** if a downstream JSON parser is strict.
**How to avoid:** Convert custom objects to dicts/strings before binding. Round-trip unit test in §10.

### Pitfall 5: Diagnose=True leaks PII (Pitfall 17)

**What goes wrong:** `diagnose=True` shows local-variable values in tracebacks. If a Pydantic ValidationError surfaces around `Settings(...)`, the rendered traceback includes `telegram_bot_token=...`, `database_url=postgres://user:pass@host`. Patcher does **not** scrub diagnose output.
**How to avoid:** `diagnose=False` in prod sink (set in §1 code). Pretty dev sink may leave it on (`diagnose=True`) since dev runs with redacted `.env` only and convenience > paranoia.

### Pitfall 6: X-Request-ID injection / log smuggling

**What goes wrong:** Untrusted client sends `X-Request-ID: \n[CRIT] root system pwned` — if echoed to log message verbatim, JSON serializer escapes it but a downstream `jq | grep` review may visually parse the injected line.
**How to avoid:** Validate `^[A-Za-z0-9-]{8,64}$` regex (D-02). Reject silently → fall back to `uuid4().hex`.

### Pitfall 7: APScheduler swallowing the contextualize block

**What goes wrong:** `scheduler.add_job(daily_job, ...)` — if `daily_job` raises, APScheduler logs and keeps running, but the contextualize block exits and run_id is lost from any *post-failure cleanup* logger calls. (Phase 22 doesn't add cleanup logic — flagged for Phase 24's `EVENT_JOB_ERROR` listener.)
**How to avoid:** Wrap `contextualize` **inside** the try/except, not around it.

## Code Examples

### Request ID middleware (full code) — §3

```python
# apps/prometheus/src/localstock/observability/middleware.py
"""Correlation ID + request logging ASGI middlewares.

Wire order (CRITICAL — see api/app.py):
    CORS  →  CorrelationId  →  RequestLog  →  routers
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

_RID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_HEADER = "X-Request-ID"


def _resolve_request_id(inbound: str | None) -> str:
    if inbound and _RID_RE.match(inbound):
        return inbound
    return uuid.uuid4().hex  # 32 hex chars — passes regex


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
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
    """OBS-04 — log {method, path, status, duration_ms} per request."""
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
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
```

**Wiring (`api/app.py` modification):**

```python
# add imports
from localstock.observability.logging import configure_logging
from localstock.observability.middleware import (
    CorrelationIdMiddleware, RequestLogMiddleware,
)

def create_app() -> FastAPI:
    configure_logging()  # earliest possible — before FastAPI logs any startup
    app = FastAPI(title="LocalStock API", lifespan=get_lifespan, ...)
    # Middleware order — last added runs FIRST (Starlette LIFO):
    # so add in reverse: RequestLog (innermost), then CorrelationId, then CORS (outermost)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)
    ...
```

> ⚠️ Starlette middleware ordering is LIFO — `add_middleware(X)` followed by `add_middleware(Y)` runs `Y` outermost. Documented gotcha. [CITED: https://www.starlette.io/middleware/#using-middleware]

### Pipeline run_id propagation — §4

`Pipeline.run_full` already creates `PipelineRun` row + commits at line 65. Wrap the body **after the commit** so `run.id` exists:

```python
# apps/prometheus/src/localstock/services/pipeline.py — modification around line 50-70

from contextvars import copy_context
from loguru import logger

from localstock.observability.context import run_id_var

async def run_full(self, run_type: str = "daily") -> PipelineRun:
    run = PipelineRun(started_at=datetime.now(UTC), status="running", run_type=run_type)
    self.session.add(run)
    await self.session.commit()                         # run.id now populated

    run_id = str(run.id)
    token = run_id_var.set(run_id)
    try:
        with logger.contextualize(run_id=run_id):       # OBS-03
            logger.info("pipeline.run.started", run_type=run_type)
            try:
                # … existing Step 1..N logic …
                pass
            finally:
                logger.info("pipeline.run.completed", status=run.status)
        return run
    finally:
        run_id_var.reset(token)
```

**Why both `contextualize` AND `run_id_var.set`:** `contextualize` covers loguru calls *only*. The redaction patcher's defensive enrichment (§1) reads `run_id_var` so any **stdlib** log routed through `InterceptHandler` (e.g., SQLAlchemy query log emitted from a repository called inside the pipeline) also gets `run_id`.

**Scheduler entry already wraps via the lifespan** — but `daily_job` itself should also bind, in case the job runs outside `run_full` (e.g., admin job worker):

```python
# scheduler/scheduler.py — daily_job modification
async def daily_job():
    logger.info("scheduler.daily.start")
    service = AutomationService()
    try:
        result = await service.run_daily_pipeline()    # Pipeline.run_full binds run_id
        logger.info("scheduler.daily.result", status=result["status"])
    except Exception as e:
        logger.exception("scheduler.daily.failed")     # exception captures stack
```

### Redaction patcher unit test — §5

```python
# apps/prometheus/tests/test_observability/test_redaction.py
import json
from io import StringIO
from loguru import logger
from localstock.observability.logging import configure_logging, _redact_url_creds

def test_url_credentials_redacted():
    assert _redact_url_creds(
        "connecting to postgresql://user:hunter2@db:5432/x"
    ) == "connecting to postgresql://***:***@db:5432/x"

def test_token_extra_redacted(capsys):
    configure_logging()
    logger.bind(telegram_bot_token="123:ABC", symbol="VNM").info("telegram.send")
    out = capsys.readouterr().out
    record = json.loads(out.strip().splitlines()[-1])
    assert record["record"]["extra"]["telegram_bot_token"] == "***REDACTED***"
    assert record["record"]["extra"]["symbol"] == "VNM"  # non-sensitive (D-10)
```

### F-string migration examples (§6)

| Before | After (positional) | After (bind) |
|--------|---------------------|--------------|
| `logger.info(f"Step 1: Stored {count} HOSE stock listings")` | `logger.info("pipeline.listings.stored", count=count)` | `logger.bind(count=count).info("pipeline.listings.stored")` |
| `logger.warning(f"Skipping {symbol}: {e}")` | `logger.warning("crawl.symbol.skipped", symbol=symbol, error=str(e))` | — |
| `logger.error(f"Telegram send failed: {e}")` | `logger.exception("telegram.send.failed")` (when inside `except`) | — |
| `logger.info(f"Fetched {len(df)} corporate events for {symbol}")` | `logger.info("crawl.events.fetched", symbol=symbol, count=len(df))` | — |

**Mechanical rule:** `f"X {var}"` → `("X.event.name", var=var)`; bare exception interpolation `f"... {e}"` → `logger.exception("...")` if inside `except`, else `error=str(e)`.

### Pre-commit hook (`.pre-commit-config.yaml`) — §7

```yaml
# .pre-commit-config.yaml — new file or merge with existing
repos:
  - repo: local
    hooks:
      - id: no-fstring-log
        name: "loguru: no f-string log calls"
        entry: bash -c '! grep -rnE "logger\.(debug|info|warning|error|critical|exception|trace|success)\(\s*f[\"\x27]" apps/prometheus/src/ apps/prometheus/tests/'
        language: system
        pass_filenames: false
        # escape: add "# noqa: log-fstring" inline
```

### GitHub Actions step — §7

```yaml
# .github/workflows/ci.yml  (or current lint workflow)
- name: Lint — no f-string log calls
  run: |
    set -e
    if grep -rnE 'logger\.(debug|info|warning|error|critical|exception|trace|success)\(\s*f["'"'"']' apps/prometheus/src/ apps/prometheus/tests/; then
      echo "::error::f-string log calls detected — convert to positional/kwargs (see Phase 22 RESEARCH §6)"
      exit 1
    fi
```

> NOTE: There is no `.github/workflows/` directory yet [VERIFIED: `ls .github/workflows` → "No such file or directory"]. Phase 22 may either (a) add a minimal lint-only workflow, or (b) defer GHA wiring until a CI workflow is introduced in a later milestone. **Planner decision** — pre-commit alone covers the local gate; GHA without an existing workflow is creating new ground.

### Test fixtures (§8)

```python
# apps/prometheus/tests/conftest.py — additions

import os
import pytest
from loguru import logger

# Ensure pytest-mode detection reaches configure_logging
os.environ.setdefault("PYTEST_CURRENT_TEST", "init")

@pytest.fixture(scope="session", autouse=True)
def _configure_test_logging():
    """Force LOG_LEVEL=DEBUG and enqueue=False for tests (D-08)."""
    os.environ["LOG_LEVEL"] = "DEBUG"
    from localstock.observability.logging import configure_logging
    configure_logging()
    yield
    logger.complete()  # drain any queued records


@pytest.fixture
def loguru_caplog():
    """Capture loguru output for a single test.

    Usage:
        async def test_x(loguru_caplog):
            do_thing()
            assert any(r["message"] == "thing.done" for r in loguru_caplog.records)
    """
    records: list[dict] = []
    sink_id = logger.add(
        lambda msg: records.append(msg.record),
        level="DEBUG",
        format="{message}",
    )
    class _Capture:
        @property
        def records(self):
            return records
    yield _Capture()
    logger.remove(sink_id)
```

## File-by-File Impact

### NEW files (3)
- `apps/prometheus/src/localstock/observability/__init__.py`
- `apps/prometheus/src/localstock/observability/logging.py` — `configure_logging`, `InterceptHandler`, `_redaction_patcher`
- `apps/prometheus/src/localstock/observability/context.py` — `request_id_var`, `run_id_var`, accessors
- `apps/prometheus/src/localstock/observability/middleware.py` — `CorrelationIdMiddleware`, `RequestLogMiddleware`

### MODIFY — wire infrastructure (4 files)
- `apps/prometheus/src/localstock/api/app.py` — call `configure_logging()` at top of `create_app()`; wire 2 middlewares (order matters — LIFO).
- `apps/prometheus/src/localstock/scheduler/scheduler.py` — convert `daily_job` f-strings; lifespan calls `configure_logging()` (defensive, idempotent).
- `apps/prometheus/src/localstock/services/pipeline.py` — wrap `run_full` body in `contextualize(run_id=...)` + `run_id_var.set`.
- `apps/prometheus/src/localstock/config.py` — already has `log_level: str = "INFO"`. Optional: add a `field_validator` that uppercases & validates against {`TRACE`,`DEBUG`,`INFO`,`SUCCESS`,`WARNING`,`ERROR`,`CRITICAL`}.

### MODIFY — f-string migration (33 source files, 103 calls)

**Crawlers (7):** `base.py`, `company_crawler.py`, `event_crawler.py`, `finance_crawler.py`, `news_crawler.py`, `price_crawler.py` (+ `macro/crawler.py`)
**Repositories (12):** `event_repo.py`, `indicator_repo.py`, `industry_repo.py`, `job_repo.py`, `macro_repo.py`, `news_repo.py`, `price_repo.py`, `ratio_repo.py`, `report_repo.py`, `score_repo.py`, `sector_repo.py`, `sentiment_repo.py`, `stock_repo.py`
**Services (8):** `admin_service.py`, `analysis_service.py`, `automation_service.py`, `news_service.py`, `pipeline.py`, `report_service.py`, `score_change_service.py`, `scoring_service.py`, `sector_service.py`
**Other (4):** `ai/client.py`, `analysis/technical.py`, `notifications/telegram.py`, `scheduler/scheduler.py`

**Verification commands:**
```bash
# Pre-migration count
grep -rEcn 'logger\.[a-z]+\(\s*f["\x27]' apps/prometheus/src | awk -F: '{s+=$2}END{print s}'  # 103

# Post-migration count (must be 0)
grep -rEln 'logger\.[a-z]+\(\s*f["\x27]' apps/prometheus/src | wc -l  # 0
```

### MODIFY — CI/test infra (2 files)
- `.pre-commit-config.yaml` — NEW or extend; add f-string-log hook.
- `apps/prometheus/tests/conftest.py` — add `_configure_test_logging` session fixture + `loguru_caplog`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `logger.info(f"...")` everywhere | Loguru positional/kwargs + `serialize=True` | Phase 22 | Searchable JSON; OBS-01..06 satisfied |
| stdlib `logging.basicConfig` (uvicorn default) | InterceptHandler bridge → loguru | Phase 22 | Single sink, single format |
| No correlation ID | `X-Request-ID` + contextvar + `contextualize` | Phase 22 | End-to-end request trace |
| Settings in plaintext logs | Patcher deny-list + URL credential mask | Phase 22 | No token leakage |

**Deprecated/outdated:**
- File rotation via loguru `rotation=` — superseded by 12-factor stdout capture (D-01).
- f-string log calls — lint-rejected.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Loguru `serialize=True` uses `json.dumps(..., default=str)` (stdlib types safe) | §"Anti-Patterns to Avoid" | Datetime/Decimal/UUID unexpectedly raise → batch fail. **Mitigation:** §10 round-trip test catches this. |
| A2 | `asgi-correlation-id` PyPI library not worth adding | Standard Stack table | Re-implementing ~30 LOC if wrong; low risk. |
| A3 | Loguru `contextualize` inherits across `asyncio.gather`-spawned tasks | Pattern 2 | If false, run_id missing in concurrent crawls. **Mitigation:** Defensive `run_id_var` enrichment in patcher (§1) covers gap. |
| A4 | Loguru `diagnose=False` does not expose local var values in traceback | Pitfall 5 | If true: prod traceback could leak `Settings`. **Mitigation:** §10 should add a test that triggers an exception inside `Settings(...)` and verifies stdout JSON contains no `telegram_bot_token` value. |
| A5 | `PipelineRun.id` is populated immediately after `await session.commit()` (UUID default) | §4 wrap point | If `id` is `None` post-commit (e.g., DB-side default not flushed back), `str(None)` poisons run_id. **Mitigation:** explicit `await session.refresh(run)` if needed; add unit test. |
| A6 | No existing `.github/workflows/` directory exists | §7 GHA snippet | Verified absent; Phase 22 must decide whether to introduce one or defer GHA gate to later milestone. |
| A7 | Helios will optionally send `X-Request-ID`; not required | §3 middleware | Helios changes are out-of-scope for Phase 22 (frontend phase later). Backend works either way. |

## Open Questions

1. **Where does `configure_logging()` run for CLI scripts (`bin/crawl.py`, `bin/analyze.py`, `bin/score.py`)?**
   - What we know: They import `from loguru import logger` and emit logs. They don't go through `create_app()`.
   - What's unclear: Should each `bin/*.py` call `configure_logging()` at module top, or import a shared `bin/__init__.py` that does so?
   - Recommendation: Add `configure_logging()` call at top of each `bin/*.py` (idempotent; cheap). Planner can add this as a small task.

2. **Should `RequestLogMiddleware` skip `/health/*` and `/metrics` paths?**
   - What we know: Health probes hit every few seconds; doubling log volume per scrape.
   - What's unclear: Phase 22 spec doesn't say.
   - Recommendation: Skip `/health` and `/metrics` (Phase 23 will add `/metrics`). Configurable env: `LOG_REQUEST_SKIP_PATHS=/health,/metrics`. Planner decides.

3. **Do we need `logger.complete()` on FastAPI shutdown?**
   - What we know: `enqueue=True` keeps a worker thread; on SIGTERM the queue may have pending records.
   - What's unclear: Whether uvicorn graceful shutdown drains atexit handlers before process exits.
   - Recommendation: Call `logger.complete()` in `get_lifespan` post-yield block. Cheap insurance.

4. **`field_validator` on `log_level`?**
   - What we know: `LOG_LEVEL=invalid` will currently start the app and fail at first `logger.add(level=...)` — late error.
   - Recommendation: Add validator that uppercases + checks against loguru's level set. Fail-fast.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All Phase 22 code | ✓ | per pyproject.toml `requires-python>=3.12` | — |
| `loguru` | Logger | ✓ | `>=0.7,<1.0` (latest 0.7.3) | — |
| `fastapi` / `starlette` | Middleware | ✓ | `>=0.135,<1.0` | — |
| `pydantic-settings` | `LOG_LEVEL` env | ✓ | `>=2.0,<3.0` | — |
| `pre-commit` | Lint gate | ✗ | — | Plain shell `Makefile` target invoked manually + GHA |
| `.github/workflows/` | GHA gate | ✗ (directory absent) [VERIFIED] | — | Pre-commit alone or defer to later milestone |

**Missing dependencies with fallback:**
- `pre-commit` → install via `uv pip install pre-commit` (dev-only); fall back to a `make lint` target if not adopted.
- `.github/workflows/` directory missing → either create with a minimal `lint.yml` or defer (decision for planner).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (auto mode) — already in `pyproject.toml` [VERIFIED] |
| Config file | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd apps/prometheus && uv run pytest tests/test_observability/ -x` |
| Full suite command | `cd apps/prometheus && uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBS-01 | Every log line is valid JSON; round-trips through `json.loads` including exc traces, datetime, Decimal | unit | `uv run pytest tests/test_observability/test_json_sink.py -x` | ❌ Wave 0 |
| OBS-02 | `X-Request-ID` echoed in response; valid inbound preserved; invalid inbound replaced with uuid4; contextvar visible from inside route handler | integration | `uv run pytest tests/test_observability/test_correlation.py -x` | ❌ Wave 0 |
| OBS-03 | `run_id` appears in every log line emitted from `Pipeline.run_full` body (including nested repo calls via stdlib bridge) | integration | `uv run pytest tests/test_observability/test_run_id.py -x` | ❌ Wave 0 |
| OBS-04 | `RequestLogMiddleware` emits `http.request.completed` with `method`, `path`, `status`, `duration_ms` numeric fields | integration | `uv run pytest tests/test_observability/test_request_log.py -x` | ❌ Wave 0 |
| OBS-05 | Logging `Settings(...)` instance does not produce token/password/database_url in JSON; URL with creds masked | unit | `uv run pytest tests/test_observability/test_redaction.py -x` | ❌ Wave 0 (sample in §"Code Examples") |
| OBS-06 | `grep -rE 'logger\.[a-z]+\(\s*f["\x27]' apps/prometheus/src apps/prometheus/tests` returns 0 matches; pre-commit hook fails on synthetic violation | shell | `bash scripts/check_no_fstring_log.sh` (or pre-commit run --all-files) | ❌ Wave 0 |
| Idempotency | `configure_logging()` called twice yields exactly 1 sink (Pitfall 5 regression) | unit | `uv run pytest tests/test_observability/test_idempotent.py -x` | ❌ Wave 0 |
| Async-safe sink | Under `enqueue=True` (non-pytest), event loop is not blocked by stdout pressure | integration / smoke | `uv run pytest tests/test_observability/test_async_sink.py` | ❌ Wave 0 (manual smoke acceptable) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_observability/ -x` (sub-second tests)
- **Per wave merge:** `uv run pytest` (full 326+ test suite — must stay green; logging changes affect every test that touches loguru)
- **Phase gate:** Full suite green + `bash scripts/check_no_fstring_log.sh` exits 0 + manual smoke: start `uv run uvicorn localstock.api.app:app`, hit `curl -H "X-Request-ID: testabcdefgh1234" http://localhost:8000/health`, confirm `X-Request-ID` echoed and a JSON log line containing `request_id` appeared on stdout.

### Wave 0 Gaps
- [ ] `apps/prometheus/tests/test_observability/__init__.py` — new test package
- [ ] `apps/prometheus/tests/test_observability/test_json_sink.py` — OBS-01 round-trip + datetime/Decimal/UUID + exception traceback
- [ ] `apps/prometheus/tests/test_observability/test_correlation.py` — OBS-02 (TestClient with valid/invalid/missing inbound header)
- [ ] `apps/prometheus/tests/test_observability/test_run_id.py` — OBS-03 (mock `Pipeline.run_full`, assert nested log records carry `run_id`)
- [ ] `apps/prometheus/tests/test_observability/test_request_log.py` — OBS-04 (assert middleware emits structured fields with realistic durations)
- [ ] `apps/prometheus/tests/test_observability/test_redaction.py` — OBS-05 (token, password, database_url, URL credentials)
- [ ] `apps/prometheus/tests/test_observability/test_idempotent.py` — Pitfall 5 regression
- [ ] `apps/prometheus/tests/test_observability/test_diagnose_no_pii.py` — Pitfall 17 regression (force exception inside Settings, scan stdout for plaintext token)
- [ ] `apps/prometheus/tests/conftest.py` — `_configure_test_logging` session fixture + `loguru_caplog` (additions)
- [ ] `scripts/check_no_fstring_log.sh` (or inline in pre-commit) — OBS-06 grep gate
- [ ] Framework install: none needed (pytest already installed)

## Project Constraints (from copilot-instructions.md / CLAUDE.md)

> `copilot-instructions.md` exists at repo root; redirects all GSD work to `.github/skills/get-shit-done`. CLAUDE.md is the operational constraint source.

- **Vietnamese comments / log messages OK** — UTF-8 round-trips through loguru `serialize=True` correctly. Event names should still be ASCII keys (`pipeline.run.started`) for grep-ability.
- **Async-first; no blocking I/O** — `enqueue=True` is mandatory in prod (Pitfall 16); pytest exception is explicit (D-08).
- **Single source of truth** — no per-module `logging.getLogger(__name__)`. Use `from loguru import logger` only.
- **Tests timeout at 30s** — `enqueue=True` could violate this if not disabled under pytest. Conftest fixture handles it.
- **All questions to user via decision UI** — orthogonal to Phase 22; affects orchestrator/planner UX, not implementation.
- **No hardcoded secrets** — config via env vars only. Phase 22 reinforces this by redacting at emit boundary.
- **No new external services** — D-01 forbids file rotation / external log shippers; 12-factor stdout only.

## Sources

### Primary (HIGH confidence)
- `loguru` 0.7.3 official docs — https://loguru.readthedocs.io/en/stable/api/logger.html — verified `serialize`, `enqueue`, `contextualize`, `patch`, `complete`, `remove` semantics
- Loguru "Entirely compatible with standard logging" recipe — https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging — InterceptHandler reference implementation
- `apps/prometheus/pyproject.toml` — verified loguru pinned `>=0.7,<1.0` [VERIFIED in repo]
- `apps/prometheus/src/localstock/api/app.py` — verified middleware wiring point + global exception handler [VERIFIED]
- `apps/prometheus/src/localstock/scheduler/scheduler.py` — verified lifespan structure + daily_job location [VERIFIED]
- `apps/prometheus/src/localstock/services/pipeline.py` — verified `PipelineRun` row created + committed before stages [VERIFIED]
- `.planning/research/PITFALLS.md` Pitfalls 4, 5, 16, 17, 20 [CITED]
- `.planning/research/STACK.md` §"Already-installed" [CITED]
- `.planning/research/ARCHITECTURE.md` §"Pattern: contextvar over Depends" [CITED]
- `.planning/phases/22-logging-foundation/22-CONTEXT.md` — D-01..D-10 locked decisions [VERIFIED in repo]

### Secondary (MEDIUM confidence)
- Starlette middleware ordering (LIFO) — https://www.starlette.io/middleware/#using-middleware
- 12-factor logs — https://12factor.net/logs (rationale for stdout-only sink)

### Tertiary (LOW confidence — flagged in Assumptions Log)
- A4: `diagnose=False` PII safety claim — unit test required to verify experimentally

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — loguru already in use, no new deps, all APIs stable since 0.6.x
- Architecture: **HIGH** — patterns are loguru-standard, codebase integration points verified by file inspection
- Pitfalls: **HIGH** — directly cited from project's own PITFALLS.md research
- F-string migration: **HIGH** — exact file/call counts verified by grep
- CI lint: **MEDIUM** — pre-commit pattern straightforward; GHA workflow does not yet exist (A6)

**Research date:** 2026-04-28
**Valid until:** 30 days (loguru is stable; revalidate if loguru 1.0 ships)
