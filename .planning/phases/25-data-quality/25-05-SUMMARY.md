---
phase: 25-data-quality
plan: 05
subsystem: data-quality
tags: [pandera, tier1, quarantine, ohlcv, dq-01]
requires: [25-01, 25-02, 25-03, 25-04]
provides: [OHLCVSchema, partition_valid_invalid, _coerce_payload, tier1_reject_to_quarantine]
affects: [services/pipeline.py:_crawl_prices, dq/schemas/ohlcv.py, dq/runner.py]
tech_stack:
  added: []
  patterns:
    - "Pandera lazy validation + per-row partition (RESEARCH §Pattern 1)"
    - "Reject-to-quarantine with rule classification + Counter increment per rule"
    - "JSON-boundary value coercion (_coerce_payload) for pandas/numpy scalars"
key_files:
  created: []
  modified:
    - apps/prometheus/src/localstock/dq/schemas/ohlcv.py
    - apps/prometheus/src/localstock/dq/runner.py
    - apps/prometheus/src/localstock/services/pipeline.py
    - apps/prometheus/tests/test_dq/test_ohlcv_schema.py
    - .planning/ROADMAP.md
decisions:
  - "OHLCVSchema is the single Tier 1 strict pandera schema; date column does NOT use coerce — caller pre-coerces with pd.to_datetime + explicit malformed_date Check (Pitfall E)"
  - "_crawl_prices builds a validation-shaped frame (rename time→date, inject symbol col) for OHLCVSchema then drops bad indices from the original (time-keyed) frame before upsert_prices — separation prevents the Tier 1 schema from leaking into the upsert contract"
  - "_normalize_rule maps pandera check names to CONTEXT D-01 vocabulary so quarantine_rows.rule is queryable by category (negative_price/non_positive_<col>, future_date, nan_ratio_exceeded, malformed_date, duplicate_pk, bad_symbol_format)"
  - "Frame-level checks failing in lazy mode invalidate every row in the batch (per-symbol scope keeps blast radius bounded)"
  - "_coerce_payload (Rule 1 fix) handles pd.Timestamp / datetime / numpy scalars at the QuarantineRepository.insert json.dumps boundary — sanitize_jsonb still owns NaN/Inf scrubbing (DQ-04 belt-and-suspenders)"
metrics:
  duration: ~25 minutes
  completed: 2026-04-29
  tasks_completed: 2
  files_modified: 4
---

# Phase 25 Plan 05: DQ-01 OHLCV Tier-1 Reject-to-Quarantine Summary

**One-liner:** Pandera Tier-1 `OHLCVSchema` + `partition_valid_invalid` runner wired into `Pipeline._crawl_prices` — bad OHLCV rows divert to `quarantine_rows{tier='strict'}` instead of `stock_prices` and increment `localstock_dq_violations_total{rule, tier='strict'}`, closing **verbatim ROADMAP Success Criterion #1**.

## What Shipped

### `dq/schemas/ohlcv.py` (Tier 1 strict)

`OHLCVSchema = DataFrameSchema(...)` declares the per-column truth:

| Column | Type | Check |
|--------|------|-------|
| `symbol` | `str` | matches `^[A-Z0-9]{3,5}$` |
| `date` | `datetime64[ns]` | **no coerce** — Pitfall E (caller pre-coerces) |
| `open`/`high`/`low`/`close` | `float` | `> 0` |
| `volume` | `int` | `>= 0` |

Frame-level checks (lazy):
- `future_date` (element-wise via `df["date"].dt.date <= today`)
- `nan_ratio_exceeded` (frame-level scalar — max per-column NaN ratio ≤ 5%)
- `malformed_date` (echo of Pitfall E — explicit `notna()` after upstream coercion)

`unique=["symbol","date"]`, `strict=True`, `coerce=True` for numerics.

### `dq/runner.py`

- `partition_valid_invalid(df, schema)` runs `schema.validate(df, lazy=True)`, catches `pae.SchemaErrors`, builds:
  - per-row rule map from `failure_cases` rows with non-NaN index
  - frame-level rule list (NaN index) — applied to **all** rows
  - `invalid_rows: list[dict]` — each entry flattens row data + adds `{rule, reason, all_rules, row}` metadata
  - `valid_df` — drops every bad index
- `_normalize_rule(check_name, column)` — maps pandera check names → CONTEXT D-01 canonical rule strings (`non_positive_open`, `future_date`, `nan_ratio_exceeded`, `malformed_date`, `duplicate_pk`, `bad_symbol_format`, `negative_price`, …).
- `_coerce_payload(row)` — Rule 1 helper: converts `pd.Timestamp`/`datetime`/`date`/numpy scalars to JSON-serializable scalars before the QuarantineRepository → `json.dumps` boundary.

### `services/pipeline.py:_crawl_prices`

Between `price_crawler.fetch` and `price_repo.upsert_prices`:

1. Build a **validation-shaped frame** (copy + rename `time→date`, coerce date dtype, inject `symbol` column).
2. Call `partition_valid_invalid(validation_df, OHLCVSchema)`.
3. For each invalid row:
   - `QuarantineRepository(self.session).insert(source='ohlcv', symbol=symbol, payload=item['row'], reason=item['reason'], rule=item['rule'], tier='strict')`
   - aggregate per-rule counts.
4. After the loop, look up `localstock_dq_violations_total` via `REGISTRY._names_to_collectors` and `inc(n)` per rule with `tier='strict'`.
5. Drop bad indices from the **original** time-keyed frame, then `upsert_prices(symbol, df)` only on the survivors.
6. If the frame becomes empty, short-circuit with `continue`.

## Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_dq/test_ohlcv_schema.py` | 4 unit (negative_price / future_date / nan_ratio / duplicate_pk) + 1 `requires_pg` integration (`test_quarantine_destination_for_bad_ohlcv_row`) | **5/5 GREEN** |
| `tests/test_dq/test_quarantine_repo.py` (regression) | 3/3 | GREEN |
| `tests/test_services/` (regression) | 24/24 (pipeline) + others | GREEN |

The 4 `test_ohlcv_schema.py` tests transitioned **RED → GREEN** as required by the TDD gate. The integration test asserts:
- `quarantine_rows` has exactly 1 row for the bad symbol with `tier='strict'`, `source='ohlcv'`, and `rule ∈ {non_positive_open, negative_price}`.
- `stock_prices` has the good row’s date but **not** the bad row’s date.

## ROADMAP SC #1 — Closure

> **SC #1 (verbatim):** "Pandera Tier 1 reject row OHLCV với negative price / future date / NaN ratio > threshold / duplicate `(symbol,date)` PK — row đi vào `quarantine_rows` table thay vì `stock_prices`."

**Closed.** All four reject conditions are encoded in `OHLCVSchema`, the integration test exercises the negative-price branch end-to-end through the pipeline, and the quarantine destination + tier label are verified against live PG.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `pd.Timestamp` payloads broke `json.dumps` in QuarantineRepository.insert**
- **Found during:** Task 2 — first run of integration test surfaced
  `TypeError: Object of type Timestamp is not JSON serializable`.
- **Issue:** `df.loc[i].to_dict()` returns `pd.Timestamp` for the `date` column; `QuarantineRepository.insert` flows the payload through `sanitize_jsonb` (which only handles NaN/Inf) and then `json.dumps` (which can't serialize Timestamp).
- **Fix:** Added `_coerce_payload(row)` in `dq/runner.py` to convert `pd.Timestamp`/`datetime`/`date`/numpy scalars to native JSON-serializable scalars. Applied only to the `row` payload field (used as the quarantine `payload` argument). Did **not** modify `sanitize_jsonb` itself — kept Tier 1 fix narrow to avoid risking DQ-04 regression. Bug + fix flagged with `# Rule 1 / DQ-04 belt-and-suspenders` comment.
- **Files modified:** `apps/prometheus/src/localstock/dq/runner.py`
- **Commit:** `e38b87e`

### Plan-level adjustments

- **Schema imports:** Plan suggested `from pandera import Check, Column, DataFrameSchema` + `import pandera.pandas`. Pandera 0.31.1 emits a `FutureWarning` for top-level `pandera.X` imports — switched to `from pandera.pandas import Check, Column, DataFrameSchema` to silence the warning without changing semantics.
- **Schema check style:** `nan_ratio_exceeded` returns a scalar bool (`bool(df.isna().mean().max() <= 0.05)`) explicitly to match pandera's frame-level check expectations and avoid an array-truthiness ambiguity.
- **Integration test fixture:** Plan referenced a `db_session` fixture local to `test_quarantine_repo.py`. Re-wrote the integration test as fully self-contained (creates its own engine + session + cleanup pre/post) so it runs in `test_ohlcv_schema.py` without cross-file fixture coupling.
- **Symbol used in integration test:** `ZZZ` (synthetic) instead of `AAA` to keep tests collision-free with real HOSE data already populated in dev DB.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (Wave 0 / 25-01) | (pre-existing scaffolds) | ✓ |
| GREEN — schema + runner | `8c3e814` `feat(25-05): implement OHLCVSchema (Tier 1) + partition_valid_invalid` | ✓ |
| GREEN — pipeline wiring + integration | `e38b87e` `feat(25-05): wire reject-to-quarantine into Pipeline._crawl_prices (DQ-01, SC #1)` | ✓ |
| REFACTOR | n/a | skipped (no refactor needed) |

## Commits

| Hash | Message |
|------|---------|
| `8c3e814` | `feat(25-05): implement OHLCVSchema (Tier 1) + partition_valid_invalid` |
| `e38b87e` | `feat(25-05): wire reject-to-quarantine into Pipeline._crawl_prices (DQ-01, SC #1)` |

## Watch-outs for Downstream Plans

- **25-06 (DQ-05 isolation):** the per-symbol try/except wrapper should NOT swallow `pae.SchemaErrors` — those never escape `partition_valid_invalid` (caught + classified inside the runner). The wrapper's job is the broader unhandled-exception layer.
- **25-07 (Tier 2 advisory):** `evaluate_tier2(...)` still raises `NotImplementedError`. The Tier 2 schema can reuse `_normalize_rule` and `_coerce_payload` if needed.
- **Schema strictness:** `strict=True` will reject any new column the crawler starts emitting. Whitelist additions must be conscious; otherwise good rows will quarantine wholesale.
- **Per-symbol scope (Pitfall):** validation runs per-symbol; do NOT hoist into a multi-symbol batch — the unique-PK + frame-level NaN ratio checks are intentionally scoped per-call.

## Self-Check: PASSED

- [x] `apps/prometheus/src/localstock/dq/schemas/ohlcv.py` — present, ≥40 LOC.
- [x] `apps/prometheus/src/localstock/dq/runner.py` — present, ≥50 LOC, contains `partition_valid_invalid`.
- [x] `apps/prometheus/src/localstock/services/pipeline.py` — contains `OHLCVSchema`, `partition_valid_invalid`, `QuarantineRepository`, `tier="strict"`.
- [x] Commit `8c3e814` reachable from HEAD (`git log --oneline | grep 8c3e814`).
- [x] Commit `e38b87e` reachable from HEAD.
- [x] 4 RED tests + 1 integration test all GREEN (`5 passed in 5.04s`).
- [x] `uvx ruff check` clean across all modified files.
- [x] No regressions in `tests/test_dq/test_quarantine_repo.py` (3/3) or `tests/test_services/` (24+ pass; 1 pre-existing `test_pipeline_isolation.py` RED for 25-06 is expected and untouched).

Verbatim ROADMAP **Success Criterion #1: ✅ closed.**
