"""Telegram message formatters for stock notifications (NOTI-01, NOTI-02, SCOR-05).

All formatters produce HTML strings for Telegram's HTML parse mode.
Per D-01: Vietnamese language, emoji indicators, concise format.
Per Research Pattern 4: Top 10 in digest (not 20), concise per-stock entries.
"""

from datetime import date


def format_daily_digest(
    top_stocks: list[dict],
    score_changes: list[dict] | None = None,
    rotation: dict | None = None,
    digest_date: date | None = None,
) -> str:
    """Format daily digest message with top stocks, changes, and rotation.

    Args:
        top_stocks: List of dicts with keys: symbol, total_score, grade,
                    rank, recommendation (optional).
        score_changes: List of score change dicts (from detect_score_changes).
        rotation: Sector rotation summary dict (from SectorService.get_rotation_summary).
        digest_date: Date for the digest. Defaults to today.

    Returns:
        HTML-formatted message string.
    """
    d = digest_date or date.today()
    lines = [f"📊 <b>LocalStock Daily Digest — {d.strftime('%d/%m/%Y')}</b>"]
    lines.append("")

    # Top stocks
    if top_stocks:
        lines.append("🏆 <b>Top Gợi ý mua:</b>")
        for i, stock in enumerate(top_stocks[:10], 1):
            grade = stock.get("grade", "?")
            score = stock.get("total_score", 0)
            symbol = stock.get("symbol", "???")
            rec = stock.get("recommendation", "")
            rec_text = f" | {rec}" if rec else ""
            lines.append(f"  {i}. <b>{symbol}</b> ({grade}) — {score:.1f} điểm{rec_text}")
    else:
        lines.append("ℹ️ Chưa có dữ liệu xếp hạng.")

    # Score changes
    if score_changes:
        lines.append("")
        lines.append("⚠️ <b>Thay đổi lớn ({} mã):</b>".format(len(score_changes)))
        for change in score_changes[:10]:
            arrow = "📈" if change["direction"] == "up" else "📉"
            lines.append(
                f"  {arrow} <b>{change['symbol']}</b>: "
                f"{change['previous_score']} → {change['current_score']} "
                f"({'+' if change['delta'] > 0 else ''}{change['delta']})"
            )

    # Sector rotation
    if rotation and (rotation.get("inflow") or rotation.get("outflow")):
        lines.append("")
        lines.append("🔄 <b>Sector Rotation:</b>")
        if rotation.get("inflow"):
            inflow_names = ", ".join(
                f"{r['group_name']} ↑" for r in rotation["inflow"][:5]
            )
            lines.append(f"  Dòng tiền vào: {inflow_names}")
        if rotation.get("outflow"):
            outflow_names = ", ".join(
                f"{r['group_name']} ↓" for r in rotation["outflow"][:5]
            )
            lines.append(f"  Dòng tiền ra: {outflow_names}")

    return "\n".join(lines)


def format_score_alerts(changes: list[dict], alert_date: date | None = None) -> str:
    """Format special alert message for significant score changes (NOTI-02).

    Args:
        changes: List of score change dicts from detect_score_changes.
        alert_date: Date of the alert. Defaults to today.

    Returns:
        HTML-formatted alert message.
    """
    d = alert_date or date.today()
    lines = [f"🚨 <b>LocalStock Score Alert — {d.strftime('%d/%m/%Y')}</b>"]
    lines.append("")
    lines.append(f"Phát hiện <b>{len(changes)}</b> mã có thay đổi điểm lớn:")
    lines.append("")

    for change in changes:
        arrow = "📈" if change["direction"] == "up" else "📉"
        delta_sign = "+" if change["delta"] > 0 else ""
        lines.append(
            f"{arrow} <b>{change['symbol']}</b> "
            f"({change['previous_grade']}→{change['current_grade']})"
        )
        lines.append(
            f"   Điểm: {change['previous_score']} → {change['current_score']} "
            f"(<b>{delta_sign}{change['delta']}</b>)"
        )
        lines.append("")

    return "\n".join(lines)


def format_sector_rotation(rotation: dict) -> str:
    """Format sector rotation detailed message (SCOR-05 display).

    Args:
        rotation: Sector rotation summary dict from SectorService.get_rotation_summary.

    Returns:
        HTML-formatted sector rotation message.
    """
    d = rotation.get("date", "N/A")
    lines = [f"🔄 <b>Sector Rotation — {d}</b>"]
    lines.append("")

    if rotation.get("inflow"):
        lines.append("💰 <b>Dòng tiền vào:</b>")
        for sector in rotation["inflow"]:
            change = sector["avg_score_change"]
            lines.append(
                f"  ▲ {sector['group_name']} — "
                f"Điểm TB: {sector['avg_score']:.1f} "
                f"(+{change:.1f}) | {sector['stock_count']} mã"
            )
        lines.append("")

    if rotation.get("outflow"):
        lines.append("📤 <b>Dòng tiền ra:</b>")
        for sector in rotation["outflow"]:
            change = sector["avg_score_change"]
            lines.append(
                f"  ▼ {sector['group_name']} — "
                f"Điểm TB: {sector['avg_score']:.1f} "
                f"({change:.1f}) | {sector['stock_count']} mã"
            )
        lines.append("")

    if not rotation.get("inflow") and not rotation.get("outflow"):
        lines.append("ℹ️ Không phát hiện dòng tiền luân chuyển đáng kể.")

    return "\n".join(lines)
