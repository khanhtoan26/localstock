---
phase: 20-service-wiring-report-content
plan: 01
subsystem: reports
tags: [python, pure-functions, tdd, price-levels]

requires:
  - phase: 19-prompt-schema-restructuring
    provides: StockReport with 6 Optional fields (entry_price, stop_loss, target_price, risk_rating, catalyst, signal_conflicts)
provides:
  - compute_entry_zone() — (lower, upper) price range with fallback
  - compute_stop_loss() — max(support_2, close × 0.93)
  - compute_target_price() — nearest_resistance or close × 1.10
  - detect_signal_conflict() — Vietnamese conflict string when |gap| > 25
affects: [20-02-service-wiring]

tech-stack:
  added: []
  patterns: [pure-computation-functions, none-safe-guards, tdd-red-green]

key-files:
  created:
    - apps/prometheus/tests/test_reports/test_price_levels.py
  modified:
    - apps/prometheus/src/localstock/reports/generator.py

key-decisions:
  - "Entry zone fallback at < 40 rows or both indicators None → close ± 2%"
  - "Sanity guard: if lower >= upper, fallback to close ± 2%"
  - "Signal conflict gate at |gap| > 25 (strict greater-than, boundary 25 returns None)"

patterns-established:
  - "Pure computation functions: module-level, None-guard first line, no I/O"
  - "TDD flow: RED commit (failing tests) → GREEN commit (passing implementation)"
---

## What was built

4 pure computation functions added to `generator.py` for price level calculations and signal conflict detection:

1. **compute_entry_zone** — Returns (nearest_support, bb_upper) range; falls back to close ± 2% for insufficient data
2. **compute_stop_loss** — Returns max(support_2, close × 0.93) for HOSE ±7% limit awareness
3. **compute_target_price** — Returns nearest_resistance if available, else close × 1.10
4. **detect_signal_conflict** — Returns Vietnamese-formatted conflict string when |tech_score - fund_score| > 25

## Test coverage

22 unit tests in `test_price_levels.py` covering:
- Normal cases, fallback paths, None inputs, boundary conditions
- 4 test classes: TestComputeEntryZone (7), TestComputeStopLoss (4), TestComputeTargetPrice (3), TestDetectSignalConflict (8)

## Self-Check: PASSED

- [x] All 22 new tests pass
- [x] All 52 existing test_generator.py tests still pass
- [x] No regressions
- [x] Functions are pure (no I/O, no DB, no logging)

## Deviations

None — implemented exactly per plan.
