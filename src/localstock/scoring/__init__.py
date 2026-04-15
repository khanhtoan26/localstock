"""Scoring package — grade mapping and composite scoring."""


def score_to_grade(score: float) -> str:
    """Map numeric score (0-100) to grade letter (D-05).

    A=80-100, B=60-79, C=40-59, D=20-39, F=0-19
    """
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    elif score >= 20:
        return "D"
    else:
        return "F"
