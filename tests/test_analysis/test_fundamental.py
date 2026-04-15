"""Tests for FundamentalAnalyzer — financial ratios and growth (FUND-01, FUND-02)."""

import pytest

from localstock.analysis.fundamental import FundamentalAnalyzer


@pytest.fixture
def analyzer():
    return FundamentalAnalyzer()


@pytest.fixture
def income_data():
    """VCI income_statement data dict (values in billion_vnd)."""
    return {
        "revenue": 15000.0,
        "net_profit": 4500.0,
        "share_holder_income": 4200.0,
    }


@pytest.fixture
def balance_data():
    """VCI balance_sheet data dict (values in billion_vnd)."""
    return {
        "asset": 700000.0,
        "debt": 640000.0,
        "equity": 60000.0,
    }


class TestComputeRatios:
    def test_returns_all_ratio_keys(self, analyzer, income_data, balance_data):
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,  # VND per share
            shares_outstanding=3_880_000_000,
        )
        for key in ["pe_ratio", "pb_ratio", "eps", "roe", "roa", "de_ratio"]:
            assert key in result, f"Missing key: {key}"

    def test_pe_ratio(self, analyzer, income_data, balance_data):
        """P/E = market_cap / net_profit = (price * shares) / share_holder_income."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        # market_cap = 85000 * 3.88B = 329,800B VND = 329,800 billion VND
        # P/E = market_cap_billion / share_holder_income = 329800 / 4200 ≈ 78.52
        expected_pe = (85000.0 * 3_880_000_000 / 1e9) / 4200.0
        assert result["pe_ratio"] == pytest.approx(expected_pe, rel=0.01)

    def test_pb_ratio(self, analyzer, income_data, balance_data):
        """P/B = market_cap / equity."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        market_cap = 85000.0 * 3_880_000_000 / 1e9
        expected_pb = market_cap / 60000.0
        assert result["pb_ratio"] == pytest.approx(expected_pb, rel=0.01)

    def test_eps(self, analyzer, income_data, balance_data):
        """EPS = share_holder_income * 1e9 / shares_outstanding (result in VND)."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        expected_eps = 4200.0 * 1e9 / 3_880_000_000
        assert result["eps"] == pytest.approx(expected_eps, rel=0.01)

    def test_roe(self, analyzer, income_data, balance_data):
        """ROE = share_holder_income / equity * 100."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        expected_roe = 4200.0 / 60000.0 * 100
        assert result["roe"] == pytest.approx(expected_roe, rel=0.01)

    def test_roa(self, analyzer, income_data, balance_data):
        """ROA = share_holder_income / asset * 100."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        expected_roa = 4200.0 / 700000.0 * 100
        assert result["roa"] == pytest.approx(expected_roa, rel=0.01)

    def test_de_ratio(self, analyzer, income_data, balance_data):
        """D/E = debt / equity."""
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        expected_de = 640000.0 / 60000.0
        assert result["de_ratio"] == pytest.approx(expected_de, rel=0.01)

    def test_negative_equity_de_none(self, analyzer, income_data):
        """Negative equity → D/E = None."""
        bad_balance = {"asset": 50000.0, "debt": 60000.0, "equity": -10000.0}
        result = analyzer.compute_ratios(
            income_data=income_data,
            balance_data=bad_balance,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        assert result["de_ratio"] is None

    def test_zero_earnings_pe_none(self, analyzer, balance_data):
        """Zero earnings → P/E = None."""
        zero_income = {"revenue": 15000.0, "net_profit": 0.0, "share_holder_income": 0.0}
        result = analyzer.compute_ratios(
            income_data=zero_income,
            balance_data=balance_data,
            current_price=85000.0,
            shares_outstanding=3_880_000_000,
        )
        assert result["pe_ratio"] is None


class TestComputeGrowth:
    def test_qoq_growth(self, analyzer):
        result = analyzer.compute_growth(
            current_revenue=15000.0,
            previous_revenue=12000.0,
            current_profit=4500.0,
            previous_profit=3800.0,
        )
        assert result["revenue_qoq"] == pytest.approx(25.0, rel=0.01)
        assert result["profit_qoq"] == pytest.approx(18.42, rel=0.01)

    def test_growth_previous_zero_returns_none(self, analyzer):
        result = analyzer.compute_growth(
            current_revenue=15000.0,
            previous_revenue=0.0,
            current_profit=4500.0,
            previous_profit=0.0,
        )
        assert result["revenue_qoq"] is None
        assert result["profit_qoq"] is None


class TestComputeTTM:
    def test_sums_four_quarters(self, analyzer):
        """TTM for revenue: sum of Q1+Q2+Q3+Q4."""
        quarterly_data = [
            {"revenue": 10000.0, "share_holder_income": 3000.0},
            {"revenue": 12000.0, "share_holder_income": 3500.0},
            {"revenue": 11000.0, "share_holder_income": 3200.0},
            {"revenue": 15000.0, "share_holder_income": 4200.0},
        ]
        result = analyzer.compute_ttm(quarterly_data, "revenue")
        assert result == pytest.approx(48000.0)

    def test_ttm_with_missing_quarter_returns_none(self, analyzer):
        """Less than 4 quarters available → None."""
        quarterly_data = [
            {"revenue": 10000.0},
            {"revenue": 12000.0},
        ]
        result = analyzer.compute_ttm(quarterly_data, "revenue")
        assert result is None
