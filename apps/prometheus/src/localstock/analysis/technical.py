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

    def compute_candlestick_patterns(self, df: pd.DataFrame) -> dict:
        """Detect 5 candlestick patterns on the latest bar (SIGNAL-01).

        Uses pandas-ta native CDL functions for doji and inside_bar (no TA-Lib required).
        Uses pure OHLC math for hammer, shooting_star, and engulfing.

        Args:
            df: OHLCV DataFrame (latest date last row). Minimum 2 rows required.

        Returns:
            Dict with keys: doji (bool), inside_bar (bool), hammer (bool),
            shooting_star (bool), engulfing_detected (bool), engulfing_direction (str | None).
            Returns all-False dict if df has < 2 rows.
        """
        _empty = {
            "doji": False,
            "inside_bar": False,
            "hammer": False,
            "shooting_star": False,
            "engulfing_detected": False,
            "engulfing_direction": None,
        }

        if df.empty or len(df) < 2:
            return _empty

        result = {}

        # 1. Doji — pandas-ta native (no TA-Lib required)
        # cdl_doji uses 10-bar rolling H-L average; returns None on very short DataFrames
        try:
            doji_series = ta.cdl_doji(df["open"], df["high"], df["low"], df["close"])
            result["doji"] = bool(doji_series.iloc[-1] == 100.0) if doji_series is not None else False
        except Exception as e:
            logger.warning(f"cdl_doji failed: {e}")
            result["doji"] = False

        # 2. Inside bar — pandas-ta native (no TA-Lib required)
        try:
            inside_series = ta.cdl_inside(df["open"], df["high"], df["low"], df["close"])
            result["inside_bar"] = bool(inside_series.iloc[-1] == 100.0) if inside_series is not None else False
        except Exception as e:
            logger.warning(f"cdl_inside failed: {e}")
            result["inside_bar"] = False

        # 3–5. Pure OHLC math (TA-Lib NOT available in this environment)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        result["hammer"] = _is_hammer(curr)
        result["shooting_star"] = _is_shooting_star(curr)
        engulfing = _detect_engulfing(prev, curr)
        result["engulfing_detected"] = engulfing is not None
        result["engulfing_direction"] = engulfing  # "bullish" | "bearish" | None

        return result

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


def _is_hammer(row: pd.Series) -> bool:
    """Hammer: small body in upper half, long lower shadow, tiny upper shadow.

    Criteria (canonical TA formula):
    - Body <= 30% of candle range
    - Lower shadow >= 2x body
    - Upper shadow <= 10% of candle range
    """
    body = abs(row["close"] - row["open"])
    candle_range = row["high"] - row["low"]
    if candle_range == 0:
        return False
    lower_shadow = min(row["open"], row["close"]) - row["low"]
    upper_shadow = row["high"] - max(row["open"], row["close"])
    return (
        body <= 0.3 * candle_range
        and lower_shadow >= 2.0 * body
        and upper_shadow <= 0.1 * candle_range
    )


def _is_shooting_star(row: pd.Series) -> bool:
    """Shooting star: small body at bottom, long upper shadow, tiny lower shadow.

    Criteria (canonical TA formula):
    - Body <= 30% of candle range
    - Upper shadow >= 2x body
    - Lower shadow <= 10% of candle range
    """
    body = abs(row["close"] - row["open"])
    candle_range = row["high"] - row["low"]
    if candle_range == 0:
        return False
    lower_shadow = min(row["open"], row["close"]) - row["low"]
    upper_shadow = row["high"] - max(row["open"], row["close"])
    return (
        body <= 0.3 * candle_range
        and upper_shadow >= 2.0 * body
        and lower_shadow <= 0.1 * candle_range
    )


def _detect_engulfing(prev: pd.Series, curr: pd.Series) -> str | None:
    """Detect bullish or bearish engulfing pattern (2-bar pure OHLC math).

    Returns: 'bullish', 'bearish', or None.
    """
    # Bullish engulfing: prev bearish, curr bullish, curr body engulfs prev body
    prev_bearish = prev["close"] < prev["open"]
    curr_bullish = curr["close"] > curr["open"]
    if prev_bearish and curr_bullish:
        if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
            return "bullish"

    # Bearish engulfing: prev bullish, curr bearish, curr body engulfs prev body
    prev_bullish = prev["close"] > prev["open"]
    curr_bearish = curr["close"] < curr["open"]
    if prev_bullish and curr_bearish:
        if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
            return "bearish"

    return None
