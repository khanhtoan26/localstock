"""Phase 25 / DQ-06 — PipelineRun.stats dual-write tests (GREEN as of 25-04).

The ``stats`` JSONB column was added in 25-01's Alembic migration. Population
landed in 25-04 (this plan) — ``Pipeline._write_stats`` writes the structured
JSONB **and** dual-writes the legacy scalar columns per CONTEXT D-07 LOCKED.

Test tiers:
  * Unit — :func:`_truncate_error` (no DB, no event loop).
  * Integration — ``Pipeline.run_full`` end-to-end with ``AsyncMock`` session
    and stubbed crawlers/repos. We don't need real Postgres because the
    ``stats`` write is a plain attribute assignment on the in-memory
    ``PipelineRun`` row (see sibling ``test_pipeline_step_timing.py``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_mock_pipeline(symbols: list[str], failed_per_step: dict | None = None):
    """Build a Pipeline with all I/O stubbed.

    ``failed_per_step``: optional dict like ``{"price": [("BAD", "boom")]}``
    where the list is the ``failed`` return tuple of the corresponding crawler.
    """
    from localstock.services.pipeline import Pipeline

    failed_per_step = failed_per_step or {}
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    pipe = Pipeline(session=session)

    async def _listings() -> int:
        return 0

    async def _symbols() -> list[str]:
        return list(symbols)

    async def _adjust() -> None:
        return None

    pipe.stock_repo.fetch_and_store_listings = AsyncMock(side_effect=_listings)
    pipe.stock_repo.get_all_hose_symbols = AsyncMock(side_effect=_symbols)
    pipe._crawl_prices = AsyncMock(
        return_value=({}, failed_per_step.get("price", []))
    )
    pipe.finance_crawler.fetch_batch = AsyncMock(
        return_value=({}, failed_per_step.get("finance", []))
    )
    pipe.company_crawler.fetch_batch = AsyncMock(
        return_value=({}, failed_per_step.get("company", []))
    )
    pipe.event_crawler.fetch_batch = AsyncMock(
        return_value=({}, failed_per_step.get("event", []))
    )
    pipe._apply_price_adjustments = AsyncMock(side_effect=_adjust)
    return pipe


# ---------------------------------------------------------------------------
# Unit — _truncate_error contract
# ---------------------------------------------------------------------------


def test_error_truncation() -> None:
    """failed_symbols error field truncated at MAX_ERROR_CHARS=200 (Pitfall G)."""
    from localstock.dq import MAX_ERROR_CHARS
    from localstock.services.pipeline import _truncate_error

    long = "x" * 500
    out = _truncate_error(RuntimeError(long))
    # Class prefix + truncated message + ellipsis
    assert out.startswith("RuntimeError: ")
    # Total length bounded by class + ': ' + MAX_ERROR_CHARS + '...'
    assert len(out) <= len("RuntimeError: ") + MAX_ERROR_CHARS + 3
    # No traceback leaked — only str(exc) (T-25-04-01 mitigation)
    assert "Traceback" not in out


def test_error_truncation_short_message_unchanged() -> None:
    """Short error messages pass through with class prefix only."""
    from localstock.services.pipeline import _truncate_error

    out = _truncate_error(ValueError("nope"))
    assert out == "ValueError: nope"


# ---------------------------------------------------------------------------
# Integration — run_full populates stats JSONB + dual-writes scalars
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_jsonb_written() -> None:
    """run_full populates PipelineRun.stats with the documented schema."""
    pipe = _build_mock_pipeline(symbols=["AAA", "BBB", "CCC"])
    run = await pipe.run_full(run_type="manual")
    assert run.status == "completed"
    assert run.stats is not None
    assert {"succeeded", "failed", "skipped", "failed_symbols"} <= set(
        run.stats.keys()
    )
    assert run.stats["succeeded"] == 3
    assert run.stats["failed"] == 0
    assert run.stats["skipped"] == 0
    assert run.stats["failed_symbols"] == []


@pytest.mark.asyncio
async def test_dual_write_mirror() -> None:
    """symbols_success/total/failed mirror stats.* exactly through v1.5 (D-07)."""
    pipe = _build_mock_pipeline(
        symbols=["AAA", "BAD", "BBB"],
        failed_per_step={"price": [("BAD", "connection refused")]},
    )
    run = await pipe.run_full(run_type="manual")
    assert run.symbols_success == run.stats["succeeded"]
    assert run.symbols_failed == run.stats["failed"]
    assert run.symbols_total == (
        run.stats["succeeded"] + run.stats["failed"] + run.stats["skipped"]
    )
    # Failed-symbol shape contract (consumed by 25-06 isolation refactor).
    assert run.stats["failed"] == 1
    assert run.stats["failed_symbols"] == [
        {"symbol": "BAD", "step": "crawl", "error": "connection refused"}
    ]


@pytest.mark.asyncio
async def test_failed_symbol_error_bounded() -> None:
    """Per-error string in failed_symbols capped at MAX_ERROR_CHARS (Pitfall G)."""
    from localstock.dq import MAX_ERROR_CHARS

    huge = "x" * 1000
    pipe = _build_mock_pipeline(
        symbols=["AAA", "BAD"],
        failed_per_step={"finance": [("BAD", huge)]},
    )
    run = await pipe.run_full(run_type="manual")
    assert run.stats["failed"] == 1
    err_str = run.stats["failed_symbols"][0]["error"]
    assert len(err_str) <= MAX_ERROR_CHARS


@pytest.mark.asyncio
async def test_hard_failure_still_writes_stats() -> None:
    """Even when the crawl block raises, run_full leaves a structured stats trail.

    Contract: ``status="failed"`` rows MUST have ``stats`` populated so
    downstream readers (dashboards, alerts) never branch on NULL.
    """
    pipe = _build_mock_pipeline(symbols=["AAA", "BBB"])
    pipe._apply_price_adjustments = AsyncMock(
        side_effect=RuntimeError("analyzer exploded")
    )
    run = await pipe.run_full(run_type="manual")
    assert run.status == "failed"
    assert run.stats is not None
    assert run.stats["succeeded"] == 0
    assert run.stats["failed"] == 2
    assert run.stats["failed_symbols"][0]["symbol"] == "*"
    assert run.stats["failed_symbols"][0]["step"] == "pipeline"
    assert run.stats["failed_symbols"][0]["error"].startswith(
        "RuntimeError: analyzer exploded"
    )
