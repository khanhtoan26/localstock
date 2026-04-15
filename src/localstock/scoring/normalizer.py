"""Scoring normalizers — convert raw indicators to 0-100 scores.

Two main functions normalize raw technical indicators and financial ratios
into comparable 0-100 scores using multi-component scoring with explicit thresholds.

Per SCOR-01: Each dimension produces a 0-100 score.
Per Anti-Pattern Pitfall 6: Never mix raw indicator scales directly.
"""


def normalize_technical_score(indicator_data: dict) -> float:
    """Normalize technical indicators to a 0-100 score.

    Scoring components (each 0-20 points, total 0-100):
    - RSI positioning (0-20)
    - Trend alignment (0-20)
    - MACD momentum (0-20)
    - Bollinger position (0-20)
    - Volume confirmation (0-20)

    Args:
        indicator_data: Dict with keys matching TechnicalIndicator column names.
            Expected keys: rsi_14, trend_direction, trend_strength,
            macd_histogram, bb_upper, bb_lower, bb_middle, close,
            relative_volume, volume_trend.

    Returns:
        Float 0-100 score. Returns 0.0 if all values are None.
    """
    if not indicator_data:
        return 0.0

    # Check if all relevant values are None
    relevant_keys = [
        "rsi_14", "trend_direction", "macd_histogram",
        "bb_upper", "relative_volume",
    ]
    if all(indicator_data.get(k) is None for k in relevant_keys):
        return 0.0

    rsi = indicator_data.get("rsi_14")
    trend_direction = indicator_data.get("trend_direction")
    trend_strength = indicator_data.get("trend_strength")
    macd_histogram = indicator_data.get("macd_histogram")
    bb_upper = indicator_data.get("bb_upper")
    bb_lower = indicator_data.get("bb_lower")
    bb_middle = indicator_data.get("bb_middle")
    close = indicator_data.get("close")
    relative_volume = indicator_data.get("relative_volume")
    volume_trend = indicator_data.get("volume_trend")

    score = 0.0

    # --- RSI positioning (0-20) ---
    if rsi is not None:
        if rsi < 30:
            score += 18
        elif rsi < 45:
            score += 15
        elif rsi <= 55:
            score += 10
        elif rsi <= 70:
            score += 5
        else:
            score += 2

    # --- Trend alignment (0-20) ---
    if trend_direction is not None:
        if trend_direction == "uptrend":
            trend_pts = 18
        elif trend_direction == "sideways":
            trend_pts = 10
        else:  # downtrend
            trend_pts = 3
        # Bonus for strong trend
        if trend_strength is not None and trend_strength > 50:
            trend_pts += 2
        score += min(trend_pts, 20)

    # --- MACD momentum (0-20) ---
    if macd_histogram is not None:
        if macd_histogram > 0:
            score += 14  # positive histogram
        elif macd_histogram == 0:
            score += 10
        else:
            score += 4  # negative histogram

    # --- Bollinger position (0-20) ---
    if close is not None and bb_upper is not None and bb_lower is not None:
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            # Position relative to BB bands
            bb_position = (close - bb_lower) / bb_range  # 0 = at lower, 1 = at upper

            if close < bb_lower * 1.02:
                score += 18  # near or below lower band
            elif bb_position < 0.35:
                score += 14  # lower half
            elif bb_position < 0.65:
                score += 10  # mid
            elif bb_position < 0.85:
                score += 6   # upper half
            else:
                score += 3   # near upper band

    # --- Volume confirmation (0-20) ---
    if relative_volume is not None:
        if relative_volume > 1.5 and trend_direction == "uptrend":
            vol_pts = 18
        elif relative_volume > 1.0:
            vol_pts = 14
        elif relative_volume >= 0.5:
            vol_pts = 10
        else:
            vol_pts = 5
        # Bonus for increasing volume in uptrend
        if volume_trend == "increasing" and trend_direction == "uptrend":
            vol_pts += 2
        score += min(vol_pts, 20)

    return min(score, 100.0)


def normalize_fundamental_score(ratio_data: dict) -> float:
    """Normalize financial ratios to a 0-100 score.

    Scoring components (each 0-25 points, total 0-100):
    - Valuation — P/E (0-25)
    - Profitability — ROE + ROA (0-25)
    - Growth — profit_yoy + revenue_yoy (0-25)
    - Financial health — D/E (0-25)

    Args:
        ratio_data: Dict with keys matching FinancialRatio column names.
            Expected keys: pe_ratio, roe, roa, profit_yoy, revenue_yoy, de_ratio.

    Returns:
        Float 0-100 score. Returns 0.0 if all values are None.
    """
    if not ratio_data:
        return 0.0

    relevant_keys = ["pe_ratio", "roe", "profit_yoy", "de_ratio"]
    if all(ratio_data.get(k) is None for k in relevant_keys):
        return 0.0

    pe = ratio_data.get("pe_ratio")
    roe = ratio_data.get("roe")
    roa = ratio_data.get("roa")
    profit_yoy = ratio_data.get("profit_yoy")
    revenue_yoy = ratio_data.get("revenue_yoy")
    de = ratio_data.get("de_ratio")

    score = 0.0

    # --- Valuation: P/E (0-25) ---
    if pe is not None and pe > 0:
        if pe < 10:
            score += 22
        elif pe < 15:
            score += 18
        elif pe <= 25:
            score += 12
        elif pe <= 40:
            score += 6
        else:
            score += 2
    else:
        # None or negative → neutral (can't evaluate)
        score += 10

    # --- Profitability: ROE + ROA (0-25) ---
    prof_pts = 0.0
    if roe is not None:
        if roe > 20:
            prof_pts = 22
        elif roe > 15:
            prof_pts = 18
        elif roe > 10:
            prof_pts = 14
        elif roe > 5:
            prof_pts = 8
        else:
            prof_pts = 3
    else:
        prof_pts = 10  # neutral if unknown

    # ROA adjustment
    if roa is not None:
        if roa > 10:
            prof_pts += 3
        elif roa < 3:
            prof_pts -= 3
    score += max(0, min(prof_pts, 25))

    # --- Growth: profit_yoy + revenue_yoy (0-25) ---
    growth_pts = 0.0
    if profit_yoy is not None:
        if profit_yoy > 30:
            growth_pts = 22
        elif profit_yoy > 15:
            growth_pts = 18
        elif profit_yoy >= 0:
            growth_pts = 12
        elif profit_yoy >= -15:
            growth_pts = 6
        else:
            growth_pts = 2
    else:
        growth_pts = 10  # neutral if unknown

    # Revenue secondary adjustment
    if revenue_yoy is not None and profit_yoy is not None:
        if revenue_yoy > 0 and profit_yoy > 0:
            growth_pts += 3  # both growing
        elif revenue_yoy > 0 and profit_yoy < 0:
            growth_pts -= 2  # revenue up but profit down
    score += max(0, min(growth_pts, 25))

    # --- Financial health: D/E (0-25) ---
    if de is not None:
        if de < 0.5:
            score += 22
        elif de < 1.0:
            score += 18
        elif de <= 2.0:
            score += 12
        elif de <= 3.0:
            score += 6
        else:
            score += 2
    else:
        score += 12  # neutral if unknown

    return min(score, 100.0)


def normalize_sentiment_score(sentiment_avg: float) -> float:
    """Normalize sentiment average to 0-100 scale.

    Simple linear scaling: input 0.0-1.0 maps to output 0.0-100.0.

    Args:
        sentiment_avg: Average sentiment score on 0.0-1.0 scale.

    Returns:
        Float 0.0-100.0.
    """
    return sentiment_avg * 100.0
