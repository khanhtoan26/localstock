"""Phase 25 / DQ-01 — Tier 1 OHLCV schema tests (RED until 25-05).

These tests target the partition_valid_invalid runner + OHLCVSchema
(currently None / NotImplementedError stubs). RED until 25-05 lands the
strict pandera schema and partition logic.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from localstock.dq.runner import partition_valid_invalid


def _make_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _good_row(symbol: str = "AAA", d: date | None = None, **over) -> dict:
    base = {
        "symbol": symbol,
        "date": pd.Timestamp(d or date.today() - timedelta(days=1)),
        "open": 10.0,
        "high": 11.0,
        "low": 9.0,
        "close": 10.5,
        "volume": 1000,
    }
    base.update(over)
    return base


def test_negative_price_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame([_good_row(), _good_row(symbol="BBB", open=-1.0)])
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert invalid[0]["symbol"] == "BBB"


def test_future_date_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame(
        [
            _good_row(),
            _good_row(symbol="FUT", d=date.today() + timedelta(days=5)),
        ]
    )
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(invalid) == 1
    assert invalid[0]["symbol"] == "FUT"


def test_nan_ratio_threshold() -> None:
    """> 5% NaN per column triggers schema-level reject."""
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    rows = [_good_row(symbol=f"S{i}") for i in range(20)]
    # Inject NaN into >5% of close column (2 out of 20 = 10%).
    rows[0]["close"] = float("nan")
    rows[1]["close"] = float("nan")
    df = _make_frame(rows)
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    # Frame-level check fails → all rows considered invalid OR row-level
    # partition catches the offending rows.
    bad_symbols = {r["symbol"] for r in invalid}
    assert "S0" in bad_symbols or len(invalid) == len(df)


def test_duplicate_pk_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame([_good_row(symbol="DUP"), _good_row(symbol="DUP")])
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(invalid) >= 1
