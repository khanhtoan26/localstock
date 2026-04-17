"""Tests for score change detection service (SCOR-04)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.services.score_change_service import detect_score_changes


def _make_score(symbol, total_score, grade, score_date):
    """Create a mock CompositeScore."""
    score = MagicMock()
    score.symbol = symbol
    score.total_score = total_score
    score.grade = grade
    score.date = score_date
    return score


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestDetectScoreChanges:

    @patch("localstock.services.score_change_service.ScoreRepository")
    @patch("localstock.services.score_change_service.get_settings")
    async def test_detects_large_increase(self, mock_settings, MockRepo, mock_session):
        settings = MagicMock()
        settings.score_change_threshold = 15.0
        mock_settings.return_value = settings

        today = date(2026, 4, 16)
        repo = MockRepo.return_value
        repo.get_latest_date = AsyncMock(return_value=today)
        repo.get_by_date = AsyncMock(return_value=[
            _make_score("HPG", 68.7, "B", today),
            _make_score("VNM", 85.0, "A", today),
        ])
        repo.get_previous_date_scores = AsyncMock(return_value=(
            date(2026, 4, 15),
            [_make_score("HPG", 45.2, "C", date(2026, 4, 15)),
             _make_score("VNM", 82.0, "A", date(2026, 4, 15))],
        ))

        changes = await detect_score_changes(mock_session, target_date=today)
        assert len(changes) == 1
        assert changes[0]["symbol"] == "HPG"
        assert changes[0]["delta"] == 23.5
        assert changes[0]["direction"] == "up"

    @patch("localstock.services.score_change_service.ScoreRepository")
    @patch("localstock.services.score_change_service.get_settings")
    async def test_detects_large_decrease(self, mock_settings, MockRepo, mock_session):
        settings = MagicMock()
        settings.score_change_threshold = 15.0
        mock_settings.return_value = settings

        today = date(2026, 4, 16)
        repo = MockRepo.return_value
        repo.get_latest_date = AsyncMock(return_value=today)
        repo.get_by_date = AsyncMock(return_value=[
            _make_score("MWG", 54.3, "C", today),
        ])
        repo.get_previous_date_scores = AsyncMock(return_value=(
            date(2026, 4, 15),
            [_make_score("MWG", 72.1, "B", date(2026, 4, 15))],
        ))

        changes = await detect_score_changes(mock_session, target_date=today)
        assert len(changes) == 1
        assert changes[0]["direction"] == "down"
        assert changes[0]["delta"] == -17.8

    @patch("localstock.services.score_change_service.ScoreRepository")
    @patch("localstock.services.score_change_service.get_settings")
    async def test_returns_empty_when_no_previous_scores(self, mock_settings, MockRepo, mock_session):
        settings = MagicMock()
        settings.score_change_threshold = 15.0
        mock_settings.return_value = settings

        today = date(2026, 4, 16)
        repo = MockRepo.return_value
        repo.get_latest_date = AsyncMock(return_value=today)
        repo.get_by_date = AsyncMock(return_value=[_make_score("HPG", 68.7, "B", today)])
        repo.get_previous_date_scores = AsyncMock(return_value=(None, []))

        changes = await detect_score_changes(mock_session, target_date=today)
        assert changes == []

    @patch("localstock.services.score_change_service.ScoreRepository")
    @patch("localstock.services.score_change_service.get_settings")
    async def test_filters_below_threshold(self, mock_settings, MockRepo, mock_session):
        settings = MagicMock()
        settings.score_change_threshold = 15.0
        mock_settings.return_value = settings

        today = date(2026, 4, 16)
        repo = MockRepo.return_value
        repo.get_latest_date = AsyncMock(return_value=today)
        repo.get_by_date = AsyncMock(return_value=[
            _make_score("FPT", 80.0, "A", today),
        ])
        repo.get_previous_date_scores = AsyncMock(return_value=(
            date(2026, 4, 15),
            [_make_score("FPT", 75.0, "B", date(2026, 4, 15))],
        ))

        changes = await detect_score_changes(mock_session, target_date=today)
        assert changes == []  # 5-point change is below threshold
