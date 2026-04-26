# Feature Landscape — LocalStock v1.4 AI Analysis Depth

**Domain:** AI-powered actionable trade guidance for Vietnamese retail stock analysis (HOSE)
**Researched:** 2026-04-25
**Confidence:** HIGH (derived from existing codebase + confirmed library capabilities)

---

## Vietnamese Retail Trading Context

Before mapping features, understanding the HOSE retail trader context is essential:

**T+3 settlement rule:** Stocks bought today cannot be sold until 3 working days later. This is already encoded in the system (t3.py). Every trade recommendation must be evaluated through this lens — an "entry zone" does not mean "buy at open"; it means "price range worth entering knowing you hold minimum 3 days."

**Price terminology used by Vietnamese retail traders:**

| Vietnamese term | English equivalent | Practical meaning in HOSE context |
|-----------------|--------------------|------------------------------------|
| Vùng mua / Vùng vào lệnh | Entry zone | Price range considered acceptable to open a position — typically a spread between nearest support and current price, not a single number |
| Cắt lỗ / Dừng lỗ | Stop-loss | Hard exit price if thesis breaks — in Vietnam, retail often sets this at -7% to -10% from entry (circuit breaker reference point), or at nearest support level minus a buffer |
| Chốt lời / Mục tiêu | Target / Take-profit | Price to exit with profit — typically nearest resistance level or a % gain target |
| Rủi ro cao / trung bình / thấp | Risk rating | High: no clear trend + low liquidity + macro headwinds; Medium: mixed signals; Low: strong trend + above-average volume + macro tailwind |
| Tín hiệu xung đột | Signal conflict | Technical says buy (uptrend, RSI recovering) but fundamental says avoid (high P/E, poor ROE) — or vice versa |
| Chất xúc tác / Catalyst | Recent catalyst | Quarterly earnings beat, policy change, macro event, sector rotation — the "why now" factor |

**HOSE-specific constraints that affect price level computation:**
- Prices are quoted in thousands VND (e.g., 25.6 means 25,600 VND/share)
- Daily price limits: ±7% (HOSE), making intraday stop-loss math straightforward
- Circuit breaker awareness: a stop-loss below -7% from a single-day purchase cannot be triggered same day
- Minimum tick size varies by price range (0.1 for < 10K VND, 0.5 for 10K-50K, 1.0 for > 50K) — entry zones must respect ticks

---

## Feature Landscape

### Table Stakes (Users Expect These)

These 7 features are committed scope for v1.4. Missing any makes the milestone incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Entry zone in report | Current report has no actionable price guidance — "mua" without a price is useless | MEDIUM | Compute from nearest_support (already in DB) + Bollinger lower band + a small buffer; express as range (e.g., "24,500–25,200 VND") |
| Stop-loss level in report | Without a stop-loss, report cannot be called actionable; Vietnamese traders expect this | MEDIUM | Compute as: max(support_2, close × 0.93) — hard floor at 7% daily limit awareness; expose as single price not a range |
| Target price in report | Corollary to entry zone — completing the trade thesis requires an exit target | MEDIUM | Nearest resistance (already in DB), or resistance_1 if no historical resistance found; express as price + % upside from entry zone midpoint |
| Signal conflict detection | "Technical score 70, fundamental score 30" is meaningless without explanation of what disagrees | MEDIUM | Rule-based: when technical ≥ 60 and fundamental ≤ 40 (or vice versa), flag conflict; LLM explains in conflict_analysis field |
| Recent catalyst section | Report currently reads like a static snapshot; traders need to know what changed this week | HIGH | Requires: (a) filter news from last 7 days, (b) detect score delta from previous score, (c) feed both to LLM for catalyst synthesis |
| Explicit risk rating | "Cao / Trung bình / Thấp" with reasoning; currently no such field in StockReport schema | LOW | Rule-based risk score from: trend strength, RSI extremes, volume confirmation, fundamental quality, macro direction — LLM adds reasoning text |
| Candlestick pattern signals | Traders recognize hammer/doji/engulfing visually; LLM needs this as input signal | MEDIUM | Use pandas-ta native `cdl_doji()` + `cdl_inside()` (no TA-Lib dependency); implement hammer/engulfing/morning star manually (4-line formula — well-documented) |

### Differentiators (Competitive Advantage)

Features beyond the committed scope that add meaningful value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Volume divergence signal | Price up + volume down = weak rally; price down + volume up = capitulation — feeds LLM with richer context | LOW | Already have relative_volume and volume_trend in DB; divergence = close_change direction vs volume_trend direction mismatch; add divergence_signal field |
| Sector momentum context | "Ngân hàng đang được dòng tiền chú ý tuần này" adds actionable macro context | LOW | SectorService already computes avg_score_change; feed sector's inflow/outflow status to report prompt — one additional field |
| Risk-reward ratio display | Auto-compute (target − entry_midpoint) / (entry_midpoint − stop_loss); display "2.5:1 R/R" | LOW | Pure math from other computed fields; add to StockReport output |
| Restructured report JSON schema | Current StockReport has 9 free-text fields; new schema should have typed price levels and rating fields | MEDIUM | Extend StockReport Pydantic model with: entry_zone_low, entry_zone_high, stop_loss, target_price, risk_rating, risk_reasoning, signal_conflict, conflict_explanation, catalyst_summary — backend migration required |

### Anti-Features

Features that seem related but should not be built in v1.4.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Backtesting for price levels | "Does our stop-loss formula work historically?" is valuable but complex; would double the scope | Flag as v2 candidate; use simple algorithmic rules for v1.4 |
| Exact single entry price (not zone) | Looks precise but creates false confidence; single price ignores bid-ask spread and tick sizes | Always express as zone (low_price–high_price range) |
| Machine learning price prediction | Requires labeled training data, validation infrastructure, significant engineering; LLM on RTX 3060 is already the AI budget | Use rule-based price level computation; LLM only for narrative interpretation |
| Multiple timeframe candlestick analysis | Weekly/monthly patterns require fetching >200 rows of extra data per symbol × 400 stocks | Daily timeframe only for v1.4; weekly is v2 |
| Real-time candlestick pattern alerts | System runs once daily post-market; intraday detection would require live data stream | Keep daily batch model |
| TA-Lib dependency for candlestick patterns | TA-Lib installation is complex (C library), unreliable on Linux without extra setup; current pyproject.toml has no talib | Implement hammer/engulfing/morning star/evening star manually — they are 3-5 line formulas; use pandas-ta `cdl_doji()` and `cdl_inside()` natively available |

---

## Feature Dependencies

```
[Existing DB data — already computed and stored]
    nearest_support, nearest_resistance, support_1, support_2,
    resistance_1, resistance_2, pivot_point, close_price
    rsi_14, macd_histogram, trend_direction, trend_strength
    relative_volume, volume_trend
    avg_score_change (SectorService)
    technical_score, fundamental_score (CompositeScore)
        │
        ├──requires──> [A] Price Level Computation (entry zone, stop-loss, target)
        │                   └──feeds──> [E] Restructured StockReport JSON schema
        │
        ├──requires──> [B] Signal Conflict Detection (rule-based)
        │                   └──feeds──> [E] Restructured StockReport JSON schema
        │
        ├──requires──> [C] Risk Rating (rule-based)
        │                   └──feeds──> [E] Restructured StockReport JSON schema
        │
        ├──requires──> [D] Candlestick Pattern Detection (manual + native pandas-ta)
        │                   └──feeds──> [F] Updated REPORT_USER_TEMPLATE
        │                   └──feeds──> [E] Restructured StockReport JSON schema
        │
        ├──requires──> [G] Volume Divergence Signal
        │                   └──feeds──> [F] Updated REPORT_USER_TEMPLATE
        │
        └──requires──> [H] Sector Momentum Signal
                            └──feeds──> [F] Updated REPORT_USER_TEMPLATE

[Recent News — last 7 days]
    + [Score delta vs previous CompositeScore]
        │
        └──requires──> [I] Catalyst Detection (LLM synthesis from news delta + score delta)
                            └──feeds──> [E] Restructured StockReport JSON schema

[E] Restructured StockReport JSON schema
    └──requires──> [F] Updated REPORT_USER_TEMPLATE (new fields injected into prompt)
    └──requires──> [J] Updated report_service.py (new fields assembled from A, B, C, D, I)
    └──requires──> [K] Updated ReportDataBuilder (new data assembly)
    └──requires──> Updated REPORT_SYSTEM_PROMPT (instruct LLM to populate new fields)
    └──enhances──> Updated Helios frontend (display new fields in stock detail page)
```

### Dependency Notes

- **Price levels require existing S/R data:** `nearest_support`, `nearest_resistance`, `support_2`, `resistance_1` already stored in `technical_indicators` table — no new crawling needed.

- **Signal conflict is independent of LLM:** The rule-based detection (technical_score vs fundamental_score delta) can run before the LLM call and be injected into the prompt. LLM only writes the explanation narrative.

- **Candlestick patterns must be computed before report generation:** Pattern detection output (hammer? doji? engulfing?) must be in the prompt so the LLM can incorporate it into technical_analysis and the pattern_signals field.

- **Catalyst detection has the hardest dependency:** Requires both (a) news from the last 7 days tagged to the symbol — already in `sentiment_scores` with `article_id` FK to `news_articles.published_at` — and (b) score delta from `composite_scores` history. Both are available; no new crawling needed.

- **Sector momentum is the easiest new signal:** `SectorService.get_rotation_summary()` already returns inflow/outflow lists. Just add the stock's sector status to the prompt template.

- **Frontend comes last:** All new fields flow naturally once the backend StockReport schema is extended. The stock detail page simply renders additional sections.

---

## MVP Definition

### Must Ship in v1.4

- [x] **Price levels (entry zone, stop-loss, target)** — core of "actionable trade guidance"; everything else is secondary
- [x] **Risk rating with reasoning** — simplest new field; high user value; rule-based so no LLM latency increase
- [x] **Restructured StockReport JSON schema** — enables all new fields; must happen early to unblock everything else
- [x] **Signal conflict detection** — addresses the most common user frustration ("why does it say Buy when fundamentals are bad?")
- [x] **Candlestick pattern signals (doji, hammer, inside bar + manual patterns)** — feeds LLM with price action context; doji/inside bar available natively without TA-Lib; hammer/engulfing/morning star/evening star implementable with manual formulas

### Add After Core Is Working

- [ ] **Recent catalyst section** — highest complexity (cross-joining news + score history + LLM); implement after schema extension is stable
- [ ] **Volume divergence signal** — low complexity but low user impact compared to price levels; add in same phase as candlestick patterns
- [ ] **Sector momentum in prompt** — one-liner addition to template; add last as it's pure signal injection
- [ ] **Frontend display of new fields** — update stock detail page to render entry_zone, stop_loss, target_price, risk_rating in structured UI components

### Future Consideration (v2+)

- [ ] **Backtesting price level accuracy** — did our stop-loss formula protect capital?
- [ ] **TA-Lib integration for 60+ candlestick patterns** — requires Linux system dependency; defer until environment is confirmed
- [ ] **Intraday candlestick signals** — requires live price feed
- [ ] **Weekly/monthly pattern recognition** — multi-timeframe analysis

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Entry zone + stop-loss + target price | HIGH | MEDIUM | P1 |
| Restructured StockReport JSON schema | HIGH (enables everything) | MEDIUM | P1 |
| Risk rating with reasoning | HIGH | LOW | P1 |
| Signal conflict detection + explanation | HIGH | MEDIUM | P1 |
| Candlestick pattern signals | MEDIUM | MEDIUM | P1 |
| Updated REPORT_USER_TEMPLATE + REPORT_SYSTEM_PROMPT | HIGH (ties all signals together) | MEDIUM | P1 |
| Recent catalyst section | HIGH | HIGH | P2 |
| Volume divergence signal | MEDIUM | LOW | P2 |
| Sector momentum in prompt | MEDIUM | LOW | P2 |
| Frontend display of new fields | MEDIUM | MEDIUM | P2 |

**Priority key:** P1 = must have for milestone; P2 = complete if P1 stable

---

## Implementation Detail: How Each Feature Works

### A. Price Level Computation

**Entry zone:**
```
entry_low  = max(nearest_support, bb_lower)       # floor: don't enter below support
entry_high = min(close × 1.005, bb_middle)         # ceiling: don't chase more than 0.5% above close
```
Both values exist in DB. If nearest_support is None, fall back to `close × 0.97` (−3% from close, ~half of daily limit).

**Stop-loss:**
```
stop_loss = max(support_2, close × 0.93)           # hard floor at 7% total risk
```
If support_2 is None, use `close × 0.93`. Express in thousands VND format (matching HOSE price display convention).

**Target price:**
```
target = nearest_resistance or resistance_1        # first meaningful overhead resistance
```
If both are None, use `close × 1.10` (10% gain, typical for 2-3 week swing trade through T+3).

### B. Signal Conflict Detection

Rule-based classification before LLM call:
```python
conflict = abs(technical_score - fundamental_score) > 25  # threshold
conflict_type = "tech_bullish_fund_bearish" if technical_score > fundamental_score else "fund_bullish_tech_bearish"
```
Feed `conflict=True/False` and `conflict_type` into prompt. LLM writes `conflict_explanation` only when `conflict=True`.

### C. Risk Rating

Score 0-3 risk factors:
- RSI > 70 or RSI < 30 (extreme momentum) → +1 risk
- trend_direction = "sideways" or trend_strength < 20 → +1 risk
- fundamental_score < 40 (weak fundamentals) → +1 risk
- macro_score < 40 → +1 risk (optional)

Map: 0 factors → "thấp"; 1-2 → "trung bình"; 3+ → "cao"

### D. Candlestick Pattern Detection

**No TA-Lib required — confirmed via codebase testing:**

Native pandas-ta (already installed):
- `ta.cdl_doji()` — works without TA-Lib, tested
- `ta.cdl_inside()` — works without TA-Lib, tested

Manual implementation (3-5 line formulas, HIGH confidence, standard financial formulas):
- **Hammer:** Small body in upper 1/3, lower shadow ≥ 2× body, upper shadow ≤ body/2; must occur after downtrend
- **Engulfing (bullish):** Current candle's body completely engulfs previous candle's body; close > prev_open and open < prev_close (for bullish)
- **Morning star:** 3-candle pattern — large bearish → small body (gap down) → large bullish close above midpoint of candle 1
- **Evening star:** Inverse of morning star

Output: dict with `{pattern_name: True/False}` for last candle — inject all detected patterns into prompt as a list string.

### E. Catalyst Detection

Approach — LLM synthesis from structured inputs (no hallucination risk because inputs are filtered):
1. Query `news_articles` where `published_at >= today - 7 days`, joined to `sentiment_scores` for the symbol
2. Query previous `composite_scores` row (t-1) and compute score delta for each dimension
3. Pass to LLM: recent article titles + score_delta dict
4. LLM writes `catalyst_summary`: "Tuần này: [earnings beat / regulatory news / sector rotation] khiến điểm kỹ thuật tăng 8.2 điểm"

This works well for LLMs because:
- Inputs are structured and factual (no generation of price data)
- Task is summarization, not prediction — LLM's strength
- Context window impact is bounded (7 days of titles for one symbol = ~20 articles max)

### F. Volume Divergence

```python
volume_divergence = None
if volume_trend and close_change is not None:
    if close_change > 0 and volume_trend == "decreasing":
        volume_divergence = "bearish_divergence"   # rally without volume = weak
    elif close_change < 0 and volume_trend == "increasing":
        volume_divergence = "capitulation"          # selloff with volume = potential bottom
    elif close_change > 0 and volume_trend == "increasing":
        volume_divergence = "bullish_confirmation"
    else:
        volume_divergence = "neutral"
```

Feed as single string into prompt template.

---

## Competitor Feature Analysis

Comparing against tools available to Vietnamese retail traders (HIGH confidence — direct knowledge of these tools):

| Feature | FireAnt / SSI iBoard | Simplize / Fstock | LocalStock v1.4 |
|---------|---------------------|-------------------|-----------------|
| Price levels in AI report | Basic TP only | TP + SL with formula | Entry zone + SL + TP, Vietnam-adapted formulas |
| Signal conflict explanation | None | None | Explicit LLM explanation with conflict_type |
| Catalyst section | Manual news timeline | Automated catalyst tags | LLM synthesis from recent news + score delta |
| Risk rating | None or color-coded | Low/Med/High (unweighted) | Rule-based multi-factor + LLM reasoning in Vietnamese |
| Candlestick patterns | Chart overlay only | Chart overlay only | Fed to LLM as text signals in report |
| T+3 integration | Warning only | Warning only | Embedded in every swing trade suggestion |
| Vietnamese language | Yes | Yes | Yes (primary design constraint) |
| Local LLM | No (paid API) | No | Yes (RTX 3060, cost-free) |

**LocalStock differentiator:** The combination of all signals synthesized into a single Vietnamese-language narrative via a local LLM — competitors either show raw indicators or use English-language AI. The new v1.4 features close the gap between "analysis tool" and "personal trading advisor."

---

## Sources

- Codebase audit: `/apps/prometheus/src/localstock/` (all analysis, reports, scoring, and AI modules)
- pandas-ta candlestick capabilities: confirmed via `uv run python` testing (2026-04-25) — `cdl_doji` and `cdl_inside` work natively; `cdl_pattern` requires TA-Lib (NOT installed)
- Context7 `/xgboosted/pandas-ta-classic` docs: confirmed hammer/engulfing/morning star need TA-Lib for `cdl_pattern()`, but manual formulas are standard
- HOSE market rules: T+3 settlement, ±7% daily limit, price tick sizes — HIGH confidence, built into existing system (t3.py, scheduler/calendar.py)
- Price level formulas: standard technical analysis (support/resistance-based entry zones) adapted for HOSE convention — MEDIUM confidence (formulas are standard; exact thresholds are opinionated)
- Vietnamese trading terminology: HIGH confidence from domain knowledge consistent with CafeF/VnExpress content patterns observed in news_crawler.py

---

*Feature research for: AI Analysis Depth — actionable trade guidance for Vietnamese HOSE stock analysis*
*Researched: 2026-04-25*
