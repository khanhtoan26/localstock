"""Tests for AutomationService — full pipeline orchestrator with notifications."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.services.automation_service import AutomationService


@pytest.fixture
def mock_session_factory():
    """Mock session factory that returns AsyncMock sessions."""
    session = AsyncMock()
    factory = MagicMock()
    # Make factory() return an async context manager
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory, session


def _make_service_with_mocks(mock_factory):
    """Create AutomationService with mocked session factory and notifier."""
    factory, session = mock_factory
    with patch("localstock.services.automation_service.get_session_factory", return_value=factory):
        service = AutomationService()
    service.notifier = MagicMock()
    service.notifier.is_configured = False
    return service, session


class TestRunDailyPipeline:

    @patch("localstock.services.automation_service.is_trading_day", return_value=False)
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_skips_non_trading_day(self, mock_factory_fn, mock_trading):
        """Test 7: Pipeline skips on non-trading days with status='skipped'."""
        mock_factory_fn.return_value = MagicMock()
        service = AutomationService()
        result = await service.run_daily_pipeline()
        assert result["status"] == "skipped"
        assert result["reason"] == "non_trading_day"

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.SectorService")
    @patch("localstock.services.automation_service.detect_score_changes")
    @patch("localstock.services.automation_service.ReportService")
    @patch("localstock.services.automation_service.ScoringService")
    @patch("localstock.services.automation_service.SentimentService")
    @patch("localstock.services.automation_service.NewsService")
    @patch("localstock.services.automation_service.AnalysisService")
    @patch("localstock.services.automation_service.Pipeline")
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_runs_all_steps(
        self, mock_factory_fn, MockPipeline, MockAnalysis, MockNews,
        MockSentiment, MockScoring, MockReports, mock_changes,
        MockSector, mock_trading,
    ):
        """Test 1: Pipeline executes all 6 steps in order."""
        # Setup mock session factory
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        # Setup pipeline mock
        crawl_result = MagicMock()
        crawl_result.symbols_success = 400
        crawl_result.symbols_total = 400
        MockPipeline.return_value.run_full = AsyncMock(return_value=crawl_result)

        # Other services return dicts
        MockAnalysis.return_value.run_full = AsyncMock(return_value={"analyzed": 400})
        MockNews.return_value.crawl_all = AsyncMock(return_value={"articles_saved": 10})
        MockSentiment.return_value.run_full = AsyncMock(return_value={"analyzed": 50})
        MockScoring.return_value.run_full = AsyncMock(return_value={"stocks_scored": 400})
        MockScoring.return_value.get_top_stocks = AsyncMock(return_value=[])
        MockReports.return_value.run_full = AsyncMock(return_value={"reports_generated": 10})
        mock_changes.return_value = []
        MockSector.return_value.compute_snapshot = AsyncMock(return_value=[])
        MockSector.return_value.get_rotation_summary = AsyncMock(return_value={"inflow": [], "outflow": [], "stable": []})

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        result = await service.run_daily_pipeline(force=True)
        assert result["status"] == "completed"
        assert "crawl" in result["steps"]
        assert "analysis" in result["steps"]
        assert "news" in result["steps"]
        assert "sentiment" in result["steps"]
        assert "scoring" in result["steps"]
        assert "reports" in result["steps"]

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.SectorService")
    @patch("localstock.services.automation_service.detect_score_changes")
    @patch("localstock.services.automation_service.ReportService")
    @patch("localstock.services.automation_service.ScoringService")
    @patch("localstock.services.automation_service.SentimentService")
    @patch("localstock.services.automation_service.NewsService")
    @patch("localstock.services.automation_service.AnalysisService")
    @patch("localstock.services.automation_service.Pipeline")
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_calls_detect_score_changes(
        self, mock_factory_fn, MockPipeline, MockAnalysis, MockNews,
        MockSentiment, MockScoring, MockReports, mock_changes,
        MockSector, mock_trading,
    ):
        """Test 2: Pipeline calls detect_score_changes after scoring."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        crawl_result = MagicMock()
        crawl_result.symbols_success = 1
        crawl_result.symbols_total = 1
        MockPipeline.return_value.run_full = AsyncMock(return_value=crawl_result)
        MockAnalysis.return_value.run_full = AsyncMock(return_value={})
        MockNews.return_value.crawl_all = AsyncMock(return_value={})
        MockSentiment.return_value.run_full = AsyncMock(return_value={})
        MockScoring.return_value.run_full = AsyncMock(return_value={})
        MockReports.return_value.run_full = AsyncMock(return_value={})
        mock_changes.return_value = [{"symbol": "VNM", "delta": 20.0}]
        MockSector.return_value.compute_snapshot = AsyncMock(return_value=[])
        MockSector.return_value.get_rotation_summary = AsyncMock(return_value={})

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        result = await service.run_daily_pipeline(force=True)
        mock_changes.assert_called_once()
        assert result["score_changes"] == [{"symbol": "VNM", "delta": 20.0}]

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.SectorService")
    @patch("localstock.services.automation_service.detect_score_changes")
    @patch("localstock.services.automation_service.ReportService")
    @patch("localstock.services.automation_service.ScoringService")
    @patch("localstock.services.automation_service.SentimentService")
    @patch("localstock.services.automation_service.NewsService")
    @patch("localstock.services.automation_service.AnalysisService")
    @patch("localstock.services.automation_service.Pipeline")
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_calls_sector_service(
        self, mock_factory_fn, MockPipeline, MockAnalysis, MockNews,
        MockSentiment, MockScoring, MockReports, mock_changes,
        MockSector, mock_trading,
    ):
        """Test 3: Pipeline calls SectorService.compute_snapshot after scoring."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        crawl_result = MagicMock()
        crawl_result.symbols_success = 1
        crawl_result.symbols_total = 1
        MockPipeline.return_value.run_full = AsyncMock(return_value=crawl_result)
        MockAnalysis.return_value.run_full = AsyncMock(return_value={})
        MockNews.return_value.crawl_all = AsyncMock(return_value={})
        MockSentiment.return_value.run_full = AsyncMock(return_value={})
        MockScoring.return_value.run_full = AsyncMock(return_value={})
        MockReports.return_value.run_full = AsyncMock(return_value={})
        mock_changes.return_value = []
        rotation_data = {"inflow": [{"group_name": "Banks"}], "outflow": [], "stable": []}
        MockSector.return_value.compute_snapshot = AsyncMock(return_value=[])
        MockSector.return_value.get_rotation_summary = AsyncMock(return_value=rotation_data)

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        result = await service.run_daily_pipeline(force=True)
        MockSector.return_value.compute_snapshot.assert_called_once()
        MockSector.return_value.get_rotation_summary.assert_called_once()
        assert result["sector_rotation"] == rotation_data

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_skips_notifications_when_not_configured(self, mock_factory_fn, mock_trading):
        """Test 6: Pipeline skips notifications when Telegram is not configured."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        with patch("localstock.services.automation_service.Pipeline") as MockP, \
             patch("localstock.services.automation_service.AnalysisService") as MockA, \
             patch("localstock.services.automation_service.NewsService") as MockN, \
             patch("localstock.services.automation_service.SentimentService") as MockS, \
             patch("localstock.services.automation_service.ScoringService") as MockSc, \
             patch("localstock.services.automation_service.ReportService") as MockR, \
             patch("localstock.services.automation_service.detect_score_changes") as mock_changes, \
             patch("localstock.services.automation_service.SectorService") as MockSect:

            crawl = MagicMock()
            crawl.symbols_success = 1
            crawl.symbols_total = 1
            MockP.return_value.run_full = AsyncMock(return_value=crawl)
            MockA.return_value.run_full = AsyncMock(return_value={})
            MockN.return_value.crawl_all = AsyncMock(return_value={})
            MockS.return_value.run_full = AsyncMock(return_value={})
            MockSc.return_value.run_full = AsyncMock(return_value={})
            MockR.return_value.run_full = AsyncMock(return_value={})
            mock_changes.return_value = []
            MockSect.return_value.compute_snapshot = AsyncMock(return_value=[])
            MockSect.return_value.get_rotation_summary = AsyncMock(return_value={})

            result = await service.run_daily_pipeline(force=True)
            assert result["notifications"]["digest"] is False
            assert result["notifications"]["alerts"] is False

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_returns_summary_dict(self, mock_factory_fn, mock_trading):
        """Test 9: Pipeline returns summary dict with expected keys."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        with patch("localstock.services.automation_service.Pipeline") as MockP, \
             patch("localstock.services.automation_service.AnalysisService") as MockA, \
             patch("localstock.services.automation_service.NewsService") as MockN, \
             patch("localstock.services.automation_service.SentimentService") as MockS, \
             patch("localstock.services.automation_service.ScoringService") as MockSc, \
             patch("localstock.services.automation_service.ReportService") as MockR, \
             patch("localstock.services.automation_service.detect_score_changes") as mock_changes, \
             patch("localstock.services.automation_service.SectorService") as MockSect:

            crawl = MagicMock()
            crawl.symbols_success = 5
            crawl.symbols_total = 5
            MockP.return_value.run_full = AsyncMock(return_value=crawl)
            MockA.return_value.run_full = AsyncMock(return_value={})
            MockN.return_value.crawl_all = AsyncMock(return_value={})
            MockS.return_value.run_full = AsyncMock(return_value={})
            MockSc.return_value.run_full = AsyncMock(return_value={})
            MockR.return_value.run_full = AsyncMock(return_value={})
            mock_changes.return_value = [{"symbol": "HPG", "delta": 18.0}]
            MockSect.return_value.compute_snapshot = AsyncMock(return_value=[])
            MockSect.return_value.get_rotation_summary = AsyncMock(
                return_value={"inflow": [], "outflow": [], "stable": []}
            )

            result = await service.run_daily_pipeline(force=True)
            assert "steps" in result
            assert "score_changes" in result
            assert "sector_rotation" in result
            assert "notifications" in result
            assert "started_at" in result
            assert "completed_at" in result

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_handles_step_failure_gracefully(self, mock_factory_fn, mock_trading):
        """Test 10: Pipeline continues even when individual steps fail."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        with patch("localstock.services.automation_service.Pipeline") as MockP, \
             patch("localstock.services.automation_service.AnalysisService") as MockA, \
             patch("localstock.services.automation_service.NewsService") as MockN, \
             patch("localstock.services.automation_service.SentimentService") as MockS, \
             patch("localstock.services.automation_service.ScoringService") as MockSc, \
             patch("localstock.services.automation_service.ReportService") as MockR, \
             patch("localstock.services.automation_service.detect_score_changes") as mock_changes, \
             patch("localstock.services.automation_service.SectorService") as MockSect:

            # Make crawl fail
            MockP.return_value.run_full = AsyncMock(side_effect=RuntimeError("DB down"))
            # Other steps succeed
            MockA.return_value.run_full = AsyncMock(return_value={"analyzed": 10})
            MockN.return_value.crawl_all = AsyncMock(return_value={})
            MockS.return_value.run_full = AsyncMock(return_value={})
            MockSc.return_value.run_full = AsyncMock(return_value={})
            MockR.return_value.run_full = AsyncMock(return_value={})
            mock_changes.return_value = []
            MockSect.return_value.compute_snapshot = AsyncMock(return_value=[])
            MockSect.return_value.get_rotation_summary = AsyncMock(return_value={})

            result = await service.run_daily_pipeline(force=True)
            # Should still complete, not crash
            assert result["status"] == "completed"
            assert "error" in result["steps"]["crawl"]
            # Analysis should still have run
            assert "analysis" in result["steps"]


class TestRunOnDemand:

    @patch("localstock.services.automation_service.ScoringService")
    @patch("localstock.services.automation_service.AnalysisService")
    @patch("localstock.services.automation_service.Pipeline")
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_single_symbol_analysis(
        self, mock_factory_fn, MockPipeline, MockAnalysis, MockScoring
    ):
        """Test: On-demand single symbol runs crawl→analyze→score."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        MockPipeline.return_value.run_single = AsyncMock(return_value={"symbol": "VNM", "status": "completed"})
        MockAnalysis.return_value.run_full = AsyncMock(return_value={})
        MockScoring.return_value.run_full = AsyncMock(return_value={})

        service = AutomationService()
        result = await service.run_on_demand(symbol="VNM")
        assert result["symbol"] == "VNM"
        assert result["status"] == "completed"

    @patch("localstock.services.automation_service.is_trading_day", return_value=True)
    @patch("localstock.services.automation_service.SectorService")
    @patch("localstock.services.automation_service.detect_score_changes")
    @patch("localstock.services.automation_service.ReportService")
    @patch("localstock.services.automation_service.ScoringService")
    @patch("localstock.services.automation_service.SentimentService")
    @patch("localstock.services.automation_service.NewsService")
    @patch("localstock.services.automation_service.AnalysisService")
    @patch("localstock.services.automation_service.Pipeline")
    @patch("localstock.services.automation_service.get_session_factory")
    async def test_on_demand_full_pipeline_forces_run(
        self, mock_factory_fn, MockPipeline, MockAnalysis, MockNews,
        MockSentiment, MockScoring, MockReports, mock_changes,
        MockSector, mock_trading,
    ):
        """Test: On-demand without symbol runs full pipeline with force=True."""
        session = AsyncMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory_fn.return_value = MagicMock(return_value=ctx)

        crawl_result = MagicMock()
        crawl_result.symbols_success = 1
        crawl_result.symbols_total = 1
        MockPipeline.return_value.run_full = AsyncMock(return_value=crawl_result)
        MockAnalysis.return_value.run_full = AsyncMock(return_value={})
        MockNews.return_value.crawl_all = AsyncMock(return_value={})
        MockSentiment.return_value.run_full = AsyncMock(return_value={})
        MockScoring.return_value.run_full = AsyncMock(return_value={})
        MockReports.return_value.run_full = AsyncMock(return_value={})
        mock_changes.return_value = []
        MockSector.return_value.compute_snapshot = AsyncMock(return_value=[])
        MockSector.return_value.get_rotation_summary = AsyncMock(return_value={})

        service = AutomationService()
        service.notifier = MagicMock()
        service.notifier.is_configured = False

        result = await service.run_on_demand()
        assert result["status"] == "completed"
