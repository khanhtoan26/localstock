---
phase: 25-data-quality
plan: 07
subsystem: dq.tier2
tags: [dq, tier2, advisory, shadow-mode, sc4-closed, dq-02, dq-03]
requires: [25-01, 25-05, 25-06]
provides:
  - "evaluate_tier2(rule, df, predicate, *, symbol=None) — shadow-by-default Tier 2 dispatcher (DQ-02)"
  - "get_tier2_mode(rule_name) -> Literal['shadow','enforce'] — per-rule env flag lookup with Settings fallback (D-06)"
  - "Tier2Violation exception (only raised in enforce mode) — caught by 25-06 per-symbol try/except"
  - "Tier 2 advisory predicates: predicate_rsi_anomaly (RSI > 99.5), predicate_gap_30pct (close-to-close gap > 30%), predicate_missing_rows_20pct (> 20% expected sessions missing)"
  - "AnalysisService.analyze_technical_single dispatches all three Tier 2 rules per symbol after compute_indicators"
  - "metrics.iter_tracked_collectors(name) — multi-registry counter lookup (WeakSet of registries seen by init_metrics)"
  - "docs/runbook/dq-tier2-promotion.md — full DQ-03 deliverable: Promotion Criteria, Procedure, Rollback, Per-Rule Status Table"
  - "ROADMAP Success Criterion #4 ✅ closed (verbatim)"
affects:
  - apps/prometheus/src/localstock/dq/shadow.py
  - apps/prometheus/src/localstock/dq/runner.py
  - apps/prometheus/src/localstock/dq/schemas/ohlcv.py
  - apps/prometheus/src/localstock/dq/schemas/indicators.py
  - apps/prometheus/src/localstock/services/analysis_service.py
  - apps/prometheus/src/localstock/observability/metrics.py
  - apps/prometheus/tests/test_dq/test_tier2_dispatch.py
  - apps/prometheus/tests/test_docs/test_runbooks.py
  - docs/runbook/dq-tier2-promotion.md
tech-stack:
  added: []
  patterns:
    - "Shadow → strict promotion via per-rule env flag (DQ_TIER2_<RULE>_MODE) with global default DQ_DEFAULT_TIER2_MODE='shadow'"
    - "Tier 2 dispatcher always emits metric + log; only the mode decides whether to raise (D-06)"
    - "WeakSet-tracked registries so test fixtures with fresh CollectorRegistry see their metric incremented"
    - "RESEARCH §Pattern 2 — predicate(df) → DataFrame of offending rows; empty == pass"
key-files:
  created:
    - docs/runbook/dq-tier2-promotion.md (full content; 117 lines)
  modified:
    - apps/prometheus/src/localstock/dq/shadow.py
    - apps/prometheus/src/localstock/dq/runner.py
    - apps/prometheus/src/localstock/dq/schemas/ohlcv.py
    - apps/prometheus/src/localstock/dq/schemas/indicators.py
    - apps/prometheus/src/localstock/services/analysis_service.py
    - apps/prometheus/src/localstock/observability/metrics.py
    - apps/prometheus/tests/test_dq/test_tier2_dispatch.py
    - apps/prometheus/tests/test_docs/test_runbooks.py
decisions:
  - "Tier 2 metric increment uses iter_tracked_collectors (WeakSet of registries) — required so the SC #4 test fixture's fresh CollectorRegistry actually sees the increment. Fixes a contract mismatch between the plan's prescribed REGISTRY-only lookup and the RED test's reg.get_sample_value() assertion. Rule 1 / Rule 3 auto-fix."
  - "Predicate-bug exceptions in AnalysisService Tier 2 dispatch are logged (dq.tier2.predicate_error) but DO NOT propagate — only Tier2Violation propagates to the per-symbol try/except. Prevents an advisory check bug from breaking analysis for a healthy symbol (defense-in-depth Pitfall C echo)."
  - "missing_rows expected-session count derived from ohlcv_df['date'].max() - .min() with a 5/7 business-day estimate. Conservative; fine for a shadow advisory rule. May be tuned when promoted."
metrics:
  duration: "≈ 8 min"
  completed: "2026-04-29"
  tasks: 3
  files: 9
  commits: 3
---

# Phase 25 Plan 07: Tier 2 Advisory Dispatcher + Shadow-Mode Promotion Runbook Summary

**One-liner:** Implements DQ-02 (`evaluate_tier2` shadow-by-default dispatcher with per-rule env-flag mode lookup) and DQ-03 (operational promotion runbook) — closes ROADMAP Success Criterion #4 verbatim and lights up `localstock_dq_violations_total{rule, tier="advisory"}` for `rsi_anomaly`, `gap`, and `missing_rows` in production AnalysisService.

## What changed

### Tier 2 dispatcher (`dq/runner.py`, `dq/shadow.py`)

- `Tier2Violation(Exception)` — carries `rule` + `offending` payload. Raised ONLY in enforce mode; caught by 25-06's per-symbol try/except so promoted rules surface in `PipelineRun.stats.failed_symbols` (D-03 + D-06).
- `get_tier2_mode(rule_name) -> Mode` — reads `Settings.dq_tier2_<rule>_mode` (per-rule override) → `Settings.dq_default_tier2_mode` (global) → hard fallback `"shadow"`. Unknown values fall back to `"shadow"` (defensive).
- `evaluate_tier2(rule, df, predicate, *, symbol=None)`:
  1. Run predicate; if empty/None, no-op.
  2. Look up mode → label tier (`"advisory"` if shadow, `"strict"` if enforce).
  3. Increment `localstock_dq_violations_total{rule, tier}` on EVERY tracked registry (WeakSet) — never throws.
  4. Emit structured `dq_warn` log with `rule, tier, symbol, violation_count`.
  5. In enforce mode: raise `Tier2Violation(rule, bad)`.

### Tier 2 predicates (`dq/schemas/`)

- `predicate_rsi_anomaly(df)` — rows with `rsi > 99.5` (DQ-02).
- `predicate_gap_30pct(df)` — rows where consecutive close-to-close gap exceeds 30% (sorts by `date` defensively, drops first-bar NaN).
- `predicate_missing_rows_20pct(df, *, expected_session_count)` — frame-level signal when `1 - actual/expected > 0.20`.

### AnalysisService dispatch hook

In `analyze_technical_single` (after `compute_indicators`):

```python
try:
    if not indicators_df.empty:
        evaluate_tier2("rsi_anomaly", indicators_df, predicate_rsi_anomaly, symbol=symbol)
    if not ohlcv_df.empty:
        evaluate_tier2("gap", ohlcv_df, predicate_gap_30pct, symbol=symbol)
        # missing_rows uses business-day estimate from ohlcv_df['date'] span
        evaluate_tier2("missing_rows", ohlcv_df, lambda d: predicate_missing_rows_20pct(d, expected_session_count=...), symbol=symbol)
except Tier2Violation:
    raise   # caught by 25-06 per-symbol try/except (D-03 + D-06)
except Exception as e:
    logger.warning("dq.tier2.predicate_error", symbol=symbol, error=str(e))
```

### Multi-registry collector lookup (`observability/metrics.py`)

Added `_TRACKED_REGISTRIES: WeakSet[CollectorRegistry]` populated by every `init_metrics(target)` call, plus `iter_tracked_collectors(name)` which dedupes counters by `id()` across all tracked registries (and falls back to global REGISTRY). Required so the SC #4 RED test pattern — `reg = CollectorRegistry(); init_metrics(reg); evaluate_tier2(...); reg.get_sample_value(...)` — actually sees the increment.

### Runbook (`docs/runbook/dq-tier2-promotion.md`, 117 lines)

Full DQ-03 deliverable replacing the Wave 0 placeholder. Sections:
- **Why this runbook exists** — shadow vs strict semantics; metric flip; failed_symbols routing.
- **Promotion Criteria** — 5-point gate (14-day window, < 5% violation rate, no FP review, exemplar present, AutomationService digest reviewed).
- **Procedure: shadow → strict** — Prometheus query, env flag flip, restart, verify, watch, audit-log update.
- **Rollback** — > 30% symbol-failure trigger, env flag reset, debug-ticket pattern.
- **Per-Rule Status Table** — `rsi_anomaly`, `gap`, `missing_rows` all currently `shadow` / "—".
- **References** — CONTEXT D-06/D-03, RESEARCH Pattern 2 + Pitfall C, source files.

### SC #4 verbatim closure

`test_sc4_tier2_emits_metric_no_block` — fresh registry, `evaluate_tier2("rsi_anomaly", ...)` MUST NOT raise, `reg.get_sample_value("localstock_dq_violations_total", {"rule":"rsi_anomaly","tier":"advisory"})` MUST be ≥ 1. ✅ green.

## Verification

```bash
cd apps/prometheus
uv run pytest tests/test_dq/test_tier2_dispatch.py -x -q
# 5 dispatch tests + 1 SC #4 test = 6 passed in 0.18s

uv run pytest tests/test_dq/test_tier2_dispatch.py tests/test_docs/test_runbooks.py -x -q
# 7 passed in 0.19s  (RED → GREEN: dispatch + runbook content)

uv run pytest tests/test_services/ tests/test_dq/ tests/test_docs/ -q
# 83 passed in 21.16s  (no regressions; AnalysisService dispatch hook clean)
```

The 5 RED tests carried in from 25-01 (`test_default_mode_is_shadow`, `test_rsi_advisory_metric_emitted`, `test_gap_shadow_no_raise`, `test_missing_rows_advisory`, `test_promotion_to_strict_raises`) all flipped to GREEN. The 6th SC #4 verbatim test was added in this plan and is GREEN.

`test_runbooks.py` upgraded from existence-only to content-required (asserts `Promotion Criteria`, `Rollback`, `Per-Rule Status Table`, `DQ_TIER2_`, `shadow`, `enforce`, `14-day` are all present). GREEN.

The pre-existing Phase-24 migration test failure (`test_migration_24_pipeline_durations.py`) is unrelated and ignored per prompt.

The 25-08 RED tests (`test_health_data_freshness.py` × 3) remain RED — they belong to the next plan and were not touched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Multi-registry counter lookup**
- **Found during:** Task 2.
- **Issue:** Plan prescribed `counter = REGISTRY._names_to_collectors.get(...)` (global registry only). The RED test fixture creates a fresh `CollectorRegistry()` and asserts `reg.get_sample_value(...) >= 1` — the global increment never reaches `reg`, so the test fails even with a correct dispatcher.
- **Fix:** Introduced `_TRACKED_REGISTRIES: WeakSet[CollectorRegistry]` in `observability/metrics.py` (populated by `init_metrics(target)`) and `iter_tracked_collectors(name)` helper. Dispatcher iterates and increments each distinct collector (deduped by `id()`). Falls back to the global default REGISTRY too — production path unchanged.
- **Files modified:** `apps/prometheus/src/localstock/observability/metrics.py`, `apps/prometheus/src/localstock/dq/runner.py`.
- **Commit:** `f09c9bb`.

**2. [Rule 2 — Critical] Predicate-bug isolation in AnalysisService dispatch**
- **Found during:** Task 3.
- **Issue:** Plan example wrapped the dispatch in a single `except Exception` that re-raises `Tier2Violation`. A buggy predicate (e.g., AttributeError, KeyError) would bubble up and break `analyze_technical_single` for healthy symbols — defeats the purpose of an advisory check.
- **Fix:** Catch `Tier2Violation` separately (re-raise to 25-06's per-symbol try/except) AND `Exception` (log `dq.tier2.predicate_error` and continue). Defense-in-depth against a buggy advisory rule taking down the analysis pipeline.
- **Files modified:** `apps/prometheus/src/localstock/services/analysis_service.py`.
- **Commit:** `42ae535`.

### Out-of-scope items (logged to `deferred-items.md`)

- Pre-existing F401 unused-import warnings in `apps/prometheus/src/localstock/services/analysis_service.py` (`VN_INDUSTRY_GROUPS` line 25, `StockPrice` line 34) — not introduced by this plan; not fixed.

## Commits

| Hash      | Type | Subject                                                                                          |
| --------- | ---- | ------------------------------------------------------------------------------------------------ |
| `98e7e3c` | feat | get_tier2_mode + Tier2Violation (DQ-03)                                                          |
| `f09c9bb` | feat | evaluate_tier2 dispatcher + Tier 2 advisory predicates (DQ-02)                                   |
| `42ae535` | feat | wire Tier 2 dispatch into AnalysisService + DQ-03 runbook (SC #4)                                |

All include `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## TDD Gate Compliance

This plan landed without a separate `test(...)` RED commit because the RED tests for Tier 2 dispatch were already shipped by 25-01 (Wave 0 scaffolds: `tests/test_dq/test_tier2_dispatch.py` × 4 + `tests/test_docs/test_runbooks.py` placeholder). 25-07 turned them GREEN and added the SC #4 verbatim test alongside the implementation in `42ae535` (acceptable per plan-type=tdd when tests pre-exist; gate sequence holds: RED commits in 25-01 → GREEN feat commits in 25-07).

## Runbook excerpt (operational summary)

To promote a Tier 2 rule shadow → strict in production:

```bash
# 1. Verify 14-day violation rate < 5% in Prometheus
sum(rate(localstock_dq_violations_total{rule="rsi_anomaly", tier="advisory"}[14d])) /
sum(rate(localstock_dq_validation_total{validator="rsi_anomaly", outcome="pass"}[14d]))

# 2. Flip env flag in production .env
DQ_TIER2_RSI_MODE=enforce

# 3. Restart API + scheduler → Settings re-loads
# 4. Watch tier="strict" series populate within 1h
# 5. Update Per-Rule Status Table in docs/runbook/dq-tier2-promotion.md
```

Rollback: `DQ_TIER2_<NAME>_MODE=shadow` (or unset) + restart.

## ROADMAP Success Criterion #4 — Closure Verification

**Verbatim contract (from must_haves.truths[0]):**

> Tier 2 advisory rules (RSI > 99.5, gap > 30%, missing > 20%) emit log dq_warn + counter dq_violations_total{rule, tier='advisory'} but do NOT block — shadow-mode flag default true.

**Verified by:**

| Component | Evidence |
|-----------|----------|
| RSI > 99.5 | `predicate_rsi_anomaly` in `dq/schemas/indicators.py`; dispatched in `analyze_technical_single`; `test_rsi_advisory_metric_emitted` ✅ |
| gap > 30% | `predicate_gap_30pct` in `dq/schemas/ohlcv.py`; dispatched in `analyze_technical_single`; `test_gap_shadow_no_raise` ✅ |
| missing > 20% | `predicate_missing_rows_20pct` in `dq/schemas/ohlcv.py`; dispatched with computed expected-session count; `test_missing_rows_advisory` ✅ |
| dq_warn log | `evaluate_tier2` emits `logger.warning("dq_warn", rule=..., tier=..., symbol=..., violation_count=...)` |
| counter `dq_violations_total{rule, tier='advisory'}` | `iter_tracked_collectors` increments on every fire; SC #4 test asserts `reg.get_sample_value(...) >= 1` ✅ |
| does NOT block | `test_sc4_tier2_emits_metric_no_block` calls `evaluate_tier2` and continues without raising; `Tier2Violation` only raised in enforce mode ✅ |
| shadow-mode default true | `Settings.dq_default_tier2_mode = "shadow"` from 25-01; `get_tier2_mode("anything") == "shadow"` ✅ |

**SC #4 ✅ CLOSED.**

## Self-Check: PASSED

- [x] `apps/prometheus/src/localstock/dq/shadow.py` — `class Tier2Violation`, `def get_tier2_mode` present.
- [x] `apps/prometheus/src/localstock/dq/runner.py` — `def evaluate_tier2` real impl, no NotImplementedError.
- [x] `apps/prometheus/src/localstock/dq/schemas/ohlcv.py` — `predicate_gap_30pct`, `predicate_missing_rows_20pct` present.
- [x] `apps/prometheus/src/localstock/dq/schemas/indicators.py` — `predicate_rsi_anomaly` present.
- [x] `apps/prometheus/src/localstock/services/analysis_service.py` — `evaluate_tier2(` dispatched in `analyze_technical_single`.
- [x] `apps/prometheus/src/localstock/observability/metrics.py` — `iter_tracked_collectors` + `_TRACKED_REGISTRIES` present.
- [x] `docs/runbook/dq-tier2-promotion.md` — 117 lines, all required sections present (verified by `test_runbooks.py`).
- [x] `apps/prometheus/tests/test_dq/test_tier2_dispatch.py` — 6 tests (5 from 25-01 + new SC #4) all GREEN.
- [x] `apps/prometheus/tests/test_docs/test_runbooks.py` — content-required assertion GREEN.
- [x] Commits `98e7e3c`, `f09c9bb`, `42ae535` exist on master (verified via `git log --oneline -4`).
- [x] All 3 commits carry `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.
- [x] Wider regression: `test_services/` + `test_dq/` + `test_docs/` → 83 passed, 0 failed.
- [x] No `Tier2Violation` raised in shadow path — verified by 4 of 5 dispatch tests.
- [x] ROADMAP SC #4 verbatim contract verified by `test_sc4_tier2_emits_metric_no_block`.
