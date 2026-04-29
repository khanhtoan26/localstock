"""Report data assembly and prompt building.

Per REPT-02: ReportDataBuilder assembles all stock data into prompt-ready dict.
StockReport model is defined in ai.client (single source of truth for Ollama format schema).
"""

from loguru import logger

from localstock.ai.prompts import REPORT_USER_TEMPLATE


def _safe(value, fallback: str = "N/A") -> str:
    """Return value as string, or fallback if None."""
    if value is None:
        return fallback
    return str(value)


def _safe_float(value, fmt: str = ".1f", fallback: str = "N/A") -> str:
    """Format float value, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):{fmt}}"
    except (ValueError, TypeError):
        return fallback


def _safe_pct(value, fallback: str = "N/A") -> str:
    """Format value as percentage, or return fallback if None."""
    if value is None:
        return fallback
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return fallback


def _format_candlestick(patterns: dict | None) -> str:
    """Format candlestick pattern dict to compact prompt string.

    Args:
        patterns: Dict from compute_candlestick_patterns() with bool values.

    Returns:
        Comma-separated detected pattern names, or "không phát hiện" if none,
        or "N/A" if input is None.
    """
    if not patterns:
        return "N/A"
    detected = [k for k, v in patterns.items() if v and k != "engulfing_direction"]
    if not detected:
        return "không phát hiện"
    if "engulfing_detected" in detected and patterns.get("engulfing_direction"):
        detected = [
            f"engulfing ({patterns['engulfing_direction']})" if k == "engulfing_detected" else k
            for k in detected
        ]
    return ", ".join(detected)


def _format_volume_divergence(div: dict | None) -> str:
    """Format volume divergence dict to compact prompt string.

    Args:
        div: Dict from compute_volume_divergence() with signal/value/indicator keys.

    Returns:
        Formatted string like "bullish (MFI=72.3)" or "N/A" if None.
    """
    if not div:
        return "N/A"
    return f"{div['signal']} ({div['indicator']}={div['value']})"


def _format_sector_momentum(mom: dict | None) -> str:
    """Format sector momentum dict to compact prompt string.

    Args:
        mom: Dict from compute_sector_momentum() with label/score_change/group_code keys.

    Returns:
        Formatted string like "mild_inflow (+0.5, nhóm BKS)" or "N/A" if None.
    """
    if not mom:
        return "N/A"
    sign = "+" if mom["score_change"] >= 0 else ""
    return f"{mom['label']} ({sign}{mom['score_change']}, nhóm {mom['group_code']})"


def compute_entry_zone(
    nearest_support: float | None,
    bb_upper: float | None,
    close: float | None,
    price_history_count: int,
) -> tuple[float | None, float | None]:
    """Compute entry zone as (lower, upper) price range.

    Per D-02: lower = nearest_support, upper = bb_upper.
    Per D-03: fallback to close ± 2% when < 40 price history rows
    or when both indicators are None.
    """
    if close is None:
        return None, None

    if price_history_count < 40 or (nearest_support is None and bb_upper is None):
        return round(close * 0.98, 1), round(close * 1.02, 1)

    lower = nearest_support if nearest_support is not None else round(close * 0.98, 1)
    upper = bb_upper if bb_upper is not None else round(close * 1.02, 1)

    if lower >= upper:
        lower, upper = round(close * 0.98, 1), round(close * 1.02, 1)

    return round(lower, 1), round(upper, 1)


def compute_stop_loss(support_2: float | None, close: float | None) -> float | None:
    """Stop-loss = max(support_2, close × 0.93). HOSE ±7% daily limit aware."""
    if close is None:
        return None
    floor = close * 0.93
    if support_2 is not None:
        return round(max(support_2, floor), 1)
    return round(floor, 1)


def compute_target_price(nearest_resistance: float | None, close: float | None) -> float | None:
    """Target = nearest_resistance if available, else close × 1.10."""
    if close is None:
        return None
    if nearest_resistance is not None:
        return round(nearest_resistance, 1)
    return round(close * 1.10, 1)


def enforce_price_ordering(report) -> None:
    """Enforce strict ordering stop_loss < entry_price < target_price.

    Per D-09: validation requires strict ordering. The deterministic price
    computations (compute_entry_zone, compute_stop_loss, compute_target_price)
    are independent of each other and can produce ties or near-ties after
    rounding to 1 decimal place — e.g. HPG with entry midpoint 27.48 and
    support_2 27.52 both round to 27.5, which then fails strict ordering and
    causes _validate_price_levels to null all three prices (silent Trade Plan
    drop on the frontend).

    This helper nudges deterministic ties apart by 0.1 (≈100 VND) so the
    downstream validation passes. Mutates ``report`` in place. Safe to call
    when prices are partially or fully None.
    """
    nudge = 0.1
    ep = report.entry_price
    sl = report.stop_loss
    tp = report.target_price

    if ep is not None and sl is not None and sl >= ep:
        report.stop_loss = round(ep - nudge, 1)
        logger.debug(
            f"enforce_price_ordering: nudged stop_loss {sl} -> {report.stop_loss} "
            f"(was >= entry_price {ep})"
        )
    if ep is not None and tp is not None and tp <= ep:
        report.target_price = round(ep + nudge, 1)
        logger.debug(
            f"enforce_price_ordering: nudged target_price {tp} -> {report.target_price} "
            f"(was <= entry_price {ep})"
        )


def detect_signal_conflict(
    tech_score: float | None,
    fund_score: float | None,
) -> str | None:
    """Detect and format signal conflict for prompt injection.

    Returns Vietnamese conflict description when |gap| > 25, else None.
    """
    if tech_score is None or fund_score is None:
        return None
    gap = tech_score - fund_score
    if abs(gap) <= 25:
        return None
    direction = "kỹ thuật > cơ bản" if gap > 0 else "cơ bản > kỹ thuật"
    return (
        f"Xung đột tín hiệu: Tech={tech_score:.0f}, Fund={fund_score:.0f}, "
        f"gap={'+' if gap > 0 else ''}{gap:.0f} ({direction})"
    )


RISK_RATING_MAP: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "cao": "high",
    "Cao": "high",
    "CAO": "high",
    "trung bình": "medium",
    "Trung bình": "medium",
    "TRUNG BÌNH": "medium",
    "thấp": "low",
    "Thấp": "low",
    "THẤP": "low",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


def _normalize_risk_rating(report):
    """Normalize risk_rating to canonical English lowercase per D-04.

    Maps Vietnamese variants (cao, trung bình, thấp) and casing variants
    to one of: "high", "medium", "low". Unknown values are set to None.

    Args:
        report: StockReport instance (mutated in place).

    Returns:
        The same StockReport with normalized risk_rating.
    """
    if report.risk_rating is not None:
        normalized = RISK_RATING_MAP.get(report.risk_rating.strip())
        if normalized is None:
            logger.warning(
                f"Unknown risk_rating '{report.risk_rating}' — setting to None"
            )
        report.risk_rating = normalized
    return report


def _validate_price_levels(report, current_close: float):
    """Validate LLM-generated price levels post-generation per D-09.

    Two checks:
    1. Price ordering: stop_loss < entry_price < target_price
    2. Range: all non-None price fields within ±30% of current_close

    On failure: nulls only the 3 price fields (entry_price, stop_loss,
    target_price). Preserves risk_rating, catalyst, signal_conflicts per D-10.

    Args:
        report: StockReport instance (mutated in place).
        current_close: Current closing price for range validation.

    Returns:
        The same StockReport with potentially nulled price fields.
    """
    ep = report.entry_price
    sl = report.stop_loss
    tp = report.target_price

    def _null_prices():
        logger.warning(
            f"Price validation failed: "
            f"stop_loss={sl}, entry={ep}, target={tp}, close={current_close}"
        )
        report.entry_price = None
        report.stop_loss = None
        report.target_price = None

    # Check 1: Price ordering (only when all three are present)
    if ep is not None and sl is not None and tp is not None:
        # Auto-correct simple stop_loss/entry_price inversion
        if sl > ep and ep < tp and sl < tp:
            logger.info(
                f"Auto-correcting inverted stop_loss/entry_price: "
                f"swapping sl={sl} <-> ep={ep}"
            )
            report.stop_loss, report.entry_price = ep, sl
            sl, ep = ep, sl
        # Auto-correct entry_price/target_price inversion
        if sl < ep and ep > tp and sl < tp:
            logger.info(
                f"Auto-correcting inverted entry_price/target_price: "
                f"swapping ep={ep} <-> tp={tp}"
            )
            report.entry_price, report.target_price = tp, ep
            ep, tp = tp, ep
        if not (sl < ep < tp):
            _null_prices()
            return report

    # Check 2: Range — each non-None price within ±30% of close
    if current_close and current_close > 0:
        for field_name in ("entry_price", "stop_loss", "target_price"):
            val = getattr(report, field_name)
            if val is not None:
                if abs(val - current_close) / current_close > 0.30:
                    _null_prices()
                    return report

    return report


def build_report_prompt(data: dict) -> str:
    """Format stock data into a report generation prompt.

    Takes a dict with all stock data fields and formats using REPORT_USER_TEMPLATE.
    Per T-04-06: Numeric data formatted as values, not raw text.

    Args:
        data: Dict with all prompt template placeholder keys.

    Returns:
        Formatted prompt string ready for LLM consumption.
    """
    # Defaults for Phase 20 keys (backward compat for callers without them)
    defaults = {
        "entry_zone_lower": "N/A",
        "entry_zone_upper": "N/A",
        "stop_loss_level": "N/A",
        "target_price_level": "N/A",
        "signal_conflict_text": "Không có xung đột tín hiệu",
        "catalyst_news": "Không có tin tức gần đây",
        "catalyst_score_delta": "N/A",
    }
    # Build safe copy with fallbacks for None values
    safe_data = {**defaults}
    for key, value in data.items():
        safe_data[key] = _safe(value) if value is None else value
    return REPORT_USER_TEMPLATE.format(**safe_data)


class ReportDataBuilder:
    """Assembles all stock data into a dict for prompt template injection.

    Gathers data from multiple sources (scoring, indicators, ratios, sentiment,
    macro, T+3 prediction, stock info) and produces a flat dict with all keys
    needed by REPORT_USER_TEMPLATE.
    """

    def build(
        self,
        symbol: str,
        score_data: dict,
        indicator_data: dict,
        ratio_data: dict,
        sentiment_data: dict,
        macro_data: dict,
        t3_data: dict,
        stock_info: dict,
        signals_data: dict | None = None,
        price_levels: dict | None = None,
        conflict_data: dict | None = None,
        catalyst_data: dict | None = None,
    ) -> dict:
        """Assemble all stock data into prompt-ready dict.

        Args:
            symbol: Stock ticker (e.g., "VNM").
            score_data: Composite scoring results (total, grade, dimension scores).
            indicator_data: Technical indicators (RSI, MACD, trend, etc.).
            ratio_data: Fundamental ratios (P/E, P/B, ROE, etc.).
            sentiment_data: Sentiment analysis summary.
            macro_data: Macro conditions summary.
            t3_data: T+3 prediction results.
            stock_info: Company name, industry, close price.
            signals_data: Phase 18 signal data (candlestick, volume, sector).

        Returns:
            Dict with all keys needed for REPORT_USER_TEMPLATE.
            None values replaced with "N/A" or "Không có dữ liệu".
        """
        return {
            # Stock info
            "symbol": symbol,
            "company_name": _safe(stock_info.get("company_name"), "Không rõ"),
            "industry": _safe(stock_info.get("industry"), "Không rõ"),
            "close_price": _safe(stock_info.get("close_price"), "N/A"),
            # Composite scores
            "total_score": _safe_float(score_data.get("total"), ".1f"),
            "grade": _safe(score_data.get("grade")),
            "technical_score": _safe_float(score_data.get("technical"), ".1f"),
            "fundamental_score": _safe_float(score_data.get("fundamental"), ".1f"),
            "sentiment_score": _safe_float(score_data.get("sentiment"), ".1f"),
            "macro_score": _safe_float(score_data.get("macro"), ".1f"),
            # Technical indicators
            "rsi_14": _safe_float(indicator_data.get("rsi_14"), ".1f"),
            "macd_histogram": _safe_float(indicator_data.get("macd_histogram"), ".3f"),
            "trend_direction": _safe(indicator_data.get("trend_direction")),
            "trend_strength": _safe_float(indicator_data.get("trend_strength"), ".1f"),
            # Fundamental ratios
            "pe_ratio": _safe_float(ratio_data.get("pe_ratio"), ".1f"),
            "pb_ratio": _safe_float(ratio_data.get("pb_ratio"), ".1f"),
            "roe": _safe_pct(ratio_data.get("roe")),
            "debt_to_equity": _safe_float(ratio_data.get("debt_to_equity"), ".2f"),
            "revenue_growth": _safe_pct(ratio_data.get("revenue_growth")),
            # Sentiment
            "sentiment_summary": _safe(
                sentiment_data.get("summary"), "Không có dữ liệu sentiment"
            ),
            # Macro
            "macro_conditions": _safe(
                macro_data.get("conditions"), "Không có dữ liệu vĩ mô"
            ),
            # T+3 prediction
            "t3_direction": _safe(t3_data.get("direction"), "neutral"),
            "t3_confidence": _safe(t3_data.get("confidence"), "low"),
            "t3_reasons": _safe(
                ", ".join(t3_data["reasons"]) if t3_data.get("reasons") else None,
                "Không đủ dữ liệu dự đoán",
            ),
            "t3_warning": _safe(
                t3_data.get("t3_warning"),
                "⚠️ CẢNH BÁO T+3: Cổ phiếu mua hôm nay chỉ có thể bán sau 3 ngày làm việc.",
            ),
            # S/R anchors (from indicator_data)
            "nearest_support": _safe_float(indicator_data.get("nearest_support"), ".0f"),
            "nearest_resistance": _safe_float(indicator_data.get("nearest_resistance"), ".0f"),
            "pivot_point": _safe_float(indicator_data.get("pivot_point"), ".0f"),
            "support_1": _safe_float(indicator_data.get("support_1"), ".0f"),
            "support_2": _safe_float(indicator_data.get("support_2"), ".0f"),
            "resistance_1": _safe_float(indicator_data.get("resistance_1"), ".0f"),
            "resistance_2": _safe_float(indicator_data.get("resistance_2"), ".0f"),
            # Phase 18 signals (from signals_data)
            "candlestick_patterns": _format_candlestick(
                (signals_data or {}).get("candlestick_patterns")
            ),
            "volume_divergence": _format_volume_divergence(
                (signals_data or {}).get("volume_divergence")
            ),
            "sector_momentum": _format_sector_momentum(
                (signals_data or {}).get("sector_momentum")
            ),
            # Phase 20: Pre-computed price levels
            "entry_zone_lower": _safe_float((price_levels or {}).get("entry_lower"), ".0f"),
            "entry_zone_upper": _safe_float((price_levels or {}).get("entry_upper"), ".0f"),
            "stop_loss_level": _safe_float((price_levels or {}).get("stop_loss"), ".0f"),
            "target_price_level": _safe_float((price_levels or {}).get("target_price"), ".0f"),
            # Phase 20: Signal conflict
            "signal_conflict_text": _safe(
                (conflict_data or {}).get("conflict_text"),
                "Không có xung đột tín hiệu",
            ),
            # Phase 20: Catalyst
            "catalyst_news": _safe(
                (catalyst_data or {}).get("news_summary"),
                "Không có tin tức gần đây",
            ),
            "catalyst_score_delta": _safe(
                (catalyst_data or {}).get("score_delta_text"),
                "N/A",
            ),
        }
