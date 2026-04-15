---
phase: 03-sentiment-analysis-scoring-engine
plan: "02"
subsystem: sentiment-analysis
tags: [news-crawler, rss, ollama, sentiment, llm, ai-client, time-decay]
dependency_graph:
  requires: [03-01]
  provides: [news-crawler, ollama-client, sentiment-aggregation, sentiment-prompts]
  affects: [03-03, 03-04]
tech_stack:
  added: [httpx, beautifulsoup4, ollama, tenacity]
  patterns: [rss-parsing, html-sanitization, exponential-decay, structured-llm-output, pydantic-schema-validation]
key_files:
  created:
    - src/localstock/crawlers/news_crawler.py
    - src/localstock/ai/client.py
    - src/localstock/ai/prompts.py
    - src/localstock/analysis/sentiment.py
    - tests/test_crawlers/test_news_crawler.py
    - tests/test_analysis/test_sentiment.py
    - tests/test_ai/test_client.py
  modified: []
decisions:
  - "NewsCrawler standalone class (not extending BaseCrawler) — RSS feeds are not per-symbol"
  - "SentimentResult Pydantic model as Ollama format schema — structured JSON output validation"
  - "Exponential time decay with 3-day half-life for sentiment aggregation — prevents stale news dominance"
  - "2000-char article truncation — limits prompt injection surface and context overflow"
  - "NON_TICKERS set filters GDP, USD, CPI etc. from ticker extraction — reduces false positives"
metrics:
  duration: 4min
  completed: "2026-04-15T11:43:00Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 24
  tests_passing: 122
  files_created: 7
  files_modified: 0
---

# Phase 03 Plan 02: News Crawler + AI Sentiment Analysis Summary

RSS-first news crawler for CafeF/VnExpress with Ollama-powered sentiment classification and exponential time-decay aggregation.

## What Was Built

### Task 1: News Crawler — RSS Feed Parsing, Article Extraction, Ticker Extraction

**Commits:** `ab3c086` (RED), `33611d8` (GREEN)

Built the `NewsCrawler` class as a standalone crawler (not extending `BaseCrawler`) that:
- Crawls 4 CafeF RSS feeds + 1 VnExpress RSS feed
- Parses RSS XML via `xml.etree.ElementTree`
- Extracts and sanitizes HTML from RSS description fields (T-03-03 mitigation)
- Identifies stock tickers from article text using regex + NON_TICKERS filter + validation against known symbols
- Fetches full article content with CSS selectors (`div.detail-content` for CafeF, `article.fck_detail` for VnExpress)
- Applies anti-bot headers (User-Agent, Accept-Language) per Pitfall 2
- Truncates article text to 2000 chars per Pitfall 1

**Key functions:**
- `parse_rss_feed()` — Parse RSS XML to list of article dicts
- `extract_tickers()` — Regex + NON_TICKERS + valid_symbols filtering
- `sanitize_html()` — BeautifulSoup strip all HTML tags
- `parse_rss_date()` — RFC 2822 date parsing with fallback
- `NewsCrawler.crawl_feeds()` — Async RSS feed fetching
- `NewsCrawler.enrich_articles()` — Full article content extraction

### Task 2: Ollama AI Client + Sentiment Prompts + Sentiment Aggregation

**Commits:** `e2e980e` (RED), `0e6be7a` (GREEN)

Built the AI sentiment analysis pipeline:

1. **`src/localstock/ai/prompts.py`** — Vietnamese sentiment classification system prompt (T-03-01: constrains LLM to article content only, no external reasoning)

2. **`src/localstock/ai/client.py`** — `OllamaClient` wrapper with:
   - `SentimentResult` Pydantic model (`sentiment`, `score`, `reason`) for structured JSON output (D-03)
   - `health_check()` — Ollama server availability check (Pitfall 4)
   - `classify_sentiment()` — Article sentiment classification with 2000-char truncation, tenacity retry (3 attempts), temperature=0.1
   - `format=SentimentResult.model_json_schema()` for Ollama structured output

3. **`src/localstock/analysis/sentiment.py`** — Sentiment aggregation with exponential time decay:
   - `aggregate_sentiment()` — Weighted average with configurable half-life (default 3 days)
   - Formula: `weight = exp(-ln(2)/half_life * age_days)` — recent articles weighted higher
   - Re-exports `score_to_grade` from scoring module

## Verification Results

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_crawlers/test_news_crawler.py -x` | ✅ 12 passed |
| `uv run pytest tests/test_analysis/test_sentiment.py -x` | ✅ 7 passed |
| `uv run pytest tests/test_ai/test_client.py -x` | ✅ 5 passed |
| All modules importable | ✅ All imports successful |
| Full test suite `uv run pytest tests/ -x` | ✅ 122 passed, 0 failed |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation | Implementation |
|-----------|-----------|----------------|
| T-03-03 | HTML sanitization on RSS content | `sanitize_html()` strips all tags via BS4 `get_text()` with script/style/iframe decomposition |
| T-03-04 | Prompt injection via article text | 2000-char truncation + system prompt constraints + `format` parameter forces JSON schema |
| T-03-05 | Ollama server not running | `health_check()` method on OllamaClient, graceful skip if unavailable |
| T-03-06 | Fake RSS feed content | Accepted — hardcoded URL list, single-user tool, low risk |

## Self-Check: PASSED

- [x] `src/localstock/crawlers/news_crawler.py` exists
- [x] `src/localstock/ai/client.py` exists
- [x] `src/localstock/ai/prompts.py` exists
- [x] `src/localstock/analysis/sentiment.py` exists
- [x] `tests/test_crawlers/test_news_crawler.py` exists
- [x] `tests/test_analysis/test_sentiment.py` exists
- [x] `tests/test_ai/test_client.py` exists
- [x] Commit `ab3c086` found
- [x] Commit `33611d8` found
- [x] Commit `e2e980e` found
- [x] Commit `0e6be7a` found
