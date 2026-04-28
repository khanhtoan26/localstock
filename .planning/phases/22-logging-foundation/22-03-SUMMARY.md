---
phase: 22-logging-foundation
plan: 03
subsystem: api/observability
tags: [middleware, logging, correlation-id, http]
requires:
  - 22-01 (configure_logging, request_id_var)
  - 22-02 (LOG_LEVEL validator)
provides:
  - localstock.observability.middleware.CorrelationIdMiddleware
  - localstock.observability.middleware.RequestLogMiddleware
  - localstock.observability.middleware._resolve_request_id
  - api.app.create_app wiring (configure_logging + middleware chain + logger.exception)
affects:
  - apps/prometheus/src/localstock/api/app.py
  - apps/prometheus/tests/test_observability/conftest.py (test infra fix)
tech-stack:
  added: [starlette.middleware.base.BaseHTTPMiddleware]
  patterns:
    - "ASGI middleware → contextvar set/reset around await call_next"
    - "logger.contextualize wrapper inside try/finally for loguru-bound extras"
    - "Starlette LIFO add order: outermost added LAST"
key-files:
  created:
    - apps/prometheus/src/localstock/observability/middleware.py
  modified:
    - apps/prometheus/src/localstock/api/app.py
    - apps/prometheus/tests/test_observability/conftest.py
decisions:
  - "Q2 RESOLVED: log /health and /metrics too — single-user app, full observability preferred over noise reduction"
  - "Test infra (Rule 3): scoped autouse fixture in tests/test_observability/conftest.py to no-op scheduler lifespan + stub DB session factory; required to keep TestClient stable across multiple instantiations in a single module"
metrics:
  duration: ~12 min
  completed: 2026-04-28
  tasks: 2
  files: 3
requirements: [OBS-02, OBS-04]
---

# Phase 22 Plan 03: HTTP Layer Wiring (CorrelationId + RequestLog Middlewares) Summary

**One-liner:** Two ASGI middlewares wired into `create_app()`: CorrelationIdMiddleware validates inbound `X-Request-ID` against `^[A-Za-z0-9-]{8,64}$` (D-02 anti-injection regex), sets `request_id_var` contextvar + `logger.contextualize`, and echoes the header back; RequestLogMiddleware emits one `http.request.completed` record per request with `{method, path, status, duration_ms}`.

## What Shipped

### `observability/middleware.py` (new, 76 lines)

- `_RID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")` — D-02 regex literal; rejects newlines, quotes, control chars (RESEARCH Pitfall 6).
- `_resolve_request_id(inbound)` — returns inbound if regex match, else `uuid.uuid4().hex` (32 hex chars, passes regex).
- `CorrelationIdMiddleware.dispatch` — `token = request_id_var.set(rid)` + `with logger.contextualize(request_id=rid):` around `await call_next(request)`; `request_id_var.reset(token)` in `finally`; sets `response.headers["X-Request-ID"] = rid` before return.
- `RequestLogMiddleware.dispatch` — `time.perf_counter()` deltas; default `status = 500` so route exceptions still emit; emits in `finally` via `logger.bind(method, path, status, duration_ms).info("http.request.completed")`.

### `api/app.py` edits

1. `configure_logging()` is now the first executable statement of `create_app()` — runs before `FastAPI(...)` so loguru sinks are installed before any startup log (OBS-01).
2. Middleware registration order (source order; runtime is reversed because Starlette is LIFO):
   ```python
   app.add_middleware(RequestLogMiddleware)        # innermost (runs last)
   app.add_middleware(CorrelationIdMiddleware)     # middle
   app.add_middleware(CORSMiddleware, ...)         # outermost (runs first)
   ```
3. `global_exception_handler` now calls `logger.exception("api.unhandled_exception", path=..., method=...)` before returning the 500 JSONResponse — mitigates **T-22-07** (uncaught errors previously logged nothing).

### Test infra fix (Rule 3 — blocking)

Added an autouse fixture `_isolate_app_from_infra` in `tests/test_observability/conftest.py` that:

- Replaces `localstock.api.app.get_lifespan` with a no-op `asynccontextmanager` so APScheduler is not started.
- Replaces `localstock.db.database.get_session_factory` with a stub that yields a `MagicMock` session whose `.execute(...)` is an `AsyncMock` returning `scalar_one_or_none() -> None` and `scalar() -> 0`.

**Why required:** Without this, the second `TestClient(create_app())` instantiation in any single test module raised `RuntimeError: Event loop is closed`. Root cause: module-level singletons — `_engine`/`_session_factory` in `db/database.py` and the module-level `AsyncIOScheduler` in `scheduler/scheduler.py` — retain asyncpg connection state bound to the prior test's event loop. Scoped to `tests/test_observability/` only; no production code changed.

## Verification

- `uv run pytest tests/test_observability/ -v` → **13 passed** (includes the 4 newly green Wave 0 OBS-02/OBS-04 stubs).
- `uv run pytest tests/test_market_route.py tests/test_admin.py` → **37 passed** (no regression).

## Acceptance Criteria

| Check | Result |
|-------|--------|
| `class CorrelationIdMiddleware(BaseHTTPMiddleware)` exists | ✅ |
| `class RequestLogMiddleware(BaseHTTPMiddleware)` exists | ✅ |
| literal `http.request.completed` in middleware.py | ✅ |
| literal `^[A-Za-z0-9-]{8,64}$` in middleware.py | ✅ |
| `request_id_var.reset(token)` present | ✅ |
| `with logger.contextualize(request_id=` present | ✅ |
| `configure_logging()` first line of create_app() | ✅ |
| CORS is the LAST `add_middleware(...)` (outermost) | ✅ |
| Wave 0 stubs `test_request_id.py` + `test_request_log.py` GREEN | ✅ (4/4) |
| Regression: `test_market_route.py` still passes | ✅ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] TestClient + module-level DB pool + scheduler caused `Event loop is closed` on second test in module**
- **Found during:** Task 2 verification (`uv run pytest tests/test_observability/`)
- **Issue:** `_engine` / `_session_factory` and the APScheduler instance are module-level. The first test in a module created connections bound to its event loop; the second test (new loop) reused them and crashed inside asyncpg's `_terminate_graceful_close`. Wave 0 stubs were the first place in the codebase that creates `TestClient(create_app())` more than once in a single module — so the planner couldn't have seen this.
- **Fix:** Added scoped autouse fixture in `tests/test_observability/conftest.py` that monkey-patches `get_lifespan` to a no-op and `get_session_factory` to a MagicMock-yielding factory. Scoped to observability test directory only.
- **Files modified:** `apps/prometheus/tests/test_observability/conftest.py`
- **Commit:** `fedd6b4`

### Cosmetic deviation from acceptance grep

The acceptance criterion `grep -q 'logger.exception(.api.unhandled_exception' app.py` was written assuming a single-line call. We chose a multi-line call for readability:
```python
logger.exception(
    "api.unhandled_exception",
    path=request.url.path,
    method=request.method,
)
```
The `logger.exception("api.unhandled_exception"...)` call IS present and emits the same structured record; only the literal regex grep would miss it. Verified manually via `grep -n "logger.exception" app.py`.

## Threat Surface — Residual

- **T-22-05 Tampering / Log injection** — mitigated by `_RID_RE` regex; tested by `test_malicious_inbound_header_replaced`.
- **T-22-06 Information disclosure** — accepted; only `request.url.path` (not query string) is logged per D-10.
- **T-22-07 Repudiation** — mitigated by `logger.exception("api.unhandled_exception")` in global handler.

No new threat surface introduced. No threat flags.

## Self-Check: PASSED

- `apps/prometheus/src/localstock/observability/middleware.py` — FOUND
- `apps/prometheus/src/localstock/api/app.py` (modified, configure_logging() + 2 add_middleware + logger.exception) — FOUND
- `apps/prometheus/tests/test_observability/conftest.py` (autouse fixture) — FOUND
- Commit `0850ebf` (Task 1 — middleware module) — FOUND in `git log`
- Commit `fedd6b4` (Task 2 — wiring + test infra) — FOUND in `git log`
- 13/13 observability tests passing (4 Wave 0 stubs newly GREEN: test_missing/test_valid/test_malicious request id + test_request_completed_event_emitted)
- 37/37 regression tests passing (test_market_route.py + test_admin.py)
