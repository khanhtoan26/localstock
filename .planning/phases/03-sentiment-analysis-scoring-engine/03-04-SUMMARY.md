# Plan 03-04 Summary: Services + API + Integration

## Status: COMPLETE

## Tasks Completed

### Task 1: Service orchestrators (news, sentiment, scoring)
- **NewsService** (`services/news_service.py`): crawl RSS feeds → extract tickers → bulk upsert articles
- **SentimentService** (`services/sentiment_service.py`): Ollama health check → funnel candidates → LLM classify → aggregate with time-decay
- **ScoringService** (`services/scoring_service.py`): normalize dimensions → compute composite → assign ranks → store
- All follow AnalysisService pattern: `__init__(session)`, `run_full() -> dict`

### Task 2: API routes + app integration
- **News routes** (`api/routes/news.py`):
  - `GET /api/news` — recent articles with pagination
  - `GET /api/news/{symbol}/sentiment` — per-stock sentiment scores + aggregate
  - `POST /api/news/crawl` — trigger RSS crawl
  - `POST /api/sentiment/run` — trigger LLM sentiment
- **Scores routes** (`api/routes/scores.py`):
  - `GET /api/scores/top` — ranked stocks with grades (SCOR-03)
  - `GET /api/scores/{symbol}` — individual composite score
  - `POST /api/scores/run` — trigger full scoring pipeline
- Updated `app.py` to include both new routers

## Commits
- `65599bb`: feat(03-04): service orchestrators for news, sentiment, and scoring
- `b4ae34e`: feat(03-04): add news and scores API routes with app integration

## Test Results
- 147 tests passing, zero regressions

## Requirements Addressed
- **SENT-01**: News crawl pipeline (CafeF + VnExpress RSS)
- **SENT-02**: LLM sentiment classification with Ollama
- **SENT-03**: Per-ticker sentiment aggregation
- **SCOR-01**: Multi-dimension composite scoring
- **SCOR-02**: Configurable weights
- **SCOR-03**: Ranked top-N list via API

## Files Created
- `src/localstock/services/news_service.py` (88 lines)
- `src/localstock/services/sentiment_service.py` (192 lines)
- `src/localstock/services/scoring_service.py` (163 lines)
- `src/localstock/api/routes/news.py` (105 lines)
- `src/localstock/api/routes/scores.py` (75 lines)

## Files Modified
- `src/localstock/api/app.py` — added news_router and scores_router
