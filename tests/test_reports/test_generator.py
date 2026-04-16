"""Tests for StockReport model and ReportDataBuilder.

Tests:
- StockReport has all 9 required fields
- StockReport validates correctly with sample data
- build_report_prompt returns formatted string with expected sections
- build_report_prompt handles None values gracefully
- ReportDataBuilder.build returns dict with all template keys populated
- build_report_prompt output is under 3000 characters
"""

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
