"""Phase 25 / DQ-02 — Indicator Tier 2 advisory predicates.

Implemented in 25-07. RSI lives in the technical indicators table
(separate from OHLCV), so it's exposed via a predicate rather than a
pandera column-level Check on the OHLCV schema (RESEARCH §Pattern 2).
"""
from __future__ import annotations


# Tier 2 placeholder — kept for backwards-compat re-exports.
IndicatorAdvisorySchema = None  # type: ignore[assignment]


def predicate_rsi_anomaly(df):
    """Return rows where RSI > 99.5.

    Defensive: if the input is missing the ``rsi`` column or is empty,
    returns an empty slice (no violation).
    """
    if df is None or not hasattr(df, "columns") or "rsi" not in df.columns:
        return df.iloc[0:0] if hasattr(df, "iloc") else df
    return df[df["rsi"] > 99.5]
