"""RSS-first news crawler for Vietnamese financial news.

Crawls CafeF and VnExpress RSS feeds, extracts article text,
and identifies stock tickers mentioned in articles.

Per D-01: Agent picks best sources — CafeF RSS primary (4 feeds, 50 items each),
VnExpress RSS secondary (kinh-doanh feed, 60 items).
"""

import asyncio
import re
from defusedxml.ElementTree import fromstring as safe_fromstring
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from localstock.config import get_settings

# Verified working RSS feeds (Research 2026-04-15)
CAFEF_RSS_FEEDS = [
    "https://cafef.vn/thi-truong-chung-khoan.rss",  # 50 items
    "https://cafef.vn/doanh-nghiep.rss",  # 50 items
    "https://cafef.vn/tai-chinh-ngan-hang.rss",  # 50 items
    "https://cafef.vn/vi-mo-dau-tu.rss",  # 50 items
]
VNEXPRESS_RSS_FEEDS = [
    "https://vnexpress.net/rss/kinh-doanh.rss",  # 60 items
]

# Ticker extraction pattern — 3 uppercase letters
TICKER_PATTERN = re.compile(r"\b([A-Z]{3})\b")

# Common abbreviations that look like tickers but aren't
NON_TICKERS = {
    "USD",
    "VND",
    "CEO",
    "GDP",
    "CPI",
    "ETF",
    "IPO",
    "FDI",
    "SBV",
    "HOSE",
    "HNX",
    "WTO",
    "FTA",
    "NHNN",
    "CTCK",
    "UBND",
    "BTC",
    "EUR",
    "JPY",
    "CNY",
    "GBP",
    "IMF",
    "WBG",
    "ADB",
    "ODA",
    "BOT",
    "PPP",
    "BDS",
    "DOC",
    "VON",
    "LAI",
    "THE",
    "AND",
    "FOR",
    "NOT",
    "BUT",
    "ALL",
    "CAN",
    "HER",
    "WAS",
    "ONE",
}

# HTTP headers to avoid anti-bot blocks (Pitfall 2)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def sanitize_html(html: str) -> str:
    """Strip ALL HTML tags from text. Prevents XSS from RSS content (T-03-03).

    Uses BeautifulSoup's get_text() to safely remove scripts, styles, iframes,
    and all other HTML elements.

    Args:
        html: Raw HTML string (may contain script tags, styles, etc.).

    Returns:
        Plain text with all HTML removed and whitespace normalized.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Remove script and style elements entirely
    for tag in soup(["script", "style", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Normalize whitespace
    return re.sub(r"\s+", " ", text).strip()


def parse_rss_date(date_str: str) -> datetime:
    """Parse RFC 2822 dates from RSS pubDate field.

    Handles "+0700" timezone offset common in Vietnamese feeds.
    Falls back to datetime.now(UTC) on parse failure.

    Args:
        date_str: Date string in RFC 2822 format.

    Returns:
        Timezone-aware datetime object.
    """
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        logger.warning("crawl.news.rss_date_parse_failed", date_str=repr(date_str))
        return datetime.now(UTC)


def parse_rss_feed(xml_text: str, source: str, feed_url: str) -> list[dict]:
    """Parse RSS XML and return list of article dicts.

    Args:
        xml_text: Raw RSS XML string.
        source: Source identifier (e.g., 'cafef', 'vnexpress').
        feed_url: URL the feed was fetched from.

    Returns:
        List of dicts with keys: title, url, description, published_at,
        source, source_feed.
    """
    articles = []
    try:
        root = safe_fromstring(xml_text)
    except Exception as e:
        logger.error("crawl.news.rss_parse_failed", feed_url=feed_url, error=str(e))
        return articles

    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        date_el = item.find("pubDate")

        title = title_el.text if title_el is not None and title_el.text else ""
        url = link_el.text if link_el is not None and link_el.text else ""
        raw_desc = desc_el.text if desc_el is not None and desc_el.text else ""
        date_str = date_el.text if date_el is not None and date_el.text else ""

        if not url:
            continue  # Skip items without links

        articles.append(
            {
                "title": title.strip(),
                "url": url.strip(),
                "description": sanitize_html(raw_desc),
                "published_at": parse_rss_date(date_str) if date_str else datetime.now(UTC),
                "source": source,
                "source_feed": feed_url,
            }
        )

    return articles


def extract_tickers(text: str, valid_symbols: set[str]) -> list[str]:
    """Extract stock ticker symbols from Vietnamese text.

    Uses regex to find 3-letter uppercase patterns, filters against
    known non-ticker abbreviations, and validates against known HOSE symbols.
    Deduplicates while preserving order of first appearance.

    Per Pitfall 3: Only returns tickers validated against valid_symbols
    to prevent noise from common abbreviations.

    Args:
        text: Article text to extract tickers from.
        valid_symbols: Set of known valid stock symbols (e.g., from stocks table).

    Returns:
        Deduplicated list of ticker symbols found, in order of appearance.
    """
    if not text:
        return []

    matches = TICKER_PATTERN.findall(text)
    seen: set[str] = set()
    result: list[str] = []

    for match in matches:
        if match in NON_TICKERS:
            continue
        if match not in valid_symbols:
            continue
        if match not in seen:
            seen.add(match)
            result.append(match)

    return result


class NewsCrawler:
    """RSS-first news crawler for Vietnamese financial news sites.

    Fetches RSS feeds from CafeF and VnExpress, parses article metadata,
    and optionally fetches full article content for enrichment.

    Does NOT extend BaseCrawler — BaseCrawler is designed for per-symbol
    fetching with DataFrame output. NewsCrawler fetches RSS feeds (not
    per-symbol) and returns dicts.

    Attributes:
        delay_seconds: Delay between HTTP requests to avoid rate limiting.
    """

    def __init__(self, delay_seconds: float = 1.0):
        self.delay_seconds = delay_seconds

    async def crawl_feeds(self, feeds: list[str] | None = None) -> list[dict]:
        """Crawl all RSS feeds and return parsed article dicts.

        Args:
            feeds: Optional list of RSS feed URLs. Defaults to all
                   CafeF + VnExpress feeds.

        Returns:
            Combined list of article dicts from all feeds.
        """
        if feeds is None:
            feeds = CAFEF_RSS_FEEDS + VNEXPRESS_RSS_FEEDS

        all_articles: list[dict] = []

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=30.0,
            verify=get_settings().ssl_verify,
        ) as client:
            for feed_url in feeds:
                try:
                    resp = await client.get(feed_url)
                    resp.raise_for_status()

                    # Determine source from URL
                    source = self._source_from_url(feed_url)
                    articles = parse_rss_feed(resp.text, source=source, feed_url=feed_url)
                    all_articles.extend(articles)
                    logger.info("crawl.news.feed_fetched", feed_url=feed_url, articles=len(articles))
                except Exception as e:
                    logger.warning("crawl.news.feed_failed", feed_url=feed_url, error=str(e))
                    continue  # Skip failed feeds

                await asyncio.sleep(self.delay_seconds)

        logger.info("crawl.news.total_fetched", articles=len(all_articles))
        return all_articles

    async def enrich_articles(
        self, articles: list[dict], client: httpx.AsyncClient
    ) -> list[dict]:
        """Fetch full article content for articles missing content field.

        Args:
            articles: List of article dicts (from crawl_feeds).
            client: Shared httpx.AsyncClient for HTTP requests.

        Returns:
            Same articles list with content field populated where possible.
        """
        for article in articles:
            if article.get("content"):
                continue  # Already has content

            url = article.get("url", "")
            try:
                content = await self._fetch_article_content(url, client)
                article["content"] = content
            except Exception as e:
                logger.warning("crawl.news.article_fetch_failed", url=url, error=str(e))
                article["content"] = None

            await asyncio.sleep(self.delay_seconds)

        return articles

    async def _fetch_article_content(
        self, url: str, client: httpx.AsyncClient
    ) -> str | None:
        """Fetch article page and extract main text.

        For CafeF: find div.detail-content
        For VnExpress: find article.fck_detail
        Truncate to 2000 chars max (Pitfall 1).
        Sanitize HTML before returning.

        Args:
            url: Article URL to fetch.
            client: httpx.AsyncClient instance.

        Returns:
            Extracted and sanitized article text, or None if extraction fails.
        """
        resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=30.0)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try CafeF article layout
        content_div = soup.find("div", class_="detail-content")
        if content_div is None:
            # Try VnExpress article layout
            content_div = soup.find("article", class_="fck_detail")
        if content_div is None:
            # Fallback: try generic article/main tags
            content_div = soup.find("article") or soup.find("main")

        if content_div is None:
            logger.debug("crawl.news.article_no_content_element", url=url)
            return None

        raw_html = str(content_div)
        text = sanitize_html(raw_html)

        # Truncate to 2000 chars to prevent context overflow (Pitfall 1)
        return text[:2000] if text else None

    @staticmethod
    def _source_from_url(url: str) -> str:
        """Determine source name from feed URL.

        Args:
            url: RSS feed URL.

        Returns:
            Source identifier string.
        """
        if "cafef.vn" in url:
            return "cafef"
        elif "vnexpress.net" in url:
            return "vnexpress"
        else:
            return "unknown"
