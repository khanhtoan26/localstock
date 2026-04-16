"""Report data assembly and StockReport model.

Per REPT-01: StockReport Pydantic model for structured LLM output with 9 sections.
Per REPT-02: ReportDataBuilder assembles all stock data into prompt-ready dict.

StockReport is used as the Ollama format schema for structured JSON generation.
ReportDataBuilder gathers data from scoring, indicators, ratios, sentiment, macro, T+3.
"""

from pydantic import BaseModel, Field

from localstock.ai.prompts import REPORT_USER_TEMPLATE


class StockReport(BaseModel):
    """Structured LLM output for stock analysis report.

    Per REPT-01: All 9 sections required for a complete analysis report.
    Used as Ollama format parameter for structured JSON generation.

    Attributes:
        summary: 2-3 sentence overview of the stock.
        technical_analysis: Technical indicator signal analysis.
        fundamental_analysis: Fundamental ratio evaluation.
        sentiment_analysis: Market sentiment from news.
        macro_impact: Macro context impact on sector/stock.
        long_term_suggestion: Long-term investment suggestion with reasoning.
        swing_trade_suggestion: Swing trade suggestion with T+3 warning.
        recommendation: Buy strong / Buy / Hold / Sell / Sell strong.
        confidence: High / Medium / Low.
    """

    summary: str = Field(description="Tóm tắt 2-3 câu về mã cổ phiếu")
    technical_analysis: str = Field(description="Phân tích tín hiệu kỹ thuật")
    fundamental_analysis: str = Field(description="Đánh giá chỉ số cơ bản")
    sentiment_analysis: str = Field(description="Phân tích tâm lý thị trường từ tin tức")
    macro_impact: str = Field(description="Ảnh hưởng bối cảnh vĩ mô lên ngành/cổ phiếu")
    long_term_suggestion: str = Field(description="Gợi ý đầu tư dài hạn với lý do")
    swing_trade_suggestion: str = Field(description="Gợi ý lướt sóng kèm cảnh báo T+3")
    recommendation: str = Field(description="Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh")
    confidence: str = Field(description="Cao / Trung bình / Thấp")


def _safe(value, fallback: str = "N/A") -> str:
    """Return value as string, or fallback if None."""
    if value is None:
        return fallback
    return str(value)


def _safe_float(value, fmt: str = ".1f", fallback: str = "N/A") -> str:
    """Format float value, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):{fmt}}"
    except (ValueError, TypeError):
        return fallback


def _safe_pct(value, fallback: str = "N/A") -> str:
    """Format value as percentage, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return fallback


def build_report_prompt(data: dict) -> str:
    """Format stock data into a report generation prompt.

    Takes a dict with all stock data fields and formats using REPORT_USER_TEMPLATE.
    Per T-04-06: Numeric data formatted as values, not raw text.

    Args:
        data: Dict with all prompt template placeholder keys.

    Returns:
        Formatted prompt string ready for LLM consumption.
    """
    # Build safe copy with fallbacks for None values
    safe_data = {}
    for key, value in data.items():
        safe_data[key] = _safe(value) if value is None else value
    return REPORT_USER_TEMPLATE.format(**safe_data)


class ReportDataBuilder:
    """Assembles all stock data into a dict for prompt template injection.

    Gathers data from multiple sources (scoring, indicators, ratios, sentiment,
    macro, T+3 prediction, stock info) and produces a flat dict with all keys
    needed by REPORT_USER_TEMPLATE.
    """

    def build(
        self,
        symbol: str,
        score_data: dict,
        indicator_data: dict,
        ratio_data: dict,
        sentiment_data: dict,
        macro_data: dict,
        t3_data: dict,
        stock_info: dict,
    ) -> dict:
        """Assemble all stock data into prompt-ready dict.

        Args:
            symbol: Stock ticker (e.g., "VNM").
            score_data: Composite scoring results (total, grade, dimension scores).
            indicator_data: Technical indicators (RSI, MACD, trend, etc.).
            ratio_data: Fundamental ratios (P/E, P/B, ROE, etc.).
            sentiment_data: Sentiment analysis summary.
            macro_data: Macro conditions summary.
            t3_data: T+3 prediction results.
            stock_info: Company name, industry, close price.

        Returns:
            Dict with all keys needed for REPORT_USER_TEMPLATE.
            None values replaced with "N/A" or "Không có dữ liệu".
        """
        return {
            # Stock info
            "symbol": symbol,
            "company_name": _safe(stock_info.get("company_name"), "Không rõ"),
            "industry": _safe(stock_info.get("industry"), "Không rõ"),
            "close_price": _safe(stock_info.get("close_price"), "N/A"),
            # Composite scores
            "total_score": _safe_float(score_data.get("total"), ".1f"),
            "grade": _safe(score_data.get("grade")),
            "technical_score": _safe_float(score_data.get("technical"), ".1f"),
            "fundamental_score": _safe_float(score_data.get("fundamental"), ".1f"),
            "sentiment_score": _safe_float(score_data.get("sentiment"), ".1f"),
            "macro_score": _safe_float(score_data.get("macro"), ".1f"),
            # Technical indicators
            "rsi_14": _safe_float(indicator_data.get("rsi_14"), ".1f"),
            "macd_histogram": _safe_float(indicator_data.get("macd_histogram"), ".3f"),
            "trend_direction": _safe(indicator_data.get("trend_direction")),
            "trend_strength": _safe_float(indicator_data.get("trend_strength"), ".1f"),
            # Fundamental ratios
            "pe_ratio": _safe_float(ratio_data.get("pe_ratio"), ".1f"),
            "pb_ratio": _safe_float(ratio_data.get("pb_ratio"), ".1f"),
            "roe": _safe_pct(ratio_data.get("roe")),
            "debt_to_equity": _safe_float(ratio_data.get("debt_to_equity"), ".2f"),
            "revenue_growth": _safe_pct(ratio_data.get("revenue_growth")),
            # Sentiment
            "sentiment_summary": _safe(
                sentiment_data.get("summary"), "Không có dữ liệu sentiment"
            ),
            # Macro
            "macro_conditions": _safe(
                macro_data.get("conditions"), "Không có dữ liệu vĩ mô"
            ),
            # T+3 prediction
            "t3_direction": _safe(t3_data.get("direction"), "neutral"),
            "t3_confidence": _safe(t3_data.get("confidence"), "low"),
            "t3_reasons": _safe(
                ", ".join(t3_data["reasons"]) if t3_data.get("reasons") else None,
                "Không đủ dữ liệu dự đoán",
            ),
            "t3_warning": _safe(
                t3_data.get("t3_warning"),
                "⚠️ CẢNH BÁO T+3: Cổ phiếu mua hôm nay chỉ có thể bán sau 3 ngày làm việc.",
            ),
        }
