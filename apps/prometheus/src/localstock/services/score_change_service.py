"""Score change detection — compares consecutive scoring dates to find significant moves (SCOR-04).

Per D-03: threshold defaults to 15.0 points. Direction is 'up' for positive delta, 'down' for negative.
Per Pitfall 5: requires at least 2 consecutive scoring dates before generating alerts.
"""

from datetime import date

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.config import get_settings
from localstock.db.models import CompositeScore
from localstock.db.repositories.score_repo import ScoreRepository


async def detect_score_changes(
    session: AsyncSession,
    target_date: date | None = None,
    threshold: float | None = None,
) -> list[dict]:
    """Detect stocks with significant score changes vs previous scoring date.

    Compares today's CompositeScore records against the most recent previous date.
    Returns list of change dicts for stocks where abs(delta) > threshold.

    Args:
        session: Database session.
        target_date: Date to check. Defaults to most recent scoring date.
        threshold: Minimum absolute delta to consider significant.
                   Defaults to Settings.score_change_threshold (15.0).

    Returns:
        List of dicts: [{symbol, previous_score, current_score, delta,
                        previous_grade, current_grade, direction, date}, ...]
    """
    settings = get_settings()
    if threshold is None:
        threshold = settings.score_change_threshold

    repo = ScoreRepository(session)

    # Get target date (most recent scoring date)
    if target_date is None:
        target_date = await repo.get_latest_date()
        if target_date is None:
            logger.info("No scoring data found — skipping change detection")
            return []

    # Get current scores
    current_scores = await repo.get_by_date(target_date)
    if not current_scores:
        return []

    # Get previous date's scores
    prev_date, prev_scores = await repo.get_previous_date_scores(target_date)
    if prev_date is None:
        logger.info("No previous scoring date — skipping change detection (Pitfall 5)")
        return []

    # Build lookup: symbol -> previous CompositeScore
    prev_map: dict[str, CompositeScore] = {s.symbol: s for s in prev_scores}

    changes = []
    for current in current_scores:
        prev = prev_map.get(current.symbol)
        if prev is None:
            continue  # New stock, no comparison possible

        delta = current.total_score - prev.total_score
        if abs(delta) >= threshold:
            changes.append({
                "symbol": current.symbol,
                "date": target_date,
                "previous_score": round(prev.total_score, 1),
                "current_score": round(current.total_score, 1),
                "delta": round(delta, 1),
                "previous_grade": prev.grade,
                "current_grade": current.grade,
                "direction": "up" if delta > 0 else "down",
            })

    # Sort by absolute delta descending
    changes.sort(key=lambda c: abs(c["delta"]), reverse=True)
    logger.info("score_change.detected", count=len(changes), threshold=threshold)
    return changes
