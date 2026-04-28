# Phase 22: Logging Foundation - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Mọi log line backend trở thành JSON cấu trúc (loguru `serialize=True` + `enqueue=True`), gắn `request_id` (HTTP) và `run_id` (pipeline) qua contextvar, secret/credentials bị redact tự động, và CI có lint chặn regression f-string log calls. Không thay đổi behavior nghiệp vụ — pure observability infrastructure.

**In scope:** OBS-01 → OBS-06 từ REQUIREMENTS.md.
**Out of scope:** Metrics (Phase 23), `/health/*` split (Phase 24), `@observe` decorator (Phase 24), DB query timing (Phase 24).

</domain>

<decisions>
## Implementation Decisions

### Log Output

- **D-01 Sinks:** stdout JSON-only trong production (`logger.add(sys.stdout, serialize=True, enqueue=True, level=...)`); pretty colored format khi stderr là TTY (dev DX qua `sys.stderr.isatty()` check). KHÔNG file rotation — process supervisor/Docker/systemd capture stdout là chuẩn 12-factor.
- **D-06 Log level:** `LOG_LEVEL` env var qua Pydantic Settings (default `INFO`; tests pin `DEBUG` qua fixture). Không có runtime endpoint — single-user app, restart đủ.

### Correlation IDs

- **D-02 Request ID:** Mỗi HTTP request — `CorrelationIdMiddleware` set contextvar `request_id`. Source priority: (1) trust `X-Request-ID` header nếu match `^[A-Za-z0-9-]{8,64}$`, (2) fallback generate `uuid.uuid4().hex`. Echo back qua response header `X-Request-ID`. Helios cùng origin nên CORS-safe.
- **D-03 Pipeline run_id:** Wrap `run_daily_pipeline` body trong `with logger.contextualize(run_id=str(pipeline_run.id))`. Reuse `PipelineRun.id` (đã persist), không sinh ID riêng. Mọi log emit trong pipeline (kể cả từ subtask qua `asyncio.gather`) inherit qua contextvar.
- **D-02b Contextvar over Depends:** request_id/run_id dùng `contextvars.ContextVar` (loguru `contextualize` wraps standard contextvar) — survive `asyncio.gather`, visible trong scheduler jobs, không cần FastAPI `Depends` injection.

### Redaction

- **D-04 Strategy:** Deny-list patcher gắn vào loguru qua `logger.patcher`. Quét `record["extra"]` keys + record message:
  - Sensitive keys (case-insensitive): `token`, `api_key`, `password`, `secret`, `authorization`, `database_url`, `telegram_bot_token`, `bot_token`
  - Regex over message: URL credentials `://[^/\s]+:[^@\s]+@` → `://***:***@`
  - Replace với literal `***REDACTED***`
- **D-10 PII clarification:** Telegram `chat_id`, stock `symbol`, user IP coi là **non-sensitive** trong app này (single-user, không GDPR/PII surface). Document trong `observability/logging.py` module docstring để contributor sau không over-redact.

### Migration & Lint

- **D-05 Existing call sites:** Hard-cut day one. Audit + fix tất cả ~40 files dùng `from loguru import logger` để loại bỏ f-string violations. Loguru hỗ trợ positional args (`logger.info("user {} did {}", user, action)`) — sửa dễ. Các call site đã structured giữ nguyên.
- **D-07 CI enforcement:** `grep`-based check, không Ruff custom rule (Ruff không có native rule cho loguru f-string). Hai layer:
  1. **Pre-commit hook** trong `.pre-commit-config.yaml` — fast-fail khi commit local
  2. **GitHub Actions step** trong existing CI workflow — định kỳ + PR gate

  Pattern (negated success): `! grep -rE 'logger\.(debug|info|warning|error|critical|exception|trace|success)\(\s*f["\x27]' apps/prometheus/src/ apps/prometheus/tests/`. Escape comment: `# noqa: log-fstring` cho rare cases.

### Test Environment

- **D-08 enqueue + pytest:** `enqueue=True` chạy logger trong background thread → có thể hang teardown. Pattern: detect `os.environ.get("PYTEST_CURRENT_TEST")` trong logging init; nếu present → `enqueue=False`. Backup: conftest fixture gọi `logger.complete()` trong finalizer.
- **D-08b Capturing logs in tests:** Dùng loguru `LogCapture` fixture (sample trong loguru docs). Document pattern trong `tests/conftest.py`.

### Stdlib Logging Bridge

- **D-09 InterceptHandler:** uvicorn / SQLAlchemy / APScheduler / asyncpg emit qua stdlib `logging` module. Cài `InterceptHandler` (loguru recipe) vào root stdlib logger → mọi log đi qua loguru sink chung. Một nguồn JSON, một format. Áp dụng trong `observability/logging.py:configure_logging()` gọi từ `create_app()` lifespan + scheduler startup.

### the agent's Discretion

- File layout cụ thể trong `localstock/observability/` (planner quyết: `logging.py`, `middleware.py`, hoặc tách thêm).
- Tên decorator/helper functions exact (chỉ cần signature stable).
- Pre-commit hook implementation detail (bash inline vs script file).
- Test fixture naming conventions.

### Folded Todos

(None — không có pending todos match Phase 22 scope.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"Observability — Logging (Phase A)" — OBS-01..06 acceptance criteria
- `.planning/ROADMAP.md` Phase 22 row — goal + success criteria + dependencies

### Research (v1.5 milestone)
- `.planning/research/SUMMARY.md` §"Phase A — Logging Foundation" — build order rationale + lint gate spec
- `.planning/research/STACK.md` §"Already-installed, no upgrade needed" — loguru version + recommended config (`serialize=True`, `enqueue=True`, `contextualize()`)
- `.planning/research/ARCHITECTURE.md` §"localstock/observability/" + §"Pattern: contextvar over Depends" — package layout + correlation ID approach
- `.planning/research/PITFALLS.md` Pitfalls 4 (f-string defeat structure), 5 (loguru double-init), 16 (sync sink blocks loop), 17 (PII leakage), 20 (un-serializable fields fail batch)

### Project
- `.planning/PROJECT.md` §"Constraints" — local-first, single-user, free-tier (no external log shippers)
- `.planning/PROJECT.md` §"Key Decisions" — existing loguru choice carried forward

### External docs (web)
- Loguru API reference — https://loguru.readthedocs.io/en/stable/api/logger.html (specifically `serialize`, `enqueue`, `contextualize`, `patcher`, `complete`)
- Loguru recipe — InterceptHandler for stdlib bridge: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Loguru already used in 40+ files** — `from loguru import logger` import pattern established. Phase 22 không thêm dep, chỉ configure global logger + add middleware/patcher.
- **Pydantic Settings (`config.py`)** — đã có pattern env-var loading; thêm `LOG_LEVEL: str = "INFO"` field đơn giản.
- **FastAPI lifespan** (`scheduler/scheduler.py:get_lifespan`) — entry point để `configure_logging()` chạy sớm.
- **Existing `create_app()` factory** (`api/app.py`) — chỗ wire middleware. Trật tự: CORS → CorrelationId → RequestLog → routers.
- **APScheduler `get_lifespan`** — chỗ wrap pipeline jobs với `logger.contextualize(run_id=...)`.

### Established Patterns

- **Single source of truth — `loguru.logger` global singleton.** Không có per-module logger factory; phù hợp với loguru philosophy.
- **f-string usage hiện tại trong logs** — vài files dùng f-string (cần audit). Đây là target của OBS-06 lint.
- **No existing middleware** — chỉ có `CORSMiddleware`. Phase 22 thêm 2 (CorrelationId, RequestLog).
- **No existing exception handler logs** — global handler ở `app.py` swallow exception. Cần verify Phase 22 không break existing behavior nhưng log exception trước khi return 500.

### Integration Points

- **`apps/prometheus/src/localstock/observability/__init__.py`** (NEW) — package root.
- **`apps/prometheus/src/localstock/observability/logging.py`** (NEW) — `configure_logging()`, redaction patcher, `InterceptHandler`.
- **`apps/prometheus/src/localstock/observability/middleware.py`** (NEW) — `CorrelationIdMiddleware`, `RequestLogMiddleware`.
- **`apps/prometheus/src/localstock/observability/context.py`** (NEW) — contextvars `request_id`, helper accessors.
- **`apps/prometheus/src/localstock/api/app.py`** (MODIFY) — wire middlewares + `configure_logging()` early.
- **`apps/prometheus/src/localstock/scheduler/scheduler.py`** (MODIFY) — wrap pipeline run với contextualize.
- **`apps/prometheus/src/localstock/services/automation_service.py` / `services/pipeline.py`** (MODIFY) — verify `run_id` propagation; refactor any f-string logger calls.
- **`apps/prometheus/src/localstock/config.py`** (MODIFY) — add `LOG_LEVEL` setting + validate.
- **All other files using `from loguru import logger` with f-strings** (MODIFY) — convert to positional args (~30-40 LOC across many files; mechanical).
- **`.pre-commit-config.yaml`** (MODIFY/CREATE) — add f-string-log gate.
- **`.github/workflows/*.yml`** (MODIFY) — add CI grep step (or hook into existing lint job).
- **`apps/prometheus/tests/conftest.py`** (MODIFY) — `enqueue=False` in test env + log capture fixture.

### Anti-Patterns (Avoid)

- ❌ Per-module `logger = logging.getLogger(__name__)` — loguru is global singleton.
- ❌ Calling `configure_logging()` more than once → "Duplicated handler" error (Pitfall 5). Use idempotent guard.
- ❌ Synchronous I/O sink without `enqueue=True` blocks event loop on disk-slow filesystem (Pitfall 16).
- ❌ Logging dict containing non-JSON-serializable values (datetime in many places, Decimal, custom objects) → batch fails. Use `default=str` fallback or explicit `.isoformat()`.

</code_context>

<specifics>
## Specific Ideas

- **Decorator name preference:** `configure_logging()` — không `setup_logging` / `init_logging`. Idempotent.
- **Contextvar names:** `request_id_var`, `run_id_var` (suffix `_var` để phân biệt với raw value).
- **Header name:** `X-Request-ID` (de facto standard; Helios nên expose qua axios/fetch wrapper).
- **JSON record top-level keys:** mặc định loguru `serialize=True` xuất `{record: {time, level, message, extra, ...}}`. Acceptable cho v1.5.
- **Vietnamese log messages OK** — codebase comments/messages tiếng Việt là norm. JSON encoding xử lý UTF-8 đúng.

</specifics>

<deferred>
## Deferred Ideas

- **Log shipping to external service** (Loki, Grafana Cloud, Datadog) — local-first constraint; defer indefinitely.
- **Log sampling for high-volume endpoints** — không có endpoint volume cao trong app cá nhân.
- **Distributed trace IDs (W3C Trace Context)** — single-process, không có cross-service hops; defer cho đến khi multi-service.
- **PII compliance audit (GDPR/CCPA)** — single-user, không phải concern.
- **Log replay / time-travel debugging** — overkill.
- **Per-route log level overrides** — `LOG_LEVEL` global đủ.

</deferred>

---

*Phase: 22-logging-foundation*
*Context gathered: 2026-04-28*
