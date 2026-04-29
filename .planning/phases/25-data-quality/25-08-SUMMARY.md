---
phase: 25-data-quality
plan: 08
subsystem: api/health
tags: [DQ-07, SC-5, health, freshness, trading-calendar, phase-25-closure]
requirements: [DQ-07]
closes_sc: [5]
dependency_graph:
  requires:
    - 25-01 (Settings.dq_stale_threshold_sessions; RED scaffolds in tests/test_api/test_health_data_freshness.py)
    - Phase 24 (_VN_HOLIDAYS_2025_2026, _is_trading_day, _trading_days_lag in api/routes/health.py)
  provides:
    - "/health/data data_freshness block { last_trading_day, max_data_date, sessions_behind, status, threshold_sessions }"
    - _last_trading_day_on_or_before(today) helper for VN trading calendar
  affects:
    - apps/prometheus/src/localstock/api/routes/health.py
    - apps/prometheus/tests/test_api/test_health_data_freshness.py
tech_stack:
  added: []
  patterns:
    - "Local get_settings() import inside route handler — lets tests cache_clear() + monkeypatch.setenv at request time without module reload"
    - "Bounded backwards-walk loop (cap=20) for last-trading-day calculation — handles worst-case Tet holiday cluster + weekend"
    - "Dual freshness signaling: legacy top-level `stale: bool` (Phase 24 hard-coded > 1) PRESERVED for back-compat (D-05); new `data_freshness.status` uses configurable threshold for new clients"
key_files:
  created: []
  modified:
    - apps/prometheus/src/localstock/api/routes/health.py (+50 lines: helper + extended endpoint)
    - apps/prometheus/tests/test_api/test_health_data_freshness.py (+37 lines: SC #5 verbatim test)
decisions:
  - id: 25-08-D1
    decision: "Keep both `stale` (top-level, hard-coded > 1) AND `data_freshness.status` (configurable threshold) in /health/data response"
    rationale: "CONTEXT D-05 LOCKED — Phase 24 contract preserved; new clients consume `status`; old dashboards keep working until v1.7 deprecation"
  - id: 25-08-D2
    decision: "HTTP 200 in all freshness states (fresh/stale/unknown); status flagged in body only"
    rationale: "Echoes 24-HEALTH-04 design — /health/data is a freshness REPORT, not a liveness gate. K8s probes hit /health/live and /health/ready; dashboards/alerting consume /health/data status"
  - id: 25-08-D3
    decision: "Cold-start (max_data_date=None) returns status='unknown' + sessions_behind=None, NOT 'stale'"
    rationale: "Distinguishes a fresh deployment from a true ingest gap; preserves legacy `stale: true` top-level for Phase 24 back-compat"
metrics:
  duration_minutes: 12
  tasks_completed: 2
  files_changed: 2
  tests_red_to_green: 3
  tests_added: 1
  total_tests_pass: 4
  regression_suite_pass: "145/145 (test_api + test_dq + test_observability + test_services)"
  completed_date: "2026-04-29"
phase_closure: true
---

# Phase 25 Plan 08: /health/data Stale Freshness Probe Summary (DQ-07, SC #5)

Wave 6 (final wave) of Phase 25 — extends `GET /health/data` with a `data_freshness`
block driven by the VN trading calendar and `Settings.dq_stale_threshold_sessions`.
Closes ROADMAP Success Criterion #5 verbatim and **completes Phase 25** (8/8 plans,
5/5 SCs ✅).

## What Shipped

**Helper added** (`api/routes/health.py`):
- `_last_trading_day_on_or_before(today: date) -> date` — bounded backwards-walk
  (cap=20 iterations) over `_VN_HOLIDAYS_2025_2026` ∪ weekends. Reuses existing
  Phase 24 `_is_trading_day` predicate; **no new holiday set** (DRY per plan
  guidance).

**Endpoint extended** (`GET /health/data`):
- Top-level keys preserved verbatim per CONTEXT D-05: `max_price_date`,
  `trading_days_lag`, `stale`. Phase 24 contract is unbroken — old dashboards
  keep working.
- New `data_freshness` block: `{ last_trading_day, max_data_date, sessions_behind,
  status, threshold_sessions }`.
  - `status = 'fresh'` iff `sessions_behind <= settings.dq_stale_threshold_sessions`
  - `status = 'stale'` otherwise
  - `status = 'unknown'` on cold start (`max_data_date is None`); `stale: true`
    legacy field preserved alongside.
- HTTP 200 in all states — freshness is reported, not gated (echoes 24-HEALTH-04).

**Tests** (`test_api/test_health_data_freshness.py`):
- 3 RED tests from 25-01 turned GREEN: `test_data_freshness_shape`,
  `test_stale_status_when_lag_exceeds_threshold`, `test_threshold_override`.
- 1 new SC #5 verbatim shape-contract test: `test_sc5_health_data_response_shape`
  — pins both Phase 24 back-compat keys and DQ-07 block keys + status enum.

## RED → GREEN

```
$ uv run pytest tests/test_api/test_health_data_freshness.py -q
....                                                                     [100%]
4 passed in 0.29s
```

Helper sanity (Reunification Day 2026-04-30 → preceding Wed Apr 29; Sun 2025-06-08
→ Fri 2025-06-06):
```
$ uv run python -c "from datetime import date; from localstock.api.routes.health import _last_trading_day_on_or_before; ..."
helper OK
```

## Regression

```
$ uv run pytest tests/test_api/ tests/test_dq/ tests/test_observability/ tests/test_services/ -q
145 passed, 1 warning in 32.13s
```

(Pre-existing 1 Phase-24 migration test failure noted in plan brief; outside this
plan's scope and not in the suites above.)

## Lint

```
$ uvx ruff check src/localstock/api/routes/health.py tests/test_api/test_health_data_freshness.py
All checks passed!
```

## Commits

- `542098b` — `feat(25-08): /health/data data_freshness block + _last_trading_day_on_or_before helper (DQ-07, SC #5)`
- `600d27f` — `test(25-08): SC #5 verbatim shape-contract for /health/data (DQ-07)`

Both carry `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## SC #5 Verbatim Closure

ROADMAP §Phase 25 SC #5: *"`/health/data` trả status `stale` khi `MAX(stock_prices.date)`
lệch trading-calendar > 1 phiên — verified bằng manual rollback date"*.

Closure evidence:
1. `test_stale_status_when_lag_exceeds_threshold`: insert `max_data_date = today - 5
   days`, default `dq_stale_threshold_sessions=1` → asserts
   `data_freshness.status == 'stale'`. ✅
2. `test_threshold_override`: with `DQ_STALE_THRESHOLD_SESSIONS=10` and
   `max_data_date = today - 2 days` → asserts `status == 'fresh'` (threshold honored).
   ✅
3. `test_sc5_health_data_response_shape`: pins the 5 documented keys
   (`last_trading_day`, `max_data_date`, `sessions_behind`, `status`,
   `threshold_sessions`) AND the Phase 24 back-compat trio
   (`max_price_date`, `trading_days_lag`, `stale`). ✅
4. Plan-acceptance manual rollback semantics: covered by tests #1+#2 (MagicMock
   returns the rolled-back date from `SELECT MAX(stock_prices.date)`).

## Phase 25 Closure (8/8 plans, 5/5 SCs)

| SC | Description | Closing Plan | Status |
| -- | ----------- | ------------ | ------ |
| #1 | Pandera Tier 1 reject corrupt OHLCV → quarantine_rows | 25-05 | ✅ |
| #2 | JSONB write boundary scrubs ±Inf/NaN → SQL NULL | 25-02 | ✅ |
| #3 | Per-symbol isolation — 1 BAD doesn't kill batch | 25-04 + 25-06 | ✅ |
| #4 | Tier 2 advisory rules emit `dq_violations_total{tier="advisory"}` shadow-mode | 25-07 | ✅ |
| #5 | `/health/data` flags stale data via trading calendar | **25-08 (this plan)** | ✅ |

| Plan | Wave | Status | Summary |
| ---- | ---- | ------ | ------- |
| 25-01 | 0 | ✅ | Pandera install, dq/ scaffold, Alembic 25a0b1c2d3e4, Settings + RED scaffolds |
| 25-02 | 1 | ✅ | sanitize_jsonb + repo wiring (DQ-04, SC #2) |
| 25-03 | 1 | ✅ | QuarantineRepository + APScheduler 03:15 cleanup cron (DQ-08) |
| 25-04 | 2 | ✅ | Pipeline._write_stats dual-write + _truncate_error (DQ-06, SC #3 partial) |
| 25-05 | 2 | ✅ | OHLCVSchema + reject-to-quarantine in _crawl_prices (DQ-01, SC #1) |
| 25-06 | 3 | ✅ | Per-symbol try/except across 5 services + Pitfall A guardrail (DQ-05, SC #3) |
| 25-07 | 5 | ✅ | evaluate_tier2 dispatcher + DQ-03 promotion runbook (DQ-02 + DQ-03, SC #4) |
| 25-08 | 6 | ✅ | /health/data data_freshness block (DQ-07, SC #5) |

## Deviations from Plan

**1. [Rule 1 - Naming]** Plan referenced helper `_is_business_day` but actual
Phase 24 code uses `_is_trading_day` (line 80, `health.py`). Used the existing
name — no functional change; the predicate is identical (Mon-Fri AND not in
`_VN_HOLIDAYS_2025_2026`).
- **Files:** `apps/prometheus/src/localstock/api/routes/health.py`
- **Commit:** `542098b`

**2. [Rule 1 - Helper placement]** Plan said "after `_trading_days_lag` (line ~88)"
— placed there exactly. No deviation.

**3. [Plan inaccuracy noted]** Plan claimed RED tests "should already exist" —
they DO exist (created in 25-01 commit `6f87508` at `tests/test_api/`, not
`tests/test_health/` as the plan frontmatter incorrectly indicated). Used the
actual location. No new file created in tests dir.

No architectural deviations. No Rule 4 escalations.

## Threat Flags

None — plan threat model T-25-08-01..03 fully addressed:
- T-25-08-02 (DoS unbounded loop) → bounded `range(20)`
- T-25-08-03 (back-compat keys removed) → SC #5 verbatim test pins all 3 Phase 24 keys

## Self-Check: PASSED

- ✅ `apps/prometheus/src/localstock/api/routes/health.py` — `_last_trading_day_on_or_before` defined (line ~92), endpoint extended (line ~204+).
- ✅ `apps/prometheus/tests/test_api/test_health_data_freshness.py` — 4 tests including `test_sc5_health_data_response_shape`.
- ✅ Commit `542098b` — `feat(25-08): /health/data data_freshness block ...` exists.
- ✅ Commit `600d27f` — `test(25-08): SC #5 verbatim shape-contract ...` exists.
- ✅ All 4 freshness tests GREEN; 145/145 regression suite GREEN; ruff clean.
- ✅ ROADMAP updated: Phase 25 box checked, plan 25-08 checked, table row → 8/8 Complete ✅.
- ✅ REQUIREMENTS.md updated: DQ-07 checkbox + traceability row → Done.
