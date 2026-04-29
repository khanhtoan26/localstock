# DQ Tier 2 Promotion Runbook

> Phase 25 / DQ-03 (CONTEXT D-06). Operational procedure for promoting
> a Tier 2 advisory rule from **shadow** → **strict** (enforce) mode
> after the 14-day shadow window per CONTEXT D-03.

## Why this runbook exists

Phase 25 ships every Tier 2 rule (`rsi_anomaly`, `gap`, `missing_rows`)
in **shadow mode** by default. Shadow mode:

- Emits the Prometheus counter
  `localstock_dq_violations_total{rule, tier="advisory"}` on every fire,
  AND a structured `dq_warn` log line with `rule`, `tier`, `symbol`,
  `violation_count`.
- Does **NOT** block the pipeline — `evaluate_tier2` returns normally;
  data continues to flow.

After a 14-day observation window we may **promote** a rule to
**strict** (enforce) mode. Strict mode raises `Tier2Violation`, which
the per-symbol `try/except` added in 25-06 (DQ-05) catches and routes
into `PipelineRun.stats.failed_symbols`. The metric label flips from
`tier="advisory"` to `tier="strict"` so promotion is visible in the
same time series.

This runbook is also the audit trail: the **Per-Rule Status Table**
below records the current mode and the last promotion date for every
Tier 2 rule (mitigates threat T-25-07-02 in 25-07-PLAN).

## Promotion Criteria (must ALL hold)

A rule may be promoted shadow → strict if and only if:

1. The rule has been deployed in `tier="advisory"` for **≥ 14 calendar
   days** (CONTEXT D-03).
2. The 14-day violation rate (rows-flagged / rows-evaluated) is
   **< 5 %** — see Prometheus query below.
3. **No false-positive review** has been raised in the past 7 days
   (manual triage of `dq_warn` log entries).
4. Pre-flight: confirm the strict-tier series exists (label exemplar on
   advisory side has been seen — query for
   `localstock_dq_violations_total{rule="<name>", tier="advisory"}`
   non-zero in the last 24h).
5. AutomationService digest (Telegram daily) reviewed — no operator
   concern flagged for that rule.

## Procedure: shadow → strict (enforce)

1. **Observe** — run the 14-day Prometheus query:

   ```promql
   sum(rate(localstock_dq_violations_total{rule="<name>", tier="advisory"}[14d]))
     /
   sum(rate(localstock_dq_validation_total{validator="<name>", outcome="pass"}[14d]))
   ```

   Confirm the ratio is **< 0.05** (5 %).

2. **Flip the env flag** in production `.env`:

   ```
   DQ_TIER2_<NAME>_MODE=enforce
   ```

   e.g., `DQ_TIER2_RSI_MODE=enforce`. Available knobs:
   - `DQ_TIER2_RSI_MODE` (rule key: `rsi`)
   - `DQ_TIER2_GAP_MODE` (rule key: `gap`)
   - `DQ_TIER2_MISSING_MODE` (rule key: `missing`)
   - `DQ_DEFAULT_TIER2_MODE` — global default for any unmatched rule.

3. **Restart** the API + scheduler pods so `Settings` re-loads.
   `get_settings.cache_clear()` is invoked automatically on the next
   request boundary.

4. **Verify** — within 1 hour, Prometheus shows
   `localstock_dq_violations_total{rule="<name>", tier="strict"}`
   beginning to populate. The matching `tier="advisory"` series stops
   incrementing.

5. **Watch the next pipeline run** — `PipelineRun.stats.failed_symbols`
   should contain entries with `step="analyze"` and an error message
   referencing `Tier2Violation` for any symbols whose rows triggered
   the rule.

6. Update the **Per-Rule Status Table** below with the promotion date
   and any operator notes.

## Rollback (strict → shadow)

If post-promotion the analysis step fails for **> 30 % of symbols**
(Pitfall C in 25-RESEARCH.md — premature hard-gate), roll back
immediately:

1. Set `DQ_TIER2_<NAME>_MODE=shadow` in the deployed `.env` (or unset
   the variable — the global default `DQ_DEFAULT_TIER2_MODE=shadow`
   takes over).
2. Restart API + scheduler.
3. Confirm `tier="strict"` series stops incrementing within 30 min.
4. Open a debug ticket — capture the offending payloads from the
   `dq_warn` logs and investigate the false-positive surface before
   re-attempting promotion.

## Per-Rule Status Table

| Rule          | Current Mode | Last Promoted | Notes                                                          |
| ------------- | ------------ | ------------- | -------------------------------------------------------------- |
| `rsi_anomaly` | shadow       | —             | RSI > 99.5; pandas-ta computed; expect rare in healthy markets |
| `gap`         | shadow       | —             | close-to-close > 30%; split adjustments may inflate            |
| `missing_rows`| shadow       | —             | > 20% of expected sessions missing in window                   |

## References

- `25-CONTEXT.md` D-06 (per-rule env flags), D-03 (14-day shadow window).
- `25-RESEARCH.md` §Pattern 2 (dispatcher) and §Pitfall C (Tier 2 hard-gate).
- `25-07-PLAN.md` (this plan — closes ROADMAP SC #4 verbatim).
- Source: `apps/prometheus/src/localstock/dq/shadow.py`,
  `apps/prometheus/src/localstock/dq/runner.py`.
