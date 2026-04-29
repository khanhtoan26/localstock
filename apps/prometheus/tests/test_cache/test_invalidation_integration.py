"""CACHE-03 / Phase 26-05 — invalidate hooks fire after each pipeline write phase.

These tests exercise the `invalidate_namespace` helper used by the
hooks in `automation_service.py` (lines 109/142/174 per RESEARCH §3).
They are smoke-level: per the plan, the hooks themselves are
straightforward `try/invalidate_namespace/except` blocks; what matters
is that the namespaces match and that failures never raise.
"""
from __future__ import annotations

import pytest

from localstock.cache import get_or_compute, invalidate_namespace
from localstock.cache.registry import _caches


async def _seed(ns: str, key: str, val: object = "x") -> None:
    async def c():
        return val

    await get_or_compute(ns, key, c)


@pytest.mark.asyncio
async def test_analysis_phase_invalidates_indicators():
    await _seed("indicators", "AAA:run=1")
    assert len(_caches["indicators"]) == 1
    invalidate_namespace("indicators")
    assert len(_caches["indicators"]) == 0


@pytest.mark.asyncio
async def test_scoring_phase_invalidates_both_score_namespaces():
    await _seed("scores:ranking", "limit=50:run=1")
    await _seed("scores:symbol", "AAA:run=1")
    assert len(_caches["scores:ranking"]) == 1
    assert len(_caches["scores:symbol"]) == 1
    invalidate_namespace("scores:ranking")
    invalidate_namespace("scores:symbol")
    assert len(_caches["scores:ranking"]) == 0
    assert len(_caches["scores:symbol"]) == 0


@pytest.mark.asyncio
async def test_sector_rotation_invalidates_market_and_run_id():
    await _seed("market:summary", "run=1")
    await _seed("pipeline:latest_run_id", "current", val=1)
    assert len(_caches["market:summary"]) == 1
    assert len(_caches["pipeline:latest_run_id"]) == 1
    invalidate_namespace("market:summary")
    invalidate_namespace("pipeline:latest_run_id")
    assert len(_caches["market:summary"]) == 0
    assert len(_caches["pipeline:latest_run_id"]) == 0


@pytest.mark.asyncio
async def test_invalidation_failure_does_not_raise():
    """D-04 — invalidate failures are logged + swallowed, never raise."""
    n = invalidate_namespace("nonexistent")
    assert n == 0


def test_automation_service_imports_invalidate_namespace():
    """Hook source-level guard — the import must be present in
    automation_service.py so the 4 hook blocks below resolve.
    """
    import localstock.services.automation_service as automod

    assert hasattr(automod, "invalidate_namespace"), (
        "automation_service.py must import `invalidate_namespace` for the "
        "post-success-phase hooks (RESEARCH §3)"
    )


def test_automation_service_has_invalidate_calls_in_pipeline():
    """Hook count guard — count the 4 hook namespaces (`indicators`,
    `scores:ranking`, `scores:symbol`, `market:summary`,
    `pipeline:latest_run_id`) referenced in the pipeline body.
    """
    import inspect

    import localstock.services.automation_service as automod

    src = inspect.getsource(automod.AutomationService.run_daily_pipeline)
    expected_namespaces = (
        "indicators",
        "scores:ranking",
        "scores:symbol",
        "market:summary",
        "pipeline:latest_run_id",
    )
    for ns in expected_namespaces:
        assert f'"{ns}"' in src or f"'{ns}'" in src, (
            f"namespace `{ns}` not found in run_daily_pipeline body"
        )
