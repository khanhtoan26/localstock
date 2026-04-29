---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Performance & Data Quality
status: Phase 24 fully closed (OBS-11, OBS-12, OBS-13, OBS-14, OBS-15, OBS-16, OBS-17). All 6 plans + Wave 0 scaffolds shipped.
stopped_at: Completed 25-03-PLAN.md (Wave 1 — DQ-08 QuarantineRepository + 03:15 retention cron; operational half of D-02 closed)
last_updated: "2026-04-29T06:42:00.000Z"
last_activity: 2026-04-29 — 25-03 complete; QuarantineRepository.insert/cleanup_older_than + APScheduler dq_quarantine_cleanup cron (CronTrigger 03:15 Asia/Ho_Chi_Minh, max_instances=1, coalesce=True) wired through @observe('dq.quarantine.cleanup'); 4 RED→GREEN
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 24
  completed_plans: 19
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agent tự động phân tích và xếp hạng cổ phiếu HOSE — cho tôi danh sách gợi ý đáng mua kèm lý do rõ ràng, cập nhật hàng ngày, không tốn phí API.
**Current focus:** v1.5 Performance & Data Quality — Phase 22 Logging Foundation (entry point per A→B→C→D→E→F→G build order)

## Current Position

Phase: 25 — Data Quality (🚧 in progress; Wave 1 complete)
Plan: 03 (complete) — DQ-08 QuarantineRepository + 30-day retention cron landed.
Status: 25-03 complete — QuarantineRepository.insert (with sanitize_jsonb belt-and-suspenders) + cleanup_older_than(days=30) over quarantine_rows; APScheduler dq_quarantine_cleanup CronTrigger hour=3 minute=15 Asia/Ho_Chi_Minh max_instances=1 coalesce=True (Pitfall F), decorated with @observe('dq.quarantine.cleanup'). Operational half of CONTEXT D-02 closed; producer wiring lands in 25-05.
Last activity: 2026-04-29 — 25-03 Wave 1 plan B: 2 commits, 3 files, 4/4 RED→GREEN, ruff clean.

Progress: [████████░░] 79%

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
