"""T+3 trend prediction logic for Vietnamese stock market.

Per T3-01: Predicts 3-day trend direction based on technical indicator signals.
Per T3-02: Always includes T+3 settlement warning for swing trade context.

The T+3 rule in Vietnam means stocks bought today can only be sold after 3 working days.
This prediction helps assess whether the trend is strong enough to hold through T+3.
"""

T3_WARNING = (
    "⚠️ CẢNH BÁO T+3: Cổ phiếu mua hôm nay chỉ có thể bán sau 3 ngày làm việc. "
    "Hãy đảm bảo xu hướng đủ mạnh để giữ vị thế trong ít nhất 3 phiên giao dịch."
)


def predict_3day_trend(indicator_data: dict) -> dict:
    """Predict 3-day trend direction based on technical signals.

    Aggregates 5 signal types, each contributing +1 (bullish) or -1 (bearish):
    1. RSI momentum: recovering (30-50) vs overbought (>70)
    2. MACD histogram: positive vs negative
    3. Trend + strength (ADX): strong uptrend vs strong downtrend
    4. Support/resistance ratio: upside potential vs downside risk
    5. Volume confirmation: high volume + uptrend

    Args:
        indicator_data: Dict with keys from TechnicalIndicator + StockPrice:
            rsi_14, macd_histogram, trend_direction, trend_strength,
            nearest_support, nearest_resistance, close, relative_volume, volume_trend.
            Any key may be missing or None.

    Returns:
        Dict with:
            direction: "bullish", "bearish", or "neutral"
            confidence: "high", "medium", or "low"
            reasons: list of Vietnamese explanation strings
            t3_warning: T+3 settlement warning string
    """
    signals = 0
    reasons: list[str] = []

    # 1. RSI momentum
    rsi = indicator_data.get("rsi_14")
    if rsi is not None:
        if 30 < rsi < 50:
            signals += 1
            reasons.append(f"RSI = {rsi:.1f} đang trong vùng phục hồi (30-50), tín hiệu tích cực")
        elif rsi > 70:
            signals -= 1
            reasons.append(f"RSI = {rsi:.1f} đang trong vùng quá mua (>70), rủi ro điều chỉnh")

    # 2. MACD histogram
    macd_h = indicator_data.get("macd_histogram")
    if macd_h is not None:
        if macd_h > 0:
            signals += 1
            reasons.append(f"MACD histogram = {macd_h:.3f} dương, xu hướng tăng đang mạnh lên")
        elif macd_h < 0:
            signals -= 1
            reasons.append(f"MACD histogram = {macd_h:.3f} âm, xu hướng giảm đang chiếm ưu thế")

    # 3. Trend direction + strength (ADX proxy via trend_strength)
    trend = indicator_data.get("trend_direction")
    adx = indicator_data.get("trend_strength")
    if trend is not None and adx is not None:
        if trend == "uptrend" and adx > 25:
            signals += 1
            reasons.append(f"Xu hướng tăng mạnh (ADX = {adx:.1f} > 25)")
        elif trend == "downtrend" and adx > 25:
            signals -= 1
            reasons.append(f"Xu hướng giảm mạnh (ADX = {adx:.1f} > 25)")

    # 4. Support/resistance ratio
    support = indicator_data.get("nearest_support")
    resistance = indicator_data.get("nearest_resistance")
    close = indicator_data.get("close")
    if support is not None and resistance is not None and close is not None:
        upside = resistance - close
        downside = close - support
        if downside > 0 and upside > downside * 2:
            signals += 1
            reasons.append(
                f"Tỷ lệ hỗ trợ/kháng cự thuận lợi: upside ({upside:.0f}) > 2× downside ({downside:.0f})"
            )
        elif upside > 0 and downside > upside * 2:
            signals -= 1
            reasons.append(
                f"Tỷ lệ hỗ trợ/kháng cự bất lợi: downside ({downside:.0f}) > 2× upside ({upside:.0f})"
            )

    # 5. Volume confirmation
    rel_vol = indicator_data.get("relative_volume")
    if rel_vol is not None and trend is not None:
        if rel_vol > 1.5 and trend == "uptrend":
            signals += 1
            reasons.append(
                f"Khối lượng giao dịch cao (relative_volume = {rel_vol:.1f}x) xác nhận xu hướng tăng"
            )
        elif rel_vol > 1.5 and trend == "downtrend":
            signals -= 1
            reasons.append(
                f"Khối lượng giao dịch cao (relative_volume = {rel_vol:.1f}x) xác nhận xu hướng giảm"
            )

    # Determine direction
    if signals >= 2:
        direction = "bullish"
    elif signals <= -2:
        direction = "bearish"
    else:
        direction = "neutral"

    # Determine confidence
    abs_signals = abs(signals)
    if abs_signals >= 3:
        confidence = "high"
    elif abs_signals >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "direction": direction,
        "confidence": confidence,
        "reasons": reasons,
        "t3_warning": T3_WARNING,
    }
