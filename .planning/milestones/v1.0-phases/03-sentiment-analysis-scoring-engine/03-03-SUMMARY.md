---
phase: 03-sentiment-analysis-scoring-engine
plan: "03"
subsystem: scoring
tags: [scoring, normalizer, composite-engine, tdd]
dependency_graph:
  requires: [03-01]
  provides: [scoring-normalizers, composite-engine, scoring-config]
  affects: [03-04]
tech_stack:
  added: []
  patterns: [multi-component-scoring, weight-redistribution, dataclass-config]
key_files:
  created:
    - src/localstock/scoring/config.py
    - src/localstock/scoring/normalizer.py
    - src/localstock/scoring/engine.py
    - tests/test_scoring/test_normalizer.py
    - tests/test_scoring/test_engine.py
  modified: []
decisions:
  - "5-component technical scoring (RSI, trend, MACD, BB, volume) each 0-20 points"
  - "4-component fundamental scoring (valuation, profitability, growth, health) each 0-25 points"
  - "Dynamic weight redistribution: missing dimensions cause proportional reallocation"
  - "ScoringConfig dataclass wraps Settings for typed access to scoring weights"
metrics:
  duration: "3min"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 0
  tests_added: 25
  tests_total: 147
requirements:
  - SCOR-01
  - SCOR-02
---

# Phase 03 Plan 03: Scoring Engine — Normalizers & Composite Summary

Multi-component normalizers (5 tech + 4 fundamental) converting raw indicators to 0-100 scores, with composite engine using configurable weight redistribution for missing dimensions.

## What Was Built

### ScoringConfig (`src/localstock/scoring/config.py`)
- Dataclass wrapping scoring weights from Settings
- `from_settings()` factory reads environment-configurable weights
- Defaults: tech=0.35, fund=0.35, sent=0.30, macro=0.0

### Technical Normalizer (`src/localstock/scoring/normalizer.py`)
- `normalize_technical_score(indicator_data: dict) -> float`: 5-component scoring
  - RSI positioning (0-20): thresholds at 30, 45, 55, 70
  - Trend alignment (0-20): uptrend=18, sideways=10, downtrend=3, +2 bonus for strong trend
  - MACD momentum (0-20): positive=14, zero=10, negative=4
  - Bollinger position (0-20): near lower=18, mid=10, near upper=3
  - Volume confirmation (0-20): high volume + uptrend=18, with bonus for increasing volume
- Returns 0.0 for all-None inputs (no crashes)

### Fundamental Normalizer (`src/localstock/scoring/normalizer.py`)
- `normalize_fundamental_score(ratio_data: dict) -> float`: 4-component scoring
  - Valuation P/E (0-25): thresholds at 10, 15, 25, 40
  - Profitability ROE+ROA (0-25): thresholds at 5, 10, 15, 20 with ROA adjustment
  - Growth profit_yoy+revenue_yoy (0-25): thresholds at -15, 0, 15, 30
  - Financial health D/E (0-25): thresholds at 0.5, 1.0, 2.0, 3.0
- Returns 0.0 for all-None inputs

### Sentiment Normalizer (`src/localstock/scoring/normalizer.py`)
- `normalize_sentiment_score(sentiment_avg: float) -> float`: linear 0-1 → 0-100

### Composite Engine (`src/localstock/scoring/engine.py`)
- `compute_composite(tech, fund, sent, macro, config)` → `(total_score, grade, dims_used, weights_dict)`
- Dynamic weight redistribution when dimensions are missing (missing dims → weights proportionally re-allocated)
- Division-by-zero guard when total_weight == 0 (T-03-07 mitigation)
- Grade mapping via `score_to_grade()` from Plan 01
- Returns actual normalized weights used for audit storage

## Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| test_normalizer.py | 15 | Tech oversold/overbought/neutral, all-None, empty; Fund strong/weak/all-None/empty; Sentiment scaling; Config from_settings |
| test_engine.py | 10 | All dimensions, missing sentiment, only tech, no dims, grade A/F, weights JSON, custom weights, macro, clamp |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a372bb8 | test | Add failing tests for scoring normalizers (RED) |
| 3276e6c | feat | Implement scoring normalizers and ScoringConfig (GREEN) |
| 60cce23 | test | Add failing tests for composite scoring engine (RED) |
| 44da6e2 | feat | Implement composite scoring engine with weight redistribution (GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **5-component technical scoring**: Each component 0-20 points matches plan specification exactly
2. **Dynamic weight redistribution**: `normalized_weights = {k: v / total_weight}` handles any combination of missing dimensions
3. **ScoringConfig dataclass pattern**: Clean separation of config from implementation, testable without Settings dependency

## Self-Check: PASSED
