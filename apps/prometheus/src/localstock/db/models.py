"""SQLAlchemy ORM models for LocalStock database."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Stock(Base):
    """Stock master data — one row per ticker symbol."""

    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str] = mapped_column(String(10))  # HOSE, HNX, UPCOM
    industry_icb3: Mapped[str | None] = mapped_column(String(200))
    industry_icb4: Mapped[str | None] = mapped_column(String(200))
    issue_shares: Mapped[float | None] = mapped_column(Float)
    charter_capital: Mapped[float | None] = mapped_column(Float)  # in billion VND
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class StockPrice(Base):
    """Daily OHLCV price data with adjustment factors."""

    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)  # volumes can exceed 2B
    # Adjusted prices (null until corporate actions applied)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    adj_factor: Mapped[float] = mapped_column(Float, default=1.0)  # cumulative adjustment factor

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_stock_price"),
        Index("ix_stock_prices_symbol_date", "symbol", "date"),
    )


class CorporateEvent(Base):
    """Corporate events (splits, dividends, rights issues)."""

    __tablename__ = "corporate_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    event_title: Mapped[str | None] = mapped_column(String(500))
    event_type: Mapped[str | None] = mapped_column(
        String(100)
    )  # 'split', 'stock_dividend', 'cash_dividend', 'rights_issue'
    exright_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    ratio: Mapped[float | None] = mapped_column(Float)  # split ratio or dividend rate
    value: Mapped[float | None] = mapped_column(Float)
    public_date: Mapped[date | None] = mapped_column(Date)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)  # has price adjustment been applied?

    __table_args__ = (
        UniqueConstraint("symbol", "exright_date", "event_type", name="uq_corporate_event"),
    )


class FinancialStatement(Base):
    """Financial statement data stored as flexible JSON."""

    __tablename__ = "financial_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    period: Mapped[str] = mapped_column(String(10))  # 'Q1', 'Q2', 'Q3', 'Q4', 'annual'
    year: Mapped[int] = mapped_column(Integer)
    report_type: Mapped[str] = mapped_column(
        String(30)
    )  # 'balance_sheet', 'income_statement', 'cash_flow'
    data: Mapped[dict] = mapped_column(JSON)  # full report stored as JSON for schema flexibility
    unit: Mapped[str] = mapped_column(String(20), default="billion_vnd")  # normalized unit
    source: Mapped[str] = mapped_column(String(10))  # 'VCI' or 'KBS'
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "year", "period", "report_type", name="uq_financial_stmt"),
    )


class PipelineRun(Base):
    """Pipeline execution tracking."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # 'running', 'completed', 'failed'
    run_type: Mapped[str] = mapped_column(String(20))  # 'backfill', 'daily', 'manual'
    symbols_total: Mapped[int] = mapped_column(Integer, default=0)
    symbols_success: Mapped[int] = mapped_column(Integer, default=0)
    symbols_failed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Phase 24 / OBS-17 — per-step duration capture (24-02 migration)
    crawl_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analyze_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Phase 25 / DQ-06 — D-07 stats JSONB; dual-written from 25-04 helper.
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TechnicalIndicator(Base):
    """Daily technical indicator values per stock."""

    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    # Moving Averages
    sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_26: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Momentum
    rsi_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Bollinger Bands
    bb_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_middle: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Additional indicators (per D-01)
    stoch_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    stoch_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    adx: Mapped[float | None] = mapped_column(Float, nullable=True)
    obv: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Volume Analysis (TECH-02)
    avg_volume_20: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_trend: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'increasing', 'decreasing', 'stable'
    # Trend (TECH-03)
    trend_direction: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'uptrend', 'downtrend', 'sideways'
    trend_strength: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0-100 based on ADX
    # Support/Resistance (TECH-04)
    pivot_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    nearest_support: Mapped[float | None] = mapped_column(Float, nullable=True)
    nearest_resistance: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Metadata
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_technical_indicator"),
        Index("ix_tech_indicators_symbol_date", "symbol", "date"),
    )


class FinancialRatio(Base):
    """Computed financial ratios per stock per period."""

    __tablename__ = "financial_ratios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    year: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(10))  # 'Q1'..'Q4', 'TTM'
    # Core ratios (FUND-01)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roa: Mapped[float | None] = mapped_column(Float, nullable=True)
    de_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Growth metrics (FUND-02)
    revenue_qoq: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_qoq: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Raw values for ratio computation
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    book_value_per_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Metadata
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "year", "period", name="uq_financial_ratio"),
    )


class IndustryGroup(Base):
    """Vietnamese-specific industry grouping for FUND-03."""

    __tablename__ = "industry_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_code: Mapped[str] = mapped_column(String(20), unique=True)
    group_name_vi: Mapped[str] = mapped_column(String(200))
    group_name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockIndustryMapping(Base):
    """Maps each stock to a Vietnamese industry group."""

    __tablename__ = "stock_industry_mapping"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    group_code: Mapped[str] = mapped_column(String(20), index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class IndustryAverage(Base):
    """Precomputed industry average ratios for FUND-03 comparison."""

    __tablename__ = "industry_averages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_code: Mapped[str] = mapped_column(String(20), index=True)
    year: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(10))
    # Average ratios
    avg_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pb: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_roa: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_de: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_revenue_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_profit_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    stock_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("group_code", "year", "period", name="uq_industry_average"),
    )


class NewsArticle(Base):
    """Crawled financial news articles."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(500), unique=True)  # dedup key
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20))  # 'cafef', 'vnexpress'
    source_feed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_news_articles_published", "published_at"),
        Index("ix_news_articles_source", "source"),
    )


class SentimentScore(Base):
    """LLM-classified sentiment per article-ticker pair."""

    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_articles.id"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    sentiment: Mapped[str] = mapped_column(String(10))  # 'positive', 'negative', 'neutral'
    score: Mapped[float] = mapped_column(Float)  # 0.0 to 1.0
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("article_id", "symbol", name="uq_sentiment_score"),
    )


class CompositeScore(Base):
    """Aggregated multi-dimensional score per stock."""

    __tablename__ = "composite_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Phase 4
    total_score: Mapped[float] = mapped_column(Float)  # 0-100 weighted
    grade: Mapped[str] = mapped_column(String(2))  # A, B, C, D, F
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions_used: Mapped[int] = mapped_column(Integer, default=2)
    weights_json: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_composite_score"),
    )


class MacroIndicator(Base):
    """Macro-economic indicator data (interest_rate, exchange_rate_usd_vnd, cpi, gdp)."""

    __tablename__ = "macro_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_type: Mapped[str] = mapped_column(String(30))  # interest_rate, exchange_rate_usd_vnd, cpi, gdp
    value: Mapped[float] = mapped_column(Float)
    period: Mapped[str] = mapped_column(String(20))  # '2026-Q1', '2026-03', etc.
    source: Mapped[str] = mapped_column(String(50))  # 'SBV', 'GSO', etc.
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'rising', 'falling', 'stable'
    recorded_at: Mapped[date] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("indicator_type", "period", name="uq_macro_indicator"),
    )


class AnalysisReport(Base):
    """LLM-generated analysis report per stock."""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    report_type: Mapped[str] = mapped_column(String(20))  # 'daily', 'weekly', etc.
    content_json: Mapped[dict] = mapped_column(JSON)  # Full report as structured JSON
    summary: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(String(20))  # 'buy', 'sell', 'hold'
    t3_prediction: Mapped[str | None] = mapped_column(String(20), nullable=True)  # T+3 price direction
    model_used: Mapped[str] = mapped_column(String(50))  # LLM model identifier
    total_score: Mapped[float] = mapped_column(Float)  # composite score at report time
    grade: Mapped[str] = mapped_column(String(2))  # A, B, C, D, F
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", "report_type", name="uq_analysis_report"),
    )


class ScoreChangeAlert(Base):
    """Records significant score changes detected between consecutive runs (SCOR-04)."""

    __tablename__ = "score_change_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    previous_score: Mapped[float] = mapped_column(Float)
    current_score: Mapped[float] = mapped_column(Float)
    delta: Mapped[float] = mapped_column(Float)
    previous_grade: Mapped[str] = mapped_column(String(2))
    current_grade: Mapped[str] = mapped_column(String(2))
    direction: Mapped[str] = mapped_column(String(10))  # 'up' or 'down'
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_score_change_alert"),
    )


class SectorSnapshot(Base):
    """Daily sector-level aggregated metrics for rotation tracking (SCOR-05)."""

    __tablename__ = "sector_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    group_code: Mapped[str] = mapped_column(String(20), index=True)
    avg_score: Mapped[float] = mapped_column(Float)
    avg_volume: Mapped[float] = mapped_column(Float)
    total_volume: Mapped[int] = mapped_column(BigInteger)
    stock_count: Mapped[int] = mapped_column(Integer)
    avg_score_change: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("date", "group_code", name="uq_sector_snapshot"),
    )


class NotificationLog(Base):
    """Log of sent notifications for deduplication (Pitfall 2 mitigation)."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    notification_type: Mapped[str] = mapped_column(String(30))  # 'daily_digest', 'score_alert', 'manual'
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    status: Mapped[str] = mapped_column(String(20))  # 'sent', 'failed', 'skipped'
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("date", "notification_type", name="uq_notification_log"),
    )


class AdminJob(Base):
    """Admin-triggered job tracking (Phase 11)."""

    __tablename__ = "admin_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(30))  # 'crawl', 'analyze', 'score', 'report', 'pipeline'
    status: Mapped[str] = mapped_column(String(20))  # 'pending', 'running', 'completed', 'failed'
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_admin_jobs_status", "status"),
        Index("ix_admin_jobs_created_at", "created_at"),
    )


class QuarantineRow(Base):
    """Phase 25 / DQ-08 — rejected rows from Tier 1 validation (D-02).

    Polymorphic across sources (ohlcv, financials, indicators). Retention
    cron lives in apps/prometheus/src/localstock/scheduler (25-03).
    """

    __tablename__ = "quarantine_rows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    payload: Mapped[dict | list] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    rule: Mapped[str] = mapped_column(String(64))
    tier: Mapped[str] = mapped_column(String(16))
    quarantined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
