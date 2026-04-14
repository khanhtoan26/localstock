# Project Research Summary

**Project:** LocalStock — AI Stock Agent for Vietnamese Market (HOSE)
**Domain:** Financial Data Pipeline + AI Analysis Agent
**Researched:** 2025-07-18
**Confidence:** HIGH

## Executive Summary

LocalStock is a personal AI-powered stock analysis agent for the Vietnamese HOSE market (~400 tickers). The expert-recommended approach is a **batch data pipeline** — not a real-time system — that runs daily after market close (15:30 VN time), crawling price/financial data via the `vnstock` library, computing technical and fundamental scores with pure Python (pandas-ta), then using a local LLM (Qwen2.5 on Ollama/RTX 3060) to synthesize Vietnamese-language narrative reports for the top-ranked stocks. The core differentiator versus existing Vietnamese platforms (Simplize, Fireant, WiChart) is the combination of multi-dimensional AI scoring per stock and LLM-generated Vietnamese analysis reports — no competing tool in Vietnam does either.

The recommended architecture is a **Python monolith with clean module boundaries** (not microservices), using FastAPI for the API layer, PostgreSQL for storage, and a sequential pipeline pattern (Ingest → Analyze → Score → Synthesize → Notify). The frontend is a Next.js dashboard with TradingView's lightweight-charts. The system is designed as a single-user localhost tool with a clear path to cloud deployment by swapping config. All stack choices are HIGH confidence — vnstock, pandas-ta, FastAPI, Ollama, and Next.js are mature, well-documented technologies with no exotic dependencies.

The primary risks are **data fragility** (Vietnamese broker APIs change without notice — vnstock abstracts this but it's still the weakest link), **price adjustment for corporate actions** (unadjusted prices corrupt all technical analysis — HOSE has frequent stock dividends/splits), and **LLM hallucination** (local 7B-14B models confidently fabricate financial numbers if not fed structured data in every prompt). All three risks are mitigable with known patterns identified in the pitfalls research, but they must be addressed in the earliest phases — not bolted on later.

## Key Findings

### Recommended Stack

The stack is a Python-heavy backend with a JavaScript frontend. Python dominates because vnstock, pandas-ta, Ollama client, and underthesea are all Python-native. The frontend is a separate Next.js app that reads from the FastAPI REST API. See [STACK.md](./STACK.md) for full details.

**Core technologies:**
- **Python 3.12+ / FastAPI**: Primary backend — async API, Pydantic validation, auto-generated docs. All data/AI libraries are Python-native.
- **PostgreSQL 16+**: Primary database — handles concurrent writes from crawler + API, full-text search for news, JSON columns for financial reports. Docker Compose makes it trivial to run.
- **vnstock 3.5+**: The only viable library for Vietnamese stock data (OHLCV, financial statements, ratios). Free for personal use. Active maintenance (62 releases).
- **pandas-ta**: 130+ technical indicators, pure Python (no C compilation unlike TA-Lib). Works directly on DataFrames.
- **Ollama + Qwen2.5 14B (Q4_K_M)**: Local LLM inference. Qwen2.5 has the best Vietnamese language support among open models. ~9-10GB VRAM at Q4 quantization fits RTX 3060 (12GB). Fallback: Qwen2.5 7B Q8_0.
- **Next.js 16+ / shadcn/ui / lightweight-charts**: Dashboard with TradingView-quality stock charts (~45KB bundle), professional UI components.
- **APScheduler**: In-process cron-like scheduler. No Redis/RabbitMQ needed (unlike Celery). Perfect for single-machine.
- **python-telegram-bot**: Async notifications for daily digests and score change alerts.

**Critical version notes:** Pin vnstock carefully — the `vnai` dependency has caused deadlock issues (GitHub issue #210). Use `uv` for Python package management (10-100x faster than pip).

### Expected Features

See [FEATURES.md](./FEATURES.md) for full analysis including competitor comparison.

**Must have (table stakes — v1 MVP):**
- Price/volume data crawling (~400 HOSE tickers, daily OHLCV + 2yr history)
- Financial statement data (quarterly income/balance/cashflow via vnstock)
- Core technical indicators (MA, RSI, MACD, Bollinger Bands, volume analysis)
- Key financial ratios (P/E, P/B, EPS, ROE, ROA, D/E)
- Composite scoring system (technical + fundamental weighted scores)
- LLM-synthesized Vietnamese analysis reports (the killer differentiator)
- Ranked stock list with CLI output (top 20 with scores + reasoning)
- Scheduled daily run (after market close) + on-demand single-stock analysis

**Should have (v1.x — after core pipeline validated):**
- Telegram notifications (daily digest + score change alerts)
- Vietnamese news sentiment analysis (LLM-classified, rule-based fallback)
- Macro-economic context linking (SBV rates, CPI → stock impact)
- Web dashboard (ranked table + stock detail with charts)
- Industry comparison (sector-relative scoring)

**Defer (v2+):**
- Sector rotation analysis, backtesting/retrospective accuracy, HNX/UPCOM support, conversational AI chatbot

**Explicitly excluded (anti-features):**
- Auto-trading, real-time tick data, portfolio tracking, price prediction, multi-user/social

### Architecture Approach

The system follows a **pipeline architecture** (ETL + Analysis) built as a monolith with clean module boundaries. Data flows sequentially: Ingest → Store → Analyze → Score → Synthesize → Notify. Each stage can run independently for testing. The LLM is treated as an internal service with structured JSON output (not free-form text parsing). A critical architectural decision is the **funnel approach**: rule-based scoring filters 400 stocks to ~50 candidates for sentiment analysis, then only the top 15-20 get full LLM report generation. See [ARCHITECTURE.md](./ARCHITECTURE.md) for full details.

**Major components:**
1. **Data Ingestion Layer** — Price crawler (vnstock), financial report crawler, news scraper (httpx+BS4), macro data collector. Each crawler implements a common adapter interface for source-swappability.
2. **Analysis Layer** — Technical analysis (pandas-ta), fundamental analysis (ratio calculations), sentiment analysis (Ollama LLM), macro analysis (rule engine + LLM). Each module is independent — no cross-dependencies.
3. **Scoring Engine** — Weighted aggregator (Technical 30% + Fundamental 30% + Sentiment 20% + Macro 20%). Configurable weights via config file. Categorical ratings (Strong Buy/Buy/Hold/Sell), not false-precision decimals.
4. **AI Synthesis** — Ollama client with structured output, prompt templates, report generation. LLM is a synthesizer (interprets pre-computed data), never a data source.
5. **Pipeline Coordinator** — Orchestrates the full crawl→analyze→score→report→notify sequence. APScheduler triggers daily runs.
6. **Presentation Layer** — FastAPI REST API, Next.js web dashboard, Telegram bot.

**Key patterns:** Repository pattern for DB access, adapter pattern for data sources, LLM-as-service with Pydantic schema enforcement.

### Critical Pitfalls

See [PITFALLS.md](./PITFALLS.md) for the full list of 7 critical pitfalls plus Vietnamese market-specific traps.

1. **Vietnamese data sources are ephemeral** — Broker APIs (TCBS, SSI, VnDirect) change without notice. During research, TCBS returned empty responses and SSI returned 502. Only VCI (via vnstock) was reachable. *Prevention:* Use vnstock as abstraction layer, implement adapter pattern, cache historical data aggressively, build health checks before each fetch cycle.

2. **Unadjusted prices corrupt all technical analysis** — vnstock returns unadjusted historical prices. Stock splits and stock dividends (common on HOSE) create false signals in RSI, MACD, etc. *Prevention:* Implement price adjustment logic for corporate actions, source ex-date/ratio data from CafeF, validate against TradingView adjusted charts.

3. **Local LLMs hallucinate financial facts** — 7B-14B models confidently fabricate numbers ("VNM P/E is 15.2") from pattern matching. *Prevention:* NEVER ask LLM to recall facts. Always inject all data into the prompt. Use structured JSON output. Post-validate any numbers in LLM output against the database.

4. **Vietnamese sentiment analysis is much harder than English** — Word segmentation is mandatory, financial domain vocabulary differs from general Vietnamese, small LLMs have weak Vietnamese understanding. *Prevention:* Start with rule-based keyword sentiment ("giảm sàn" = strongly negative). Use underthesea for word segmentation. Consider PhoBERT for classification. Don't block scoring on perfect sentiment.

5. **Financial statement unit mismatch (BCTC)** — Companies report in different units (triệu đồng vs tỷ đồng vs đồng). Silent corruption makes one company's P/E 1,000x too low, promoting it to #1 in rankings. *Prevention:* Normalize all financial data to tỷ đồng at ingestion time. Store original unit alongside normalized value. Sanity-check P/E, ROE, EPS ranges.

## Implications for Roadmap

Based on combined research, the roadmap should follow the data dependency chain. You cannot analyze data you haven't crawled, score analysis you haven't computed, or present results that don't exist.

### Phase 1: Foundation & Data Pipeline
**Rationale:** Everything depends on having data in a database. Data ingestion is also the most fragile part (API instability, price adjustment, unit normalization) — get it right first.
**Delivers:** Project scaffold, database schema, price crawler, financial report crawler, corporate action adjustment, CLI to verify data integrity.
**Addresses:** Price/volume crawling, financial statement data, historical data backfill, company profile/listing info.
**Avoids:** Pitfall 1 (data source instability — adapter pattern), Pitfall 2 (unadjusted prices — corporate action handling), Pitfall 5 (BCTC unit mismatch — normalization at ingestion).

### Phase 2: Technical & Fundamental Analysis
**Rationale:** Pure computation, no LLM dependency. Produces the first two scoring dimensions. Gives you a usable (if incomplete) ranking system immediately.
**Delivers:** Technical indicators + scoring, fundamental ratios + scoring, basic composite score (2 dimensions), CLI ranked list.
**Addresses:** Core technical indicators, volume analysis, trend identification, financial ratios, revenue/profit growth, composite scoring (partial).
**Avoids:** Pitfall 6 (false precision — use categorical ratings from the start, show component scores).

### Phase 3: LLM Integration & Sentiment
**Rationale:** The most complex and least predictable component. By this point you already have a useful tool (technical + fundamental ranking). LLM adds the differentiating value.
**Delivers:** Ollama client wrapper, prompt templates, news crawler + sentiment classification, LLM report generation for top stocks, full 3-dimension scoring (tech + fundamental + sentiment).
**Addresses:** LLM-synthesized Vietnamese reports, Vietnamese news sentiment analysis, multi-dimensional score fusion.
**Avoids:** Pitfall 3 (LLM hallucination — data injection prompts from day one), Pitfall 4 (Vietnamese sentiment difficulty — start with rules, add ML later), Pitfall 7 (VRAM exhaustion — funnel approach, only LLM top 30-50 stocks).

### Phase 4: Automation & Notifications
**Rationale:** Only automate what works end-to-end manually. Scheduler + Telegram are the delivery mechanism for daily value.
**Delivers:** APScheduler daily pipeline, Telegram bot (daily digest + alerts), score change detection, error handling & monitoring, Vietnamese holiday calendar handling.
**Addresses:** Scheduled daily run, Telegram notifications, score change alerts, on-demand analysis triggers.
**Avoids:** Scheduler edge cases (weekends, Vietnamese holidays — Tết, 30/4, 2/9).

### Phase 5: Web Dashboard
**Rationale:** Dashboard is read-only presentation — it needs a fully populated database to display. Building UI before the pipeline runs is wasted effort. CLI + Telegram provide output in earlier phases.
**Delivers:** FastAPI REST API endpoints, Next.js dashboard with ranked stock table, stock detail view with charts (lightweight-charts), analysis report display.
**Addresses:** Web dashboard, stock charts, ranked stock browsing, report viewing.
**Avoids:** UX pitfalls (show data freshness timestamps, score breakdowns not just totals, confidence indicators).

### Phase 6: Macro Analysis & Refinement
**Rationale:** Macro analysis is the least data-available dimension (SBV/GSO data requires semi-manual collection). Add it last as the 4th scoring dimension. Use this phase for scoring calibration.
**Delivers:** Macro data collection, macro scoring, full 4-dimension composite score, industry/sector comparison, scoring weight calibration, retrospective accuracy tracking.
**Addresses:** Macro-economic context linking, industry comparison, customizable scoring weights, sector-relative scoring.
**Avoids:** Pitfall 6 (scoring overconfidence — backtest against historical returns in this phase).

### Phase Ordering Rationale

- **Data before analysis:** You cannot compute RSI without price data. You cannot calculate P/E without financial statements. Phase 1 must precede Phase 2.
- **Computation before LLM:** Technical and fundamental analysis are pure math — fast, deterministic, debuggable. Get these working before introducing the LLM's non-determinism. Phase 2 before Phase 3.
- **Manual before automated:** Run the pipeline manually end-to-end before adding a scheduler. Phase 3 completion before Phase 4 automation.
- **Backend before frontend:** A dashboard with no data is useless. CLI output and Telegram cover the presentation need while the pipeline matures. Phase 4 before Phase 5.
- **Core before enrichment:** Technical + fundamental + sentiment cover 80% of the scoring value. Macro is the hardest to source and least impactful dimension. Phase 6 is enhancement, not core.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 1 (Data Pipeline):** Corporate action data sourcing for HOSE needs investigation — where to reliably get ex-dates and split ratios. CafeF is the likely source but scraping patterns need validation.
- **Phase 3 (LLM Integration):** Prompt engineering for Vietnamese financial analysis is niche — little public guidance exists. Qwen2.5's actual Vietnamese financial text comprehension needs empirical testing. VRAM budget with 14B vs 7B model needs benchmarking on the actual RTX 3060.
- **Phase 4 (Automation):** Vietnamese public holiday calendar integration — need to find or build a reliable holiday list for market closures.

**Phases with standard patterns (skip deep research):**
- **Phase 2 (Analysis):** Technical indicators via pandas-ta and ratio calculations are well-documented, standard patterns. No research needed.
- **Phase 5 (Dashboard):** Next.js + shadcn/ui + lightweight-charts is a well-trodden path. Standard CRUD dashboard patterns apply.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified via PyPI/npm. Versions confirmed. vnstock is the only viable VN stock library — no alternatives. |
| Features | HIGH | Competitor analysis (Simplize, Fireant, WiChart, Danelfin) confirms feature gaps. MVP scope is well-defined with clear v1/v1.x/v2+ boundaries. |
| Architecture | HIGH | Pipeline architecture is the natural fit for batch data processing. Patterns are standard (repository, adapter, ETL). Build order follows clear dependency chain. |
| Pitfalls | HIGH | Verified via vnstock source code review, API endpoint testing, and issue tracker analysis. Vietnamese market-specific traps (±7% limits, corporate actions, đội lái) are domain-critical. |

**Overall confidence:** HIGH

### Gaps to Address

- **Database choice discrepancy:** STACK.md recommends PostgreSQL; ARCHITECTURE.md assumes SQLite for localhost. **Recommendation: Use PostgreSQL from the start** — Docker Compose makes it trivially easy, avoids migration later, and handles concurrent access from scheduler + API. SQLite is a false economy.
- **Corporate action data source:** No confirmed reliable API for HOSE corporate actions (ex-dates, split ratios, stock dividend rates). CafeF scraping is the likely approach but needs validation during Phase 1 planning.
- **Qwen2.5 Vietnamese performance:** Model recommendation is based on training data composition analysis, not empirical testing on Vietnamese financial text. Need to benchmark during Phase 3 — may need to fall back to 7B or try Vistral.
- **vnai dependency risk:** vnstock's mandatory `vnai` analytics package has caused issues (deadlocks on Windows, potential tracking concerns). May need to fork vnstock or patch out vnai if it becomes problematic on Linux.
- **PhoBERT vs LLM for sentiment:** PITFALLS.md recommends PhoBERT for sentiment classification, but STACK.md recommends underthesea + LLM. **Recommendation: Start with rule-based keyword sentiment (fastest, most reliable), upgrade to LLM-based classification if accuracy is sufficient, and only bring in PhoBERT if LLM sentiment proves inadequate** — PhoBERT competes for GPU VRAM with Ollama.

## Sources

### Primary (HIGH confidence)
- vnstock v3.5.1 — PyPI + GitHub (thinh-vu/vnstock) — stock data API, source code review
- FastAPI v0.135.3 — PyPI — backend framework
- Ollama Python v0.6.1 — PyPI + GitHub — LLM client
- pandas-ta v0.4.71b0 — PyPI — technical indicators
- Next.js v16.2.3 — npm — dashboard framework
- lightweight-charts v5.1.0 — npm — financial charts
- APScheduler v3.11.2 — PyPI — scheduler
- python-telegram-bot v22.7 — PyPI — notifications
- underthesea v9.4.0 — PyPI + GitHub — Vietnamese NLP
- Competitor platforms: Simplize, Fireant, WiChart — site crawls confirmed feature gaps
- HOSE market structure — price limits, ATC/ATO, T+2 settlement rules

### Secondary (MEDIUM confidence)
- Qwen2.5 14B VRAM requirements — quantization math estimates (~9-10GB Q4_K_M), needs empirical verification
- newspaper4k v0.9.5 — Vietnamese article extraction capability needs testing
- Vietnamese financial sentiment research — limited academic work, only 1 GitHub repo >20 stars
- Architecture patterns — synthesized from general financial data pipeline best practices, not VN-market-specific case studies

### Tertiary (LOW confidence)
- HOSE corporate action data sourcing — CafeF assumed but not validated as scraping target
- Vietnamese public holiday calendar — programmatic source not yet identified

---
*Research completed: 2025-07-18*
*Ready for roadmap: yes*
