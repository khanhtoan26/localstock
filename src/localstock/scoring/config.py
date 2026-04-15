"""Scoring configuration — reads from Settings, provides typed access.

Per D-06: Weights are configurable via environment variables.
Per D-04: Default weights: tech 35%, fund 35%, sentiment 30%, macro 0%.
"""

from dataclasses import dataclass

from localstock.config import get_settings


@dataclass
class ScoringConfig:
    """Scoring weights and thresholds."""

    weight_technical: float
    weight_fundamental: float
    weight_sentiment: float
    weight_macro: float

    @classmethod
    def from_settings(cls) -> "ScoringConfig":
        """Create ScoringConfig from application Settings."""
        settings = get_settings()
        return cls(
            weight_technical=settings.scoring_weight_technical,
            weight_fundamental=settings.scoring_weight_fundamental,
            weight_sentiment=settings.scoring_weight_sentiment,
            weight_macro=settings.scoring_weight_macro,
        )
