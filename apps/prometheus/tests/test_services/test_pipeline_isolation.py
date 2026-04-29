"""Phase 25 / DQ-05 — per-symbol pipeline isolation tests (RED until 25-06)."""

from __future__ import annotations

import pytest


pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]


async def test_one_bad_symbol_completes_batch(monkeypatch) -> None:
    """If one symbol's _crawl_prices raises, the other symbols still complete.

    DQ-06 contract: stats.failed_symbols includes BAD with step="crawl".
    """
    from localstock.services.pipeline import Pipeline

    pipe = Pipeline()  # Pipeline() ctor surface may change in 25-06.

    async def fake_get_symbols(self):  # noqa: ARG001
        return ["AAA", "BAD", "BBB"]

    monkeypatch.setattr(
        "localstock.db.repositories.stock_repo.StockRepository.get_all_hose_symbols",
        fake_get_symbols,
        raising=False,
    )

    async def fake_fetch(self, symbol, **kw):  # noqa: ARG001
        if symbol == "BAD":
            raise RuntimeError("network down")
        import pandas as pd

        return pd.DataFrame()

    monkeypatch.setattr(
        "localstock.crawlers.price_crawler.PriceCrawler.fetch",
        fake_fetch,
        raising=False,
    )

    run = await pipe.run_full(run_type="manual")
    assert run.status == "completed"
    assert run.stats is not None
    failed = {fs["symbol"]: fs for fs in run.stats["failed_symbols"]}
    assert "BAD" in failed
    assert failed["BAD"]["step"] == "crawl"


async def test_failed_symbols_step_recorded() -> None:
    pytest.skip(
        "Implemented as part of test_one_bad_symbol_completes_batch — see 25-06"
    )


async def test_analyze_step_isolation() -> None:
    """One symbol failing in analyze step does not abort the batch."""
    pytest.skip("DQ-05: implemented in 25-06-PLAN.md")
