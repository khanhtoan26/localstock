# Roadmap: LocalStock

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-04-16) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 UX Polish & Educational Depth** — Phases 7-10 (shipped 2026-04-21) — [Archive](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Admin Console** — Phases 11-13 (shipped 2026-04-23) — [Archive](milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 UI/UX Refinement** — Phases 14-17 (shipped 2026-04-25) — [Archive](milestones/v1.3-ROADMAP.md)
- 🚧 **v1.4 AI Analysis Depth** — Phases 18-21 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-04-16</summary>

- [x] Phase 1: Foundation & Data Pipeline (4/4 plans) — completed 2026-04-14
- [x] Phase 2: Technical & Fundamental Analysis (4/4 plans) — completed 2026-04-14
- [x] Phase 3: Sentiment Analysis & Scoring Engine (4/4 plans) — completed 2026-04-15
- [x] Phase 4: AI Reports, Macro Context & T+3 Awareness (4/4 plans) — completed 2026-04-15
- [x] Phase 5: Automation & Notifications (3/3 plans) — completed 2026-04-15
- [x] Phase 6: Web Dashboard (4/4 plans) — completed 2026-04-16

</details>

<details>
<summary>✅ v1.1 UX Polish & Educational Depth (Phases 7-10) — SHIPPED 2026-04-21</summary>

- [x] Phase 7: Theme Foundation & Visual Identity (4/4 plans) — completed 2026-04-20
- [x] Phase 8: Stock Page Reading-First Redesign (merged into Phase 7) — completed 2026-04-20
- [x] Phase 9: Academic/Learning Page & Glossary Data (2/2 plans) — completed 2026-04-20
- [x] Phase 10: Interactive Glossary Linking (2/2 plans) — completed 2026-04-21

</details>

<details>
<summary>✅ v1.2 Admin Console (Phases 11-13) — SHIPPED 2026-04-23</summary>

- [x] Phase 11: Admin API Endpoints (2/2 plans) — completed 2026-04-22
- [x] Phase 12: Admin Console UI (2/2 plans) — completed 2026-04-22
- [x] Phase 12.1: Performance & Polish (2/2 plans) — completed 2026-04-23
- [x] Phase 13: AI Report Generation UI (2/2 plans) — completed 2026-04-23

</details>

<details>
<summary>✅ v1.3 UI/UX Refinement (Phases 14-17) — SHIPPED 2026-04-25</summary>

- [x] Phase 14: Visual Foundation — Source Sans 3 font + warm neutral color palette (1/1 plans) — completed 2026-04-24
- [x] Phase 15: Sidebar Redesign — Claude Desktop floating card sidebar (3/3 plans) — completed 2026-04-24
- [x] Phase 16: Table, Search & Session Bar — Sort fix, search filter, HOSE session bar (6/6 plans) — completed 2026-04-25
- [x] Phase 17: Market Overview Metrics — Live 4-card market summary + backend API (4/4 plans) — completed 2026-04-25

</details>

### 🚧 v1.4 AI Analysis Depth (In Progress)

**Milestone Goal:** Transform robotic AI recommendations into actionable trade guidance — with price levels, signal conflict resolution, recent catalysts, and explicit risk ratings.

- [x] **Phase 18: Signal Computation** - Candlestick pattern detection + volume divergence + sector momentum signal methods
- [ ] **Phase 19: Prompt & Schema Restructuring** - Expanded StockReport Pydantic model + restructured prompts + context window + post-generation validation
- [ ] **Phase 20: Service Wiring & Report Content** - Full pipeline integration delivering entry/stop-loss/target/risk/conflict/catalyst in every report
- [ ] **Phase 21: Frontend Trade Plan Display** - TradePlanSection on stock detail page with VND-formatted prices, risk badge, and conditional conflict section

## Phase Details

### Phase 18: Signal Computation
**Goal**: The analysis engine can compute three new signal types — candlestick patterns, volume divergence, and sector momentum — available as structured data for injection into downstream prompts
**Depends on**: Phase 17 (v1.3 complete)
**Requirements**: SIGNAL-01, SIGNAL-02, SIGNAL-03
**Success Criteria** (what must be TRUE):
  1. Given any OHLCV DataFrame, the system detects and returns presence/absence of all 5 candlestick patterns (doji, inside, hammer, engulfing, shooting star) using pandas-ta native functions and pure OHLC math — no TA-Lib required
  2. For a stock with avg_volume >= 100k shares/day, the system returns a volume divergence signal (MFI/CMF/OBV-based); for a low-liquidity stock below that threshold, it returns null without error
  3. The system reads sector momentum from SectorSnapshot and returns it as a named scalar value ready for LLM prompt injection per stock
  4. All three signal methods are independently unit-testable with a synthetic DataFrame — no live DB or network calls required
**Plans**: 4 plans

Plans:
- [x] 18-01-PLAN.md — Test stubs + signals.py module stub (Wave 0)
- [x] 18-02-PLAN.md — compute_candlestick_patterns() + SIGNAL-01 tests (Wave 1)
- [x] 18-03-PLAN.md — compute_volume_divergence() + SIGNAL-02 tests (Wave 1)
- [x] 18-04-PLAN.md — compute_sector_momentum() + SIGNAL-03 tests (Wave 2)

### Phase 19: Prompt & Schema Restructuring
**Goal**: The StockReport Pydantic model and Ollama prompt are restructured to accommodate new trade guidance fields, with the context window enlarged and output validated post-generation
**Depends on**: Phase 18
**Requirements**: PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04
**Success Criteria** (what must be TRUE):
  1. The Ollama client is called with num_ctx >= 6144 tokens before any new prompt content is added, and this is verified by a unit test or config assertion
  2. StockReport gains six new Optional fields (entry_price, stop_loss, target_price, risk_rating, catalyst, signal_conflicts) — all default to None so existing deserialization of old reports does not break
  3. Prompts explicitly name S/R anchors (nearest_support, nearest_resistance, support_1/2, resistance_1/2, pivot_point), candlestick patterns, volume divergence, and sector momentum as distinct context variables in the formatted prompt string
  4. Post-generation validation rejects any LLM output where stop_loss >= entry_price or entry_price >= target_price, or where any price level falls outside ±30% of the current close — returning a safe fallback rather than crashing
**Plans**: 3 plans

Plans:
- [ ] 19-01-PLAN.md — StockReport schema extension (6 Optional fields) + num_ctx 8192 + backward compat tests
- [ ] 19-02-PLAN.md — Prompt restructuring (system rules + 🔔 TÍN HIỆU BỔ SUNG section) + signal formatters
- [ ] 19-03-PLAN.md — Post-generation price validation + risk_rating normalization + service wiring

### Phase 20: Service Wiring & Report Content
**Goal**: Every generated stock report contains entry zone, stop-loss, target price, risk rating, signal conflict explanation, and recent catalyst — fully integrated through ReportService and persisted via content_json
**Depends on**: Phase 19
**Requirements**: REPORT-01, REPORT-02, REPORT-03, REPORT-04, REPORT-05
**Success Criteria** (what must be TRUE):
  1. A generated report for any stock includes an entry zone expressed as a price range (nearest_support + Bollinger band range), with automatic fallback to close ± 2% for stocks with fewer than 40 price history rows
  2. A generated report includes stop-loss set to max(support_2, close × 0.93) and target price set to nearest_resistance or close × 1.10 — both reflecting HOSE ±7% daily limit awareness
  3. A generated report includes a risk rating of "high", "medium", or "low" with Vietnamese reasoning text explaining the rating
  4. When |tech_score − fund_score| > 25, the report includes a signal conflict explanation naming the conflicting signals and the LLM's resolution; when the gap is <= 25, the field is null
  5. A generated report includes a recent catalyst section synthesized from the past 7 days of news articles plus the composite score delta since the prior run
**Plans**: 2 plans

Plans:
- [ ] 20-01-PLAN.md — Pure computation functions (entry zone, SL/TP, signal conflict) + TDD tests
- [ ] 20-02-PLAN.md — Service wiring (both methods) + prompt template extension + catalyst + integration tests

### Phase 21: Frontend Trade Plan Display
**Goal**: The stock detail page shows a dedicated Trade Plan section that surfaces entry zone, stop-loss, target price, risk badge, and signal conflict — all conditionally rendered from the existing report API response
**Depends on**: Phase 20
**Requirements**: FRONTEND-01, FRONTEND-02, FRONTEND-03
**Success Criteria** (what must be TRUE):
  1. The /stock/[symbol] page renders a Trade Plan section showing entry zone, stop-loss, and target price formatted in VND notation (e.g., 45.200d) when those fields are present in the report
  2. The Trade Plan section displays a colored risk badge — red for "high", yellow for "medium", green for "low" — with a tooltip that shows the Vietnamese reasoning text from the LLM
  3. A signal conflict subsection is conditionally rendered only when the signal_conflicts field is non-null in the report response; it is completely absent from the DOM when the field is null
  4. The Trade Plan section degrades gracefully when report data is loading or when the report predates v1.4 (all new fields null) — no layout breaks or unhandled errors
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | v1.0 | 4/4 | Complete | 2026-04-14 |
| 2. Technical & Fundamental Analysis | v1.0 | 4/4 | Complete | 2026-04-14 |
| 3. Sentiment Analysis & Scoring Engine | v1.0 | 4/4 | Complete | 2026-04-15 |
| 4. AI Reports, Macro Context & T+3 | v1.0 | 4/4 | Complete | 2026-04-15 |
| 5. Automation & Notifications | v1.0 | 3/3 | Complete | 2026-04-15 |
| 6. Web Dashboard | v1.0 | 4/4 | Complete | 2026-04-16 |
| 7. Theme Foundation & Visual Identity | v1.1 | 4/4 | Complete | 2026-04-20 |
| 8. Stock Page Reading-First Redesign | v1.1 | - | Complete (merged) | 2026-04-20 |
| 9. Academic/Learning Page & Glossary Data | v1.1 | 2/2 | Complete | 2026-04-20 |
| 10. Interactive Glossary Linking | v1.1 | 2/2 | Complete | 2026-04-21 |
| 11. Admin API Endpoints | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12. Admin Console UI | v1.2 | 2/2 | Complete | 2026-04-22 |
| 12.1 Performance & Polish | v1.2 | 2/2 | Complete | 2026-04-23 |
| 13. AI Report Generation UI | v1.2 | 2/2 | Complete | 2026-04-23 |
| 14. Visual Foundation | v1.3 | 1/1 | Complete | 2026-04-24 |
| 15. Sidebar Redesign | v1.3 | 3/3 | Complete | 2026-04-24 |
| 16. Table, Search & Session Bar | v1.3 | 6/6 | Complete | 2026-04-25 |
| 17. Market Overview Metrics | v1.3 | 4/4 | Complete | 2026-04-25 |
| 18. Signal Computation | v1.4 | 4/4 | Complete | 2026-04-26 |
| 19. Prompt & Schema Restructuring | v1.4 | 0/? | Not started | - |
| 20. Service Wiring & Report Content | v1.4 | 0/? | Not started | - |
| 21. Frontend Trade Plan Display | v1.4 | 0/? | Not started | - |

## Backlog

### Phase 999.1: Paper Trading Emulator (BACKLOG)

**Goal:** Giả lập mua/bán cổ phiếu (paper trading) để kiểm chứng độ chính xác của khuyến nghị AI. Người dùng đặt lệnh mua thử với số lượng tùy chọn, hệ thống theo dõi P&L theo thời gian thực để đánh giá nhận định đúng/sai.

**Requirements:** TBD

**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
