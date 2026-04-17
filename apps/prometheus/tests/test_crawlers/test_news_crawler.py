"""Unit tests for NewsCrawler RSS parsing, ticker extraction, and HTML sanitization."""

from datetime import UTC, datetime

import pytest

from localstock.crawlers.news_crawler import (
    NewsCrawler,
    extract_tickers,
    parse_rss_date,
    parse_rss_feed,
    sanitize_html,
)

# Sample RSS XML for tests
SAMPLE_RSS_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>CafeF</title>
    <item>
      <title>VNM doanh thu tăng 15%</title>
      <link>https://cafef.vn/vnm-doanh-thu-tang-20260415.chn</link>
      <description>&lt;p&gt;Vinamilk công bố kết quả kinh doanh quý 1&lt;/p&gt;</description>
      <pubDate>Tue, 15 Apr 2026 10:30:00 +0700</pubDate>
    </item>
    <item>
      <title>HPG sản lượng thép tăng mạnh</title>
      <link>https://cafef.vn/hpg-san-luong-thep-20260415.chn</link>
      <description>Hòa Phát công bố sản lượng thép</description>
      <pubDate>Tue, 15 Apr 2026 09:00:00 +0700</pubDate>
    </item>
    <item>
      <title>Thị trường biến động trong phiên sáng</title>
      <link>https://cafef.vn/thi-truong-bien-dong-20260415.chn</link>
      <description>Thị trường chứng khoán Việt Nam biến động mạnh</description>
      <pubDate>Mon, 14 Apr 2026 15:00:00 +0700</pubDate>
    </item>
  </channel>
</rss>"""


class TestParseRssFeed:
    """Tests for parse_rss_feed() function."""

    def test_parse_rss_xml(self):
        """Given valid RSS XML with 3 items, returns list of 3 dicts with expected keys."""
        result = parse_rss_feed(SAMPLE_RSS_XML, source="cafef", feed_url="https://cafef.vn/test.rss")

        assert len(result) == 3
        for item in result:
            assert "title" in item
            assert "url" in item
            assert "description" in item
            assert "published_at" in item
            assert "source" in item
            assert "source_feed" in item

        assert result[0]["title"] == "VNM doanh thu tăng 15%"
        assert result[0]["url"] == "https://cafef.vn/vnm-doanh-thu-tang-20260415.chn"
        assert result[0]["source"] == "cafef"
        assert result[0]["source_feed"] == "https://cafef.vn/test.rss"

    def test_parse_rss_description_html_stripped(self):
        """RSS description with HTML entities should be cleaned."""
        result = parse_rss_feed(SAMPLE_RSS_XML, source="cafef", feed_url="https://cafef.vn/test.rss")
        # Description should have HTML tags stripped
        desc = result[0]["description"]
        assert "<p>" not in desc
        assert "Vinamilk" in desc


class TestExtractTickers:
    """Tests for extract_tickers() function."""

    def test_extract_tickers(self):
        """Given text with VNM and HPG mentions, returns both (validated against known symbols)."""
        text = "VNM doanh thu tăng 15%, giống HPG đã làm"
        valid_symbols = {"VNM", "HPG", "FPT"}
        result = extract_tickers(text, valid_symbols)
        assert result == ["VNM", "HPG"]

    def test_extract_tickers_filters_non_tickers(self):
        """Common abbreviations (GDP, USD) are filtered out."""
        text = "GDP tăng, USD mạnh, VNM tốt"
        valid_symbols = {"VNM", "GDP", "USD"}
        result = extract_tickers(text, valid_symbols)
        assert result == ["VNM"]

    def test_extract_tickers_validates_against_known_symbols(self):
        """Only symbols in valid_symbols set are returned."""
        text = "ABC XYZ VNM"
        valid_symbols = {"VNM"}
        result = extract_tickers(text, valid_symbols)
        assert result == ["VNM"]

    def test_extract_tickers_deduplicates(self):
        """Duplicate mentions of same ticker return only one entry."""
        text = "VNM tốt, VNM tốt hơn nữa"
        valid_symbols = {"VNM"}
        result = extract_tickers(text, valid_symbols)
        assert result == ["VNM"]

    def test_extract_tickers_empty_text(self):
        """Empty text returns empty list."""
        result = extract_tickers("", {"VNM"})
        assert result == []


class TestSanitizeHtml:
    """Tests for sanitize_html() function."""

    def test_sanitize_html(self):
        """Strips all HTML tags including script tags."""
        html = "<p>Good news <script>alert(1)</script></p>"
        result = sanitize_html(html)
        assert result == "Good news"
        assert "<" not in result
        assert "script" not in result

    def test_sanitize_html_preserves_text(self):
        """Plain text passes through unchanged."""
        text = "VNM doanh thu tăng 15%"
        assert sanitize_html(text) == text

    def test_sanitize_html_complex_tags(self):
        """Handles div, span, a tags, iframes, styles."""
        html = '<div class="content"><span>Text</span> <a href="test">link</a> <iframe></iframe> <style>.x{}</style></div>'
        result = sanitize_html(html)
        assert "Text" in result
        assert "link" in result
        assert "<" not in result


class TestParseRssDate:
    """Tests for parse_rss_date() function."""

    def test_parse_rss_date_formats(self):
        """Parses RFC 2822 date with +0700 timezone correctly."""
        date_str = "Tue, 15 Apr 2026 10:30:00 +0700"
        result = parse_rss_date(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 15

    def test_parse_rss_date_invalid_fallback(self):
        """Invalid date string falls back to datetime.now(UTC)."""
        result = parse_rss_date("not a date")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
