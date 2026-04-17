"""Vietnamese stock market trading calendar.

HOSE trading hours: 9:00-15:00, Monday-Friday.
Skips weekends and Vietnamese public holidays using the `holidays` package.
Per D-02: scheduler must recognize VN holidays to avoid running on non-trading days.
"""

from datetime import date, timedelta

import holidays


def is_trading_day(check_date: date | None = None) -> bool:
    """Check if the given date is a HOSE trading day.

    A trading day is a weekday (Mon-Fri) that is NOT a Vietnamese public holiday.
    Uses the `holidays` package which handles lunar calendar dates (Tết shifts yearly).

    Args:
        check_date: Date to check. Defaults to today.

    Returns:
        True if the date is a trading day.
    """
    d = check_date or date.today()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    vn_holidays = holidays.Vietnam(years=d.year)
    return d not in vn_holidays


def get_next_trading_day(from_date: date | None = None) -> date:
    """Get the next trading day after the given date.

    Args:
        from_date: Starting date. Defaults to today.

    Returns:
        The next trading day (skipping weekends and VN holidays).
    """
    d = (from_date or date.today()) + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d
