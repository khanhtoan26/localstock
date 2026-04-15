"""Fundamental analysis: financial ratio and growth computation (FUND-01, FUND-02).

Computes P/E, P/B, EPS, ROE, ROA, D/E from financial statement JSON data,
and calculates QoQ/YoY growth rates for revenue and profit.

All monetary values are expected in billion_vnd (normalized in Phase 1).
Price is in VND per share. Shares outstanding is in shares.
"""

from datetime import UTC, datetime

from loguru import logger


class FundamentalAnalyzer:
    """Computes financial ratios and growth metrics from financial statements.

    Per FUND-01: P/E, P/B, EPS, ROE, ROA, D/E
    Per FUND-02: Revenue QoQ/YoY, Profit QoQ/YoY
    """

    def compute_ratios(
        self,
        income_data: dict,
        balance_data: dict,
        current_price: float,
        shares_outstanding: int | float,
    ) -> dict:
        """Compute core financial ratios (FUND-01).

        Args:
            income_data: Dict from FinancialStatement.data (income_statement).
                         Keys: 'revenue', 'net_profit', 'share_holder_income'.
                         Values in billion_vnd.
            balance_data: Dict from FinancialStatement.data (balance_sheet).
                          Keys: 'asset', 'debt', 'equity'.
                          Values in billion_vnd.
            current_price: Latest stock close price in VND per share.
            shares_outstanding: Number of shares (from stocks.issue_shares).

        Returns:
            Dict with keys: pe_ratio, pb_ratio, eps, roe, roa, de_ratio,
            plus raw values: revenue, net_profit, total_assets, total_equity,
            total_debt, book_value_per_share, market_cap, shares_outstanding,
            current_price.
        """
        share_holder_income = income_data.get("share_holder_income", 0.0) or 0.0
        revenue = income_data.get("revenue", 0.0) or 0.0
        net_profit = income_data.get("net_profit", 0.0) or 0.0
        total_assets = balance_data.get("asset", 0.0) or 0.0
        total_debt = balance_data.get("debt", 0.0) or 0.0
        equity = balance_data.get("equity", 0.0) or 0.0

        # Market cap in billion VND
        market_cap = current_price * shares_outstanding / 1e9 if shares_outstanding else None

        # P/E = market_cap / share_holder_income
        pe_ratio = None
        if market_cap and share_holder_income and share_holder_income > 0:
            pe_ratio = round(market_cap / share_holder_income, 2)

        # P/B = market_cap / equity
        pb_ratio = None
        if market_cap and equity and equity > 0:
            pb_ratio = round(market_cap / equity, 2)

        # EPS = share_holder_income (billion VND) * 1e9 / shares_outstanding → VND/share
        eps = None
        if shares_outstanding and shares_outstanding > 0:
            eps = round(share_holder_income * 1e9 / shares_outstanding, 2)

        # ROE = share_holder_income / equity * 100
        roe = None
        if equity and equity > 0:
            roe = round(share_holder_income / equity * 100, 2)

        # ROA = share_holder_income / total_assets * 100
        roa = None
        if total_assets and total_assets > 0:
            roa = round(share_holder_income / total_assets * 100, 2)

        # D/E = debt / equity (negative equity → None)
        de_ratio = None
        if equity and equity > 0 and total_debt is not None:
            de_ratio = round(total_debt / equity, 2)

        # Book value per share = equity (billion) * 1e9 / shares
        bvps = None
        if shares_outstanding and shares_outstanding > 0 and equity:
            bvps = round(equity * 1e9 / shares_outstanding, 2)

        return {
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "eps": eps,
            "roe": roe,
            "roa": roa,
            "de_ratio": de_ratio,
            # Raw values
            "revenue": revenue,
            "net_profit": net_profit,
            "total_assets": total_assets,
            "total_equity": equity,
            "total_debt": total_debt,
            "book_value_per_share": bvps,
            "market_cap": round(market_cap, 2) if market_cap else None,
            "shares_outstanding": int(shares_outstanding) if shares_outstanding else None,
            "current_price": current_price,
        }

    def compute_growth(
        self,
        current_revenue: float,
        previous_revenue: float,
        current_profit: float,
        previous_profit: float,
    ) -> dict:
        """Compute QoQ or YoY growth rates (FUND-02).

        Growth = (current - previous) / abs(previous) * 100

        Args:
            current_revenue: Current period revenue (billion_vnd).
            previous_revenue: Previous period revenue (billion_vnd).
            current_profit: Current period net profit (billion_vnd).
            previous_profit: Previous period net profit (billion_vnd).

        Returns:
            Dict with revenue_qoq and profit_qoq as percentage values.
            None if previous = 0.
        """
        rev_growth = None
        if previous_revenue and abs(previous_revenue) > 0:
            rev_growth = round(
                (current_revenue - previous_revenue) / abs(previous_revenue) * 100, 2
            )

        profit_growth = None
        if previous_profit and abs(previous_profit) > 0:
            profit_growth = round(
                (current_profit - previous_profit) / abs(previous_profit) * 100, 2
            )

        return {
            "revenue_qoq": rev_growth,
            "profit_qoq": profit_growth,
        }

    def compute_ttm(
        self, quarterly_data: list[dict], metric: str
    ) -> float | None:
        """Compute Trailing Twelve Months value by summing last 4 quarters.

        Args:
            quarterly_data: List of 4 dicts (one per quarter), each with the metric key.
            metric: Key name to sum (e.g., 'revenue', 'share_holder_income').

        Returns:
            Sum of 4 quarters, or None if < 4 quarters available.
        """
        if len(quarterly_data) < 4:
            return None

        values = []
        for q in quarterly_data[-4:]:
            val = q.get(metric)
            if val is None:
                return None
            values.append(float(val))

        return sum(values)

    def to_ratio_row(
        self,
        symbol: str,
        year: int,
        period: str,
        ratios: dict,
        growth_qoq: dict | None = None,
        growth_yoy: dict | None = None,
    ) -> dict:
        """Map computed ratios and growth to FinancialRatio model columns.

        Args:
            symbol: Stock ticker.
            year: Fiscal year.
            period: 'Q1'..'Q4' or 'TTM'.
            ratios: Dict from compute_ratios().
            growth_qoq: Dict from compute_growth() for QoQ.
            growth_yoy: Dict from compute_growth() for YoY.

        Returns:
            Dict ready for RatioRepository.bulk_upsert().
        """
        row = {
            "symbol": symbol,
            "year": year,
            "period": period,
            **ratios,
            "computed_at": datetime.now(UTC),
        }

        if growth_qoq:
            row["revenue_qoq"] = growth_qoq.get("revenue_qoq")
            row["profit_qoq"] = growth_qoq.get("profit_qoq")

        if growth_yoy:
            row["revenue_yoy"] = growth_yoy.get("revenue_qoq")  # reused key name
            row["profit_yoy"] = growth_yoy.get("profit_qoq")

        return row
