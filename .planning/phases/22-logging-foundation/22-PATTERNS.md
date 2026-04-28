# Phase 22: Logging Foundation — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 5 NEW + 5 MODIFY-infra + ~33 MODIFY-fstring + 3 NEW test files + 1 NEW pre-commit/CI
**Analogs found:** 8 / 11 distinct file roles (3 roles have no in-repo analog — see "No Analog Found")

> Authoritative file layout follows `22-RESEARCH.md` §"Recommended Project Structure". The `pattern_mapping_context` mentioned alternate paths (e.g. `api/middleware/request_log.py`) — RESEARCH.md wins: middleware lives in `localstock/observability/middleware.py`.

---

## File Classification

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `localstock/observability/__init__.py` | NEW | package-init | n/a | `localstock/api/__init__.py` (any pkg `__init__.py` in repo) | role-match |
| `localstock/observability/logging.py` | NEW | config / process-bootstrap | event-driven (emit-time patcher) | `localstock/scheduler/scheduler.py` (singleton + lifespan-init pattern) | partial (closest singleton-bootstrap analog) |
| `localstock/observability/context.py` | NEW | utility (contextvars) | event-driven | none — first contextvars module in repo | **no analog** |
| `localstock/observability/middleware.py` | NEW | middleware (ASGI) | request-response | `localstock/api/app.py` lines 33-39 (CORS wiring) — usage only; no in-repo BaseHTTPMiddleware subclass exists | partial (usage analog only) |
| `localstock/api/app.py` | MODIFY | app-factory | request-response | itself (extend existing `create_app()`) | exact (self-edit) |
| `localstock/scheduler/scheduler.py` | MODIFY | scheduler / lifespan | event-driven | itself + `services/pipeline.py` | exact |
| `localstock/services/pipeline.py` | MODIFY | service (orchestrator) | batch / async-gather | itself (wrap existing `run_full`) | exact |
| `localstock/config.py` | MODIFY | config (pydantic-settings) | request-response | itself — `database_url` validator at lines 27-33 | exact |
| ~33 src files (crawlers/repos/services/...) | MODIFY | various | various | one another — mechanical f-string→positional sweep | exact (sample below) |
| `apps/prometheus/tests/conftest.py` | MODIFY | test-fixture | event-driven | itself (extend existing fixtures lines 9-21) | exact |
| `apps/prometheus/tests/test_observability/*.py` | NEW | test | request-response | `apps/prometheus/tests/test_market_route.py` (FastAPI TestClient + class layout) | role-match |
| `.pre-commit-config.yaml` | NEW | CI/lint | n/a | none — no existing pre-commit / workflow files | **no analog** |
| `scripts/check_no_fstring_log.sh` (optional) | NEW | shell | n/a | none — no `scripts/` dir exists | **no analog** |

---

## Pattern Assignments

### `localstock/observability/logging.py` (config / bootstrap)

**Analogs:** `localstock/scheduler/scheduler.py` (module-singleton + idempotent lifespan init) + `localstock/config.py` (settings access pattern). No in-repo precedent for `loguru.add()` / `logger.configure(patcher=...)` / `InterceptHandler` — pull verbatim from `22-RESEARCH.md` §"Pattern 1: Idempotent configure_logging()" lines 208-334.

**Imports pattern** (mirror `scheduler.py:1-16` style — module docstring first, `from __future__`-OK, stdlib → third-party → `localstock.*`):
```python
"""Loguru configuration — idempotent, JSON-stdout, redaction-aware."""
from __future__ import annotations
import logging, os, re, sys
from typing import Any
from loguru import logger
from localstock.config import get_settings
from localstock.observability.context import request_id_var, run_id_var
```

**Settings access pattern** (copy from `scheduler.py:31`):
```python
settings = get_settings()
level = settings.log_level.upper()
```

**Idempotency-guard pattern** (no in-repo precedent for module-flag; use the canonical):
```python
_configured = False
def configure_logging() -> None:
    global _configured
    if _configured: return
    logger.remove()  # always remove first — Pitfall 5
    ...
    _configured = True
```

**Source for `_redaction_patcher`, `InterceptHandler`, sink config** → copy verbatim from `22-RESEARCH.md` lines 240-333. No codebase analog exists.

---

### `localstock/observability/context.py` (contextvars)

**Analog:** none in repo. `grep -rn "ContextVar\|contextvars" apps/prometheus/src` returns 0 matches. Pull from `22-RESEARCH.md` §"Pattern 2" lines 340-361:

```python
from __future__ import annotations
from contextvars import ContextVar
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
def get_request_id() -> str | None: return request_id_var.get()
def get_run_id() -> str | None: return run_id_var.get()
```

---

### `localstock/observability/middleware.py` (CorrelationIdMiddleware, RequestLogMiddleware)

**Analog (usage only):** `localstock/api/app.py` lines 33-39 — `app.add_middleware(CORSMiddleware, ...)`. No `BaseHTTPMiddleware` subclass exists in repo today.

**Wiring conventions to mirror** (`api/app.py:33-39`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Class body** → copy verbatim from `22-RESEARCH.md` §"Request ID middleware (full code)" lines 451-515 (`_RID_RE`, `_resolve_request_id`, `CorrelationIdMiddleware`, `RequestLogMiddleware`).

**Module docstring style** (mirror `scheduler.py:1-7` — Vietnamese-OK, references decisions):
```python
"""Correlation ID + request logging ASGI middlewares.

Wire order (CRITICAL — Starlette LIFO):
    CORS  →  CorrelationId  →  RequestLog  →  routers
Per CONTEXT.md D-02 / D-04 / D-09.
"""
```

---

### `localstock/api/app.py` (MODIFY — wire middlewares + configure_logging)

**Self-analog (current state, lines 21-60):**
```python
def create_app() -> FastAPI:
    app = FastAPI(title="LocalStock API", ..., lifespan=get_lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    app.include_router(health_router, tags=["health"])
    ...
```

**Edits required:**
1. Add `configure_logging()` call as **first line** of `create_app()` (before `FastAPI(...)`).
2. Add 2× `app.add_middleware()` calls AFTER existing CORS but BEFORE routers — order matters (Starlette LIFO):
   ```python
   app.add_middleware(RequestLogMiddleware)        # innermost (runs last)
   app.add_middleware(CorrelationIdMiddleware)     # runs before RequestLog
   app.add_middleware(CORSMiddleware, ...)         # outermost — KEEP existing
   ```
   ⚠️ Because `add_middleware` is LIFO, the **last added runs first**. Existing CORS is added first today — that's fine if we add Correlation/RequestLog **after** CORS in source, they wrap closer to the route.
3. Existing `global_exception_handler` (lines 41-47) currently swallows the exception silently. **Add** `logger.exception("api.unhandled_exception")` before `return JSONResponse(...)` (per CONTEXT.md "Established Patterns" note).

**Imports to add** (mirror existing import block style — top of file, alphabetical-ish):
```python
from localstock.observability.logging import configure_logging
from localstock.observability.middleware import CorrelationIdMiddleware, RequestLogMiddleware
```

---

### `localstock/scheduler/scheduler.py` (MODIFY — bind run_id, fix f-strings, defensive `configure_logging`)

**Self-analog (current `daily_job`, lines 33-41):**
```python
async def daily_job():
    logger.info("Scheduled daily pipeline starting...")
    service = AutomationService()
    try:
        result = await service.run_daily_pipeline()
        logger.info(f"Scheduled pipeline result: status={result['status']}")  # ← f-string violation
    except Exception as e:
        logger.error(f"Scheduled pipeline failed: {e}")                        # ← f-string violation
```

**Edits required (per RESEARCH §"Pipeline run_id propagation" lines 575-585 + D-05):**
```python
async def daily_job():
    logger.info("scheduler.daily.start")
    service = AutomationService()
    try:
        result = await service.run_daily_pipeline()
        logger.info("scheduler.daily.result", status=result["status"])
    except Exception:
        logger.exception("scheduler.daily.failed")  # captures stack
```

Also fix lines 67-70 (the `logger.info(f"Scheduler configured: ...")` f-string) → positional/kwargs.

**Lifespan defensive call** (mirror existing pattern at lines 81-85):
```python
@asynccontextmanager
async def get_lifespan(app: FastAPI):
    from localstock import configure_ssl, configure_vnstock_api_key
    from localstock.observability.logging import configure_logging
    configure_logging()  # NEW — idempotent, defensive
    configure_ssl()
    configure_vnstock_api_key()
    setup_scheduler()
    scheduler.start()
    logger.info("scheduler.started")  # was "APScheduler started"
    yield
    scheduler.shutdown()
    logger.complete()  # NEW — drain enqueued records on shutdown (RESEARCH Open Q3)
    logger.info("scheduler.stopped")
```

---

### `localstock/services/pipeline.py` (MODIFY — wrap run_full body in contextualize)

**Self-analog (current `run_full` lines 49-70):**
```python
async def run_full(self, run_type: str = "daily") -> PipelineRun:
    run = PipelineRun(started_at=datetime.now(UTC), status="running", run_type=run_type)
    self.session.add(run)
    await self.session.commit()                # run.id now populated
    try:
        try:
            count = await self.stock_repo.fetch_and_store_listings()
            logger.info(f"Step 1: Stored {count} HOSE stock listings")  # ← f-string
        except Exception as e:
            logger.warning(f"Step 1: Listing fetch failed ({e}), using existing DB stocks")  # ← f-string
        ...
```

**Edit pattern** (RESEARCH §4 lines 543-569):
```python
await self.session.commit()
run_id = str(run.id)
token = run_id_var.set(run_id)
try:
    with logger.contextualize(run_id=run_id):
        logger.info("pipeline.run.started", run_type=run_type)
        try:
            # …existing Step 1..N logic, with f-strings converted…
            count = await self.stock_repo.fetch_and_store_listings()
            logger.info("pipeline.listings.stored", count=count, step=1)
            ...
        finally:
            logger.info("pipeline.run.completed", status=run.status)
    return run
finally:
    run_id_var.reset(token)
```

**Imports to add:**
```python
from localstock.observability.context import run_id_var
```

(`from loguru import logger` already present line 17.)

---

### `localstock/config.py` (MODIFY — add LOG_LEVEL validator)

**Self-analog (existing validator pattern, lines 27-33):**
```python
@field_validator("database_url", mode="before")
@classmethod
def ensure_asyncpg_driver(cls, v: str) -> str:
    if isinstance(v, str) and (v.startswith("postgresql://") or v.startswith("postgres://")):
        v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
    return v
```

**Existing `log_level` field (line 39):** `log_level: str = "INFO"` — already present, no change to default.

**Edit (add validator, mirror existing style verbatim):**
```python
@field_validator("log_level", mode="before")
@classmethod
def normalize_log_level(cls, v: str) -> str:
    allowed = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
    if not isinstance(v, str):
        raise ValueError("log_level must be a string")
    upper = v.upper()
    if upper not in allowed:
        raise ValueError(f"log_level must be one of {sorted(allowed)}, got {v!r}")
    return upper
```

---

### F-string log migration (~33 files, 103 calls)

**Analog (representative migration):** `crawlers/price_crawler.py:62`

**Before:**
```python
logger.info(f"Fetched {len(df)} price rows for {symbol} ({start} to {end})")
```

**After (kwargs form — RESEARCH §"F-string migration examples" lines 612-619):**
```python
logger.info("crawl.prices.fetched", symbol=symbol, rows=len(df), start=str(start), end=str(end))
```

**Mechanical rules (apply uniformly across all 33 files):**
| Source pattern | Replacement |
|---|---|
| `logger.X(f"...{var}...")` (informational) | `logger.X("event.name", var=var, ...)` — event names dot-separated, ASCII |
| `logger.error(f"... {e}")` inside `except` | `logger.exception("event.name")` — captures stack |
| `logger.warning(f"Failed to X for {sym}: {e}")` | `logger.warning("event.name", symbol=sym, error=str(e))` |
| Vietnamese in message OK; **event keys must be ASCII** for grep-ability |

**Affected file list** (RESEARCH §"File-by-File Impact" lines 712-715): 7 crawlers, 12 repositories, 8 services, 4 other (`ai/client.py`, `analysis/technical.py`, `notifications/telegram.py`, `scheduler/scheduler.py`).

**Verification command** (post-migration must return 0):
```bash
grep -rEln 'logger\.[a-z]+\(\s*f["\x27]' apps/prometheus/src apps/prometheus/tests | wc -l
```

---

### `apps/prometheus/tests/conftest.py` (MODIFY)

**Self-analog (existing fixture style, lines 9-21):**
```python
@pytest.fixture
def sample_ohlcv_df():
    return pd.DataFrame({...})
```

**Edits required** — append two new fixtures (RESEARCH §8 lines 654-694):
```python
import os, pytest
from loguru import logger

os.environ.setdefault("PYTEST_CURRENT_TEST", "init")  # ensure detection at first import

@pytest.fixture(scope="session", autouse=True)
def _configure_test_logging():
    os.environ["LOG_LEVEL"] = "DEBUG"
    from localstock.observability.logging import configure_logging
    configure_logging()
    yield
    logger.complete()

@pytest.fixture
def loguru_caplog():
    records: list[dict] = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG", format="{message}")
    class _Capture:
        @property
        def records(self): return records
    yield _Capture()
    logger.remove(sink_id)
```

Existing data-fixture style untouched.

---

### `apps/prometheus/tests/test_observability/*.py` (NEW — 8 test files)

**Analog:** `apps/prometheus/tests/test_market_route.py` lines 1-30 (FastAPI TestClient + class-based grouping).

**Imports pattern (copy from analog):**
```python
"""Tests for Phase 22: Observability — <area>."""
from unittest.mock import AsyncMock, patch
from localstock.api.app import create_app
```

**Class layout pattern:**
```python
class TestRedactionPatcher:
    def test_url_credentials_redacted(self): ...
    def test_token_extra_redacted(self, capsys): ...
```

**Files to create** (RESEARCH §"Wave 0 Gaps" lines 819-829):
- `__init__.py` (empty)
- `test_json_sink.py` — OBS-01 (round-trip + datetime/Decimal/UUID + exception traceback)
- `test_correlation.py` — OBS-02 (TestClient: valid header / invalid header / missing header)
- `test_run_id.py` — OBS-03 (mock `Pipeline.run_full`, verify nested logs carry `run_id`)
- `test_request_log.py` — OBS-04 (assert `http.request.completed` structured fields)
- `test_redaction.py` — OBS-05 (sample in RESEARCH §5 lines 590-608)
- `test_idempotent.py` — Pitfall 5 regression (call `configure_logging()` 2× → exactly 1 sink)
- `test_diagnose_no_pii.py` — Pitfall 17 regression
- `test_async_sink.py` — smoke (optional)

**Sample test body (copy from RESEARCH §5):**
```python
def test_token_extra_redacted(capsys):
    configure_logging()
    logger.bind(telegram_bot_token="123:ABC", symbol="VNM").info("telegram.send")
    out = capsys.readouterr().out
    record = json.loads(out.strip().splitlines()[-1])
    assert record["record"]["extra"]["telegram_bot_token"] == "***REDACTED***"
    assert record["record"]["extra"]["symbol"] == "VNM"  # non-sensitive (D-10)
```

---

## Shared Patterns

### Loguru import (apply to ALL src + middleware + observability files)
**Source:** `localstock/scheduler/scheduler.py:14`
```python
from loguru import logger
```
Single global singleton — never `logging.getLogger(__name__)` (CONTEXT.md anti-pattern).

### Settings access (apply to logging.py, any new bootstrap code)
**Source:** `localstock/scheduler/scheduler.py:16, 31`
```python
from localstock.config import get_settings
settings = get_settings()  # cached via @lru_cache
```

### Module docstring (apply to ALL new files)
**Source:** `localstock/scheduler/scheduler.py:1-7`
```python
"""<one-line summary>.

Per <CONTEXT.md D-XX>: <decision recap>.
Per <RESEARCH.md §X>: <approach recap>.
"""
```
Vietnamese OK in body comments/messages; English+ASCII for event keys.

### Pydantic field_validator (apply to config.py edits)
**Source:** `localstock/config.py:27-33`
```python
@field_validator("<field>", mode="before")
@classmethod
def <name>(cls, v: <type>) -> <type>:
    ...
```

### Test file layout (apply to all NEW test files)
**Source:** `apps/prometheus/tests/test_market_route.py:1-30`
- Top-level docstring naming the phase
- Imports: stdlib → unittest.mock → localstock
- `class TestX:` groupings with method names `test_<behavior>`

---

## No Analog Found

| File | Role | Reason | Source to copy from |
|---|---|---|---|
| `localstock/observability/context.py` | contextvars utility | No `ContextVar` usage anywhere in repo | RESEARCH §"Pattern 2" lines 340-361 |
| `localstock/observability/logging.py` core (patcher, InterceptHandler, sinks) | logger config | No prior loguru config code; current code uses default config | RESEARCH §"Pattern 1" lines 208-334 |
| `localstock/observability/middleware.py` `BaseHTTPMiddleware` subclass | ASGI middleware class | Repo only uses 3rd-party `CORSMiddleware`; no in-repo subclass | RESEARCH §"Request ID middleware" lines 451-515 |
| `.pre-commit-config.yaml` | CI/lint config | No pre-commit infra in repo | RESEARCH §7 lines 621-634 |
| `scripts/check_no_fstring_log.sh` | shell utility | No `scripts/` dir in repo | RESEARCH §7 + GHA snippet lines 638-647 |
| `.github/workflows/lint.yml` (optional) | CI workflow | `.github/workflows/` does not exist [VERIFIED] | RESEARCH §7 + Open Question A6 — planner may defer |

---

## Metadata

**Analog search scope:**
- `apps/prometheus/src/localstock/` (all subpackages)
- `apps/prometheus/tests/`
- repo root for `.pre-commit-config.yaml`, `.github/workflows/`, `scripts/`

**Files scanned:** 14 directly read (CONTEXT, RESEARCH, app.py, scheduler.py, config.py, conftest.py, pipeline.py, test_market_route.py, copilot-instructions.md, package listings × 5).

**Pattern extraction date:** 2026-04-28
