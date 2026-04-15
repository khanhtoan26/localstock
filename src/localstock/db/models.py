"""SQLAlchemy ORM models for LocalStock database."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
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
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "year", "period", "report_type", name="uq_financial_stmt"),
    )


class PipelineRun(Base):
    """Pipeline execution tracking."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # 'running', 'completed', 'failed'
    run_type: Mapped[str] = mapped_column(String(20))  # 'backfill', 'daily', 'manual'
    symbols_total: Mapped[int] = mapped_column(Integer, default=0)
    symbols_success: Mapped[int] = mapped_column(Integer, default=0)
    symbols_failed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
