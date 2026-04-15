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
    scoring_weight_technical: float = 0.35
    scoring_weight_fundamental: float = 0.35
    scoring_weight_sentiment: float = 0.30
    scoring_weight_macro: float = 0.0  # Phase 4 activates this

    # Funnel settings
    funnel_top_n: int = 50  # Stocks passing to LLM sentiment
    sentiment_articles_per_stock: int = 5
    sentiment_lookback_days: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
