"""Application configuration loaded from .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql+asyncpg://localhost:5432/localstock"
    database_url_migration: str = ""
    vnstock_source: str = "VCI"
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
