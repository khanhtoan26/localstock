"""Tests for Vietnamese trading calendar — is_trading_day and get_next_trading_day."""

from datetime import date

import pytest

from localstock.scheduler.calendar import get_next_trading_day, is_trading_day


class TestIsTradingDay:
    """Test is_trading_day with weekdays, weekends, and VN holidays."""

    def test_monday_is_trading_day(self):
        assert is_trading_day(date(2026, 4, 13)) is True  # Monday

    def test_friday_is_trading_day(self):
        assert is_trading_day(date(2026, 4, 17)) is True  # Friday

    def test_saturday_is_not_trading_day(self):
        assert is_trading_day(date(2026, 4, 18)) is False  # Saturday

    def test_sunday_is_not_trading_day(self):
        assert is_trading_day(date(2026, 4, 19)) is False  # Sunday

    def test_reunification_day_not_trading(self):
        # April 30 is VN Reunification Day
        assert is_trading_day(date(2026, 4, 30)) is False

    def test_national_day_not_trading(self):
        # September 2 is VN National Day
        assert is_trading_day(date(2026, 9, 2)) is False

    def test_new_year_not_trading(self):
        # January 1 is international New Year
        assert is_trading_day(date(2026, 1, 1)) is False

    def test_regular_wednesday_is_trading(self):
        # A random Wednesday with no holiday
        assert is_trading_day(date(2026, 3, 4)) is True


class TestGetNextTradingDay:
    """Test get_next_trading_day skipping weekends and holidays."""

    def test_friday_to_monday(self):
        # Friday Apr 17 → next trading day is Monday Apr 20
        result = get_next_trading_day(date(2026, 4, 17))
        assert result == date(2026, 4, 20)

    def test_skips_holiday(self):
        # Apr 29 (Wed) → Apr 30 is Reunification Day, May 1 is Labour Day
        # Next trading day should skip both
        result = get_next_trading_day(date(2026, 4, 29))
        assert result.weekday() < 5  # Must be weekday
        assert is_trading_day(result) is True
