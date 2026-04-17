"""Technical indicator computation using pandas-ta (per D-02).

Computes all required indicators (TECH-01) and volume analysis (TECH-02)
for a single stock's OHLCV DataFrame.
"""

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pandas_ta as ta
from loguru import logger


class TechnicalAnalyzer:
    """Computes technical indicators from OHLCV data using pandas-ta.

    Per D-01: Minimum set (SMA, EMA, RSI, MACD, BB) + additional
    (Stochastic, ADX, OBV) for richer analysis.
    Per D-02: Uses pandas-ta library for all calculations.

    Individual indicator calls (not Strategy) for per-indicator error handling
    as recommended by research.
    """

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all technical indicators on an OHLCV DataFrame.

        Args:
            df: DataFrame with columns: date, open, high, low, close, volume.
                Must have at least 200 rows for SMA(200) to be meaningful.

        Returns:
            Copy of input DataFrame with indicator columns appended.
            Column names follow pandas-ta convention (SMA_20, RSI_14, etc.)
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            result[col] = pd.to_numeric(result[col], errors="coerce")

        # Moving Averages (TECH-01)
        indicators = [
            ("sma", {"length": 20}),
            ("sma", {"length": 50}),
            ("sma", {"length": 200}),
            ("ema", {"length": 12}),
            ("ema", {"length": 26}),
            # Momentum
            ("rsi", {"length": 14}),
            ("macd", {"fast": 12, "slow": 26, "signal": 9}),
            # Bollinger Bands
            ("bbands", {"length": 20, "std": 2}),
            # Additional (per D-01)
            ("stoch", {}),
            ("adx", {}),
            ("obv", {}),
        ]

        for name, params in indicators:
            try:
                method = getattr(result.ta, name)
                method(append=True, **params)
            except Exception as e:
                logger.warning(f"Failed to compute {name}({params}): {e}")

        return result

    def compute_volume_analysis(self, df: pd.DataFrame) -> dict:
        """Compute volume analysis metrics (TECH-02).

        Args:
            df: OHLCV DataFrame (latest date should be last row).

        Returns:
            Dict with keys: avg_volume_20 (int), relative_volume (float),
            volume_trend (str: 'increasing'/'decreasing'/'stable').
        """
        if df.empty or len(df) < 20:
            return {
                "avg_volume_20": None,
                "relative_volume": None,
                "volume_trend": None,
            }

        volumes = df["volume"].astype(float)
        avg_20 = int(volumes.tail(20).mean())
        current_vol = int(volumes.iloc[-1])
        relative = current_vol / avg_20 if avg_20 > 0 else 0.0

        # Volume trend: compare recent 5-day avg vs 20-day avg
        avg_5 = volumes.tail(5).mean()
        if avg_5 > avg_20 * 1.2:
            trend = "increasing"
        elif avg_5 < avg_20 * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "avg_volume_20": avg_20,
            "relative_volume": round(relative, 4),
            "volume_trend": trend,
        }

    def to_indicator_row(
        self,
        symbol: str,
        ohlcv_df: pd.DataFrame,
        indicators_df: pd.DataFrame,
        volume_analysis: dict,
        trend_data: dict | None = None,
        sr_data: dict | None = None,
    ) -> dict:
        """Map computed indicators to TechnicalIndicator model column names.

        Takes the last row from indicators_df and maps pandas-ta column names
        to the flat model column names.

        Args:
            symbol: Stock ticker.
            ohlcv_df: Original OHLCV DataFrame (for date extraction).
            indicators_df: DataFrame with pandas-ta indicator columns.
            volume_analysis: Dict from compute_volume_analysis().
            trend_data: Optional dict with trend_direction, trend_strength.
            sr_data: Optional dict with pivot points and S/R levels.

        Returns:
            Dict ready for IndicatorRepository.bulk_upsert().
        """
        if indicators_df.empty:
            return {}

        last = indicators_df.iloc[-1]
        last_date = ohlcv_df["date"].iloc[-1]
        if isinstance(last_date, pd.Timestamp):
            last_date = last_date.date()

        def safe_float(val):
            """Convert to float, returning None for NaN/None."""
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        def safe_int(val):
            """Convert to int, returning None for NaN/None."""
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return None
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        row = {
            "symbol": symbol,
            "date": last_date,
            # Moving Averages
            "sma_20": safe_float(last.get("SMA_20")),
            "sma_50": safe_float(last.get("SMA_50")),
            "sma_200": safe_float(last.get("SMA_200")),
            "ema_12": safe_float(last.get("EMA_12")),
            "ema_26": safe_float(last.get("EMA_26")),
            # Momentum
            "rsi_14": safe_float(last.get("RSI_14")),
            "macd": safe_float(last.get("MACD_12_26_9")),
            "macd_signal": safe_float(last.get("MACDs_12_26_9")),
            "macd_histogram": safe_float(last.get("MACDh_12_26_9")),
            # Bollinger Bands — pandas-ta uses double suffix: BBL_20_2.0_2.0
            "bb_upper": safe_float(last.get("BBU_20_2.0_2.0")),
            "bb_middle": safe_float(last.get("BBM_20_2.0_2.0")),
            "bb_lower": safe_float(last.get("BBL_20_2.0_2.0")),
            # Additional
            "stoch_k": safe_float(last.get("STOCHk_14_3_3")),
            "stoch_d": safe_float(last.get("STOCHd_14_3_3")),
            "adx": safe_float(last.get("ADX_14")),
            "obv": safe_int(last.get("OBV")),
            # Volume analysis
            "avg_volume_20": volume_analysis.get("avg_volume_20"),
            "relative_volume": volume_analysis.get("relative_volume"),
            "volume_trend": volume_analysis.get("volume_trend"),
            # Trend (filled by trend.py, passed in)
            "trend_direction": trend_data.get("trend_direction") if trend_data else None,
            "trend_strength": trend_data.get("trend_strength") if trend_data else None,
            # S/R (filled by trend.py, passed in)
            "pivot_point": sr_data.get("pivot_point") if sr_data else None,
            "support_1": sr_data.get("support_1") if sr_data else None,
            "support_2": sr_data.get("support_2") if sr_data else None,
            "resistance_1": sr_data.get("resistance_1") if sr_data else None,
            "resistance_2": sr_data.get("resistance_2") if sr_data else None,
            "nearest_support": sr_data.get("nearest_support") if sr_data else None,
            "nearest_resistance": sr_data.get("nearest_resistance") if sr_data else None,
            # Metadata
            "computed_at": datetime.now(UTC),
        }

        return row
