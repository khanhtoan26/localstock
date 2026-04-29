---
status: resolved
trigger: "The Trade Plan is not consistency after run pipeline, sometime missing trade plan. Fix it"
created: 2026-04-29
updated: 2026-04-29
goal: find_and_fix
---

# Debug Session: trade-plan-missing-after-pipeline

## Symptoms

- **Expected**: After a successful daily pipeline run, every analyzed stock's report should include a Trade Plan section in the UI with entry/stop-loss/target prices populated.
- **Actual**: Some stocks' Trade Plan section is completely hidden because `content_json.entry_price`, `stop_loss`, and `target_price` are all `null`. Frontend `extractTradePlan` returns `null` and the component renders nothing.
- **Inconsistency**: Varies between symbols within the same run; same symbol may vary across runs.
- **Errors**: None — silent data drop.
- **Reproduction**: Inspect `/api/reports/{symbol}` for multiple symbols after pipeline; some have prices, others null.

## Current Focus

reasoning_checkpoint:
  hypothesis: "_validate_price_levels nulls all three prices when deterministic entry_price and stop_loss round to equal values (HPG 2026-04-29: ep=27.5, sl=27.5). The auto-correct swap only fires on strict inversion (sl > ep), and the final check `sl < ep < tp` rejects ties — triggering _null_prices() which silently zeroes the trade plan."
  confirming_evidence:
    - "Repro with HPG inputs (close=27.65, nearest_support=26.05, bb_upper=28.91, support_2=27.52): entry_price=27.48 → 27.5; stop_loss=max(27.52, 25.71)=27.52 → 27.5; logger emits 'Price validation failed: stop_loss=27.5, entry=27.5, target=29.4' and returns (None, None, None)."
    - "DB row analysis_reports(HPG, 2026-04-29) has ep/sl/tp = null but risk_rating='medium' and signal_conflicts populated — the exact signature of _null_prices() per D-10."
    - "DB by-date breakdown: 2026-04-29 1/3 null, 2026-04-28 1/10. Inconsistency confirmed."
  falsification_test: "After the fix, repro with same HPG inputs should yield non-None prices satisfying sl < ep < tp. Verified: entry_price=27.5, stop_loss=27.4, target_price=29.4."
  fix_rationale: "Add enforce_price_ordering(report) helper called after deterministic injection and before _validate_price_levels. Nudges stop_loss down by 0.1 when sl ≥ ep, and target_price up by 0.1 when tp ≤ ep. Fixes ties at the trusted-deterministic layer rather than letting the LLM-output validator null them."
  blind_spots: "Older runs (2026-04-22 to 2026-04-24) had 100% null prices, suggesting a separate historical bug pre-deterministic injection. Forward-only fix. The 0.1 nudge assumes VND-thousands price scale used throughout the codebase."
  next_action: "(complete)"

## Eliminated

- hypothesis: "LLM occasionally omits entry_price/stop_loss/target_price"
  evidence: "Deterministic post-LLM injection (report_service.py:301-306, 536-541) ALWAYS overrides LLM values when current_close is non-None. LLM output is irrelevant when injection runs."
  timestamp: 2026-04-29

- hypothesis: "compute_target_price returns nearest_resistance > 30% above close → range-check fails"
  evidence: "HPG nearest_resistance=29.4 vs close=27.65 → 6.3% diff, well within ±30%."
  timestamp: 2026-04-29

- hypothesis: "Missing latest_price (current_close=None) skips injection, LLM None values persist"
  evidence: "HPG has 506 price records. The exact null signature (3 prices null, others preserved) requires _validate_price_levels to have run, which only happens when current_close is non-None."
  timestamp: 2026-04-29

## Evidence

- timestamp: 2026-04-29
  checked: "reports/generator.py compute_entry_zone, compute_stop_loss, compute_target_price, _validate_price_levels"
  found: "Three independent compute_* helpers; auto-correct swaps only fire on strict inversion (sl > ep, ep > tp), not on ties (sl == ep)."
  implication: "Tie scenarios silently fall through to _null_prices()."

- timestamp: 2026-04-29
  checked: "DB content_json for HPG 2026-04-29"
  found: "entry_price/stop_loss/target_price all null; risk_rating='medium' and signal_conflicts populated; summary text mentions LLM-suggested entry of 27,650 VND."
  implication: "Exact signature of _validate_price_levels._null_prices() per D-10."

- timestamp: 2026-04-29
  checked: "HPG technical_indicators (date=2026-04-29, computed_at=04:22:48 UTC) and price (close=27.65); report generated_at=04:26:31 UTC"
  found: "nearest_support=26.05, bb_upper=28.908, support_2=27.52, nearest_resistance=29.4. Indicators were available 4 minutes before report generation."
  implication: "Inputs to compute_* are healthy; problem is in the validation/ordering check downstream."

- timestamp: 2026-04-29
  checked: "Direct repro: compute_entry_zone(26.05, 28.908, 27.65, 506) + compute_stop_loss(27.52, 27.65) + compute_target_price(29.4, 27.65) → inject → _validate_price_levels(close=27.65)"
  found: "midpoint 27.5; stop_loss 27.5; target 29.4. Validation logs 'Price validation failed: stop_loss=27.5, entry=27.5, target=29.4, close=27.65' and returns all None."
  implication: "Root cause confirmed: tie at .1 rounding precision."

- timestamp: 2026-04-29
  checked: "Same repro with enforce_price_ordering inserted between injection and validation"
  found: "stop_loss=27.4, entry_price=27.5, target_price=29.4. Validation passes. All three preserved."
  implication: "Fix verified at unit level."

## Resolution

- root_cause: "_validate_price_levels nulls all three deterministic prices (entry_price, stop_loss, target_price) when the independent compute_entry_zone-midpoint and compute_stop_loss values round to the same .1-precision number — the auto-correct swap only fires on strict inversion (sl > ep), so ties (sl == ep) fall through to the strict ordering check `sl < ep < tp`, fail it, and trigger _null_prices(). The frontend extractTradePlan then returns null and silently hides the Trade Plan section."

- fix: |
    Added enforce_price_ordering(report) helper in
    apps/prometheus/src/localstock/reports/generator.py that nudges stop_loss
    down by 0.1 when sl >= ep, and nudges target_price up by 0.1 when tp <= ep.
    Invoked in apps/prometheus/src/localstock/services/report_service.py in
    BOTH report-generation paths (run_full and generate_for_symbol) after
    deterministic price injection and before _validate_price_levels.

- verification: |
    1. Reproduction script with HPG 2026-04-29 inputs:
       - Before fix: (None, None, None) — Trade Plan hidden.
       - After fix:  stop_loss=27.4, entry_price=27.5, target_price=29.4 — passes.
    2. Targeted tests: 94 passed (test_reports/* + test_services/test_report_service.py),
       including 8 new regression tests in TestEnforcePriceOrdering covering
       equal sl/ep nudge, inverted sl/ep nudge, equal/inverted tp/ep nudge,
       partial-None and all-None safety, and full inject+enforce+validate
       end-to-end HPG regression.
    3. Full suite: 528 passed, 0 failed (520 baseline + 8 new).

- files_changed:
  - apps/prometheus/src/localstock/reports/generator.py
  - apps/prometheus/src/localstock/services/report_service.py
  - apps/prometheus/tests/test_reports/test_generator.py
