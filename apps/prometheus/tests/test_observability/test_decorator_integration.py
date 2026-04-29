"""Phase 24-05 / OBS-11 + ROADMAP SC-1 — integration: @observe applied to crawler.fetch.

Closes the gap between 24-01 (decorator unit tests in isolation) and the
ROADMAP SC-1 verbatim contract: the literal label combination
``domain=crawl,subsystem=ohlcv,action=fetch,outcome=success`` must appear
in ``/metrics`` after a real ``await PriceCrawler().fetch(...)`` call.
"""
from __future__ import annotations

import inspect

import pandas as pd
import pytest
from prometheus_client import REGISTRY

from localstock.crawlers.company_crawler import CompanyCrawler
from localstock.crawlers.event_crawler import EventCrawler
from localstock.crawlers.finance_crawler import FinanceCrawler
from localstock.crawlers.price_crawler import PriceCrawler


def _sample_count(domain: str, subsystem: str, action: str, outcome: str) -> float:
    """Read current localstock_op_duration_seconds_count for the label combo."""
    labels = {
        "domain": domain,
        "subsystem": subsystem,
        "action": action,
        "outcome": outcome,
    }
    val = REGISTRY.get_sample_value(
        "localstock_op_duration_seconds_count", labels
    )
    return val if val is not None else 0.0


def test_all_four_crawler_fetches_are_observe_wrapped():
    """24-01 D-01 — decorator preserves coroutine identity + exposes __wrapped__."""
    for cls in (PriceCrawler, FinanceCrawler, CompanyCrawler, EventCrawler):
        assert hasattr(cls.fetch, "__wrapped__"), (
            f"{cls.__name__}.fetch is not @observe-wrapped"
        )
        assert inspect.iscoroutinefunction(cls.fetch), (
            f"{cls.__name__}.fetch lost coroutine status"
        )


@pytest.mark.asyncio
async def test_crawl_fetch_emits_op_metric(monkeypatch):
    """ROADMAP SC-1 verbatim — domain=crawl,subsystem=ohlcv,action=fetch,outcome=success
    sample count must increase by >=1 after a real (decorated) fetch call."""
    before = _sample_count("crawl", "ohlcv", "fetch", "success")

    # Patch the deepest network helper so the real (decorated) PriceCrawler.fetch
    # body runs end-to-end and the @observe wrapper records on success.
    class _StubQuote:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start, end, interval):
            return pd.DataFrame(
                {
                    "time": ["2024-01-02"],
                    "open": [25000.0],
                    "high": [25800.0],
                    "low": [24800.0],
                    "close": [25500.0],
                    "volume": [1_000_000],
                }
            )

    # PriceCrawler.fetch does `from vnstock.explorer.kbs.quote import Quote as KBSQuote`
    # inside its `_fetch_sync` closure. Replace the attribute on the source module.
    import vnstock.explorer.kbs.quote as kbs_quote_mod

    monkeypatch.setattr(kbs_quote_mod, "Quote", _StubQuote)

    crawler = PriceCrawler(delay_seconds=0.0)
    df = await crawler.fetch("VCB")
    assert not df.empty

    after = _sample_count("crawl", "ohlcv", "fetch", "success")
    assert after >= before + 1, (
        f"Expected sample count to increase by >=1, got before={before} "
        f"after={after}. The @observe decorator did not fire at the call site."
    )
