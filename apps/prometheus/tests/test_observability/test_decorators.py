"""Phase 24 — @observe decorator unit tests (OBS-11).

Covers VALIDATION.md OBS-11 unit rows:
  1. test_observe_sync_success
  2. test_observe_async_success
  3. test_observe_sync_reraises_with_fail_outcome
  4. test_observe_async_reraises_with_fail_outcome
  5. test_observe_rejects_malformed_name
  6. test_timed_query_emits_op_metric
  7. test_observe_log_false_suppresses_log_but_emits_metric (RESEARCH §8 row 6)

The decorator looks up the ``localstock_op_duration_seconds`` histogram on
the *default* prometheus_client REGISTRY (already initialised at module
import via ``observability.metrics._DEFAULT_METRICS``). Each test uses a
unique ``action`` token so independent label tuples never collide.
"""
from __future__ import annotations

import asyncio

import pytest

from localstock.observability.decorators import observe, timed_query
from localstock.observability.metrics import init_metrics

_LABELS = ("domain", "subsystem", "action", "outcome")


def _count(domain: str, subsystem: str, action: str, outcome: str) -> float:
    """Return the cumulative ``_count`` sample for a label tuple on the
    default-registry op histogram (0.0 if no sample yet)."""
    hist = init_metrics()["op_duration_seconds"]
    target = (domain, subsystem, action, outcome)
    for metric in hist.collect():
        for s in metric.samples:
            if s.name.endswith("_count") and tuple(s.labels[k] for k in _LABELS) == target:
                return s.value
    return 0.0


# ---- 1. sync success -------------------------------------------------------

def test_observe_sync_success(loguru_caplog):
    before = _count("test", "unit", "sync_ok", "success")

    @observe("test.unit.sync_ok")
    def f(x: int) -> int:
        return x * 2

    assert f(3) == 6
    after = _count("test", "unit", "sync_ok", "success")
    assert after - before == pytest.approx(1.0), "histogram count must increment exactly once"

    completes = [r for r in loguru_caplog.records if r["message"] == "op_complete"
                 and r["extra"].get("op_name") == "test.unit.sync_ok"]
    assert len(completes) == 1
    rec = completes[0]
    assert rec["extra"]["outcome"] == "success"
    assert isinstance(rec["extra"]["duration_ms"], int)
    assert rec["extra"]["duration_ms"] >= 0


# ---- 2. async success ------------------------------------------------------

def test_observe_async_success(loguru_caplog):
    before = _count("test", "unit", "async_ok", "success")

    @observe("test.unit.async_ok")
    async def f(x: int) -> int:
        await asyncio.sleep(0)
        return x * 2

    assert asyncio.run(f(3)) == 6
    after = _count("test", "unit", "async_ok", "success")
    assert after - before == pytest.approx(1.0)

    completes = [r for r in loguru_caplog.records if r["message"] == "op_complete"
                 and r["extra"].get("op_name") == "test.unit.async_ok"]
    assert len(completes) == 1
    assert completes[0]["extra"]["outcome"] == "success"


# ---- 3. sync exception path ------------------------------------------------

def test_observe_sync_reraises_with_fail_outcome(loguru_caplog):
    before_fail = _count("test", "unit", "sync_boom", "fail")
    before_ok = _count("test", "unit", "sync_boom", "success")

    @observe("test.unit.sync_boom")
    def f() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        f()

    assert _count("test", "unit", "sync_boom", "fail") - before_fail == pytest.approx(1.0)
    assert _count("test", "unit", "sync_boom", "success") - before_ok == pytest.approx(0.0)

    fails = [r for r in loguru_caplog.records if r["message"] == "op_failed"
             and r["extra"].get("op_name") == "test.unit.sync_boom"]
    assert len(fails) == 1
    assert fails[0]["extra"]["error_type"] == "ValueError"
    assert fails[0]["extra"]["outcome"] == "fail"


# ---- 4. async exception path -----------------------------------------------

def test_observe_async_reraises_with_fail_outcome(loguru_caplog):
    before_fail = _count("test", "unit", "async_boom", "fail")

    @observe("test.unit.async_boom")
    async def f() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError, match="kaboom"):
        asyncio.run(f())

    assert _count("test", "unit", "async_boom", "fail") - before_fail == pytest.approx(1.0)

    fails = [r for r in loguru_caplog.records if r["message"] == "op_failed"
             and r["extra"].get("op_name") == "test.unit.async_boom"]
    assert len(fails) == 1
    assert fails[0]["extra"]["error_type"] == "RuntimeError"


# ---- 5. naming validation --------------------------------------------------

@pytest.mark.parametrize("bad", ["foo", "only.two", "a.b.c.d", "", "a..c", ".b.c", "a.b."])
def test_observe_rejects_malformed_name(bad: str):
    with pytest.raises(ValueError, match="domain.subsystem.action"):
        observe(bad)


# ---- 6. timed_query alias --------------------------------------------------

def test_timed_query_emits_op_metric(loguru_caplog):
    before = _count("db", "query", "upsert_prices", "success")

    @timed_query("upsert_prices")
    async def upsert() -> int:
        await asyncio.sleep(0)
        return 42

    assert asyncio.run(upsert()) == 42
    assert _count("db", "query", "upsert_prices", "success") - before == pytest.approx(1.0)


# ---- 7. log=False suppresses log but keeps metric --------------------------

def test_observe_log_false_suppresses_log_but_emits_metric(loguru_caplog):
    before = _count("test", "silent", "fn", "success")

    @observe("test.silent.fn", log=False)
    def f() -> int:
        return 1

    assert f() == 1
    assert _count("test", "silent", "fn", "success") - before == pytest.approx(1.0)

    silent_records = [r for r in loguru_caplog.records
                      if r["extra"].get("op_name") == "test.silent.fn"]
    assert silent_records == [], "log=False must suppress op_complete/op_failed"
