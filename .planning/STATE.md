---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Performance & Data Quality
status: Phase 25 Wave 3 in progress — 25-05 complete (DQ-01 OHLCV reject-to-quarantine landed; ROADMAP SC #1 ✅ closed).
stopped_at: Completed 25-05-PLAN.md (Wave 3 — DQ-01 Tier-1 OHLCV reject-to-quarantine; SC #1 ✅)
last_updated: "2026-04-29T07:30:00.000Z"
last_activity: 2026-04-29 — 25-05 complete; OHLCVSchema (Tier 1 strict) + partition_valid_invalid runner + Pipeline._crawl_prices reject-to-quarantine wiring landed; bad rows divert to quarantine_rows{tier='strict'} and increment localstock_dq_violations_total{rule, tier='strict'} per rule; 4/4 RED→GREEN + 1 requires_pg integration test passing; ROADMAP SC #1 verbatim ✅ closed
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 24
  completed_plans: 21
  percent: 79
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.
**Current focus:** v1.5 Performance & Data Quality — Phase 22 Logging Foundation (entry point per A→B→C→D→E→F→G build order)

## Current Position

Phase: 25 — Data Quality (🚧 in progress; Wave 3 in progress)
Plan: 05 (complete) — DQ-01 OHLCV Tier-1 reject-to-quarantine landed; ROADMAP SC #1 verbatim ✅ closed.
Status: 25-05 complete — `OHLCVSchema` (pandera DataFrameSchema, Tier 1 strict) declares symbol regex / date dtype no-coerce (Pitfall E) / OHLC>0 / volume>=0 + composite checks (future_date element-wise, nan_ratio_exceeded ≤5% frame-level, malformed_date) + unique=[symbol,date] + strict=True. `partition_valid_invalid(df, schema)` runs lazy validation, classifies failures into per-row + frame-level rule maps via `_normalize_rule` (CONTEXT D-01 vocabulary: non_positive_<col>, future_date, nan_ratio_exceeded, duplicate_pk, malformed_date, bad_symbol_format), returns (valid_df, invalid_rows, failure_cases). `Pipeline._crawl_prices` builds a validation-shaped frame (rename time→date, inject symbol col), partitions, routes invalid rows to `QuarantineRepository.insert(source='ohlcv', tier='strict', rule, reason)`, increments `localstock_dq_violations_total{rule, tier='strict'}` per rule, then drops bad indices from the original time-keyed frame before `upsert_prices`. `_coerce_payload` (Rule 1 fix) converts pd.Timestamp/datetime/numpy scalars at the json.dumps boundary. 4 RED tests + 1 requires_pg integration test all GREEN.
Last activity: 2026-04-29 — 25-05 Wave 3: 2 commits, 4 files modified, 4/4 RED→GREEN + 1 integration test passing, ruff clean. ROADMAP SC #1 ✅ closed.

Progress: [████████░░] 87%

## Performance Metrics

**Velocity:**

- Total plans completed: 53 (v1.0: 23, v1.1: 12, v1.2: 8, v1.3: 14, v1.4: 11)
- Total plans created: 53

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
