"""Composite scoring engine — combines dimension scores with configurable weights.

Per SCOR-01: Composite score 0-100 combining available dimensions.
Per SCOR-02: Weights are configurable via ScoringConfig.
Per D-05: Grade letter (A/B/C/D/F) for display, numeric 0-100 internally.
Per Pitfall 5: Missing dimensions → redistribute weight proportionally.
Per T-03-07: Division by zero guard when total_weight == 0.
"""

from localstock.scoring import score_to_grade
from localstock.scoring.config import ScoringConfig


def compute_composite(
    tech: float | None,
    fund: float | None,
    sent: float | None,
    macro: float | None,
    config: ScoringConfig,
) -> tuple[float, str, int, dict]:
    """Compute composite score with dynamic weight redistribution.

    Args:
        tech: Technical dimension score (0-100) or None if unavailable.
        fund: Fundamental dimension score (0-100) or None if unavailable.
        sent: Sentiment dimension score (0-100) or None if unavailable.
        macro: Macro dimension score (0-100) or None if unavailable.
        config: ScoringConfig with weights.

    Returns:
        Tuple of (total_score, grade, dimensions_used, actual_weights_dict).
        actual_weights_dict contains the normalized weights actually applied,
        suitable for storing in CompositeScore.weights_json.
    """
    dimensions: dict[str, float] = {}
    weights: dict[str, float] = {}

    if tech is not None:
        dimensions["technical"] = tech
        weights["technical"] = config.weight_technical
    if fund is not None:
        dimensions["fundamental"] = fund
        weights["fundamental"] = config.weight_fundamental
    if sent is not None:
        dimensions["sentiment"] = sent
        weights["sentiment"] = config.weight_sentiment
    if macro is not None:
        dimensions["macro"] = macro
        weights["macro"] = config.weight_macro

    if not dimensions:
        return 0.0, "F", 0, {}

    # Normalize weights to sum to 1.0 (redistribution for missing dims)
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0, "F", 0, {}

    normalized_weights = {k: v / total_weight for k, v in weights.items()}

    total_score = sum(
        dimensions[k] * normalized_weights[k] for k in dimensions
    )

    # Clamp to 0-100
    total_score = max(0.0, min(100.0, total_score))
    grade = score_to_grade(total_score)
    dimensions_used = len(dimensions)

    return total_score, grade, dimensions_used, normalized_weights
