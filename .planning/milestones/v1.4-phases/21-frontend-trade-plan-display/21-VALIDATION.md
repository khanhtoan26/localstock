# Phase 21: Frontend Trade Plan Display - Validation

**Extracted from:** 21-RESEARCH.md
**Date:** 2026-04-28

## Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (configured in apps/helios/vitest.config.ts) |
| Config file | `apps/helios/vitest.config.ts` |
| Quick run command | `cd apps/helios && npx vitest run --reporter=verbose` |
| Full suite command | `cd apps/helios && npx vitest run` |

## Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRONTEND-01 | extractTradePlan returns correct data from content_json | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "extract" --reporter=verbose` | ❌ Wave 0 |
| FRONTEND-01 | formatVND displays prices correctly | unit | Already covered by existing utils | ✅ |
| FRONTEND-02 | Risk badge maps rating to correct color class | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "risk" --reporter=verbose` | ❌ Wave 0 |
| FRONTEND-03 | extractTradePlan returns null for pre-v1.4 reports | unit | `cd apps/helios && npx vitest run tests/trade-plan.test.ts -t "null" --reporter=verbose` | ❌ Wave 0 |

## Sampling Rate
- **Per task commit:** `cd apps/helios && npx vitest run tests/trade-plan.test.ts --reporter=verbose`
- **Per wave merge:** `cd apps/helios && npx vitest run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

## Wave 0 Gaps
- [ ] `apps/helios/tests/trade-plan.test.ts` — covers FRONTEND-01, FRONTEND-02, FRONTEND-03 (extractTradePlan logic, risk color mapping, null handling)
