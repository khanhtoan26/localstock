"""Application configuration loaded from .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def _find_env_file() -> str:
    """Search up from CWD for .env file (monorepo support)."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".env").exists():
            return str(parent / ".env")
        if (parent / ".git").exists():
            break
    return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql+asyncpg://localhost:5432/localstock"
    database_url_migration: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        if isinstance(v, str) and (v.startswith("postgresql://") or v.startswith("postgres://")):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: object) -> str:
        """Normalize and validate log_level (per CONTEXT.md D-06).

        Loguru recognizes: TRACE < DEBUG < INFO < SUCCESS < WARNING < ERROR < CRITICAL.
        Fail-fast at startup beats a confusing error from `logger.add(level=...)` later.
        """
        allowed = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        if not isinstance(v, str):
            raise ValueError("log_level must be a string")
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got {v!r}")
        return upper

    vnstock_source: str = "VCI"
    vnstock_api_key: str = ""  # Set via VNSTOCK_API_KEY env var
    crawl_delay_seconds: float = 1.0
    crawl_batch_size: int = 50
    log_level: str = "INFO"

    # Ollama settings (per D-02)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"
    ollama_timeout: int = 120
    ollama_keep_alive: str = "30m"

    # Scoring weights — must sum to 1.0 across active dims (per D-04, D-06)
    scoring_weight_technical: float = 0.30
    scoring_weight_fundamental: float = 0.30
    scoring_weight_sentiment: float = 0.20
    scoring_weight_macro: float = 0.20  # Phase 4: macro dimension active

    # Funnel settings
    funnel_top_n: int = 50  # Stocks passing to LLM sentiment
    sentiment_articles_per_stock: int = 5
    sentiment_lookback_days: int = 7

    # Report generation settings (Phase 4)
    report_top_n: int = 20  # Top-ranked stocks to generate reports for
    report_max_tokens: int = 4096  # LLM context window for report generation

    # SSL verification (set to false behind corporate proxy with self-signed certs)
    ssl_verify: bool = True

    # Telegram notifications (per D-01)
    telegram_bot_token: str = ""  # Set via TELEGRAM_BOT_TOKEN env var
    telegram_chat_id: str = ""    # Set via TELEGRAM_CHAT_ID env var

    # Scheduler settings (per D-02)
    scheduler_run_hour: int = 15
    scheduler_run_minute: int = 45

    # Score change alert threshold (per D-03)
    score_change_threshold: float = 15.0

    # Phase 24 — slow-query threshold (D-02, OBS-13)
    slow_query_threshold_ms: int = Field(default=250, ge=1, le=10000)

    # === Phase 25 / DQ — per-rule shadow dispatcher (D-06) ===
    # Per CONTEXT D-06: env flags per rule; default = shadow until promotion.
    # The `dq_default_tier2_mode` applies when a per-rule mode is unset.
    dq_default_tier2_mode: str = "shadow"  # validated to {'shadow','enforce'}
    dq_tier2_rsi_mode: str | None = None
    dq_tier2_gap_mode: str | None = None
    dq_tier2_missing_mode: str | None = None

    # === Phase 25 / DQ-07 — stale-data threshold (D-05) ===
    # /health/data flips from "fresh" → "stale" once max(prices.date) lags
    # the latest trading session by more than this many sessions.
    dq_stale_threshold_sessions: int = 1

    @field_validator(
        "dq_default_tier2_mode",
        "dq_tier2_rsi_mode",
        "dq_tier2_gap_mode",
        "dq_tier2_missing_mode",
        mode="before",
    )
    @classmethod
    def _validate_tier2_mode(cls, v: object) -> object:
        """Per-rule Tier 2 modes must be one of {shadow, enforce} (D-06).

        ``None`` and empty-string both mean "fall back to dq_default_tier2_mode".
        """
        if v is None:
            return None
        if isinstance(v, str) and v == "":
            return None
        allowed = {"shadow", "enforce"}
        if not isinstance(v, str) or v.lower() not in allowed:
            raise ValueError(
                f"tier2 mode must be one of {sorted(allowed)}, got {v!r}"
            )
        return v.lower()

    model_config = {"env_file": _find_env_file(), "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
