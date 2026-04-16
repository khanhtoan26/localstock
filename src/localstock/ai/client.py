"""Ollama AsyncClient wrapper with retry and structured output.

Per D-02: Uses Qwen2.5 14B Q4_K_M (configurable).
Per D-03: Uses Ollama format parameter with Pydantic JSON Schema for structured output.
Per Pitfall 4: Health check before LLM calls — skip sentiment if Ollama is down.
Per REPT-01: StockReport model for structured report generation output.
"""

import httpx
from loguru import logger
from ollama import AsyncClient, ResponseError
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from localstock.ai.prompts import REPORT_SYSTEM_PROMPT, SENTIMENT_SYSTEM_PROMPT
from localstock.config import get_settings


class SentimentResult(BaseModel):
    """Structured sentiment classification output from LLM.

    Per D-03: { sentiment, score, reason } format.

    Attributes:
        sentiment: One of "positive", "negative", or "neutral".
        score: Confidence score from 0.0 (very negative) to 1.0 (very positive).
        reason: Brief explanation in Vietnamese.
    """

    sentiment: str = Field(description="positive, negative, or neutral")
    score: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0, 0.5=neutral")
    reason: str = Field(description="Brief explanation in Vietnamese")


class StockReport(BaseModel):
    """Structured report output from LLM for stock analysis.

    Per REPT-01: All 9 sections for a complete AI-generated analysis report.
    Used as Ollama format parameter for structured JSON generation.

    Attributes:
        summary: 2-3 sentence overview of the stock.
        technical_analysis: Technical indicator signal analysis.
        fundamental_analysis: Fundamental ratio evaluation.
        sentiment_analysis: Market sentiment from news.
        macro_impact: Macro context impact on sector/stock.
        long_term_suggestion: Long-term investment suggestion with reasoning.
        swing_trade_suggestion: Swing trade suggestion with T+3 warning.
        recommendation: Mua mạnh / Mua / Nắm giữ / Bán / Bán mạnh.
        confidence: Cao / Trung bình / Thấp.
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


class OllamaClient:
    """Wrapper around Ollama AsyncClient with retry, health check, and structured output.

    Provides a simplified interface for LLM-powered sentiment classification
    with built-in retry logic, server health checking, and Pydantic-validated
    structured JSON output.

    Attributes:
        model: Ollama model name (e.g., "qwen2.5:14b-instruct-q4_K_M").
        host: Ollama server URL.
        timeout: Request timeout in seconds.
        keep_alive: How long to keep the model loaded in memory.
        client: Ollama AsyncClient instance.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: int | None = None,
        keep_alive: str | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host
        self.timeout = timeout or settings.ollama_timeout
        self.keep_alive = keep_alive or settings.ollama_keep_alive
        self.client = AsyncClient(
            host=self.host, timeout=httpx.Timeout(self.timeout)
        )

    async def health_check(self) -> bool:
        """Check if Ollama server is running (GET /api/version).

        Per Pitfall 4: Don't block scoring if Ollama is down.

        Returns:
            True if Ollama server responds with 200, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.host}/api/version", timeout=5)
                return resp.status_code == 200
        except Exception:
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.TimeoutException, ResponseError)
        ),
    )
    async def classify_sentiment(
        self, article_text: str, symbol: str
    ) -> SentimentResult:
        """Classify sentiment of article text for a specific stock symbol.

        Per T-03-01: Truncate article to 2000 chars to limit prompt injection surface.
        Per D-03: Uses format parameter with SentimentResult JSON schema.

        Args:
            article_text: Full or partial article text to analyze.
            symbol: Stock ticker symbol (e.g., "VNM").

        Returns:
            SentimentResult with sentiment classification, score, and reason.

        Raises:
            ConnectionError: If Ollama server is not reachable (retried 3 times).
            TimeoutError: If request exceeds timeout (retried 3 times).
            ValidationError: If LLM output doesn't match SentimentResult schema.
        """
        # Truncate to prevent context overflow (Pitfall 1)
        truncated = article_text[:2000]

        logger.debug(f"Classifying sentiment for {symbol} ({len(truncated)} chars)")

        response = await self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Mã cổ phiếu: {symbol}\n\nBài viết:\n{truncated}",
                },
            ],
            format=SentimentResult.model_json_schema(),
            options={"temperature": 0.1, "num_ctx": 4096},
            keep_alive=self.keep_alive,
        )

        result = SentimentResult.model_validate_json(response.message.content)
        logger.info(
            f"Sentiment for {symbol}: {result.sentiment} "
            f"(score={result.score:.2f}) — {result.reason}"
        )
        return result

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=5, max=30),
        retry=retry_if_exception_type(
            (httpx.ConnectError, httpx.TimeoutException, ResponseError)
        ),
    )
    async def generate_report(self, data_prompt: str, symbol: str) -> StockReport:
        """Generate a structured stock analysis report using LLM.

        Sends data-injection prompt with REPORT_SYSTEM_PROMPT and returns
        a StockReport parsed from the LLM's structured JSON output.

        Per T-04-07: System prompt includes disclaimer about not being official advice.
        Per REPT-01: Uses StockReport schema as Ollama format parameter.

        Args:
            data_prompt: Formatted prompt with all stock data injected.
            symbol: Stock ticker symbol (e.g., "VNM") for logging.

        Returns:
            StockReport with all 9 analysis sections filled by LLM.

        Raises:
            ConnectionError: If Ollama server is not reachable (retried 2 times).
            TimeoutError: If request exceeds timeout (retried 2 times).
            ValidationError: If LLM output doesn't match StockReport schema.
        """
        logger.debug(f"Generating report for {symbol} ({len(data_prompt)} chars prompt)")

        response = await self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": data_prompt},
            ],
            format=StockReport.model_json_schema(),
            options={"temperature": 0.3, "num_ctx": 4096},
            keep_alive=self.keep_alive,
        )

        result = StockReport.model_validate_json(response.message.content)
        logger.info(f"Generated report for {symbol}: {result.recommendation}")
        return result
