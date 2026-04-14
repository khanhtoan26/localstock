# Feature Research

**Domain:** AI Stock Analysis Agent — Vietnamese Market (HOSE)
**Researched:** 2026-04-14
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

These are non-negotiable. Without them the tool delivers no value as a stock analysis agent.

#### Data Acquisition Layer

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Price/Volume data crawling** (~400 HOSE tickers) | No data = no analysis. Every tool from CafeF to Simplize starts here | MEDIUM | Use vnstock library (VCI/KBS sources). Need OHLCV daily + intraday. ~400 tickers, batch crawl after market close (15:00) |
| **Historical price data** (≥2 years) | Technical analysis needs history for MA200, yearly comparisons, trend identification | MEDIUM | Store locally in DB. Backfill on first run. Incremental daily updates after |
| **Financial statement data** (quarterly + annual) | P/E, EPS, ROE are meaningless without income statement + balance sheet | MEDIUM | vnstock provides `finance.income_statement()`, `finance.balance_sheet()`, `finance.cash_flow()`, `finance.ratio()`. Quarterly cadence |
| **Company profile/listing info** | Need sector, industry, market cap, float for context | LOW | Static data, update monthly. vnstock provides listing info |

#### Technical Analysis

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Core technical indicators** (MA, RSI, MACD, Bollinger Bands) | Every stock tool from TradingView to Fireant has these. Bare minimum for technical signals | LOW | Use ta-lib or pandas-ta. Calculate: SMA(20,50,200), EMA(12,26), RSI(14), MACD(12,26,9), Bollinger(20,2) |
| **Volume analysis** (avg volume, relative volume, volume trend) | Volume confirms price moves. Without it, signals are unreliable | LOW | Simple calculations on OHLCV data |
| **Trend identification** (uptrend/downtrend/sideways) | Users need to know: is this stock going up or down? | LOW | Derive from MA crossovers + price action |
| **Support/Resistance levels** | Key decision points for entry/exit | MEDIUM | Pivot points, recent highs/lows. Algorithmic detection |

#### Fundamental Analysis

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Key financial ratios** (P/E, P/B, EPS, ROE, ROA, D/E) | Simplize, WiChart, VnDirect all show these. Table stakes for any stock tool | LOW | Calculate from financial statements. vnstock `finance.ratio()` provides most |
| **Revenue/profit growth** (QoQ, YoY) | Growth trajectory is the #1 fundamental signal | LOW | Compare sequential quarters/years from income statements |
| **Industry comparison** | A stock's P/E means nothing without industry context | MEDIUM | Group by ICB/GICS sector, calculate industry averages for comparison |

#### Scoring & Ranking

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Composite stock score** (e.g., 85/100) | Core value proposition per PROJECT.md. This IS the product | HIGH | Multi-dimensional: technical score + fundamental score + sentiment score + macro score → weighted composite. Like Danelfin's AI Score (1-10) or TipRanks Smart Score |
| **Ranked stock list** (top N recommendations) | Users want "what should I look at?" not "here's 400 stocks" | MEDIUM | Sort by composite score. Top 10-20 with clear reasoning |
| **Per-stock analysis report** | Users need to understand WHY a score is high/low | HIGH | LLM synthesizes all dimensions into readable Vietnamese report |

#### Scheduling & Automation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Scheduled daily run** (after market close) | Agent must be autonomous — that's the whole point | MEDIUM | Cron-like scheduler. Run after 15:30 when market data settles. Crawl → Calculate → Score → Report → Notify |
| **On-demand analysis** (single stock or full scan) | Sometimes you want answers NOW, not tomorrow | MEDIUM | CLI or API trigger. "Analyze VNM right now" |

#### Output & Notification

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Telegram notifications** | Per PROJECT.md requirement. Push alerts when high-confidence picks emerge | MEDIUM | Telegram Bot API. Send daily digest + special alerts for score changes |
| **Web dashboard** (basic) | Need visual interface to browse scores, charts, reports | HIGH | Table of ranked stocks, click into detail view with charts + report. Simplize/WiChart level of presentation not needed — functional is fine |

### Differentiators (Competitive Advantage)

These set LocalStock apart from existing Vietnamese platforms like Simplize, Fireant, WiChart.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **LLM-synthesized narrative reports** (Vietnamese) | Existing tools show numbers. LocalStock EXPLAINS them in natural Vietnamese. "VNM's P/E of 18 is 20% above dairy industry average of 15, suggesting premium valuation justified by 12% YoY revenue growth" | HIGH | Ollama (Qwen2.5 7B or similar) generates Vietnamese analysis. This is the killer feature — no VN tool does this well with local LLM |
| **Multi-dimensional score fusion** | Simplize has technical signals. WiChart has fundamentals. Nobody combines tech + fundamental + sentiment + macro into one score with LLM reasoning | HIGH | Weighted scoring: Technical (30%) + Fundamental (30%) + Sentiment (20%) + Macro (20%). Weights adjustable. LLM provides qualitative override |
| **Vietnamese news sentiment analysis** | CafeF/VnExpress/Thanh Niên financial news analyzed for sentiment. Most tools ignore Vietnamese NLP | HIGH | Crawl Vietnamese financial news → LLM classifies positive/negative/neutral per ticker. Vietnamese-capable LLM (Qwen, Vistral) critical |
| **Macro-economic context linking** | No VN tool connects macro (SBV interest rates, CPI, USD/VND) to individual stock impact. "Rising interest rates → negative for REE, positive for banking" | MEDIUM | Crawl SBV data, GSO statistics. LLM interprets macro → sector/stock impact |
| **Zero-cost, fully local** | Simplize charges 499k-1.99M VND/month for premium. Fireant has paid tiers. LocalStock = free forever, runs on your GPU | LOW | Architecture decision, not a feature to build. But a key differentiator in positioning |
| **Customizable scoring weights** | Personal tool means personal preferences. Prefer technical over fundamental? Adjust weights | LOW | Config file with weight parameters. No UI needed initially |
| **Score change alerts** | "VNM score dropped from 85 to 60 because of earnings miss" — proactive monitoring | MEDIUM | Compare today's scores vs yesterday. Alert on significant changes (>15 points) via Telegram |
| **Sector rotation analysis** | Identify which sectors are gaining/losing momentum. "Money flowing from banking to real estate" | MEDIUM | Aggregate sector-level scores and track trends over time |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-trading (buy/sell execution)** | "If it knows what to buy, why not just buy it?" | Legal liability, financial risk, API complexity with VN brokers (SSI/VnDirect APIs are unreliable), emotional/trust issues when real money is at stake. PROJECT.md explicitly excludes this | Recommendation-only with clear "this is not financial advice" disclaimer. Provide entry/exit price levels as guidance |
| **Real-time tick-by-tick data** | "I want live prices!" | Massive infrastructure cost, unnecessary for daily analysis approach, WebSocket complexity, VN market data vendors charge for real-time feeds | End-of-day analysis is sufficient. On-demand can use 15-min delayed data from free sources. Intraday snapshots at most |
| **Portfolio tracking with P&L** | "Track my actual positions and returns" | Scope creep into portfolio management — a different product entirely. Requires transaction logging, cost basis tracking, tax calculation | Focus on discovery/analysis. Users track portfolios in broker apps (SSI, VnDirect, TCBS) which do this well |
| **Backtesting engine** | "Let me test my strategy on historical data" | Massive complexity (survivorship bias, look-ahead bias, slippage modeling). A whole product in itself | Provide historical score accuracy metrics. "Last month's top 10 scored stocks gained X% on average" — simple retrospective validation |
| **Social features / multi-user** | "Let others use it too" | Auth system, data isolation, scaling, moderation. PROJECT.md explicitly excludes | Single-user tool. If others want it, they run their own instance |
| **Mobile app** | "I want to check on my phone" | Separate codebase, app store publishing, push notification complexity | Responsive web dashboard works on mobile. Telegram bot covers mobile notifications |
| **Options/derivatives analysis** | "Analyze VN30F futures too" | VN derivatives market is thin (only VN30F + a few covered warrants). Completely different analysis framework | Out of scope. Focus on equities. Can add later as separate module if needed |
| **AI chatbot / conversational interface** | "Let me ask questions about stocks" | LLM latency on local hardware (7B model = 5-15 sec response), complex prompt engineering, conversation context management | Structured reports + on-demand analysis commands. No free-form chat in v1. CLI commands like `analyze VNM` are more reliable |
| **Price prediction / target price** | "Tell me VNM will be 120k in 3 months" | Dangerously overconfident. LLMs and even ML models are notoriously bad at price prediction. Creates false sense of certainty | Score-based assessment: "conditions favorable for upside" vs "84/100 = strong buy signal." No specific price targets |
| **HNX/UPCOM coverage** | "I also want to see smaller stocks" | Doubles data volume, lower liquidity stocks have less reliable signals, PROJECT.md defers this | HOSE-only for v1. Architecture should support adding exchanges later, but don't build it now |

## Feature Dependencies

```
[Price/Volume Data Crawling]
    └──requires──> [Database/Storage Layer]
    └──enables──> [Technical Indicators]
                      └──enables──> [Technical Score]
                                        └──enables──> [Composite Score]
                                                          └──enables──> [Ranked List]
                                                          └──enables──> [Score Change Alerts]
                                                          └──enables──> [LLM Analysis Report]
                                                                            └──enables──> [Dashboard Display]
                                                                            └──enables──> [Telegram Notification]

[Financial Statement Crawling]
    └──requires──> [Database/Storage Layer]
    └──enables──> [Financial Ratios]
                      └──enables──> [Industry Comparison]
                      └──enables──> [Fundamental Score]
                                        └──enables──> [Composite Score]

[News Crawling]
    └──requires──> [Database/Storage Layer]
    └──enables──> [Vietnamese Sentiment Analysis (LLM)]
                      └──enables──> [Sentiment Score]
                                        └──enables──> [Composite Score]

[Macro Data Crawling]
    └──requires──> [Database/Storage Layer]
    └──enables──> [Macro Context Analysis (LLM)]
                      └──enables──> [Macro Score]
                                        └──enables──> [Composite Score]

[Ollama/LLM Setup]
    └──enables──> [Vietnamese Sentiment Analysis]
    └──enables──> [Macro Context Analysis]
    └──enables──> [LLM Analysis Report]
    └──enables──> [Multi-dimensional Score Fusion]

[Scheduler (Cron)]
    └──requires──> [All Crawlers + Analysis Pipeline]
    └──enables──> [Daily Automated Run]

[Telegram Bot Setup]
    └──requires──> [Composite Score + Report]
    └──enables──> [Daily Digest Notification]
    └──enables──> [Score Change Alerts]

[Web Dashboard]
    └──requires──> [Composite Score + Report + Price Data]
    └──enables──> [Ranked Stock Table]
    └──enables──> [Stock Detail View]
    └──enables──> [Price Charts]
```

### Dependency Notes

- **Composite Score requires all 4 sub-scores:** Technical, Fundamental, Sentiment, Macro. But can launch with partial scoring (tech + fundamental) while sentiment + macro are being built
- **LLM is a bottleneck dependency:** Sentiment analysis, macro analysis, and report generation ALL need Ollama working. Set up early
- **Data crawling must precede everything:** No data = no analysis. This is phase 1
- **Dashboard depends on the entire pipeline:** Build last. CLI/Telegram output first
- **Scheduler wraps the pipeline:** Only add after manual pipeline works end-to-end

## MVP Definition

### Launch With (v1)

Minimum viable product — enough to get daily stock recommendations.

- [x] **Price/Volume data crawling** (HOSE ~400 tickers, daily OHLCV) — foundation of everything
- [x] **Financial statement data** (quarterly income/balance/cashflow) — foundation for fundamentals
- [x] **Core technical indicators** (MA, RSI, MACD, Bollinger, Volume) — immediate analysis value
- [x] **Key financial ratios** (P/E, P/B, EPS, ROE, ROA, debt ratios) — immediate analysis value
- [x] **Composite scoring system** (technical + fundamental weighted scores) — the core product
- [x] **LLM analysis reports** (per-stock Vietnamese narrative) — the differentiator
- [x] **Ranked stock list** (CLI output: top 20 with scores + summary) — actionable output
- [x] **On-demand analysis** (CLI: `localstock analyze` or `localstock analyze VNM`) — user interaction
- [x] **Scheduled daily run** (cron after market close) — automation

### Add After Validation (v1.x)

Features to add once core pipeline is working and scores are calibrated.

- [ ] **Telegram notifications** — trigger: once daily scores are reliable enough to push
- [ ] **Vietnamese news sentiment** — trigger: once base scoring works, add sentiment dimension
- [ ] **Macro-economic analysis** — trigger: once sentiment works, add macro context
- [ ] **Web dashboard** (basic: ranked table + stock detail page) — trigger: when CLI output feels limiting
- [ ] **Score change alerts** — trigger: once you have ≥7 days of score history to compare
- [ ] **Industry comparison** — trigger: once fundamental analysis covers enough stocks

### Future Consideration (v2+)

Features to defer until the tool is daily-drivable and trusted.

- [ ] **Sector rotation analysis** — why defer: needs weeks of sector score history
- [ ] **Customizable scoring weights via UI** — why defer: config file is fine for personal tool
- [ ] **Backtesting / retrospective accuracy** — why defer: needs months of score history
- [ ] **HNX/UPCOM support** — why defer: architecture allows it, but data volume doubles
- [ ] **Conversational AI interface** — why defer: structured commands are more reliable with local LLM

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Price/Volume data crawling | HIGH | MEDIUM | **P1** |
| Financial statement data | HIGH | MEDIUM | **P1** |
| Core technical indicators | HIGH | LOW | **P1** |
| Key financial ratios | HIGH | LOW | **P1** |
| Composite scoring system | HIGH | HIGH | **P1** |
| LLM analysis reports | HIGH | HIGH | **P1** |
| Ranked stock list (CLI) | HIGH | LOW | **P1** |
| Scheduled daily run | HIGH | LOW | **P1** |
| On-demand analysis | MEDIUM | LOW | **P1** |
| Telegram notifications | MEDIUM | MEDIUM | **P2** |
| Vietnamese news sentiment | HIGH | HIGH | **P2** |
| Macro-economic analysis | MEDIUM | HIGH | **P2** |
| Web dashboard | MEDIUM | HIGH | **P2** |
| Score change alerts | MEDIUM | LOW | **P2** |
| Industry comparison | MEDIUM | MEDIUM | **P2** |
| Sector rotation analysis | LOW | MEDIUM | **P3** |
| Retrospective accuracy tracking | LOW | MEDIUM | **P3** |
| HNX/UPCOM support | LOW | MEDIUM | **P3** |

**Priority key:**
- **P1:** Must have for launch — delivers core value proposition
- **P2:** Should have, add once P1 is stable and calibrated
- **P3:** Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Simplize (VN) | Fireant (VN) | WiChart (VN) | Danelfin (Global) | Our Approach |
|---------|---------------|--------------|--------------|-------------------|--------------|
| Price data | ✅ Real-time + historical | ✅ Real-time + historical | ✅ Real-time + historical | ✅ (US stocks) | EOD + on-demand delayed. Sufficient for daily analysis |
| Technical indicators | ✅ Chart-based (TradingView embed) | ✅ Built-in charts | ✅ Full technical charts | ✅ 900+ indicators scored | Calculate indicators, output scores (not charts initially) |
| Financial statements | ✅ Full BCTC | ✅ Basic ratios | ✅ Comprehensive + valuation | ❌ Limited | Full BCTC via vnstock. Calculate key ratios |
| AI scoring | ⚠️ Market Cycle/Structure Index (market-wide, not per-stock) | ❌ No AI scoring | ❌ No AI scoring | ✅ AI Score 1-10 (technical + fundamental + sentiment) | Composite 0-100 score with LLM reasoning. **Unique in VN market** |
| Sentiment analysis | ❌ No automated sentiment | ✅ Social buzz tracking | ❌ No sentiment | ✅ Built-in sentiment score | LLM-based Vietnamese news sentiment. **Unique approach** |
| Macro analysis | ✅ Macro dashboard (interest rates, FX) | ❌ Limited | ✅ Macro data section | ❌ No macro | LLM links macro → stock impact. **Unique** |
| Reports (narrative) | ⚠️ Aggregates broker reports (not AI-generated) | ❌ No reports | ⚠️ WiGroup analyst reports | ❌ No narrative | LLM-generated Vietnamese narrative reports. **Core differentiator** |
| Alerts/Notifications | ✅ Price alerts | ✅ Price alerts | ❌ Limited | ✅ Email alerts | Telegram: daily digest + score change alerts |
| Screener/Filter | ✅ Basic stock screener | ✅ Advanced filters | ✅ Good screener | ✅ AI-ranked lists | Score-ranked list replaces traditional screener |
| Cost | Freemium (499k-1.99M VND/month for premium) | Freemium (paid tiers) | Freemium (paid reports) | $17-67/month | **Free forever** (local LLM, free data) |

### Key Competitive Insights

1. **No VN tool does AI scoring per stock.** Simplize's Market Cycle Index is market-wide, not per-stock. This is LocalStock's opening.
2. **No VN tool generates AI narrative reports.** They aggregate broker reports or show raw numbers. LLM synthesis is genuinely novel for VN market.
3. **Sentiment analysis for Vietnamese financial news** is virtually nonexistent in consumer tools. LLMs capable of Vietnamese (Qwen2.5, Vistral) make this feasible now.
4. **Macro-to-stock linking** is done editorially (human analysts write about it) but no tool automates it. LLM can do this.
5. **All competitors are paid SaaS.** A free, local-first tool has zero marginal cost after setup.

## Sources

- **Simplize (simplize.vn):** Vietnamese stock analysis platform with AI Market Cycle/Structure indices. Pricing: 499k-1.99M VND/month. Features confirmed via site crawl (2026-04-14). Confidence: HIGH
- **Fireant (fireant.vn):** Vietnamese stock platform with social/community features and stock screener. Free + paid tiers. Confirmed via site crawl. Confidence: HIGH
- **WiChart (wichart.vn):** WiGroup's comprehensive stock analysis platform with macro data, sector analysis, and financial data. Confirmed via site crawl. Confidence: HIGH
- **Danelfin (danelfin.com):** Global AI stock scoring platform (US/EU stocks). AI Score 1-10 based on technical + fundamental + sentiment. Reference architecture for scoring systems. Confidence: MEDIUM (obfuscated JS site)
- **FinViz (finviz.com):** Gold standard stock screener. 150+ filter criteria confirmed via site crawl (2026-04-14). Confidence: HIGH
- **vnstock library (PyPI v3.5.1):** Open-source Python library for VN stock data. Sources: VCI, KBS (TCBS), MSN, FMarket. Provides OHLCV, financial statements, ratios, listing data. Confirmed via GitHub repo structure. Confidence: HIGH
- **ta-lib:** 150+ technical indicators. Industry standard. Confirmed via PyPI/GitHub. Confidence: HIGH
- **GitHub search:** Surveyed Vietnamese stock analysis repos (2026-04-14). Most are academic/hobby projects (<10 stars). No production-grade AI scoring system exists for VN market. Confidence: HIGH

---
*Feature research for: AI Stock Analysis Agent — Vietnamese Market (HOSE)*
*Researched: 2026-04-14*
