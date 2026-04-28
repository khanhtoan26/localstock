# Phase 19: Prompt & Schema Restructuring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-26
**Phase:** 19-prompt-schema-restructuring
**Mode:** discuss (all areas delegated to Claude)
**Areas analyzed:** num_ctx value, Prompt signal injection, risk_rating field type, Validation fallback scope

## Gray Areas Presented

| Area | Options Presented | Decision |
|------|------------------|----------|
| num_ctx value | 6144 (minimum) vs 8192 (safer headroom) | Claude's Discretion → 8192 |
| Prompt signal injection | Dedicated new section vs inline; None → "N/A" vs omit | Claude's Discretion → dedicated section + "N/A" |
| risk_rating field type | Literal (strict, crash risk) vs str (permissive, normalize post-hoc) | Claude's Discretion → str + normalizer |
| Validation fallback scope | Price fields only vs all 6 new fields | Claude's Discretion → price fields only |

## User Direction

User delegated all four gray areas to Claude: "agent decide what best fix for every areas"

## Decisions Made (Claude's Discretion)

### num_ctx: 8192
- Qwen2.5 14B Q4_K_M uses ~8GB VRAM; 8192 context → ~9.5GB total, within RTX 3060 12GB
- 33% headroom over 6144 minimum — covers expanded prompt comfortably
- Sentiment stays at 4096 (short prompts, no expansion needed)

### Prompt injection: dedicated section + "N/A" for None
- New `🔔 TÍN HIỆU BỔ SUNG` block at end of REPORT_USER_TEMPLATE
- Groups all new context (S/R anchors, candlestick, volume divergence, sector momentum)
- None values rendered as "N/A" — omitting would leave LLM unaware the field exists

### risk_rating: str + post-hoc normalizer
- `Literal["high","medium","low"]` would crash entire report on LLM output variation
- `Optional[str]` with normalization table (handles "Cao"→"high", "High"→"high", etc.)
- System prompt explicitly instructs English lowercase output

### Validation fallback: price fields only
- Only `entry_price`, `stop_loss`, `target_price` are nulled on validation failure
- `risk_rating`, `catalyst`, `signal_conflicts` are preserved — valid LLM outputs unrelated to price failure
- Warning logged for observability

## Auto-Resolved

All gray areas auto-resolved via user delegation — no corrections applied.
