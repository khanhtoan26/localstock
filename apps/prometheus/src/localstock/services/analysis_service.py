"""Analysis pipeline orchestrator — runs technical + fundamental analysis.

Coordinates TechnicalAnalyzer, FundamentalAnalyzer, IndustryAnalyzer
with their respective repositories to compute and store analysis results
for all HOSE stocks.

Architecture per Research section 8:
1. Load prices from DB (batch)
2. Compute indicators per symbol (CPU-bound, sequential)
3. Bulk upsert results (async)
4. Compute financial ratios
5. Compute industry averages
"""

from datetime import UTC, datetime

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.analysis.fundamental import FundamentalAnalyzer
from localstock.analysis.industry import (
    IndustryAnalyzer,
    VN_INDUSTRY_GROUPS,
    map_icb_to_group,
)
from localstock.analysis.technical import TechnicalAnalyzer
from localstock.analysis.trend import (
    compute_pivot_points,
    detect_trend,
    find_support_resistance,
)
from localstock.db.models import FinancialStatement, Stock, StockPrice
from localstock.db.repositories.indicator_repo import IndicatorRepository
from localstock.db.repositories.industry_repo import IndustryRepository
from localstock.db.repositories.price_repo import PriceRepository
from localstock.db.repositories.ratio_repo import RatioRepository
from localstock.db.repositories.stock_repo import StockRepository


def _normalize_income(raw: dict) -> dict:
    """Map VCI income statement keys to simplified keys (values in Bn VND)."""
    to_bn = 1e9
    return {
        "revenue": (raw.get("Revenue (Bn. VND)") or raw.get("Net Sales") or 0) / to_bn,
        "net_profit": (raw.get("Net Profit For the Year") or 0) / to_bn,
        "share_holder_income": (
            raw.get("Attributable to parent company")
            or raw.get("Attribute to parent company (Bn. VND)")
            or 0
        ) / to_bn,
    }


def _normalize_balance(raw: dict) -> dict:
    """Map VCI balance sheet keys to simplified keys (values in Bn VND)."""
    to_bn = 1e9
    return {
        "asset": (raw.get("TOTAL ASSETS (Bn. VND)") or 0) / to_bn,
        "debt": (raw.get("LIABILITIES (Bn. VND)") or 0) / to_bn,
        "equity": (raw.get("OWNER'S EQUITY(Bn.VND)") or 0) / to_bn,
    }


class AnalysisService:
    """Orchestrates the full analysis pipeline for HOSE stocks.

    Usage:
        service = AnalysisService(session)
        result = await service.run_full()         # all stocks
        result = await service.run_single("VNM")  # one stock
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)
        self.price_repo = PriceRepository(session)
        self.indicator_repo = IndicatorRepository(session)
        self.ratio_repo = RatioRepository(session)
        self.industry_repo = IndustryRepository(session)
        self.tech_analyzer = TechnicalAnalyzer()
        self.fund_analyzer = FundamentalAnalyzer()
        self.industry_analyzer = IndustryAnalyzer()

    async def run_full(self) -> dict:
        """Run full analysis pipeline for all HOSE stocks.

        Steps:
        1. Seed industry groups
        2. Map stocks to industries
        3. Run technical analysis for all symbols
        4. Run fundamental analysis for all symbols
        5. Compute industry averages

        Returns:
            Summary dict with counts and errors.
        """
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "technical_success": 0,
            "technical_failed": 0,
            "fundamental_success": 0,
            "fundamental_failed": 0,
            "errors": [],
        }

        # Step 1: Seed industry groups
        await self.seed_industry_groups()

        # Step 2: Get all HOSE symbols
        symbols = await self.stock_repo.get_all_hose_symbols()
        logger.info(f"Starting analysis for {len(symbols)} symbols")

        # Step 3: Map stocks to industries
        await self.map_stock_industries(symbols)

        # Step 4: Technical analysis
        for symbol in symbols:
            try:
                await self._run_technical(symbol)
                summary["technical_success"] += 1
            except Exception as e:
                summary["technical_failed"] += 1
                summary["errors"].append(f"tech:{symbol}:{e}")
                logger.warning(f"Technical analysis failed for {symbol}: {e}")

        # Step 5: Fundamental analysis
        for symbol in symbols:
            try:
                await self._run_fundamental(symbol)
                summary["fundamental_success"] += 1
            except Exception as e:
                summary["fundamental_failed"] += 1
                summary["errors"].append(f"fund:{symbol}:{e}")
                logger.warning(f"Fundamental analysis failed for {symbol}: {e}")

        # Step 6: Compute industry averages
        try:
            await self._compute_all_industry_averages()
        except Exception as e:
            summary["errors"].append(f"industry_avg:{e}")
            logger.error(f"Industry averages failed: {e}")

        summary["completed_at"] = datetime.now(UTC).isoformat()
        logger.info(
            f"Analysis complete: tech={summary['technical_success']}/{len(symbols)}, "
            f"fund={summary['fundamental_success']}/{len(symbols)}"
        )
        return summary

    async def run_single(self, symbol: str) -> dict:
        """Run analysis for a single symbol.

        Args:
            symbol: Stock ticker (e.g., 'VNM').

        Returns:
            Dict with technical and fundamental results.
        """
        result = {"symbol": symbol, "status": "completed", "errors": []}

        try:
            await self._run_technical(symbol)
            result["technical"] = "ok"
        except Exception as e:
            result["errors"].append(f"technical: {e}")

        try:
            await self._run_fundamental(symbol)
            result["fundamental"] = "ok"
        except Exception as e:
            result["errors"].append(f"fundamental: {e}")

        if result["errors"]:
            result["status"] = "partial"
        return result

    async def seed_industry_groups(self) -> int:
        """Seed VN industry group definitions into the database.

        Returns:
            Count of groups upserted.
        """
        groups = self.industry_analyzer.get_group_definitions()
        count = await self.industry_repo.upsert_groups(groups)
        logger.info(f"Seeded {count} industry groups")
        return count

    async def map_stock_industries(self, symbols: list[str] | None = None) -> int:
        """Map stocks to VN industry groups based on ICB3 data.

        Args:
            symbols: List of symbols to map. If None, maps all HOSE stocks.

        Returns:
            Count of mappings created.
        """
        if symbols is None:
            symbols = await self.stock_repo.get_all_hose_symbols()

        # Load stock ICB data
        stmt = select(Stock.symbol, Stock.industry_icb3).where(
            Stock.symbol.in_(symbols)
        )
        result = await self.session.execute(stmt)
        stocks = result.all()

        mappings = []
        for symbol, icb3 in stocks:
            group_code = map_icb_to_group(icb3)
            mappings.append({"symbol": symbol, "group_code": group_code})

        count = await self.industry_repo.upsert_mappings(mappings)
        logger.info(f"Mapped {count} stocks to industry groups")
        return count

    def analyze_technical_single(
        self, symbol: str, ohlcv_df: pd.DataFrame
    ) -> dict:
        """Compute all technical indicators for a single symbol (CPU-bound).

        This is a synchronous method — call from async context.

        Args:
            symbol: Stock ticker.
            ohlcv_df: OHLCV DataFrame for this symbol.

        Returns:
            Dict ready for IndicatorRepository.bulk_upsert().
        """
        # Compute indicators
        indicators_df = self.tech_analyzer.compute_indicators(ohlcv_df)

        # Volume analysis
        vol = self.tech_analyzer.compute_volume_analysis(ohlcv_df)

        # Trend detection (needs indicator columns)
        trend_data = None
        if not indicators_df.empty and len(indicators_df) > 0:
            latest = indicators_df.iloc[-1]
            # Add close price for trend detection
            latest_with_close = latest.copy()
            if "close" not in latest_with_close.index:
                latest_with_close["close"] = ohlcv_df["close"].iloc[-1]
            trend_data = detect_trend(latest_with_close)

        # Support/Resistance
        sr_data = None
        if len(ohlcv_df) >= 3:
            # Pivot points from previous day
            prev = ohlcv_df.iloc[-2]
            sr_data = compute_pivot_points(
                high=float(prev["high"]),
                low=float(prev["low"]),
                close=float(prev["close"]),
            )
            # Nearest S/R from peak/trough detection
            prices = ohlcv_df["close"].tolist()
            order = min(20, len(prices) // 4) if len(prices) > 10 else 2
            if order >= 2:
                nearest_s, nearest_r = find_support_resistance(prices, order=order)
                sr_data["nearest_support"] = nearest_s
                sr_data["nearest_resistance"] = nearest_r

        return self.tech_analyzer.to_indicator_row(
            symbol=symbol,
            ohlcv_df=ohlcv_df,
            indicators_df=indicators_df,
            volume_analysis=vol,
            trend_data=trend_data,
            sr_data=sr_data,
        )

    def analyze_fundamental_single(
        self,
        symbol: str,
        year: int,
        period: str,
        income_data: dict,
        balance_data: dict,
        current_price: float,
        shares_outstanding: int | float,
        prev_income: dict | None = None,
        yoy_income: dict | None = None,
    ) -> dict:
        """Compute financial ratios for a single symbol/period.

        Args:
            symbol: Stock ticker.
            year: Fiscal year.
            period: 'Q1'..'Q4'.
            income_data: Income statement data dict.
            balance_data: Balance sheet data dict.
            current_price: Latest close price (VND).
            shares_outstanding: From stocks.issue_shares.
            prev_income: Previous quarter income data (for QoQ growth).
            yoy_income: Same quarter last year income data (for YoY growth).

        Returns:
            Dict ready for RatioRepository.bulk_upsert().
        """
        ratios = self.fund_analyzer.compute_ratios(
            income_data=income_data,
            balance_data=balance_data,
            current_price=current_price,
            shares_outstanding=shares_outstanding,
        )

        growth_qoq = None
        if prev_income:
            growth_qoq = self.fund_analyzer.compute_growth(
                current_revenue=income_data.get("revenue", 0) or 0,
                previous_revenue=prev_income.get("revenue", 0) or 0,
                current_profit=income_data.get("share_holder_income", 0) or 0,
                previous_profit=prev_income.get("share_holder_income", 0) or 0,
            )

        growth_yoy = None
        if yoy_income:
            growth_yoy = self.fund_analyzer.compute_growth(
                current_revenue=income_data.get("revenue", 0) or 0,
                previous_revenue=yoy_income.get("revenue", 0) or 0,
                current_profit=income_data.get("share_holder_income", 0) or 0,
                previous_profit=yoy_income.get("share_holder_income", 0) or 0,
            )

        return self.fund_analyzer.to_ratio_row(
            symbol=symbol,
            year=year,
            period=period,
            ratios=ratios,
            growth_qoq=growth_qoq,
            growth_yoy=growth_yoy,
        )

    async def _run_technical(self, symbol: str) -> None:
        """Run technical analysis for one symbol and store results."""
        prices = await self.price_repo.get_prices(symbol)
        if not prices:
            logger.debug(f"No price data for {symbol}, skipping technical analysis")
            return

        ohlcv_df = pd.DataFrame([
            {
                "date": p.date,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ])

        row = self.analyze_technical_single(symbol, ohlcv_df)
        if row:
            await self.indicator_repo.bulk_upsert([row])

    async def _run_fundamental(self, symbol: str) -> None:
        """Run fundamental analysis for one symbol and store results."""
        # Get latest price for current_price
        prices = await self.price_repo.get_prices(symbol)
        if not prices:
            return
        current_price = prices[-1].close

        # Get shares outstanding (fallback: derive from charter_capital / 10,000 VND par)
        stmt = select(Stock.issue_shares, Stock.charter_capital).where(
            Stock.symbol == symbol
        )
        result = await self.session.execute(stmt)
        row_stock = result.one_or_none()
        if not row_stock:
            logger.debug(f"Stock {symbol} not found, skipping fundamental")
            return
        shares = row_stock[0] or (
            row_stock[1] / 10_000 if row_stock[1] else None
        )
        if not shares:
            logger.debug(f"No issue_shares for {symbol}, skipping fundamental")
            return

        # Get latest financial statements
        stmt_income = (
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.report_type == "income_statement",
            )
            .order_by(FinancialStatement.year.desc(), FinancialStatement.period.desc())
            .limit(5)  # get extra for growth calculation
        )
        result = await self.session.execute(stmt_income)
        income_stmts = list(result.scalars().all())

        stmt_balance = (
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.report_type == "balance_sheet",
            )
            .order_by(FinancialStatement.year.desc(), FinancialStatement.period.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt_balance)
        balance_stmt = result.scalar_one_or_none()

        if not income_stmts or not balance_stmt:
            logger.debug(f"No financial data for {symbol}, skipping fundamental")
            return

        latest_income = income_stmts[0]

        # Previous quarter income (for QoQ growth)
        prev_income = income_stmts[1].data if len(income_stmts) > 1 else None

        # YoY: find same quarter last year
        yoy_income = None
        for stmt in income_stmts[1:]:
            if (
                stmt.period == latest_income.period
                and stmt.year == latest_income.year - 1
            ):
                yoy_income = stmt.data
                break

        row = self.analyze_fundamental_single(
            symbol=symbol,
            year=latest_income.year,
            period=latest_income.period,
            income_data=_normalize_income(latest_income.data),
            balance_data=_normalize_balance(balance_stmt.data),
            current_price=current_price,
            shares_outstanding=shares,
            prev_income=_normalize_income(prev_income) if prev_income else None,
            yoy_income=_normalize_income(yoy_income) if yoy_income else None,
        )
        if row:
            await self.ratio_repo.bulk_upsert([row])

    async def _compute_all_industry_averages(self) -> None:
        """Compute industry averages for all groups."""
        groups = await self.industry_repo.get_all_groups()

        for group in groups:
            group_code = group.group_code
            symbols = await self.industry_repo.get_symbols_by_group(group_code)
            if not symbols:
                continue

            # Get latest ratios for each symbol in the group
            group_ratios = []
            for symbol in symbols:
                ratio = await self.ratio_repo.get_latest(symbol)
                if ratio:
                    group_ratios.append({
                        "pe_ratio": ratio.pe_ratio,
                        "pb_ratio": ratio.pb_ratio,
                        "roe": ratio.roe,
                        "roa": ratio.roa,
                        "de_ratio": ratio.de_ratio,
                        "revenue_yoy": ratio.revenue_yoy,
                        "profit_yoy": ratio.profit_yoy,
                    })

            if not group_ratios:
                continue

            # Find year/period from the first symbol that actually has ratio data
            first_ratio = None
            for sym in symbols:
                first_ratio = await self.ratio_repo.get_latest(sym)
                if first_ratio:
                    break
            if not first_ratio:
                continue

            avg = self.industry_analyzer.compute_industry_averages(
                group_code=group_code,
                year=first_ratio.year,
                period=first_ratio.period,
                ratios=group_ratios,
            )
            await self.industry_repo.upsert_averages([avg])

        logger.info("Industry averages computed for all groups")
