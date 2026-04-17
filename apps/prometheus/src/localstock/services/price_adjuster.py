"""Backward price adjustment for corporate actions (DATA-05).

Adjustment formula (per research Pitfall 2):
- For stock split with ratio R: price_adj = price / R, volume_adj = volume * R
- For stock dividend with ratio R (e.g., 1.1 for 10%): same formula
- Adjustments are applied BACKWARD from ex_date — all prices BEFORE ex_date are adjusted
- Prices on or after ex_date remain unchanged
"""

from datetime import date

import pandas as pd
from loguru import logger


def adjust_prices_for_event(
    prices: pd.DataFrame,
    ex_date: date,
    ratio: float,
) -> pd.DataFrame:
    """Adjust historical prices backward from ex_date.

    Args:
        prices: DataFrame with columns [date, open, high, low, close, volume].
        ex_date: The ex-rights date (ngày GDKHQ).
        ratio: The adjustment ratio (e.g., 2.0 for 2:1 split,
               1.1 for 10% stock dividend).

    Returns:
        DataFrame with adjusted prices before ex_date.
        Prices on/after ex_date unchanged.
    """
    if prices.empty:
        return prices

    df = prices.copy()
    mask = df["date"] < ex_date
    adjustment_factor = 1.0 / ratio

    for col in ["open", "high", "low", "close"]:
        df.loc[mask, col] = df.loc[mask, col] * adjustment_factor
    df.loc[mask, "volume"] = (df.loc[mask, "volume"] * ratio).astype(int)

    logger.info(
        f"Adjusted {mask.sum()} rows before {ex_date} with ratio {ratio} "
        f"(factor={adjustment_factor:.6f})"
    )
    return df


def compute_adjustment_factor(events: list[dict]) -> float:
    """Compute cumulative adjustment factor from multiple corporate events.

    Args:
        events: list of {"ex_date": date, "ratio": float}
                sorted by ex_date ascending.

    Returns:
        Cumulative factor: 1 / (ratio1 * ratio2 * ... * ratioN).
    """
    cumulative_ratio = 1.0
    for event in events:
        cumulative_ratio *= event["ratio"]
    return 1.0 / cumulative_ratio
