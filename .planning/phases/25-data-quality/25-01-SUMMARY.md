---
phase: 25-data-quality
plan: 01
subsystem: data-quality
tags: [scaffolds, tdd-red, alembic, pandera, dq, wave-0]
requires:
  - phase: 24
    plan: 06
    why: "Phase 24 OBS-17 head (24a1b2c3d4e5) is the down_revision for the new 25a0b1c2d3e4 migration."
provides:
  - "localstock.dq package skeleton (sanitizer, shadow, runner, quarantine_repo, schemas/*)"
  - "Alembic head 25a0b1c2d3e4 — quarantine_rows table + pipeline_runs.stats JSONB"
  - "Settings.dq_default_tier2_mode, dq_tier2_{rsi,gap,missing}_mode, dq_stale_threshold_sessions"
  - "Counter localstock_dq_violations_total{rule, tier}"
  - "MAX_ERROR_CHARS=200 budget for failed_symbols error truncation"
  - "30 RED tests across DQ-01..DQ-08 ready for Wave 1+"
  - "docs/runbook/dq-tier2-promotion.md placeholder (DQ-03)"
affects:
  - "All Phase 25 plans (25-02..25-08) — every Wave 1+ plan now has its RED test waiting"
tech-stack:
  added:
    - "pandera[pandas]>=0.31,<1.0"
  patterns:
    - "TDD Wave 0 — Nyquist scaffolding ahead of every implementation wave"
    - "Idempotent Counter registration via existing observability/_register helper"
    - "Polymorphic JSONB quarantine table (single table, source/symbol discriminators)"
key-files:
  created:
    - apps/prometheus/src/localstock/dq/__init__.py
    - apps/prometheus/src/localstock/dq/sanitizer.py
    - apps/prometheus/src/localstock/dq/shadow.py
    - apps/prometheus/src/localstock/dq/runner.py
    - apps/prometheus/src/localstock/dq/quarantine_repo.py
    - apps/prometheus/src/localstock/dq/schemas/__init__.py
    - apps/prometheus/src/localstock/dq/schemas/ohlcv.py
    - apps/prometheus/src/localstock/dq/schemas/financials.py
    - apps/prometheus/src/localstock/dq/schemas/indicators.py
    - apps/prometheus/alembic/versions/25a0b1c2d3e4_phase25_dq_tables.py
    - apps/prometheus/tests/test_dq/__init__.py
    - apps/prometheus/tests/test_dq/test_sanitizer.py
    - apps/prometheus/tests/test_dq/test_quarantine_repo.py
    - apps/prometheus/tests/test_dq/test_ohlcv_schema.py
    - apps/prometheus/tests/test_dq/test_tier2_dispatch.py
    - apps/prometheus/tests/test_db/test_phase25_migration.py
    - apps/prometheus/tests/test_scheduler/test_quarantine_cleanup.py
    - apps/prometheus/tests/test_services/test_pipeline_isolation.py
    - apps/prometheus/tests/test_services/test_pipeline_stats.py
    - apps/prometheus/tests/test_api/test_health_data_freshness.py
    - apps/prometheus/tests/test_docs/__init__.py
    - apps/prometheus/tests/test_docs/test_runbooks.py
    - docs/runbook/dq-tier2-promotion.md
  modified:
    - apps/prometheus/pyproject.toml
    - uv.lock
    - apps/prometheus/src/localstock/db/models.py
    - apps/prometheus/src/localstock/config.py
    - apps/prometheus/src/localstock/observability/metrics.py
    - .planning/phases/25-data-quality/25-VALIDATION.md
decisions:
  - "Honour all CONTEXT D-01..D-08 — pandera install (D-01), polymorphic quarantine_rows (D-02), JSONB sanitizer at write boundary (D-04), per-rule shadow dispatcher (D-06), pipeline_runs.stats dual-write column (D-07), Wave 0 scaffolds-first (D-08)."
  - "Counter labels are (rule, tier) — never (symbol). Phase 23 D-06 / OBS-09 cardinality budget is non-negotiable."
  - "Settings._validate_tier2_mode normalises empty string → None, rejects bogus values at startup (Loguru fail-fast precedent)."
metrics:
  duration: "~25 min wall clock"
  completed: 2026-04-29
---

# Phase 25 Plan 01: Wave 0 Data-Quality Scaffolds Summary

Wave 0 scaffolding for Phase 25 (Data Quality): pandera installed, `localstock.dq` package skeleton committed, Alembic migration `25a0b1c2d3e4` lands `quarantine_rows` + `pipeline_runs.stats`, four new Settings fields + `localstock_dq_violations_total{rule, tier}` Counter registered, runbook placeholder created, and 30 RED tests are armed across DQ-01..DQ-08 — every Wave 1+ plan now has its failing test waiting.

## What Was Built

### Dependency

- **pandera[pandas] 0.31.1** added to `apps/prometheus/pyproject.toml`. Resolved via `uv add`; the workspace `uv.lock` (repo root) gained the entry.
- Verified import path `import pandera.pandas as pa` works (D-01 / RESEARCH Pattern 1).

### `localstock.dq` package skeleton

- `dq/__init__.py` — exports `MAX_ERROR_CHARS = 200` (Pitfall G error-truncation budget).
- `dq/sanitizer.py::sanitize_jsonb` — stub raising `NotImplementedError("DQ-04: implemented in 25-02-PLAN.md")`.
- `dq/shadow.py::get_tier2_mode` + `Mode = Literal["shadow", "enforce"]` — stub for 25-07.
- `dq/runner.py::partition_valid_invalid` (DQ-01, 25-05) and `evaluate_tier2` (DQ-02, 25-07) — stubs.
- `dq/quarantine_repo.py::QuarantineRepository` — class with `insert(...)` and `cleanup_older_than(days=30)` stubs (DQ-08, 25-03).
- `dq/schemas/{ohlcv,financials,indicators}.py` — `None` placeholders for `OHLCVSchema`, `OHLCVAdvisorySchema`, `FinancialsSchema`, `IndicatorAdvisorySchema`.

### Alembic migration `25a0b1c2d3e4`

- `down_revision = "24a1b2c3d4e5"` (cleanly stacks atop Phase 24 OBS-17 head).
- Creates `quarantine_rows` (8 columns, `payload`/`reason`/`rule`/`tier` + `quarantined_at` timestamp) with `ix_quarantine_rows_source_qa` and `ix_quarantine_rows_symbol`.
- Adds `pipeline_runs.stats` JSONB nullable for D-07 dual-write.
- Applied locally (`alembic upgrade head` → `25a0b1c2d3e4 (head)`); the 3 `requires_pg` smoke tests in `tests/test_db/test_phase25_migration.py` pass GREEN immediately.
- ORM updates in `db/models.py`: `PipelineRun.stats` field + new `QuarantineRow` class.

### Settings + observability primitives

- 4 new fields with safe defaults: `dq_default_tier2_mode='shadow'`, `dq_tier2_{rsi,gap,missing}_mode=None`, `dq_stale_threshold_sessions=1`.
- `_validate_tier2_mode` field validator rejects bogus values at startup; empty-string is normalised to `None` so per-rule overrides fall back to the default.
- `localstock_dq_violations_total{rule, tier}` Counter registered via the existing idempotent `_register` helper. **No `symbol` label** (Phase 23 D-06 / OBS-09 cardinality rule).

### Runbook placeholder

- `docs/runbook/dq-tier2-promotion.md` — TOC with TODO markers for Promotion Criteria / Shadow → Strict / Rollback. DQ-03 smoke test asserts existence + presence of "shadow" + "TODO" markers.

### RED test scaffolds — 30 total

| File | Tests | DQ Req | Wave Target |
|------|-------|--------|-------------|
| `tests/test_dq/test_sanitizer.py` | 6 (5 unit + 1 skip) | DQ-04 | 25-02 |
| `tests/test_dq/test_quarantine_repo.py` | 3 | DQ-08 | 25-03 |
| `tests/test_dq/test_ohlcv_schema.py` | 4 | DQ-01 | 25-05 |
| `tests/test_dq/test_tier2_dispatch.py` | 5 | DQ-02 + DQ-03 | 25-07 |
| `tests/test_services/test_pipeline_isolation.py` | 3 (1 active + 2 skip) | DQ-05 | 25-06 |
| `tests/test_services/test_pipeline_stats.py` | 3 | DQ-06 | 25-04 |
| `tests/test_api/test_health_data_freshness.py` | 3 | DQ-07 | 25-08 |
| `tests/test_scheduler/test_quarantine_cleanup.py` | 1 | DQ-08 | 25-03 |
| `tests/test_db/test_phase25_migration.py` | 3 (GREEN — smoke) | DQ-06/08 | 25-01 |
| `tests/test_docs/test_runbooks.py` | 1 (GREEN — smoke) | DQ-03 | 25-01 |

Selection target gate (`pytest -k "dq_ or sanitize or quarantine or health_data or pipeline_stats or pipeline_isolation or runbook or phase25"`): **30 collected** ≥ 28 required.

## Tasks & Commits

| Task | Name | Commit |
|------|------|--------|
| 1 | Install pandera + create dq/ package skeleton | `41f98b9` |
| 2 | Alembic migration + ORM updates + migration smoke test | `d1fa26a` |
| 3 | Settings DQ fields + dq_violations_total Counter | `2897d11` |
| 4 | RED scaffolds — DQ-04 sanitizer + DQ-08 quarantine_repo | `b04f10a` |
| 5 | RED scaffolds — DQ-01 ohlcv schema + DQ-05/06 pipeline | `f9f02f3` |
| 6 | RED scaffolds — DQ-02/03 tier2 + DQ-07 freshness + runbook | `6f87508` |
| 7 | Sanity gate — wave_0_complete=true | `f7bd84f` |

## Verification Performed

- `uv run python -c "import pandera.pandas as pa; ..."` — all 9 dq/* modules import; `MAX_ERROR_CHARS == 200`.
- `uv run alembic upgrade head` — no errors; current revision = `25a0b1c2d3e4 (head)`.
- `uv run pytest tests/test_db/test_phase25_migration.py` — 3 passed (`requires_pg`).
- Settings invariants — `dq_default_tier2_mode == 'shadow'`, `dq_stale_threshold_sessions == 1`, per-rule modes `None`, `DQ_DEFAULT_TIER2_MODE=bogus` raises `ValidationError` at startup.
- `init_metrics(reg)` registers `localstock_dq_violations_total`; `inc()` produces sample under labels `{rule='r', tier='advisory'}` = 1.0.
- `uv run pytest -k "dq_ or sanitize or quarantine or health_data or pipeline_stats or pipeline_isolation or runbook or phase25"` — 30 collected, 8 passed (migration + runbook + 3 skips don't count), 19 failed RED, 3 skipped. Zero `ModuleNotFoundError` on `localstock.dq.*` — all failures point at exact Wave 1+ symbols (`NotImplementedError("DQ-XX: implemented in 25-NN-PLAN.md")`).
- `uv run --with ruff ruff check ...` — all checks passed across the new sources.
- `uv run pytest --collect-only` — full suite still collects 560 tests with no regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Off-by-one in `tests/test_docs/test_runbooks.py` path resolution**
- **Found during:** Task 6 verification.
- **Issue:** Plan's snippet used `Path(__file__).resolve().parents[3]` to reach the repo root, but the actual layout is `apps/prometheus/tests/test_docs/test_runbooks.py` so `parents[3]` resolves to `apps/`, not the monorepo root. The DQ-03 runbook smoke test failed to find `docs/runbook/dq-tier2-promotion.md`.
- **Fix:** Changed to `parents[4]` (test_docs → tests → prometheus → apps → repo root). Comment updated to spell out the chain.
- **Files modified:** `apps/prometheus/tests/test_docs/test_runbooks.py`.
- **Commit:** `6f87508`.

**2. [Rule 1 — Plan keyword typo] Sanity-gate `-k` expression**
- **Found during:** Task 7 collection gate.
- **Issue:** Plan's keyword expression `pipeline_run_stats` doesn't substring-match the file `test_pipeline_stats.py` (no `_run` segment). Using the plan-suggested expression collected only 27 tests (< 28 target).
- **Fix:** Used `pipeline_stats` (matches the actual filename). Now collects 30. The expression substitution is a doc-only change inside the executor flow; the underlying test count is unchanged.
- **Files modified:** none (executor-side keyword only).

**3. [Rule 1 — Test fixture compatibility] Health route async-mock shape**
- **Found during:** Task 6 RED collection.
- **Issue:** Plan's snippet used `sess.execute.return_value.scalar_one_or_none = lambda: ...`, which assigns to a SAFE attribute on an `AsyncMock` and breaks because `execute(...)` returns a coroutine that itself returns a Result. Even as a RED test it would crash with `TypeError: object MagicMock can't be used in 'await' expression`.
- **Fix:** Made the mock explicit — `result = MagicMock(); result.scalar_one_or_none.return_value = ...; sess.execute.return_value = result`. Test still fails RED (the route doesn't yet emit `data_freshness`), but the failure is a clean `KeyError`/`AssertionError` on the response shape, not a fixture crash.
- **Files modified:** `apps/prometheus/tests/test_api/test_health_data_freshness.py`.
- **Commit:** `6f87508`.

### Auth Gates

None.

### Out-of-scope discoveries

None deferred. The single `ImportError` on `localstock.services.pipeline._truncate_error` (test_pipeline_stats.py) is intentional — that symbol lands in 25-04.

## Threat Model Compliance

All 5 threats from the plan's `<threat_model>` are addressed by Wave 0 primitives:

- **T-25-01-01 (Tampering / NaN-Inf into JSONB)** — `sanitize_jsonb` stub registered; full impl 25-02.
- **T-25-01-02 (DoS / unbounded quarantine_rows)** — table created with `ix_quarantine_rows_source_qa` index supporting time-window pruning; cron lands 25-03.
- **T-25-01-03 (EoP / silent Tier 2 promotion)** — per-rule env flags + `_validate_tier2_mode` startup validator + DQ-03 runbook placeholder + smoke test.
- **T-25-01-04 (Info disclosure / stack-trace leak)** — `MAX_ERROR_CHARS = 200` constant exported and the failing `test_error_truncation` test enforces the budget.
- **T-25-01-05 (Repudiation)** — accepted; `quarantined_at` server_default + payload preservation captured by table DDL.

No new threat surface introduced beyond what the plan's threat register already covers.

## Known Stubs

The following placeholders are **intentional Wave 0 stubs**, each covered by an existing RED test that names the future plan:

| Stub | File | Resolved by |
|------|------|-------------|
| `sanitize_jsonb` raises NIE | `dq/sanitizer.py` | 25-02 |
| `QuarantineRepository.insert/cleanup_older_than` raise NIE | `dq/quarantine_repo.py` | 25-03 |
| `_truncate_error` not yet defined in `services/pipeline` | (referenced in test_pipeline_stats.py) | 25-04 |
| `partition_valid_invalid` raises NIE; `OHLCVSchema = None` | `dq/runner.py`, `dq/schemas/ohlcv.py` | 25-05 |
| `Pipeline.run_full` per-symbol isolation | `services/pipeline.py` | 25-06 |
| `evaluate_tier2`, `get_tier2_mode` raise NIE; `OHLCVAdvisorySchema = None` | `dq/runner.py`, `dq/shadow.py`, `dq/schemas/ohlcv.py` | 25-07 |
| `data_freshness` block missing on `/health/data` | `api/routes/health.py` | 25-08 |
| Runbook TODO markers | `docs/runbook/dq-tier2-promotion.md` | 25-07 |

These are all expected per CONTEXT D-08 ("Wave 0 = scaffolds + RED tests, no impl"). The Wave 0 acceptance gate is precisely "RED tests fire on these stubs".

## TDD Gate Compliance

This plan's `type: tdd` cycle ran inverted relative to a typical feature plan because Wave 0's product **is the RED scaffold** — there is no GREEN to land in 25-01 itself. The `feat()` commits in this plan establish the structural enabling primitives (package, migration, settings, metric, runbook); the `test()` commits add the RED scaffolds that Waves 1–4 will turn GREEN. This is the agreed pattern from CONTEXT D-08.

## Self-Check: PASSED

Verified all created files exist:
- `apps/prometheus/src/localstock/dq/{__init__,sanitizer,shadow,runner,quarantine_repo}.py` ✓
- `apps/prometheus/src/localstock/dq/schemas/{__init__,ohlcv,financials,indicators}.py` ✓
- `apps/prometheus/alembic/versions/25a0b1c2d3e4_phase25_dq_tables.py` ✓
- All 10 test files ✓
- `docs/runbook/dq-tier2-promotion.md` ✓

Verified all commits exist:
- `41f98b9`, `d1fa26a`, `2897d11`, `b04f10a`, `f9f02f3`, `6f87508`, `f7bd84f` ✓
