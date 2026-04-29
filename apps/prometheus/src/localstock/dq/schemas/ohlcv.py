"""Phase 25 / DQ-01 — OHLCV pandera schemas (D-01).

Tier 1 (block-on-fail) schema: rejects negative price, future date,
NaN ratio > 5%, duplicate (symbol,date) PK. RESEARCH §Pattern 1 +
Pitfall E (date coerce — explicit notna check).
"""

from __future__ import annotations

from datetime import date

from pandera.pandas import Check, Column, DataFrameSchema

# VN HOSE tickers: 3-5 alphanum chars uppercase.
_SYMBOL_RE = r"^[A-Z0-9]{3,5}$"


OHLCVSchema = DataFrameSchema(
    columns={
        "symbol": Column(str, Check.str_matches(_SYMBOL_RE)),
        "date": Column("datetime64[ns]"),  # No coerce — Pitfall E
        "open": Column(float, Check.gt(0)),
        "high": Column(float, Check.gt(0)),
        "low": Column(float, Check.gt(0)),
        "close": Column(float, Check.gt(0)),
        "volume": Column(int, Check.ge(0)),
    },
    checks=[
        # Element-wise (Series-returning) — future date per row.
        Check(
            lambda df: df["date"].dt.date <= date.today(),
            error="future_date",
            name="future_date",
        ),
        # Frame-level scalar — NaN ratio per column ≤ 5%.
        Check(
            lambda df: bool(df.isna().mean().max() <= 0.05),
            error="nan_ratio_exceeded",
            name="nan_ratio_exceeded",
        ),
        # Pitfall E echo: explicit not-NA on date after upstream coercion.
        Check(
            lambda df: df["date"].notna(),
            error="malformed_date",
            name="malformed_date",
        ),
    ],
    unique=["symbol", "date"],
    strict=True,  # reject unknown columns
    coerce=True,  # coerce numerics; date type already datetime64
)


# Tier 2 placeholder — filled in 25-07.
OHLCVAdvisorySchema = None  # type: ignore[assignment]
