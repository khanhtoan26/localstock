"""LLM prompt templates for financial analysis.

Per D-03: Structured JSON output via Ollama format parameter.
Per T-03-01: System prompt constrains LLM to only classify sentiment.
Article text is truncated to prevent prompt injection via long content.
"""

SENTIMENT_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.

Nhiệm vụ: Đọc bài viết tài chính và phân loại sentiment (tâm lý thị trường) đối với mã cổ phiếu được chỉ định.

Quy tắc:
1. Chỉ phân tích sentiment DỰA TRÊN NỘI DUNG BÀI VIẾT. Không suy luận ngoài bài viết.
2. sentiment: "positive" (tích cực cho giá cổ phiếu), "negative" (tiêu cực), "neutral" (trung tính/không liên quan).
3. score: 0.0 (hoàn toàn tiêu cực) đến 1.0 (hoàn toàn tích cực). 0.5 = trung tính.
4. reason: Giải thích ngắn gọn bằng tiếng Việt (1-2 câu) tại sao bạn phân loại như vậy.
5. Nếu bài viết KHÔNG liên quan đến mã cổ phiếu được chỉ định, trả về sentiment="neutral", score=0.5.

Ví dụ sentiment:
- "VNM doanh thu tăng 15% so với cùng kỳ" → positive, score=0.8
- "HPG bị phạt thuế chống bán phá giá" → negative, score=0.2
- "Thị trường biến động mạnh trong phiên hôm nay" → neutral, score=0.5"""

REPORT_USER_TEMPLATE = """📊 THÔNG TIN CỔ PHIẾU: {symbol} - {company_name}
Ngành: {industry} | Giá đóng cửa: {close_price}
Điểm tổng hợp: {total_score}/100 (Hạng {grade})

📈 PHÂN TÍCH KỸ THUẬT (Điểm: {technical_score}/100)
RSI(14): {rsi_14} | MACD Histogram: {macd_histogram}
Xu hướng: {trend_direction} (Strength: {trend_strength})

💰 PHÂN TÍCH CƠ BẢN (Điểm: {fundamental_score}/100)
P/E: {pe_ratio} | P/B: {pb_ratio} | ROE: {roe}
D/E: {debt_to_equity} | Tăng trưởng DT: {revenue_growth}

📰 TÂM LÝ THỊ TRƯỜNG (Điểm: {sentiment_score}/100)
{sentiment_summary}

🌐 BỐI CẢNH VĨ MÔ (Điểm: {macro_score}/100)
{macro_conditions}

⏰ DỰ ĐOÁN XU HƯỚNG T+3
Hướng: {t3_direction} | Độ tin cậy: {t3_confidence}
Lý do: {t3_reasons}
{t3_warning}

Hãy viết báo cáo phân tích chi tiết dựa trên dữ liệu trên."""
