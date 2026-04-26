# Pitfalls Research — LocalStock v1.4 AI Analysis Depth

**Domain:** Adding structured LLM outputs and new technical signals to existing Vietnamese stock analysis pipeline
**Researched:** 2026-04-25
**Confidence:** HIGH (based on direct codebase inspection + confirmed library behavior tests)

---

## Critical Pitfalls

### Pitfall 1: TA-Lib Dependency Silently Missing — cdl_pattern Returns None

**What goes wrong:** The existing codebase uses `pandas-ta>=0.4.71b0`, which is installed without TA-Lib. All 60+ TA-Lib candlestick patterns (`cdl_pattern(name="hammer")`, `cdl_pattern(name="engulfing")`, etc.) require TA-Lib to be installed separately. When TA-Lib is absent, `cdl_pattern()` prints a warning to stdout but **returns None instead of raising an exception**. Code that calls `df.ta.cdl_pattern(name="hammer", append=True)` silently does nothing — no column is added, no exception is thrown.

**Why it happens:** `pandas-ta` checks `Imports['talib']` at runtime. The project's `pyproject.toml` has no `TA-Lib` dependency, and `uv run python -c "import pandas_ta; print(pandas_ta.Imports)"` confirms `{'talib': False, ...}`. Developers assume `pandas-ta` handles candlesticks natively like it handles RSI/MACD.

**How to avoid:** Use only the 5 native pandas-ta candlestick functions: `ta.cdl_doji()`, `ta.cdl_inside()`, `ta.ha()`, `ta.cdl_z()`, and `ta.candle()`. These work without TA-Lib and were confirmed working in the environment. Do NOT use `cdl_pattern()` or any of the 60+ TA-Lib patterns unless TA-Lib is added to `pyproject.toml` as a compiled dependency. TA-Lib installation on Linux requires system-level `libta-lib-dev` package and a compiled wheel — it is not a simple `pip install`.

**Warning signs:** Adding a candlestick call, running the pipeline, checking the `technical_indicators` table — the CDL column simply doesn't exist. No error in logs. If using `append=True` on the DataFrame accessor (`.ta.cdl_pattern(name="hammer", append=True)`), the column is silently omitted.

**Phase to address:** The phase that implements candlestick pattern detection. Must decide upfront: implement TA-Lib on the server (compile step required), OR implement manual Python candlestick detection for the 3-5 most important patterns (doji, engulfing, hammer, morning/evening star) using pure OHLC math, OR use only the 5 native patterns available today.

---

### Pitfall 2: LLM Generating Implausible Price Levels — Hallucinated Float Fields

**What goes wrong:** When `StockReport` Pydantic schema is extended with `entry_price: Optional[float]`, `exit_price: Optional[float]`, and `stop_loss: Optional[float]`, the LLM (qwen2.5:14b) tends to hallucinate plausible-sounding but incorrect prices. The `format=StockReport.model_json_schema()` Ollama parameter enforces the **type** (float) but not the **semantic validity** (price must be near current close, stop-loss must be below entry for longs, etc.). A stock closing at 45,000 VND might get `entry_price: 45200.0`, `stop_loss: 43100.0`, `exit_price: 52000.0` — where the exit/entry ratio implies 15% gain with no basis in the data.

**Why it happens:** The current `REPORT_USER_TEMPLATE` injects `close_price`, `support_1`, `support_2`, `resistance_1`, `resistance_2` as formatted strings, but the LLM has no explicit instruction anchoring price levels to the injected support/resistance values. Without tight prompt constraints like "entry_price MUST be between support_1 ({support_1}) and current close ({close_price})", the model uses its parametric knowledge about "reasonable" stock price levels rather than the actual data.

**How to avoid:** Extend `REPORT_USER_TEMPLATE` with explicit price anchoring constraints in Vietnamese. Example: "Mức vào lệnh PHẢI trong khoảng {support_1} đến {close_price}. Cắt lỗ PHẢI thấp hơn {support_2}. Chốt lời PHẢI không vượt {resistance_2}." Add post-generation validation in the service layer: assert `stop_loss < entry_price < exit_price`, assert all prices are within ±30% of close. If validation fails, fall back to `None` values rather than storing garbage.

**Warning signs:** Generated price levels that are round numbers (50000, 60000) instead of values near actual S/R levels. Stop-loss above entry price. Exit targets more than 20% above current price for a "hold" recommendation. These indicate the LLM is not grounding on the injected data.

**Phase to address:** The prompt restructuring phase. Validation must be implemented in the same phase as the new schema fields — never store unvalidated price levels.

---

### Pitfall 3: Expanding StockReport Pydantic Schema Breaks Existing Stored JSON

**What goes wrong:** `AnalysisReport.content_json` stores the full `StockReport.model_dump()` as a JSON column. When new fields (`entry_price`, `risk_rating`, `signal_conflict`, `recent_catalyst`) are added to `StockReport`, all previously generated reports in the database have `content_json` without these keys. The frontend's `AIReportPanel` renders from `content_json` via `Object.entries(fallbackJson)` — so old reports just show missing sections. But any backend code that does `StockReport.model_validate(report.content_json)` on a stored report will fail with `ValidationError` if new required fields were not made `Optional` with defaults.

**Why it happens:** `content_json` is a schemaless JSON column — the DB doesn't enforce structure. Old rows are not migrated when the Pydantic model changes. The current `StockReport` has all required fields with no defaults. If a new field is added as required (no `Optional`, no `default`), `model_validate()` on old rows will raise `ValidationError`.

**How to avoid:** All new fields in `StockReport` must use `Optional[T] = None` or have a default value. Never add a required field without a default when stored JSON needs to remain backward-compatible. If a field like `risk_rating` must be required going forward, add it as `Optional[str] = None` initially, populate existing rows via a one-time migration script, then tighten to required after all rows are updated. Test backward compatibility by validating a sample of the oldest stored `content_json` against the new schema before deploying.

**Warning signs:** `ValidationError: field required` appearing in report service logs when reading old reports. 404 responses on `GET /api/reports/{symbol}` for stocks that had reports generated before the schema change.

**Phase to address:** The Pydantic schema extension phase. Required step: audit the existing `StockReport` class before adding any field, confirm backward-compatibility with a DB query checking oldest stored reports.

---

### Pitfall 4: Context Window Overflow When Injecting New Signals Into Existing Prompts

**What goes wrong:** The current `generate_report` call uses `options={"temperature": 0.3, "num_ctx": 4096}`. The existing `REPORT_USER_TEMPLATE` already injects ~600-800 characters of data. Adding candlestick pattern signals (e.g., "5 patterns detected: Doji, Inside Bar, ..."), volume divergence text, and sector momentum context could push the full prompt to 1,200-1,500 characters of user content plus system prompt. At num_ctx=4096, this is fine for input, but the LLM must also generate a full `StockReport` JSON response (9+ fields, each 50-200 words in Vietnamese). The combined input + output token budget at 4096 may cause truncated generation — the JSON gets cut mid-field, causing `model_validate_json()` to throw.

**Why it happens:** Token counting is not done before sending to Ollama. The `num_ctx=4096` setting is the entire context window (input + output combined for qwen2.5:14b). The existing report already pushes close to the limit. New signal fields in the template add input tokens; new output fields (`risk_reasoning`, `recent_catalyst`, `signal_conflict`) add output tokens.

**How to avoid:** Increase `num_ctx` to 8192 for report generation (qwen2.5:14b supports up to 131K context, RTX 3060 12GB can handle 8192 at Q4_K_M). Update the config setting `report_max_tokens` (currently 4096) and the hardcoded `options={"num_ctx": 4096}` in `client.py`. Add a rough token budget check before calling Ollama: if `len(prompt.split()) > 600` (a conservative approximation), log a warning.

**Warning signs:** `model_validate_json` raising `JSONDecodeError` or `ValidationError` on truncated output. Reports for stocks with many news articles (longer sentiment_summary) failing more often than stocks with sparse data. Logs showing `report_service.py` errors only for the last stocks in the batch (those processed when model memory is most loaded).

**Phase to address:** The prompt restructuring phase — increase `num_ctx` before adding new fields, not after observing failures.

---

### Pitfall 5: Alembic Migration Missing for New TechnicalIndicator Columns

**What goes wrong:** When new columns are added to `TechnicalIndicator` (e.g., `cdl_doji`, `cdl_inside`, `volume_divergence_signal`, `sector_momentum`) by editing `models.py`, the existing Supabase PostgreSQL database does not know about them until an Alembic migration runs. The analysis service will fail at `IndicatorRepository.bulk_upsert()` with `psycopg2.errors.UndefinedColumn` when trying to insert the new column values. Because the `to_indicator_row()` method returns a dict that is passed directly to the upsert, any key in the dict that doesn't exist as a column causes an immediate DB error for all stocks in the batch.

**Why it happens:** SQLAlchemy async with Alembic requires `alembic revision --autogenerate` + `alembic upgrade head` to sync models with the DB. The `init_db.py` startup script runs migrations, but only if it's explicitly re-run. The daily pipeline does not auto-migrate. In development it's easy to forget to run migrations after changing models.

**How to avoid:** For any new column on `TechnicalIndicator` or `AnalysisReport`: (1) add to `models.py`, (2) run `uv run alembic revision --autogenerate -m "add_v14_indicator_columns"` and review the generated file, (3) run `uv run alembic upgrade head` against the Supabase DB before deploying any analysis code that references the new column. Use `nullable=True` with a default for all new indicator columns — this allows the migration to run on a live table without requiring a full rewrite.

**Warning signs:** `sqlalchemy.exc.ProgrammingError: column "cdl_doji" of relation "technical_indicators" does not exist` in logs. Analysis service completes 0 stocks despite indicators being computed.

**Phase to address:** Any phase that adds columns to an existing table. Treat migration as the first sub-task, not the last.

---

### Pitfall 6: Volume Divergence Logic Producing Meaningless Signals on Low-Liquidity Stocks

**What goes wrong:** Volume divergence (price going up while OBV goes down, or vice versa) is a meaningful signal only for stocks with consistent trading activity. HOSE has ~400 tracked stocks, but many small-caps trade fewer than 50,000 shares/day. Computing OBV-based divergence on these stocks yields noisy, unreliable signals because a single large-block trade can flip the OBV trend. Worse, if this noisy signal is injected into the LLM prompt as "volume divergence: bearish", the LLM will write a bearish section even when the stock has fundamentally strong data — poisoning the report.

**Why it happens:** The existing `compute_volume_analysis()` already handles `len(df) < 20` gracefully, but has no threshold for minimum average daily volume. The `relative_volume` field exists in `TechnicalIndicator` but no downstream gate filters out low-volume stocks before feeding signals to the LLM.

**How to avoid:** Add a minimum volume threshold before computing divergence signals. Stocks with `avg_volume_20 < 100_000` shares/day should have volume signals explicitly marked as `"insufficient_volume"` and excluded from the LLM prompt. The `ReportDataBuilder.build()` method can gate on `indicator_data.get("avg_volume_20", 0) < 100_000` and substitute a null/absent signal for the volume divergence section. Document this threshold in the config.

**Warning signs:** Small-cap stocks (market cap < 1,000 Bn VND) consistently getting "volume divergence: bearish" signals regardless of price action. Sector momentum showing contradictory signals week-over-week for the same sector.

**Phase to address:** The volume divergence signal computation phase. Gate logic must be implemented alongside the signal — not retrofitted after observing bad reports.

---

## Moderate Pitfalls

### Pitfall 7: risk_rating String Field With No Enum Constraint — LLM Invents Values

**What goes wrong:** If `risk_rating` is defined as `str` in the Pydantic schema without an `Enum` or `Literal` constraint, the LLM may generate values like "cao" (Vietnamese for "high"), "trung bình", "thấp", "medium-high", "Cao (Rủi ro cao)", etc. instead of the expected `"high"/"medium"/"low"`. The frontend then cannot reliably map the string to a color/badge component.

**How to avoid:** Use `Literal["high", "medium", "low"]` for the type annotation. The Ollama `format` parameter derives the JSON schema from the Pydantic model, and `Literal` types produce an `enum` constraint in the JSON schema that Ollama's constrained decoding enforces. Also add a Vietnamese mapping in `REPORT_SYSTEM_PROMPT`: "risk_rating: 'high' (rủi ro cao), 'medium' (rủi ro trung bình), hoặc 'low' (rủi ro thấp)."

**Phase to address:** Schema design phase — use Literal from the start.

---

### Pitfall 8: Candlestick Signal Staleness — Patterns Computed on Previous Day's Data

**What goes wrong:** The daily pipeline runs at 15:45 ICT, after market close. The `TechnicalAnalyzer.compute_indicators()` computes all indicators on the latest available OHLCV data (today's close). Candlestick patterns are inherently daily patterns — a "doji" detected today means today's candle formed a doji. But because the data crawl and analysis run sequentially, if the price crawl fails for a symbol, the indicator computation uses yesterday's data. The candlestick signal stored is for D-1, but the report generated says "doji detected" as if it's today's signal — potentially misleading.

**How to avoid:** Add `date` validation in `to_indicator_row()`: assert that the `last_date` matches the expected crawl date. If a symbol's latest price row is more than 1 trading day old, skip candlestick signal injection for that symbol and log a warning. The existing `TechnicalAnalyzer.to_indicator_row()` already captures `last_date` — add a staleness check there.

**Phase to address:** Candlestick detection phase. Simple guard, high value.

---

### Pitfall 9: Sector Momentum Signal Circular Reference in Scoring

**What goes wrong:** Sector momentum is computed from `SectorSnapshot.avg_score`, which is itself derived from `CompositeScore.total_score` for all stocks in the sector. If sector momentum is then fed back into each stock's LLM report as "sector is bullish", the LLM may reinforce a stock's positive framing purely because its sector has a high composite score — which was already influenced by the stock's own score. This creates a self-reinforcing bias where high-scoring stocks get more bullish narrative purely because they're in a sector of other high-scoring stocks.

**How to avoid:** Sector momentum should be computed from price-based metrics (volume flow, price return of the sector index) rather than from composite scores. Use `SectorSnapshot.avg_volume` change and the average close-price return of sector constituents (both already crawlable from `StockPrice`) as the momentum signal. Feed "sector price return +5% over 5 days" to the LLM, not "sector composite score is 75."

**Phase to address:** Sector momentum signal design phase. Design the signal source before implementing the computation.

---

### Pitfall 10: Frontend Type Mismatch When Adding New Report Fields

**What goes wrong:** The `StockReport` TypeScript interface in `apps/helios/src/lib/types.ts` has `content_json: Record<string, unknown> | null`. The `AIReportPanel` component renders from `content_json` via `Object.entries(fallbackJson)`. When new structured fields (`entry_price`, `stop_loss`, `risk_rating`) are added to the backend `StockReport` Pydantic model, they appear as keys in `content_json`. The frontend's fallback rendering will display `entry_price` as "entry price: 45200" in plain text — no formatting, no currency, no risk-color badge.

**How to avoid:** For each new structured field added to `content_json`, update the frontend rendering in `AIReportPanel` with specific UI treatment: price levels formatted as VND (`formatVND()`), risk_rating rendered as a colored badge, signal_conflict surfaced with a distinct visual indicator. Add TypeScript types for the new fields to the `StockReport` interface. Do not rely on the generic `Object.entries` fallback for v1.4 features — it will silently display raw data without the UX polish the feature requires.

**Warning signs:** New trade plan data appearing as raw JSON keys in the AI report panel. Numbers displayed without VND formatting (e.g., "45200" instead of "45,200 ₫").

**Phase to address:** The frontend trade plan display phase — explicit rendering must be built alongside, not after, the backend schema change.

---

### Pitfall 11: Ollama Retry Storm During Batch Report Generation

**What goes wrong:** The current `generate_report()` has `stop_after_attempt(2)` with `wait_exponential(min=5, max=30)`. During batch generation for 20 stocks, if Ollama becomes slow (e.g., model swapped out due to `keep_alive` expiry, or GPU memory pressure after processing 15 dense reports), retries stack up. Two retries × 20 stocks × 30s max wait = up to 20 minutes of retry overhead on top of normal generation time. The `asyncio.Lock` in `routes/reports.py` means only one batch runs at a time, but sequential retries within the batch cause wall-clock time to balloon.

**How to avoid:** Keep `stop_after_attempt(2)` but reduce `wait_exponential(max=10)` for the report call. More importantly, add a `keep_alive=self.keep_alive` call that's currently already set (30m). Ensure `num_ctx` is set explicitly to prevent the model from being evicted mid-batch. Consider adding a `pre_ping` Ollama health check before each stock (not just once at batch start) if the batch takes more than 5 minutes.

**Phase to address:** Prompt/generation restructuring phase. Tune before adding more fields that increase generation time per stock.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store new fields in existing `content_json` JSON column (no schema migration) | No Alembic migration needed | Can't query/filter on fields (e.g., find all stocks with `risk_rating='high'`) | Acceptable for MVP if querying is not required |
| Add signal text to existing prompt template (string concat) | No new template design | Prompt grows unbounded, token overflow risk | Never — use structured injection with length caps |
| Skip volume threshold guard, compute divergence on all stocks | Simpler code | Noisy signals for small-caps poison LLM reports | Never |
| Use `str` instead of `Literal` for `risk_rating` field | Flexibility | LLM invents values, frontend can't map reliably | Never |
| Not adding candlestick migration, relying on nullable columns being auto-ignored | Fewer steps | psycopg2 `UndefinedColumn` error crashes the entire batch | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ollama `format=` parameter | Passing too large a schema (10+ fields, nested objects) — model may hallucinate schema compliance without actually filling all fields | Keep schema flat (no nesting), use `Optional` for all non-critical fields, validate every field post-generation |
| pandas-ta `cdl_pattern()` | Calling without TA-Lib — silently returns `None`, no column added | Check `pandas_ta.Imports['talib']` before calling; use only `cdl_doji`, `cdl_inside`, `cdl_z`, `ha` natively |
| Alembic autogenerate on Supabase | Running `alembic revision --autogenerate` against the local DB copy — generates correct diff but misses Supabase-specific extensions (e.g., row-level security policies) | Always run `--autogenerate` against the actual Supabase connection string, review output carefully |
| `content_json` backward compatibility | Validating stored JSON with new required-field Pydantic model — raises `ValidationError` on old rows | All new `StockReport` fields must be `Optional[T] = None` |
| `REPORT_USER_TEMPLATE` string formatting | Adding new `{placeholder}` keys to the template without adding them to `ReportDataBuilder.build()` — raises `KeyError` at runtime for every stock | Add both the template placeholder and the `build()` key in the same commit |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing OBV divergence on all 400 stocks sequentially in analysis service | Analysis pipeline time increases from ~5 min to ~12 min | Gate on avg_volume threshold (skip small-caps), batch OBV computation | At 400 stocks, OBV + trend already runs; adding divergence comparison adds ~1s/stock |
| Increasing `num_ctx` to 8192 without measuring GPU memory | RTX 3060 (12GB VRAM) runs out of memory mid-batch; Ollama crashes silently | Test with `num_ctx=8192` on qwen2.5:14b Q4_K_M for 5 sequential requests before enabling for full batch | 12GB VRAM is sufficient for 8K context at Q4_K_M, but concurrent requests would OOM |
| Adding 5 new columns to `TechnicalIndicator` bulk upsert | `bulk_upsert` generates 5 extra columns per INSERT for 400 stocks — negligible at this scale | Not a performance concern at current scale | Would become relevant only at 10K+ stocks |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Displaying raw `entry_price: 45200.0` from `content_json` without formatting | User sees "45200" instead of "45,200 ₫" — looks like a bug | Use `formatVND()` utility that already exists in `apps/helios/src/lib/utils.ts` for all price fields |
| Showing "signal_conflict: null" when no conflict exists | Noise in the UI — user wonders what they're missing | Only render the signal conflict section when `signal_conflict !== null && signal_conflict !== ""` |
| Displaying trade plan prices without current price context | User can't assess whether entry_price is reasonable without knowing where the stock trades now | Always show `entry_price` alongside current close price; show percentage distance (`+2.3% from current`) |
| risk_rating badge with no explanation tooltip | User sees "HIGH" risk badge but doesn't know why | Display `risk_reasoning` as tooltip or expandable section beneath the badge |
| Candlestick pattern names displayed in English (CDL_DOJI) | Vietnamese audience unfamiliar with pattern codes | Map pattern codes to Vietnamese: `cdl_doji → Nến Doji`, `cdl_inside → Nến Inside Bar` |

---

## "Looks Done But Isn't" Checklist

- [ ] **Candlestick patterns:** Patterns appear in DB indicator row — verify TA-Lib is not silently missing. Run `python -c "import pandas_ta; print(pandas_ta.Imports)"` to confirm.
- [ ] **Price levels in report:** `entry_price` and `stop_loss` are populated in `content_json` — verify they're within ±15% of current close, not hallucinated round numbers.
- [ ] **risk_rating field:** Values stored in DB are exactly `"high"`, `"medium"`, or `"low"` — not Vietnamese or compound strings.
- [ ] **Schema backward compatibility:** Old reports (generated before v1.4) can still be fetched via `GET /api/reports/{symbol}` without 500 errors — verify `model_validate` handles missing new fields.
- [ ] **Alembic migration applied:** `uv run alembic current` shows head revision includes new columns — not just that `models.py` was updated.
- [ ] **Volume threshold guard:** Small-cap stocks (< 100k shares/day avg volume) do NOT have volume divergence signals injected into their prompts.
- [ ] **Frontend type coverage:** New `StockReport` fields have explicit TypeScript types and explicit render paths in `AIReportPanel` — not falling through to the generic `Object.entries` fallback.
- [ ] **num_ctx increased:** Ollama `generate_report` call uses `num_ctx >= 6144` to accommodate new prompt content + new output fields.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| TA-Lib not installed, no CDL signals in DB | LOW | Decision: (1) install TA-Lib via system package + compiled wheel, or (2) implement 3 manual patterns in pure Python. Both take ~2-4 hours. |
| Price levels hallucinated and stored in DB | MEDIUM | Add post-gen validation, rerun report generation for affected stocks (POST /api/reports/run replaces via upsert) — no data loss, upsert overwrites. |
| Pydantic schema broke old `content_json` reads | HIGH | Make all new fields Optional immediately, redeploy, then run a one-time script to backfill missing fields with null. Old reports will show incomplete new sections — acceptable. |
| num_ctx too low, JSON truncation causing ValidationError | LOW | Increase `num_ctx` in config and `client.py`, rerun report generation. No DB migration needed. |
| Alembic migration not applied, bulk_upsert crashing | MEDIUM | Run migration immediately. If Supabase has production data, the migration adds nullable columns — zero data loss. Pipeline will need to re-run for the day. |
| Sector momentum circular bias discovered after shipping | MEDIUM | Switch signal source from avg_score to price-return; recompute sector snapshots. Sector snapshots are an append-only table — no data to fix, just new computation. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| TA-Lib silent miss (P1) | Candlestick detection phase | Run `pandas_ta.Imports` check in CI; confirm CDL columns exist in DB after analysis |
| LLM price level hallucination (P2) | Prompt restructuring phase | Assert `stop_loss < entry_price < exit_price` and all prices within ±30% of close in post-generation validation |
| StockReport schema breaks old JSON (P3) | Schema extension phase (before any new fields deployed) | Test `StockReport.model_validate(old_report.content_json)` against 5 oldest DB rows |
| Context window overflow (P4) | Prompt restructuring phase — increase num_ctx before adding fields | Verify no `JSONDecodeError` in report logs for 3 consecutive days of batch generation |
| Missing Alembic migration (P5) | Any phase adding DB columns | `uv run alembic current` shows head; DB schema matches ORM models |
| Volume divergence on low-liquidity stocks (P6) | Volume divergence signal phase | Confirm stocks with avg_volume < 100k are absent from volume divergence section of generated reports |
| risk_rating enum violation (P7) | Schema design | Query `SELECT DISTINCT content_json->>'risk_rating' FROM analysis_reports` — should return only 3 values |
| Candlestick staleness (P8) | Candlestick detection phase | Add date assertion in `to_indicator_row()` |
| Sector momentum circular bias (P9) | Sector momentum design | Signal source is price-return or volume-flow, not composite score |
| Frontend type mismatch (P10) | Frontend trade plan display phase | Manual test: price fields show VND format; risk_rating shows badge not raw string |
| Ollama retry storm (P11) | Prompt restructuring phase | Observe batch generation wall-clock time; should be < 15 minutes for 20 stocks |

---

## Sources

- Direct codebase inspection: `apps/prometheus/src/localstock/ai/client.py`, `ai/prompts.py`, `reports/generator.py`, `analysis/technical.py`, `analysis/trend.py`, `db/models.py`, `services/report_service.py`, `services/sector_service.py`, `config.py`
- Live environment test: `uv run python -c "import pandas_ta; print(pandas_ta.Imports)"` → `{'talib': False, ...}`
- Live test: `ta.cdl_pattern(name="hammer")` returns `None` silently without TA-Lib installed
- Live test: `ta.cdl_doji()`, `ta.cdl_inside()`, `ta.ha()` work without TA-Lib
- Context7: `/websites/pandas-ta_dev` — candlestick patterns require TA-Lib for `cdl_pattern()`; 5 native patterns available without it
- Context7: `/xgboosted/pandas-ta-classic` — confirms TA-Lib dependency for 62 patterns, 5 native
- Context7: `/ollama/ollama-python` — `format=` enforces type schema but not semantic validity
- Context7: `/llmstxt/ollama_llms_txt` — `num_ctx` default is 2048, must be set explicitly; `num_ctx` covers input + output combined
- Direct inspection: `pyproject.toml` — `pandas-ta>=0.4.71b0` present, no `TA-Lib` entry
- Direct inspection: `alembic/versions/` — 7 migration files confirm manual migration workflow required

---
*Pitfalls research for: AI Analysis Depth addition to existing LocalStock pipeline*
*Researched: 2026-04-25*
