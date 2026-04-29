---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Performance & Data Quality
status: completed
stopped_at: "Completed 25-07-PLAN.md (Wave 5 — DQ-02 Tier 2 dispatcher + DQ-03 promotion runbook; SC #4 ✅)"
last_updated: "2026-04-29T16:40:00.000Z"
last_activity: "2026-04-29 — 26-03 Wave 2 complete (CACHE-02 ✅, ROADMAP SC #2 ✅ verbatim closed). PipelineRunRepository.get_latest_completed() reads max-completed PK with status filter (T-26-03-02). cache.version.resolve_latest_run_id wraps it in get_or_compute(namespace='pipeline:latest_run_id', key='current') — 5s TTL (D-02) absorbs request bursts. Public re-export added to localstock.cache. Lazy import of get_or_compute inside helper sidesteps circular load with __init__.py. Verbatim SC #2 test: seed run1 → populate scores:ranking:run=1 → insert run2 → invalidate both namespaces (simulating 26-05 finalize hook) → resolver returns run2 immediately (no 5s wait); old run=1 key unreachable by composers — old key never serves stale data. 5s-TTL hit/miss test pins counters delta. 18/18 cache+repo tests GREEN; ruff clean. Full suite: 583 passed, 2 out-of-scope fails (Phase-24 migration_downgrade pre-existing; test_market_route::test_endpoint_calls_repo polluted by 26-04 cache-wrapping — owner: 26-04). 4 commits (4c1646a RED repo, 54ff416 GREEN repo, 05a697d RED versioning, 937565b GREEN versioning) with Copilot co-author trailer."
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 30
  completed_plans: 28
  percent: 93
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.
**Current focus:** v1.6 Performance Caching — **Phase 26 IN PROGRESS** (3/6 plans complete). 26-01 ✅ closes CACHE-04 + ROADMAP SC #3; 26-02 ✅ closes CACHE-07; 26-03 ✅ closes CACHE-02 + ROADMAP SC #2. Next: 26-04 SUMMARY pending, then 26-05/06.

## Current Position

Phase: 26 — Caching (IN PROGRESS — 3/6 plans complete; ROADMAP SC #2 ✅ + SC #3 ✅ closed)
Plan: 03 (complete) — PipelineRunRepository.get_latest_completed + cache.version.resolve_latest_run_id (5s TTL) + verbatim SC #2 closure. Wave 2 sibling 26-04 has feat commit (f208c4a) but SUMMARY pending.
Status: 26-03 complete — `db/repositories/pipeline_run_repo.py` ships `PipelineRunRepository.get_latest_completed() -> int | None` (async-SQLAlchemy 2.0 read-only repo, mirrors news_repo.py shape; `select(PipelineRun.id).where(status='completed').order_by(completed_at.desc()).limit(1)` filters running/failed rows — T-26-03-02). New `cache/version.py` exposes `resolve_latest_run_id(session_factory)` wrapping the repo call in `get_or_compute(namespace='pipeline:latest_run_id', key='current', compute_fn=_fetch)` — 5s TTL from D-02 absorbs request bursts (T-26-03-03). Lazy import of `get_or_compute` inside the helper body sidesteps circular load; `cache/__init__.py` re-exports `resolve_latest_run_id` AFTER `get_or_compute` is defined. ROADMAP SC #2 verbatim closure (`tests/test_cache/test_versioning.py::test_new_pipeline_run_invalidates_old_keys`): seeds run1 → populates `scores:ranking:limit=50:run=N1` → inserts run2 → invalidates both namespaces (simulating 26-05 finalize hook) → resolver returns N2 immediately without waiting for 5s TTL; old `run=N1` key is unreachable because composers only ever address the current run_id. 5s-TTL hit/miss test pins `cache_hits_total{cache_name='pipeline:latest_run_id'}` delta=1 and `cache_misses_total` delta=1 across two back-to-back calls. 18/18 cache + new repo tests GREEN; `uvx ruff check` clean on `src/localstock/cache/`, `src/localstock/db/repositories/pipeline_run_repo.py`, `tests/test_cache/test_versioning.py`, `tests/test_db/test_pipeline_run_repo.py`. Full project suite 583 passed, 2 out-of-scope fails: Phase-24 `migration_downgrade` (pre-existing, ignored per prompt) and `test_market_route::TestMarketSummaryResponse::test_endpoint_calls_repo` (NEW failure caused by 26-04 wrapping `/market/summary` with `get_or_compute` — cached results bypass the test's mock; passes in isolation; logged to `.planning/phases/26-caching/deferred-items.md` for 26-04 owner). 4 commits with Copilot co-author trailer: 4c1646a (test 26-03 RED repo), 54ff416 (feat 26-03 GREEN repo), 05a697d (test 26-03 RED versioning), 937565b (feat 26-03 GREEN versioning).
Last activity: 2026-04-29 — 26-03 Wave 2: 4 commits, 4 files created + 1 modified, 5/5 RED→GREEN (3 repo + 2 versioning), 18/18 cache+repo, 583/585 full suite (2 out-of-scope), ruff clean. CACHE-02 ✅; ROADMAP SC #2 ✅ verbatim closed.

Progress: [█████████░] 93%

## Performance Metrics

**Velocity:**

- Total plans completed: 54 (v1.0: 23, v1.1: 12, v1.2: 8, v1.3: 14, v1.4: 11)
- Total plans created: 54

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Full decision history from v1.0–v1.4 archived in `.planning/milestones/`.

- Phase 22 Wave 0: RED test scaffolds + OBS-06 lint skeleton landed before any impl (Nyquist contract)
- 22-02: log_level field_validator normalizes to uppercase and rejects non-loguru levels at startup (OBS-01)
- Phase 22 Plan 01: lazy _stdout_sink callable for loguru sink to support pytest capsys per-test stdout swap; preserves serialize/enqueue/diagnose contract
- 22-03: CorrelationIdMiddleware validates inbound X-Request-ID against ^[A-Za-z0-9-]{8,64}$ and uses logger.contextualize for loguru extras (D-02/D-04)
- 22-05: f-string log sweep used `logger.exception()` inside every except block — auto-captures traceback through redacted JSON sink instead of f-string interpolating exception value
- 24-04: /health split into 4 probes (`/health/{live,ready,pipeline,data}`) + deprecated `/health` alias with `X-Deprecated` header. Bounded 2s `asyncio.wait_for` DB ping → 503 on `OperationalError`/timeout. Static VN holiday set 2025–2026; full calendar deferred (OBS-14)
- 24-05: dedup keyed by `(job_id, error_type)` with `threading.Lock` + 15-min window — distinct keys NOT deduped together (D-06). Telegram dispatch is `asyncio.create_task` fire-and-forget with done-callback to suppress task exceptions. `@observe('crawl.<subsystem>.fetch')` applied to PriceCrawler/FinanceCrawler/CompanyCrawler/EventCrawler entry points only — minimal CONTEXT D-01 scope. Phase 23 D-08 boundary explicitly lifted for 24-05 implementation files (documented in 24-05-SUMMARY.md)
- 24-06: `Pipeline._step_timer(step_name, run)` is the documented D-08 exception in `services/pipeline.py` — atomic column write (`setattr(run, f'{step_name}_duration_ms', ms)`) + histogram emission via `REGISTRY._names_to_collectors` lookup. `try/yield/except(set fail outcome, raise)/finally(record + observe)` ordering guarantees column write on exception path (Pitfall 7). Q-3 wrap granularity: crawl=Steps 1-7, analyze=`_apply_price_adjustments` only; score/report explicitly None until AutomationService integration (future phase)
- 25-01: Wave 0 scaffolds shipped — pandera installed, dq/ package + Alembic 25a0b1c2d3e4 + Settings + Counter + 30 RED tests landed
- 25-02: sanitize_jsonb is the single source of truth for JSONB NaN/Inf scrubbing — wired at first line of every JSONB-bound repo write (financial/report/score/notification/job). Inline `_clean_nan` in services/pipeline.py REMOVED. Recipe handles dict/list/tuple recursion + numpy.float64 (via float-subclass isinstance) + bool short-circuit. scheduler.py:156 errors-dict NOT wrapped (owned by 25-03; literal dict has no float content). DQ-04 + ROADMAP SC #2 closed.
- 25-03: QuarantineRepository.cleanup uses Python-side `datetime.now(UTC) - timedelta(days)` cutoff bound parameter (not SQL `now() - interval`) so the boundary is testable with frozen-time fixtures. APScheduler `dq_quarantine_cleanup` registered at hour=3 minute=15 Asia/Ho_Chi_Minh with max_instances=1 + coalesce=True — Pitfall F mandate: away from 15:46 daily pipeline, single instance, stale fires coalesced. Test asserts `job.trigger.timezone` attribute (not `str(job.trigger)`, which omits tz). Producer (DQ-01 reject-to-quarantine) deferred to 25-05.
- 25-04: `Pipeline._write_stats(run, *, succeeded, failed, skipped, failed_symbols)` is the single write-point for `PipelineRun.stats` JSONB; dual-writes scalars `symbols_total/success/failed` per CONTEXT D-07 LOCKED through v1.5 (drop in v1.6). Module-level `_truncate_error(exc)` formats `'{ExcClass}: {str(exc)[:MAX_ERROR_CHARS]}...'` — class prefix sits OUTSIDE the 200-char cap; only `str(exc)` captured, no traceback (T-25-04-01). `failed_symbols` shape locked as `[{"symbol", "step", "error"}, ...]` for 25-06 consumption. run_full's except branch also calls `_write_stats` (succeeded=0, failed=len(symbols)) so `status="failed"` rows are never NULL-stats. Stats dict funneled through `sanitize_jsonb` before assignment (T-25-04-03 defence-in-depth). Tests use AsyncMock-session harness from sibling test_pipeline_step_timing.py — no live PG needed because stats write is in-memory attribute assignment.
- 25-05: `OHLCVSchema` is the Tier 1 strict pandera DataFrameSchema for OHLCV ingest — symbol regex `^[A-Z0-9]{3,5}$`, date dtype `datetime64[ns]` with NO coerce (Pitfall E — caller pre-coerces with `pd.to_datetime` + explicit `malformed_date` Check), OHLC > 0, volume ≥ 0, composite future_date (element-wise) + nan_ratio_exceeded (frame-level scalar, ≤ 5% per column) + unique=[symbol,date] + strict=True. `partition_valid_invalid(df, schema)` runs `schema.validate(df, lazy=True)`, catches `pae.SchemaErrors`, builds (per-row + frame-level) rule maps; frame-level failures invalidate every row in the per-symbol batch. `_normalize_rule` is the canonical pandera-check-name → CONTEXT D-01 vocabulary mapper (`negative_price`/`non_positive_<col>`, `future_date`, `nan_ratio_exceeded`, `malformed_date`, `duplicate_pk`, `bad_symbol_format`). `_coerce_payload` (Rule 1 fix) handles pd.Timestamp / datetime / numpy scalars at the QuarantineRepository.insert → json.dumps boundary; sanitize_jsonb keeps NaN/Inf scrubbing (DQ-04 belt-and-suspenders). `Pipeline._crawl_prices` builds a validation-shaped frame (rename time→date, inject symbol col) for OHLCVSchema then drops bad indices from the original time-keyed frame before upsert_prices — separation prevents Tier 1 schema from leaking into upsert contract. Tier 1 metric increment uses `REGISTRY._names_to_collectors` lookup (Phase 23 D-08 boundary, also used by 24-06 step-timer). ROADMAP SC #1 verbatim ✅ closed.
- 25-06: Per-symbol serial `for symbol in symbols: try/except` isolation across analysis_service / scoring_service / sentiment_service / admin_service / report_service / finance_crawler — NO `asyncio.gather` over per-symbol generators (CONTEXT D-03 LOCKED, Pitfall A — bounded concurrency deferred to Phase 27). Each AnalysisService/ScoringService/SentimentService/ReportService maintains `self._failed_symbols: list[dict] = []` buffer + `get_failed_symbols(reset: bool = True) -> list[dict]` drain method; entries shape `{symbol, step, error: _truncate_error(e)}`. AutomationService caller-side aggregation contract: Pipeline.run_full only aggregates crawl-step failures (Q-3 scope); analyze/score/sentiment/report buffers drained by AutomationService when wired. Pipeline.run_full failed_symbols dedup tightened to `(symbol, step)` tuple (was symbol-only) per CONTEXT D-03 step-level granularity — separate `failed_symbol_set: set[str]` for the failed-counter tally. RESEARCH Open Q4 closed: report_service.py:137 (`for score in scores:` loop with `symbol = score.symbol`) IS a per-symbol loop and is now isolated with structured aggregation (step='report'). Pitfall A guardrail (test_no_gather_in_per_symbol_loops) inspects 5 service modules with comment-line skipping and fails CI if any non-comment line contains both `asyncio.gather` and `symbol`. Tests use AsyncMock-session harness (no Postgres dependency) — 4 GREEN: SC #3 verbatim (1 BAD + 2 GOOD → status=completed/succeeded=2/failed=1), keyset assertion, AnalysisService run_full with raising tech+fund, Pitfall A guardrail. ROADMAP SC #3 verbatim ✅ closed jointly with 25-04 DQ-06.
- 25-07: `evaluate_tier2(rule, df, predicate, *, symbol=None)` is the canonical Tier 2 advisory dispatcher (DQ-02). Shadow-by-default: `get_tier2_mode(rule_name)` reads `Settings.dq_tier2_<rule>_mode` → `Settings.dq_default_tier2_mode` → hard fallback `'shadow'`. Tier label `'advisory'` in shadow / `'strict'` in enforce. Always emits `localstock_dq_violations_total{rule, tier}` + `dq_warn` log; raises `Tier2Violation(rule, offending)` ONLY in enforce mode → caught by 25-06 per-symbol try/except → `PipelineRun.stats.failed_symbols` (D-03 + D-06). Predicates: `predicate_rsi_anomaly` (RSI > 99.5, indicators schema), `predicate_gap_30pct` (close-to-close > 30%, sorts by date defensively, drops first-bar NaN), `predicate_missing_rows_20pct` (frame-level signal when `1 - actual/expected > 0.20`). Wired into `AnalysisService.analyze_technical_single` after `compute_indicators`; `Tier2Violation` re-raised, all OTHER predicate exceptions logged as `dq.tier2.predicate_error` and swallowed (Rule 2 defense-in-depth — buggy advisory check must never break analysis). `metrics.iter_tracked_collectors(name)` + `_TRACKED_REGISTRIES: WeakSet[CollectorRegistry]` populated by `init_metrics(target)` so the dispatcher increments collectors on EVERY tracked registry (Rule 1 — required for the SC #4 RED test contract `reg = CollectorRegistry(); init_metrics(reg); evaluate_tier2(...); reg.get_sample_value(...) >= 1`). `docs/runbook/dq-tier2-promotion.md` (117 lines, replaces Wave 0 placeholder): Promotion Criteria 5-point gate (≥14d advisory, <5% violation rate, no FP review, exemplar present, AutomationService digest reviewed), Procedure (`DQ_TIER2_<NAME>_MODE=enforce` env flag flip + restart + verify tier="strict" series), Rollback (>30% symbol-failure trigger), Per-Rule Status Table. `test_runbooks.py` upgraded existence-only → content-required (`Promotion Criteria`, `Rollback`, `Per-Rule Status Table`, `DQ_TIER2_`, `shadow`, `enforce`, `14-day`). New `test_sc4_tier2_emits_metric_no_block` — verbatim ROADMAP SC #4 closure (assert no raise + `dq_violations_total{rule="rsi_anomaly", tier="advisory"} >= 1`). 6/6 dispatch tests + 1/1 runbook content test GREEN; 83/83 `test_services + test_dq + test_docs` (no regressions). ROADMAP SC #4 verbatim ✅ closed.
- 25-08: `GET /health/data` extended with `data_freshness` block { last_trading_day, max_data_date, sessions_behind, status, threshold_sessions } (DQ-07, ROADMAP SC #5 verbatim ✅). `status=fresh` iff `sessions_behind <= settings.dq_stale_threshold_sessions` (default 1 from 25-01); `stale` otherwise; `unknown` on cold start (`max_data_date is None`). Phase 24 top-level keys (`max_price_date`, `trading_days_lag`, `stale`) preserved verbatim per CONTEXT D-05 — back-compat unbroken. New helper `_last_trading_day_on_or_before(today)` placed next to `_trading_days_lag` in `api/routes/health.py`: bounded backwards-walk (cap=20) over `_VN_HOLIDAYS_2025_2026` ∪ weekends, reuses existing Phase 24 `_is_trading_day` predicate (no new holiday set — DRY). HTTP 200 in all states (D-05 — `/health/data` is freshness REPORT not liveness gate; status flagged in body, not status code). Local `from localstock.config import get_settings` import inside route handler — lets tests `get_settings.cache_clear() + monkeypatch.setenv("DQ_STALE_THRESHOLD_SESSIONS", "10")` at request time. 3 RED tests from 25-01 (`tests/test_api/test_health_data_freshness.py`) GREEN; new `test_sc5_health_data_response_shape` pins both Phase 24 trio + DQ-07 5-key block. 145/145 regression in test_api + test_dq + test_observability + test_services (no regressions). **Phase 25 CLOSED — 8/8 plans, 5/5 SCs ✅; v1.5 DQ scope DONE.**

### Watch Out For (from research)

Top pitfalls from `.planning/research/PITFALLS.md` to keep front-of-mind through v1.5:

- Pitfall 4 — f-string log lines defeat structured logging (Phase 22 CI gate)
- Pitfall 5 — loguru double-init / Prometheus `Duplicated timeseries` in tests (Phase 22, 23)
- Pitfall 6 — label cardinality explosion if `symbol` becomes a label (Phase 23)
- Pitfall 10 — NaN/Inf into JSONB → broken `/api/reports` JSON parse (Phase 25)
- Pitfall 11 — Tier 2 hard-gates abort day-one; require shadow mode (Phase 25)
- Pitfall 1 — TTL-only cache returns stale ranks after pipeline; key must include `pipeline_run_id` (Phase 26)
- Pitfall 8 — vnstock soft-ban on uncapped concurrency; Semaphore(8) + token-bucket (Phase 27)
- Pitfall 9 — DB pool exhaustion at 15:45 if `pool_size` not lifted with concurrency (Phase 27)
- Pitfall 12 — locking index migrations during pipeline window; `CREATE INDEX CONCURRENTLY` only, run outside 15:30–16:30 (Phase 28)
- Pitfall 13 — Supabase pgbouncer disables `pg_stat_statements` on transaction-pooler URL (Phase 28)

### Pending Todos

None.

### Blockers/Concerns

None.

## Deferred Items

Items carried over from earlier milestones:

| Category | Item | Status |
|----------|------|--------|
| uat | Phase 07: 07-UAT.md — 9 pending scenarios | testing |
| verification | Phase 09: 09-VERIFICATION.md | human_needed |
| verification | Phase 21: 21-VERIFICATION.md | human_needed (UAT completed) |
| Phase 22 P00 | 6 | 3 tasks | 12 files |
| Phase 22 P02 | 4m | 1 tasks | 2 files |
| Phase 22 P01 | 6m | 4 tasks | 11 files |
| Phase 22 P03 | 12min | 2 tasks | 3 files |
| Phase 22 P06 | 5min | 3 tasks | 2 files |
| Phase 23 P03 | 2 | 1 tasks | 1 files |
| Phase 25 P01 | 25min | 7 tasks | 23 files |

## Session Continuity

Last session: 2026-04-29T06:29:32.746Z
Stopped at: Completed 25-07-PLAN.md (Wave 5 — DQ-02 Tier 2 dispatcher + DQ-03 promotion runbook; SC #4 ✅)
Resume: `/gsd-plan-phase 25` — Data Quality (next)

**Planned Phase:** 22 (Logging Foundation) — 7 plans — 2026-04-28T10:23:23.585Z
