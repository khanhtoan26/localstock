---
phase: 24
plan: "04"
subsystem: api
tags: [health, observability, OBS-14, fastapi, tdd]
requirements: [OBS-14]
status: complete
completed_at: "2026-04-29"
duration_minutes: 35
tasks_completed: 2
tasks_total: 2
files_created: 3
files_modified: 1
dependency_graph:
  requires:
    - apps/prometheus/src/localstock/db/database.py (get_engine, get_session)
    - apps/prometheus/src/localstock/db/models.py (PipelineRun, StockPrice)
  provides:
    - /health/live HTTP route
    - /health/ready HTTP route
    - /health/pipeline HTTP route
    - /health/data HTTP route
    - /health (deprecated alias) HTTP route
    - _ready_payload() helper (shared by /health/ready and /health alias)
    - _trading_days_lag() helper + _VN_HOLIDAYS_2025_2026 frozenset
  affects:
    - apps/prometheus/src/localstock/api/routes/health.py (rewritten)
tech_stack:
  added:
    - fastapi.Response (response-header / status-code injection in handlers)
    - asyncio.wait_for (2s bounded DB ping in /health/ready)
  patterns:
    - "Shared (status_code, body) tuple helper to keep alias byte-identical to /health/ready"
    - "raising=False monkeypatch on get_engine — allows RED phase before health.py imports the symbol"
    - "FastAPI dependency_overrides[get_session] yielding MagicMock(execute=AsyncMock(...)) — replaces real DB without a test database"
key_files:
  created:
    - apps/prometheus/tests/test_api/__init__.py
    - apps/prometheus/tests/test_api/conftest.py
    - apps/prometheus/tests/test_api/test_health_endpoints.py
  modified:
    - apps/prometheus/src/localstock/api/routes/health.py
decisions:
  - "Tests use mocked AsyncSession + dependency_overrides instead of a real test database; consistent with existing Phase 22+23 test_observability conftest pattern (project has no live test-DB fixture). Plan called this out as adaptable."
  - "mock_engine fixture patches localstock.api.routes.health.get_engine with raising=False so the same fixture works in both RED (symbol not yet imported) and GREEN."
  - "Static VN holiday set scoped to 2025–2026 only with TODO(backlog) marker — full vnstock-driven calendar deferred per D-03 + Open Q-2."
  - "/health alias intentionally NOT excluded from Phase 23-02 Instrumentator — leaving it visible in /metrics so dashboards can detect lingering callers before v1.7 removal."
metrics:
  duration_minutes: 35
  tests_added: 6
  tests_passing: 6
  full_suite_passing: 484
  loc_added_test: 197
  loc_added_impl_net: 153
commits:
  - hash: cf2c9ba
    type: test
    message: "test(api): RED tests for split health endpoints (Phase 24-04)"
  - hash: a87355c
    type: feat
    message: "feat(api): split /health into 4 probes + deprecated alias (Phase 24-04)"
---

# Phase 24 Plan 04: Health endpoints split — 4 probes + /health deprecated alias — Summary

**One-liner**: Replaced the single `/health` endpoint with 4 ops-ready probes (`/health/{live,ready,pipeline,data}`) plus a deprecated `/health` alias that mirrors `/health/ready` and emits `X-Deprecated`. Bounded `SELECT 1` ping (2s via `asyncio.wait_for`) drives 503 on DB failure. Closes OBS-14.

## What Was Built

### 1. RED — 6 OBS-14 integration tests (commit `cf2c9ba`)

Created `apps/prometheus/tests/test_api/` package (new directory; project had no `test_api` suite previously) with three files:

- `__init__.py` — package marker
- `conftest.py` — fixtures:
  - `app` — `create_app()` with the APScheduler lifespan stubbed to a no-op
  - `client` — `TestClient(app)`
  - `mock_session` — `MagicMock` whose `.execute` is an `AsyncMock`
  - `override_session` — applies `app.dependency_overrides[get_session]` and yields the mock for per-test configuration; clears overrides on teardown
  - `mock_engine` — patches `localstock.api.routes.health.get_engine` (with `raising=False` so RED works before the import lands) to a mock with `pool.{size,checkedin,checkedout,overflow}()` configured
- `test_health_endpoints.py` — 6 verbatim tests from VALIDATION.md OBS-14 rows:
  1. `test_health_live_returns_200`
  2. `test_health_ready_503_when_db_ping_fails` (mock execute raises `OperationalError`)
  3. `test_health_ready_200_with_pool_stats`
  4. `test_health_pipeline_returns_age_seconds` (1h-old `MagicMock` PipelineRun)
  5. `test_health_data_returns_freshness` (yesterday's max date)
  6. `test_health_legacy_alias_has_deprecation_header`

RED state confirmed: 5 tests fail with HTTP 404 (routes not defined yet), 1 fails on missing `X-Deprecated` header (pre-existing single `/health` returned a different body).

### 2. GREEN — rewrite `health.py` per RESEARCH §3 (commit `a87355c`)

`apps/prometheus/src/localstock/api/routes/health.py` rewritten end-to-end:

- **Module exports `router = APIRouter()`** — name preserved so `api/app.py:include_router(health_router)` works without edits.
- **5 routes registered** in this order: `/health/live` → `/health/ready` → `/health/pipeline` → `/health/data` → `/health` (alias).
- **`_ready_payload(session)` helper** returns `(status_code, body)` and is shared by `/health/ready` and `/health` so the alias is byte-identical.
- **DB ping**: `await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2.0)`. Catches `(TimeoutError, asyncio.TimeoutError, OperationalError, SQLAlchemyError)` → 503 with `error_type=type(exc).__name__`.
- **Pool stats**: `engine.pool.{size, checkedin, checkedout, overflow}()`.
- **`/health/data`**: `func.max(StockPrice.date)` + `_trading_days_lag(latest, today)` excluding weekends + the static `_VN_HOLIDAYS_2025_2026` frozenset (20 dates covering Tết + national holidays for 2025–2026). Marked with `TODO(backlog): full VN trading calendar — D-03 + Open Q-2`.
- **`/health` alias**: sets `response.headers["X-Deprecated"] = "use /health/ready instead"` after copying the ready payload + status code.
- **Read-only**: every probe is `select`/`text("SELECT 1")` — no INSERT/UPDATE/DELETE. No `.inc()` / `.observe()` calls inside this file (HTTP histogram comes from Phase 23-02 Instrumentator; D-03 says health probes stay clean).
- **`/health/live` performs zero I/O** — no `Depends(get_session)`, just `return {"status": "alive"}`. This is also the only path excluded from the Phase 23-02 Instrumentator handler regex.

## Verification

- `uv run pytest tests/test_api/test_health_endpoints.py -q` → **6/6 passed** (0.90s).
- `uv run pytest tests/test_api/ tests/test_observability/ tests/test_admin.py tests/test_market_route.py tests/test_api_dashboard.py -q` → **86/86 passed**.
- `uv run pytest -q --ignore=tests/test_phase5` (full prometheus suite) → **484/484 passed** in 22.19s — zero regressions.
- `bash scripts/lint-no-fstring-logs.sh` → `OK: zero f-string log calls`.
- Router shape probe:
  ```
  OK ['/health/live', '/health/ready', '/health/pipeline', '/health/data', '/health']
  ```

## Deviations from Plan

**None.** Plan executed exactly as written, with one explicitly-anticipated adaptation: the planner noted "Adapt fixture names to match the project's existing conftest" because the example RED test referenced `db_session` (a real-DB fixture) that the project does not have. Adopted the project's mocked-session pattern (matching `tests/test_observability/conftest.py`) — this is the documented adaptation, not a deviation.

## Authentication Gates

None encountered. Pure code change, no external services touched.

## Known Stubs

`_VN_HOLIDAYS_2025_2026` is intentionally a minimal static set (20 dates) covering Solar New Year, Tết, Hùng Kings Day, Reunification Day, Labour Day, and National Day for 2025 and 2026 only. This is a deliberate scope decision per D-03 / Open Q-2 — full Vietnamese trading calendar (e.g. via `vnstock.trading_dates()` or a maintained JSON manifest) is in the backlog. Marked inline with `TODO(backlog): full VN trading calendar — D-03 + Open Q-2`. Tests verify shape (`stale: bool`, `trading_days_lag: int`) rather than calendar accuracy.

## TDD Gate Compliance

- ✅ RED gate: `test(api): RED tests for split health endpoints (Phase 24-04)` (`cf2c9ba`) — 6 tests added, all failing on `master` HEAD before GREEN.
- ✅ GREEN gate: `feat(api): split /health into 4 probes + deprecated alias (Phase 24-04)` (`a87355c`) — same 6 tests now passing, full suite green.
- REFACTOR gate: not needed — implementation lifted directly from RESEARCH §3 with documentation polish.

## Self-Check: PASSED

- ✅ `apps/prometheus/tests/test_api/__init__.py` — exists
- ✅ `apps/prometheus/tests/test_api/conftest.py` — exists
- ✅ `apps/prometheus/tests/test_api/test_health_endpoints.py` — exists, 6 tests
- ✅ `apps/prometheus/src/localstock/api/routes/health.py` — rewritten, 5 routes registered
- ✅ Commit `cf2c9ba` (RED) — present in `git log`
- ✅ Commit `a87355c` (GREEN) — present in `git log`
- ✅ Lint `scripts/lint-no-fstring-logs.sh` — clean
- ✅ Full suite (484 tests) — passing, zero regressions
