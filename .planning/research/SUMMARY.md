# Project Research Summary

**Project:** LocalStock v1.4 — AI Analysis Depth
**Domain:** Stock analysis — structured AI trade guidance for HOSE market
**Researched:** 2026-04-25
**Confidence:** HIGH

## Executive Summary

LocalStock v1.4 is a vertical enrichment of an existing, well-architected pipeline — not a greenfield build. The system already ingests OHLCV data for ~400 HOSE stocks, computes 26 technical indicators, scores stocks across 4 dimensions, and generates AI reports via a local Ollama LLM (qwen2.5:14b on RTX 3060). The v1.4 milestone adds four capabilities to make those reports actionable: candlestick pattern signals, volume divergence analysis, sector momentum context, and structured LLM outputs with concrete trade price levels.

**All required libraries are already installed. No new dependencies needed.**

The recommended approach is surgical modification of 5-6 existing files with no new top-level modules, no new API endpoints, and no new DB tables for signals. Signals route through the existing `indicator_data` dict into the LLM prompt. The expanded `StockReport` Pydantic model gains `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, and `signal_conflicts` — all grounded in already-stored support/resistance data. The `AnalysisReport.content_json` JSONB column absorbs new fields without any schema migration.

**The single biggest risk** is LLM price-level hallucination: the model will generate plausible-sounding but semantically invalid prices if support/resistance anchors are not made explicit in the prompt. Mitigation: mandatory post-generation validation (`stop_loss < entry_price < target_price`, all within ±30% of close) combined with prompt constraints naming exact S/R levels. **Second biggest risk:** context window overflow — `num_ctx` must be raised from 4096 to at least 6144 before adding new prompt sections.

## Key Findings

### Stack additions

**No new Python dependencies.** All v1.4 features use already-installed packages:
- **pandas-ta 0.4.71b0**: Native `cdl_doji()`, `cdl_inside()`, `mfi()`, `cmf()`, `obv()` confirmed
- **TA-Lib is NOT installed** and must not be required (C binary system dependency) — use 5 native + manual OHLC math for hammer, engulfing, shooting star (<50 lines each)
- **Ollama SDK + pydantic ≥2.13**: `Literal["high","medium","low"]` renders as enum constraint in format schema
- **One Alembic migration** covers all new DB columns if typed columns needed (optional — `content_json` JSONB absorbs new fields automatically)

### Feature table stakes (must ship v1.4)

| Feature | Approach | Complexity |
|---------|----------|------------|
| Entry zone | nearest_support + Bollinger band range | Low |
| Stop-loss | max(support_2, close × 0.93) — HOSE ±7% aware | Low |
| Target price | nearest_resistance or close × 1.10 | Low |
| Risk rating | LLM Literal["high","medium","low"] with reasoning | Medium |
| Signal conflict detection | Rule: abs(tech_score − fund_score) > 25 | Low |
| Candlestick patterns | 5 patterns: doji, inside, hammer, engulfing, shooting star | Medium |
| Structured StockReport schema | Expanded Pydantic model with Optional fields | Medium |
| Prompt restructuring | Rewrite with S/R anchors, num_ctx 6144+ | High |

### Feature differentiators (add after table stakes stable)

| Feature | Approach | Complexity |
|---------|----------|------------|
| Recent catalyst section | LLM synthesis from 7-day news + score delta | High |
| Volume divergence signal | MFI/CMF/OBV, gated on avg_volume ≥ 100k/day | Medium |
| Sector momentum in prompt | One-liner from SectorSnapshot.avg_score_change | Low |
| Frontend TradePlanSection | VND-formatted prices + risk badge + signal conflict | Medium |

### Features deferred to v2+

- Backtesting price-level accuracy
- TA-Lib 60-pattern integration
- Intraday signals / multi-timeframe analysis
- ML price prediction

### Architecture

**Two insertion points in the unchanged pipeline:**

1. **TechnicalAnalyzer** (`analysis/technical.py`): gains `detect_candlestick_patterns()` and `compute_volume_divergence()` — pure DataFrame methods, fully unit-testable
2. **ReportService** (`services/report_service.py`): injects new signals + sector momentum into `indicator_data` before LLM call

**No new API endpoints. No new DB tables. No new Python modules.**
`content_json` JSONB absorbs new fields automatically.

**Build order (each phase unblocks the next):**
1. Schema + DB migration (if typed columns) → signal computation methods
2. Expanded StockReport Pydantic model + prompt restructuring (highest risk — validate manually)
3. Service wiring: ReportService injects new signals into pipeline
4. Frontend: TradePlanSection on /stock/[symbol]

### Watch Out For

1. **LLM price hallucination** — inject exact S/R values in prompt; validate post-generation
2. **TA-Lib silent miss** — `cdl_pattern()` returns None silently; use only 5 native + manual math
3. **Context window overflow** — raise `num_ctx` to 6144+ before adding new content (current: 4096)
4. **StockReport backward compat** — all new fields must be `Optional[T] = None`
5. **Missing Alembic migration** — new columns must be migrated before first bulk upsert or `UndefinedColumn` crashes the batch
6. **Entry zone for low-liquidity stocks** — fallback to `close ± 2%` if <40 price history rows

## Recommended Phase Structure

**4 phases total:**

| Phase | Name | Goal | Risk |
|-------|------|------|------|
| 18 | Signal Computation | Candlestick patterns + volume divergence methods | Low |
| 19 | Prompt Restructuring | Expanded StockReport schema + new prompts + validation | High |
| 20 | Service Wiring | Full pipeline integration + sector momentum | Medium |
| 21 | Frontend Display | TradePlanSection on stock detail page | Low |

## Confidence Assessment

| Area | Level | Basis |
|------|-------|-------|
| Stack | HIGH | Live `uv run python` tests against installed packages |
| Features | HIGH | Codebase audit + HOSE market rules in existing code |
| Architecture | HIGH | Full read of all relevant service/model/repo files |
| Pitfalls | HIGH | Critical pitfalls verified via live environment tests |

---
*Research completed: 2026-04-25 — Ready for roadmap: yes*
