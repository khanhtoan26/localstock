"""Signal computation functions for LLM prompt injection (SIGNAL-03).

Per CONTEXT.md decision: compute_sector_momentum accepts a pre-fetched dict
to remain unit-testable without live DB dependency.
"""


def compute_sector_momentum(sector_data: dict | None) -> dict | None:
    """Convert SectorSnapshot data to a named scalar for LLM injection (SIGNAL-03).

    Classifies sector money flow direction using avg_score_change thresholds
    aligned with SectorService.get_rotation_summary() (>2.0 inflow, <-2.0 outflow).

    Args:
        sector_data: Pre-fetched dict with keys:
            avg_score_change (float | None): day-over-day change in sector avg composite score.
            avg_score (float): current sector avg composite score.
            group_code (str): sector group identifier (e.g. "BKS", "TCB").
            Pass None if sector mapping unavailable for this stock.

    Returns:
        Dict with keys:
            label (str): "strong_inflow" (>2.0), "mild_inflow" (0 to 2.0],
                         "mild_outflow" [-2.0 to 0), "strong_outflow" (<-2.0)
            score_change (float): avg_score_change rounded to 2 decimal places
            group_code (str): sector group identifier
        Returns None if sector_data is None or avg_score_change is None.
    """
    if sector_data is None:
        return None

    score_change = sector_data.get("avg_score_change")
    if score_change is None:
        return None

    # Classify by threshold — aligned with SectorService inflow/outflow boundaries
    if score_change > 2.0:
        label = "strong_inflow"
    elif score_change > 0:
        label = "mild_inflow"
    elif score_change < -2.0:
        label = "strong_outflow"
    else:
        label = "mild_outflow"

    return {
        "label": label,
        "score_change": round(float(score_change), 2),
        "group_code": sector_data.get("group_code", ""),
    }
