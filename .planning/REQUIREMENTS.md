# Requirements: LocalStock v1.4

**Defined:** 2026-04-25
**Core Value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.

## v1.4 Requirements

Requirements for AI Analysis Depth milestone. All map to roadmap phases.

### Signal Computation

- [x] **SIGNAL-01**: System detects 5 candlestick patterns (doji, inside, hammer, engulfing, shooting star) from OHLCV data using pandas-ta native functions + pure OHLC math (no TA-Lib)
- [x] **SIGNAL-02**: System computes volume divergence signal (MFI/CMF/OBV-based), gated on avg_volume ≥ 100k shares/day — returns null for low-liquidity stocks
- [x] **SIGNAL-03**: System reads sector momentum from SectorSnapshot for injection into LLM prompt per stock

### Prompt & Schema

- [ ] **PROMPT-01**: Ollama context window raised from 4096 to 6144+ tokens before any new prompt content is added
- [ ] **PROMPT-02**: `StockReport` Pydantic model extended with `entry_price`, `stop_loss`, `target_price`, `risk_rating`, `catalyst`, `signal_conflicts` — all `Optional[T] = None` for backward compatibility
- [ ] **PROMPT-03**: Prompts restructured to inject S/R anchors (nearest_support, nearest_resistance, support_1/2, resistance_1/2, pivot_point), candlestick patterns, volume divergence, and sector momentum as explicit named context
- [ ] **PROMPT-04**: Post-generation validation enforces `stop_loss < entry_price < target_price` and all price levels within ±30% of current close

### Report Content

- [ ] **REPORT-01**: AI report includes entry zone as a price range (from nearest_support + Bollinger band range), with fallback to `close ± 2%` for low-history stocks
- [ ] **REPORT-02**: AI report includes stop-loss (max(support_2, close × 0.93) — HOSE ±7% limit aware) and target price (nearest_resistance or close × 1.10)
- [ ] **REPORT-03**: AI report includes risk rating (Literal["high","medium","low"]) with Vietnamese reasoning from LLM
- [ ] **REPORT-04**: AI report includes signal conflict explanation when |tech_score − fund_score| > 25, naming the conflicting signals and LLM's resolution
- [ ] **REPORT-05**: AI report includes recent catalyst section synthesized by LLM from 7-day news articles + composite score delta

### Frontend

- [ ] **FRONTEND-01**: `/stock/[symbol]` shows dedicated Trade Plan section with entry zone, stop-loss, and target price formatted in VND (e.g., 45.200đ)
- [ ] **FRONTEND-02**: Trade Plan section shows colored risk badge (red=high, yellow=medium, green=low) with tooltip displaying Vietnamese reasoning text
- [ ] **FRONTEND-03**: Signal conflict section conditionally rendered — only shown when `signal_conflicts` field is non-null in report

## v2 Requirements

Deferred — not in current roadmap.

### Advanced Signals

- **SIGNAL-04**: Multi-timeframe candlestick analysis (weekly + daily pattern agreement)
- **SIGNAL-05**: TA-Lib full 60-pattern integration (requires C binary system dependency)
- **SIGNAL-06**: Intraday volume profile signals

### Advanced Analysis

- **REPORT-06**: Backtesting accuracy of historical price-level recommendations
- **REPORT-07**: ML-based price target prediction

## Out of Scope

| Feature | Reason |
|---------|--------|
| TA-Lib pattern library | Requires C binary system dependency not installed; pure OHLC math for needed patterns |
| Real-time price alerts | Out of scope for v1.4 — alert system is a separate milestone |
| Multi-timeframe analysis | Complexity; daily OHLCV is sufficient for entry/exit quality in v1.4 |
| Backtesting | Not needed to ship better recommendations; v2 candidate |
| New API endpoints | content_json JSONB absorbs new fields automatically — no new routes needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SIGNAL-01 | Phase 18 | Complete |
| SIGNAL-02 | Phase 18 | Complete |
| SIGNAL-03 | Phase 18 | Complete |
| PROMPT-01 | Phase 19 | Pending |
| PROMPT-02 | Phase 19 | Pending |
| PROMPT-03 | Phase 19 | Pending |
| PROMPT-04 | Phase 19 | Pending |
| REPORT-01 | Phase 20 | Pending |
| REPORT-02 | Phase 20 | Pending |
| REPORT-03 | Phase 20 | Pending |
| REPORT-04 | Phase 20 | Pending |
| REPORT-05 | Phase 20 | Pending |
| FRONTEND-01 | Phase 21 | Pending |
| FRONTEND-02 | Phase 21 | Pending |
| FRONTEND-03 | Phase 21 | Pending |

**Coverage:**
- v1.4 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-25*
*Last updated: 2026-04-25 after initial definition*
