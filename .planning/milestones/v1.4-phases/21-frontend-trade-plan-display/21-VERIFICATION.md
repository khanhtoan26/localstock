---
phase: 21-frontend-trade-plan-display
verified: 2026-04-28T06:31:28Z
status: human_needed
score: 7/7
overrides_applied: 0
human_verification:
  - test: "Open /stock/VNM in browser — verify Trade Plan card appears between chart and score/report grid"
    expected: "Card with 'Kế Hoạch Giao Dịch' title shows entry zone, stop-loss, target price in VND format with % variance"
    why_human: "Visual layout positioning and VND formatting correctness require browser rendering"
  - test: "Hover/tap risk badge (Cao/Trung bình/Thấp) — verify tooltip appears with reasoning text"
    expected: "Colored pill badge (red/yellow/green) shows tooltip with report summary on hover"
    why_human: "Tooltip interaction behavior and color rendering need visual confirmation"
  - test: "Load a stock with signal_conflicts present in report — verify amber alert box appears"
    expected: "Yellow/amber alert box with ⚠️ icon and conflict text visible below price levels"
    why_human: "Conditional rendering requires real API data; visual styling needs human eye"
  - test: "Load a stock with a pre-v1.4 report (no trade plan fields) — verify Trade Plan section is completely absent"
    expected: "No Trade Plan card in DOM; page layout unaffected"
    why_human: "Graceful degradation requires real legacy data to confirm"
---

# Phase 21: Frontend Trade Plan Display Verification Report

**Phase Goal:** The stock detail page shows a dedicated Trade Plan section that surfaces entry zone, stop-loss, target price, risk badge, and signal conflict — all conditionally rendered from the existing report API response
**Verified:** 2026-04-28T06:31:28Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | TradePlanData interface exists with all required fields | ✓ VERIFIED | `types.ts:118-125` — interface with entry_price, stop_loss, target_price, risk_rating, signal_conflicts, catalyst |
| 2 | extractTradePlan() returns null when all price fields are null (pre-v1.4 backward compat) | ✓ VERIFIED | `trade-plan-section.tsx:35` — null return when all three prices null; 3 tests cover this case |
| 3 | extractTradePlan() returns typed TradePlanData from content_json with runtime narrowing | ✓ VERIFIED | `trade-plan-section.tsx:19-53` — typeof checks for each field, risk_rating validated against enum |
| 4 | TradePlanSection renders skeleton when loading, null when no data, full card when data present | ✓ VERIFIED | `trade-plan-section.tsx:182-197` skeleton, line 200 null return, lines 202-246 full card |
| 5 | Risk badge shows correct color class for high/medium/low with tooltip | ✓ VERIFIED | `trade-plan-section.tsx:55-60` riskColors map (red/yellow/green), lines 74-106 RiskBadge with Tooltip component |
| 6 | Signal conflict alert renders only when signal_conflicts is non-null | ✓ VERIFIED | `trade-plan-section.tsx:241` conditional `{tradePlan.signal_conflicts && <SignalConflictAlert ...>}` |
| 7 | All user-facing text uses next-intl translation keys | ✓ VERIFIED | All labels use `t("...")` calls; vi.json and en.json both contain `stock.tradePlan` with 11 keys |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/helios/src/lib/types.ts` | TradePlanData interface | ✓ VERIFIED | Lines 117-125, all 6 fields with proper types |
| `apps/helios/src/components/stock/trade-plan-section.tsx` | Main component + sub-components | ✓ VERIFIED | 247 lines, exports TradePlanSection + extractTradePlan + getRiskColors |
| `apps/helios/tests/trade-plan.test.ts` | Unit tests | ✓ VERIFIED | 83 lines, 11 tests covering extractTradePlan + getRiskColors |
| `apps/helios/messages/vi.json` | Vietnamese i18n keys | ✓ VERIFIED | tradePlan object with title, entryZone, stopLoss, targetPrice, risk levels, signalConflict, catalyst |
| `apps/helios/messages/en.json` | English i18n keys | ✓ VERIFIED | Matching English translations for all keys |
| `apps/helios/src/app/stock/[symbol]/page.tsx` | Page integration | ✓ VERIFIED | Import on line 16, render on line 195 with correct props |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `trade-plan-section.tsx` | `types.ts` | `import type { TradePlanData, StockReport }` | ✓ WIRED | Line 15 |
| `trade-plan-section.tsx` | `utils.ts` | `import { formatVND }` | ✓ WIRED | Line 14, used in PriceLevelRow line 132 |
| `page.tsx` | `trade-plan-section.tsx` | `import { TradePlanSection }` | ✓ WIRED | Line 16, rendered line 195-199 |
| `page.tsx` → `TradePlanSection` props | report + isLoading + currentClose | `report={reportQuery.data} isLoading={reportQuery.isLoading} currentClose={latest?.close ?? null}` | ✓ WIRED | Lines 196-198 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `trade-plan-section.tsx` | `report.content_json` | `reportQuery.data` from `useStockReport()` | Yes — API fetches from DB | ✓ FLOWING |
| `trade-plan-section.tsx` | `currentClose` | `latest?.close` from price query | Yes — from price history API | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| extractTradePlan returns null for empty | Unit test suite | 11/11 tests pass per summary | ? SKIP — no test runner available |
| Component exports | `grep "export function" trade-plan-section.tsx` | 3 exports found (extractTradePlan, getRiskColors, TradePlanSection) | ✓ PASS |
| TypeScript compilation | Per summary: `tsc --noEmit` passes | Clean compilation | ? SKIP — no Node.js build env |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| FRONTEND-01 | 21-01, 21-02 | Trade Plan section with entry zone, stop-loss, target price in VND | ✓ SATISFIED | PriceLevelRow uses formatVND(); 3 rows rendered in TradePlanSection |
| FRONTEND-02 | 21-01 | Colored risk badge (red/yellow/green) with tooltip | ✓ SATISFIED | RiskBadge component with riskColors map + Tooltip wrapper |
| FRONTEND-03 | 21-01 | Signal conflict conditionally rendered when non-null | ✓ SATISFIED | Conditional `{tradePlan.signal_conflicts && <SignalConflictAlert>}` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO, FIXME, placeholder, console.log, or stub patterns detected.

### Human Verification Required

### 1. Visual Layout Verification
**Test:** Open `/stock/VNM` (or any stock with v1.4+ report) in browser
**Expected:** Trade Plan card appears between chart/indicators section and score+report 2-column grid, with VND-formatted prices (e.g., 45.200đ) and % variance
**Why human:** Layout positioning and VND formatting correctness require browser rendering

### 2. Risk Badge Tooltip Interaction
**Test:** Hover/tap the risk badge (Cao/Trung bình/Thấp pill)
**Expected:** Colored pill (red for high, yellow for medium, green for low) shows tooltip with report summary text on hover
**Why human:** Tooltip interaction behavior and color rendering need visual confirmation

### 3. Signal Conflict Conditional Rendering
**Test:** Load a stock whose report has `signal_conflicts` populated
**Expected:** Yellow/amber alert box with ⚠️ icon and conflict text appears below price levels
**Why human:** Requires real API data with signal_conflicts; visual styling needs human eye

### 4. Graceful Degradation for Pre-v1.4 Reports
**Test:** Load a stock with pre-v1.4 report (all trade plan fields null)
**Expected:** Trade Plan section completely absent from DOM; no empty card or placeholder shown
**Why human:** Requires real legacy data to confirm; layout shift detection needs visual check

### Gaps Summary

No code-level gaps found. All artifacts exist, are substantive (no stubs), properly wired, and data flows through real API queries. All 3 requirements (FRONTEND-01, FRONTEND-02, FRONTEND-03) are satisfied at the code level.

Human verification is needed to confirm visual rendering, tooltip interaction, and graceful degradation behavior in a live browser environment.

---

_Verified: 2026-04-28T06:31:28Z_
_Verifier: the agent (gsd-verifier)_
