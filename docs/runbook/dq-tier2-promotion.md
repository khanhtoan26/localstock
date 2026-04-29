# DQ Tier 2 Promotion Runbook

> Phase 25 / DQ-03 placeholder — full content lands in 25-07-PLAN.md.
> Per CONTEXT.md D-06: per-rule env flag promotion after 14-day shadow window.

## Status

PLACEHOLDER — see 25-07 for the full procedure.

## Promotion Criteria

<!-- TODO: filled in 25-07 — read dq_violations_total{rule, tier="advisory"}
     over the 14-day shadow window. Promote if violation rate < 5%. -->

## Shadow → Strict

<!-- TODO: filled in 25-07 — set DQ_TIER2_<RULE>_MODE=enforce in .env,
     restart prometheus app, watch dq_violations_total{tier="strict"}. -->

## Rollback

<!-- TODO: filled in 25-07 — unset DQ_TIER2_<RULE>_MODE (back to shadow),
     restart, file an incident with the captured payloads. -->
