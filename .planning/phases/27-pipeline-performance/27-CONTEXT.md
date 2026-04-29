---
phase: 27
name: Pipeline Performance
milestone: v1.6
status: context-locked
created: 2026-04-29
mode: auto-accept (user accepted all recommendations 2026-04-29)
requirements: [PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06]
---

# Phase 27 — Pipeline Performance: Context & Locked Decisions

## Goal (verbatim from ROADMAP)

Toàn bộ pipeline (crawl + analyze + score + report cho ~400 mã) hoàn thành nhanh hơn baseline ≥ 3× nhờ concurrent crawl, không trigger vnstock soft-ban, không exhaust DB pool, không block event loop bằng pandas-ta.

## Success Criteria (verbatim from ROADMAP)

1. Daily pipeline end-to-end duration giảm ≥ 3× so với baseline đo ở cuối Phase 24 — verified bằng `pipeline_duration_seconds` histogram trước/sau.
2. Crawler dùng `asyncio.Semaphore(8) + gather(return_exceptions=True)` + per-source `aiolimiter` token-bucket; vnstock không trả 429 trong 5 lần chạy liên tiếp; circuit breaker mở sau 3 consecutive 429s.
3. Mọi external HTTP call site được wrap bằng `@retry` (tenacity, exponential backoff + jitter, max 3 attempts) — verified bằng injected transient 503 → request thành công sau retry.
4. `pandas-ta` chạy qua `asyncio.to_thread` — verified bằng event-loop lag metric không spike khi compute indicators cho 400 mã (loop responsive < 100 ms).
5. SQLAlchemy pool tuning áp dụng (`pool_size=10, max_overflow=10, pool_timeout=5, pool_pre_ping=True`, giữ `prepared_statement_cache_size=0`); pipeline 15:30 không log `QueuePool limit ... overflow` lỗi.
6. Telegram digest send là background task (không await trong pipeline finalize) — pipeline marks complete trước khi Telegram message đi.

## Dependencies (verbatim from ROADMAP)

Phase 24 (measure the win), Phase 25 (DQ catch corruption mà concurrency amplify), Phase 26 (cache invalidation hooks tồn tại trước khi restructure write boundaries).

All three predecessors are CLOSED. Pre-existing assets to leverage:

- **Phase 24**: `pipeline_duration_seconds` histogram + `db_query_duration_seconds` slow-query log on `/metrics`. Baseline values for SC #1 must be captured BEFORE any 27 changes land.
- **Phase 25**: Per-symbol `try/except` isolation already in 5 services (analysis / scoring / sentiment / admin / report) — concurrency must preserve this. Pitfall A guardrail (`test_no_gather_in_per_symbol_loops`) currently blocks `asyncio.gather` over `symbol`. **Phase 27 will replace that guardrail with a structured `Semaphore + gather` pattern** in the crawler stage only; analyze/score/sentiment/report remain serial-with-isolation.
- **Phase 26**: `cache.invalidate_namespace(...)` hooks at lines 109/142/174 of `automation_service.py`. Concurrency restructuring must keep those write→invalidate sequences intact.

## Locked Decisions

### D-01 — Concurrency Boundary: Crawler Only
**LOCKED**: Concurrency primitives (`Semaphore`, `gather`, `aiolimiter`, circuit breaker) are scoped to the **crawl stage** only. Analyze, score, sentiment, and report stages remain serial-with-isolation as established in Phase 25 (D-03 LOCKED there).

- Rationale: per Phase 25 RESEARCH/CONTEXT, per-symbol serial loops with structured `_failed_symbols` buffers are the contract for downstream stages. Concurrency on those stages would break SC #3 of Phase 25 (per-symbol isolation) and Pitfall A (no `gather` over `symbol`).
- Phase 27's `pandas-ta` parallelism (D-05) is achieved via `asyncio.to_thread` — **per call**, not via `gather` over a per-symbol generator. The serial loop continues to drive `to_thread` calls one at a time so the existing isolation pattern is preserved.
- **The Pitfall-A guardrail is updated, not deleted**: the regex now whitelists `crawlers/` modules where `gather` over `symbol` is the new contract. Tests in 27-01 will assert (a) crawler uses `gather`, (b) analyze/score/sentiment/report do NOT.

### D-02 — `Semaphore` Cap = 8 (LOCKED by ROADMAP SC #2)
**LOCKED**: `asyncio.Semaphore(8)` for crawler concurrency, exact value from SC #2.

- Configurable via `CRAWLER_CONCURRENCY` env var with default `8` (so ops can dial down if vnstock policy changes), but the default is what passes SC #2.
- The token-bucket (D-03) is the upstream rate limiter; the semaphore is the downstream concurrency cap. Both are required.

### D-03 — Token-Bucket: `aiolimiter`, Per-Source Configurable
**LOCKED**: `aiolimiter.AsyncLimiter` per data source (vnstock primary, FMP-style backup if any). Token-bucket limit values are NOT in the SC; research must derive them empirically (typical vnstock budget is ~5 req/s but unconfirmed — researcher confirms from vnstock docs / observed 429 thresholds).

- Defaults pending research: `vnstock` initial = `AsyncLimiter(max_rate=5, time_period=1.0)` (5/s) — researcher to ratify.
- Each crawler entry point composes `async with limiter, semaphore: ...` so both gates are enforced.

### D-04 — Circuit Breaker: 3-Strike + 60s Cool-Off
**LOCKED** (per SC #2 + standard pattern):

- After **3 consecutive 429s** from the same source, the circuit OPENS for **60 s** (cool-off).
- During OPEN state, all calls to that source short-circuit with a `CircuitOpenError` immediately (no retry, no wait).
- After cool-off elapses, the circuit moves to HALF-OPEN: the next call is a probe; success → CLOSED, failure → re-open for another 60 s.
- Implementation: a small in-process `CircuitBreaker` class (~50 LOC), no external dep. Lives in `crawlers/_circuit.py`.
- The 60 s cool-off is configurable via `CRAWLER_CIRCUIT_COOLOFF_SECONDS` (default 60).
- A new metric `crawler_circuit_state{source, state}` Counter increments on each transition for observability.

### D-05 — `pandas-ta` Offload: `asyncio.to_thread` per `analyze_technical_single` Call
**LOCKED**: The `pandas-ta` bundled call inside `AnalysisService.analyze_technical_single` (line 264, audited in Phase 26 RESEARCH) is wrapped with `await asyncio.to_thread(_pandas_ta_compute, df)`.

- **Granularity**: per single call (per symbol). Do NOT batch into one `to_thread` over many symbols — that would block per-symbol isolation. The serial loop continues to drive one `to_thread` call at a time.
- **Cache-aware**: this happens INSIDE the `cached_analyze_technical_single` wrapper (Phase 26 D-06). On a cache hit, `to_thread` is never called (cheap return path). The offload only occurs on the slow path, which is exactly what SC #4 measures.
- **Verification**: a new metric `event_loop_lag_seconds` (Histogram) sampled every 100 ms during a synthetic 400-symbol run; SC #4 requires p95 < 100 ms.

### D-06 — Tenacity Retry: Exponential Backoff + Jitter, max 3 Attempts
**LOCKED** (per SC #3 verbatim):

- Decorator: `@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=8.0), retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)))`.
- Applies to: every external HTTP call site — vnstock client wrappers, news crawler HTTP gets, Telegram bot send, FMP/macro client calls (audit list to be produced by researcher).
- 429s and circuit-open errors are NOT retried by tenacity — they are handled by the circuit breaker (D-04). Use `retry=retry_if_exception_type(...)` to scope to transient 5xx + transport errors only.
- A `RetryError` after exhaustion bubbles up to per-symbol `try/except` (Phase 25 D-03 contract) and lands in `_failed_symbols`.

### D-07 — SQLAlchemy Pool Tuning (LOCKED by ROADMAP SC #5)
**LOCKED** values verbatim from SC #5:

```python
create_async_engine(
    url,
    pool_size=10,
    max_overflow=10,
    pool_timeout=5,
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_cache_size": 0,  # PRESERVE — Supabase pgbouncer
        "statement_cache_size": 0,
    },
)
```

- Applied in `db/database.py` `get_engine()` factory.
- `pool_pre_ping=True` adds a SELECT 1 before each checkout (~1 ms overhead) — acceptable price for stale-connection survivability under bursty 15:45 load.
- `pool_timeout=5` means a checkout that waits >5 s raises `TimeoutError` instead of hanging forever — caught by per-symbol try/except, logged as failed, pipeline continues.
- **No async-pool-class change** (still default `AsyncAdaptedQueuePool`) — Supabase + asyncpg standard.
- **Verification**: log search for `"QueuePool limit"` and `"connection invalidated"` over 5 consecutive 15:45 runs must yield zero hits.

### D-08 — Telegram Digest: Fire-and-Forget via `asyncio.create_task`
**LOCKED**: After pipeline finalize emits success metrics + invalidates caches, the Telegram digest send is launched as a fire-and-forget background task:

```python
task = asyncio.create_task(
    notification_service.send_daily_digest(payload),
    name="telegram_daily_digest",
)
task.add_done_callback(_log_task_exception)  # don't swallow exceptions silently
```

- Pipeline `finalize()` does NOT `await` this task — it returns immediately so `pipeline_duration_seconds` reflects pipeline cost, not Telegram round-trip.
- A weak reference is held in a module-level `_pending_tasks: set[asyncio.Task]` per the `asyncio.create_task` GC pitfall — done callback removes from set.
- If FastAPI shuts down with the task still running, uvicorn's graceful shutdown (`lifespan`) awaits the set with a 10s timeout; tasks unfinished by then are cancelled (digest is best-effort).
- A new metric `telegram_digest_send_duration_seconds` (Histogram) is recorded inside the task, so we still observe digest latency separately from pipeline duration.
- Tenacity retries (D-06) wrap the bot.send call inside the task; failures after 3 attempts log + increment `telegram_send_errors_total`.

## Out of Scope (Deferred / Not in This Phase)

- **Phase 28** territory: composite indexes, bulk upsert, `CREATE INDEX CONCURRENTLY` migrations. Phase 27 measures pool/concurrency wins but does NOT touch query shape.
- Multi-process worker pool / pre-fork crawler processes — single asyncio loop with `to_thread` is sufficient per SC #4.
- Adaptive concurrency (vary `Semaphore` cap based on observed 429 rate) — fixed at 8 for v1.6; revisit if SC #2 fails empirically.
- Replacing `aiolimiter` with custom token-bucket — only if `aiolimiter` proves unmaintained (it isn't, as of writing).
- Crawler retry budget separate from per-call tenacity (e.g., "retry the entire stage if >50% symbols fail") — out of scope; Phase 25's per-symbol isolation is the contract.

## Open Questions for Researcher

1. **Q-1 (token-bucket rate)**: What is the documented or empirically observed safe `aiolimiter` rate for vnstock? Default in D-03 is 5 req/s — confirm against vnstock issue tracker and prior 429 incident logs.
2. **Q-2 (HTTP call audit)**: Produce the full list of external HTTP call sites that need `@retry` (D-06) — vnstock client + news crawler + macro feeds + Telegram. Verify each is `httpx`-based (tenacity wrap requires consistent exception types).
3. **Q-3 (circuit breaker scope)**: Should the breaker be per-source (vnstock-wide) or per-endpoint (per vnstock route)? Default in D-04 is per-source — confirm this matches the 429 blast radius.
4. **Q-4 (event-loop lag instrumentation)**: How to sample event-loop lag without itself adding lag? Default: `loop.call_later(0.1, _sample)` recording wall-clock drift from expected wake — confirm precision is acceptable for SC #4's 100 ms gate.
5. **Q-5 (Pitfall-A guardrail update)**: Where exactly is the existing `test_no_gather_in_per_symbol_loops` (Phase 25) and how should the new whitelist for `crawlers/` be expressed without permitting it elsewhere?
6. **Q-6 (baseline measurement)**: Has Phase 24 already captured a `pipeline_duration_seconds` baseline? If yes, where is the snapshot? If no, the first plan must capture one before any code changes.
7. **Q-7 (concurrent test harness)**: Do we test concurrency with a synthetic 400-symbol simulation (mocked vnstock) or a real run? Default: synthetic in CI + real in staging — confirm the staging path exists.

## Audit Lists for Researcher

- All call sites of vnstock client functions (for Semaphore/limiter wrapping).
- All `httpx` invocations across `crawlers/`, `services/notifications/`, `services/news_service.py`, `services/macro_service.py` (for tenacity wrapping).
- All places `pandas-ta` or `pd_ta` is imported / called (for `to_thread` wrapping — should be exactly one site at `analysis_service.py:264` per Phase 26 audit, but verify no drift).
- Engine creation site(s) — confirm there is exactly one `create_async_engine` call to retune.
- Telegram send call sites (should be one — `notification_service.send_daily_digest` — but verify no admin-triggered sync sends remain).

## Suggested Plan Structure (Researcher will refine)

- **27-01 (W1, solo)**: Baseline capture + concurrency primitives module (`crawlers/_concurrency.py` with `Semaphore`, limiter factory, circuit breaker class). Closes part of PERF-01 prerequisite.
- **27-02 (W2)**: Crawler refactor — wire `Semaphore + aiolimiter + circuit_breaker` into vnstock client + per-source crawl entry points. Closes PERF-01 + PERF-02. SC #2.
- **27-03 (W2)**: Tenacity decorator on all external HTTP call sites (audit list from researcher). Closes PERF-03. SC #3.
- **27-04 (W2)**: `asyncio.to_thread` wrap of `pandas-ta` call + event-loop lag metric. Closes PERF-04. SC #4.
- **27-05 (W3)**: Engine pool tuning + log assertion test. Closes PERF-05. SC #5.
- **27-06 (W3)**: Telegram fire-and-forget refactor + digest duration metric + lifespan-shutdown drain. Closes PERF-06. SC #6.
- **27-07 (W4, solo)**: End-to-end perf gate — measure post-change `pipeline_duration_seconds` p95 against baseline; assert ≥ 3× speedup. Closes SC #1 + Phase 27.

(Researcher decides final wave plan; this is a starting hypothesis for their critique.)

## Threats Pre-Identified (research will expand)

- **T-1**: Semaphore + per-symbol isolation interaction — if a symbol fails inside `gather`, the exception must surface as a structured `_failed_symbols` entry, not abort the gather. `return_exceptions=True` is mandatory (already in SC #2).
- **T-2**: `aiolimiter` acquires synchronously (no timeout) — under sustained pressure could starve. Mitigate by bounding total crawl time with `asyncio.timeout(...)` at the stage level.
- **T-3**: `to_thread` thread-pool default is `min(32, os.cpu_count() + 4)` — under 400-symbol fanout this is fine since it's serial, but if granularity ever changes to parallel, the default pool would saturate. Document the constraint inline.
- **T-4**: `pool_pre_ping` adds a SELECT 1 per checkout — if the pipeline does N=20k tiny queries, pre-ping cost is non-trivial. Researcher confirms expected query count and whether `pool_recycle=300` is a better trade.
- **T-5**: `create_task` without keeping a strong ref — Python may GC the task before it runs (the documented `asyncio.create_task` pitfall). D-08 mitigates with the `_pending_tasks` set.
- **T-6**: Telegram digest cancelled on shutdown — if user runs `kill -TERM` mid-send, digest is lost. Acceptable by SC #6 (digest is best-effort, pipeline correctness is not at stake).
- **T-7**: Tenacity retry interacts with circuit breaker — if a 429 reaches tenacity and tenacity retries, we'd violate the "3 strikes opens the circuit" rule by issuing 3 retries × 3 strikes = 9 calls before opening. Mitigate: tenacity's `retry_if_exception_type` excludes 429 (the breaker handles those).
- **T-8**: Event-loop lag sampling itself runs on the loop — can mis-attribute lag to itself if unconditional. Sample rate 100 ms is large enough that the sampler's own time is negligible (<1%).

## Repo Conventions (carried from Phase 26)

- Backend: `apps/prometheus/`; tests `uv run pytest`; lint `uvx ruff check`.
- Pre-existing 1 Phase-24 migration test failure unrelated; ignore.
- Commit trailer (REQUIRED): `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.
- All metrics use `localstock_*` prefix and Prometheus client. New metrics this phase: `crawler_circuit_state{source,state}`, `event_loop_lag_seconds`, `telegram_digest_send_duration_seconds`, `telegram_send_errors_total`.

---

**Status:** All 8 decisions auto-accepted by user 2026-04-29. Ready for `/gsd-plan-phase 27` (researcher → planner → plan-checker).
