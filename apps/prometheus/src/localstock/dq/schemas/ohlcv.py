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


# ----------------------------------------------------------------------
# Tier 2 (advisory) predicates — DQ-02 / 25-07.
# Used by evaluate_tier2 from AnalysisService. RESEARCH §Pattern 2.
# ----------------------------------------------------------------------
def predicate_gap_30pct(df):
    """Return rows where consecutive close-to-close gap exceeds 30%.

    Sorts by date (defensive — caller frame may not be sorted), computes
    the absolute pct-change between consecutive closes, and returns the
    rows whose gap > 0.30. Rows with NaN previous close (the very first
    bar) are dropped.
    """
    import pandas as pd

    if df is None or len(df) < 2 or "close" not in df.columns:
        return df.iloc[0:0] if hasattr(df, "iloc") else df
    work = df.copy()
    if "date" in work.columns:
        work = work.sort_values("date")
    prev = work["close"].shift(1)
    pct = (work["close"] - prev).abs() / prev.replace(0, pd.NA)
    work = work.assign(_gap_pct=pct)
    bad = work[work["_gap_pct"] > 0.30].dropna(subset=["_gap_pct"])
    return bad


def predicate_missing_rows_20pct(df, *, expected_session_count: int):
    """Flag the entire frame if missing > 20% of expected rows.

    Returns a single-row DataFrame (signal) when the missing-row ratio
    exceeds 20%, else an empty DataFrame. Used as a frame-level Tier 2
    advisory check.
    """
    if df is None or expected_session_count is None or expected_session_count <= 0:
        return df.iloc[0:0] if hasattr(df, "iloc") else df
    actual = len(df)
    missing_ratio = 1.0 - (actual / float(expected_session_count))
    if missing_ratio > 0.20:
        return df.iloc[0:1] if not df.empty else df
    return df.iloc[0:0]
