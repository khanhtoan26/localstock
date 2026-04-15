# Requirements: LocalStock

**Defined:** 2026-04-14
**Core Value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## v1 Requirements

### Data Acquisition

- [x] **DATA-01**: Agent crawl được dữ liệu giá/khối lượng OHLCV hàng ngày cho ~400 mã HOSE
- [x] **DATA-02**: Agent lưu trữ dữ liệu lịch sử ≥2 năm trong database local
- [x] **DATA-03**: Agent thu thập báo cáo tài chính (BCTC) theo quý và năm (bảng cân đối, kết quả kinh doanh, lưu chuyển tiền tệ)
- [x] **DATA-04**: Agent lưu thông tin công ty (ngành, vốn hóa, số lượng cổ phiếu lưu hành)
- [x] **DATA-05**: Agent xử lý điều chỉnh giá khi có sự kiện chia tách/phát hành thêm (corporate actions)

### Technical Analysis

- [x] **TECH-01**: Agent tính toán các chỉ báo kỹ thuật cơ bản: SMA(20,50,200), EMA(12,26), RSI(14), MACD(12,26,9), Bollinger Bands(20,2)
- [x] **TECH-02**: Agent phân tích khối lượng giao dịch (average volume, relative volume, xu hướng volume)
- [x] **TECH-03**: Agent nhận diện xu hướng giá (uptrend/downtrend/sideways) từ MA crossovers và price action
- [x] **TECH-04**: Agent xác định vùng hỗ trợ/kháng cự từ pivot points và đỉnh/đáy gần nhất

### Fundamental Analysis

- [x] **FUND-01**: Agent tính toán các chỉ số tài chính cơ bản: P/E, P/B, EPS, ROE, ROA, D/E
- [x] **FUND-02**: Agent đánh giá tăng trưởng doanh thu và lợi nhuận theo QoQ và YoY
- [x] **FUND-03**: Agent so sánh chỉ số tài chính với trung bình ngành (theo phân ngành ICB)

### Sentiment Analysis

- [x] **SENT-01**: Agent crawl tin tức tài chính từ các nguồn Việt Nam (CafeF, VnExpress, Thanh Niên...)
- [x] **SENT-02**: Agent sử dụng LLM local để phân loại sentiment tin tức (tích cực/tiêu cực/trung tính) cho từng mã
- [x] **SENT-03**: Agent tổng hợp điểm sentiment từ nhiều bài viết thành score cho từng mã

### Macro Analysis

- [ ] **MACR-01**: Agent thu thập dữ liệu vĩ mô: lãi suất (SBV), tỷ giá USD/VND, CPI, GDP
- [ ] **MACR-02**: Agent phân tích tác động vĩ mô đến từng ngành/mã cổ phiếu (VD: lãi suất tăng → tiêu cực cho bất động sản, tích cực cho ngân hàng)

### Scoring & Ranking

- [x] **SCOR-01**: Agent chấm điểm tổng hợp cho từng mã (thang 0-100) kết hợp 4 chiều: kỹ thuật + cơ bản + sentiment + vĩ mô
- [x] **SCOR-02**: Agent cho phép tùy chỉnh trọng số chấm điểm (mặc định: kỹ thuật 30%, cơ bản 30%, sentiment 20%, vĩ mô 20%)
- [ ] **SCOR-03**: Agent xếp hạng và đưa ra danh sách top 10-20 mã đáng mua kèm lý do
- [ ] **SCOR-04**: Agent phát hiện và cảnh báo khi điểm thay đổi đáng kể (>15 điểm) so với phiên trước
- [ ] **SCOR-05**: Agent phân tích sector rotation — theo dõi dòng tiền chảy giữa các ngành

### T+3 Settlement Awareness

- [ ] **T3-01**: Khi gợi ý mã lướt sóng, agent dự đoán xu hướng ít nhất 3 ngày tới (do quy tắc T+3 của HOSE — mua hôm nay, 3 ngày sau mới bán được)
- [ ] **T3-02**: Agent phân biệt rõ ràng giữa gợi ý đầu tư dài hạn và gợi ý lướt sóng, kèm cảnh báo T+3

### AI Reports

- [ ] **REPT-01**: LLM local (Ollama) tổng hợp phân tích đa chiều thành báo cáo tiếng Việt cho từng mã, giải thích TẠI SAO điểm cao/thấp
- [ ] **REPT-02**: Báo cáo bao gồm: tín hiệu kỹ thuật, đánh giá cơ bản, sentiment tin tức, ảnh hưởng vĩ mô, và khuyến nghị tổng hợp

### Automation

- [ ] **AUTO-01**: Agent chạy tự động hàng ngày sau khi thị trường đóng cửa (sau 15:30)
- [ ] **AUTO-02**: Agent hỗ trợ chạy on-demand khi người dùng yêu cầu (phân tích 1 mã hoặc toàn bộ)

### Notification

- [ ] **NOTI-01**: Agent gửi thông báo qua Telegram bot khi có gợi ý mã đáng mua (daily digest)
- [ ] **NOTI-02**: Agent gửi alert đặc biệt qua Telegram khi phát hiện thay đổi điểm lớn hoặc tín hiệu mạnh

### Dashboard

- [ ] **DASH-01**: Web dashboard hiển thị bảng xếp hạng cổ phiếu theo điểm tổng hợp
- [ ] **DASH-02**: Dashboard cho phép xem chi tiết từng mã: biểu đồ giá, chỉ báo kỹ thuật, báo cáo AI
- [ ] **DASH-03**: Dashboard hiển thị tổng quan thị trường và phân tích vĩ mô

## v2 Requirements

### Enhanced Analysis

- **ENH-01**: Hỗ trợ thêm sàn HNX và UPCOM
- **ENH-02**: Phân tích intraday (dữ liệu phút/giờ thay vì chỉ ngày)
- **ENH-03**: Backtesting — kiểm tra độ chính xác gợi ý trong quá khứ
- **ENH-04**: Portfolio tracking — theo dõi danh mục đầu tư cá nhân

### Cloud & Scale

- **CLD-01**: Deploy lên cloud (VPS/Docker)
- **CLD-02**: Multi-user support với authentication

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-trading (tự mua/bán) | Rủi ro tài chính, pháp lý, API broker VN không ổn định |
| Mobile app | Web dashboard đủ cho v1, tool cá nhân |
| Paid LLM API (GPT/Claude) | Cam kết miễn phí, dùng local LLM |
| Real-time streaming data | Batch processing sau giờ đóng cửa là đủ cho v1 |
| Multi-user/auth | Tool cá nhân, không cần phức tạp |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1: Foundation & Data Pipeline | Complete |
| DATA-02 | Phase 1: Foundation & Data Pipeline | Complete |
| DATA-03 | Phase 1: Foundation & Data Pipeline | Complete |
| DATA-04 | Phase 1: Foundation & Data Pipeline | Complete |
| DATA-05 | Phase 1: Foundation & Data Pipeline | Complete |
| TECH-01 | Phase 2: Technical & Fundamental Analysis | Complete |
| TECH-02 | Phase 2: Technical & Fundamental Analysis | Complete |
| TECH-03 | Phase 2: Technical & Fundamental Analysis | Complete |
| TECH-04 | Phase 2: Technical & Fundamental Analysis | Complete |
| FUND-01 | Phase 2: Technical & Fundamental Analysis | Complete |
| FUND-02 | Phase 2: Technical & Fundamental Analysis | Complete |
| FUND-03 | Phase 2: Technical & Fundamental Analysis | Complete |
| SENT-01 | Phase 3: Sentiment Analysis & Scoring Engine | Complete |
| SENT-02 | Phase 3: Sentiment Analysis & Scoring Engine | Complete |
| SENT-03 | Phase 3: Sentiment Analysis & Scoring Engine | Complete |
| SCOR-01 | Phase 3: Sentiment Analysis & Scoring Engine | Complete |
| SCOR-02 | Phase 3: Sentiment Analysis & Scoring Engine | Complete |
| SCOR-03 | Phase 3: Sentiment Analysis & Scoring Engine | Pending |
| REPT-01 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| REPT-02 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| MACR-01 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| MACR-02 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| T3-01 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| T3-02 | Phase 4: AI Reports, Macro Context & T+3 | Pending |
| AUTO-01 | Phase 5: Automation & Notifications | Pending |
| AUTO-02 | Phase 5: Automation & Notifications | Pending |
| NOTI-01 | Phase 5: Automation & Notifications | Pending |
| NOTI-02 | Phase 5: Automation & Notifications | Pending |
| SCOR-04 | Phase 5: Automation & Notifications | Pending |
| SCOR-05 | Phase 5: Automation & Notifications | Pending |
| DASH-01 | Phase 6: Web Dashboard | Pending |
| DASH-02 | Phase 6: Web Dashboard | Pending |
| DASH-03 | Phase 6: Web Dashboard | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after roadmap creation*
