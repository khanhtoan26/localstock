---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Performance & Data Quality
status: Phase 25 Wave 4 complete — 25-06 landed (DQ-05 per-symbol error isolation; ROADMAP SC #3 ✅ closed).
stopped_at: Completed 25-06-PLAN.md (Wave 4 — DQ-05 per-symbol try/except isolation across services + crawlers; SC #3 ✅)
last_updated: "2026-04-29T07:50:00.000Z"
last_activity: 2026-04-29 — 25-06 complete; per-symbol try/except isolation landed across analysis_service / scoring_service / sentiment_service / admin_service / report_service / finance_crawler. New per-service `_failed_symbols` buffers + `get_failed_symbols(reset=True)` drain pattern; AutomationService caller-side aggregation contract documented in pipeline.run_full. pipeline.py failed_symbols dedup tightened to (symbol, step) tuple per CONTEXT D-03 step-level granularity. Pitfall A guardrail test (test_no_gather_in_per_symbol_loops) inspects 5 service modules and fails CI if any non-comment line contains both asyncio.gather and symbol — bounded concurrency deferred to Phase 27. RESEARCH Open Q4 closed: report_service.py:137 IS a per-symbol loop and is now isolated with structured aggregation. 4/4 RED→GREEN tests using AsyncMock-session harness (no Postgres dep). ROADMAP SC #3 verbatim ✅ closed.
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 24
  completed_plans: 22
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.
**Current focus:** v1.5 Performance & Data Quality — Phase 25 Wave 4 complete; Wave 5 (25-07 Tier 2 dispatcher + 25-08 freshness probe) remains.

## Current Position

Phase: 25 — Data Quality (🚧 in progress; Wave 4 complete)
Plan: 06 (complete) — DQ-05 per-symbol error isolation landed; ROADMAP SC #3 verbatim ✅ closed.
Status: 25-06 complete — Per-symbol serial `for symbol in symbols: try/except` isolation applied (NOT asyncio.gather — CONTEXT D-03 LOCKED, Pitfall A guardrail). Each AnalysisService/ScoringService/SentimentService/ReportService maintains `self._failed_symbols: list[dict] = []` buffer + `get_failed_symbols(reset: bool = True)` drain method; entries shape `{symbol, step, error: _truncate_error(e)}`. Audit list closed: 4 previously-unwrapped loops now in try/except (analysis_service:456,474; scoring_service:176; sentiment_service:145), 5 admin_service loops adapted to structured logging + `_truncate_error` in result dicts (steps: admin.crawl, admin.report, admin.pipeline.crawl/analyze/report), report_service per-symbol loop (RESEARCH Open Q4) confirmed isolated and now buffers as step='report'. finance_crawler:109 verified isolated with audit comment. Pipeline.run_full failed_symbols aggregation dedup tightened to (symbol, step) tuple — one symbol can fail in multiple steps (CONTEXT D-03 step-level granularity); separate failed_symbol_set for the count. AutomationService caller-side aggregation contract documented (Pipeline.run_full only handles crawl-step today per Q-3 scope; analyze/score/sentiment/report buffers drained by AutomationService when wired). 4 GREEN tests via AsyncMock-session harness: test_one_bad_symbol_completes_batch (SC #3 verbatim — 1 BAD + 2 GOOD → status=completed, succeeded=2, failed=1), test_failed_symbols_step_recorded (keyset {symbol,step,error}), test_analyze_step_isolation (AnalysisService run_full with one symbol raising in technical AND fundamental — counters increment, buffer captures BAD/analyze with `_truncate_error` formatting), test_no_gather_in_per_symbol_loops (Pitfall A guardrail across 5 service modules).
Last activity: 2026-04-29 — 25-06 Wave 4: 3 commits, 8 files modified, 4/4 GREEN tests, ruff clean (pre-existing warnings only). ROADMAP SC #3 ✅ closed jointly with 25-04 DQ-06.

Progress: [█████████░] 92%

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
Stopped at: Completed 25-01-PLAN.md (Wave 0 scaffolds — pandera + dq/ + alembic 25a0b1c2d3e4 + 30 RED tests)
Resume: `/gsd-plan-phase 25` — Data Quality (next)

**Planned Phase:** 22 (Logging Foundation) — 7 plans — 2026-04-28T10:23:23.585Z
