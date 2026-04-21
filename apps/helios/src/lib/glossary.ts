// Glossary Data Module — Single source of truth for all learn pages and Phase 10 linking
// Contains typed entries for technical indicators, fundamental ratios, and macro concepts

export type GlossaryCategory = "technical" | "fundamental" | "macro";

export interface GlossaryEntry {
  id: string;                    // URL-safe slug: "rsi", "pe-ratio", "cpi"
  term: string;                  // Vietnamese name: "Chỉ số sức mạnh tương đối (RSI)"
  termEn: string;                // English name: "Relative Strength Index"
  aliases: string[];             // Phase 10 matching: ["RSI", "chỉ số RSI", "Relative Strength Index"]
  category: GlossaryCategory;
  shortDef: string;              // 1-sentence Vietnamese definition
  content: string;               // Full markdown article (Vietnamese, English terms in parens)
  formula?: string;              // Optional: plain text formula
}

// === TECHNICAL INDICATORS ===

const technicalEntries: Record<string, GlossaryEntry> = {
  rsi: {
    id: "rsi",
    term: "Chỉ số sức mạnh tương đối (RSI)",
    termEn: "Relative Strength Index",
    aliases: ["RSI", "chỉ số RSI", "Relative Strength Index", "chỉ số sức mạnh tương đối"],
    category: "technical",
    shortDef: "Chỉ báo dao động đo lường tốc độ và biên độ thay đổi giá, giúp xác định trạng thái quá mua hoặc quá bán.",
    formula: "RSI = 100 - (100 / (1 + RS)), RS = Avg Gain / Avg Loss (14 phiên)",
    content: `## Định nghĩa

RSI (Relative Strength Index) là chỉ báo dao động (oscillator) được phát triển bởi J. Welles Wilder vào năm 1978. RSI đo lường tốc độ và biên độ thay đổi giá trong một khoảng thời gian nhất định, thường là 14 phiên giao dịch. Giá trị RSI dao động từ 0 đến 100.

## Cách tính

RSI được tính qua hai bước:
1. Tính RS (Relative Strength) = Trung bình phiên tăng / Trung bình phiên giảm trong 14 phiên
2. RSI = 100 - (100 / (1 + RS))

Trung bình phiên tăng (Average Gain) là tổng các phiên giá tăng chia cho 14. Trung bình phiên giảm (Average Loss) là tổng các phiên giá giảm chia cho 14.

## Cách đọc / Diễn giải

- **RSI > 70:** Vùng quá mua (overbought) — giá có thể đã tăng quá nhanh và sắp điều chỉnh giảm
- **RSI < 30:** Vùng quá bán (oversold) — giá có thể đã giảm quá sâu và sắp hồi phục
- **RSI = 50:** Mức trung tính — không có tín hiệu rõ ràng
- **Phân kỳ (Divergence):** Khi giá tạo đỉnh mới nhưng RSI không tạo đỉnh mới → tín hiệu đảo chiều giảm

## Ví dụ thực tế

Cổ phiếu VNM có RSI(14) = 78, nằm trong vùng quá mua. Điều này gợi ý rằng VNM đã tăng mạnh trong 14 phiên gần đây và có khả năng điều chỉnh ngắn hạn. Tuy nhiên, trong xu hướng tăng mạnh, RSI có thể duy trì trên 70 khá lâu.

## Lưu ý

- RSI hoạt động tốt nhất trong thị trường sideway (đi ngang). Trong xu hướng mạnh, RSI có thể ở vùng quá mua/quá bán rất lâu mà giá vẫn tiếp tục đi theo xu hướng.
- Nên kết hợp RSI với các chỉ báo khác như MACD, Bollinger Bands để xác nhận tín hiệu.
- Mức 70/30 là mặc định, nhưng có thể điều chỉnh thành 80/20 cho thị trường biến động mạnh.`,
  },

  macd: {
    id: "macd",
    term: "Đường MACD",
    termEn: "Moving Average Convergence Divergence",
    aliases: ["MACD", "hội tụ phân kỳ", "Moving Average Convergence Divergence"],
    category: "technical",
    shortDef: "Chỉ báo xu hướng kết hợp động lượng, đo khoảng cách giữa hai đường trung bình hàm mũ để xác định xu hướng và tín hiệu mua bán.",
    formula: "MACD = EMA(12) - EMA(26), Signal = EMA(9) của MACD",
    content: `## Định nghĩa

MACD (Moving Average Convergence Divergence) là chỉ báo xu hướng và động lượng được phát triển bởi Gerald Appel. MACD đo lường mối quan hệ giữa hai đường trung bình hàm mũ (EMA) — cụ thể là sự hội tụ và phân kỳ giữa EMA ngắn hạn và EMA dài hạn.

## Cách tính

MACD bao gồm ba thành phần:
1. **Đường MACD** = EMA(12) - EMA(26)
2. **Đường Signal** = EMA(9) của đường MACD
3. **Histogram** = Đường MACD - Đường Signal

Khi EMA(12) cắt lên trên EMA(26), MACD dương → xu hướng tăng. Khi EMA(12) cắt xuống dưới EMA(26), MACD âm → xu hướng giảm.

## Cách đọc / Diễn giải

- **MACD cắt lên trên Signal:** Tín hiệu mua (bullish crossover)
- **MACD cắt xuống dưới Signal:** Tín hiệu bán (bearish crossover)
- **Histogram tăng dần:** Động lượng tăng đang mạnh lên
- **Histogram giảm dần:** Động lượng tăng đang yếu đi
- **Phân kỳ giá/MACD:** Tín hiệu đảo chiều mạnh

## Ví dụ thực tế

Cổ phiếu FPT đang có MACD = 1.5 và Signal = 0.8, histogram = 0.7 (dương và tăng dần). Điều này cho thấy xu hướng tăng đang mạnh. Nếu histogram bắt đầu thu hẹp (ví dụ từ 0.7 xuống 0.4), đó là dấu hiệu động lượng tăng đang suy yếu.

## Lưu ý

- MACD là chỉ báo trễ (lagging indicator) vì dựa trên đường trung bình — tín hiệu đến chậm hơn so với giá thực tế.
- Hiệu quả nhất khi kết hợp với RSI hoặc volume để xác nhận.
- Trong thị trường sideway, MACD có thể tạo nhiều tín hiệu giả (whipsaws).`,
  },

  sma: {
    id: "sma",
    term: "Đường trung bình đơn giản (SMA)",
    termEn: "Simple Moving Average",
    aliases: ["SMA", "đường trung bình", "Simple Moving Average", "MA"],
    category: "technical",
    shortDef: "Đường trung bình cộng của giá đóng cửa trong một khoảng thời gian, giúp làm mượt biến động giá và xác định xu hướng.",
    formula: "SMA(n) = (P1 + P2 + ... + Pn) / n",
    content: `## Định nghĩa

SMA (Simple Moving Average) là đường trung bình đơn giản nhất, tính bằng trung bình cộng giá đóng cửa trong n phiên gần nhất. SMA giúp làm mượt biến động giá ngắn hạn để nhà đầu tư nhận diện xu hướng dài hạn.

## Cách tính

SMA(n) = (P₁ + P₂ + ... + Pₙ) / n

Trong đó Pᵢ là giá đóng cửa phiên thứ i. Ví dụ SMA(20) là trung bình giá 20 phiên gần nhất.

## Cách đọc / Diễn giải

- **Giá > SMA:** Xu hướng tăng — giá đang giao dịch trên mức trung bình
- **Giá < SMA:** Xu hướng giảm — giá đang giao dịch dưới mức trung bình
- **SMA ngắn cắt lên SMA dài (Golden Cross):** Tín hiệu tăng mạnh (ví dụ SMA(50) cắt lên SMA(200))
- **SMA ngắn cắt xuống SMA dài (Death Cross):** Tín hiệu giảm mạnh
- **Các SMA phổ biến:** SMA(20) cho ngắn hạn, SMA(50) cho trung hạn, SMA(200) cho dài hạn

## Ví dụ thực tế

Cổ phiếu HPG có SMA(20) = 28,500 VND, SMA(50) = 27,200 VND, SMA(200) = 25,800 VND. Cả ba SMA đều tăng dần và xếp theo thứ tự SMA(20) > SMA(50) > SMA(200) → xu hướng tăng rõ ràng ở cả ba khung thời gian.

## Lưu ý

- SMA phản ứng chậm với thay đổi giá vì mọi phiên có trọng số bằng nhau.
- Một phiên biến động mạnh bất thường có thể kéo SMA lệch đáng kể.
- Nên dùng EMA thay SMA khi cần phản ứng nhanh hơn với giá gần đây.`,
  },

  ema: {
    id: "ema",
    term: "Đường trung bình hàm mũ (EMA)",
    termEn: "Exponential Moving Average",
    aliases: ["EMA", "trung bình hàm mũ", "Exponential Moving Average"],
    category: "technical",
    shortDef: "Đường trung bình có trọng số cao hơn cho các phiên gần đây, phản ứng nhanh hơn SMA với biến động giá mới nhất.",
    formula: "EMA = Price × k + EMA(previous) × (1 - k), k = 2 / (n + 1)",
    content: `## Định nghĩa

EMA (Exponential Moving Average) là đường trung bình hàm mũ, tương tự SMA nhưng gán trọng số cao hơn cho các phiên giao dịch gần đây. Nhờ vậy, EMA phản ứng nhanh hơn với thay đổi giá mới nhất, giúp bắt tín hiệu sớm hơn.

## Cách tính

EMA được tính đệ quy:
1. EMA đầu tiên = SMA(n) (dùng SMA làm giá trị khởi tạo)
2. Các phiên sau: EMA = Giá × k + EMA(trước) × (1 - k)
3. Hệ số nhân (multiplier): k = 2 / (n + 1)

Với EMA(12): k = 2/13 ≈ 0.1538, nghĩa là phiên gần nhất chiếm ~15.4% trọng số.

## Cách đọc / Diễn giải

- **Giá cắt lên trên EMA:** Tín hiệu tăng ngắn hạn
- **Giá cắt xuống dưới EMA:** Tín hiệu giảm ngắn hạn
- **EMA(12) và EMA(26):** Hai đường EMA này là thành phần chính của MACD
- **EMA phản ứng nhanh hơn SMA:** Phù hợp cho giao dịch ngắn hạn (swing trading)

## Ví dụ thực tế

Cổ phiếu MWG có giá hiện tại 52,000 VND, EMA(12) = 51,200 VND. Giá đang trên EMA(12) → xu hướng ngắn hạn vẫn tích cực. Nếu giá giảm xuống dưới 51,200 → có thể là tín hiệu chuyển xu hướng.

## Lưu ý

- EMA nhạy hơn SMA nên dễ bị "whipsaw" (tín hiệu giả) trong thị trường sideway.
- Dùng EMA ngắn hạn (12, 26) cho giao dịch nhanh, EMA dài hạn (50, 200) cho đầu tư dài hạn.
- EMA(12) và EMA(26) là nền tảng của MACD — hiểu EMA giúp hiểu MACD tốt hơn.`,
  },

  "bollinger-bands": {
    id: "bollinger-bands",
    term: "Dải Bollinger (Bollinger Bands)",
    termEn: "Bollinger Bands",
    aliases: ["Bollinger Bands", "dải Bollinger", "BB", "Bollinger"],
    category: "technical",
    shortDef: "Dải biến động gồm ba đường bao quanh giá, giúp đo lường mức độ biến động và xác định vùng giá quá cao hoặc quá thấp.",
    formula: "Middle = SMA(20), Upper = SMA(20) + 2σ, Lower = SMA(20) - 2σ",
    content: `## Định nghĩa

Bollinger Bands là chỉ báo biến động (volatility) được phát triển bởi John Bollinger vào thập niên 1980. Bao gồm ba đường: dải giữa là SMA(20), dải trên và dải dưới cách dải giữa 2 độ lệch chuẩn (standard deviation). Khoảng cách giữa hai dải phản ánh mức độ biến động của giá.

## Cách tính

1. **Dải giữa (Middle Band)** = SMA(20)
2. **Dải trên (Upper Band)** = SMA(20) + 2 × σ (độ lệch chuẩn 20 phiên)
3. **Dải dưới (Lower Band)** = SMA(20) - 2 × σ

Theo thống kê, khoảng 95% giá sẽ nằm trong phạm vi 2 độ lệch chuẩn.

## Cách đọc / Diễn giải

- **Giá chạm dải trên:** Có thể quá mua — nhưng không nhất thiết là tín hiệu bán
- **Giá chạm dải dưới:** Có thể quá bán — nhưng không nhất thiết là tín hiệu mua
- **Dải co hẹp (Squeeze):** Biến động thấp → thường báo trước một đợt biến động mạnh sắp đến
- **Dải mở rộng:** Biến động đang tăng, xu hướng đang mạnh
- **Bollinger Bounce:** Giá có xu hướng quay về dải giữa

## Ví dụ thực tế

Cổ phiếu TCB có Bollinger Bands co hẹp bất thường trong 10 phiên (dải trên và dải dưới gần nhau). Đây là tín hiệu "Squeeze" — cho thấy TCB sắp có biến động mạnh. Nhà đầu tư nên theo dõi hướng phá vỡ (breakout) để quyết định mua hay bán.

## Lưu ý

- Bollinger Bands không cho biết hướng đi của giá — chỉ cho biết mức độ biến động.
- Nên kết hợp với RSI hoặc MACD để xác định hướng breakout sau Squeeze.
- Trong xu hướng mạnh, giá có thể "đi dọc" dải trên hoặc dải dưới (band walking) mà không đảo chiều.`,
  },

  obv: {
    id: "obv",
    term: "Khối lượng cân bằng (OBV)",
    termEn: "On-Balance Volume",
    aliases: ["OBV", "On-Balance Volume", "khối lượng cân bằng"],
    category: "technical",
    shortDef: "Chỉ báo khối lượng tích lũy dựa trên hướng giá, giúp xác nhận xu hướng và phát hiện phân kỳ giá-khối lượng.",
    formula: "OBV = OBV(trước) ± Volume (+ nếu giá tăng, - nếu giá giảm)",
    content: `## Định nghĩa

OBV (On-Balance Volume) là chỉ báo khối lượng do Joseph Granville phát triển. OBV tích lũy khối lượng giao dịch theo hướng giá — cộng khối lượng khi giá tăng, trừ khối lượng khi giá giảm. Ý tưởng cốt lõi: khối lượng đi trước giá (volume leads price).

## Cách tính

- Nếu giá đóng cửa hôm nay > hôm qua: OBV = OBV(hôm qua) + Volume(hôm nay)
- Nếu giá đóng cửa hôm nay < hôm qua: OBV = OBV(hôm qua) - Volume(hôm nay)
- Nếu giá đóng cửa không đổi: OBV = OBV(hôm qua)

Giá trị tuyệt đối của OBV không quan trọng — xu hướng (tăng/giảm) mới là ý nghĩa.

## Cách đọc / Diễn giải

- **OBV tăng:** Khối lượng mua đang áp đảo → hỗ trợ xu hướng tăng giá
- **OBV giảm:** Khối lượng bán đang áp đảo → hỗ trợ xu hướng giảm giá
- **OBV tăng nhưng giá đi ngang:** Tích lũy (accumulation) — giá có thể sắp tăng
- **OBV giảm nhưng giá đi ngang:** Phân phối (distribution) — giá có thể sắp giảm
- **Phân kỳ OBV/Giá:** Tín hiệu mạnh về sự thay đổi xu hướng sắp tới

## Ví dụ thực tế

Cổ phiếu VIC có giá đi ngang quanh 45,000 VND trong 2 tuần, nhưng OBV liên tục tăng. Đây là tín hiệu tích lũy — các nhà đầu tư lớn đang mua gom cổ phiếu. Khả năng VIC sẽ breakout tăng giá trong thời gian tới.

## Lưu ý

- OBV hiệu quả nhất khi kết hợp với phân tích giá và các chỉ báo xu hướng khác.
- Trên sàn HOSE, khối lượng có thể bị ảnh hưởng bởi giao dịch thỏa thuận (put-through) — làm méo OBV.
- Nên dùng OBV trên khung thời gian ngày (daily) trở lên để giảm nhiễu.`,
  },

  vwap: {
    id: "vwap",
    term: "Giá trung bình theo khối lượng (VWAP)",
    termEn: "Volume Weighted Average Price",
    aliases: ["VWAP", "Volume Weighted Average Price", "giá trung bình theo khối lượng"],
    category: "technical",
    shortDef: "Giá trung bình được tính có trọng số theo khối lượng giao dịch, phản ánh giá 'thực tế' trung bình trong phiên.",
    formula: "VWAP = Σ(Price × Volume) / Σ(Volume)",
    content: `## Định nghĩa

VWAP (Volume Weighted Average Price) là giá trung bình có trọng số theo khối lượng. Khác với SMA (trung bình đơn giản), VWAP tính đến khối lượng giao dịch tại mỗi mức giá, phản ánh mức giá trung bình mà thị trường thực sự giao dịch.

## Cách tính

VWAP = Tổng(Giá × Khối lượng) / Tổng(Khối lượng)

Thông thường sử dụng giá điển hình (Typical Price) = (High + Low + Close) / 3 cho mỗi phiên, nhân với khối lượng phiên đó, rồi chia tổng cho tổng khối lượng tích lũy.

## Cách đọc / Diễn giải

- **Giá > VWAP:** Người mua đang trả giá cao hơn trung bình → xu hướng tăng
- **Giá < VWAP:** Người mua đang trả giá thấp hơn trung bình → xu hướng giảm
- **VWAP là "fair value":** Giá quay về VWAP có thể được coi là cơ hội mua/bán
- **Tổ chức lớn dùng VWAP:** Làm benchmark để đánh giá chất lượng lệnh mua/bán lớn

## Ví dụ thực tế

Trong phiên giao dịch, VNM có VWAP = 72,500 VND, giá hiện tại 73,200 VND. Giá đang cao hơn VWAP → người mua đang chấp nhận trả giá cao hơn trung bình phiên. Nếu giá giảm về 72,500 (VWAP), đó có thể là vùng hỗ trợ tự nhiên.

## Lưu ý

- VWAP thường được reset mỗi phiên (intraday) — khác với SMA/EMA có thể dùng đa khung thời gian.
- Trên sàn HOSE, VWAP đặc biệt hữu ích cho nhà đầu tư tổ chức muốn mua/bán lô lớn.
- Có thể dùng VWAP trên khung tuần/tháng nhưng ít phổ biến hơn.`,
  },

  stochastic: {
    id: "stochastic",
    term: "Stochastic Oscillator",
    termEn: "Stochastic Oscillator",
    aliases: ["Stochastic", "%K", "%D", "Stochastic Oscillator"],
    category: "technical",
    shortDef: "Chỉ báo dao động so sánh giá đóng cửa với phạm vi giá trong một khoảng thời gian, xác định trạng thái quá mua/quá bán.",
    formula: "%K = (Close - Low14) / (High14 - Low14) × 100, %D = SMA(3) của %K",
    content: `## Định nghĩa

Stochastic Oscillator là chỉ báo dao động được phát triển bởi George Lane vào thập niên 1950. Nó so sánh giá đóng cửa hiện tại với phạm vi giá cao nhất và thấp nhất trong 14 phiên gần nhất. Giá trị dao động từ 0 đến 100.

## Cách tính

1. **%K (Fast Stochastic)** = (Giá đóng cửa - Giá thấp nhất 14 phiên) / (Giá cao nhất 14 phiên - Giá thấp nhất 14 phiên) × 100
2. **%D (Slow Stochastic)** = SMA(3) của %K (trung bình 3 phiên của %K)

%K phản ứng nhanh với giá, %D là phiên bản làm mượt hơn.

## Cách đọc / Diễn giải

- **%K > 80:** Vùng quá mua (overbought)
- **%K < 20:** Vùng quá bán (oversold)
- **%K cắt lên trên %D:** Tín hiệu mua (bullish crossover)
- **%K cắt xuống dưới %D:** Tín hiệu bán (bearish crossover)
- **Tín hiệu mạnh nhất:** Crossover xảy ra trong vùng quá mua/quá bán

## Ví dụ thực tế

Cổ phiếu MSN có %K = 15 và %D = 22. Cả hai đều nằm dưới 20 (vùng quá bán). Nếu %K cắt lên trên %D → đây là tín hiệu mua trong vùng quá bán, một trong những tín hiệu mạnh nhất của Stochastic.

## Lưu ý

- Stochastic hoạt động tốt nhất trong thị trường sideway, giống RSI.
- Trong xu hướng mạnh, Stochastic có thể "dính" ở vùng quá mua hoặc quá bán rất lâu.
- Sử dụng phiên bản Slow Stochastic (%D) để giảm tín hiệu giả.`,
  },

  adx: {
    id: "adx",
    term: "Chỉ số xu hướng trung bình (ADX)",
    termEn: "Average Directional Index",
    aliases: ["ADX", "Average Directional Index", "chỉ số xu hướng"],
    category: "technical",
    shortDef: "Chỉ báo đo sức mạnh xu hướng (không phân biệt tăng hay giảm), giúp xác định thị trường đang trending hay sideway.",
    formula: "ADX = SMA(14) của DX, DX = |+DI - -DI| / (+DI + -DI) × 100",
    content: `## Định nghĩa

ADX (Average Directional Index) là chỉ báo đo sức mạnh xu hướng, được phát triển bởi J. Welles Wilder (cùng tác giả RSI). ADX không cho biết hướng xu hướng (tăng hay giảm) — chỉ cho biết xu hướng mạnh hay yếu. Giá trị từ 0 đến 100.

## Cách tính

ADX được tính qua nhiều bước:
1. Tính +DM (Positive Directional Movement) và -DM (Negative Directional Movement)
2. Tính +DI và -DI bằng cách chia +DM/-DM cho ATR rồi × 100
3. DX = |+DI - -DI| / (+DI + -DI) × 100
4. ADX = SMA(14) của DX

## Cách đọc / Diễn giải

- **ADX < 20:** Xu hướng yếu hoặc thị trường sideway → dùng oscillator (RSI, Stochastic)
- **ADX 20-40:** Xu hướng đang hình thành → cân nhắc theo xu hướng
- **ADX > 40:** Xu hướng rất mạnh → dùng chỉ báo xu hướng (MACD, MA)
- **ADX > 50:** Cực kỳ mạnh, hiếm gặp — thường ở đỉnh xu hướng
- **+DI > -DI:** Xu hướng tăng; **-DI > +DI:** Xu hướng giảm

## Ví dụ thực tế

Cổ phiếu ACB có ADX = 35 và +DI > -DI. ADX cho thấy xu hướng tăng đang khá mạnh. Trong trường hợp này, chiến lược mua theo xu hướng (trend following) sẽ hiệu quả hơn chiến lược giao dịch ngược (mean reversion).

## Lưu ý

- ADX trễ (lagging) vì dựa trên trung bình — có thể bắt đầu tăng khi xu hướng đã chạy được một đoạn.
- Dùng ADX để chọn chiến lược: ADX thấp → dùng oscillator, ADX cao → dùng trend following.
- ADX giảm không có nghĩa xu hướng đảo chiều — chỉ là xu hướng đang yếu đi.`,
  },

  atr: {
    id: "atr",
    term: "Phạm vi thực trung bình (ATR)",
    termEn: "Average True Range",
    aliases: ["ATR", "Average True Range", "phạm vi thực"],
    category: "technical",
    shortDef: "Chỉ báo đo mức độ biến động (volatility) trung bình của giá, hữu ích cho việc đặt stop-loss và xác định rủi ro.",
    formula: "ATR = SMA(14) của True Range, TR = max(H-L, |H-Cprev|, |L-Cprev|)",
    content: `## Định nghĩa

ATR (Average True Range) là chỉ báo biến động được phát triển bởi J. Welles Wilder. ATR đo biên độ dao động trung bình của giá trong một khoảng thời gian (thường 14 phiên), tính bằng đơn vị giá (VND, không phải phần trăm).

## Cách tính

1. **True Range (TR)** = Giá trị lớn nhất trong ba giá trị:
   - High - Low (biên độ phiên)
   - |High - Close(hôm trước)| (gap tăng)
   - |Low - Close(hôm trước)| (gap giảm)
2. **ATR** = SMA(14) của True Range (hoặc EMA(14) cho phản ứng nhanh hơn)

## Cách đọc / Diễn giải

- **ATR cao:** Biến động lớn → rủi ro cao hơn nhưng cũng nhiều cơ hội
- **ATR thấp:** Biến động nhỏ → thị trường yên tĩnh, có thể sắp có biến động lớn
- **Đặt Stop-loss:** Dùng bội số ATR: Stop-loss = Giá mua - 2×ATR (phổ biến)
- **Position sizing:** ATR nhỏ → có thể mua nhiều hơn; ATR lớn → mua ít hơn để kiểm soát rủi ro

## Ví dụ thực tế

Cổ phiếu VHM có ATR(14) = 1,200 VND và giá hiện tại 45,000 VND. Biến động trung bình mỗi phiên là 1,200 VND (~2.7%). Nếu đặt stop-loss 2×ATR = 2,400 VND dưới giá mua, stop-loss sẽ ở 42,600 VND. Điều này cho phép giá biến động bình thường mà không bị dính stop-loss.

## Lưu ý

- ATR không cho biết hướng giá — chỉ đo biến động.
- ATR tính bằng đơn vị giá tuyệt đối nên không thể so sánh trực tiếp giữa cổ phiếu giá cao và giá thấp. Dùng ATR% = ATR/Giá × 100 để so sánh.
- ATR đặc biệt hữu ích cho quản lý rủi ro và xác định kích cỡ vị thế (position sizing).`,
  },
};

// === FUNDAMENTAL RATIOS ===

const fundamentalEntries: Record<string, GlossaryEntry> = {
  "pe-ratio": {
    id: "pe-ratio",
    term: "Hệ số giá trên lợi nhuận (P/E)",
    termEn: "Price-to-Earnings Ratio",
    aliases: ["P/E", "PE", "Price-to-Earnings", "hệ số giá trên lợi nhuận"],
    category: "fundamental",
    shortDef: "Hệ số cho biết nhà đầu tư sẵn sàng trả bao nhiêu đồng cho mỗi đồng lợi nhuận của doanh nghiệp.",
    formula: "P/E = Giá cổ phiếu / EPS",
    content: `## Định nghĩa

P/E (Price-to-Earnings Ratio) là hệ số định giá phổ biến nhất, cho biết nhà đầu tư sẵn sàng trả bao nhiêu đồng cho mỗi đồng lợi nhuận trên mỗi cổ phiếu (EPS). P/E phản ánh kỳ vọng tăng trưởng của thị trường đối với doanh nghiệp.

## Cách tính

P/E = Giá cổ phiếu / EPS (Lợi nhuận trên mỗi cổ phiếu)

Có hai loại P/E:
- **Trailing P/E:** Dùng EPS 4 quý gần nhất (dữ liệu thực tế)
- **Forward P/E:** Dùng EPS dự phóng (ước tính của analyst)

## Cách đọc / Diễn giải

- **P/E thấp (<10):** Có thể định giá rẻ — hoặc thị trường kỳ vọng tăng trưởng thấp
- **P/E trung bình (10-20):** Mức định giá hợp lý cho đa số ngành
- **P/E cao (>20):** Thị trường kỳ vọng tăng trưởng cao — hoặc định giá quá đắt
- **So sánh P/E:** Nên so với trung bình ngành, không so giữa ngành khác nhau

## Ví dụ thực tế

Cổ phiếu VNM có P/E = 18, trong khi trung bình ngành thực phẩm đồ uống là P/E = 22. VNM đang giao dịch rẻ hơn trung bình ngành → có thể là cơ hội mua. Tuy nhiên, P/E thấp hơn ngành cũng có thể vì tăng trưởng của VNM đang chậm lại.

## Lưu ý

- P/E âm (khi EPS âm) không có ý nghĩa — doanh nghiệp thua lỗ không thể dùng P/E để định giá.
- P/E không tính đến nợ vay — dùng thêm D/E ratio để đánh giá rủi ro tài chính.
- Ngành ngân hàng, bất động sản trên HOSE thường có P/E khác biệt lớn so với ngành công nghệ, tiêu dùng.`,
  },

  "pb-ratio": {
    id: "pb-ratio",
    term: "Hệ số giá trên giá trị sổ sách (P/B)",
    termEn: "Price-to-Book Ratio",
    aliases: ["P/B", "PB", "Price-to-Book", "giá trên giá trị sổ sách"],
    category: "fundamental",
    shortDef: "Hệ số so sánh giá thị trường với giá trị sổ sách, cho biết thị trường đang trả bao nhiêu lần giá trị tài sản ròng.",
    formula: "P/B = Giá cổ phiếu / Giá trị sổ sách mỗi cổ phiếu",
    content: `## Định nghĩa

P/B (Price-to-Book Ratio) so sánh giá cổ phiếu trên thị trường với giá trị sổ sách (book value) của mỗi cổ phiếu. Giá trị sổ sách = Tổng tài sản - Tổng nợ phải trả, chia cho số cổ phiếu lưu hành. P/B cho biết nhà đầu tư đang trả bao nhiêu lần giá trị tài sản ròng.

## Cách tính

P/B = Giá cổ phiếu / (Vốn chủ sở hữu / Số cổ phiếu lưu hành)

Giá trị sổ sách mỗi cổ phiếu (BVPS) = Vốn chủ sở hữu / Số cổ phiếu lưu hành.

## Cách đọc / Diễn giải

- **P/B < 1:** Giá thị trường thấp hơn giá trị sổ sách — có thể bị định giá thấp, hoặc doanh nghiệp gặp vấn đề
- **P/B = 1-3:** Mức bình thường cho đa số ngành
- **P/B > 3:** Thị trường đánh giá cao tài sản vô hình (thương hiệu, know-how, tăng trưởng tương lai)
- **Ngành khác nhau có P/B khác nhau:** Ngân hàng thường P/B 1-2, công nghệ có thể P/B 5-10

## Ví dụ thực tế

Ngân hàng VCB có P/B = 2.5, trong khi MBB có P/B = 1.3. Thị trường đánh giá VCB cao hơn gấp đôi so với giá trị sổ sách, phản ánh kỳ vọng về chất lượng tài sản và thương hiệu vượt trội của VCB trong ngành ngân hàng Việt Nam.

## Lưu ý

- P/B phụ thuộc vào ngành: ngành thâm dụng vốn (ngân hàng, bất động sản) nên dùng P/B; ngành dịch vụ/công nghệ nên ưu tiên P/E.
- Giá trị sổ sách có thể không phản ánh giá trị thực nếu tài sản được ghi nhận theo giá gốc (historical cost).
- P/B dưới 1 trên sàn HOSE không hiếm — đặc biệt ở cổ phiếu vốn hóa nhỏ.`,
  },

  eps: {
    id: "eps",
    term: "Lợi nhuận trên mỗi cổ phiếu (EPS)",
    termEn: "Earnings Per Share",
    aliases: ["EPS", "Earnings Per Share", "lợi nhuận trên cổ phiếu"],
    category: "fundamental",
    shortDef: "Phần lợi nhuận ròng phân bổ cho mỗi cổ phiếu đang lưu hành, là thước đo cơ bản của khả năng sinh lời.",
    formula: "EPS = (Lợi nhuận ròng - Cổ tức ưu đãi) / Số cổ phiếu lưu hành",
    content: `## Định nghĩa

EPS (Earnings Per Share) là lợi nhuận ròng chia cho số cổ phiếu đang lưu hành. EPS cho biết mỗi cổ phiếu đang tạo ra bao nhiêu đồng lợi nhuận — là thước đo trực tiếp nhất về khả năng sinh lời tính trên mỗi đơn vị đầu tư.

## Cách tính

EPS = (Lợi nhuận ròng - Cổ tức ưu đãi) / Số cổ phiếu bình quân lưu hành

- **EPS cơ bản (Basic EPS):** Dùng số cổ phiếu hiện tại
- **EPS pha loãng (Diluted EPS):** Tính cả cổ phiếu tiềm năng từ trái phiếu chuyển đổi, quyền chọn

## Cách đọc / Diễn giải

- **EPS tăng qua các quý:** Doanh nghiệp đang phát triển tốt
- **EPS giảm:** Lợi nhuận suy giảm — cần tìm hiểu nguyên nhân
- **EPS âm:** Doanh nghiệp thua lỗ
- **So sánh EPS:** Nên so EPS YoY (cùng kỳ năm trước) để loại bỏ yếu tố mùa vụ
- **EPS là mẫu số của P/E:** EPS tăng → P/E giảm (nếu giá không đổi) → cổ phiếu "rẻ" hơn

## Ví dụ thực tế

FPT có EPS 4 quý gần nhất = 5,200 VND/cổ phiếu, tăng 18% so với cùng kỳ năm trước. Với giá cổ phiếu 100,000 VND, P/E = 100,000/5,200 ≈ 19.2. EPS tăng trưởng 18% cho thấy FPT đang trong giai đoạn kinh doanh tốt.

## Lưu ý

- EPS có thể bị "phóng đại" bởi lợi nhuận bất thường (bán tài sản, thanh lý đầu tư). Nên xem EPS từ hoạt động kinh doanh cốt lõi.
- Cổ phiếu pha loãng (diluted) từ ESOP, trái phiếu chuyển đổi làm tăng mẫu số → giảm EPS thực tế.
- Trên HOSE, nhiều doanh nghiệp BĐS có EPS "đột biến" do ghi nhận dự án — không bền vững.`,
  },

  roe: {
    id: "roe",
    term: "Tỷ suất lợi nhuận trên vốn chủ sở hữu (ROE)",
    termEn: "Return on Equity",
    aliases: ["ROE", "Return on Equity", "lợi nhuận trên vốn chủ"],
    category: "fundamental",
    shortDef: "Tỷ suất đo lường hiệu quả sử dụng vốn chủ sở hữu để tạo lợi nhuận, là thước đo yêu thích của Warren Buffett.",
    formula: "ROE = Lợi nhuận ròng / Vốn chủ sở hữu × 100%",
    content: `## Định nghĩa

ROE (Return on Equity) đo lường khả năng sinh lời trên mỗi đồng vốn mà cổ đông bỏ ra. ROE là một trong những chỉ số quan trọng nhất để đánh giá hiệu quả quản lý — Warren Buffett thường tìm doanh nghiệp có ROE > 15% duy trì ổn định.

## Cách tính

ROE = Lợi nhuận ròng / Vốn chủ sở hữu bình quân × 100%

Có thể phân tích ROE thành 3 yếu tố (DuPont Analysis):
ROE = Biên lợi nhuận ròng × Vòng quay tài sản × Đòn bẩy tài chính

## Cách đọc / Diễn giải

- **ROE > 15%:** Hiệu quả sử dụng vốn tốt
- **ROE > 20%:** Xuất sắc — doanh nghiệp tạo giá trị cao cho cổ đông
- **ROE < 10%:** Hiệu quả thấp — cổ đông nên cân nhắc cơ hội đầu tư khác
- **ROE tăng đều:** Doanh nghiệp đang cải thiện hiệu quả kinh doanh
- **So sánh ROE:** Nên so với trung bình ngành và lãi suất tiền gửi ngân hàng

## Ví dụ thực tế

VCB có ROE = 22%, trong khi trung bình ngành ngân hàng HOSE là 16%. ROE cao vượt trội cho thấy VCB sử dụng vốn cổ đông hiệu quả hơn đa số ngân hàng. Tuy nhiên, cần kiểm tra xem ROE cao có phải do đòn bẩy tài chính (nợ nhiều) hay do biên lợi nhuận thực sự tốt.

## Lưu ý

- ROE cao do đòn bẩy (D/E cao) là không bền vững — rủi ro khi lãi suất tăng.
- Phân tích DuPont giúp hiểu ROE cao đến từ đâu: biên lợi nhuận, hiệu quả tài sản, hay đòn bẩy.
- Ngân hàng có ROE khác biệt do đặc thù đòn bẩy cao — so sánh trong cùng ngành.`,
  },

  roa: {
    id: "roa",
    term: "Tỷ suất lợi nhuận trên tổng tài sản (ROA)",
    termEn: "Return on Assets",
    aliases: ["ROA", "Return on Assets", "lợi nhuận trên tổng tài sản"],
    category: "fundamental",
    shortDef: "Tỷ suất đo lường hiệu quả sử dụng toàn bộ tài sản (bao gồm cả nợ vay) để tạo lợi nhuận.",
    formula: "ROA = Lợi nhuận ròng / Tổng tài sản × 100%",
    content: `## Định nghĩa

ROA (Return on Assets) đo lường hiệu quả sử dụng toàn bộ tài sản của doanh nghiệp để tạo ra lợi nhuận. Khác với ROE (chỉ tính vốn chủ), ROA tính cả phần tài sản từ nợ vay, cho bức tranh đầy đủ hơn về hiệu quả hoạt động.

## Cách tính

ROA = Lợi nhuận ròng / Tổng tài sản bình quân × 100%

ROA liên hệ với ROE qua đòn bẩy: ROE = ROA × (Tổng tài sản / Vốn chủ sở hữu)

## Cách đọc / Diễn giải

- **ROA > 5%:** Tốt cho đa số ngành sản xuất, bán lẻ
- **ROA > 10%:** Xuất sắc — doanh nghiệp sử dụng tài sản rất hiệu quả
- **ROA < 2%:** Hiệu quả thấp — đặc biệt nếu không phải ngành thâm dụng vốn
- **Ngân hàng:** ROA 1-2% là bình thường do tổng tài sản rất lớn (bao gồm tiền gửi khách hàng)

## Ví dụ thực tế

MWG (Thế Giới Di Động) có ROA = 8%, trong khi HPG (Hòa Phát) có ROA = 4%. MWG sử dụng tài sản hiệu quả hơn — mỗi 100 đồng tài sản tạo 8 đồng lợi nhuận, so với 4 đồng của HPG. Tuy nhiên, HPG là ngành thép nặng vốn nên ROA tự nhiên thấp hơn.

## Lưu ý

- ROA phụ thuộc vào ngành: ngành thâm dụng vốn (thép, xi măng) có ROA tự nhiên thấp hơn ngành dịch vụ, công nghệ.
- So sánh ROA giữa doanh nghiệp cùng ngành mới có ý nghĩa.
- ROA bù cho điểm yếu của ROE: nếu ROE cao nhưng ROA thấp → doanh nghiệp dựa vào đòn bẩy nợ.`,
  },

  "de-ratio": {
    id: "de-ratio",
    term: "Hệ số nợ trên vốn chủ sở hữu (D/E)",
    termEn: "Debt-to-Equity Ratio",
    aliases: ["D/E", "DE", "Debt-to-Equity", "hệ số nợ"],
    category: "fundamental",
    shortDef: "Hệ số đo lường mức độ đòn bẩy tài chính, cho biết doanh nghiệp vay nợ bao nhiêu lần so với vốn tự có.",
    formula: "D/E = Tổng nợ / Vốn chủ sở hữu",
    content: `## Định nghĩa

D/E (Debt-to-Equity Ratio) là hệ số đòn bẩy tài chính, so sánh tổng nợ phải trả với vốn chủ sở hữu. D/E cho biết doanh nghiệp sử dụng bao nhiêu đồng nợ vay cho mỗi đồng vốn tự có. Hệ số này phản ánh rủi ro tài chính của doanh nghiệp.

## Cách tính

D/E = Tổng nợ phải trả / Vốn chủ sở hữu

Một số nhà phân tích chỉ dùng nợ vay có lãi (interest-bearing debt) thay vì tổng nợ phải trả để loại bỏ nợ phải trả nhà cung cấp (không lãi suất).

## Cách đọc / Diễn giải

- **D/E < 1:** Doanh nghiệp dùng vốn tự có nhiều hơn nợ vay → rủi ro thấp
- **D/E = 1-2:** Mức đòn bẩy bình thường cho đa số ngành
- **D/E > 2:** Đòn bẩy cao → rủi ro lớn khi lãi suất tăng hoặc kinh doanh suy giảm
- **Ngành khác nhau có D/E khác nhau:** Bất động sản, ngân hàng thường D/E cao hơn công nghệ, tiêu dùng

## Ví dụ thực tế

NVL (Novaland) có D/E = 3.5, trong khi FPT có D/E = 0.6. NVL là doanh nghiệp bất động sản phụ thuộc vào vốn vay, trong khi FPT tự tài trợ hoạt động bằng vốn chủ. Khi lãi suất tăng từ 8% lên 12%, NVL chịu áp lực chi phí lãi vay rất lớn, còn FPT gần như không bị ảnh hưởng.

## Lưu ý

- D/E cao không nhất thiết xấu — nếu ROE cao hơn lãi suất vay, đòn bẩy tạo giá trị cho cổ đông.
- D/E của ngành ngân hàng rất cao (>10) do bản chất kinh doanh — không thể so sánh với ngành khác.
- Trên HOSE, nên cảnh giác với D/E > 3 ở ngành phi tài chính — đặc biệt trong môi trường lãi suất tăng.`,
  },

  "revenue-growth": {
    id: "revenue-growth",
    term: "Tăng trưởng doanh thu",
    termEn: "Revenue Growth",
    aliases: ["tăng trưởng doanh thu", "Revenue Growth", "doanh thu"],
    category: "fundamental",
    shortDef: "Tỷ lệ phần trăm thay đổi doanh thu so với kỳ trước, phản ánh khả năng mở rộng kinh doanh của doanh nghiệp.",
    formula: "Revenue Growth = (Doanh thu kỳ này - Doanh thu kỳ trước) / Doanh thu kỳ trước × 100%",
    content: `## Định nghĩa

Tăng trưởng doanh thu (Revenue Growth) đo lường mức thay đổi doanh thu thuần giữa hai kỳ kế toán. Đây là chỉ số quan trọng nhất phản ánh khả năng mở rộng quy mô kinh doanh — "top-line growth" — trước khi xét đến chi phí và lợi nhuận.

## Cách tính

Revenue Growth (%) = (Doanh thu kỳ này - Doanh thu kỳ trước) / Doanh thu kỳ trước × 100%

Có hai cách so sánh:
- **QoQ (Quarter over Quarter):** So với quý trước — phát hiện xu hướng ngắn hạn
- **YoY (Year over Year):** So cùng kỳ năm trước — loại bỏ yếu tố mùa vụ

## Cách đọc / Diễn giải

- **Tăng trưởng > 20%:** Doanh nghiệp đang mở rộng nhanh
- **Tăng trưởng 5-20%:** Tăng trưởng ổn định, bền vững
- **Tăng trưởng 0-5%:** Chậm lại — cần xem lý do
- **Tăng trưởng âm:** Doanh thu giảm — tín hiệu cảnh báo
- **So sánh:** Nên so với trung bình ngành và GDP để đánh giá tương đối

## Ví dụ thực tế

FPT có doanh thu Q3/2025 = 15,200 tỷ VND, Q3/2024 = 12,800 tỷ VND. Tăng trưởng YoY = (15,200 - 12,800) / 12,800 × 100% = 18.75%. Mức này cho thấy FPT duy trì tăng trưởng ấn tượng trong ngành công nghệ Việt Nam.

## Lưu ý

- Doanh thu tăng nhưng lợi nhuận giảm (biên lợi nhuận thu hẹp) là dấu hiệu cảnh báo — "tăng trưởng bằng mọi giá."
- So sánh YoY quan trọng hơn QoQ vì loại bỏ tính mùa vụ (ngành bán lẻ bán nhiều hơn Q4, xây dựng mạnh Q2-Q3).
- Trên HOSE, cẩn thận với doanh thu đột biến từ bán tài sản hoặc thanh lý đầu tư — không bền vững.`,
  },

  "profit-growth": {
    id: "profit-growth",
    term: "Tăng trưởng lợi nhuận",
    termEn: "Profit Growth",
    aliases: ["tăng trưởng lợi nhuận", "Profit Growth", "lợi nhuận"],
    category: "fundamental",
    shortDef: "Tỷ lệ phần trăm thay đổi lợi nhuận ròng so với kỳ trước, phản ánh khả năng chuyển doanh thu thành lợi nhuận thực tế.",
    formula: "Profit Growth = (LN kỳ này - LN kỳ trước) / LN kỳ trước × 100%",
    content: `## Định nghĩa

Tăng trưởng lợi nhuận (Profit Growth) đo lường mức thay đổi lợi nhuận ròng (net income) giữa hai kỳ kế toán. Đây là "bottom-line growth" — phản ánh kết quả cuối cùng sau khi trừ hết chi phí, thuế, và lãi vay.

## Cách tính

Profit Growth (%) = (Lợi nhuận ròng kỳ này - Lợi nhuận ròng kỳ trước) / |Lợi nhuận ròng kỳ trước| × 100%

Dùng giá trị tuyệt đối ở mẫu số để tính đúng khi lợi nhuận kỳ trước âm.

## Cách đọc / Diễn giải

- **LN tăng > doanh thu tăng:** Biên lợi nhuận mở rộng → quản lý chi phí tốt
- **LN tăng < doanh thu tăng:** Biên lợi nhuận thu hẹp → chi phí tăng nhanh hơn doanh thu
- **LN tăng khi doanh thu giảm:** Cắt giảm chi phí hiệu quả — nhưng không bền vững dài hạn
- **LN giảm khi doanh thu tăng:** Dấu hiệu cảnh báo nghiêm trọng — cần tìm hiểu chi phí

## Ví dụ thực tế

HPG có lợi nhuận Q2/2025 = 3,800 tỷ VND so với Q2/2024 = 2,100 tỷ VND. Tăng trưởng YoY = (3,800 - 2,100) / 2,100 × 100% = 80.9%. Đây là mức tăng trưởng rất mạnh, phản ánh chu kỳ phục hồi ngành thép. Tuy nhiên, mức tăng cao bất thường vì so với nền thấp (Q2/2024 lợi nhuận giảm sâu).

## Lưu ý

- Lợi nhuận có thể bị thổi phồng bởi thu nhập bất thường (thanh lý tài sản, chênh lệch tỷ giá, hoàn nhập dự phòng).
- Nên xem lợi nhuận từ hoạt động kinh doanh cốt lõi (operating profit) để đánh giá chất lượng tăng trưởng.
- "Hiệu ứng nền thấp" (low base effect) có thể làm tỷ lệ tăng trưởng rất cao nhưng giá trị tuyệt đối không ấn tượng.`,
  },

  "market-cap": {
    id: "market-cap",
    term: "Vốn hóa thị trường",
    termEn: "Market Capitalization",
    aliases: ["vốn hóa", "Market Cap", "Market Capitalization", "vốn hóa thị trường"],
    category: "fundamental",
    shortDef: "Tổng giá trị thị trường của toàn bộ cổ phiếu đang lưu hành, phản ánh quy mô và tầm quan trọng của doanh nghiệp.",
    formula: "Market Cap = Giá cổ phiếu × Số cổ phiếu lưu hành",
    content: `## Định nghĩa

Vốn hóa thị trường (Market Capitalization) là tổng giá trị của tất cả cổ phiếu đang lưu hành, tính bằng giá thị trường hiện tại. Đây là thước đo quy mô công ty phổ biến nhất, dùng để phân loại cổ phiếu theo nhóm vốn hóa lớn, trung bình, và nhỏ.

## Cách tính

Market Cap = Giá cổ phiếu × Tổng số cổ phiếu đang lưu hành

Vốn hóa thay đổi theo giá cổ phiếu hàng ngày.

## Cách đọc / Diễn giải

Trên sàn HOSE:
- **Vốn hóa lớn (Large-cap):** > 10,000 tỷ VND — VNM, VCB, FPT, VIC, HPG. Thanh khoản cao, biến động ít
- **Vốn hóa trung bình (Mid-cap):** 1,000-10,000 tỷ VND — Nhiều cơ hội tăng trưởng
- **Vốn hóa nhỏ (Small-cap):** < 1,000 tỷ VND — Biến động lớn, rủi ro cao nhưng tiềm năng sinh lời cao

## Ví dụ thực tế

VCB có giá cổ phiếu 90,000 VND × 4.7 tỷ cổ phiếu = vốn hóa ~423,000 tỷ VND (~17 tỷ USD). Đây là cổ phiếu vốn hóa lớn nhất sàn HOSE, chiếm tỷ trọng đáng kể trong chỉ số VN-Index. Biến động giá VCB ảnh hưởng trực tiếp đến VN-Index.

## Lưu ý

- Vốn hóa lớn không có nghĩa "đắt" — cổ phiếu rẻ hay đắt phải dùng P/E, P/B để đánh giá.
- Free-float (cổ phiếu tự do giao dịch) có thể khác tổng cổ phiếu lưu hành — ảnh hưởng thanh khoản thực tế.
- Trên HOSE, top 30 cổ phiếu vốn hóa lớn nhất (VN30) chiếm phần lớn khối lượng giao dịch hàng ngày.`,
  },

  "current-ratio": {
    id: "current-ratio",
    term: "Hệ số thanh toán hiện hành",
    termEn: "Current Ratio",
    aliases: ["Current Ratio", "hệ số thanh toán", "thanh toán hiện hành"],
    category: "fundamental",
    shortDef: "Hệ số đo khả năng thanh toán các khoản nợ ngắn hạn bằng tài sản ngắn hạn, phản ánh thanh khoản doanh nghiệp.",
    formula: "Current Ratio = Tài sản ngắn hạn / Nợ ngắn hạn",
    content: `## Định nghĩa

Current Ratio (Hệ số thanh toán hiện hành) đo lường khả năng doanh nghiệp thanh toán các nghĩa vụ nợ ngắn hạn (đến hạn trong 12 tháng) bằng tài sản ngắn hạn (tiền, hàng tồn kho, khoản phải thu). Đây là chỉ số thanh khoản cơ bản nhất.

## Cách tính

Current Ratio = Tài sản ngắn hạn / Nợ ngắn hạn

Tài sản ngắn hạn bao gồm: tiền và tương đương tiền, đầu tư ngắn hạn, khoản phải thu, hàng tồn kho, và tài sản ngắn hạn khác.

## Cách đọc / Diễn giải

- **Current Ratio > 2:** Thanh khoản tốt — nhưng có thể đang giữ quá nhiều tiền mặt (không hiệu quả)
- **Current Ratio 1-2:** Mức bình thường — đủ khả năng thanh toán ngắn hạn
- **Current Ratio < 1:** Cảnh báo — tài sản ngắn hạn không đủ trả nợ ngắn hạn, rủi ro mất thanh khoản
- **Current Ratio quá cao (>3):** Có thể doanh nghiệp quản lý vốn lưu động kém hiệu quả

## Ví dụ thực tế

VNM có Current Ratio = 2.1, cho thấy cứ 1 đồng nợ ngắn hạn được bảo đảm bởi 2.1 đồng tài sản ngắn hạn. VNM có thanh khoản tốt, phù hợp với đặc thù ngành FMCG (hàng tiêu dùng nhanh) — vòng quay hàng tồn kho nhanh, khoản phải thu thấp.

## Lưu ý

- Current Ratio không tính đến chất lượng tài sản ngắn hạn — hàng tồn kho khó bán hoặc khoản phải thu khó đòi làm tỷ số bị phóng đại.
- Dùng Quick Ratio (Acid-test) = (Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn để kiểm tra khắt khe hơn.
- Ngành bán lẻ (MWG, PNJ) thường có Current Ratio thấp hơn do vòng quay hàng tồn kho nhanh.`,
  },
};

// === MACRO CONCEPTS ===

const macroEntries: Record<string, GlossaryEntry> = {
  cpi: {
    id: "cpi",
    term: "Chỉ số giá tiêu dùng (CPI)",
    termEn: "Consumer Price Index",
    aliases: ["CPI", "Consumer Price Index", "chỉ số giá tiêu dùng", "lạm phát"],
    category: "macro",
    shortDef: "Chỉ số đo lường mức thay đổi giá cả hàng hóa và dịch vụ tiêu dùng theo thời gian, phản ánh lạm phát.",
    content: `## Định nghĩa

CPI (Consumer Price Index) là chỉ số đo lường mức thay đổi giá cả của một rổ hàng hóa và dịch vụ tiêu dùng đại diện. CPI là thước đo lạm phát phổ biến nhất — khi CPI tăng, sức mua đồng tiền giảm.

## Cách đọc / Diễn giải

- **CPI tăng 2-4%/năm:** Mức lạm phát lành mạnh, hỗ trợ tăng trưởng kinh tế
- **CPI tăng > 5%:** Lạm phát cao — Ngân hàng Nhà nước có thể tăng lãi suất → tiêu cực cho chứng khoán
- **CPI giảm (giảm phát):** Nguy hiểm hơn lạm phát — doanh nghiệp giảm doanh thu, nợ xấu tăng
- **CPI Việt Nam:** Tổng cục Thống kê công bố hàng tháng, mục tiêu kiểm soát dưới 4%/năm

## Ví dụ thực tế

CPI Việt Nam tháng 6/2025 tăng 3.8% YoY — nằm trong mục tiêu kiểm soát. Tuy nhiên, nếu CPI vượt 4.5%, Ngân hàng Nhà nước có thể thắt chặt tiền tệ (tăng lãi suất), gây áp lực giảm giá lên thị trường chứng khoán, đặc biệt nhóm bất động sản và ngân hàng.

## Lưu ý

- CPI "core" (loại trừ thực phẩm, năng lượng) phản ánh lạm phát nền chính xác hơn CPI tổng.
- Tại Việt Nam, CPI bị ảnh hưởng nhiều bởi giá thực phẩm (chiếm tỷ trọng lớn trong rổ hàng hóa).
- Lạm phát kỳ vọng quan trọng hơn lạm phát thực tế — thị trường phản ứng trước khi số liệu CPI công bố.
- Mối quan hệ CPI-chứng khoán: CPI tăng vừa phải (2-4%) → tích cực; CPI tăng mạnh (>5%) → tiêu cực do lãi suất tăng.`,
  },

  "gdp-growth": {
    id: "gdp-growth",
    term: "Tăng trưởng GDP",
    termEn: "GDP Growth Rate",
    aliases: ["GDP", "GDP Growth", "tăng trưởng GDP", "tổng sản phẩm quốc nội"],
    category: "macro",
    shortDef: "Tốc độ tăng trưởng tổng sản phẩm quốc nội, phản ánh sức khỏe tổng thể và đà tăng trưởng của nền kinh tế.",
    formula: "GDP Growth = (GDP kỳ này - GDP kỳ trước) / GDP kỳ trước × 100%",
    content: `## Định nghĩa

GDP (Gross Domestic Product) là tổng giá trị hàng hóa và dịch vụ cuối cùng được sản xuất trong lãnh thổ quốc gia trong một khoảng thời gian. Tăng trưởng GDP là tỷ lệ % thay đổi so với kỳ trước, phản ánh đà tăng trưởng kinh tế tổng thể.

## Cách đọc / Diễn giải

- **GDP tăng > 6%:** Kinh tế Việt Nam tăng trưởng mạnh → tích cực cho chứng khoán
- **GDP tăng 4-6%:** Tăng trưởng ổn định — mức trung bình của Việt Nam giai đoạn gần đây
- **GDP tăng < 4%:** Kinh tế chậm lại — doanh nghiệp khó tăng trưởng lợi nhuận
- **GDP âm (2 quý liên tiếp):** Suy thoái kinh tế (recession) — hiếm gặp ở Việt Nam

## Ví dụ thực tế

GDP Việt Nam 6 tháng đầu 2025 tăng 6.9% YoY — cao hơn mục tiêu cả năm 6.5%. Tăng trưởng mạnh hỗ trợ lợi nhuận doanh nghiệp niêm yết, đặc biệt nhóm ngân hàng (tín dụng tăng), tiêu dùng (chi tiêu tăng), và công nghiệp (sản xuất mở rộng).

## Lưu ý

- GDP là chỉ số trễ (lagging) — thị trường chứng khoán thường phản ứng trước 3-6 tháng.
- GDP danh nghĩa vs GDP thực: GDP thực đã loại bỏ yếu tố lạm phát, phản ánh tăng trưởng thật sự.
- Cấu trúc GDP Việt Nam: dịch vụ (~42%), công nghiệp-xây dựng (~38%), nông nghiệp (~12%).
- Thị trường chứng khoán tương quan dương với GDP dài hạn, nhưng ngắn hạn có thể lệch pha.`,
  },

  "interest-rate": {
    id: "interest-rate",
    term: "Lãi suất điều hành",
    termEn: "Policy Interest Rate",
    aliases: ["lãi suất", "Interest Rate", "lãi suất điều hành", "lãi suất chính sách"],
    category: "macro",
    shortDef: "Lãi suất do Ngân hàng Nhà nước thiết lập, ảnh hưởng trực tiếp đến chi phí vay vốn và định giá cổ phiếu.",
    content: `## Định nghĩa

Lãi suất điều hành (Policy Interest Rate) là lãi suất do Ngân hàng Nhà nước Việt Nam (SBV) thiết lập, bao gồm lãi suất tái cấp vốn, lãi suất chiết khấu, và lãi suất cho vay qua đêm. Lãi suất điều hành là công cụ chính của chính sách tiền tệ, ảnh hưởng đến toàn bộ nền kinh tế.

## Cách đọc / Diễn giải

- **Giảm lãi suất:** Kích thích kinh tế → doanh nghiệp vay rẻ hơn → tăng đầu tư → tích cực cho chứng khoán
- **Tăng lãi suất:** Kiềm chế lạm phát → doanh nghiệp vay đắt hơn → tiêu cực cho chứng khoán
- **Lãi suất thấp:** Dòng tiền chuyển từ gửi tiết kiệm sang chứng khoán (TINA effect)
- **Lãi suất cao:** Dòng tiền rút khỏi chứng khoán vào tiết kiệm an toàn

## Ví dụ thực tế

Cuối 2023, SBV liên tục giảm lãi suất điều hành từ 6% xuống 4.5%. Lãi suất tiền gửi giảm từ 9% xuống 5%. Dòng tiền nhàn rỗi không còn hấp dẫn ở ngân hàng → chảy vào thị trường chứng khoán, đẩy VN-Index tăng từ 1,050 lên 1,280 điểm trong 6 tháng.

## Lưu ý

- Nhóm cổ phiếu nhạy lãi suất nhất: ngân hàng (biên lãi ròng NIM), bất động sản (chi phí vay), tiện ích (nợ vay lớn).
- Lãi suất Việt Nam bị ảnh hưởng bởi Fed (Cục Dự trữ Liên bang Mỹ) — khi Fed tăng lãi suất, SBV phải cân nhắc để giữ tỷ giá.
- Chênh lệch lãi suất VND-USD ảnh hưởng dòng vốn ngoại trên HOSE.
- Mối quan hệ lãi suất-chứng khoán có độ trễ 3-6 tháng — giảm lãi suất hôm nay, chứng khoán phản ứng dần.`,
  },

  "exchange-rate": {
    id: "exchange-rate",
    term: "Tỷ giá hối đoái",
    termEn: "Exchange Rate",
    aliases: ["tỷ giá", "Exchange Rate", "USD/VND", "tỷ giá hối đoái"],
    category: "macro",
    shortDef: "Giá trị quy đổi giữa hai đồng tiền, ảnh hưởng đến doanh nghiệp xuất nhập khẩu và dòng vốn ngoại.",
    content: `## Định nghĩa

Tỷ giá hối đoái (Exchange Rate) là giá trị quy đổi giữa đồng Việt Nam (VND) và ngoại tệ, quan trọng nhất là USD/VND. Tỷ giá ảnh hưởng trực tiếp đến doanh nghiệp xuất nhập khẩu, dòng vốn đầu tư nước ngoài, và giá trị tài sản tính bằng ngoại tệ.

## Cách đọc / Diễn giải

- **VND yếu (USD/VND tăng):** Có lợi cho xuất khẩu (VHC, PHR, DPM) — bất lợi cho nhập khẩu và nợ ngoại tệ
- **VND mạnh (USD/VND giảm):** Có lợi cho nhập khẩu (ACV, PVD) — bất lợi cho xuất khẩu
- **Tỷ giá ổn định:** Thu hút vốn ngoại — nhà đầu tư nước ngoài không lo mất giá khi quy đổi
- **SBV quản lý tỷ giá:** Cơ chế tỷ giá trung tâm ± biên độ giao dịch, không thả nổi hoàn toàn

## Ví dụ thực tế

USD/VND tăng từ 24,200 lên 25,500 trong năm 2024 (VND mất giá ~5.4%). Doanh nghiệp xuất khẩu thủy sản VHC hưởng lợi vì doanh thu USD quy đổi ra nhiều VND hơn. Ngược lại, hãng hàng không VJC chịu thiệt vì chi phí nhiên liệu và thuê máy bay tính bằng USD tăng.

## Lưu ý

- Tỷ giá phụ thuộc vào: chênh lệch lãi suất VND-USD, cán cân thương mại, dòng vốn FDI/FII, chính sách tiền tệ SBV.
- Nhà đầu tư nước ngoài trên HOSE phải chịu rủi ro tỷ giá — VND mất giá làm giảm lợi nhuận tính bằng USD.
- SBV sử dụng dự trữ ngoại hối (~100 tỷ USD) để can thiệp khi tỷ giá biến động mạnh.
- Cổ phiếu "hưởng lợi từ VND yếu": VHC, PHR, DPM, GVR. "Thiệt hại khi VND yếu": ACV, VJC, cổ phiếu nợ ngoại tệ lớn.`,
  },

  "money-supply-m2": {
    id: "money-supply-m2",
    term: "Cung tiền M2",
    termEn: "Money Supply M2",
    aliases: ["M2", "Money Supply", "cung tiền", "cung tiền M2"],
    category: "macro",
    shortDef: "Tổng lượng tiền trong nền kinh tế bao gồm tiền mặt, tiền gửi thanh toán và tiền gửi có kỳ hạn, phản ánh thanh khoản hệ thống.",
    content: `## Định nghĩa

M2 (Money Supply M2) là thước đo cung tiền rộng trong nền kinh tế, bao gồm: tiền mặt lưu hành + tiền gửi không kỳ hạn (M1) + tiền gửi có kỳ hạn + tiền gửi tiết kiệm. M2 phản ánh tổng thanh khoản của hệ thống tài chính.

## Cách đọc / Diễn giải

- **M2 tăng nhanh (>15%):** Thanh khoản dồi dào → hỗ trợ chứng khoán, nhưng có thể gây lạm phát
- **M2 tăng chậm (<10%):** Thanh khoản hạn chế → thị trường chứng khoán khó tăng mạnh
- **M2 tương quan với VN-Index:** Lịch sử cho thấy M2 tăng mạnh thường đi kèm thị trường tăng
- **Tín dụng tăng trưởng:** Khi SBV nới tín dụng → M2 tăng → thanh khoản hệ thống tốt hơn

## Ví dụ thực tế

M2 Việt Nam tăng 14% YoY (tháng 6/2025), trong khi tín dụng toàn hệ thống tăng 12%. Tốc độ tăng M2 cao hơn tăng trưởng tín dụng cho thấy tiền đang tích lũy trong hệ thống (tiền gửi tăng nhanh). Dòng tiền dư thừa này có thể chảy vào thị trường chứng khoán và bất động sản.

## Lưu ý

- Mối quan hệ M2-chứng khoán có độ trễ: M2 tăng 3-6 tháng trước khi thị trường phản ứng rõ rệt.
- SBV kiểm soát M2 qua: lãi suất điều hành, tỷ lệ dự trữ bắt buộc, nghiệp vụ thị trường mở (OMO).
- M2/GDP ratio (Việt Nam ~180%) phản ánh mức tiền tệ hóa — cao hơn nhiều nước trong khu vực.
- Khi M2 tăng mạnh nhưng GDP tăng chậm → rủi ro lạm phát và bong bóng tài sản tăng.`,
  },
};

// === COMBINED GLOSSARY ===

export const glossary: Record<string, GlossaryEntry> = {
  ...technicalEntries,
  ...fundamentalEntries,
  ...macroEntries,
};

// === HELPER FUNCTIONS ===

export function getEntriesByCategory(category: GlossaryCategory): GlossaryEntry[] {
  return Object.values(glossary).filter((e) => e.category === category);
}

export function getAllEntries(): GlossaryEntry[] {
  return Object.values(glossary);
}

export function normalizeForSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")  // Remove combining diacritical marks
    .replace(/[đĐ]/g, "d")            // Vietnamese đ/Đ → d (NOT handled by NFD)
    .toLowerCase();
}
