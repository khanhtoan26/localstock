"""Tests for AnalysisService — analysis pipeline orchestration."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from localstock.services.analysis_service import AnalysisService


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def ohlcv_250():
    """250-day OHLCV data for a single symbol."""
    np.random.seed(42)
    n = 250
    dates = [date(2023, 1, 2) + pd.Timedelta(days=i) for i in range(n)]
    close = 50000 + np.cumsum(np.random.randn(n) * 500)
    return pd.DataFrame({
        "date": dates,
        "open": close - np.random.rand(n) * 200,
        "high": close + np.abs(np.random.randn(n)) * 300,
        "low": close - np.abs(np.random.randn(n)) * 300,
        "close": close,
        "volume": np.random.randint(500_000, 5_000_000, n),
    })


class TestAnalyzeTechnicalSingle:
    def test_produces_indicator_row(self, ohlcv_250):
        service = AnalysisService.__new__(AnalysisService)
        from localstock.analysis.technical import TechnicalAnalyzer
        from localstock.analysis.trend import detect_trend, compute_pivot_points, find_support_resistance
        service.tech_analyzer = TechnicalAnalyzer()

        row = service.analyze_technical_single("VNM", ohlcv_250)
        assert row["symbol"] == "VNM"
        assert "sma_20" in row
        assert "rsi_14" in row
        assert "macd" in row
        assert "avg_volume_20" in row
        assert "trend_direction" in row
        assert "pivot_point" in row

    def test_handles_short_data(self):
        """Data with < 20 rows should still produce partial results."""
        service = AnalysisService.__new__(AnalysisService)
        from localstock.analysis.technical import TechnicalAnalyzer
        service.tech_analyzer = TechnicalAnalyzer()

        short_df = pd.DataFrame({
            "date": [date(2024, 1, i) for i in range(1, 6)],
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [102.0] * 5,
            "volume": [1000000] * 5,
        })
        row = service.analyze_technical_single("TEST", short_df)
        assert row["symbol"] == "TEST"


class TestAnalyzeFundamentalSingle:
    def test_produces_ratio_row(self):
        service = AnalysisService.__new__(AnalysisService)
        from localstock.analysis.fundamental import FundamentalAnalyzer
        service.fund_analyzer = FundamentalAnalyzer()

        income = {"revenue": 15000.0, "net_profit": 4500.0, "share_holder_income": 4200.0}
        balance = {"asset": 700000.0, "debt": 640000.0, "equity": 60000.0}

        row = service.analyze_fundamental_single(
            symbol="ACB",
            year=2024,
            period="Q3",
            income_data=income,
            balance_data=balance,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        assert row["symbol"] == "ACB"
        assert row["pe_ratio"] is not None
        assert row["roe"] is not None
        assert row["de_ratio"] is not None
