"""CACHE-03 / D-06 — indicator cache wrapper at analysis_service.py:264.

Cache key: ``indicators:{symbol}:run={run_id}`` (D-06 ratified —
no `{indicator_name}` segment since pandas-ta computes all 11
indicators in one bundled call).
"""
from __future__ import annotations

import inspect
import time
from unittest.mock import MagicMock

import pandas as pd
import pytest

from localstock.cache import invalidate_namespace
from localstock.cache.registry import _caches


def _make_svc():
    """Build an AnalysisService stub with only `analyze_technical_single`
    overridden — the wrapper does not touch any other attribute.
    """
    from localstock.services.analysis_service import AnalysisService

    svc = AnalysisService.__new__(AnalysisService)
    svc.analyze_technical_single = MagicMock(return_value={"rsi": 50.0})
    return svc


@pytest.mark.asyncio
async def test_second_call_is_hit():
    invalidate_namespace("indicators")
    svc = _make_svc()
    df = pd.DataFrame({"close": [10, 11, 12, 13]})

    v1 = await svc.cached_analyze_technical_single("AAA", df, run_id=1)
    v2 = await svc.cached_analyze_technical_single("AAA", df, run_id=1)

    assert v1 == v2 == {"rsi": 50.0}
    assert svc.analyze_technical_single.call_count == 1, (
        "indicator cache did not deduplicate same-run computation"
    )


@pytest.mark.asyncio
async def test_run_id_change_invalidates_logically():
    invalidate_namespace("indicators")
    svc = _make_svc()
    df = pd.DataFrame({"close": [10, 11, 12]})

    await svc.cached_analyze_technical_single("AAA", df, run_id=1)
    # New run_id → new key → must recompute
    await svc.cached_analyze_technical_single("AAA", df, run_id=2)
    assert svc.analyze_technical_single.call_count == 2


@pytest.mark.asyncio
async def test_none_run_id_bypasses_cache():
    invalidate_namespace("indicators")
    svc = _make_svc()
    df = pd.DataFrame({"close": [10, 11, 12]})

    await svc.cached_analyze_technical_single("AAA", df, run_id=None)
    await svc.cached_analyze_technical_single("AAA", df, run_id=None)
    # Bypass: every call computes
    assert svc.analyze_technical_single.call_count == 2
    # And nothing was cached
    assert len(_caches["indicators"]) == 0


def test_indicator_wrapper_requires_run_id_param():
    """W2 — wrapper signature MUST take run_id as a parameter so caller
    can hoist resolution out of the per-symbol loop. Calling without it
    must raise TypeError at bind-time, not silently resolve internally.
    """
    from localstock.services.analysis_service import AnalysisService

    sig = inspect.signature(AnalysisService.cached_analyze_technical_single)
    params = list(sig.parameters.keys())
    assert "run_id" in params, (
        f"wrapper missing required `run_id` parameter; got {params}"
    )
    run_id_param = sig.parameters["run_id"]
    assert run_id_param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ), f"`run_id` has unexpected kind {run_id_param.kind}"
    # No default — caller must supply it (None is allowed only as an
    # explicit bypass signal, which the caller must pass intentionally).
    assert run_id_param.default is inspect.Parameter.empty, (
        "`run_id` MUST NOT have a default — caller must pass it explicitly "
        "(W2 — loop invariant; the wrapper must not silently resolve)"
    )


@pytest.mark.asyncio
async def test_indicator_cache_speedup_across_400_symbols():
    """SC #4 closure — coarse-grained timing test (Q-4, no pytest-benchmark).

    Simulate a 2nd-run scenario across a small symbol fanout: when
    `analyze_technical_single` is artificially slow, the cache hits in
    the second pass should drop total time substantially (>50%).
    """
    invalidate_namespace("indicators")

    SLEEP_S = 0.002  # 2ms — keeps total wall-clock under 200ms for 50 syms

    def slow_compute(symbol, df):
        time.sleep(SLEEP_S)
        return {"rsi": 50.0, "symbol": symbol}

    from localstock.services.analysis_service import AnalysisService

    svc = AnalysisService.__new__(AnalysisService)
    svc.analyze_technical_single = MagicMock(side_effect=slow_compute)

    df = pd.DataFrame({"close": [10, 11, 12]})
    symbols = [f"S{i:03d}" for i in range(50)]
    run_id = 42

    # First pass — all misses
    t0 = time.perf_counter()
    for sym in symbols:
        await svc.cached_analyze_technical_single(sym, df, run_id=run_id)
    miss_dur = time.perf_counter() - t0
    assert svc.analyze_technical_single.call_count == 50

    # Second pass — same run_id, all hits
    t0 = time.perf_counter()
    for sym in symbols:
        await svc.cached_analyze_technical_single(sym, df, run_id=run_id)
    hit_dur = time.perf_counter() - t0
    assert svc.analyze_technical_single.call_count == 50, (
        "cache hit pass triggered recomputation"
    )

    # SC #4 — hit pass must be >50% faster than miss pass.
    assert hit_dur < miss_dur * 0.5, (
        f"indicator cache speedup insufficient: miss={miss_dur:.3f}s "
        f"hit={hit_dur:.3f}s ratio={hit_dur / miss_dur:.2%}"
    )
