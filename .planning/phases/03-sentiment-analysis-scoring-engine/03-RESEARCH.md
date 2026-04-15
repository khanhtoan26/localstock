# Phase 3: Sentiment Analysis & Scoring Engine - Research

**Researched:** 2026-04-15
**Domain:** Vietnamese financial news crawling, LLM-based sentiment classification (Ollama), composite scoring engine
**Confidence:** HIGH

## Summary

Phase 3 adds two major capabilities: (1) crawling Vietnamese financial news and classifying sentiment per stock ticker using a local LLM via Ollama, and (2) building a composite scoring engine that combines technical indicators (Phase 2), fundamental ratios (Phase 2), and sentiment scores into a single 0-100 score with grade letter display (A/B/C/D/F). The funnel strategy filters ~400 stocks to ~50 candidates before running the expensive LLM sentiment analysis.

Key discoveries during research: CafeF RSS feeds are the best news source — multiple feeds (`thi-truong-chung-khoan`, `doanh-nghiep`, `tai-chinh-ngan-hang`, `vi-mo-dau-tu`) each return 50 articles with proper structure and are accessible without anti-bot challenges. VnExpress RSS works for `kinh-doanh` (60 items) but stock-specific feeds redirect. The Ollama Python client (v0.6.1) supports `AsyncClient` with a `format` parameter that accepts JSON Schema for structured output — exactly what D-03 requires. RTX 3060 with 12GB VRAM (9.7GB free confirmed via `nvidia-smi`) can run Qwen2.5 14B Q4_K_M (~9-10GB). Ollama is NOT installed yet — the plan must include an installation step.

**Primary recommendation:** Use CafeF RSS as primary news source (verified working), VnExpress RSS kinh-doanh as secondary. Use `ollama` AsyncClient with Pydantic model JSON schema as `format` parameter for structured sentiment output. Build scoring engine with configurable weights via `pydantic-settings` (existing pattern). Skip `underthesea` preprocessing initially — let LLM handle Vietnamese text directly (simpler, fewer dependencies, Qwen2.5 handles Vietnamese natively).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Agent tự research và chọn nguồn tin tức tài chính VN tốt nhất. Gợi ý từ research: CafeF, VnExpress, Thanh Niên.
- **D-02:** Agent tự test và chọn model Ollama tốt nhất cho sentiment tiếng Việt (gợi ý: Qwen2.5 7B hoặc 14B Q4).
- **D-03:** Output format: JSON cấu trúc — `{ sentiment: "positive/negative/neutral", score: 0-1, reason: "..." }`. Dùng Ollama structured output (format parameter với JSON Schema).
- **D-04:** Agent tự chọn trọng số composite score phù hợp.
- **D-05:** Thang điểm kết hợp: Grade letter (A/B/C/D/F) hiển thị cho user + điểm số chi tiết (0-100) lưu bên trong. Tránh false precision khi hiển thị.
- **D-06:** Trọng số scoring phải configurable — user có thể tùy chỉnh sau.

### Agent's Discretion
- Nguồn tin tức cụ thể và cách crawl/parse
- Model LLM cho sentiment (Qwen2.5 7B vs 14B vs khác)
- Trọng số mặc định cho composite score
- Funnel strategy: bao nhiêu mã qua LLM sentiment (research gợi ý ~50 sau khi lọc bằng tech+fund score)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SENT-01 | Agent crawl tin tức tài chính từ các nguồn Việt Nam (CafeF, VnExpress, Thanh Niên...) | CafeF RSS verified working (4 feeds, 50 items each). VnExpress kinh-doanh RSS verified (60 items). httpx + BeautifulSoup4 for article text extraction. |
| SENT-02 | Agent sử dụng LLM local để phân loại sentiment tin tức (tích cực/tiêu cực/trung tính) cho từng mã | Ollama AsyncClient with `format=SentimentResult.model_json_schema()` for structured JSON output. Qwen2.5 14B Q4_K_M fits in 12GB VRAM. |
| SENT-03 | Agent tổng hợp điểm sentiment từ nhiều bài viết thành score cho từng mã | Time-weighted average of per-article sentiment scores. Recent articles weighted higher. Configurable decay window (default 7 days). |
| SCOR-01 | Agent chấm điểm tổng hợp cho từng mã (thang 0-100) kết hợp 3 chiều: kỹ thuật + cơ bản + sentiment | Scoring engine combines normalized dimension scores with configurable weights. Macro dimension placeholder at 0 weight (Phase 4). |
| SCOR-02 | Agent cho phép tùy chỉnh trọng số chấm điểm | ScoringConfig dataclass in settings with SCORING_WEIGHT_TECHNICAL etc. env vars. Default: tech 35%, fund 35%, sentiment 30%. |
| SCOR-03 | Agent xếp hạng và đưa ra danh sách top 10-20 mã đáng mua kèm lý do | Query composite_scores ordered by total_score desc, return top N with per-dimension breakdown explaining WHY. |

</phase_requirements>

## Standard Stack

### Core (New Dependencies for Phase 3)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ollama | 0.6.1 | Ollama Python client (async) | Official client with AsyncClient, structured output via `format` parameter, keep_alive support. [VERIFIED: PyPI v0.6.1, GitHub README confirms AsyncClient + format parameter] |
| beautifulsoup4 | 4.14.3 | HTML parsing for article extraction | Battle-tested HTML parser, already in STACK.md recommendation. Use with `lxml` parser. [VERIFIED: PyPI v4.14.3] |
| lxml | 5.x | Fast XML/HTML parser backend | 10x faster than html.parser for BeautifulSoup. Also parses RSS XML. [VERIFIED: PyPI] |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28+ | Async HTTP client | Fetching RSS feeds and article pages [VERIFIED: pyproject.toml] |
| SQLAlchemy | 2.0+ | ORM for new tables | news_articles, sentiment_scores, composite_scores tables [VERIFIED: pyproject.toml] |
| Alembic | 1.18+ | Schema migration | Adding new Phase 3 tables [VERIFIED: pyproject.toml] |
| pydantic | 2.13+ | Data validation | Sentiment result model, scoring config [VERIFIED: pyproject.toml] |
| pydantic-settings | 2.0+ | Settings from env vars | Scoring weights configuration [VERIFIED: pyproject.toml] |
| tenacity | 9.0+ | Retry logic | Retry failed Ollama calls and HTTP requests [VERIFIED: pyproject.toml] |
| loguru | 0.7+ | Structured logging | Crawling and sentiment analysis progress [VERIFIED: pyproject.toml] |

### Deferred (NOT Needed for Phase 3)
| Library | Why Not Now |
|---------|------------|
| underthesea | Skip Vietnamese NLP preprocessing — Qwen2.5 handles Vietnamese natively. Add only if sentiment quality is poor after testing. Avoids heavy dependency (~500MB+ with models). [ASSUMED] |
| newspaper4k | Skip article extraction library — CafeF article structure is simple enough for BS4 direct extraction (verified: `detail-content`, `sapo` CSS classes). Add only if extraction fails on edge cases. |
| trafilatura | Same as newspaper4k — not needed when BS4 works. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CafeF RSS | VnExpress HTML scraping | CafeF RSS is structured, reliable, no anti-bot. VnExpress RSS only has kinh-doanh feed. |
| Ollama direct client | LangChain | LangChain adds massive overhead for simple chat+format. Direct ollama is simpler. Per STACK.md anti-stack. |
| BS4 article extraction | newspaper4k/trafilatura | BS4 gives precise control over CafeF's known HTML structure. Libraries are overkill for 2 sites. |
| underthesea preprocessing | Raw text to LLM | Qwen2.5 handles Vietnamese text. Preprocessing adds complexity/dependencies without proven benefit. |

**Installation:**
```bash
uv add ollama beautifulsoup4 lxml
```

**Ollama Server Setup:**
```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended model
ollama pull qwen2.5:14b-instruct-q4_K_M

# Fallback model (if 14B too slow)
ollama pull qwen2.5:7b-instruct-q8_0

# Verify
ollama list
```

## Architecture Patterns

### Recommended Project Structure
```
src/localstock/
├── crawlers/
│   └── news_crawler.py          # NEW: RSS feed crawler + article text extraction
├── analysis/
│   └── sentiment.py             # NEW: LLM sentiment classification (pure logic)
├── scoring/                     # NEW MODULE
│   ├── __init__.py
│   ├── config.py                # Scoring weights & grade thresholds
│   ├── normalizer.py            # Normalize dimensions to 0-100 scale
│   └── engine.py                # Composite score aggregation
├── services/
│   ├── news_service.py          # NEW: Orchestrate crawl → parse → store
│   ├── sentiment_service.py     # NEW: Orchestrate LLM sentiment for stocks
│   └── scoring_service.py       # NEW: Orchestrate full scoring pipeline
├── ai/                          # NEW MODULE
│   ├── __init__.py
│   ├── client.py                # Ollama AsyncClient wrapper with retry
│   └── prompts.py               # Sentiment prompt templates
├── db/
│   ├── models.py                # ADD: NewsArticle, SentimentScore, CompositeScore
│   └── repositories/
│       ├── news_repo.py         # NEW: CRUD for news_articles
│       ├── sentiment_repo.py    # NEW: CRUD for sentiment_scores
│       └── score_repo.py        # NEW: CRUD for composite_scores
├── api/
│   └── routes/
│       ├── scores.py            # NEW: scoring/ranking endpoints
│       └── news.py              # NEW: news/sentiment endpoints
└── config.py                    # EXTEND: Add Ollama + scoring settings
```

### Pattern 1: Ollama AsyncClient with Structured Output
**What:** Wrap Ollama's AsyncClient with retry logic and Pydantic model JSON schema for guaranteed structured responses.
**When to use:** All LLM calls in the project.
**Example:**
```python
# Source: Ollama Python GitHub README + API docs [VERIFIED]
from pydantic import BaseModel, Field
from ollama import AsyncClient
from tenacity import retry, stop_after_attempt, wait_exponential

class SentimentResult(BaseModel):
    sentiment: str = Field(description="positive, negative, or neutral")
    score: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
    reason: str = Field(description="Brief explanation in Vietnamese")

class OllamaClient:
    def __init__(self, model: str = "qwen2.5:14b-instruct-q4_K_M",
                 host: str = "http://localhost:11434"):
        self.model = model
        self.client = AsyncClient(host=host)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def classify_sentiment(self, article_text: str, symbol: str) -> SentimentResult:
        response = await self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Mã cổ phiếu: {symbol}\n\nBài viết:\n{article_text[:2000]}"},
            ],
            format=SentimentResult.model_json_schema(),
            options={"temperature": 0.1, "num_ctx": 4096},
            keep_alive="30m",
        )
        return SentimentResult.model_validate_json(response.message.content)
```

### Pattern 2: RSS-First News Crawling
**What:** Use RSS feeds as primary news source — structured, rate-limit friendly, no anti-bot issues. Fall back to HTML scraping only for article body text.
**When to use:** All news acquisition.
**Example:**
```python
# Source: CafeF RSS verified working [VERIFIED: 2026-04-15]
import xml.etree.ElementTree as ET
import httpx
from datetime import datetime

CAFEF_RSS_FEEDS = [
    "https://cafef.vn/thi-truong-chung-khoan.rss",  # 50 items [VERIFIED]
    "https://cafef.vn/doanh-nghiep.rss",             # 50 items [VERIFIED]
    "https://cafef.vn/tai-chinh-ngan-hang.rss",       # 50 items [VERIFIED]
    "https://cafef.vn/vi-mo-dau-tu.rss",              # 50 items [VERIFIED]
]
VNEXPRESS_RSS_FEEDS = [
    "https://vnexpress.net/rss/kinh-doanh.rss",       # 60 items [VERIFIED]
]

async def fetch_rss(url: str, client: httpx.AsyncClient) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/rss+xml,application/xml,text/xml",
    }
    resp = await client.get(url, headers=headers, timeout=30)
    root = ET.fromstring(resp.text)
    articles = []
    for item in root.findall(".//item"):
        articles.append({
            "title": item.findtext("title", "").strip(),
            "url": item.findtext("link", "").strip(),
            "description": item.findtext("description", "").strip(),
            "published_at": parse_rss_date(item.findtext("pubDate", "")),
            "source": "cafef" if "cafef" in url else "vnexpress",
        })
    return articles
```

### Pattern 3: Ticker Extraction from Vietnamese Text
**What:** Extract stock ticker symbols from article titles and text using regex with exclusion list.
**When to use:** Mapping articles to stocks for per-ticker sentiment aggregation.
**Example:**
```python
# Source: Runtime testing against real CafeF headlines [VERIFIED: 2026-04-15]
import re

TICKER_PATTERN = re.compile(r'\b([A-Z]{3})\b')
NON_TICKERS = {
    'USD', 'VND', 'CEO', 'GDP', 'CPI', 'ETF', 'IPO', 'FDI', 'SBV',
    'HOSE', 'HNX', 'WTO', 'FTA', 'NHNN', 'CTCK', 'UBND', 'BTC',
}

def extract_tickers(text: str, valid_symbols: set[str]) -> list[str]:
    """Extract stock tickers from Vietnamese text.

    Args:
        text: Article title or body text.
        valid_symbols: Set of known HOSE stock symbols for validation.

    Returns:
        List of unique, validated ticker symbols found in text.
    """
    candidates = TICKER_PATTERN.findall(text)
    return list(dict.fromkeys(  # preserve order, deduplicate
        t for t in candidates
        if t not in NON_TICKERS and t in valid_symbols
    ))
```

### Pattern 4: Configurable Scoring Engine
**What:** Scoring weights and grade thresholds stored in Settings (pydantic-settings), loadable from .env file. Follows existing config.py pattern.
**When to use:** All scoring operations.
**Example:**
```python
# Following existing config.py pattern [VERIFIED: src/localstock/config.py]
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing fields ...

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    ollama_timeout: int = 120
    ollama_keep_alive: str = "30m"

    # Scoring weights (must sum to 1.0 across active dimensions)
    scoring_weight_technical: float = 0.35
    scoring_weight_fundamental: float = 0.35
    scoring_weight_sentiment: float = 0.30
    scoring_weight_macro: float = 0.0  # Phase 4 will activate this

    # Funnel settings
    funnel_top_n: int = 50  # How many stocks pass to LLM sentiment
    sentiment_articles_per_stock: int = 5  # Max articles per stock for LLM
    sentiment_lookback_days: int = 7  # How far back to look for news
```

### Pattern 5: Scoring Normalization
**What:** Normalize each analysis dimension to 0-100 scale before applying weights.
**When to use:** Converting raw indicator values to comparable scores.
**Example:**
```python
# Source: Pitfall 6 from PITFALLS.md — avoid mixing incompatible scales [CITED: .planning/research/PITFALLS.md]
def normalize_technical_score(indicator: TechnicalIndicator) -> float:
    """Convert raw technical indicators to 0-100 score.

    Components (each 0-20, total 0-100):
    - RSI positioning: 0-20 (oversold=high, overbought=low)
    - Trend alignment: 0-20 (uptrend with MA stack = high)
    - MACD momentum: 0-20 (bullish crossover = high)
    - Bollinger position: 0-20 (near lower band = high)
    - Volume confirmation: 0-20 (above avg with uptrend = high)
    """
    score = 0.0
    # RSI: 30-40 range is bullish, 60-70 is bearish
    if indicator.rsi_14 is not None:
        if indicator.rsi_14 < 30:
            score += 18  # oversold — potential reversal
        elif indicator.rsi_14 < 45:
            score += 15  # healthy zone
        elif indicator.rsi_14 < 55:
            score += 10  # neutral
        elif indicator.rsi_14 < 70:
            score += 5   # getting hot
        else:
            score += 2   # overbought
    # ... more components ...
    return min(score, 100.0)
```

### Anti-Patterns to Avoid
- **Don't use LLM to recall financial facts** (Pitfall 3) — always inject data into prompt. The LLM classifies sentiment from given text, never generates financial data. [CITED: .planning/research/PITFALLS.md]
- **Don't run LLM on all 400 stocks** (Pitfall 7) — funnel to top ~50 first using rules-based tech+fund scores. [CITED: .planning/research/PITFALLS.md]
- **Don't score to false precision** (Pitfall 6) — use grade letters for display (A-F), numeric 0-100 internally only. [CITED: .planning/research/PITFALLS.md]
- **Don't scrape full HTML pages for news** — use RSS feeds first (structured, faster, no anti-bot). Only scrape article body text when needed for LLM context.
- **Don't process old articles repeatedly** — store article URL hash, only process new articles. [CITED: .planning/research/PITFALLS.md, Performance Traps]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM structured output parsing | Custom JSON regex parser | Ollama `format` param + Pydantic `model_json_schema()` | Ollama guarantees valid JSON matching the schema. No parsing failures. [VERIFIED: Ollama API docs] |
| RSS XML parsing | Custom string parsing | `xml.etree.ElementTree` (stdlib) | Part of Python stdlib, handles CDATA, namespaces, encoding. |
| HTTP retry logic | Custom retry loops | `tenacity` (already in project) | Exponential backoff, jitter, configurable stop conditions. |
| Article text extraction | Custom HTML strippers | BeautifulSoup4 with `lxml` | Handles malformed HTML, encoding issues, CSS selectors. |
| Configuration management | Custom config file parser | `pydantic-settings` (already in project) | Type-safe, .env support, validation, follows existing pattern. |

**Key insight:** The Ollama `format` parameter with a JSON Schema is the breakthrough for reliable LLM output. It eliminates the entire class of "LLM returned malformed JSON" errors that typically require complex retry/fallback logic.

## Common Pitfalls

### Pitfall 1: LLM Context Window Overflow
**What goes wrong:** Sending full article text (2000+ words) to LLM exceeds context window, produces truncated/garbage output.
**Why it happens:** Vietnamese articles can be 3000-5000 words. Qwen2.5 14B Q4_K_M with 12GB VRAM supports ~4096 tokens comfortably (8K theoretical but VRAM-constrained).
**How to avoid:** Truncate article text to ~1500 chars (title + first 3 paragraphs + sapo/summary). This captures the key sentiment signal without overwhelming the context. Send one article per LLM call, not batch.
**Warning signs:** LLM responses become repetitive, incoherent, or return default/neutral for everything.

### Pitfall 2: CafeF Anti-Bot Redirect
**What goes wrong:** CafeF redirects to `c.cafef.vn/sorry?continue=...` page when detecting automated requests without proper headers.
**Why it happens:** CafeF uses Cloudflare/OpenResty filtering. Bare `curl` or `requests` without User-Agent gets blocked.
**How to avoid:** Always send browser-like headers with httpx: `User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36`. RSS feeds work with basic UA. Article pages need full Chrome-like UA. [VERIFIED: 2026-04-15 — RSS works with basic UA, article pages need full UA]
**Warning signs:** HTTP 302 redirects to `c.cafef.vn/sorry`, empty article text, page size < 5KB.

### Pitfall 3: Ticker-Article Mapping Noise
**What goes wrong:** Article mentions VNM in passing ("giống như VNM đã làm năm ngoái") but is actually about HPG. Sentiment gets attributed to wrong stock.
**Why it happens:** Vietnamese financial articles frequently reference multiple tickers for comparison. Simple regex extraction doesn't understand context.
**How to avoid:** (1) Use headline tickers as primary — CafeF headlines typically mention the main stock first. (2) If article mentions >3 tickers, treat as "market overview" not stock-specific. (3) Let the LLM identify the PRIMARY ticker as part of its structured response. (4) Validate extracted tickers against known HOSE symbols list.
**Warning signs:** Every article gets mapped to 5+ tickers, sentiment scores are identical across many stocks.

### Pitfall 4: Ollama Server Not Running
**What goes wrong:** Sentiment service tries to call Ollama but the server isn't running. Entire sentiment pipeline fails silently.
**Why it happens:** Ollama needs to be started as a service. After reboot or crash, it may not auto-restart.
**How to avoid:** Add health check for Ollama at service startup (`GET /api/version`). If Ollama is down, log warning and skip sentiment analysis — don't block scoring. Scores without sentiment dimension should still be useful (tech + fund only). [CITED: .planning/research/PITFALLS.md, Integration Gotchas]
**Warning signs:** All sentiment scores are null/zero, scoring service takes <1 second (no LLM calls made).

### Pitfall 5: Missing Dimension Handling in Scoring
**What goes wrong:** Stock has no recent news → sentiment score is null → composite score divides by wrong number or returns NaN.
**Why it happens:** Not all stocks have news coverage. Macro dimension is Phase 4 (always null in Phase 3). Scoring formula must handle missing dimensions gracefully.
**How to avoid:** When a dimension is null/unavailable, redistribute its weight proportionally to available dimensions. Example: if sentiment=null (weight 0.30), redistribute: tech becomes 0.35/(0.35+0.35)=0.50, fund becomes 0.50. Store a `dimensions_available` field in composite_scores.
**Warning signs:** Many stocks have 0 composite score, NaN in scores, ranking changes wildly when one article is added.

### Pitfall 6: Stale Sentiment Dominating Score
**What goes wrong:** A major negative article from 2 weeks ago keeps dragging down a stock's score even though the situation has resolved.
**Why it happens:** Simple average of all articles doesn't decay. Old news has equal weight to new news.
**How to avoid:** Time-weighted sentiment aggregation. Articles from today get weight 1.0, yesterday 0.85, 3 days ago 0.6, 7 days ago 0.3. Configurable decay function.
**Warning signs:** Stock's sentiment doesn't change even after new positive articles appear.

## Code Examples

### Example 1: News Article Model (DB)
```python
# Following existing models.py pattern [VERIFIED: src/localstock/db/models.py]
class NewsArticle(Base):
    """Crawled financial news articles."""
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(500), unique=True)  # dedup key
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # full article text
    source: Mapped[str] = mapped_column(String(20))  # 'cafef', 'vnexpress'
    source_feed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_news_articles_published", "published_at"),
        Index("ix_news_articles_source", "source"),
    )


class SentimentScore(Base):
    """LLM-classified sentiment per article-ticker pair."""
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    sentiment: Mapped[str] = mapped_column(String(10))  # 'positive', 'negative', 'neutral'
    score: Mapped[float] = mapped_column(Float)  # 0.0 to 1.0
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50))  # e.g. 'qwen2.5:14b-instruct-q4_K_M'
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("article_id", "symbol", name="uq_sentiment_score"),
    )


class CompositeScore(Base):
    """Aggregated multi-dimensional score per stock."""
    __tablename__ = "composite_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    # Dimension scores (0-100 each)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Phase 4
    # Composite
    total_score: Mapped[float] = mapped_column(Float)  # 0-100 weighted
    grade: Mapped[str] = mapped_column(String(2))  # A, B, C, D, F
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Metadata
    dimensions_used: Mapped[int] = mapped_column(Integer, default=2)  # how many non-null dimensions
    weights_json: Mapped[dict] = mapped_column(JSON)  # actual weights used (for audit)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_composite_score"),
    )
```

### Example 2: Sentiment Prompt Template
```python
# Source: Pitfall 3 (LLM hallucination prevention) + D-03 (structured output) [CITED: .planning/research/PITFALLS.md]
SENTIMENT_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.

Nhiệm vụ: Đọc bài viết tài chính và phân loại sentiment (tâm lý thị trường) đối với mã cổ phiếu được chỉ định.

Quy tắc:
1. Chỉ phân tích sentiment DỰA TRÊN NỘI DUNG BÀI VIẾT. Không suy luận ngoài bài viết.
2. sentiment: "positive" (tích cực cho giá cổ phiếu), "negative" (tiêu cực), "neutral" (trung tính/không liên quan).
3. score: 0.0 (hoàn toàn tiêu cực) đến 1.0 (hoàn toàn tích cực). 0.5 = trung tính.
4. reason: Giải thích ngắn gọn bằng tiếng Việt (1-2 câu) tại sao bạn phân loại như vậy.
5. Nếu bài viết KHÔNG liên quan đến mã cổ phiếu được chỉ định, trả về sentiment="neutral", score=0.5.

Ví dụ sentiment:
- "VNM doanh thu tăng 15% so với cùng kỳ" → positive, score=0.8
- "HPG bị phạt thuế chống bán phá giá" → negative, score=0.2
- "Thị trường biến động mạnh trong phiên hôm nay" → neutral, score=0.5"""
```

### Example 3: Grade Mapping
```python
# Source: D-05 from CONTEXT.md, Pitfall 6 from PITFALLS.md [CITED: CONTEXT.md]
def score_to_grade(score: float) -> str:
    """Map numeric score (0-100) to grade letter.

    Grade boundaries per CONTEXT.md specifics:
    A = 80-100 (Strong Buy signal)
    B = 60-79  (Buy signal)
    C = 40-59  (Hold/Neutral)
    D = 20-39  (Caution/Weak)
    F = 0-19   (Avoid)
    """
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    elif score >= 20:
        return "D"
    else:
        return "F"
```

### Example 4: Funnel Strategy
```python
# Source: ARCHITECTURE.md funnel pattern + Pitfall 7 (VRAM management) [CITED: .planning/research/ARCHITECTURE.md]
async def get_funnel_candidates(session: AsyncSession, top_n: int = 50) -> list[str]:
    """Filter ~400 stocks to top N candidates for LLM sentiment.

    Uses pre-computed technical + fundamental scores (Phase 2) to rank.
    Only top N get the expensive LLM sentiment analysis.

    Strategy: Simple average of technical + fundamental dimension scores.
    Both are 0-100, so average gives preliminary ranking without weights.
    """
    # Get latest technical indicators with scores
    indicators = await indicator_repo.get_all_latest()
    ratios = await ratio_repo.get_all_latest()

    # Compute preliminary score per symbol
    prelim_scores = {}
    for symbol in indicators:
        tech = normalize_technical_score(indicators[symbol])
        fund = normalize_fundamental_score(ratios.get(symbol))
        if fund is not None:
            prelim_scores[symbol] = (tech + fund) / 2
        else:
            prelim_scores[symbol] = tech

    # Sort and take top N
    ranked = sorted(prelim_scores.items(), key=lambda x: x[1], reverse=True)
    return [symbol for symbol, _ in ranked[:top_n]]
```

## Scoring Engine Design

### Default Weights (D-04, D-06)
| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Technical | 0.35 | Price action is the most immediate signal for short-term trading |
| Fundamental | 0.35 | Financial health determines long-term value |
| Sentiment | 0.30 | News sentiment provides market psychology context |
| Macro | 0.00 | Placeholder — activated in Phase 4 |

**When macro activates (Phase 4):** Recommended rebalance: Technical 0.30, Fundamental 0.30, Sentiment 0.20, Macro 0.20 (matching REQUIREMENTS.md SCOR-02 default). [ASSUMED — default weights are subjective, user should adjust]

### Grade Thresholds (D-05)
| Grade | Score Range | Meaning | Action Signal |
|-------|-------------|---------|---------------|
| A | 80-100 | Excellent across all dimensions | Strong Buy |
| B | 60-79 | Good with minor concerns | Buy |
| C | 40-59 | Mixed signals | Hold/Watch |
| D | 20-39 | Weak signals | Caution |
| F | 0-19 | Poor across dimensions | Avoid |

### Missing Dimension Handling
When a dimension has no data (e.g., no news for a stock):
1. Remove the dimension from the active set
2. Redistribute its weight proportionally among remaining dimensions
3. Record `dimensions_used` count and actual `weights_json` in the score row

```python
def compute_composite(
    tech: float | None, fund: float | None, sent: float | None, macro: float | None,
    config: ScoringConfig,
) -> tuple[float, str, dict]:
    """Compute composite score with dynamic weight redistribution.

    Returns: (total_score, grade, actual_weights_used)
    """
    dimensions = {}
    weights = {}
    if tech is not None:
        dimensions["technical"] = tech
        weights["technical"] = config.scoring_weight_technical
    if fund is not None:
        dimensions["fundamental"] = fund
        weights["fundamental"] = config.scoring_weight_fundamental
    if sent is not None:
        dimensions["sentiment"] = sent
        weights["sentiment"] = config.scoring_weight_sentiment
    if macro is not None:
        dimensions["macro"] = macro
        weights["macro"] = config.scoring_weight_macro

    if not dimensions:
        return 0.0, "F", {}

    # Normalize weights to sum to 1.0
    total_weight = sum(weights.values())
    normalized = {k: v / total_weight for k, v in weights.items()}

    total = sum(dimensions[k] * normalized[k] for k in dimensions)
    grade = score_to_grade(total)
    return total, grade, normalized
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `format="json"` (free-form) | `format=JsonSchema` (structured) | Ollama 0.5+ | Guarantees valid JSON matching exact schema. Eliminates parsing failures entirely. |
| LangChain for LLM integration | Direct ollama client | Current best practice for simple use cases | 50+ fewer dependencies, simpler debugging, faster execution |
| Rule-based Vietnamese sentiment | LLM with Vietnamese capability (Qwen2.5) | Qwen2.5 release (2024) | Qwen2.5 has strong Vietnamese support, handles financial jargon without custom dictionary |
| Web scraping for news | RSS feeds + selective HTML scraping | N/A (RSS always existed but often overlooked) | 10x more reliable, structured data, no anti-bot issues |

**Deprecated/outdated:**
- `ollama.generate()` for chat-style tasks → use `ollama.chat()` with message format
- `format="json"` without schema → use JSON Schema for guaranteed structure

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Qwen2.5 14B Q4_K_M fits in 12GB VRAM with ~4096 token context | Standard Stack | Would need to fall back to 7B model. Low risk — math checks out (14B*4bit/8 ≈ 7GB + overhead) and 9.7GB VRAM confirmed free. |
| A2 | Qwen2.5 handles Vietnamese financial text adequately without underthesea preprocessing | Architecture Patterns | Would need to add underthesea dependency and preprocessing step. Medium risk — Qwen2.5 multilingual support includes Vietnamese but financial domain accuracy unverified. |
| A3 | Default weights (tech 35%, fund 35%, sent 30%) produce reasonable rankings | Scoring Engine Design | Weights are subjective. User can adjust via config. Low impact — configurable by D-06. |
| A4 | CafeF RSS feeds will remain accessible and stable | Standard Stack | Would need to switch to HTML scraping or alternative source. Low risk — RSS has been stable, but CafeF API has broken before (Pitfall 1). |
| A5 | 50 articles/day across all feeds is sufficient for meaningful sentiment coverage of top stocks | Architecture Patterns | Might miss important news. Could increase crawl frequency or add more feeds. |
| A6 | Truncating articles to ~1500 chars preserves sentiment signal | Common Pitfalls | Might miss nuanced sentiment deep in the article. Alternative: use LLM to summarize first, then classify. |

## Open Questions

1. **Qwen2.5 14B Vietnamese financial sentiment accuracy**
   - What we know: Qwen2.5 has multilingual training including Vietnamese. 14B should outperform 7B on reasoning tasks.
   - What's unclear: Actual accuracy on Vietnamese financial text. How well does it handle mixed Vietnamese-English financial jargon?
   - Recommendation: Build the sentiment pipeline first, run on 20-30 manually evaluated articles, measure accuracy. Fall back to 7B Q8 if 14B is too slow (>15s per article). This is why D-02 says "agent tests and picks."

2. **Sentiment aggregation decay function**
   - What we know: Recent articles should matter more than old ones.
   - What's unclear: Optimal decay rate. Linear? Exponential? How many days back to include?
   - Recommendation: Start with exponential decay (half-life = 3 days), lookback window = 7 days. Make configurable. Evaluate after real data.

3. **VnExpress stock-specific RSS feeds**
   - What we know: `vnexpress.net/rss/kinh-doanh.rss` works (60 items). `chung-khoan.rss` returns 302 redirect.
   - What's unclear: Whether VnExpress has other stock-specific feeds or if the redirect is permanent.
   - Recommendation: Use VnExpress kinh-doanh feed only. Don't rely on VnExpress for stock-specific news. CafeF is more reliable.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Ollama | LLM sentiment (SENT-02) | ✗ | — | **Must install**: `curl -fsSL https://ollama.com/install.sh \| sh` |
| NVIDIA GPU (RTX 3060) | LLM inference speed | ✓ | 12288 MiB total, 9752 MiB free | CPU inference (very slow, ~60s/article vs ~5s) |
| Python 3.12 | Runtime | ✓ | 3.12.3 | — |
| uv | Package management | ✓ | 0.11.6 | — |
| PostgreSQL (Supabase) | Data storage | ✓ (from Phase 1) | — | — |
| CafeF RSS | News crawling (SENT-01) | ✓ | 4 feeds, 50 items each | VnExpress RSS (fewer items) |
| VnExpress RSS | Secondary news source | ✓ | kinh-doanh feed, 60 items | CafeF only |

**Missing dependencies with no fallback:**
- **Ollama** — must be installed. Plan must include installation step + model pull + verification.

**Missing dependencies with fallback:**
- None — all other dependencies available or have viable alternatives.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.26+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x --timeout=30` |
| Full suite command | `uv run pytest tests/ --timeout=30 -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SENT-01 | RSS feed parsing extracts articles correctly | unit | `uv run pytest tests/test_crawlers/test_news_crawler.py -x` | ❌ Wave 0 |
| SENT-02 | LLM returns valid SentimentResult for Vietnamese text | integration | `uv run pytest tests/test_analysis/test_sentiment.py -x` | ❌ Wave 0 |
| SENT-03 | Per-ticker aggregation produces weighted sentiment score | unit | `uv run pytest tests/test_analysis/test_sentiment.py::test_aggregate -x` | ❌ Wave 0 |
| SCOR-01 | Composite score calculation with all dimensions | unit | `uv run pytest tests/test_scoring/test_engine.py -x` | ❌ Wave 0 |
| SCOR-02 | Weights are configurable and redistribute on missing dims | unit | `uv run pytest tests/test_scoring/test_engine.py::test_weights -x` | ❌ Wave 0 |
| SCOR-03 | Top-N ranking query returns stocks with grade and breakdown | unit | `uv run pytest tests/test_scoring/test_engine.py::test_ranking -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_crawlers/test_news_crawler.py tests/test_analysis/test_sentiment.py tests/test_scoring/ -x`
- **Per wave merge:** `uv run pytest tests/ --timeout=30 -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_crawlers/test_news_crawler.py` — covers SENT-01
- [ ] `tests/test_analysis/test_sentiment.py` — covers SENT-02, SENT-03
- [ ] `tests/test_scoring/__init__.py` — new test directory
- [ ] `tests/test_scoring/test_engine.py` — covers SCOR-01, SCOR-02, SCOR-03
- [ ] `tests/test_scoring/test_normalizer.py` — covers dimension normalization
- [ ] `tests/test_ai/__init__.py` — new test directory
- [ ] `tests/test_ai/test_client.py` — covers Ollama client wrapper

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user personal tool |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No user roles |
| V5 Input Validation | Yes | Pydantic models for LLM output, RSS content sanitization |
| V6 Cryptography | No | No secrets in this phase |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection via news article text | Tampering | Truncate article text, system prompt instructs to only classify sentiment, structured output format limits response shape |
| Malicious content in RSS feeds | Tampering | Sanitize HTML before storing, don't render raw HTML from RSS descriptions |
| Ollama binding to 0.0.0.0 | Information Disclosure | Bind to 127.0.0.1 only (Ollama default). Document in setup instructions. [CITED: .planning/research/PITFALLS.md, Security Mistakes] |

## Project Constraints (from copilot-instructions.md)

- **Python 3.12+** — already satisfied
- **FastAPI** for API layer — follow existing `create_app()` pattern in `api/app.py`
- **SQLAlchemy 2.0 async** — use `Mapped` type annotations, `mapped_column()`, `DateTime(timezone=True)` for all timestamps
- **PostgreSQL** (Supabase) — use `pg_insert().on_conflict_do_update()` for upserts (existing pattern)
- **uv** package manager — use `uv add` for new dependencies
- **Repository pattern** — one repo per table, follow `IndicatorRepository` pattern exactly
- **Alembic** for migrations — create migration for new tables
- **loguru** for logging — not stdlib `logging`
- **pydantic-settings** for config — follow existing `Settings` class pattern
- **No LangChain** — use direct ollama client (per STACK.md anti-stack)
- **Timezone-aware datetimes** — `DateTime(timezone=True)`, `datetime.now(UTC)` (per Phase 1 lesson)
- **`BigInteger` for Vietnamese stock volumes** — can exceed 2 billion

## Sources

### Primary (HIGH confidence)
- CafeF RSS feeds — verified accessible 2026-04-15, 4 feeds × 50 items each, proper RSS structure
- VnExpress RSS kinh-doanh — verified accessible 2026-04-15, 60 items, proper structure
- Ollama Python client v0.6.1 — verified from PyPI and GitHub README, AsyncClient + format parameter confirmed
- Ollama API docs — verified `format` parameter accepts JSON Schema for structured output
- nvidia-smi — confirmed RTX 3060 12288 MiB total, 9752 MiB free
- Existing codebase — models.py, config.py, analysis_service.py, indicator_repo.py patterns verified
- CafeF article page structure — verified `detail-content`, `sapo` CSS classes, extractable via BS4

### Secondary (MEDIUM confidence)
- Qwen2.5 14B VRAM requirements — based on quantization math (14B × 4bit ÷ 8 ≈ 7GB + overhead). Empirical verification needed post-install.
- PITFALLS.md and ARCHITECTURE.md — project research documents with verified recommendations

### Tertiary (LOW confidence)
- Qwen2.5 Vietnamese financial text accuracy — not empirically tested. Based on training knowledge about multilingual capabilities.
- Sentiment aggregation decay function — no empirical basis for half-life choice, needs tuning with real data.
- Default scoring weights — subjective, no backtesting to validate.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, Ollama API verified from source
- Architecture: HIGH — follows established patterns from Phase 1 & 2 codebase
- News sources: HIGH — CafeF and VnExpress RSS verified working in real-time
- LLM integration: MEDIUM — API verified but Vietnamese financial sentiment accuracy unproven
- Scoring engine: MEDIUM — design sound but weights/thresholds need empirical validation
- Pitfalls: HIGH — drawn from project's own PITFALLS.md + runtime verification

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days — CafeF RSS stability may change; Ollama client API stable)
