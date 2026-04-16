---
phase: 03-sentiment-analysis-scoring-engine
reviewed: 2025-07-18T10:30:00Z
depth: deep
files_reviewed: 20
files_reviewed_list:
  - src/localstock/ai/__init__.py
  - src/localstock/ai/client.py
  - src/localstock/ai/prompts.py
  - src/localstock/analysis/sentiment.py
  - src/localstock/api/routes/news.py
  - src/localstock/api/routes/scores.py
  - src/localstock/config.py
  - src/localstock/crawlers/news_crawler.py
  - src/localstock/db/models.py
  - src/localstock/db/repositories/news_repo.py
  - src/localstock/db/repositories/score_repo.py
  - src/localstock/db/repositories/sentiment_repo.py
  - src/localstock/scoring/__init__.py
  - src/localstock/scoring/config.py
  - src/localstock/scoring/engine.py
  - src/localstock/scoring/normalizer.py
  - src/localstock/services/news_service.py
  - src/localstock/services/scoring_service.py
  - src/localstock/services/sentiment_service.py
  - alembic/versions/c4007f49f9a7_add_phase3_sentiment_scoring_tables.py
findings:
  critical: 0
  warning: 7
  info: 4
  total: 11
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2025-07-18T10:30:00Z
**Depth:** deep
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 3 adds sentiment analysis (Ollama LLM-powered) and a multi-dimensional composite scoring engine. The architecture is clean: RSS crawler → article storage → LLM sentiment classification → time-weighted aggregation → composite score with configurable weights. Code is well-documented with consistent docstrings and clear separation of concerns.

**Key concerns:**
1. The retry decorator in `OllamaClient` catches the wrong exception types, making retry logic effectively a no-op for actual network failures.
2. The Ollama timeout setting is configured but never passed to the client or API calls — LLM requests could hang indefinitely.
3. Ticker extraction results are computed then discarded in `NewsService.crawl_and_store()`, suggesting a missing feature (article-ticker association).
4. Repository methods auto-commit transactions, preventing atomic multi-step operations.

Overall code quality is good. No critical security vulnerabilities found. The structured output enforcement via Pydantic schema in Ollama calls provides solid LLM output validation.

## Warnings

### WR-01: Retry decorator catches wrong exception types — retries never trigger

**File:** `src/localstock/ai/client.py:83-87`
**Issue:** The `@retry` decorator is configured with `retry_if_exception_type((ConnectionError, TimeoutError))`. These are Python builtin exceptions inheriting from `OSError`. However, the Ollama client uses `httpx` internally, which raises `httpx.ConnectError` (inherits from `httpx.TransportError → Exception`) and `httpx.TimeoutException` — neither inherits from `ConnectionError` or `TimeoutError`. The retry logic will never trigger on actual network failures.
**Fix:**
```python
from httpx import ConnectError as HttpxConnectError, TimeoutException
from ollama import ResponseError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((HttpxConnectError, TimeoutException, ResponseError)),
)
async def classify_sentiment(self, article_text: str, symbol: str) -> SentimentResult:
    ...
```

### WR-02: Ollama timeout setting stored but never applied

**File:** `src/localstock/ai/client.py:63-66`
**Issue:** `self.timeout` is set from config (`ollama_timeout: int = 120`) but is never passed to the `AsyncClient` constructor (line 66) or the `.chat()` call (line 113). LLM inference on a 14B model can take 30-120+ seconds — without a timeout, requests could hang indefinitely if the model stalls.
**Fix:**
```python
# In __init__:
self.client = AsyncClient(host=self.host, timeout=httpx.Timeout(self.timeout))

# Or pass per-request in classify_sentiment:
response = await self.client.chat(
    model=self.model,
    messages=[...],
    format=SentimentResult.model_json_schema(),
    options={"temperature": 0.1, "num_ctx": 4096},
    keep_alive=self.keep_alive,
    # Note: check ollama client API for timeout parameter support
)
```

### WR-03: Ticker count threshold inconsistency — off-by-one logic

**File:** `src/localstock/services/sentiment_service.py:95-96`
**Issue:** When an article mentions many tickers, the code checks `if len(tickers) > 3` but slices to `tickers[:2]`. This means: 1-3 tickers → keep all; 4+ tickers → keep only 2. The jump from 3→2 is inconsistent. If the intent is "at most 3 primary tickers", slice to `[:3]`. If the intent is "at most 2 primary tickers", the condition should be `> 2`.
**Fix:**
```python
# Option A: Keep at most 3 tickers
if len(tickers) > 3:
    tickers = tickers[:3]

# Option B: Keep at most 2 tickers
if len(tickers) > 2:
    tickers = tickers[:2]
```

### WR-04: Extracted tickers computed but discarded — missing article-ticker linkage

**File:** `src/localstock/services/news_service.py:58-59`
**Issue:** In `crawl_and_store()`, tickers are extracted from each article's title+description (line 59) but the `tickers` variable is never used — it's not stored in the article row or linked to any association table. This means the sentiment service must re-extract tickers later (which it does in `run_full()`), duplicating work. More importantly, the article rows stored in the database have no `tickers` field, so there's no way to query "articles mentioning symbol X" without re-parsing all text.
**Fix:** Either store extracted tickers in the article (add a `tickers` JSON column to `NewsArticle`) or remove the extraction to avoid confusion:
```python
# Remove dead code if not storing:
rows.append({
    "url": article["url"],
    "title": article["title"],
    "summary": article.get("description"),
    "content": article.get("content"),
    "source": article["source"],
    "source_feed": article.get("source_feed"),
    "published_at": article["published_at"],
})
# Delete lines 58-59 (ticker extraction)
```

### WR-05: XML parsing of untrusted RSS feeds without defusedxml

**File:** `src/localstock/crawlers/news_crawler.py:12,142`
**Issue:** `xml.etree.ElementTree.fromstring()` is used to parse RSS XML from external sources (cafef.vn, vnexpress.net). Python's official documentation [warns](https://docs.python.org/3/library/xml.html#xml-vulnerabilities) that `xml.etree.ElementTree` "is not secure against maliciously constructed data." While the default `expat` parser mitigates XXE and entity expansion, it remains vulnerable to quadratic blowup attacks with crafted attribute values. For external RSS feeds that could be served via MITM or compromised CDN, `defusedxml` is recommended.
**Fix:**
```python
# Replace:
import xml.etree.ElementTree as ET

# With:
from defusedxml.ElementTree import fromstring as safe_fromstring

# In parse_rss_feed:
root = safe_fromstring(xml_text)  # instead of ET.fromstring(xml_text)
```
Add `defusedxml` to dependencies: `uv add defusedxml`

### WR-06: Repository methods auto-commit — breaks transaction atomicity

**File:** `src/localstock/db/repositories/news_repo.py:34`, `sentiment_repo.py:35`, `score_repo.py:34`
**Issue:** All three Phase 3 repositories call `await self.session.commit()` inside their `bulk_upsert()` methods. This means:
1. If a service needs to upsert articles AND sentiment scores atomically, it can't — articles are committed before sentiment insertion.
2. If sentiment upsert fails after article commit, data is in an inconsistent state.
3. The pattern prevents the service layer from controlling transaction boundaries.

This matches the existing Phase 1/2 repository pattern, but becomes riskier with the multi-step sentiment pipeline.
**Fix:** Move commits to the service layer or use the Unit of Work pattern:
```python
# In repository — remove commit:
async def bulk_upsert(self, rows: list[dict]) -> int:
    ...
    await self.session.execute(stmt)
    # Don't commit here
    return len(rows)

# In service — commit after all operations:
async def run_full(self):
    await self.sentiment_repo.bulk_upsert(sentiment_rows)
    await self.session.commit()  # Single commit point
```

### WR-07: Missing ForeignKey constraint on sentiment_scores.article_id

**File:** `src/localstock/db/models.py:311`, `alembic/versions/c4007f49f9a7_...py:59`
**Issue:** `SentimentScore.article_id` is declared as `Mapped[int] = mapped_column(Integer, index=True)` without a `ForeignKey("news_articles.id")` constraint. This means:
1. No referential integrity — sentiment scores can reference non-existent articles.
2. Deleting articles leaves orphaned sentiment scores.
3. The Alembic migration also lacks the FK constraint.
**Fix:**
```python
# In models.py:
from sqlalchemy import ForeignKey
article_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("news_articles.id"), index=True
)
```
Generate a follow-up Alembic migration to add the FK constraint.

## Info

### IN-01: Dead code in news_service.py enrichment path

**File:** `src/localstock/services/news_service.py:75-78`
**Issue:** After `bulk_upsert`, the code fetches `unprocessed = await self.news_repo.get_unprocessed(limit=50)` but the result is never used. The enrichment logic (fetching full article text) is planned but not implemented, leaving dead code that executes an unnecessary database query.
**Fix:** Remove or comment out until enrichment is implemented:
```python
# TODO: Phase 3 Plan 02 — enrich articles with full text
# if enrich:
#     unprocessed = await self.news_repo.get_unprocessed(limit=50)
#     ...
```

### IN-02: Float equality comparison in sentiment aggregation

**File:** `src/localstock/analysis/sentiment.py:54`
**Issue:** `if total_weight == 0:` uses exact float equality. While safe here (total_weight can only be 0 if the loop didn't execute, which is already guarded by the empty check on line 38), epsilon comparison is more robust against future refactoring.
**Fix:**
```python
if total_weight < 1e-10:
    return None
```

### IN-03: Unnecessary subquery nesting in news_repo.get_unprocessed

**File:** `src/localstock/db/repositories/news_repo.py:63-66`
**Issue:** The query creates a subquery via `.subquery()` then wraps it in another `select()` for `notin_()`. This produces a doubly-nested SQL statement. The idiomatic SQLAlchemy 2.0 pattern passes the Select directly:
```python
# Current (works but unnecessarily nested):
subq = select(SentimentScore.article_id).distinct().subquery()
stmt = select(NewsArticle).where(NewsArticle.id.notin_(select(subq)))

# Simpler:
subq = select(SentimentScore.article_id).distinct()
stmt = select(NewsArticle).where(NewsArticle.id.notin_(subq))
```

### IN-04: POST API endpoints lack concurrency guards

**File:** `src/localstock/api/routes/news.py:84-104`, `src/localstock/api/routes/scores.py:63-74`
**Issue:** The POST endpoints `/api/news/crawl`, `/sentiment/run`, and `/scores/run` trigger expensive operations (RSS crawling, LLM inference for ~50 stocks, full scoring pipeline). Multiple simultaneous calls could overwhelm the system or cause duplicate processing. Consider adding a simple in-memory lock or "already running" check.
**Fix:**
```python
import asyncio
_scoring_lock = asyncio.Lock()

@router.post("/scores/run")
async def trigger_scoring(session: AsyncSession = Depends(get_session)):
    if _scoring_lock.locked():
        raise HTTPException(status_code=409, detail="Scoring already in progress")
    async with _scoring_lock:
        service = ScoringService(session)
        result = await service.run_full()
        return result
```

---

_Reviewed: 2025-07-18T10:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
