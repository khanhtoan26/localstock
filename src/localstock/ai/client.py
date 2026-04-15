"""Ollama AsyncClient wrapper with retry and structured output.

Per D-02: Uses Qwen2.5 14B Q4_K_M (configurable).
Per D-03: Uses Ollama format parameter with Pydantic JSON Schema for structured output.
Per Pitfall 4: Health check before LLM calls — skip sentiment if Ollama is down.
"""

import httpx
from loguru import logger
from ollama import AsyncClient
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from localstock.ai.prompts import SENTIMENT_SYSTEM_PROMPT
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
        self.client = AsyncClient(host=self.host)

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
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
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
