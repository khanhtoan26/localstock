---
phase: 03-sentiment-analysis-scoring-engine
plan: 01
subsystem: data-layer
tags: [db-models, config, repositories, alembic, dependencies]
dependency_graph:
  requires: [02-04]
  provides: [NewsArticle, SentimentScore, CompositeScore, NewsRepository, SentimentRepository, ScoreRepository, ollama-config, scoring-weights]
  affects: [03-02, 03-03, 03-04]
tech_stack:
  added: [ollama>=0.6, beautifulsoup4>=4.14, lxml>=5.0]
  patterns: [repository-pattern, pydantic-settings, alembic-autogenerate]
key_files:
  created:
    - src/localstock/db/repositories/news_repo.py
    - src/localstock/db/repositories/sentiment_repo.py
    - src/localstock/db/repositories/score_repo.py
    - src/localstock/ai/__init__.py
    - src/localstock/scoring/__init__.py
    - tests/test_ai/__init__.py
    - tests/test_scoring/__init__.py
    - alembic/versions/c4007f49f9a7_add_phase3_sentiment_scoring_tables.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/localstock/config.py
    - src/localstock/db/models.py
decisions:
  - "URL as dedup key for NewsArticle (unique constraint on url column)"
  - "Scoring weights: 0.35 tech + 0.35 fundamental + 0.30 sentiment + 0.0 macro (Phase 4)"
  - "score_to_grade in scoring/__init__.py shared by Plan 02 and 03"
metrics:
  duration: 3min
  completed: 2026-04-15T11:35:40Z
  tasks: 2
  files: 12
---

# Phase 03 Plan 01: Phase 3 Foundation — Dependencies, Config, Models, Repositories Summary

**One-liner:** Data layer for sentiment/scoring pipeline — 3 ORM models, Alembic migration for news/sentiment/score tables, 3 repositories with pg_insert upsert, and 10 new config fields for Ollama and scoring weights.

## What Was Built

### Task 1: Dependencies, Config, DB Models, Migration, and Package Scaffolding
- Added `ollama>=0.6,<1.0`, `beautifulsoup4>=4.14,<5.0`, `lxml>=5.0,<6.0` to pyproject.toml
- Extended Settings with 10 new fields: Ollama host/model/timeout/keep_alive, 4 scoring weights, funnel_top_n, sentiment_articles_per_stock, sentiment_lookback_days
- Created **NewsArticle** model (news_articles table): URL dedup, published_at/source indexes
- Created **SentimentScore** model (sentiment_scores table): article_id+symbol unique constraint
- Created **CompositeScore** model (composite_scores table): symbol+date unique constraint, grade field (A-F), weights_json for recording scoring config
- All DateTime columns use `DateTime(timezone=True)` per Phase 1 UAT lesson
- Generated Alembic migration `c4007f49f9a7` with proper upgrade/downgrade
- Created `src/localstock/ai/__init__.py` (empty), `src/localstock/scoring/__init__.py` (with `score_to_grade` function), `tests/test_ai/__init__.py`, `tests/test_scoring/__init__.py`
- **Commit:** `7da0d53`

### Task 2: News, Sentiment, and Score Repositories
- Created **NewsRepository** with bulk_upsert (URL index_elements dedup), get_recent, get_by_url, get_unprocessed (anti-join on SentimentScore), count
- Created **SentimentRepository** with bulk_upsert (uq_sentiment_score constraint dedup), get_by_symbol, get_symbols_with_sentiment
- Created **ScoreRepository** with bulk_upsert (uq_composite_score constraint dedup), get_latest, get_top_ranked (auto-finds most recent date), get_by_date
- All follow existing IndicatorRepository pattern: AsyncSession constructor, pg_insert + on_conflict_do_update
- **Commit:** `16190d6`

## Verification Results

- ✅ All 3 new models importable from `localstock.db.models`
- ✅ Config: 10 new fields accessible via `get_settings()` with correct defaults
- ✅ All 3 repos importable from their modules
- ✅ Dependencies installed: `ollama`, `bs4`, `lxml` all import successfully
- ✅ Package scaffolding: `localstock.ai`, `localstock.scoring` importable
- ✅ `score_to_grade` function works correctly for all grade boundaries
- ✅ All 98 existing tests pass (`uv run pytest tests/ -x --timeout=30`)

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **URL as dedup key for NewsArticle** — unique constraint on `url` column, upsert via `index_elements=["url"]`
2. **Scoring weights default to 0.35/0.35/0.30/0.0** — macro_score weight is 0.0 until Phase 4 activates it
3. **score_to_grade placed in `scoring/__init__.py`** — shared utility for Plan 02 (scoring engine) and Plan 03 (composite scoring)

## Self-Check: PASSED

- All 9 created files verified on disk
- Both task commits (7da0d53, 16190d6) verified in git log
