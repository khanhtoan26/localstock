"""Tests for Telegram message formatters."""

from datetime import date

import pytest

from localstock.notifications.formatters import (
    format_daily_digest,
    format_score_alerts,
    format_sector_rotation,
)


class TestFormatDailyDigest:

    def test_includes_header_with_date(self):
        msg = format_daily_digest([], digest_date=date(2026, 4, 16))
        assert "16/04/2026" in msg
        assert "Daily Digest" in msg

    def test_includes_top_stocks(self):
        stocks = [
            {"symbol": "VNM", "total_score": 87.3, "grade": "A", "rank": 1},
            {"symbol": "FPT", "total_score": 84.1, "grade": "A", "rank": 2},
        ]
        msg = format_daily_digest(stocks, digest_date=date(2026, 4, 16))
        assert "VNM" in msg
        assert "FPT" in msg
        assert "87.3" in msg
        assert "🏆" in msg

    def test_handles_empty_top_stocks(self):
        msg = format_daily_digest([], digest_date=date(2026, 4, 16))
        assert "Chưa có dữ liệu" in msg

    def test_includes_score_changes(self):
        changes = [{"symbol": "HPG", "previous_score": 45.2,
                    "current_score": 68.7, "delta": 23.5, "direction": "up"}]
        msg = format_daily_digest([], score_changes=changes, digest_date=date(2026, 4, 16))
        assert "HPG" in msg
        assert "23.5" in msg
        assert "📈" in msg

    def test_includes_sector_rotation(self):
        rotation = {
            "inflow": [{"group_name": "Ngân hàng", "avg_score_change": 5.0}],
            "outflow": [{"group_name": "BĐS", "avg_score_change": -4.0}],
        }
        msg = format_daily_digest([], rotation=rotation, digest_date=date(2026, 4, 16))
        assert "Ngân hàng" in msg
        assert "BĐS" in msg


class TestFormatScoreAlerts:

    def test_includes_alert_header(self):
        changes = [{"symbol": "HPG", "previous_score": 45.2, "current_score": 68.7,
                    "delta": 23.5, "direction": "up", "previous_grade": "C",
                    "current_grade": "B"}]
        msg = format_score_alerts(changes, alert_date=date(2026, 4, 16))
        assert "Score Alert" in msg
        assert "HPG" in msg

    def test_shows_grade_transition(self):
        changes = [{"symbol": "HPG", "previous_score": 45.2, "current_score": 68.7,
                    "delta": 23.5, "direction": "up", "previous_grade": "C",
                    "current_grade": "B"}]
        msg = format_score_alerts(changes)
        assert "C→B" in msg


class TestFormatSectorRotation:

    def test_shows_inflow_outflow(self):
        rotation = {
            "date": "2026-04-16",
            "inflow": [{"group_name": "Ngân hàng", "avg_score": 75.0,
                        "avg_score_change": 5.0, "stock_count": 10}],
            "outflow": [{"group_name": "BĐS", "avg_score": 45.0,
                         "avg_score_change": -4.0, "stock_count": 8}],
            "stable": [],
        }
        msg = format_sector_rotation(rotation)
        assert "Dòng tiền vào" in msg
        assert "Ngân hàng" in msg
        assert "Dòng tiền ra" in msg
        assert "BĐS" in msg

    def test_handles_no_rotation(self):
        rotation = {"date": "2026-04-16", "inflow": [], "outflow": [], "stable": []}
        msg = format_sector_rotation(rotation)
        assert "Không phát hiện" in msg
