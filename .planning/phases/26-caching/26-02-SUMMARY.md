---
phase: 26-caching
plan: 02
subsystem: cache, observability/middleware
tags: [cache, telemetry, x-cache-header, prometheus, asgi-middleware, contextvar]
status: complete
type: tdd
wave: 1
requirements: [CACHE-07]
provides:
  - cache_prewarm_errors_total counter (D-08)
  - CacheHeaderMiddleware (X-Cache: hit|miss response header, P-4 verified)
  - middleware registered in api/app.py
requires:
  - cache_outcome_var ContextVar (26-01)
  - get_or_compute (26-01)
  - cache_compute_total counter (26-01, B1 ownership)
affects:
  - apps/prometheus/src/localstock/observability/metrics.py
  - apps/prometheus/src/localstock/cache/middleware.py
  - apps/prometheus/src/localstock/api/app.py
  - apps/prometheus/tests/test_cache/test_middleware.py
  - apps/prometheus/tests/test_cache/test_metrics_exposed.py
tech-stack:
  added: []
  patterns:
    - pure ASGI middleware (send-wrapper) for child→parent ContextVar read
    - ContextVar reset BEFORE invoking inner app (P-4 stale-outcome guard)
key-files:
  created:
    - apps/prometheus/src/localstock/cache/middleware.py
    - apps/prometheus/tests/test_cache/test_middleware.py
    - apps/prometheus/tests/test_cache/test_metrics_exposed.py
  modified:
    - apps/prometheus/src/localstock/observability/metrics.py
    - apps/prometheus/src/localstock/api/app.py
decisions:
  - 26-02 deviated from plan's BaseHTTPMiddleware recipe to pure ASGI (Rule 1 — required for child→parent contextvar visibility; the plan's mirror-of-CorrelationIdMiddleware approach is broken for this direction due to anyio Task isolation across `await call_next`). RESEARCH §7 P-4 explicitly flagged this; the plan still proposed the broken pattern.
metrics:
  duration: ~25 minutes
  tasks_completed: 2
  files_changed: 5
  commits: 4
  tests_added: 6
  completed_date: "2026-04-29"
---

# Phase 26 Plan 02: Cache Telemetry — Counters + X-Cache Middleware Summary

**One-liner:** Added `cache_prewarm_errors_total{cache_name}` Counter and pure-ASGI `CacheHeaderMiddleware` that reads `cache_outcome_var` (set by `get_or_compute`) to attach `X-Cache: hit|miss` response headers — closes CACHE-07 and lays the header infra needed by ROADMAP SC #1 / surface needed by SC #5.

## What Shipped

1. **`cache_prewarm_errors_total{cache_name}` Counter** — declared in `observability/metrics.py` via the existing `_register(...)` factory, in a region disjoint from 26-01's `cache_compute_total` (B1 ownership split — Wave-1 parallel-merge-safe).
2. **`CacheHeaderMiddleware`** — pure ASGI middleware (`__call__(scope, receive, send)`) that:
   - Resets `cache_outcome_var` to `None` BEFORE invoking the inner app (P-4: prevents stale-outcome propagation across requests in pooled tasks).
   - Wraps `send` so when `http.response.start` fires, it reads `cache_outcome_var` (set inside the handler by `get_or_compute`) and writes `X-Cache: <outcome>` only when non-None.
   - `finally`-resets the ContextVar token regardless of exception path.
3. **Wire-up in `api/app.py`** — registered after `CorrelationIdMiddleware` and before `CORSMiddleware`. Runtime LIFO order: CORS → CacheHeader → CorrelationId → Prom → RequestLog → handler.

## RED → GREEN Cycle

| Stage | Commit | Tests | Result |
|-------|--------|-------|--------|
| Task 1 RED | `3e81e90` | `test_metrics_exposed.py` (3 tests: registry surface, label name, cardinality bound) | 1 fail (missing `cache_prewarm_errors_total`) |
| Task 1 GREEN | `10b6f40` | same | 3/3 pass |
| Task 2 RED | `7660179` | `test_middleware.py` (3 tests: miss-then-hit, no header on uncached, contextvar reset) | ModuleNotFoundError |
| Task 2 GREEN | `267db01` | same | 3/3 pass |

**Final regression:** `tests/test_cache/` 15/15 + `tests/test_api/` 23/23 pass after 26-04's parallel work also landed. Full project: 582 passed (only pre-existing Phase-24 migration_downgrade failure remains — out of scope).

`uvx ruff check src/localstock/cache/ src/localstock/observability/metrics.py src/localstock/api/app.py` clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CacheHeaderMiddleware rewritten from `BaseHTTPMiddleware` to pure ASGI**

- **Found during:** Task 2 GREEN run.
- **Issue:** Plan's recipe subclassed `BaseHTTPMiddleware` and read `cache_outcome_var.get()` after `await call_next(request)`. Test `test_cached_route_emits_miss_then_hit` failed: `X-Cache` was `None`. Root cause: Starlette's `BaseHTTPMiddleware` runs the downstream app in a separate `anyio` Task, so `ContextVar` mutations made inside the handler are isolated and invisible to `dispatch` after `await call_next`. This is the well-known Starlette boundary issue and is exactly RESEARCH §7 P-4 — but the plan still proposed the same broken pattern by analogy with `CorrelationIdMiddleware` (which works for the *parent→child* direction only).
- **Fix:** Rewrote as a pure ASGI middleware (no `BaseHTTPMiddleware` subclass). `__call__(scope, receive, send)` awaits `self.app(scope, receive, send_wrapper)` directly in the same coroutine context — no Task boundary — so the ContextVar set by `get_or_compute` is visible inside `send_wrapper` when `http.response.start` is dispatched.
- **Files modified:** `apps/prometheus/src/localstock/cache/middleware.py`
- **Commit:** `267db01`

### Index-Hygiene Recovery (parallel-execution incident)

While committing the GREEN for Task 2, my `git commit` swept up files that the parallel 26-04 agent had staged but not yet committed in the shared (non-worktree) repository (`api/routes/market.py`, `api/routes/scores.py`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`). I caught this on the post-commit `git show --stat` check, performed `git reset --soft HEAD~1`, `git restore --staged` on the four foreign paths, and re-committed only the two files actually owned by 26-02 (`api/app.py`, `cache/middleware.py`). The 26-04 agent then landed its own commit `f208c4a` cleanly. No work was lost.

## Threat Flags

None. The threat model in PLAN.md (T-26-02-01..04) was upheld:

- T-26-02-02 (header tampering) — pure ASGI middleware writes via `MutableHeaders(scope=message)` which appends to / overwrites response headers; client-supplied request `X-Cache` headers are never read.
- T-26-02-03 (cardinality DoS) — `test_cardinality_bounded` asserts each new cache counter has `_labelnames == ("cache_name",)` (and `("cache_name", "reason")` for evictions). PASS.

## Self-Check: PASSED

**Files exist:**

- `apps/prometheus/src/localstock/cache/middleware.py` — FOUND (1759 bytes, pure ASGI)
- `apps/prometheus/tests/test_cache/test_middleware.py` — FOUND
- `apps/prometheus/tests/test_cache/test_metrics_exposed.py` — FOUND

**Counter declared:**

- `localstock_cache_prewarm_errors_total` registered in `observability/metrics.py` (verified by `test_all_cache_metrics_registered`).

**Commits exist (verified via `git log`):**

- `3e81e90` test(26-02) RED counter
- `10b6f40` feat(26-02) GREEN counter
- `7660179` test(26-02) RED middleware
- `267db01` feat(26-02) GREEN middleware + app.py wiring

All four commits carry the `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.
