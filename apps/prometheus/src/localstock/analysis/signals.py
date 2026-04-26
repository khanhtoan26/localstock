"""Signal computation functions for LLM prompt injection (SIGNAL-03).

Per D-01: compute_sector_momentum accepts a pre-fetched dict to remain
unit-testable without live DB dependency.
"""


def compute_sector_momentum(sector_data: dict | None) -> dict | None:
    """Convert SectorSnapshot data to a named scalar for LLM injection (SIGNAL-03).

    Args:
        sector_data: Pre-fetched dict with keys:
            avg_score_change (float | None): day-over-day change in sector avg composite score.
            avg_score (float): current sector avg composite score.
            group_code (str): sector group identifier.
            Pass None if sector mapping unavailable.

    Returns:
        Dict with keys label (str), score_change (float), group_code (str), or None.
        Labels: "strong_inflow" (>2.0), "mild_inflow" (0 to 2.0],
                "mild_outflow" [-2.0 to 0), "strong_outflow" (<-2.0).
        Returns None if sector_data is None or avg_score_change is None.
    """
    raise NotImplementedError("compute_sector_momentum not yet implemented — Wave 1 plan 04")
