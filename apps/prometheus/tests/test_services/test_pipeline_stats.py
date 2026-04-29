"""Phase 25 / DQ-06 — PipelineRun.stats dual-write tests (RED until 25-04).

The `stats` JSONB column was added in 25-01's Alembic migration. Population
lands in 25-04, which adds the `_truncate_error` helper and the dual-write
glue inside Pipeline.run_full.
"""

from __future__ import annotations

import pytest


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_stats_jsonb_written() -> None:
    from localstock.services.pipeline import Pipeline

    pipe = Pipeline()
    run = await pipe.run_full(run_type="manual")
    assert run.stats is not None
    assert {"succeeded", "failed", "skipped", "failed_symbols"} <= set(
        run.stats.keys()
    )


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_dual_write_mirror() -> None:
    """symbols_success/total/failed mirror stats.* exactly through v1.5 (D-07)."""
    from localstock.services.pipeline import Pipeline

    pipe = Pipeline()
    run = await pipe.run_full(run_type="manual")
    assert run.symbols_success == run.stats["succeeded"]
    assert run.symbols_failed == run.stats["failed"]
    assert (
        run.symbols_total
        == run.stats["succeeded"] + run.stats["failed"] + run.stats["skipped"]
    )


def test_error_truncation() -> None:
    """failed_symbols error field truncated at MAX_ERROR_CHARS=200 (Pitfall G)."""
    from localstock.dq import MAX_ERROR_CHARS
    from localstock.services.pipeline import _truncate_error  # added in 25-04

    long = "x" * 500
    out = _truncate_error(RuntimeError(long))
    assert len(out) <= MAX_ERROR_CHARS + 30  # +30 for "RuntimeError: " prefix budget
    assert out.startswith("RuntimeError")
