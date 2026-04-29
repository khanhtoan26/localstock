"""Phase 25 / DQ-02 + DQ-03 — Tier 2 dispatcher tests (RED until 25-07)."""

from __future__ import annotations

import pandas as pd
import pytest
from prometheus_client import CollectorRegistry

from localstock.dq.runner import evaluate_tier2
from localstock.dq.shadow import get_tier2_mode
from localstock.observability.metrics import init_metrics


def test_default_mode_is_shadow() -> None:
    assert get_tier2_mode("rsi") == "shadow"


def test_rsi_advisory_metric_emitted() -> None:
    """Even in shadow mode, dq_violations_total{rule, tier='advisory'} increments."""
    reg = CollectorRegistry()
    m = init_metrics(reg)
    _ = m["dq_violations_total"]
    df = pd.DataFrame({"rsi": [50.0, 99.7, 30.0]})
    evaluate_tier2(
        "rsi_anomaly",
        df,
        predicate=lambda d: d[d["rsi"] > 99.5],
        symbol="AAA",
    )
    sample = reg.get_sample_value(
        "localstock_dq_violations_total",
        {"rule": "rsi_anomaly", "tier": "advisory"},
    )
    assert sample is not None and sample >= 1


def test_gap_shadow_no_raise() -> None:
    """Shadow mode logs + counts but does NOT raise."""
    df = pd.DataFrame({"close": [100.0, 60.0]})  # 40% gap
    evaluate_tier2(
        "gap",
        df,
        predicate=lambda d: d.assign(pct=d["close"].pct_change().abs()).query(
            "pct > 0.30"
        ),
        symbol="GAP",
    )


def test_missing_rows_advisory() -> None:
    """missing > 20% emits warning, no raise."""
    df = pd.DataFrame({"v": [1.0, None, None, 4.0, 5.0]})  # 40% missing
    evaluate_tier2(
        "missing_rows",
        df,
        predicate=lambda d: d[d["v"].isna()],
        symbol="M",
    )


def test_promotion_to_strict_raises(monkeypatch) -> None:
    """DQ-03: setting DQ_TIER2_RSI_MODE=enforce flips advisory→strict and raises."""
    from localstock.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("DQ_TIER2_RSI_MODE", "enforce")
    df = pd.DataFrame({"rsi": [99.9]})
    with pytest.raises(Exception):  # Tier2Violation defined in 25-07
        evaluate_tier2(
            "rsi",
            df,
            predicate=lambda d: d[d["rsi"] > 99.5],
            symbol="X",
        )
