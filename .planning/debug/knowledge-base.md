# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## trade-plan-missing-after-pipeline — Trade Plan section silently hidden after pipeline runs (entry_price/stop_loss/target_price all null in content_json)
- **Date:** 2026-04-29
- **Error patterns:** trade plan, entry_price, stop_loss, target_price, content_json, missing, null, _validate_price_levels, _null_prices, deterministic price levels, ordering, rounding tie
- **Root cause:** `_validate_price_levels` nulls all three deterministic prices when `compute_entry_zone` midpoint and `compute_stop_loss` round to equal values at .1 precision — auto-correct swap only fires on strict inversion (sl > ep), ties fall through to `sl < ep < tp` strict-check, fail, and trigger `_null_prices()`. Frontend `extractTradePlan` returns null and hides the Trade Plan section.
- **Fix:** Added `enforce_price_ordering(report)` helper in `reports/generator.py` invoked after deterministic injection and before `_validate_price_levels` in both `run_full` and `generate_for_symbol`. Nudges stop_loss down by 0.1 when sl ≥ ep, target_price up by 0.1 when tp ≤ ep.
- **Files changed:** apps/prometheus/src/localstock/reports/generator.py, apps/prometheus/src/localstock/services/report_service.py, apps/prometheus/tests/test_reports/test_generator.py
---
