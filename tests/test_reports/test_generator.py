"""Tests for StockReport model, ReportDataBuilder, prompts, and OllamaClient.generate_report().

Tests:
- StockReport has all 9 required fields
- StockReport validates correctly with sample data
- build_report_prompt returns formatted string with expected sections
- build_report_prompt handles None values gracefully
- ReportDataBuilder.build returns dict with all template keys populated
- build_report_prompt output is under 3000 characters
- REPORT_SYSTEM_PROMPT contains Vietnamese instructions, T+3, long-term/swing
- REPORT_USER_TEMPLATE has placeholder markers
- StockReport importable from localstock.ai.client
- OllamaClient.generate_report() calls chat with correct params
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.reports.generator import (
    ReportDataBuilder,
    StockReport,
    build_report_prompt,
)


class TestStockReportModel:
    """Test StockReport Pydantic model structure."""

    REQUIRED_FIELDS = [
        "summary",
        "technical_analysis",
        "fundamental_analysis",
        "sentiment_analysis",
        "macro_impact",
        "long_term_suggestion",
        "swing_trade_suggestion",
        "recommendation",
        "confidence",
    ]

    def test_has_all_required_fields(self):
        schema = StockReport.model_json_schema()
        props = schema.get("properties", {})
        for field in self.REQUIRED_FIELDS:
            assert field in props, f"Missing field: {field}"

    def test_exactly_9_fields(self):
        schema = StockReport.model_json_schema()
        props = schema.get("properties", {})
        assert len(props) == 9

    def test_validates_with_sample_data(self):
        report = StockReport(
            summary="Tóm tắt VNM",
            technical_analysis="RSI đang ở vùng quá bán",
            fundamental_analysis="P/E thấp hơn ngành",
            sentiment_analysis="Tin tức tích cực",
            macro_impact="Lãi suất giảm hỗ trợ",
            long_term_suggestion="Nên mua và giữ dài hạn",
            swing_trade_suggestion="Có thể lướt sóng với T+3",
            recommendation="Mua",
            confidence="Cao",
        )
        assert report.summary == "Tóm tắt VNM"
        assert report.recommendation == "Mua"

    def test_model_json_schema_valid(self):
        """Schema should be valid for Ollama format parameter."""
        schema = StockReport.model_json_schema()
        assert "properties" in schema
        assert schema.get("type") == "object"
        # All fields should have descriptions (for Ollama guidance)
        for field_name, field_info in schema["properties"].items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )


class TestBuildReportPrompt:
    """Test build_report_prompt() formatting."""

    def _make_sample_data(self) -> dict:
        return {
            "symbol": "VNM",
            "company_name": "Vinamilk",
            "industry": "Thực phẩm & Đồ uống",
            "close_price": 75000,
            "total_score": 72.5,
            "grade": "B+",
            "technical_score": 65.0,
            "fundamental_score": 80.0,
            "sentiment_score": 70.0,
            "macro_score": 55.0,
            "rsi_14": 45.0,
            "macd_histogram": 0.3,
            "trend_direction": "uptrend",
            "trend_strength": 25.0,
            "pe_ratio": 15.2,
            "pb_ratio": 3.1,
            "roe": 0.25,
            "debt_to_equity": 0.4,
            "revenue_growth": 0.12,
            "sentiment_summary": "3 tin tích cực, 1 tin tiêu cực",
            "macro_conditions": "Lãi suất ổn định, tỷ giá tăng nhẹ",
            "t3_direction": "bullish",
            "t3_confidence": "medium",
            "t3_reasons": "RSI đang phục hồi, MACD dương",
            "t3_warning": "⚠️ CẢNH BÁO T+3: ...",
        }

    def test_returns_string(self):
        data = self._make_sample_data()
        result = build_report_prompt(data)
        assert isinstance(result, str)

    def test_contains_symbol(self):
        data = self._make_sample_data()
        result = build_report_prompt(data)
        assert "VNM" in result

    def test_contains_section_markers(self):
        """Prompt should have emoji section headers."""
        data = self._make_sample_data()
        result = build_report_prompt(data)
        assert "📊" in result  # Stock info
        assert "📈" in result  # Technical
        assert "💰" in result  # Fundamental
        assert "📰" in result  # Sentiment
        assert "🌐" in result  # Macro
        assert "⏰" in result  # T+3

    def test_under_3000_chars(self):
        """Prompt budget: should be under 3000 characters."""
        data = self._make_sample_data()
        result = build_report_prompt(data)
        assert len(result) < 3000, f"Prompt is {len(result)} chars, exceeds 3000"

    def test_handles_none_values(self):
        """Should not crash with None values."""
        data = self._make_sample_data()
        data["pe_ratio"] = None
        data["sentiment_summary"] = None
        result = build_report_prompt(data)
        assert isinstance(result, str)
        assert "VNM" in result

    def test_includes_t3_data(self):
        data = self._make_sample_data()
        result = build_report_prompt(data)
        assert "bullish" in result or "T+3" in result


class TestReportDataBuilder:
    """Test ReportDataBuilder assembles all data correctly."""

    def test_build_returns_dict(self):
        builder = ReportDataBuilder()
        result = builder.build(
            symbol="VNM",
            score_data={"total": 72.5, "grade": "B+", "technical": 65.0,
                        "fundamental": 80.0, "sentiment": 70.0, "macro": 55.0},
            indicator_data={"rsi_14": 45.0, "macd_histogram": 0.3,
                            "trend_direction": "uptrend", "trend_strength": 25.0},
            ratio_data={"pe_ratio": 15.2, "pb_ratio": 3.1, "roe": 0.25,
                        "debt_to_equity": 0.4, "revenue_growth": 0.12},
            sentiment_data={"summary": "3 tin tích cực"},
            macro_data={"conditions": "Lãi suất ổn định"},
            t3_data={"direction": "bullish", "confidence": "medium",
                     "reasons": ["RSI phục hồi"], "t3_warning": "⚠️ CẢNH BÁO T+3: ..."},
            stock_info={"company_name": "Vinamilk", "industry": "Thực phẩm",
                        "close_price": 75000},
        )
        assert isinstance(result, dict)

    def test_build_has_required_keys(self):
        builder = ReportDataBuilder()
        result = builder.build(
            symbol="VNM",
            score_data={"total": 72.5, "grade": "B+", "technical": 65.0,
                        "fundamental": 80.0, "sentiment": 70.0, "macro": 55.0},
            indicator_data={},
            ratio_data={},
            sentiment_data={},
            macro_data={},
            t3_data={},
            stock_info={},
        )
        # Should have all keys needed by REPORT_USER_TEMPLATE
        assert "symbol" in result
        assert "total_score" in result
        assert "grade" in result
        assert "t3_direction" in result
        assert "t3_warning" in result

    def test_build_handles_none_data(self):
        """None values should get fallback strings."""
        builder = ReportDataBuilder()
        result = builder.build(
            symbol="VNM",
            score_data={},
            indicator_data={},
            ratio_data={},
            sentiment_data={},
            macro_data={},
            t3_data={},
            stock_info={},
        )
        assert result["symbol"] == "VNM"
        # None fields should have fallback values, not None
        for key, val in result.items():
            assert val is not None, f"Key '{key}' is None, should have fallback"


class TestReportSystemPrompt:
    """Test REPORT_SYSTEM_PROMPT content."""

    def test_is_nonempty_string(self):
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert isinstance(REPORT_SYSTEM_PROMPT, str)
        assert len(REPORT_SYSTEM_PROMPT) > 100

    def test_contains_vietnamese_instructions(self):
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert "tiếng Việt" in REPORT_SYSTEM_PROMPT or "Việt Nam" in REPORT_SYSTEM_PROMPT

    def test_mentions_t3(self):
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert "T+3" in REPORT_SYSTEM_PROMPT

    def test_mentions_swing_trade(self):
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert "lướt sóng" in REPORT_SYSTEM_PROMPT

    def test_mentions_long_term(self):
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert "dài hạn" in REPORT_SYSTEM_PROMPT

    def test_mentions_disclaimer(self):
        """Per T-04-07: System prompt includes disclaimer."""
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        assert "không phải tư vấn đầu tư chính thức" in REPORT_SYSTEM_PROMPT


class TestReportUserTemplate:
    """Test REPORT_USER_TEMPLATE structure."""

    def test_is_string_with_placeholders(self):
        from localstock.ai.prompts import REPORT_USER_TEMPLATE

        assert isinstance(REPORT_USER_TEMPLATE, str)
        assert "{symbol}" in REPORT_USER_TEMPLATE
        assert "{total_score}" in REPORT_USER_TEMPLATE


class TestStockReportFromClient:
    """Test StockReport is importable from ai.client."""

    def test_importable(self):
        from localstock.ai.client import StockReport as ClientStockReport

        assert ClientStockReport is not None
        schema = ClientStockReport.model_json_schema()
        assert "properties" in schema


class TestOllamaClientGenerateReport:
    """Test OllamaClient.generate_report() method."""

    def _make_mock_response(self) -> MagicMock:
        """Create a mock Ollama chat response with valid StockReport JSON."""
        report_json = json.dumps(
            {
                "summary": "VNM tổng quan",
                "technical_analysis": "RSI tích cực",
                "fundamental_analysis": "P/E hợp lý",
                "sentiment_analysis": "Tin tức tốt",
                "macro_impact": "Vĩ mô thuận lợi",
                "long_term_suggestion": "Nên mua dài hạn",
                "swing_trade_suggestion": "Lướt sóng thận trọng",
                "recommendation": "Mua",
                "confidence": "Cao",
            }
        )
        response = MagicMock()
        response.message.content = report_json
        return response

    @pytest.mark.asyncio
    async def test_returns_stock_report(self):
        from localstock.ai.client import OllamaClient, StockReport

        with patch("localstock.ai.client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_model = "test-model"
            settings.ollama_host = "http://localhost:11434"
            settings.ollama_timeout = 120
            settings.ollama_keep_alive = "5m"
            mock_settings.return_value = settings

            client = OllamaClient()
            client.client = AsyncMock()
            client.client.chat = AsyncMock(return_value=self._make_mock_response())

            result = await client.generate_report("test prompt", "VNM")
            assert isinstance(result, StockReport)
            assert result.recommendation == "Mua"

    @pytest.mark.asyncio
    async def test_calls_chat_with_correct_params(self):
        from localstock.ai.client import OllamaClient

        with patch("localstock.ai.client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_model = "test-model"
            settings.ollama_host = "http://localhost:11434"
            settings.ollama_timeout = 120
            settings.ollama_keep_alive = "5m"
            mock_settings.return_value = settings

            client = OllamaClient()
            client.client = AsyncMock()
            client.client.chat = AsyncMock(return_value=self._make_mock_response())

            await client.generate_report("test prompt data", "VNM")

            call_kwargs = client.client.chat.call_args
            assert call_kwargs.kwargs["model"] == "test-model"
            # Check system prompt is in messages
            messages = call_kwargs.kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert "Việt Nam" in messages[0]["content"]
            # Check options
            assert call_kwargs.kwargs["options"]["temperature"] == 0.3
            assert call_kwargs.kwargs["options"]["num_ctx"] == 4096

    @pytest.mark.asyncio
    async def test_uses_report_system_prompt(self):
        from localstock.ai.client import OllamaClient
        from localstock.ai.prompts import REPORT_SYSTEM_PROMPT

        with patch("localstock.ai.client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.ollama_model = "test-model"
            settings.ollama_host = "http://localhost:11434"
            settings.ollama_timeout = 120
            settings.ollama_keep_alive = "5m"
            mock_settings.return_value = settings

            client = OllamaClient()
            client.client = AsyncMock()
            client.client.chat = AsyncMock(return_value=self._make_mock_response())

            await client.generate_report("test prompt", "VNM")

            call_kwargs = client.client.chat.call_args
            messages = call_kwargs.kwargs["messages"]
            assert messages[0]["content"] == REPORT_SYSTEM_PROMPT
