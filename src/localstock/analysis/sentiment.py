"""Sentiment score aggregation with time-weighted decay.

Per SENT-03: Aggregates per-article sentiment scores into a single
score per stock ticker, weighting recent articles more heavily.

Per Research Pitfall 6: Uses exponential decay to prevent stale
sentiment from dominating the score. Half-life = 3 days by default.

Note: score_to_grade is imported from localstock.scoring (created in Plan 01)
and re-exported here for convenience.
"""

import math
from datetime import UTC, datetime

from localstock.scoring import score_to_grade  # noqa: F401 — re-export


def aggregate_sentiment(
    scores: list[dict],
    now: datetime | None = None,
    half_life_days: float = 3.0,
) -> float | None:
    """Compute time-weighted average of sentiment scores.

    Uses exponential decay so that recent articles have more influence
    than older ones. With a half-life of 3 days, a 3-day-old article
    has half the weight of a brand new article.

    Args:
        scores: List of dicts with 'score' (float 0-1) and 'computed_at' (datetime).
        now: Reference time for decay calculation. Defaults to datetime.now(UTC).
        half_life_days: Exponential decay half-life in days. Default 3.0.

    Returns:
        Weighted average score (0.0 to 1.0), or None if no scores provided.
    """
    if not scores:
        return None

    if now is None:
        now = datetime.now(UTC)

    total_weight = 0.0
    weighted_sum = 0.0
    decay_constant = math.log(2) / half_life_days

    for s in scores:
        age_days = (now - s["computed_at"]).total_seconds() / 86400.0
        weight = math.exp(-decay_constant * max(age_days, 0.0))
        weighted_sum += s["score"] * weight
        total_weight += weight

    if total_weight < 1e-10:
        return None

    return weighted_sum / total_weight
