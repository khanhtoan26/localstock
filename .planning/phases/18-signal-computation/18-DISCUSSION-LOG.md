# Phase 18: Signal Computation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 18-signal-computation
**Areas discussed:** Volume divergence output

---

## Volume Divergence Output

| Option | Description | Selected |
|--------|-------------|----------|
| MFI | Money Flow Index (0–100 oscillator, volume-weighted RSI). pandas-ta native. | ✓ |
| CMF | Chaikin Money Flow (-1 to +1). Measures buying/selling pressure over N days. | |
| OBV | On-Balance Volume (already computed by TechnicalAnalyzer). | |
| Composite of all three | Use all three, combine into a weighted signal. | |

**User's choice:** MFI as primary indicator

---

| Option | Description | Selected |
|--------|-------------|----------|
| Label + raw value | Dict: `{"signal": "bullish", "value": 72.3, "indicator": "MFI"}` | ✓ |
| Label only | Just a string: "bullish" / "bearish" / "neutral" | |
| Raw float only | Just the indicator value (e.g., 67.3) | |

**User's choice:** Label + raw value dict

---

| Option | Description | Selected |
|--------|-------------|----------|
| 70/30 symmetric | MFI > 70 = "bullish", MFI < 30 = "bearish", 30–70 = "neutral" | ✓ |
| 60/40 tighter neutral | MFI > 60 = "bullish", MFI < 40 = "bearish", 40–60 = "neutral" | |
| Claude decides | Let planner pick thresholds based on market data patterns | |

**User's choice:** 70/30 symmetric thresholds (consistent with RSI convention)

---

## Claude's Discretion

- Code structure (new class vs extend TechnicalAnalyzer) — not selected for discussion
- Liquidity threshold window (20-day vs 60-day avg_volume) — not selected for discussion
- Sector momentum definition — not selected for discussion
- Candlestick pattern pandas-ta vs pure math split — not selected for discussion

## Deferred Ideas

None
