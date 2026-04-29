"""Phase 25 / DQ-05 — per-symbol pipeline isolation tests.

Closes ROADMAP Success Criterion #3:

    "Pipeline with one symbol injecting an error completes the full run;
    PipelineRun.stats shows {succeeded: N-1, failed: 1, failed_symbols: [...]}
    instead of aborting."

Uses the AsyncMock-session harness (sibling test_pipeline_step_timing.py)
so the tests do not require a live Postgres database. The contract under
test is the in-memory aggregation of crawler-side ``failed`` lists into
``PipelineRun.stats.failed_symbols``.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from localstock.services.pipeline import Pipeline


def _build_pipe() -> Pipeline:
    """Build a Pipeline against an AsyncMock session (no Postgres)."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return Pipeline(session=session)


@pytest.mark.asyncio
async def test_one_bad_symbol_completes_batch() -> None:
    """SC #3 verbatim: 1 bad + N good → run completes; stats reflects 1 fail."""
    pipe = _build_pipe()

    # Stub repos / crawlers so run_full traverses end-to-end without I/O.
    pipe.stock_repo.fetch_and_store_listings = AsyncMock(return_value=0)
    pipe.stock_repo.get_all_hose_symbols = AsyncMock(
        return_value=["AAA", "BAD", "BBB"]
    )

    # ``_crawl_prices`` returns ({results}, [(symbol, error_str), ...]).
    # Inject ONE failure for "BAD" so isolation can be observed.
    pipe._crawl_prices = AsyncMock(
        return_value=(
            {"AAA": pd.DataFrame(), "BBB": pd.DataFrame()},
            [("BAD", "RuntimeError: simulated network error")],
        )
    )

    async def _empty_batch(_symbols: list[str]) -> tuple[dict, list]:
        return {}, []

    pipe.finance_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.company_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.event_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe._apply_price_adjustments = AsyncMock(return_value=None)

    run = await pipe.run_full(run_type="manual")

    # SC #3 verbatim assertions
    assert run.status == "completed", (
        f"Pipeline aborted instead of isolating; status={run.status}"
    )
    assert run.stats is not None
    assert run.stats["succeeded"] == 2  # AAA + BBB
    assert run.stats["failed"] == 1
    bad_symbols = {fs["symbol"] for fs in run.stats["failed_symbols"]}
    assert bad_symbols == {"BAD"}
    bad_steps = {fs["step"] for fs in run.stats["failed_symbols"]}
    assert "crawl" in bad_steps


@pytest.mark.asyncio
async def test_failed_symbols_step_recorded() -> None:
    """Step field carries the failing-step name (D-03 step granularity)."""
    pipe = _build_pipe()
    pipe.stock_repo.fetch_and_store_listings = AsyncMock(return_value=0)
    pipe.stock_repo.get_all_hose_symbols = AsyncMock(return_value=["AAA", "BAD"])
    pipe._crawl_prices = AsyncMock(
        return_value=({"AAA": pd.DataFrame()}, [("BAD", "boom")])
    )

    async def _empty_batch(_symbols: list[str]) -> tuple[dict, list]:
        return {}, []

    pipe.finance_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.company_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe.event_crawler.fetch_batch = AsyncMock(side_effect=_empty_batch)
    pipe._apply_price_adjustments = AsyncMock(return_value=None)

    run = await pipe.run_full(run_type="manual")
    assert run.stats is not None
    assert run.stats["failed_symbols"], "expected at least one failed_symbols entry"
    for fs in run.stats["failed_symbols"]:
        assert set(fs.keys()) >= {"symbol", "step", "error"}, (
            f"failed_symbols entry missing required keys: {fs}"
        )
        assert fs["step"] == "crawl"
        assert isinstance(fs["error"], str) and fs["error"]


@pytest.mark.asyncio
async def test_analyze_step_isolation() -> None:
    """One symbol failing in the analyze step does not abort the batch.

    AnalysisService.run_full's per-symbol loops are wrapped in try/except
    (DQ-05 / D-03). Inject an exception on _run_technical("BAD") and verify
    the loop continues, the failure is buffered in ``_failed_symbols``, and
    the success counter still increments for the good symbol.
    """
    from localstock.services.analysis_service import AnalysisService

    session = AsyncMock()
    svc = AnalysisService(session=session)

    svc.seed_industry_groups = AsyncMock(return_value=None)
    svc.stock_repo.get_all_hose_symbols = AsyncMock(return_value=["GOOD", "BAD"])
    svc.map_stock_industries = AsyncMock(return_value=None)
    svc._compute_all_industry_averages = AsyncMock(return_value=None)

    async def _tech(symbol: str) -> None:
        if symbol == "BAD":
            raise RuntimeError("simulated technical failure")

    async def _fund(symbol: str) -> None:
        if symbol == "BAD":
            raise ValueError("simulated fundamental failure")

    svc._run_technical = AsyncMock(side_effect=_tech)
    svc._run_fundamental = AsyncMock(side_effect=_fund)

    summary = await svc.run_full()

    assert summary["technical_success"] == 1
    assert summary["technical_failed"] == 1
    assert summary["fundamental_success"] == 1
    assert summary["fundamental_failed"] == 1

    failed = svc.get_failed_symbols()
    assert any(
        f["symbol"] == "BAD" and f["step"] == "analyze" for f in failed
    ), f"expected BAD/analyze in buffer, got {failed}"
    # Errors must be _truncate_error formatted (ExcClass: msg)
    assert all(
        ":" in f["error"] and f["error"].split(":", 1)[0]
        in {"RuntimeError", "ValueError"}
        for f in failed
        if f["symbol"] == "BAD"
    )


def test_no_gather_in_per_symbol_loops() -> None:
    """Pitfall A guardrail — services keep serial isolation, no gather over symbols."""
    from localstock.services import (
        admin_service,
        analysis_service,
        report_service,
        scoring_service,
        sentiment_service,
    )

    forbidden_modules = (
        analysis_service,
        scoring_service,
        sentiment_service,
        admin_service,
        report_service,
    )
    for mod in forbidden_modules:
        src = inspect.getsource(mod)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "asyncio.gather" in stripped and "symbol" in stripped:
                pytest.fail(
                    f"Pitfall A regression in {mod.__name__}: {stripped!r} — "
                    "per-symbol gather() is forbidden until Phase 27 bounded "
                    "concurrency lands."
                )
