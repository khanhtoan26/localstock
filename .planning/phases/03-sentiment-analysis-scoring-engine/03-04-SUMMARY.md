---
phase: 03-sentiment-analysis-scoring-engine
plan: "04"
subsystem: services-api
tags: [services, api, scoring, sentiment, news, integration]
dependency_graph:
  requires: [03-01, 03-02, 03-03]
  provides: [scoring-api, news-api, sentiment-pipeline, scoring-pipeline]
  affects: [api/app.py]
tech_stack:
  added: []
  patterns: [service-orchestrator, api-router, session-based-repos]
key_files:
  created:
    - src/localstock/services/news_service.py
    - src/localstock/services/sentiment_service.py
    - src/localstock/services/scoring_service.py
    - src/localstock/api/routes/scores.py
    - src/localstock/api/routes/news.py
  modified:
    - src/localstock/api/app.py
decisions:
  - "Services follow AnalysisService pattern: __init__(session), run_full() -> dict"
  - "Scoring pipeline iterates all symbols, assigns rank by sorted total_score"
  - "Sentiment funnel filters to top-N stocks by preliminary tech+fund score"
  - "API routes use flat dict responses consistent with existing analysis.py pattern"
metrics:
  duration: "3min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 3 Plan 4: Services + API Integration Summary

Three service orchestrators wiring news crawl → LLM sentiment → composite scoring, plus 7 API endpoints for rankings, news, and sentiment

## What Was Built

### Task 1: Service Orchestrators

**NewsService** (`services/news_service.py`):
- `crawl_and_store(enrich=True)` — fetches RSS feeds, extracts tickers, bulk upserts articles
- Uses NewsCrawler for RSS fetch + parse, StockRepository for valid symbol validation
- Error isolation: catches exceptions per-crawl, returns summary dict

**SentimentService** (`services/sentiment_service.py`):
- `run_full()` — checks Ollama health → gets funnel candidates → classifies sentiment per article-ticker pair → stores scores
- `_get_funnel_candidates(top_n)` — ranks symbols by preliminary tech+fund normalized scores
- `get_aggregated_sentiment(symbol, days)` — returns time-decay weighted average (0-1)
- Limits tickers per article to 2 when >3 found (noise prevention)
- 0.5s rate limit between LLM calls

**ScoringService** (`services/scoring_service.py`):
- `run_full()` — normalizes all dimensions → computes composite → assigns ranks → bulk upserts
- `get_top_stocks(limit)` — returns ranked list with scores, grades, dimension breakdown
- Uses ScoringConfig.from_settings() for weight configuration
- Missing dimensions handled via compute_composite's weight redistribution

### Task 2: API Routes + App Integration

**Scores routes** (`api/routes/scores.py`):
- `GET /api/scores/top` — top-ranked stocks with grades and breakdown (SCOR-03), limit param (1-100)
- `GET /api/scores/{symbol}` — latest composite score for specific stock, 404 if not scored
- `POST /api/scores/run` — trigger full scoring pipeline

**News routes** (`api/routes/news.py`):
- `GET /api/news` — recent articles with days/limit params
- `GET /api/news/{symbol}/sentiment` — per-stock sentiment scores + aggregate, 404 if no data
- `POST /api/news/crawl` — trigger RSS news crawl
- `POST /api/sentiment/run` — trigger LLM sentiment analysis (skips gracefully if Ollama down)

**App integration**: `app.py` updated with `news_router` and `scores_router` via `include_router`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `65599bb` | Service orchestrators for news, sentiment, and scoring |
| 2 | `b4ae34e` | API routes for scores and news + app.py integration |

## Test Results

- **147 tests passing**, zero regressions
- All services importable
- All 13 API routes registered (6 existing + 7 new)

## Deviations from Plan

None — plan executed exactly as written.

## Requirements Addressed

| Requirement | Description | Status |
|-------------|-------------|--------|
| SENT-01 | News crawl pipeline (CafeF + VnExpress RSS) | ✅ Complete |
| SENT-02 | LLM sentiment classification with Ollama | ✅ Complete |
| SENT-03 | Per-ticker sentiment aggregation with time-decay | ✅ Complete |
| SCOR-01 | Multi-dimension composite scoring (0-100) | ✅ Complete |
| SCOR-02 | Configurable weights via environment variables | ✅ Complete |
| SCOR-03 | Ranked top-N list via API endpoint | ✅ Complete |

## Decisions Made

1. **Services follow AnalysisService pattern** — `__init__(session)` with repos created internally, `run_full() -> dict` async methods returning summary dicts
2. **Rank assignment by sorted total_score** — after all stocks scored, sort descending and assign 1-N ranks before bulk upsert
3. **Funnel uses preliminary tech+fund average** — simple average of normalized scores for top-N selection before expensive LLM calls
4. **API flat dict responses** — consistent with existing health.py and analysis.py patterns, no Pydantic response models

## Self-Check: PASSED
