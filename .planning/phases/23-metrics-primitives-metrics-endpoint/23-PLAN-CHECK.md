# Phase 23 — Plan Check

**Verdict**: ✅ **PASSED** (with 1 non-blocking warning)

**Plans verified**: 23-01, 23-02, 23-03
**Date**: pre-execute review
**Method**: goal-backward — start from 4 ROADMAP success criteria + 8 locked decisions, walk back to plan tasks.

---

## Summary

| Dimension | Status | Notes |
|---|---|---|
| Requirement coverage (OBS-07..10) | ✅ PASS | All 4 reqs covered by 9 tests in VALIDATION.md |
| Task completeness (files/action/verify/done) | ✅ PASS | All 5 tasks across 3 plans well-formed |
| Dependency graph | ✅ PASS | 23-01∥23-03 (W1) → 23-02 (W2). No cycles, no overlap. |
| Key links / wiring | ✅ PASS | metrics.py → app.py via `init_metrics()` + Instrumentator wiring explicit |
| Scope sanity | ✅ PASS | 23-01: 3 tasks/5 files; 23-02: 2 tasks/2 files; 23-03: 1 task/1 file |
| must_haves derivation | ✅ PASS | Truths user-observable + cite decision IDs |
| Context compliance (D-01..D-08) | ⚠ 7 PASS / 1 WARN | See decision table below |
| Scope reduction | ✅ PASS | No "v1/v2/static for now" hedging detected |
| Architectural tier | n/a | No responsibility map in RESEARCH |
| Cross-plan data contracts | ✅ PASS | No shared mutable data; metrics.py owned by 23-01, consumed read-only by 23-02 |
| copilot-instructions.md compliance | ✅ PASS | Vietnamese-acceptable, atomic commits, no f-string logs reaffirmed |
| Nyquist (8a–8e) | ✅ PASS | VALIDATION.md exists; every test has producing task; no watch-mode; sampling continuous |
| TDD ordering (23-01) | ✅ PASS | Task 2 (RED tests) precedes Task 3 (GREEN impl) |
| Rollback present | ✅ PASS | All 3 plans include git-revert + manual fallback |
| Boundary (D-08) | ✅ PASS | grep gate present in 23-01 + 23-02 acceptance + verification blocks |

---

## Coverage Table — Roadmap Success Criterion → Test → Producing Task

| SC# | Roadmap criterion | Test | Plan task |
|---|---|---|---|
| 1 | `GET /metrics` 200 + `text/plain; version=0.0.4` | `test_metrics_endpoint_returns_200_with_correct_content_type` | 23-02 / Task 2 |
| 1 | exposes `http_request_duration_seconds` | `test_metrics_endpoint_exposes_default_http_histogram` | 23-02 / Task 2 |
| 2 | module primitives import w/o raise | `test_metrics_module_level_import_does_not_raise`, `test_init_metrics_returns_all_primitive_families` | 23-01 / Task 2+3 |
| 3 | no `Duplicated timeseries` | `test_init_metrics_idempotent_on_same_registry` + `metrics_registry` fixture | 23-01 / Task 2+3 |
| 4 | no `symbol` label, cardinality ≤50 | `test_no_metric_has_symbol_label`, `test_label_schema_matches_budget` | 23-01 / Task 2+3 |

Plus: `test_metrics_namespace_prefix` (D-01), `test_pipeline_step_histogram_buckets` (D-03) — also produced by 23-01/Task 2+3. **9 tests total, all mapped.**

---

## Decision Adherence Table

| ID | Decision | Status | Evidence |
|---|---|---|---|
| **D-01** | All custom metrics use literal `localstock_` name prefix (NOT `metric_namespace=`) | ✅ PASS | 23-01 EXPECTED_LABELS keys all `localstock_*`; `test_metrics_namespace_prefix` enforces; 23-02 acceptance grep `metric_namespace` returns 0 |
| **D-02** | `/metrics` exposed without auth | ✅ PASS | 23-02 uses `expose(app, endpoint="/metrics", include_in_schema=False)` — no `Depends(...)`, no auth middleware. Runbook warning shipped in 23-03. |
| **D-03** | Histogram bucket constants per CONTEXT table | ✅ PASS | 23-01 invariant 1 names all 4 constants; `test_pipeline_step_histogram_buckets` asserts exact tuple `(1,5,10,30,60,120,300,600,1800,3600)` matching CONTEXT line 49 |
| **D-04** | `init_metrics(registry=None)` idempotent via try/except ValueError + `_names_to_collectors` lookup | ✅ PASS | 23-01 Task 3 invariant 2 + frontmatter key_link `pattern: "_names_to_collectors"`; `test_init_metrics_idempotent_on_same_registry` asserts `first[k] is second[k]` |
| **D-05** | Single `metrics.py` (no split) | ✅ PASS | 23-01 frontmatter declares one source file; section comments enumerated as Task 3 invariant 4 |
| **D-06** | Label sets match budget; NO `symbol`; cardinality test exists | ✅ PASS | EXPECTED_LABELS table mirrors CONTEXT D-06; `test_no_metric_has_symbol_label` + `test_label_schema_matches_budget` |
| **D-07** | Instrumentator constructor uses exact kwargs | ⚠ **WARN** | All kwargs match EXCEPT `excluded_handlers`: CONTEXT.md D-07 says `["/metrics", "/health/live"]`; plan 23-02 line 189 uses `["^/metrics$", "^/health/live$"]`. See W-1 below. |
| **D-08** | NO new `.inc()/.observe()/.set()` outside metrics.py; boundary grep gate present | ✅ PASS | grep gate appears in: 23-01 Task 3 acceptance line 442, 23-01 verification line 460, 23-02 Task 1 acceptance line 254, 23-02 verification line 387 |

---

## Warnings

### W-1 — D-07 `excluded_handlers` value uses anchored regex (deviates from CONTEXT literal)

- **Severity**: warning (technically improves correctness; deviates from locked text)
- **File**: `.planning/phases/23-metrics-primitives-metrics-endpoint/23-02-PLAN.md` line 189
- **Locked text** (`23-CONTEXT.md` line 118):
  ```python
  excluded_handlers=["/metrics", "/health/live"],
  ```
- **Plan text** (`23-02-PLAN.md` lines 189):
  ```python
  excluded_handlers=["^/metrics$", "^/health/live$"],
  ```
- **Rationale (planner)**: 23-RESEARCH §"Common Pitfalls" Pitfall 3 — `prometheus-fastapi-instrumentator` uses `re.search`, so unanchored `/metrics` would also match `/metrics-foo` and silently exclude legitimate routes. Anchoring is the correct behavior.
- **Assessment**: The deviation is technically superior and documented. However, the discussion phase locked exact strings, and a strict plan-checker should surface any divergence so the user can either (a) accept the planner's improvement and amend CONTEXT.md, or (b) require the literal values.
- **Recommended action** (one of):
  1. **Accept improvement** — add a one-line note to `23-CONTEXT.md` D-07 amending the kwarg to `["^/metrics$", "^/health/live$"]` with the Pitfall 3 citation. Plan stays as is.
  2. **Strict literal** — change 23-02 line 189 back to `["/metrics", "/health/live"]` (functionally identical for the two handlers in question since neither has a `-foo` collision risk in this app, but loses defense-in-depth for future `/health/live*`-prefixed routes).

This is **not a blocker** for execution — the discrepancy is between two valid implementations of the same intent.

---

## Spot-checks performed

- ✅ Middleware order (researcher finding #4): 23-02 add order `RequestLog → instrument(app) → CorrelationId → CORS` produces runtime stack `CORS(outer) → CorrelationId → Prometheus → RequestLog → routers` — Prometheus sits between CorrelationId and RequestLog as required (LIFO verified).
- ✅ TDD ordering: 23-01 Task 2 explicitly states "tests must FAIL with ImportError (RED phase). After Task 3, all 7 must pass (GREEN)" — proper RED→GREEN sequencing.
- ✅ File overlap: zero — no file appears in two plans simultaneously, so parallel execution of 23-01 + 23-03 in Wave 1 is safe.
- ✅ Verification commands: every plan's `<verification>` block contains runnable `pytest` invocations + boundary grep + (where applicable) mypy + lint guard.
- ✅ Boundaries: no plan touches `bin/*.py`, `scheduler/`, `services/`, `crawlers/`, or AI modules. Only `apps/prometheus/{pyproject.toml, src/localstock/observability/, src/localstock/api/app.py, tests/test_observability/}` and `docs/observability.md`.
- ✅ Test count reconciliation: 23-01 Task 2 transparently flags that the planning brief's "T1–T6" was approximate and matches VALIDATION.md's 7 unit tests verbatim — no silent scope drift.
- ✅ Plan 23-02 deviation from researcher's optional T9 (`test_metrics_endpoint_excludes_self_handler`) is explicitly called out (lines 286–294) with rationale ("redundant with body inspection; config-time enforcement via anchored regex"). Not a scope reduction — Nyquist contract requires only the 2 OBS-07 integration tests, both present.

---

## Recommendation

**Proceed to execute.** Plans are atomic, well-scoped, dependency-correct, and Nyquist-complete. Resolve W-1 by either amending CONTEXT.md (preferred — preserves the planner's correct improvement) or reverting the regex to literal strings before Wave 2 starts. Either path unblocks `/gsd-execute-phase 23`.

**Suggested execution order**:
- Wave 1 (parallel): `23-01` + `23-03`
- Wave 2: `23-02`
