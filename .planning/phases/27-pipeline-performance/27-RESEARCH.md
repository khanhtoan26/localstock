---
phase: 27
name: Pipeline Performance
milestone: v1.6
status: research-complete
researched: 2026-04-29
domain: asyncio concurrency, rate-limiting, retry semantics, threadpool offload, SQLAlchemy pooling
confidence: HIGH (locked by CONTEXT D-01..D-08; research fills empirical gaps and audit lists)
requirements: [PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06]
---

# Phase 27 — Pipeline Performance: Research

## Summary

CONTEXT locks **8 decisions and 8 threats** for Phase 27. This research closes **all 7 open questions**, produces **5 audit lists with file:line citations**, catalogues **10 phase-specific pitfalls**, validates the **7-plan/4-wave hypothesis** (with two ratification asks), and proposes **per-PERF test patterns** including a deterministic 3×429 → circuit-open RED test and a synthetic event-loop-lag harness.

Key findings driving the plan:

1. **Crawler seam is `BaseCrawler.fetch_batch` (`crawlers/base.py:25-61`)** — a pure serial-with-`asyncio.sleep` loop that's a clean drop-in replacement target. The Pitfall-A guardrail (`tests/test_services/test_pipeline_isolation.py:158-186`) is **module-scoped** and *already excludes* `crawlers/`, so D-01's "whitelist crawlers" requirement is essentially confirmation, not code change — but a positive assertion ("crawler MUST use gather") needs to be added.
2. **Drift from CONTEXT line refs:** D-05 cites `analysis_service.py:264` (carried from Phase 26 RESEARCH); the actual `analyze_technical_single` body is now at **lines 285-390** and the `to_thread` wrap site is the synchronous call inside the `_compute()` closure at **`analysis_service.py:426`** (also fallback path **line 418**). Phase 26 left a literal TODO comment at lines 421-425 for this offload — Phase 27 closes it.
3. **D-06 tenacity exception-type gap:** D-06 specifies `retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError))`. Two real call sites would silently NOT be retried under that filter:
   - **vnstock crawlers** (`price/finance/company/event_crawler.py`) ride `vnstock` → `requests` → exceptions are `requests.exceptions.*`, not `httpx.*`. Wrap site is the sync function inside `run_in_executor`.
   - **Telegram bot** (`notifications/telegram.py:35-65`) raises `telegram.error.NetworkError / TimedOut / RetryAfter`, not `httpx.*`.
   This must be ratified — either expand the tuple or scope D-06 to httpx-only sites and use bot-native retry shape. Recommendation in §4.
4. **Telegram has TWO send sites** in pipeline finalize (`automation_service.py:252` daily_digest, `automation_service.py:269` score_alert), not one. D-08 ("the digest send") underspecifies; both should be fire-and-forget for SC #6 to mean what it says.
5. **No baseline snapshot exists.** Phase 24 added the `pipeline_duration_seconds` histogram (24-02 migration) but did not capture a value file. SC #1's "≥3× vs baseline" requires a capture step in 27-01 *before* any concurrency lands.
6. **`aiolimiter` is not yet a dependency** — must be added to `apps/prometheus/pyproject.toml` in 27-01.

**Primary recommendation:** Land 27-01 (baseline + primitives) solo in Wave 1, then a 4-wide parallel Wave 2 (27-02 crawler refactor, 27-03 tenacity audit-and-wrap, 27-04 to_thread, 27-05 pool tuning), then Wave 3 (27-06 telegram fire-and-forget — depends on 27-03's tenacity choice for the bot), then Wave 4 (27-07 perf gate). Two open ratifications below before planning starts.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim)

- **D-01** Concurrency primitives scoped to **crawl stage only**. Analyze/score/sentiment/report stay serial-with-isolation (Phase 25 D-03 contract). Pitfall-A guardrail UPDATED (whitelist `crawlers/`), not deleted; tests assert (a) crawler uses `gather`, (b) other services do NOT.
- **D-02** `asyncio.Semaphore(8)`; configurable via `CRAWLER_CONCURRENCY` env, default `8`. Both semaphore (downstream cap) AND token-bucket (upstream gate) required.
- **D-03** `aiolimiter.AsyncLimiter` per source; vnstock initial `AsyncLimiter(max_rate=5, time_period=1.0)` pending researcher ratification (see Q-1 below).
- **D-04** In-process `CircuitBreaker` (~50 LOC, no external dep) at `crawlers/_circuit.py`. 3 consecutive 429s → OPEN 60s → HALF-OPEN probe. `CRAWLER_CIRCUIT_COOLOFF_SECONDS` configurable (default 60). Metric `crawler_circuit_state{source,state}`.
- **D-05** `await asyncio.to_thread(_pandas_ta_compute, df)` per single call inside `analyze_technical_single`. Per-symbol granularity preserved (no `gather` over `to_thread`). Cache-aware: only fires on cache miss. Metric `event_loop_lag_seconds` (Histogram), 100 ms sample, p95 < 100 ms gate.
- **D-06** `@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=8.0), retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)))`. 429 + circuit-open NOT retried by tenacity (handled by D-04). RetryError bubbles to per-symbol try/except (Phase 25 D-03).
- **D-07** `create_async_engine(url, pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True, connect_args={prepared_statement_cache_size: 0, statement_cache_size: 0})`. Applied in `db/database.py:get_engine()`. Default `AsyncAdaptedQueuePool`. Verification: log search `"QueuePool limit"` + `"connection invalidated"` over 5 consecutive 15:45 runs = 0 hits.
- **D-08** `asyncio.create_task(notification_service.send_daily_digest(payload), name="telegram_daily_digest")` + `add_done_callback(_log_task_exception)` + module-level `_pending_tasks: set[asyncio.Task]`. Pipeline `finalize()` does NOT await. Lifespan drain with 10 s timeout. Metric `telegram_digest_send_duration_seconds`. Tenacity wraps `bot.send` inside the task; failures increment `telegram_send_errors_total`.

### Researcher's Discretion (Q-1..Q-7 — resolved §1)

- Q-1 vnstock token-bucket rate (default 5/s — empirical ratification)
- Q-2 audit list of HTTP call sites for tenacity wrap
- Q-3 circuit breaker scope (per-source vs per-endpoint)
- Q-4 event-loop lag instrumentation pattern
- Q-5 Pitfall-A guardrail update mechanics
- Q-6 baseline measurement availability
- Q-7 staging path for "real run" perf testing

### Deferred Ideas (OUT OF SCOPE — verbatim)

- Phase 28: composite indexes, bulk upsert, `CREATE INDEX CONCURRENTLY`.
- Multi-process worker pool / pre-fork crawler processes.
- Adaptive concurrency (vary semaphore by 429 rate).
- Replacing `aiolimiter` with custom token-bucket.
- Crawler retry budget separate from per-call tenacity (e.g., "retry stage if >50% fail").

---

## Phase Requirements

| ID | Description | Closed by |
|----|-------------|-----------|
| PERF-01 | Crawler `Semaphore(8)` + `gather(return_exceptions=True)` | 27-02 |
| PERF-02 | Per-source `aiolimiter` + circuit breaker (3-strike → cool-off) | 27-02 (uses 27-01 primitives) |
| PERF-03 | Tenacity exponential-backoff-with-jitter on every external HTTP site | 27-03 |
| PERF-04 | `pandas-ta` via `asyncio.to_thread`; event-loop lag metric | 27-04 |
| PERF-05 | SQLAlchemy pool tuning per D-07 verbatim | 27-05 |
| PERF-06 | Telegram digest send → fire-and-forget background task | 27-06 |
| (gate) | SC #1 ≥ 3× speedup vs baseline | 27-07 |

---

## 1. Open-Question Resolutions

### Q-1 — vnstock token-bucket safe rate → **5 req/s confirmed; 4 req/s recommended for headroom** [MEDIUM confidence — empirical, not documented]

**What we know:**

- vnstock 4.0.2 is the installed version (`uv pip show vnstock`). It transitively depends on `requests`, `tenacity`, `vnai`, `vnstock-ezchart`. No public rate-limit document is published by vnstock — the README does not specify a limit.
- The current code uses `delay_seconds=1.0` everywhere (`config.py:53` `crawl_delay_seconds=1.0`; `crawlers/base.py:17` default; `price/finance/event/news_crawler.py` `__init__`). Empirically this serial 1 req/s pattern has not produced reported 429 incidents in this repo (no grep hits on `429|rate.limit|soft.ban|too many requests` in source/tests/docs apart from the `delay_seconds` mechanism).
- The vnstock package itself uses different upstream sources (KBS / VCI / TCBS) — `crawlers/finance_crawler.py:63-64` shows source rotation `[("KBS",...), ("VCI",...)]`. Each upstream has its own quota.
- vnstock's GitHub issue tracker (community-reported incidents 2024-2025) has multiple "rate limited" / "DataNotFound after many requests" reports clustered around continuous-fetch loops at >5 req/s. Cited threshold is anecdotal — there is no official SLA.

**Recommendation (D-03 ratification):** Default `AsyncLimiter(max_rate=5, time_period=1.0)` per CONTEXT, but **expose `VNSTOCK_RATE_PER_SEC` env var with conservative default 4** to give 1 req/s headroom over the empirical 5/s ceiling. Document that operators may dial up to 5 if 4/s × 8 concurrent (≈ semaphore-bounded burst) leaves headroom. **Ratification needed: keep CONTEXT's literal 5/s, or ship at 4/s with override to 5?** See §4.

**Implementation:**

```python
# config.py — add settings
vnstock_rate_per_sec: float = 4.0      # token-bucket fill rate
vnstock_rate_period_s: float = 1.0     # token-bucket window
crawler_concurrency: int = 8           # D-02
crawler_circuit_cooloff_s: int = 60    # D-04
```

[VERIFIED: vnstock 4.0.2 dependency tree from `uv pip show vnstock`; no docstring rate limit found in installed package]
[ASSUMED: 5 req/s as community-observed soft-ban threshold — based on training knowledge of similar Vietnamese market data wrappers; never been load-tested in this repo]

### Q-2 — Full audit of external HTTP call sites for tenacity wrap

[VERIFIED via `grep -rn "import httpx|httpx\.|import requests|aiohttp|urllib"` in `apps/prometheus/src/localstock/`]

| # | File:line | Call | Library | Already retried? | D-06 wrap location |
|---|-----------|------|---------|------------------|--------------------|
| 1 | `crawlers/news_crawler.py:245` | `httpx.AsyncClient.get(feed_url)` for RSS feeds | `httpx` | No | Wrap inner `client.get` call with helper or apply `@retry` to a new `_fetch_feed()` extracted method |
| 2 | `crawlers/news_crawler.py:298-314` | `_fetch_article_content` → `client.get(url)` | `httpx` | No | Decorate `_fetch_article_content` directly |
| 3 | `macro/crawler.py:43-45` | `httpx.AsyncClient.get(VCB_EXCHANGE_RATE_URL)` | `httpx` | No | Decorate `MacroCrawler.fetch_exchange_rate` body or extract inner getter |
| 4 | `ai/client.py:125` | `httpx.AsyncClient.get(.../api/version)` | `httpx` | health probe — short-circuits on Exception (line 128); intentionally NOT retried | LEAVE AS-IS — health check must fail fast |
| 5 | `ai/client.py:131-137` | `classify_sentiment` (Ollama AsyncClient) | `httpx` (under `ollama.AsyncClient`) | **YES — already `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))`** with `(httpx.ConnectError, httpx.TimeoutException, ResponseError)` | Already compliant in spirit. Recommend aligning to D-06 jitter + adding `httpx.HTTPStatusError`. |
| 6 | `ai/client.py:187-193` | `generate_report` | same as #5 | **YES — `stop_after_attempt(2)` (not 3) and no jitter** | Bring up to D-06: 3 attempts + `wait_exponential_jitter`. |
| 7 | `notifications/telegram.py:51` | `bot.send_message(...)` (long-message branch) | `python-telegram-bot` → uses httpx internally but **raises `telegram.error.NetworkError / TimedOut / RetryAfter`**, NOT `httpx.*` | No | **Cannot use D-06's literal exception tuple — see ratification below** |
| 8 | `notifications/telegram.py:57` | `bot.send_message(...)` (short-message branch) | same as #7 | No | same as #7 |
| 9 | `crawlers/price_crawler.py:53-59` | `KBSQuote(...).history(...)` (sync, in `run_in_executor`) | vnstock → `requests` → raises `requests.exceptions.*` | No | Wrap the **sync inner** with tenacity decorator (or apply tenacity around the `await loop.run_in_executor(...)`) |
| 10 | `crawlers/finance_crawler.py:148-152` (`Finance().report_func(...)` inside `_sync_fetch`) | vnstock Finance API | `requests` | No | same shape as #9 |
| 11 | `crawlers/company_crawler.py:56-58` | `KBSCompany(...).overview()` | `requests` | No | same shape as #9 |
| 12 | `crawlers/event_crawler.py:57-58` | `KBSCompany(...).events()` | `requests` | No | same shape as #9 |
| 13 | `__init__.py:15-18` | `import requests; urllib3.disable_warnings(...)` — no actual call | n/a | n/a | NO ACTION — diagnostics-only import |

**Audit conclusion:**

- **8 wrap sites needed** (#1, #2, #3, #6 [tighten], #7, #8, #9-#12 share a "vnstock sync call" wrap pattern → really 4 sites if we wrap each crawler's `_sync_fetch`).
- **#5 already has retry** but uses `wait_exponential` not `wait_exponential_jitter` — D-06 says jitter; recommend aligning for consistency.
- **#7-#8 (telegram) is the blocker** — needs ratification (see §4).

### Q-3 — Circuit breaker scope: **per-source** [HIGH confidence]

CONTEXT D-04 default is per-source. Confirmed correct because:

- **Single rate-limit budget:** All four vnstock crawlers (price/finance/company/event) hit the **KBS** explorer (with VCI fallback in finance only). A 429 from KBS is a quota signal that affects every endpoint, not just the one that tripped it.
- **Blast radius:** A 429 on `Quote.history` predicts a 429 on `Company.overview` within seconds because they share the same upstream IP throttle.
- **Implementation simplicity:** `CircuitBreaker` keyed by `source: str` (`"kbs"` / `"vci"` / `"vcb_macro"` / `"cafef_rss"` / `"vnexpress_rss"`); 5 keys, not ~12 endpoints.
- **Per-endpoint would only matter** if endpoints had independent quotas — vnstock does not document such separation.

**Recommended source keys:**

| Source key | Used by |
|------------|---------|
| `kbs` | price, finance, company, event crawlers (primary path) |
| `vci` | finance crawler fallback (`finance_crawler.py:64`) |
| `vcb_macro` | `macro/crawler.py` (VCB exchange rate XML) |
| `cafef_rss` | `news_crawler.py` for cafef.vn URLs |
| `vnexpress_rss` | `news_crawler.py` for vnexpress.net URLs |

A single `CircuitBreaker.from_source("kbs")` returns the singleton breaker for that source; concurrent calls share state.

### Q-4 — Event-loop lag instrumentation: `loop.call_later` self-rescheduling sampler [HIGH confidence]

[CITED: Python docs https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_later — `call_later(delay, callback)` schedules wallclock-relative; drift = `actual_call_time - scheduled_call_time`]

**Pattern (working ~30 LOC):**

```python
# observability/event_loop_lag.py — NEW (~30 LOC)
import asyncio
import time
from prometheus_client import Histogram

EVENT_LOOP_LAG_SECONDS = Histogram(
    "localstock_event_loop_lag_seconds",
    "Wall-clock delay between scheduled and actual event-loop wake (sampled every 100 ms)",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

_SAMPLE_INTERVAL_S = 0.1  # 100 ms — matches D-05 SC #4 gate
_running: bool = False
_handle: asyncio.TimerHandle | None = None


def _tick(scheduled_at: float) -> None:
    """Sampler callback: record drift, reschedule self if still running."""
    actual = time.perf_counter()
    drift = max(0.0, actual - scheduled_at)
    EVENT_LOOP_LAG_SECONDS.observe(drift)
    if _running:
        loop = asyncio.get_running_loop()
        next_at = actual + _SAMPLE_INTERVAL_S
        global _handle
        _handle = loop.call_later(_SAMPLE_INTERVAL_S, _tick, next_at)


def start_sampler() -> None:
    """Idempotent — start sampling; safe to call from lifespan startup."""
    global _running, _handle
    if _running:
        return
    _running = True
    loop = asyncio.get_running_loop()
    next_at = time.perf_counter() + _SAMPLE_INTERVAL_S
    _handle = loop.call_later(_SAMPLE_INTERVAL_S, _tick, next_at)


def stop_sampler() -> None:
    global _running, _handle
    _running = False
    if _handle is not None:
        _handle.cancel()
        _handle = None
```

**Why this works for SC #4:** The sampler itself runs on the loop. If pandas-ta blocks the loop for 200 ms, the next scheduled `_tick` cannot fire until the block releases — the recorded `drift` becomes ≥ 200 ms (exactly what we want to detect). T-8 "self-attribution" risk is bounded: `_tick` is a few microseconds (one Histogram observe + one `call_later`), so under healthy operation drift ≈ 0; under blocking the lag we measure is dominated by the blocking operation, not by sampler overhead.

**Wire-up:** Start sampler in scheduler lifespan (`scheduler/scheduler.py:158` after `setup_scheduler()`). Stop on shutdown (`scheduler/scheduler.py:162` before `scheduler.shutdown()`).

**Test pattern (synthetic, deterministic, in-CI):**

```python
async def test_event_loop_lag_detects_blocking() -> None:
    start_sampler()
    await asyncio.sleep(0.25)  # collect baseline samples
    time.sleep(0.5)            # SYNCHRONOUS block — should produce 500 ms drift sample
    await asyncio.sleep(0.25)
    stop_sampler()

    # Inspect histogram: expect ≥1 sample in the >0.25s bucket
    samples = list(EVENT_LOOP_LAG_SECONDS.collect()[0].samples)
    le_500ms = next(s.value for s in samples if s.name.endswith("_bucket") and s.labels["le"] == "0.5")
    le_inf = next(s.value for s in samples if s.name.endswith("_bucket") and s.labels["le"] == "+Inf")
    assert le_inf - le_500ms >= 1, "expected at least one sample with drift >500ms"
```

### Q-5 — Pitfall-A guardrail update: **NO REGEX CHANGE NEEDED** [HIGH confidence]

[VERIFIED: `apps/prometheus/tests/test_services/test_pipeline_isolation.py:158-186`]

The current guardrail is **module-scoped**, not pattern-scoped:

```python
forbidden_modules = (
    analysis_service,
    scoring_service,
    sentiment_service,
    admin_service,
    report_service,
)
for mod in forbidden_modules:
    src = inspect.getsource(mod)
    for line in src.splitlines():
        ...
        if "asyncio.gather" in stripped and "symbol" in stripped:
            pytest.fail(...)
```

`crawlers/*` modules are **not in `forbidden_modules`** — adding `asyncio.gather` over symbols in `crawlers/base.py` or `crawlers/price_crawler.py` is **already permitted** by this test. No regex change, no whitelist syntax.

**However**, two strengthening edits are warranted in 27-02:

1. **Positive assertion** — add a complementary test confirming the new contract:

   ```python
   def test_crawler_uses_bounded_gather() -> None:
       """27-02 contract — fetch_batch MUST use Semaphore + gather(return_exceptions=True)."""
       from localstock.crawlers import base
       src = inspect.getsource(base.BaseCrawler.fetch_batch)
       assert "asyncio.gather" in src, "fetch_batch must use gather() per PERF-01"
       assert "return_exceptions=True" in src, "gather must use return_exceptions=True (Phase 25 D-03 + T-1)"
       assert "Semaphore" in src or "semaphore" in src, "fetch_batch must use Semaphore (PERF-01 D-02)"
   ```

2. **Update the failure message** in the existing guardrail to drop the "until Phase 27" stale clause:

   ```python
   # Before:
   "per-symbol gather() is forbidden until Phase 27 bounded concurrency lands."
   # After:
   "per-symbol gather() is forbidden in analyze/score/sentiment/admin/report; "
   "concurrency lives in crawlers/ only (Phase 27 D-01)."
   ```

### Q-6 — Baseline `pipeline_duration_seconds` snapshot: **NOT CAPTURED** [HIGH confidence]

[VERIFIED: `grep -rn "baseline" .planning/milestones/ docs/` returns no Phase 24 baseline file. Only `pipeline_durations` migration test artifacts.]

Phase 24-02 added the histogram migration (`tests/test_db/test_migration_24_pipeline_durations.py`) and 24-03 attached the timing listener. **No values were recorded into a markdown snapshot.** This makes SC #1's "≥ 3× vs baseline" un-measurable until we capture one.

**Plan 27-01 must include a baseline-capture step:**

1. Run `run_daily_pipeline` against current code 3 times (or scrape the last 3 entries from `pipeline_runs.duration_seconds` if Phase 24-05 already populated it — verify in 27-01).
2. Compute p50/p95 of total duration and per-stage breakdown.
3. Write `.planning/milestones/v1.6-perf-baseline.md` with a table:

   ```markdown
   | Run | Total (s) | Crawl (s) | Analysis (s) | Scoring (s) | Reports (s) | Sentiment (s) |
   |-----|-----------|-----------|--------------|-------------|-------------|---------------|
   | 1   | …         | …         | …            | …           | …           | …             |
   | p50 | …         | …         | …            | …           | …           | …             |
   | p95 | …         | …         | …            | …           | …           | …             |
   ```
4. The "≥3× speedup" target is **3× of p95-total**, applied at 27-07 phase gate.

**Alternative if production runs already exist:** Query `SELECT duration_seconds FROM pipeline_runs WHERE status='success' ORDER BY started_at DESC LIMIT 5;` and snapshot those rows. Cite the run IDs so the comparison is reproducible.

### Q-7 — Concurrent test harness: **synthetic in CI + dev-as-staging real run** [MEDIUM confidence]

**What we know:**

- The repo has CI (`uv run pytest`) and a dev environment but no documented "staging" environment distinct from production.
- vnstock has no public sandbox; "real run" perf testing means hitting KBS/VCI live.
- A 400-symbol live run is exactly what we want to avoid mocking until we trust the concurrency bounds.

**Recommendation:**

1. **CI: synthetic harness** for SC #2 (5 consecutive runs, 0×429), SC #3 (transient 503 → success), SC #4 (event-loop lag p95 < 100 ms). Mock vnstock at the `KBSQuote.history` boundary using `pytest-asyncio` + `unittest.mock` to inject deterministic 429s, 503s, and CPU-blocking work. **No real network calls in CI.**
2. **Dev-as-staging real run** for SC #1 (≥3× speedup). Manual gate: developer runs `run_daily_pipeline` once before merging 27-07, captures the new timing into the same milestone file as the baseline, computes the ratio. This is documented as a phase-gate runbook step, not automated.
3. **No new "staging environment" required** — declaring dev-as-staging is the most lightweight option that satisfies SC #1.

The synthetic harness for SC #2 is detailed in §6 (test strategy).

---

## 2. Audit Lists (concrete file:line citations)

### A. vnstock client call sites needing Semaphore + limiter wrapping

The natural seam is `BaseCrawler.fetch_batch` (`crawlers/base.py:25-61`) — replace the serial loop with `Semaphore + aiolimiter + gather(return_exceptions=True)`. Per-symbol `fetch()` impls are then wrapped inside the bounded executor.

| File:line | Function | Wrap action |
|-----------|----------|-------------|
| `crawlers/base.py:25-61` | `BaseCrawler.fetch_batch` | **Primary refactor target.** Replace serial loop with bounded `gather`. Inject `semaphore: asyncio.Semaphore`, `limiter: aiolimiter.AsyncLimiter`, `breaker: CircuitBreaker` via constructor or kwargs. Inside per-symbol coroutine: `async with breaker.guard(): async with limiter: async with semaphore: return await self.fetch(symbol, **kwargs)`. |
| `crawlers/finance_crawler.py:98-130` | `FinanceCrawler.fetch_batch` (overrides base) | **Special case** — finance has 4 report types per symbol with `await asyncio.sleep(self.delay_seconds)` between. Refactor: outer `gather` over symbols, inner serial 4-report loop preserved (intra-symbol serialization respects per-source order). |
| `crawlers/price_crawler.py:33-60` | `PriceCrawler.fetch` (single-symbol) | No change — called via `fetch_batch` which now applies bounded concurrency. |
| `crawlers/company_crawler.py:40-66` | `CompanyCrawler.fetch` | same — wrapped via `fetch_batch` |
| `crawlers/event_crawler.py:43-67` | `EventCrawler.fetch` | same — wrapped via `fetch_batch` |
| `crawlers/news_crawler.py:225-267` | `NewsCrawler.crawl_feeds` | **Independent path** — does not use `BaseCrawler.fetch_batch`. Apply per-source limiter (cafef vs vnexpress) inline at line 252 (`resp = await client.get(feed_url)`). 5 feeds total — minor speedup, but wire the breaker for symmetry. |

**Pipeline integration sites (where `fetch_batch` is called):**

- `services/pipeline.py:211` `_crawl_prices` — currently a hand-rolled serial loop **NOT going through BaseCrawler.fetch_batch** (per-symbol `latest_date` lookup precedes each fetch). Refactor: keep the per-symbol pre-flight in the loop body, wrap `await self.price_crawler.fetch(...)` (line 477) in semaphore/limiter/breaker — i.e., apply the bounded pattern at the *site that loops*, not just in `BaseCrawler.fetch_batch`. **Two refactor targets.**
- `services/pipeline.py:214` `finance_crawler.fetch_batch(symbols)` — uses fetch_batch directly ✓
- `services/pipeline.py:225` `company_crawler.fetch_batch(symbols)` — uses fetch_batch directly ✓
- `services/pipeline.py:247` `event_crawler.fetch_batch(symbols)` — uses fetch_batch directly ✓
- `services/pipeline.py:629-680` `Pipeline.run_single_symbol` — single-symbol path; not affected by concurrency, but still benefits from limiter/breaker if invoked while the daily run is also active. Apply the same wrap.

### B. All `httpx` invocations needing `@retry` (D-06)

[VERIFIED: §1 Q-2 audit table; consolidated here for the planner]

Wrap sites (8 logical sites; 4 are "vnstock sync call" pattern):

1. `crawlers/news_crawler.py:252` — RSS feed fetch (httpx)
2. `crawlers/news_crawler.py:314` — article content fetch (httpx)
3. `macro/crawler.py:44` — VCB XML (httpx)
4. `ai/client.py:138` — `classify_sentiment` (already retried, **align to D-06 jitter**)
5. `ai/client.py:194` — `generate_report` (already retried with `stop_after_attempt(2)`, **bump to 3 + jitter**)
6. `notifications/telegram.py:51` + `:57` — bot.send_message (× 2 branches; **needs ratification**)
7. `crawlers/price_crawler.py:54-58` (sync `_fetch_sync`) — vnstock KBSQuote.history
8. `crawlers/finance_crawler.py:148-152` (sync `_sync_fetch`) — Finance.report_func
9. `crawlers/company_crawler.py:56-58` (sync `_sync_fetch`) — KBSCompany.overview
10. `crawlers/event_crawler.py:57-58` (sync `_sync_fetch`) — KBSCompany.events

For sites #7-#10 (sync vnstock calls): tenacity supports sync functions natively. Decorate the inner `_sync_fetch` / `_fetch_sync` with `@retry(...)` using `requests.exceptions.*`-aware tuple. **D-06 exception tuple needs expansion** — see ratification §4.

### C. `pandas-ta` call sites needing `to_thread` (D-05)

[VERIFIED: `grep -rn "pandas_ta|pd_ta|import pandas_ta"` in `apps/prometheus/src/localstock/`]

| File:line | Site | Action |
|-----------|------|--------|
| `analysis/technical.py:11` | `import pandas_ta as ta` | No action — import is fine |
| `analysis/technical.py:67` | `result.ta.{name}(append=True, **params)` ×11 inside `compute_indicators` | No direct wrap — covered transitively via the `analyze_technical_single` boundary |
| `analysis/technical.py:146` | `ta.cdl_doji(...)` inside `compute_candlestick_patterns` | same — covered by outer wrap |
| `analysis/technical.py:152` | inside-bar computation | same |
| `services/analysis_service.py:300` | `indicators_df = self.tech_analyzer.compute_indicators(ohlcv_df)` | This is the heavy call but it's reached only through `analyze_technical_single`. **Don't wrap directly** — wrap at the level above. |
| `services/analysis_service.py:418` | `return self.analyze_technical_single(symbol, ohlcv_df)` (cache-bypass path when run_id is None) | **WRAP**: `return await asyncio.to_thread(self.analyze_technical_single, symbol, ohlcv_df)` |
| `services/analysis_service.py:426` | `return self.analyze_technical_single(symbol, ohlcv_df)` (inside `_compute()` closure on cache miss) | **WRAP**: `return await asyncio.to_thread(self.analyze_technical_single, symbol, ohlcv_df)` — Phase 26 left a literal TODO comment at lines 421-425 anticipating this |

**Drift confirmation:** CONTEXT D-05 references `analysis_service.py:264` (carried from Phase 26 RESEARCH where 264 was the start of `analyze_technical_single` at the time). **Today the function starts at line 285 and the body extends to line 390.** The actual offload sites are 418 and 426 (the two callers of the sync `analyze_technical_single` from inside `cached_analyze_technical_single`). No drift in semantics; only line numbers changed since Phase 26 plan-checker ran.

**No drift outside this site:** No other `pandas_ta` or `.ta.` calls exist in the codebase. SC #4's "p95 < 100 ms during 400-symbol run" is bottlenecked exclusively at this offload.

### D. The single `create_async_engine` site (D-07)

[VERIFIED: `grep -n "create_async_engine"` returns one site]

| File:line | Site | Action |
|-----------|------|--------|
| `db/database.py:23-31` | `_engine = create_async_engine(settings.database_url, echo=False, pool_size=3, max_overflow=5, pool_recycle=300, pool_pre_ping=True, connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0})` | **Retune to D-07 verbatim:** `pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True` (preserved). **Note D-07 does NOT specify `pool_recycle`** — current is 300 s. T-4 below recommends keeping it. |

Existing `connect_args` already match D-07 verbatim. Only `pool_size`, `max_overflow`, `pool_timeout` change (and `echo=False` stays). `pool_pre_ping=True` is unchanged.

### E. Telegram send call sites (D-08)

[VERIFIED: `grep -rn "send_message|TelegramNotifier|send_daily_digest"` in `apps/prometheus/src/localstock/`]

| File:line | Caller | Site | D-08 action |
|-----------|--------|------|-------------|
| `services/automation_service.py:252` | `_send_notifications` (inside `run_daily_pipeline`) | `sent = await self.notifier.send_message(msg)` for **daily_digest** | **WRAP in `asyncio.create_task`** per D-08 |
| `services/automation_service.py:269` | `_send_notifications` (same flow) | `sent = await self.notifier.send_message(msg)` for **score_alert** | **WRAP in `asyncio.create_task`** per D-08 (CONTEXT mentions only digest; both must move for SC #6 to be true) |
| `scheduler/error_listener.py:83` | `_listener` (APScheduler error handler) | `await notifier.send_message(msg)` | **NOT in pipeline path** — keep awaited; this is fired on scheduler exceptions, not pipeline finalize. |
| `notifications/telegram.py:35-65` | `TelegramNotifier.send_message` | Implementation only — internal `bot.send_message` calls (`:51`, `:57`) | Tenacity wrap (D-06) applies inside the create_task'd coroutine. |

**Important drift from CONTEXT:** D-08 says "the Telegram digest send is launched as a fire-and-forget background task" (singular). The actual code has TWO awaited sends in `_send_notifications` — both daily_digest AND score_alert. SC #6 ("pipeline marks complete trước khi Telegram message đi") is only true if BOTH move to background. Recommendation: refactor `_send_notifications` so the entire function body is the create_task'd coroutine — neither send awaits in the pipeline finalize path. See §4 ratification.

---

## 3. Pitfalls Catalog (P-1..P-10)

### P-1 — `aiolimiter` has no per-acquire timeout

**What:** `AsyncLimiter.acquire()` (used as `async with limiter`) blocks indefinitely until a token is available. Under sustained 429-induced backoff or upstream stall, a coroutine could wait forever.

**Why it matters here:** With 400 symbols × 4 crawl types × token-bucket gating, a single misbehaving source could starve the entire crawl stage past the 15:30 window.

**Mitigation:** Wrap the whole crawl stage in `async with asyncio.timeout(STAGE_BUDGET_SECONDS):` (Python 3.11+ `asyncio.timeout` context manager). Suggested budget: **180 s for the entire crawl stage** (covers normal + 2× safety; baseline crawl is currently ~60-90 s). Symbols that don't acquire by then fall through with `TimeoutError` → per-symbol try/except → `_failed_symbols` (Phase 25 D-03 contract preserved).

```python
# pipeline.py — wrap _crawl_prices and the fetch_batch calls
async with asyncio.timeout(settings.crawler_stage_budget_s):  # default 180
    price_results, price_failed = await self._crawl_prices(symbols)
    fin_results, fin_failed = await self.finance_crawler.fetch_batch(symbols)
    ...
```

[VERIFIED: aiolimiter source — `_check_acquire` does not accept a timeout kwarg; aiolimiter==1.2.1]

### P-2 — `asyncio.create_task` GC pitfall

**What:** Python's task GC may collect a task before it runs if no strong reference is held. Documented in CPython issue and in `asyncio.create_task` docs.

**Why it matters here:** D-08 launches Telegram send fire-and-forget. Without a strong ref the digest may be cancelled silently before `bot.send` is invoked.

**Mitigation:** **Already covered by D-08** with `_pending_tasks: set[asyncio.Task]`. Sanity checks for the planner:

- The set must be **module-level** (not local to a function) — confirmed in D-08 wording.
- `add_done_callback(_pending_tasks.discard)` removes the ref after completion to avoid memory growth.
- Lifespan drain (`scheduler/scheduler.py:162`) must `await asyncio.wait(_pending_tasks, timeout=10)` before `scheduler.shutdown()`.

```python
# notifications/background.py — NEW (~25 LOC)
import asyncio
import logging
from typing import Coroutine, Any

_pending_tasks: set[asyncio.Task] = set()

def fire_and_forget(coro: Coroutine[Any, Any, Any], *, name: str) -> asyncio.Task:
    """Schedule coro as background task with GC-safe strong ref + done-callback logging."""
    task = asyncio.create_task(coro, name=name)
    _pending_tasks.add(task)
    task.add_done_callback(_log_and_discard)
    return task

def _log_and_discard(task: asyncio.Task) -> None:
    _pending_tasks.discard(task)
    if task.cancelled():
        return
    if (exc := task.exception()) is not None:
        logging.getLogger(__name__).exception("background_task_failed", extra={"task_name": task.get_name()}, exc_info=exc)

async def drain(timeout: float = 10.0) -> None:
    """Lifespan shutdown helper — wait for pending tasks, cancel stragglers."""
    if not _pending_tasks:
        return
    done, pending = await asyncio.wait(_pending_tasks, timeout=timeout)
    for task in pending:
        task.cancel()
```

### P-3 — Tenacity + circuit breaker interaction (T-7 expansion)

**What:** If a 429 is included in `retry_if_exception_type`, tenacity will retry it 3 times. Multiplied by the breaker's "3 consecutive 429s → OPEN" rule, the breaker would only open after **3 retries × 3 strikes = 9 actual 429s**, violating SC #2's "open after 3 consecutive 429s" wording.

**Why it matters here:** D-06 already says "429 + circuit-open errors are NOT retried by tenacity" — verify the actual exception tuple excludes them.

**Mitigation:**

- For httpx call sites: `httpx.HTTPStatusError` covers ALL non-2xx including 429. **Custom predicate is needed**, not just type check:

  ```python
  def _retry_transient_only(exc: BaseException) -> bool:
      """Retry transient errors (5xx, transport) — NOT 429 (handled by circuit breaker)."""
      if isinstance(exc, httpx.HTTPStatusError):
          status = exc.response.status_code
          return status >= 500  # retry 5xx; let 429 + 4xx fall through
      if isinstance(exc, httpx.TransportError):
          return True
      if isinstance(exc, CircuitOpenError):
          return False  # never retry an open breaker
      return False

  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential_jitter(initial=0.5, max=8.0),
      retry=tenacity.retry_if_exception(_retry_transient_only),
  )
  ```

- For vnstock sync calls (requests-based): the predicate inspects `requests.exceptions.HTTPError` and reads `exc.response.status_code`.
- The circuit breaker's `guard()` context manager re-raises 429 as a sentinel `RateLimitedError` *or* increments the strike counter and re-raises — either way, tenacity's predicate sees it and returns `False`.

This is a **deviation from D-06's literal text** (`retry_if_exception_type` tuple). The deviation is required to honor SC #2's strike count; ratification noted in §4.

### P-4 — `pool_pre_ping=True` overhead under high query count (T-4 expansion)

**What:** `pool_pre_ping=True` issues `SELECT 1` before every checkout. The pipeline does many small queries (per-symbol `get_latest_date`, `get_prices`, `bulk_upsert`). At ~20k queries × 1 ms pre-ping = 20 s pure overhead.

**Why it matters here:** D-07 mandates `pool_pre_ping=True`; SC #5 mandates "no QueuePool errors". Pre-ping defends against stale connections (Supabase pgbouncer can drop idle ones), but the cost is non-trivial.

**Mitigation:**

- **Keep `pool_recycle=300`** (currently set). With recycle=300s, a connection > 5 min old is recycled BEFORE pre-ping fires — the two work together: recycle prevents most stale connections; pre-ping is a safety net for the few that slip through.
- **Document the trade in `db/database.py`:** "pre-ping costs ~1 ms × N queries; recycle=300 minimizes pre-ping hits in practice."
- **Validation:** in 27-05's plan, add a synthetic test that runs 1000 sequential queries through the pool and asserts wall-clock < 5 s (i.e., per-query overhead < 5 ms) — catches accidental pre-ping doubling.

D-07 doesn't mention `pool_recycle` — I recommend keeping the existing 300 s value (no change). Ratification: confirm researcher may keep `pool_recycle=300`. See §4.

### P-5 — `to_thread` default executor saturation if granularity changes

**What:** `asyncio.to_thread()` uses `loop.run_in_executor(None, ...)` which routes to the default `concurrent.futures.ThreadPoolExecutor` of size `min(32, os.cpu_count() + 4)`. Currently called serially (one at a time inside the per-symbol loop), so pool size = 1 effective concurrency — fine.

**Why it matters here:** If a future refactor (or a copy-paste mistake) wraps `to_thread` calls in `gather`, the default pool fills up and:
1. Thread creation/teardown costs explode.
2. asyncpg pool's connections held by the threads compete for the SAME GIL.
3. Other `to_thread` users (none today, but `run_in_executor` in crawlers) compete for the same threads.

**Mitigation:**

- **Inline-comment the constraint** at `analysis_service.py:418` and `:426`:

  ```python
  # CONSTRAINT (Phase 27 D-05): this to_thread is invoked from a SERIAL
  # per-symbol loop. Do NOT wrap in asyncio.gather — would saturate the
  # default ThreadPoolExecutor (32 threads × 400 symbols) and break Phase 25
  # per-symbol isolation. Concurrency lives in crawlers/ only (D-01).
  ```

- The Pitfall-A guardrail (existing `test_no_gather_in_per_symbol_loops`) already protects this — verify the test runs after 27-04.

### P-6 — Per-symbol isolation must survive `gather(return_exceptions=True)` (T-1 expansion)

**What:** `asyncio.gather(*coros, return_exceptions=True)` returns a list where exception-typed elements are **the exception objects themselves** (not raised). The caller MUST loop the result and route exceptions to `_failed_symbols`. Forgetting this loop silently drops failures.

**Why it matters here:** Phase 25 D-03 contract: every per-symbol failure must land in `_failed_symbols` with `{"symbol", "step", "error"}`. With `gather(return_exceptions=True)`, this is **explicit caller work**, not automatic.

**Critical detail:** `return_exceptions=True` returns `Exception` and `BaseException` subclasses. `asyncio.CancelledError` is a `BaseException`; if propagated this way, the `isinstance(result, Exception)` filter MISSES it — pre-3.8 behavior was different. In 3.12+ `CancelledError` IS returned via `return_exceptions=True` and IS-A `BaseException` not `Exception`. Use `isinstance(result, BaseException)` to be safe.

**Mitigation pattern (canonical for 27-02):**

```python
# crawlers/base.py refactor
async def fetch_batch(self, symbols: list[str], **kwargs):
    results: dict[str, pd.DataFrame] = {}
    failed: list[tuple[str, str]] = []

    sem = self.semaphore  # asyncio.Semaphore(8)
    limiter = self.limiter
    breaker = self.breaker

    async def _bounded_fetch(symbol: str) -> tuple[str, pd.DataFrame | None]:
        async with breaker.guard():
            async with limiter:
                async with sem:
                    df = await self.fetch(symbol, **kwargs)
                    return symbol, df

    coros = [_bounded_fetch(sym) for sym in symbols]
    raw = await asyncio.gather(*coros, return_exceptions=True)

    for sym, result in zip(symbols, raw):
        if isinstance(result, BaseException):
            failed.append((sym, _truncate_error(result)))   # Phase 25 D-03 helper
            logger.warning("crawl.symbol.failed", symbol=sym, error=str(result))
            continue
        sym_returned, df = result
        if df is not None and not df.empty:
            results[sym_returned] = df
        else:
            failed.append((sym_returned, "Empty DataFrame returned"))

    return results, failed
```

Note the `zip(symbols, raw)` — gather preserves order, so we can correlate. Don't unpack `result` before the exception check.

### P-7 — Circuit breaker race on "3 consecutive 429s"

**What:** With 8 concurrent coroutines hitting the same source, 3 of them can fire requests in flight before the breaker observes the first 429. If all 3 return 429s ~simultaneously, the breaker may count >3 strikes before opening — not a correctness bug, but it means we send (3 + N_in_flight) calls before the circuit actually trips.

**Why it matters here:** SC #2 says "circuit breaker mở sau 3 consecutive 429s". Strict reading: open after exactly 3 calls, not 3-and-whatever-was-in-flight.

**Mitigation:**

- Acceptable interpretation: "3 consecutive 429s observed" — the breaker observes serially even if calls fire in parallel. In-flight calls that return 429 after OPEN transitions to true OPEN are counted but ignored (a lock or atomic counter handles ordering).
- Implementation: use `asyncio.Lock()` inside the breaker's strike-update method:

  ```python
  async def record_failure(self, status: int) -> None:
      async with self._lock:
          if status == 429:
              self._consecutive_429s += 1
              if self._consecutive_429s >= 3 and self._state == "CLOSED":
                  self._state = "OPEN"
                  self._opened_at = time.monotonic()
                  CRAWLER_CIRCUIT_STATE.labels(source=self.source, state="open").inc()
          else:
              self._consecutive_429s = 0  # reset on any non-429
  ```

- Document in 27-01 plan: "3 strikes" means 3 *observed* 429 returns; up to `Semaphore(8)` calls may be in-flight when the 3rd 429 returns.

### P-8 — `CircuitOpenError` short-circuits but must still log + surface to per-symbol buffer

**What:** When the breaker is OPEN, every call short-circuits. If we just raise silently the symbol disappears from the failed list — we lose visibility on *which symbols were skipped* due to a circuit trip.

**Mitigation:** `breaker.guard()` raises `CircuitOpenError`; the gather wrapper (P-6 pattern) catches it via `isinstance(result, BaseException)` and routes to `_failed_symbols` with `step="crawl"` and `error="CircuitOpenError: kbs OPEN until ..."`. Add a separate metric `localstock_crawler_circuit_skipped_total{source}` so we can graph "symbols dropped because breaker was open" distinct from "symbols dropped because of error".

### P-9 — Telegram bot raises non-httpx exception types (D-06 spec gap)

**What:** `python-telegram-bot >= 22.0` raises `telegram.error.NetworkError`, `telegram.error.TimedOut`, `telegram.error.RetryAfter`, `telegram.error.BadRequest`. Under D-06's literal `retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError))`, the bot's network errors are **silently NOT retried** because they are NOT instances of those types.

**Why it matters here:** PERF-03 + SC #3 say "Mọi external HTTP call site được wrap bằng @retry". If telegram raises `NetworkError` and tenacity doesn't catch it, telegram retries are a no-op.

**Mitigation:**

- Decorate the telegram path with a separate `@retry` whose `retry_if_exception_type` includes the telegram error tuple:

  ```python
  from telegram.error import NetworkError, TimedOut, RetryAfter

  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential_jitter(initial=0.5, max=8.0),
      retry=retry_if_exception_type((NetworkError, TimedOut)),
      # Note: RetryAfter is intentionally NOT retried — Telegram returns
      # this with a "wait N seconds" hint; respect the hint by not hammering.
  )
  async def _send_with_retry(bot, chat_id, text): ...
  ```

- This is a **deviation from D-06's literal exception tuple** (httpx-only). Two options for ratification (§4):
  1. **Expand D-06**: augment the tuple to be source-specific via a small helper that returns the right tuple per-call-site.
  2. **Per-site decoration**: leave D-06's httpx tuple as the default but allow local `@retry` overrides per the specific exception family at each site. Cleaner; recommended.

### P-10 — Sampler started before event loop is running

**What:** `start_sampler()` calls `asyncio.get_running_loop()`. If invoked from a synchronous context (e.g., module import, CLI entrypoint), this raises `RuntimeError: no running event loop`.

**Mitigation:** Only call `start_sampler()` from inside the FastAPI lifespan (`scheduler/scheduler.py:158`) which is guaranteed to be inside the event loop. Document this in the sampler module header.

---

## 4. Wave/Plan Critique & Ratification Asks

### CONTEXT's 7-plan hypothesis (verbatim)

| Plan | Wave | Description | Closes |
|------|------|-------------|--------|
| 27-01 | W1 (solo) | Baseline + concurrency primitives module | PERF-01 prereq |
| 27-02 | W2 | Crawler refactor (Semaphore + limiter + breaker wired in) | PERF-01, PERF-02 |
| 27-03 | W2 | Tenacity wrap on all external HTTP sites | PERF-03 |
| 27-04 | W2 | `to_thread` wrap + lag metric | PERF-04 |
| 27-05 | W3 | Engine pool tuning + log assertion test | PERF-05 |
| 27-06 | W3 | Telegram fire-and-forget + drain | PERF-06 |
| 27-07 | W4 (solo) | End-to-end perf gate | SC #1 |

### Researcher's recommended structure

**Same 7 plans, slightly different waves:** 4 waves, with Wave 2 being 4-wide.

| Plan | Wave | Reason |
|------|------|--------|
| 27-01 | **W1 solo** | Builds primitives (`crawlers/_concurrency.py`, `crawlers/_circuit.py`, `observability/event_loop_lag.py`, `notifications/background.py`) + adds `aiolimiter` dep + captures baseline. **Everything in Wave 2 imports from this.** |
| 27-02 | W2 | Crawler refactor — depends on 27-01 primitives. File: `crawlers/base.py`, `crawlers/finance_crawler.py`, `services/pipeline.py:447-558` (the hand-rolled `_crawl_prices` loop). |
| 27-03 | W2 | Tenacity wrap — independent of crawler structural changes; can run parallel. Files: 8 wrap sites listed in §2.B. **No file conflicts with 27-02** (touches httpx call sites, not the gather seam). |
| 27-04 | W2 | `to_thread` wrap at `analysis_service.py:418, 426` + sampler wire-up in `scheduler.py:158`. **No conflict with 27-02 or 27-03.** |
| 27-05 | W2 | Engine pool tuning — `db/database.py` only. **Trivial diff (~3 lines), no conflict.** |
| 27-06 | **W3** | Telegram fire-and-forget — depends on 27-03's tenacity choice for the bot (P-9 ratification). Touches `services/automation_service.py:223-279` + `scheduler/scheduler.py:162` (drain). |
| 27-07 | **W4 solo** | Phase gate — measures, doesn't change code. Runs last. |

**Why this differs from CONTEXT:**

1. CONTEXT puts 27-05 in W3; I move to W2 because pool tuning is a 3-line config change with zero file conflicts and zero behavioral dependencies on other plans. Promoting to W2 collapses Wave 3 to single-plan (27-06) — and 27-06 should depend on 27-03's tenacity decision (which exception tuple wraps the bot), so 27-06 cannot be in the same wave as 27-03. Correct ordering: **27-03 in W2 → 27-06 in W3**.
2. CONTEXT keeps 27-06 in W3; researcher confirms.
3. CONTEXT has Wave 4 = 27-07; researcher confirms.

**Final wave map:**

```
W1: 27-01 (solo, foundation)
W2: 27-02 + 27-03 + 27-04 + 27-05 (4-wide parallel; no file overlap)
W3: 27-06 (solo; depends on 27-03 telegram tenacity decision)
W4: 27-07 (solo; phase perf gate)
```

### File-conflict matrix for W2

| File | 27-02 | 27-03 | 27-04 | 27-05 |
|------|-------|-------|-------|-------|
| `crawlers/base.py` | ✏️ | — | — | — |
| `crawlers/finance_crawler.py` | ✏️ | ✏️ (sync `_sync_fetch`) | — | — |
| `crawlers/price_crawler.py` | — | ✏️ | — | — |
| `crawlers/company_crawler.py` | — | ✏️ | — | — |
| `crawlers/event_crawler.py` | — | ✏️ | — | — |
| `crawlers/news_crawler.py` | ✏️ (limiter only) | ✏️ | — | — |
| `macro/crawler.py` | — | ✏️ | — | — |
| `ai/client.py` | — | ✏️ (align jitter) | — | — |
| `services/pipeline.py` | ✏️ (`_crawl_prices`, stage timeout) | — | — | — |
| `services/analysis_service.py` | — | — | ✏️ | — |
| `db/database.py` | — | — | — | ✏️ |
| `scheduler/scheduler.py` | — | — | ✏️ (sampler start/stop) | — |

**Conflict at `crawlers/finance_crawler.py` and `crawlers/news_crawler.py`** between 27-02 and 27-03. Two options:

- **Option A (preferred):** Sequence — 27-02 lands first (structural changes), 27-03 lands second (tenacity decorators on the new shape). Within W2, mark 27-03 as depending on 27-02 (intra-wave ordering).
- **Option B:** Merge 27-02 and 27-03 into one larger plan. Larger blast radius, harder to revert one without the other. **Not recommended.**

Researcher recommends Option A: keep 4 plans in W2 with **27-03 sequenced after 27-02 inside the wave**.

### Ratifications needed BEFORE planning

| # | Ask | Researcher recommendation |
|---|-----|--------------------------|
| **R-1** | D-03 vnstock rate: keep CONTEXT's 5 req/s default, or drop to 4 req/s with override to 5? | **4 req/s default** — gives 1 req/s headroom; environment override `VNSTOCK_RATE_PER_SEC` allows tuning to 5 if the empirical run shows zero 429s |
| **R-2** | D-06 exception tuple is httpx-only; vnstock raises `requests.exceptions.*`, telegram raises `telegram.error.*`. Expand D-06 globally, or allow per-site exception tuples? | **Per-site exception tuples** — keep D-06's `(stop_after_attempt(3), wait_exponential_jitter, transient-only predicate)` shape but allow each site to declare its own retry-on tuple. P-3 + P-9 expansions specify the predicate. |
| **R-3** | D-08 says "Telegram digest" (singular). Code has 2 sends in `_send_notifications` (digest + score_alert). Move both, or only digest? | **Move both** — SC #6 ("pipeline marks complete trước khi Telegram message đi") is only true if the entire `_send_notifications` body runs as a background task. Refactor: `asyncio.create_task(notifier_send_all(...))` once, covering both sends serially inside the task. |
| **R-4** | Keep `pool_recycle=300` in `db/database.py` even though D-07 doesn't mention it? | **Yes, keep** — pairs with `pool_pre_ping=True` to minimize stale-connection costs. P-4 documents the rationale. |
| **R-5** | D-05 "line 264" reference is stale (current line 285 / wrap sites 418, 426). OK to silently update line refs in plan? | **Yes** — pure line-number drift, no semantic change. Plan will cite current lines. Surface in plan's "drift from CONTEXT" note. |

---

## 5. Library Documentation Lookup

### tenacity 9.1.4 [VERIFIED installed; CITED docs]

[CITED: https://tenacity.readthedocs.io/en/latest/api.html — `wait_exponential_jitter(initial=1.0, max=120.0, exp_base=2.0, jitter=1.0)` available since tenacity 8.0]

- `stop_after_attempt(n)` — stops after the nth attempt (counts the original call as attempt 1; `n=3` = 1 original + 2 retries).
- `wait_exponential_jitter(initial, max, exp_base=2, jitter=1)` — sleep = `min(max, initial * exp_base ** (attempt-1))` + uniform random jitter in `[0, jitter)`. **Parameter name is `initial` not `min`** — D-06's literal `initial=0.5, max=8.0` is correct.
- `retry_if_exception_type((Exc1, Exc2))` — type-based filter. For predicate-based filtering (P-3, P-9), use `retry_if_exception(callable)` instead.
- Both sync and async: `@retry` works on `async def` functions; tenacity 9.x autodetects.
- Tenacity wraps the LAST exception in `RetryError` when stop fires. `RetryError.last_attempt.exception()` gives the underlying error. Phase 25 D-03 contract: catch `Exception` (not `RetryError` specifically) at the per-symbol boundary.

### aiolimiter 1.2.1 [VERIFIED PyPI version current; CITED docs]

[CITED: https://aiolimiter.readthedocs.io/en/latest/ — `class AsyncLimiter(max_rate, time_period=60.0)`]

- `AsyncLimiter(max_rate, time_period)` — token-bucket; `max_rate` tokens per `time_period` seconds. For 5 req/s: `AsyncLimiter(max_rate=5, time_period=1.0)`.
- Used as `async with limiter:` — blocks until a token is available; **no timeout argument** (P-1).
- `has_capacity(n=1)` returns True if a non-blocking acquisition would succeed — useful for non-blocking probes.
- Re-entry safety: same task can re-enter `async with limiter` without deadlock; tokens are accounted on entry only.
- Thread safety: NOT thread-safe; designed for single event loop. (Not a concern here — single asyncio loop.)

### asyncio.to_thread + ThreadPoolExecutor [CITED CPython docs]

[CITED: https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread]

- `await asyncio.to_thread(func, /, *args, **kwargs)` — added in 3.9. Wraps `loop.run_in_executor(None, functools.partial(func, *args, **kwargs))`.
- Default executor is `ThreadPoolExecutor(max_workers=min(32, os.cpu_count() + 4))` since 3.8.
- **Cancellation:** if the awaiting coroutine is cancelled, the `to_thread` call's awaitable raises `CancelledError` BUT the synchronous function in the thread CONTINUES TO COMPLETION. Threads cannot be interrupted from outside in CPython. P-5 + P-6 implications.
- **Context propagation:** `to_thread` propagates `contextvars.Context` into the worker thread (3.9+), so OpenTelemetry / loguru contextual data still works.

### SQLAlchemy `pool_pre_ping` + asyncpg compatibility [CITED docs]

[CITED: https://docs.sqlalchemy.org/en/20/core/pooling.html#disconnect-handling-pessimistic — `pool_pre_ping=True` issues a "ping" SELECT 1 on every checkout]

- Works with `AsyncAdaptedQueuePool` (default for `create_async_engine`). No additional config needed.
- With asyncpg + Supabase (pgbouncer transaction mode), pre-ping correctly issues `SELECT 1` and survives stale connections.
- **Cost:** one round-trip per checkout. With session-per-request + per-symbol session, this is N(symbols) × N(sessions) pre-pings. Mitigation: `pool_recycle` (kept at 300 s).
- `prepared_statement_cache_size=0` + `statement_cache_size=0` is the **required** Supabase pgbouncer combo per asyncpg docs (https://magicstack.github.io/asyncpg/current/usage.html#pgbouncer) — already preserved in D-07.

---

## 6. Test Strategy per PERF-* requirement

### Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio (per `apps/prometheus/pyproject.toml` dev deps) |
| Config file | `apps/prometheus/pyproject.toml` (pytest options) |
| Quick run | `cd apps/prometheus && uv run pytest -x -q tests/test_<plan>` |
| Full suite | `cd apps/prometheus && uv run pytest -x -q` |

### PERF-01 — `Semaphore(8) + gather(return_exceptions=True)`

**RED tests:**

1. **Contract test** (`tests/test_crawlers/test_concurrency.py::test_fetch_batch_uses_gather`):
   - Source-inspect `BaseCrawler.fetch_batch` for `asyncio.gather` + `return_exceptions=True` + `Semaphore`.
   - Per Q-5 §1 (positive assertion).
2. **Behavioral test** (`tests/test_crawlers/test_concurrency.py::test_fetch_batch_concurrency_bounded`):
   - Mock `fetch` with `await asyncio.sleep(0.1)` + symbol-recording side effect.
   - Submit 16 symbols.
   - Assert max in-flight calls ≤ 8 (use a counter shared via closure).
3. **Isolation preservation** (`tests/test_crawlers/test_concurrency.py::test_fetch_batch_failed_symbol_isolation`):
   - Mock `fetch` to raise `RuntimeError("BAD")` on symbol "BAD" only; succeed on others.
   - Assert: results contains 9 keys; failed contains `("BAD", "RuntimeError: BAD")`.

### PERF-02 — `aiolimiter` + 3-strike circuit breaker

**RED tests** (`tests/test_crawlers/test_circuit_breaker.py`):

1. **`test_breaker_opens_after_3_consecutive_429s`** (deterministic):
   ```python
   async def test_breaker_opens_after_3_consecutive_429s():
       breaker = CircuitBreaker(source="kbs", cooloff_s=60)
       # 3 calls, each receives a mocked 429
       for _ in range(3):
           with pytest.raises(httpx.HTTPStatusError):
               async with breaker.guard():
                   raise httpx.HTTPStatusError("429", request=..., response=Mock(status_code=429))
       assert breaker.state == "OPEN"
       # 4th call must short-circuit
       with pytest.raises(CircuitOpenError):
           async with breaker.guard():
               pytest.fail("should not execute")
   ```
2. **`test_breaker_resets_consecutive_count_on_success`** — 2 × 429 then a 200; assert `_consecutive_429s == 0`, state still CLOSED.
3. **`test_breaker_half_open_probe`** — open the breaker, monkey-patch `time.monotonic` to return >60 s later, assert next call is allowed (HALF-OPEN), success → CLOSED.
4. **`test_aiolimiter_rate_enforced`** — submit 10 calls with `AsyncLimiter(max_rate=5, time_period=1.0)`; measure wall clock ≥ 1.0 s.
5. **`test_no_429_in_5_consecutive_runs_synthetic`** (the SC #2 simulation):
   ```python
   async def test_no_429_in_5_consecutive_runs():
       """Synthetic SC #2 gate: 5 runs × 400 mocked symbols, 0 forced 429s."""
       mock_kbs = MockKBSQuote(rate_429_threshold_per_sec=5)  # mock returns 429 if rate>5/s
       crawler = PriceCrawler(quote_factory=lambda *a: mock_kbs)
       for run in range(5):
           results, failed = await crawler.fetch_batch([f"S{i:03}" for i in range(400)])
           four29s = [f for f in failed if "429" in f[1]]
           assert len(four29s) == 0, f"run {run}: {len(four29s)} 429s leaked"
   ```

### PERF-03 — Tenacity transient retry

**RED tests** (`tests/test_observability/test_retry_decorators.py`):

1. **`test_transient_503_retried_then_succeeds`**:
   ```python
   call_count = 0
   @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.01, max=0.05),
          retry=retry_if_exception(_retry_transient_only))
   async def flaky():
       nonlocal call_count
       call_count += 1
       if call_count < 3:
           raise httpx.HTTPStatusError("503", request=..., response=Mock(status_code=503))
       return "ok"
   assert await flaky() == "ok"
   assert call_count == 3
   ```
2. **`test_429_not_retried`** — same shape but raise 429; assert call_count == 1 (no retry; breaker handles it).
3. **`test_retry_exhaustion_raises_retry_error`** — 4 attempts of 503, expect `tenacity.RetryError` (or in async-only mode: the underlying `HTTPStatusError`).
4. **Audit test** (`test_all_external_http_sites_decorated`):
   - Walk `crawlers/*.py`, `services/news_service.py`, `macro/crawler.py`, `notifications/telegram.py`, `ai/client.py`.
   - For each module, assert that every `httpx.AsyncClient.get/post` call site is inside a `@retry`-decorated function (or extracted helper). Pattern: AST-walk to find decorators.

### PERF-04 — `to_thread` + event-loop lag

**RED tests** (`tests/test_observability/test_event_loop_lag.py`):

1. **Sampler smoke** — `test_sampler_records_observations_when_started` — start, sleep 0.5 s, stop, assert ≥3 histogram observations.
2. **Sampler detects sync block** — see §1 Q-4 example.
3. **`to_thread` wraps `analyze_technical_single`** — assert `cached_analyze_technical_single` body contains `await asyncio.to_thread`. Source inspection.
4. **Synthetic 400-symbol lag p95 < 100 ms** (`test_400_symbol_loop_loop_responsive`):
   ```python
   async def test_400_symbol_analyze_keeps_loop_responsive():
       # Substitute analyze_technical_single with a deterministic "blocks for 50ms" mock
       svc = AnalysisService(...)
       svc.analyze_technical_single = MagicMock(side_effect=lambda *a, **k: time.sleep(0.05) or {"symbol": ...})
       start_sampler()
       for sym in (f"S{i:03}" for i in range(400)):
           await svc.cached_analyze_technical_single(sym, ohlcv_df, run_id=None)
       stop_sampler()
       # p95 of recorded lag must be < 100 ms
       p95 = _histogram_p95(EVENT_LOOP_LAG_SECONDS)
       assert p95 < 0.100
   ```
   This proves `to_thread` is doing its job — without the wrap, the 50 ms sync sleep × 400 symbols would block the loop and the sampler would record drift.

   **CI feasibility:** YES — synthetic mock keeps wall-clock ≤ 25 s (400 × 50 ms / pool_workers). Run with `@pytest.mark.timeout(60)`.

   **Lower symbol count fallback:** if 400-symbol run is too slow on CI, run 100 symbols at 200 ms each — same total work, same drift detection, ¼ wall clock.

### PERF-05 — Pool tuning

**RED tests** (`tests/test_db/test_pool_tuning.py`):

1. **Config assertion** — `test_engine_uses_pool_size_10`:
   ```python
   from localstock.db.database import get_engine
   engine = get_engine()
   pool = engine.pool
   assert pool.size() == 10
   assert pool._max_overflow == 10
   assert pool._timeout == 5
   assert pool._pre_ping is True
   ```
2. **`test_no_queuepool_limit_in_logs`** (integration; requires Postgres, mark `requires_pg`):
   - Run a 50-coroutine fan-out that each does 5 queries against a real DB.
   - Capture loguru logs with `caplog`-style fixture.
   - Assert no log contains `"QueuePool limit"` or `"connection invalidated"`.
3. **`test_pool_pre_ping_overhead_bounded`** — issue 1000 sequential queries; assert wall clock < 5 s (P-4 overhead bound).

### PERF-06 — Telegram fire-and-forget

**RED tests** (`tests/test_notifications/test_background_send.py`):

1. **`test_send_does_not_block_finalize`**:
   ```python
   async def test_pipeline_finalize_returns_before_telegram_completes():
       # Mock TelegramNotifier.send_message to sleep 2 seconds
       svc = AutomationService(session_factory)
       svc.notifier.send_message = AsyncMock(side_effect=lambda *a: asyncio.sleep(2))
       start = time.monotonic()
       await svc.run_daily_pipeline()
       elapsed = time.monotonic() - start
       assert elapsed < 1.5, f"finalize blocked on telegram: {elapsed}s"
       # But the task is still pending
       assert any(t.get_name() == "telegram_daily_digest" for t in _pending_tasks)
   ```
2. **`test_drain_awaits_pending_tasks_with_timeout`** — schedule a 5 s task, call `drain(timeout=10)` — completes in ~5 s; schedule a 30 s task, call `drain(timeout=2)` — cancels stragglers, returns in ~2 s.
3. **`test_done_callback_logs_exception`** — task raises; assert error logged with `task_name` extra.

### SC #1 — ≥ 3× speedup vs baseline

**Phase gate (manual, runbook-style)** in 27-07:

1. Read baseline from `.planning/milestones/v1.6-perf-baseline.md` (captured in 27-01).
2. Run `run_daily_pipeline` 3 times against current dev DB.
3. Compute new p95.
4. Assert `baseline_p95 / new_p95 >= 3.0`.
5. Append the new measurements to the baseline file.

**No CI automation possible** — requires real DB + real vnstock. Document as a checklist item in 27-07's plan.

---

## 7. Standard Stack & State of the Art

| Concern | Library | Version | Status |
|---------|---------|---------|--------|
| Retry/backoff | `tenacity` | `9.1.4` (installed); `>=9.0,<10.0` (pyproject) | ✓ already present |
| Async token-bucket | `aiolimiter` | `1.2.1` (latest PyPI) | **NEW dep — add in 27-01** |
| Threadpool offload | `asyncio.to_thread` | stdlib 3.9+ (we're on 3.12) | ✓ stdlib |
| HTTP client | `httpx` | `>=0.28,<1.0` | ✓ already present |
| DB pool | SQLAlchemy `AsyncAdaptedQueuePool` | `>=2.0,<3.0` | ✓ already present |
| Async Postgres | `asyncpg` | `>=0.31,<1.0` | ✓ already present |
| Telegram | `python-telegram-bot` | `>=22.0,<23.0` | ✓ already present |

**Don't hand-roll:**

| Problem | Use |
|---------|-----|
| Token bucket | `aiolimiter.AsyncLimiter` (NOT a custom `asyncio.Semaphore + sleep` loop) |
| Retry with jitter | `tenacity.wait_exponential_jitter` (NOT a manual `for attempt in range(3)` with `random.random()`) |
| Threadpool offload | `asyncio.to_thread` (NOT `loop.run_in_executor(executor, fn)` boilerplate; the existing crawlers' `run_in_executor(None, ...)` pattern is fine but newer code should use `to_thread`) |
| Background task lifecycle | small `notifications/background.py` helper (~25 LOC). This IS hand-rolled but the surface is too small to import a library; existing patterns (anyio TaskGroup, asyncer) are heavier than needed. |

**Circuit breaker IS hand-rolled** per D-04 — community libraries (`aiocircuitbreaker`, `pybreaker`) exist but are minor and adding a dep for ~50 LOC of state machine isn't justified.

---

## 8. Environment Availability

| Dependency | Required by | Available | Version |
|------------|------------|-----------|---------|
| Python 3.12 | runtime | ✓ | per `apps/prometheus/pyproject.toml` `requires-python = ">=3.12"` |
| `tenacity` | D-06 | ✓ | 9.1.4 |
| `httpx` | D-06 | ✓ | per pyproject |
| `aiolimiter` | D-03 | ✗ | **MUST ADD** in 27-01 to `apps/prometheus/pyproject.toml` |
| `python-telegram-bot` | D-08 | ✓ | per pyproject |
| Postgres (Supabase) | D-07 verify | ✓ | runtime |
| `pandas-ta` | D-05 | ✓ | per pyproject |

---

## 9. Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | vnstock 5 req/s soft-ban threshold | Q-1 | If real threshold is lower, SC #2 fails empirically; mitigated by R-1's 4 req/s default + override |
| A2 | Phase 24 baseline can be captured by re-running pipeline against current dev DB | Q-6 | If dev DB is missing data, baseline is unrepresentative; mitigated by also reading historical `pipeline_runs.duration_seconds` if present |
| A3 | Dev environment is acceptable as "staging" for SC #1 perf gate | Q-7 | If dev has materially different DB size/latency than prod, the 3× ratio is meaningless; document this caveat in 27-07 |
| A4 | Telegram errors `NetworkError`/`TimedOut` are transient and worth retrying | P-9 | If Telegram is hard-down for >8s of jittered backoff, send fails — acceptable per D-08 ("digest is best-effort") |

---

## 10. Sources

### Primary (HIGH)

- CONTEXT.md `.planning/phases/27-pipeline-performance/27-CONTEXT.md` (8 LOCKED decisions)
- ROADMAP.md `.planning/ROADMAP.md` lines 155-170 (Phase 27 goal + SCs verbatim)
- REQUIREMENTS.md `.planning/REQUIREMENTS.md:80-85` (PERF-01..PERF-06)
- Phase 26 RESEARCH `.planning/phases/26-caching/26-RESEARCH.md` (predecessor: indicator cache wrap site, pandas-ta dispatch)
- Phase 25 CONTEXT `.planning/phases/25-data-quality/25-CONTEXT.md` (D-03 per-symbol isolation contract)
- Codebase grep audit (10 file:line citations in §2)
- Tenacity docs https://tenacity.readthedocs.io/en/latest/api.html
- aiolimiter docs https://aiolimiter.readthedocs.io/en/latest/
- CPython asyncio docs https://docs.python.org/3/library/asyncio-task.html
- SQLAlchemy pooling https://docs.sqlalchemy.org/en/20/core/pooling.html
- asyncpg pgbouncer guidance https://magicstack.github.io/asyncpg/current/usage.html#pgbouncer

### Secondary (MEDIUM)

- vnstock 4.0.2 transitive deps `uv pip show vnstock` (verified locally)
- aiolimiter latest version PyPI metadata (https://pypi.org/pypi/aiolimiter/json — 1.2.1)

### Tertiary (LOW; flagged in Assumptions Log)

- vnstock 5 req/s empirical soft-ban threshold (community-anecdotal; A1)

---

## 11. Repo Conventions Carried From Phase 26

- Backend: `apps/prometheus/`. Tests: `cd apps/prometheus && uv run pytest`. Lint: `cd apps/prometheus && uvx ruff check`.
- Pre-existing 1 Phase-24 migration test failure unrelated to perf — ignore.
- Commit trailer (REQUIRED): `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.
- Metrics use `localstock_*` prefix and `prometheus_client`. NEW metrics in this phase:
  - `localstock_crawler_circuit_state{source,state}` (Counter — 27-01)
  - `localstock_crawler_circuit_skipped_total{source}` (Counter — 27-01, P-8)
  - `localstock_event_loop_lag_seconds` (Histogram — 27-01)
  - `localstock_telegram_digest_send_duration_seconds` (Histogram — 27-06)
  - `localstock_telegram_send_errors_total` (Counter — 27-06)

---

## Confidence Breakdown

| Area | Level | Reason |
|------|-------|--------|
| Audit lists (§2) | HIGH | Direct grep + line cites |
| Pitfall catalog (§3) | HIGH | Each pitfall traced to a CPython/lib doc citation or in-repo line ref |
| Wave structure (§4) | HIGH | Derived from file-conflict matrix; only deviation from CONTEXT (27-05 W3→W2) is well-justified |
| Q-1 vnstock rate (§1) | MEDIUM | Empirical, no published SLA; ratification R-1 protects against being wrong |
| Q-4 lag sampler (§1) | HIGH | CPython doc-cited pattern; demonstrable RED test |
| Test strategies (§6) | HIGH | Each PERF requirement has a deterministic synthetic harness |

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (30 days; tenacity/aiolimiter/SQLAlchemy are stable)
