# Pitfalls Research

**Domain:** Vietnamese Stock Market AI Agent (HOSE) — Local LLM + Web Scraping
**Researched:** 2026-04-14
**Confidence:** HIGH (verified via source code, API testing, issue trackers)

## Critical Pitfalls

### Pitfall 1: Vietnamese Stock Data Sources Are Ephemeral

**What goes wrong:**
You build your data pipeline against a specific API endpoint (TCBS, SSI, VnDirect/VCI, CafeF), and it breaks within weeks or months. Vietnamese brokerages treat their public-facing APIs as internal infrastructure — they change URLs, add authentication, restructure responses, or shut down endpoints without notice. During research, TCBS's `apipubaws.tcbs.com.vn` returned empty responses, SSI's `iboard.ssi.com.vn` returned 502, and Vietstock returned 404. Only VietCap (VCI) endpoints used by vnstock v3.5.1 were reachable.

**Why it happens:**
Vietnamese brokerages don't publish official developer APIs. What developers scrape are internal APIs that power their web/mobile apps. When the brokerage redesigns their frontend, the API endpoints change. There's no deprecation notice, no versioning, no developer relations team.

**How to avoid:**
- **Use vnstock (v3.5.1) as a data abstraction layer** rather than hitting APIs directly. vnstock's maintainer actively tracks source changes (62 releases to date, 1,200+ GitHub stars). When VCI changes, vnstock updates — you update one dependency instead of rewriting scraping code.
- **Design a data source adapter pattern** from day one: `interface DataSource { getPrice(), getFinancials(), getCompanyInfo() }`. Each source (VCI, TCBS, CafeF) implements the interface. Swap sources without touching analysis code.
- **Cache aggressively.** Historical price data doesn't change. Once you have VNM's price history for 2024, store it in your local DB. Only fetch deltas (latest trading day).
- **Build health checks** that run before each data fetch cycle. If a source returns errors, log it and fall back — don't crash the whole pipeline.
- **CRITICAL:** vnstock v3.5.x has a mandatory `vnai` dependency (analytics/tracking package) that has caused deadlock issues on Windows (see vnstock issue #210). Pin the version carefully and test.

**Warning signs:**
- vnstock starts throwing `KeyError: 'data'` (issue #218 — happened March 2026)
- HTTP 403/502 responses from previously working endpoints
- Sudden empty dataframes from `stock.quote.history()`
- vnstock releases a new version with "fix data source" in changelog

**Phase to address:**
Phase 1 (Data Pipeline Foundation). Build the adapter pattern and caching layer before any analysis code. This is the most fragile part of the entire system and must be resilient from the start.

---

### Pitfall 2: Unadjusted Price Data Corrupts All Technical Analysis

**What goes wrong:**
You calculate RSI, MACD, Bollinger Bands on raw historical prices, and every stock split, bonus share issuance, or large cash dividend creates a false cliff in the chart. Example: A stock trading at 80,000 VND does a 2:1 split → price drops to 40,000. Your RSI screams "oversold," MACD shows massive bearish crossover, Bollinger Bands explode — all false signals. This corrupts your entire scoring system for every stock that has ever had a corporate action.

**Why it happens:**
Vietnamese data sources (including VCI via vnstock) typically return **unadjusted** historical prices. In our source code review of vnstock's `Quote` class, there is no `adjust`, `split`, or `dividend` handling in the price fetching logic. HOSE stocks have frequent corporate actions: stock dividends (cổ tức bằng cổ phiếu), rights issues (phát hành quyền mua), and bonus shares (thưởng cổ phiếu) are more common than cash dividends in Vietnam.

**How to avoid:**
- **Implement your own price adjustment logic.** Fetch corporate actions data (ngày GDKHQ — ex-date, tỷ lệ — ratio) and retroactively adjust historical prices.
- **Source corporate actions separately:** CafeF and VnDirect publish corporate action calendars. Scrape these and maintain a local corporate actions database.
- **Adjustment formula:** For a stock split with ratio R, multiply all prices before ex-date by (1/R) and all volumes by R. For stock dividends at rate D%, multiply prices by 1/(1+D%) before ex-date.
- **Validate by comparing:** Check your adjusted prices against TradingView's VN stock charts (which do adjust). If they diverge, your adjustment is wrong.
- **Re-adjust when new corporate actions occur.** This means recomputing ALL historical adjusted prices for that ticker, not just appending.

**Warning signs:**
- Technical indicators showing extreme readings on days that were normal trading
- Sudden large gaps in price history that don't correspond to market events
- MA crossovers that fire on corporate action dates
- Scoring system consistently ranking recently-split stocks as "oversold"

**Phase to address:**
Phase 1 (Data Pipeline). Corporate action data must be collected alongside price data. Price adjustment MUST happen before any technical indicator calculation in Phase 2.

---

### Pitfall 3: Local 7B-13B LLMs Hallucinate Financial Facts Confidently

**What goes wrong:**
You ask your local Llama/Qwen/Mistral model "Analyze VNM's financial health" and it generates plausible-sounding but fabricated numbers: "VNM's P/E ratio is 15.2, revenue grew 12% YoY" — but these numbers are invented. The model has no access to current data; it pattern-matches financial language from training data. Worse, it does this confidently, with no hedging. A user reading the report takes the fabricated numbers as analysis.

**Why it happens:**
LLMs are text generators, not databases. A 7B-13B model on 12GB VRAM has even less capacity for factual recall than GPT-4. It will generate text that *looks like* financial analysis because it's seen millions of such documents in training, but every number is potentially made up. Vietnamese stocks are underrepresented in English-trained models' training data, making hallucination worse for HOSE-specific facts.

**How to avoid:**
- **NEVER ask the LLM to recall facts.** Always inject all data into the prompt. Instead of "Analyze VNM," send: "Given these facts about VNM: P/E=18.5, ROE=35.2%, Revenue Q3=15,000 tỷ VND (+8% YoY)... Provide analysis."
- **Use LLM as synthesizer, not data source.** The LLM's job is to weigh the structured data you feed it and generate a human-readable narrative, NOT to know what VNM's EPS is.
- **Structured output enforcement:** Use JSON mode or structured output prompts to get scores/ratings that you can validate (e.g., "rate from 1-10" for each dimension), not free-form text that might contain fabricated stats.
- **Template-based reports with LLM fill-in.** Pre-build the report structure with real data tables, and let the LLM write only the interpretation paragraphs.
- **Post-validation:** After LLM generates text, programmatically check any numbers it mentions against your database. Flag mismatches.

**Warning signs:**
- LLM output contains specific numbers that weren't in the prompt
- LLM makes claims about "recent" events (it has no recent knowledge)
- Two runs produce different numbers for the same stock
- LLM analysis contradicts the structured data you fed it

**Phase to address:**
Phase 3 (LLM Integration). Design the prompt engineering framework with strict data injection from the start. Never build a "chat with your portfolio" feature that lets the LLM free-associate.

---

### Pitfall 4: Vietnamese Financial Sentiment Analysis Is Much Harder Than English

**What goes wrong:**
You build sentiment analysis for Vietnamese financial news and get ~50-60% accuracy — barely better than random. Headlines like "VNM lao dốc sau tin sáp nhập" (VNM plunges after merger news) get classified as negative, but the merger might be positive for long-term value. Financial Vietnamese has domain-specific vocabulary, sarcasm patterns, and the critical challenge of **word segmentation** (Vietnamese words can be multi-syllable: "thị trường" = market, but "thị" alone = city/visual).

**Why it happens:**
1. **Word segmentation is mandatory** for Vietnamese NLP. Unlike English, Vietnamese word boundaries aren't spaces. "Cổ phiếu" (stock) is one word written as two syllables. Tools like `underthesea` (v9.4.0) handle this, but errors compound.
2. **Financial domain vocabulary** differs from general Vietnamese. Models trained on general text misinterpret financial terms.
3. **Small local LLMs (7B-13B) have weak Vietnamese understanding.** Even Qwen2.5 and Llama models are primarily English-trained. Vietnamese performance drops significantly vs English.
4. **Sarcasm and irony** in Vietnamese financial forums (e.g., "Cổ phiếu bay cao quá" = "Stock flying too high" — could be genuine excitement or sarcastic fear of a crash).
5. **Mixed language:** Vietnamese financial text mixes Vietnamese and English freely ("VNM break out vùng kháng cự, target 95k").

**How to avoid:**
- **Use PhoBERT (VinAI Research, 777 GitHub stars) for Vietnamese-specific sentiment** rather than general-purpose LLMs. PhoBERT is pre-trained on 20GB of Vietnamese text and handles word segmentation natively.
- **Don't use the LLM for sentiment classification.** Use a dedicated classifier (PhoBERT fine-tuned on financial sentiment) for the classification task, and only use the LLM for synthesis/reporting.
- **Build a financial Vietnamese dictionary** mapping domain terms to sentiment signals. "Phá đáy" (break support) = bearish. "Breakout" = bullish. "Lướt sóng" (wave riding) = short-term trading = neutral.
- **Use headline-level sentiment, not article-level.** Vietnamese financial articles often bury the lede. Headlines are more reliably sentiment-indicative.
- **Start with simple keyword/rule-based sentiment** and only add ML when you have enough labeled data. Rules like "giảm sàn" (limit down) = strongly negative are 100% accurate.
- **Aggregate sentiment over multiple articles** per stock per day. Single-article sentiment is noisy; daily aggregate is more reliable.

**Warning signs:**
- Sentiment scores don't correlate at all with next-day price movements
- Same event gets opposite sentiment on consecutive runs
- All stocks showing similar sentiment scores (model not differentiating)
- Vietnamese text being tokenized character-by-character instead of word-by-word

**Phase to address:**
Phase 2 (Analysis Engine). Start with rule-based/keyword sentiment in Phase 2. Add ML-based sentiment (PhoBERT) as a Phase 3 enhancement when labeled training data is available. Don't block the scoring system on perfect sentiment.

---

### Pitfall 5: BCTC (Financial Statement) Parsing Creates Silent Data Corruption

**What goes wrong:**
You parse Vietnamese financial statements (Báo Cáo Tài Chính) and get numbers that are off by factors of 1,000 or 1,000,000 because of inconsistent unit reporting. Company A reports revenue in "triệu đồng" (millions VND), Company B reports in "tỷ đồng" (billions VND), and Company C reports in "đồng" (VND). Your P/E ratio for Company B comes out 1,000x too low, and it gets ranked #1 in your scoring system. Nobody notices because the number "looks reasonable" for a different company.

**Why it happens:**
- Vietnamese BCTC has no enforced unit standard across companies. The unit is usually noted in the report header, not per-line-item.
- VCI/vnstock's financial API returns data with units that may vary by source and period.
- Quarterly reports (báo cáo quý) vs. annual reports (báo cáo năm) may use different units for the same company.
- Some companies restate prior periods, creating duplicate or conflicting data for the same quarter.
- Consolidated (hợp nhất) vs. parent-only (riêng) financial statements report different numbers for the same entity.

**How to avoid:**
- **Normalize all financial data to a single unit immediately upon ingestion.** Pick "tỷ đồng" (billions VND) as your standard. Convert everything at ingestion time, not at display time.
- **Store the original unit alongside the normalized value** so you can debug mismatches.
- **Cross-validate key metrics:** If vnstock reports VNM's revenue as X and CafeF reports it as Y, flag discrepancies above 1% for manual review.
- **Always use consolidated (hợp nhất) statements,** not parent-only. vnstock's Finance class defaults to this, but verify.
- **Implement sanity checks:** P/E < 0 or > 500 = likely data error. ROE > 100% = verify. Revenue negative = verify (some sectors like insurance report this way).
- **Track the reporting period carefully.** Vietnamese companies report Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec). Some have fiscal years not aligned with calendar years.

**Warning signs:**
- A stock suddenly appears at the top/bottom of rankings after a new quarterly report
- Financial ratios for one company are orders of magnitude different from peers
- Negative P/E ratios for profitable companies
- Revenue or earnings showing 1000x jumps between quarters

**Phase to address:**
Phase 1 (Data Pipeline) for ingestion normalization. Phase 2 (Analysis Engine) for sanity checks and cross-validation. This pitfall is insidious because it's silent — bad data produces plausible-looking wrong analysis.

---

### Pitfall 6: Scoring System Produces False Precision and Overconfidence

**What goes wrong:**
You build a scoring system that says "VNM: 87/100, HPG: 82/100" and treat the 5-point difference as meaningful, when in reality the scoring weights are arbitrary, the input data has ±10% noise, and the whole system is basically astrology with extra steps. Users (even you as the sole user) start trusting scores as gospel and making investment decisions based on rank ordering that has no statistical validity.

**Why it happens:**
- **Arbitrary weight assignment:** You decide technical analysis = 30%, fundamental = 40%, sentiment = 20%, macro = 10%. These weights have no empirical basis.
- **Mixing incompatible scales:** RSI (0-100) gets combined with P/E ratio (3-300) gets combined with sentiment (-1 to 1). Normalization choices dominate the final score.
- **No backtesting:** The scoring system is never validated against actual returns. It "feels right" because it ranks blue chips highly, but that's just survivorship bias.
- **Stale signals:** Technical indicators optimized for trending markets give false signals in HOSE's frequent sideways/choppy periods (which are common for VN market).
- **False precision:** Scoring to 2 decimal places suggests accuracy that doesn't exist.

**How to avoid:**
- **Use categorical ratings, not precise scores.** "Strong Buy / Buy / Hold / Sell / Strong Sell" or "A / B / C / D / F" tiers. Don't pretend you know VNM is exactly 87.3 points.
- **Show component scores alongside totals.** If VNM scores high, show WHY: "Technical: Bullish (RSI=45, above MA200), Fundamental: Strong (ROE=35%, P/E below sector avg), Sentiment: Neutral." Let the user weigh dimensions themselves.
- **Backtest before trusting.** Before deploying the scoring system, run it against 2 years of historical data and check: do high-scored stocks actually outperform? If not, fix the model before shipping.
- **Use relative scoring within sectors.** VNM (dairy) vs. HPG (steel) are apples vs. oranges. Score within sector first, then compare across sectors.
- **Include a confidence/data-quality indicator.** If a stock has missing fundamental data or no news coverage, flag the score as "low confidence" rather than filling in zeros.
- **Make weights configurable.** Since weights are subjective, let the user (you) adjust them in a config file and see how rankings change.

**Warning signs:**
- Top-ranked stocks don't outperform randomly selected stocks after 1-3 months
- Minor data updates cause large ranking shuffles
- All stocks cluster around 50/100 (scoring system has poor discrimination)
- You find yourself ignoring the scores and just looking at the individual metrics

**Phase to address:**
Phase 2 (Analysis Engine) for initial scoring design. Phase 4 (Dashboard) for making component scores visible. Phase 5 (Refinement) for backtesting validation. Design scores as "decision support" not "decision replacement" from day one.

---

### Pitfall 7: VRAM Exhaustion and LLM Throughput Bottleneck at Scale

**What goes wrong:**
You need to analyze ~400 stocks daily. Each stock needs an LLM call with context (price data, fundamentals, news, macro). Even a 7B model on RTX 3060 (12GB VRAM) takes 5-15 seconds per inference. 400 stocks × 10 seconds = 67 minutes just for LLM calls, assuming no failures. If you accidentally send too-long prompts, the model runs out of context window, truncates critical data, and produces garbage analysis. If you try to batch or parallelize, VRAM OOM kills the process.

**Why it happens:**
- RTX 3060 has 12GB VRAM. A Q4-quantized 7B model uses ~4-5GB, leaving ~7GB for KV cache. Context window is limited (typically 4K-8K tokens for 7B models at this VRAM level; 32K theoretical but will OOM).
- Financial analysis prompts are long: price history + financial ratios + news headlines + macro context easily exceeds 4K tokens per stock.
- Ollama loads/unloads models, adding 5-10 seconds overhead per cold start.
- No batching support in Ollama's API for different prompts.

**How to avoid:**
- **Tier your analysis.** Don't run LLM on all 400 stocks. Use rules-based scoring (fast, runs on CPU) to filter to top 30-50 candidates, then run LLM deep analysis only on those. This reduces LLM calls from 400 to 30-50.
- **Use Qwen2.5-7B-Instruct (Q4_K_M quantization)** — best Vietnamese language support among 7B models, fits comfortably in 12GB VRAM with room for 8K context.
- **Keep prompts under 2K tokens.** Summarize data before sending to LLM. Send key metrics, not raw time series. "VNM: Price=82k, MA20=80k, RSI=45, P/E=18.5, ROE=35%, Sector avg P/E=22" instead of 90 days of OHLCV data.
- **Sequential processing with Ollama keep-alive.** Set `OLLAMA_KEEP_ALIVE=30m` so the model stays loaded in VRAM between calls. Don't load/unload per request.
- **Implement a processing queue** with retry logic. If a call fails, retry once, then skip and mark as "analysis unavailable."
- **Pre-compute everything you can outside the LLM.** Technical indicators, financial ratios, sentiment scores — all computed before LLM sees the data. LLM only does synthesis.

**Warning signs:**
- Processing 400 stocks takes >2 hours
- Ollama log shows "out of memory" or "context length exceeded"
- LLM responses become incoherent or repetitive (truncated context)
- System swap usage spikes during analysis runs

**Phase to address:**
Phase 3 (LLM Integration). Design the tiered analysis pipeline and prompt templates before integrating the LLM. Test with 10 stocks first, measure throughput, then extrapolate.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding VCI API URLs | Works now, ships faster | Breaks when VCI changes endpoints; requires code changes to fix | Never — use config/env vars |
| Skipping price adjustment for splits | Less code, "most stocks don't split" | Silent corruption of technical indicators; wrong rankings | Never — splits happen frequently on HOSE |
| Using LLM for all analysis (no rules engine) | Simpler architecture | 400 LLM calls daily, slow, expensive on VRAM, hallucination risk | Only for final synthesis/reporting, never for raw computation |
| Storing raw HTML/JSON from scrapers | Quick to implement | Storage bloat, hard to query, breaks when HTML changes | MVP only — move to structured DB quickly |
| Single-source data fetching | Works when source is up | Total failure when source goes down | MVP phase only (max 2 weeks) |
| No data versioning / audit trail | Less DB schema complexity | Can't debug when rankings change unexpectedly | Never — always store ingestion timestamp and source |
| Putting all analysis in one giant prompt | "The LLM will figure it out" | Context overflow, inconsistent results, impossible to debug | Never — decompose into structured sub-analyses |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| vnstock library | Using latest version without pinning; `vnai` dependency causes deadlocks (issue #210) | Pin to specific version (3.5.1), test `vnai` behavior, consider forking if vnai becomes mandatory/problematic |
| VCI GraphQL API | Assuming response schema is stable; not handling rate limits | Cache responses, implement exponential backoff, validate response schema before parsing |
| CafeF news scraping | Scraping full article text (heavy, slow, anti-bot detection) | Scrape headlines only for sentiment; CafeF uses Cloudflare protection on some pages |
| Ollama API | Not setting `keep_alive` parameter; model reloads between each call | Set `keep_alive: "30m"` in API calls; use `/api/chat` with streaming for long responses |
| Telegram Bot API | Sending too many messages (rate limited at ~30 msg/sec to same chat) | Batch alerts into single messages; use Markdown formatting for readability; send max 1-2 messages per analysis run |
| Vietnamese news sites (general) | Using requests library without headers | Set proper User-Agent, Accept-Language: vi headers; some sites block non-browser requests |
| underthesea / PhoBERT | Loading model on GPU alongside Ollama model | Run NLP preprocessing on CPU; keep GPU exclusively for Ollama LLM inference |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching all 400 stock histories on every run | Run takes 30+ minutes; data source rate-limits you | Fetch only today's delta; cache all historical data locally | >50 stocks per batch without delays |
| Loading full OHLCV history into memory for indicator calculation | RAM spikes, OOM on large histories (10+ years) | Use windowed calculation (only need last 200 candles for most indicators) | >100 stocks × 10 years history |
| Re-running sentiment analysis on old news articles | Wasted compute; same results every time | Store sentiment results in DB with article hash; only analyze new articles | >500 articles per run |
| Synchronous LLM calls in a loop | 400 × 10s = 67 minutes blocked | Tiered filtering (rules engine → top 50 → LLM) | >30 stocks through LLM |
| Storing analysis results as JSON files | Disk I/O bottleneck; no querying capability | Use SQLite from day one; JSON is fine for LLM prompt/response logs | >1 month of daily analysis data |
| Computing all technical indicators for all stocks | CPU-bound, wasteful for illiquid stocks | Only compute indicators for stocks meeting minimum volume threshold | >400 stocks × 10 indicators |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing Telegram bot token in source code | Token exposed if repo ever becomes public; bot hijacked | Use `.env` file, add to `.gitignore`; use `python-dotenv` or similar |
| Logging full API responses including potential auth tokens | Credentials in log files accessible on disk | Sanitize logs; never log headers or cookies from broker APIs |
| Running Ollama on 0.0.0.0 without auth | Anyone on LAN can use your LLM and see your financial data | Bind Ollama to 127.0.0.1 only (default); don't expose to network |
| Scraper credential exposure | If using authenticated endpoints (TCBS account), credentials in config | Encrypt at rest; use system keyring; never commit credentials |
| Publishing analysis results publicly | Could be interpreted as unlicensed investment advice (Vietnam securities law) | Keep as personal tool; if sharing, add clear disclaimers |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing only the composite score without breakdown | Can't understand why a stock is ranked high/low; loses trust | Always show dimension scores: Technical ▲ / Fundamental ★★★ / Sentiment ● |
| Displaying too many decimal places (87.34/100) | False precision creates false confidence | Use integer scores or letter grades; round aggressively |
| Not showing data freshness timestamp | User doesn't know if analysis is from today or 3 days ago | Show "Last updated: 14/04/2026 15:30" prominently on dashboard |
| Overwhelming dashboard with all 400 stocks | Information overload; can't find actionable signals | Default view: Top 10 + Bottom 10 + Watchlist; filter/sort for the rest |
| LLM-generated reports that are too long | Nobody reads a 2000-word report per stock daily | Summary first (3 sentences), expandable detail sections |
| No indication of analysis confidence | User treats low-confidence analysis same as high-confidence | Show data quality badges: 🟢 Full data / 🟡 Partial / 🔴 Insufficient |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Price data pipeline:** Often missing **adjusted prices for corporate actions** — verify by checking a known stock split (e.g., check if VIC's 2020 prices are adjusted)
- [ ] **Technical indicators:** Often missing **handling of insufficient data** — verify RSI doesn't NaN-crash on newly listed stocks with <14 days of history
- [ ] **Financial data:** Often missing **unit normalization** — verify P/E ratios are sensible across all 400 stocks (none should be >1000 or <-100 without flagging)
- [ ] **Sentiment analysis:** Often missing **handling of no-news stocks** — verify stocks with zero news articles get "neutral" not "error"
- [ ] **Scoring system:** Often missing **sector-relative comparison** — verify a bank (VCB) and a tech stock (FPT) aren't scored on identical criteria
- [ ] **LLM reports:** Often missing **data injection verification** — verify the LLM report contains only facts from the structured data, no fabricated numbers
- [ ] **Scheduler:** Often missing **holiday/weekend handling** — verify the system doesn't try to fetch data on Vietnamese public holidays (Tết, 30/4, 2/9, etc.)
- [ ] **Data pipeline:** Often missing **T+0 vs T+1 data alignment** — verify that today's price and today's news are aligned correctly in analysis
- [ ] **Telegram notifications:** Often missing **deduplication** — verify the same alert isn't sent multiple times if the scheduler re-runs
- [ ] **Dashboard:** Often missing **error state handling** — verify dashboard shows meaningful message when data pipeline failed, not a blank page

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Data source API breaks | LOW | Switch vnstock to alternative connector (VCI→MSN→KBS); update adapter config; re-test |
| Unadjusted prices discovered after analysis | MEDIUM | Fetch corporate action history; rebuild adjusted price table; recompute all technical indicators; re-run scoring |
| LLM hallucinating numbers in reports | LOW | Add post-validation step comparing LLM output numbers against DB; re-generate flagged reports with stricter prompt |
| BCTC unit mismatch corrupting rankings | HIGH | Audit all financial data in DB against CafeF manual check for top 20 stocks; rebuild normalization pipeline; re-ingest |
| Scoring system producing meaningless rankings | MEDIUM | Add backtesting harness; test against 1-year historical returns; adjust weights or switch to categorical ratings |
| VRAM OOM during batch analysis | LOW | Reduce batch size; increase quantization level (Q4→Q3); reduce prompt length; add memory monitoring |
| Vietnamese sentiment consistently wrong | MEDIUM | Fall back to rule-based keyword sentiment; collect labeled training data manually (100+ articles); retrain or fine-tune |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Data source instability | Phase 1: Data Pipeline | Health check passes for all sources; adapter pattern allows source swap in <1 hour |
| Unadjusted prices | Phase 1: Data Pipeline | Compare 5 known split stocks against TradingView adjusted prices; <0.1% deviation |
| LLM hallucination | Phase 3: LLM Integration | Run 20 LLM analyses; zero fabricated numbers found in output |
| Vietnamese sentiment accuracy | Phase 2: Analysis Engine | Sentiment scores for 50 manually-labeled headlines achieve >70% accuracy |
| BCTC parsing corruption | Phase 1: Data Pipeline | P/E, ROE, EPS for VN30 stocks match CafeF displayed values within 1% |
| Scoring false precision | Phase 2: Analysis Engine | Backtest shows top-tier stocks outperform bottom-tier by >5% over 6 months |
| VRAM exhaustion | Phase 3: LLM Integration | Full 400-stock pipeline completes in <30 minutes with zero OOM errors |
| Scheduler edge cases | Phase 4: Automation | System correctly skips Vietnamese public holidays and weekends; no false alerts |

## Vietnamese Market-Specific Traps

Unique characteristics of HOSE that general stock analysis tools don't handle.

| Trap | What's Different About HOSE | Impact If Ignored |
|------|------------------------------|-------------------|
| Price limits (±7%) | HOSE stocks can only move ±7% per day (ceiling/floor prices) | Technical indicators calibrated for unlimited-range markets give wrong signals at limits; limit-up/down is a strong signal itself |
| ATC/ATO sessions | Opening (9:00-9:15) and closing (14:30-14:45) are call auctions, not continuous trading | Intraday data has gaps; ATC price may differ significantly from last continuous trade |
| T+2 settlement | Stocks settle T+2 in Vietnam | Not directly relevant for analysis but affects cash flow if user acts on recommendations |
| Foreign ownership limits | Many stocks have FOL (Foreign Ownership Limit) restrictions | Stocks near FOL caps trade differently (premium/discount to local); sentiment signals differ |
| "Đội lái" manipulation | Small/mid-cap HOSE stocks are frequently manipulated by market makers ("đội lái") | Volume spikes and price patterns that look like breakouts are actually pump-and-dump; apply manipulation detection filters for small caps |
| Vietnamese holiday calendar | Tết Nguyên Đán (7-10 days off), 30/4 & 1/5, 2/9, and various holidays | Scheduler must use Vietnamese holiday calendar, not just weekends; pre/post-holiday trading has different patterns |
| Lot size = 100 shares for standard order | Standard lot = 100 shares; odd-lot trading has different rules | Not critical for analysis but relevant for recommendations |

## Sources

- **vnstock GitHub repository** (thinh-vu/vnstock): Source code analysis of VCI connector, issue tracker (#210 vnai deadlock, #218 KeyError, #219 API errors) — [github.com/thinh-vu/vnstock](https://github.com/thinh-vu/vnstock) — HIGH confidence
- **vnstock PyPI**: v3.5.1, 62 releases, active maintenance — HIGH confidence
- **vnai PyPI**: v2.4.6, analytics dependency causing issues — verified via issue tracker — HIGH confidence
- **VCI API endpoints**: Verified reachable at trading.vietcap.com.vn — tested 2026-04-14 — HIGH confidence
- **TCBS API**: apipubaws.tcbs.com.vn returning empty responses — tested 2026-04-14 — HIGH confidence
- **SSI API**: iboard.ssi.com.vn returning 502 — tested 2026-04-14 — HIGH confidence
- **underthesea**: v9.4.0, Vietnamese NLP toolkit — PyPI verified — HIGH confidence
- **PhoBERT**: VinAIResearch/PhoBERT, 777 stars, pre-trained Vietnamese LM — GitHub verified — HIGH confidence
- **Ollama**: v0.20.7 (2026-04-13), active development — GitHub verified — HIGH confidence
- **Vietnamese stock sentiment research**: Limited academic work; only 1 repo with >20 stars (PhoBERT classification, 21 stars) — LOW confidence for ML-based sentiment approaches
- **HOSE trading rules** (price limits, ATC/ATO, T+2): Based on training data knowledge of Vietnamese market regulations — MEDIUM confidence (verify against current HOSE rules)

---
*Pitfalls research for: Vietnamese Stock Market AI Agent (HOSE)*
*Researched: 2026-04-14*
