"""Tests for ReportService — orchestrates report generation pipeline.

Tests use mocked dependencies (repositories, OllamaClient, SentimentService).
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.services.report_service import ReportService


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_score():
    """Create a mock CompositeScore object."""
    score = MagicMock()
    score.symbol = "VNM"
    score.date = date(2026, 4, 16)
    score.total_score = 85.0
    score.grade = "A"
    score.rank = 1
    score.technical_score = 80.0
    score.fundamental_score = 90.0
    score.sentiment_score = 75.0
    score.macro_score = 65.0
    score.dimensions_used = 4
    score.weights_json = {"tech": 0.3, "fund": 0.3, "sent": 0.2, "macro": 0.2}
    return score


@pytest.fixture
def mock_score_2():
    """Create a second mock CompositeScore object."""
    score = MagicMock()
    score.symbol = "FPT"
    score.date = date(2026, 4, 16)
    score.total_score = 78.0
    score.grade = "B"
    score.rank = 2
    score.technical_score = 75.0
    score.fundamental_score = 82.0
    score.sentiment_score = 70.0
    score.macro_score = 60.0
    score.dimensions_used = 4
    score.weights_json = {"tech": 0.3, "fund": 0.3, "sent": 0.2, "macro": 0.2}
    return score


@pytest.fixture
def mock_indicator():
    """Create a mock TechnicalIndicator object."""
    ind = MagicMock()
    ind.rsi_14 = 45.0
    ind.macd_histogram = 0.5
    ind.trend_direction = "uptrend"
    ind.trend_strength = 30.0
    ind.nearest_support = 90000.0
    ind.nearest_resistance = 105000.0
    ind.relative_volume = 1.2
    ind.volume_trend = "increasing"
    ind.sma_20 = 95000.0
    ind.sma_50 = 93000.0
    ind.sma_200 = 90000.0
    ind.ema_12 = 96000.0
    ind.ema_26 = 94000.0
    ind.macd = 2000.0
    ind.macd_signal = 1500.0
    ind.bb_upper = 100000.0
    ind.bb_middle = 95000.0
    ind.bb_lower = 90000.0
    ind.stoch_k = 55.0
    ind.stoch_d = 50.0
    ind.adx = 30.0
    ind.obv = 1000000
    ind.avg_volume_20 = 500000
    ind.pivot_point = 95000.0
    ind.support_1 = 92000.0
    ind.support_2 = 89000.0
    ind.resistance_1 = 98000.0
    ind.resistance_2 = 101000.0
    # Fake __table__.columns for dict conversion
    col_names = [
        "id", "symbol", "date", "rsi_14", "macd_histogram",
        "trend_direction", "trend_strength", "nearest_support",
        "nearest_resistance", "relative_volume", "volume_trend",
        "sma_20", "computed_at",
    ]
    cols = []
    for name in col_names:
        col = MagicMock()
        col.name = name
        cols.append(col)
    ind.__table__ = MagicMock()
    ind.__table__.columns = cols
    return ind


@pytest.fixture
def mock_ratio():
    """Create a mock FinancialRatio object."""
    ratio = MagicMock()
    ratio.pe_ratio = 15.0
    ratio.pb_ratio = 2.5
    ratio.roe = 0.2
    ratio.debt_to_equity = 0.5
    ratio.revenue_growth = 0.15
    ratio.eps = 5000.0
    col_names = [
        "id", "symbol", "year", "period", "pe_ratio", "pb_ratio",
        "roe", "debt_to_equity", "revenue_growth", "eps", "computed_at",
    ]
    cols = []
    for name in col_names:
        col = MagicMock()
        col.name = name
        cols.append(col)
    ratio.__table__ = MagicMock()
    ratio.__table__.columns = cols
    return ratio


@pytest.fixture
def mock_stock():
    """Create a mock Stock object."""
    stock = MagicMock()
    stock.symbol = "VNM"
    stock.name = "Vinamilk"
    stock.exchange = "HOSE"
    stock.industry_icb3 = "Thực phẩm & Đồ uống"
    return stock


@pytest.fixture
def mock_stock_report():
    """Create a mock StockReport response from LLM."""
    from localstock.ai.client import StockReport

    return StockReport(
        summary="VNM đang trong xu hướng tăng tích cực.",
        technical_analysis="RSI ở mức 45, vùng phục hồi.",
        fundamental_analysis="P/E 15, hợp lý cho ngành.",
        sentiment_analysis="Tâm lý thị trường tích cực.",
        macro_impact="Bối cảnh vĩ mô thuận lợi cho ngành F&B.",
        long_term_suggestion="Nên nắm giữ dài hạn.",
        swing_trade_suggestion="Có thể mua lướt sóng, chú ý T+3.",
        recommendation="Mua",
        confidence="Cao",
    )


@pytest.fixture
def mock_macro_indicator():
    """Create a mock MacroIndicator object."""
    ind = MagicMock()
    ind.indicator_type = "interest_rate"
    ind.value = 4.5
    ind.period = "2026-Q1"
    ind.source = "SBV"
    ind.trend = "stable"
    ind.recorded_at = date(2026, 4, 1)
    ind.fetched_at = datetime(2026, 4, 1, tzinfo=UTC)
    return ind


class TestReportServiceInit:
    """Test ReportService constructor."""

    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    def test_init_creates_required_instances(self, mock_sent_cls, mock_ollama_cls, mock_session):
        """ReportService.__init__ creates all required repository + client instances."""
        service = ReportService(mock_session)
        assert service.session is mock_session
        assert service.score_repo is not None
        assert service.report_repo is not None
        assert service.macro_repo is not None
        assert service.indicator_repo is not None
        assert service.ratio_repo is not None
        assert service.industry_repo is not None
        assert service.stock_repo is not None
        assert service.sentiment_service is not None
        assert service.ollama is not None


class TestReportServiceRunFull:
    """Test ReportService.run_full() pipeline."""

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    @patch("localstock.services.report_service.predict_3day_trend")
    @patch("localstock.services.report_service.ReportDataBuilder")
    @patch("localstock.services.report_service.build_report_prompt")
    @patch("localstock.services.report_service.MacroCrawler")
    async def test_run_full_happy_path(
        self,
        mock_crawler_cls,
        mock_build_prompt,
        mock_builder_cls,
        mock_predict,
        mock_sent_cls,
        mock_ollama_cls,
        mock_session,
        mock_score,
        mock_score_2,
        mock_indicator,
        mock_ratio,
        mock_stock,
        mock_stock_report,
        mock_macro_indicator,
    ):
        """run_full() fetches top-ranked stocks and generates reports for each."""
        # Setup mocks
        service = ReportService(mock_session)

        service.score_repo.get_top_ranked = AsyncMock(
            return_value=[mock_score, mock_score_2]
        )
        service.macro_repo.get_all_latest = AsyncMock(
            return_value=[mock_macro_indicator]
        )
        mock_crawler_inst = AsyncMock()
        mock_crawler_inst.determine_macro_conditions = AsyncMock(
            return_value={"interest_rate": "stable"}
        )
        mock_crawler_cls.return_value = mock_crawler_inst

        service.indicator_repo.get_latest = AsyncMock(return_value=mock_indicator)
        service.ratio_repo.get_latest = AsyncMock(return_value=mock_ratio)
        service.sentiment_service.get_aggregated_sentiment = AsyncMock(return_value=0.7)
        service.stock_repo.get_all_hose_symbols = AsyncMock(return_value=["VNM", "FPT"])
        service.industry_repo.get_group_for_symbol = AsyncMock(return_value="FOOD_BEV")

        # Mock stock info — use a mock with symbol and name
        mock_stock_vnm = MagicMock()
        mock_stock_vnm.symbol = "VNM"
        mock_stock_vnm.name = "Vinamilk"
        mock_stock_vnm.industry_icb3 = "Thực phẩm"
        service.stock_repo.get_by_symbol = AsyncMock(return_value=mock_stock_vnm)

        # Mock price repo for close price
        mock_price = MagicMock()
        mock_price.close = 97000.0
        service.price_repo.get_latest = AsyncMock(return_value=mock_price)

        # Mock T+3 prediction
        mock_predict.return_value = {
            "direction": "bullish",
            "confidence": "medium",
            "reasons": ["RSI phục hồi"],
            "t3_warning": "Cảnh báo T+3",
        }

        # Mock ReportDataBuilder
        mock_builder_inst = MagicMock()
        mock_builder_inst.build.return_value = {"symbol": "VNM"}
        mock_builder_cls.return_value = mock_builder_inst

        # Mock prompt building
        mock_build_prompt.return_value = "prompt text"

        # Mock Ollama
        service.ollama.health_check = AsyncMock(return_value=True)
        service.ollama.generate_report = AsyncMock(return_value=mock_stock_report)
        service.ollama.model = "qwen2.5:14b"

        # Mock report upsert
        service.report_repo.upsert = AsyncMock()

        result = await service.run_full(top_n=5)

        assert result["reports_generated"] == 2
        assert result["reports_failed"] == 0
        assert service.report_repo.upsert.call_count == 2

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    async def test_run_full_ollama_down(self, mock_sent_cls, mock_ollama_cls, mock_session):
        """run_full() returns early when Ollama health check fails."""
        service = ReportService(mock_session)
        service.ollama.health_check = AsyncMock(return_value=False)

        result = await service.run_full()

        assert result["reports_generated"] == 0
        assert "Ollama not available" in result["errors"]

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    @patch("localstock.services.report_service.predict_3day_trend")
    @patch("localstock.services.report_service.ReportDataBuilder")
    @patch("localstock.services.report_service.build_report_prompt")
    @patch("localstock.services.report_service.MacroCrawler")
    async def test_run_full_per_stock_error_isolation(
        self,
        mock_crawler_cls,
        mock_build_prompt,
        mock_builder_cls,
        mock_predict,
        mock_sent_cls,
        mock_ollama_cls,
        mock_session,
        mock_score,
        mock_score_2,
        mock_indicator,
        mock_ratio,
        mock_stock,
        mock_stock_report,
        mock_macro_indicator,
    ):
        """run_full() isolates errors per stock — one failure doesn't stop others."""
        service = ReportService(mock_session)

        service.score_repo.get_top_ranked = AsyncMock(
            return_value=[mock_score, mock_score_2]
        )
        service.macro_repo.get_all_latest = AsyncMock(
            return_value=[mock_macro_indicator]
        )
        mock_crawler_inst = AsyncMock()
        mock_crawler_inst.determine_macro_conditions = AsyncMock(
            return_value={"interest_rate": "stable"}
        )
        mock_crawler_cls.return_value = mock_crawler_inst

        service.indicator_repo.get_latest = AsyncMock(return_value=mock_indicator)
        service.ratio_repo.get_latest = AsyncMock(return_value=mock_ratio)
        service.sentiment_service.get_aggregated_sentiment = AsyncMock(return_value=0.7)
        service.industry_repo.get_group_for_symbol = AsyncMock(return_value="FOOD_BEV")
        service.stock_repo.get_by_symbol = AsyncMock(return_value=mock_stock)

        mock_price = MagicMock()
        mock_price.close = 97000.0
        service.price_repo.get_latest = AsyncMock(return_value=mock_price)

        mock_predict.return_value = {
            "direction": "bullish",
            "confidence": "medium",
            "reasons": ["RSI phục hồi"],
            "t3_warning": "Cảnh báo T+3",
        }
        mock_builder_inst = MagicMock()
        mock_builder_inst.build.return_value = {"symbol": "VNM"}
        mock_builder_cls.return_value = mock_builder_inst
        mock_build_prompt.return_value = "prompt text"

        # First call fails, second succeeds
        service.ollama.health_check = AsyncMock(return_value=True)
        service.ollama.generate_report = AsyncMock(
            side_effect=[Exception("LLM error"), mock_stock_report]
        )
        service.ollama.model = "qwen2.5:14b"
        service.report_repo.upsert = AsyncMock()

        result = await service.run_full(top_n=5)

        assert result["reports_generated"] == 1
        assert result["reports_failed"] == 1
        assert len(result["errors"]) == 1


class TestReportServiceGetReports:
    """Test ReportService.get_reports() and get_report()."""

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    async def test_get_reports(self, mock_sent_cls, mock_ollama_cls, mock_session):
        """get_reports() returns list of report dicts."""
        service = ReportService(mock_session)

        mock_report = MagicMock()
        mock_report.symbol = "VNM"
        mock_report.date = date(2026, 4, 16)
        mock_report.summary = "VNM tốt."
        mock_report.recommendation = "buy"
        mock_report.t3_prediction = "bullish"
        mock_report.total_score = 85.0
        mock_report.grade = "A"
        mock_report.generated_at = datetime(2026, 4, 16, 10, 0, tzinfo=UTC)

        service.report_repo.get_by_date = AsyncMock(return_value=[mock_report])

        result = await service.get_reports(limit=20)

        assert len(result) == 1
        assert result[0]["symbol"] == "VNM"
        assert result[0]["recommendation"] == "buy"

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    async def test_get_report(self, mock_sent_cls, mock_ollama_cls, mock_session):
        """get_report() returns single report dict or None."""
        service = ReportService(mock_session)

        mock_report = MagicMock()
        mock_report.symbol = "VNM"
        mock_report.date = date(2026, 4, 16)
        mock_report.content_json = {"summary": "Good stock"}
        mock_report.summary = "Good stock"
        mock_report.recommendation = "buy"
        mock_report.t3_prediction = "bullish"
        mock_report.total_score = 85.0
        mock_report.grade = "A"
        mock_report.model_used = "qwen2.5:14b"
        mock_report.generated_at = datetime(2026, 4, 16, 10, 0, tzinfo=UTC)

        service.report_repo.get_latest = AsyncMock(return_value=mock_report)

        result = await service.get_report("VNM")

        assert result is not None
        assert result["symbol"] == "VNM"
        assert result["content_json"] == {"summary": "Good stock"}

    @pytest.mark.asyncio
    @patch("localstock.services.report_service.OllamaClient")
    @patch("localstock.services.report_service.SentimentService")
    async def test_get_report_not_found(self, mock_sent_cls, mock_ollama_cls, mock_session):
        """get_report() returns None when no report exists."""
        service = ReportService(mock_session)
        service.report_repo.get_latest = AsyncMock(return_value=None)

        result = await service.get_report("XYZ")

        assert result is None
