"""Macro score normalization — converts sector impact to 0-100 score.

Maps aggregate macro impact (-1.0 to +1.0) to score (0 to 100).
50 = neutral (no impact or no data).
"""

from localstock.macro.impact import get_macro_impact


def normalize_macro_score(
    sector_code: str | None, macro_conditions: dict[str, str]
) -> float:
    """Compute macro dimension score (0-100) for a stock's sector.

    50 = neutral (no macro impact or no data).
    >50 = macro conditions favorable for this sector.
    <50 = macro conditions unfavorable.

    Formula: score = 50 + (impact * 50), clamped to [0, 100].

    Args:
        sector_code: VN industry group code (e.g., 'BANKING'). None → neutral.
        macro_conditions: Dict of active macro conditions.
            Keys: 'interest_rate', 'exchange_rate', 'cpi', 'gdp'.
            Values: trend direction (e.g., 'rising', 'falling').

    Returns:
        Float in [0.0, 100.0]. 50.0 if no sector or no conditions.
    """
    if sector_code is None or not macro_conditions:
        return 50.0

    impact = get_macro_impact(sector_code, macro_conditions)
    score = 50.0 + (impact * 50.0)

    return max(0.0, min(100.0, score))
