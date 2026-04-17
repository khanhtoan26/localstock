"""Tests for Phase 5 Task 1: config settings, DB models."""

from localstock.config import Settings
from localstock.db.models import NotificationLog, ScoreChangeAlert, SectorSnapshot


class TestPhase5Config:
    """Test new Phase 5 config settings in Settings class."""

    def test_telegram_bot_token_default_empty(self):
        s = Settings(database_url="sqlite:///:memory:")
        assert s.telegram_bot_token == ""

    def test_telegram_chat_id_default_empty(self):
        s = Settings(database_url="sqlite:///:memory:")
        assert s.telegram_chat_id == ""

    def test_score_change_threshold_default(self):
        s = Settings(database_url="sqlite:///:memory:")
        assert s.score_change_threshold == 15.0

    def test_scheduler_run_hour_default(self):
        s = Settings(database_url="sqlite:///:memory:")
        assert s.scheduler_run_hour == 15

    def test_scheduler_run_minute_default(self):
        s = Settings(database_url="sqlite:///:memory:")
        assert s.scheduler_run_minute == 45


class TestPhase5Models:
    """Test new Phase 5 ORM models exist with correct tablenames."""

    def test_score_change_alert_tablename(self):
        assert ScoreChangeAlert.__tablename__ == "score_change_alerts"

    def test_sector_snapshot_tablename(self):
        assert SectorSnapshot.__tablename__ == "sector_snapshots"

    def test_notification_log_tablename(self):
        assert NotificationLog.__tablename__ == "notification_logs"
