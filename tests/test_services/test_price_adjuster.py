"""Tests for backward price adjustment service (DATA-05).

TDD: Tests written before implementation.
Verifies:
- 2:1 split adjustment (prices halved, volumes doubled before ex_date)
- 10% stock dividend adjustment (prices divided by 1.1 before ex_date)
- Prices on/after ex_date are NOT modified
- Empty DataFrame handled gracefully
- All OHLC columns are adjusted (not just close)
- Cumulative adjustment factor chains multiple events
- EventCrawler event type parsing
"""

from datetime import date

import pandas as pd
import pytest

from localstock.services.price_adjuster import (
    adjust_prices_for_event,
    compute_adjustment_factor,
)


@pytest.fixture
def price_df():
    """10 days of price data around an ex-date of 2024-06-15."""
    dates = [date(2024, 6, d) for d in range(10, 20)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [100.0] * 10,
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "close": [102.0] * 10,
            "volume": [1_000_000] * 10,
        }
    )


def test_adjust_for_2_to_1_split(price_df):
    """2:1 split on 2024-06-15: prices before halved, volumes doubled."""
    result = adjust_prices_for_event(
        price_df, ex_date=date(2024, 6, 15), ratio=2.0
    )
    # Before ex_date (June 10-14): prices should be halved
    before = result[result["date"] < date(2024, 6, 15)]
    assert before["close"].tolist() == pytest.approx([51.0] * 5)
    assert before["open"].tolist() == pytest.approx([50.0] * 5)
    assert before["high"].tolist() == pytest.approx([52.5] * 5)
    assert before["low"].tolist() == pytest.approx([47.5] * 5)
    assert (before["volume"] == 2_000_000).all()
    # On or after ex_date (June 15-19): unchanged
    after = result[result["date"] >= date(2024, 6, 15)]
    assert after["close"].tolist() == pytest.approx([102.0] * 5)
    assert (after["volume"] == 1_000_000).all()


def test_adjust_for_10pct_stock_dividend(price_df):
    """10% stock dividend: ratio=1.1, prices before divided by 1.1."""
    result = adjust_prices_for_event(
        price_df, ex_date=date(2024, 6, 15), ratio=1.1
    )
    before = result[result["date"] < date(2024, 6, 15)]
    assert before["close"].tolist() == pytest.approx([102.0 / 1.1] * 5, rel=1e-4)
    assert before["open"].tolist() == pytest.approx([100.0 / 1.1] * 5, rel=1e-4)
    assert before["high"].tolist() == pytest.approx([105.0 / 1.1] * 5, rel=1e-4)
    assert before["low"].tolist() == pytest.approx([95.0 / 1.1] * 5, rel=1e-4)


def test_adjust_empty_dataframe():
    """Empty DataFrame returns unchanged."""
    empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    result = adjust_prices_for_event(empty, ex_date=date(2024, 6, 15), ratio=2.0)
    assert result.empty


def test_adjust_does_not_modify_after_exdate(price_df):
    """Prices on or after ex_date are NOT modified."""
    original_after = price_df[price_df["date"] >= date(2024, 6, 15)]["close"].tolist()
    result = adjust_prices_for_event(
        price_df, ex_date=date(2024, 6, 15), ratio=2.0
    )
    result_after = result[result["date"] >= date(2024, 6, 15)]["close"].tolist()
    assert original_after == result_after


def test_adjust_all_ohlc_columns(price_df):
    """All 4 OHLC columns are adjusted, not just close."""
    result = adjust_prices_for_event(
        price_df, ex_date=date(2024, 6, 15), ratio=2.0
    )
    before = result[result["date"] < date(2024, 6, 15)]
    assert before["open"].tolist() == pytest.approx([50.0] * 5)
    assert before["high"].tolist() == pytest.approx([52.5] * 5)
    assert before["low"].tolist() == pytest.approx([47.5] * 5)
    assert before["close"].tolist() == pytest.approx([51.0] * 5)


def test_compute_adjustment_factor_chains_events():
    """Multiple events chain: split 2:1 then 10% dividend → factor = 1/(2.0*1.1)."""
    events = [
        {"ex_date": date(2024, 3, 1), "ratio": 2.0},
        {"ex_date": date(2024, 6, 1), "ratio": 1.1},
    ]
    factor = compute_adjustment_factor(events)
    assert factor == pytest.approx(1.0 / (2.0 * 1.1), rel=1e-6)


def test_adjust_preserves_original_dataframe(price_df):
    """Adjustment returns a copy — original DataFrame is not modified."""
    original_close = price_df["close"].tolist()
    adjust_prices_for_event(price_df, ex_date=date(2024, 6, 15), ratio=2.0)
    assert price_df["close"].tolist() == original_close


class TestEventCrawlerParsing:
    """Tests for EventCrawler event type parsing."""

    def test_parse_event_type_split(self):
        from localstock.crawlers.event_crawler import EventCrawler

        assert EventCrawler.parse_event_type("split") == "split"

    def test_parse_event_type_stock_dividend(self):
        from localstock.crawlers.event_crawler import EventCrawler

        assert EventCrawler.parse_event_type("stock_dividend") == "stock_dividend"

    def test_parse_event_type_bonus_share_maps_to_stock_dividend(self):
        from localstock.crawlers.event_crawler import EventCrawler

        assert EventCrawler.parse_event_type("bonus_share") == "stock_dividend"

    def test_parse_event_type_unknown_returns_original(self):
        from localstock.crawlers.event_crawler import EventCrawler

        assert EventCrawler.parse_event_type("some_new_type") == "some_new_type"

    def test_parse_event_type_none_returns_unknown(self):
        from localstock.crawlers.event_crawler import EventCrawler

        assert EventCrawler.parse_event_type(None) == "unknown"
