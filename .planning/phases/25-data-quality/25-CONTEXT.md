---
phase: 25
phase_name: Data Quality
phase_slug: data-quality
milestone: v1.5
created: 2026-04-29
updated: 2026-04-29
upstream_deps: [Phase 24 — Instrumentation & Health]
downstream_deps: [Phase 26 Caching, Phase 27 Pipeline Performance, Phase 28 DB Optimization]
requirements: [DQ-01, DQ-02, DQ-03, DQ-04, DQ-05, DQ-06, DQ-07, DQ-08]
---

# Phase 25 Context — Data Quality

## Vision

Pipeline rejects corrupt rows at the boundary instead of silently corrupting downstream consumers. One symbol failing must NOT kill the batch of ~400. Rejected rows are quarantined for inspection/replay rather than silently dropped. `/health/data` flags stale data so downstream cache + automation know to skip a stale snapshot. **Must land before Phase 27 parallelism** — concurrency amplifies whatever DQ holes exist today (research §"D before F").

## Locked Requirements (from REQUIREMENTS.md)

- **DQ-01** Tier 1 validators (block per-symbol) — pandera schemas reject corrupt OHLCV: negative price, future date, NaN ratio > threshold, duplicate (symbol,date) PK
- **DQ-02** Tier 2 advisory validators (warn + metric, no block): RSI > 99.5, gap > 30%, missing rows > 20%
- **DQ-03** Shadow mode default 14 days for Tier 2 rules before allowed promotion to Tier 1 (operational policy documented)
- **DQ-04** NaN/Inf sanitizer at JSONB write boundary — `df.replace([±inf], NaN).where(notna(), None)` applied before every JSONB insert
- **DQ-05** Per-stock try/except isolation in pipeline — one symbol failing does NOT kill batch (`return_exceptions=True`)
- **DQ-06** `PipelineRun.stats` JSONB column records succeeded/failed/skipped count + failed-symbol list
- **DQ-07** Stale-data detection — `/health/data` compares `MAX(date)` against trading-calendar; flags if drift > 1 session
- **DQ-08** Quarantine table for rejected rows — never silently drop; inspectable/replayable

## Success Criteria (verbatim from ROADMAP.md)

1. Pandera Tier 1 rejects OHLCV row with negative price / future date / NaN ratio > threshold / duplicate `(symbol,date)` PK — row goes to `quarantine_rows` table instead of `stock_prices`.
2. JSONB write boundary converts `±Inf` and `NaN` to SQL `NULL` — verified via injected DataFrame with inf, after insert `report.content_json` contains no string `"NaN"` or `"Infinity"`.
3. Pipeline with one symbol injecting an error (raise in crawler) completes the full run; `PipelineRun.stats` JSONB shows `{succeeded: 399, failed: 1, failed_symbols: ["BAD"]}` instead of aborting.
4. Tier 2 advisory rules (RSI > 99.5, gap > 30%, missing > 20%) emit log `dq_warn` + counter `dq_violations_total{rule, tier="advisory"}` but do NOT block — shadow-mode flag default true.
5. `/health/data` returns status `stale` when `MAX(stock_prices.date)` drifts from trading-calendar > 1 session — verified by manual rollback of date.

## Decisions

### D-01 — Pandera schemas live in per-domain modules under `src/localstock/dq/schemas/`

**Decision:** New package `src/localstock/dq/` with sub-package `schemas/` containing `ohlcv.py`, `financials.py`, `indicators.py`. The `dq/` package is the single home for all data-quality concerns (schemas, validators, sanitizer, quarantine repo, shadow-mode dispatcher).

**Why:** Each schema can be unit-tested in isolation; downstream consumers import a single, obvious symbol per domain (e.g., `from localstock.dq.schemas.ohlcv import OHLCVSchema`); avoids a megafile that becomes a merge-conflict hotspot.

**Implications:** Researcher should investigate pandera 0.31's recommended layout for multi-schema projects + how to compose check-only sub-schemas (Tier 1 vs Tier 2 versions of the same OHLCV frame).

---

### D-02 — Quarantine is a single polymorphic `quarantine_rows` table with 30-day retention

**Decision:** New table `quarantine_rows` with columns `(id, source, symbol, payload JSONB, reason, rule, tier, quarantined_at)`. Retention enforced by a daily cron (APScheduler job, runs at off-hours) deleting rows where `quarantined_at < now() - INTERVAL '30 days'`.

**Why:** Polymorphic shape matches the lightweight-stack philosophy (research §STACK.md) — no per-source migration churn. JSONB payload preserves the original row exactly so replay is loss-free. 30-day retention is enough to catch a "data was wrong last week" complaint without unbounded growth.

**Implications:** `source` column should be a small enum-string (`'ohlcv'`, `'financials'`, `'indicators'`) — index it for cheap filtering. APScheduler cleanup job needs Phase 24 `@observe` instrumentation. Replay path is OUT OF SCOPE for Phase 25 (manual SQL is acceptable; automated replay is a v1.6 backlog candidate).

---

### D-03 — Per-stock isolation applies at EVERY per-symbol step (crawl, analyze, score, report)

**Decision:** Each per-symbol step uses `asyncio.gather(*coros, return_exceptions=True)` (or equivalent loop with try/except). Failures are logged with structured fields `{symbol, step, exception_class, message}` and recorded in the run's `failed_symbols` list with the step name (`{"BAD": "crawl"}`) so post-run analysis can see WHERE in the pipeline a symbol died.

**Why:** A single bad ticker should never take down 399 others, regardless of which step trips. Boundary-only isolation (option 2) leaves the analyze/score/report steps batch-failing; top-level only (option 3) loses step-level granularity.

**Implications:** Existing pipeline.py `run_full` and AnalysisService/ScoringService/ReportService.run_full need audit — wherever a `for symbol in symbols:` loop runs without try/except, that's a fix site. Researcher should map every per-symbol loop in `services/` and `crawlers/`. Plan should batch the audit + fix into one or two coordinated plans.

---

### D-04 — NaN/Inf sanitizer lives in the repository layer as a single `_sanitize_jsonb()` helper

**Decision:** New helper `localstock.dq.sanitizer.sanitize_jsonb(value: dict | list | None) -> dict | list | None` (recurses into nested dicts/lists, replaces `float('inf')`, `float('-inf')`, and `NaN` with `None`). Every repository method that writes to a JSONB column calls this helper on the payload BEFORE constructing the SQLAlchemy insert/upsert statement.

**Why:** Repository layer is the chokepoint — every JSONB write goes through a repo today (verified during scout). Single helper = one obvious test target, one source of truth. Service-layer placement is too easy to forget; SQLAlchemy event listener is too invisible (silent magic); pandera-only doesn't cover paths that bypass DataFrames (e.g., LLM JSON outputs).

**Implications:** Researcher must enumerate every repo write to a JSONB column (`stock_reports.content_json`, `pipeline_runs.errors`, `pipeline_runs.stats`, any others). Plan should add a unit test per repo proving sanitize is called. The helper itself gets a property-test (hypothesis) covering nested structures.

---

### D-05 — Stale-data threshold reuses Phase 24's static VN trading-calendar; default = 1 session lag

**Decision:** `/health/data` (extends the 24-04 `/health/data` probe) computes `last_trading_day = max(d for d in VN_TRADING_CALENDAR if d <= today)` (reusing the static 2025–2026 set from 24-04) and reports `status='stale'` if `MAX(stock_prices.date) < last_trading_day - settings.dq_stale_threshold_sessions` (default `1`). Threshold is configurable via env (`DQ_STALE_THRESHOLD_SESSIONS=2` to be more lenient).

**Why:** Reusing the existing calendar avoids two sources of truth. Default of 1 session means a missed daily pipeline shows up immediately; configurable threshold lets ops tune for noisy weekend behavior. The existing `/health/data` probe already exists from Phase 24-04 — this extends it rather than creating a parallel endpoint.

**Implications:** The static calendar set is currently 2025–2026; a 2027+ rollover is a known limitation tracked in 24-04. Researcher should confirm the calendar module location. `/health/data` response needs a new field (e.g., `data_freshness: {last_trading_day, max_data_date, sessions_behind, status}`).

---

### D-06 — Tier 2 shadow mode is per-rule env-flag-driven; metric labels carry the tier always

**Decision:** Each Tier 2 rule has an env flag of the form `DQ_TIER2_<RULE>_MODE=shadow|enforce` (e.g., `DQ_TIER2_RSI_MODE`, `DQ_TIER2_GAP_MODE`, `DQ_TIER2_MISSING_MODE`). A default `DQ_DEFAULT_TIER2_MODE=shadow` covers any unset rule. The `dq_violations_total{rule, tier}` counter ALWAYS emits with `tier="advisory"` for Tier 2 rules in shadow mode, and `tier="strict"` once promoted; this lets dashboards compare violation rates pre/post promotion.

**Why:** Per-rule granularity lets ops promote one rule at a time after the 14-day shadow window; a global flag (option 2) forces all-or-nothing. DB-table config (option 3) adds an unnecessary table for ~3 rules. Metric label discipline ensures Phase 24's dashboards keep working through the promotion.

**Implications:** Settings model (Pydantic `Settings`) needs new fields. Shadow-vs-enforce dispatch is one helper (`def get_tier2_mode(rule_name: str) -> Literal['shadow', 'enforce']`). Promotion runbook (e.g., `docs/runbook/dq-tier2-promotion.md`) is a deliverable in this phase — not just a code change but operational documentation.

---

### D-07 — `PipelineRun.stats` JSONB added; existing scalar columns dual-written for backward compat through v1.5

**Decision:** New column `stats: JSONB | None` on `pipeline_runs` table containing `{succeeded: int, failed: int, skipped: int, failed_symbols: [{"symbol": str, "step": str, "error": str}, ...]}`. Existing scalar columns (`symbols_total`, `symbols_success`, `symbols_failed`) continue to be written (mirrored from `stats`) through v1.5; deprecation + drop happens in v1.6.

**Why:** Anything reading the scalar columns today (UI dashboard, external scripts, possibly a Telegram digest formatter) keeps working without coordinated change. JSONB is forward-compatible — adding a `stats.warnings_count` field later doesn't need a migration.

**Implications:** New Alembic migration. Pipeline orchestrator code that updates the run row needs a single helper to write both shapes. Researcher should grep for any code reading `symbols_total/symbols_success/symbols_failed` to compile the deprecation impact list. Tests verify mirroring is exact.

---

### D-08 — Wave/plan ordering: TDD-first scaffolds → foundations → validators → operational

**Decision:** 5 waves total, mirroring the Phase 22 Nyquist contract (RED tests + lint gates land before any impl):

- **Wave 0** — RED test scaffolds for all DQ-01–DQ-08 + `pandera[pandas]` dependency install + `dq/` package skeleton + Alembic migration for `quarantine_rows` and `pipeline_runs.stats`.
- **Wave 1 (foundations)** — DQ-04 (`sanitize_jsonb` helper + repo wiring) + DQ-08 (`quarantine_rows` repo + retention cron). Parallelizable.
- **Wave 2 (validators + isolation + stats)** — DQ-01 (Tier 1 OHLCV pandera schemas + reject-to-quarantine), DQ-05 (per-step per-symbol isolation audit + fix), DQ-06 (`PipelineRun.stats` write path + dual-write to scalars). Parallelizable but DQ-05 depends on DQ-06's `failed_symbols` schema.
- **Wave 3 (advisory)** — DQ-02 (Tier 2 schemas + dispatcher) + DQ-03 (shadow-mode env flags + runbook). Sequential within wave (DQ-03 wraps DQ-02).
- **Wave 4 (operational)** — DQ-07 (`/health/data` stale extension + tests). Standalone.

**Why:** TDD-first matches the project's established Nyquist pattern. Foundations before validators because validators consume the sanitizer and quarantine repo. Operational last because it depends on stats being written.

**Implications:** Researcher and planner should respect the wave boundaries when designing plan dependencies. Each wave is one or more PLANs; planner decides plan granularity within a wave. `autonomous: true` on most plans; DQ-03 runbook plan likely needs human review (operational doc).

## Out of Scope (Deferred)

These came up implicitly in discussion or are tempting scope creep — explicitly NOT in Phase 25:

- **Automated quarantine replay** — Phase 25 ships the table + manual SQL replay only. Automated "retry the quarantined row" workflow is a v1.6 backlog candidate.
- **Trading-calendar 2027+ extension** — known limitation from 24-04; ROADMAP backlog item.
- **DQ rules for non-OHLCV sources** (news, macro, fund flows) — Phase 25 covers OHLCV (Tier 1) and indicator anomalies (Tier 2). Other sources get their own DQ rules in later phases.
- **Per-symbol rate-limit / throttle** — that's Phase 27 (Pipeline Performance). DQ is about correctness, not concurrency.
- **Replacing scalar `symbols_total/success/failed` with `stats` JSONB outright** — dual-write through v1.5; cleanup in v1.6.
- **Telegram alerting on quarantine spikes** — visible in `dq_violations_total` Prometheus metric; alert routing is a future ops phase.

## Specifics & References

- Pandera version pinned in `.planning/research/STACK.md`: `pandera>=0.31,<1.0` with `[pandas]` extra.
- `_sanitize_jsonb` recipe per RESEARCH Pitfall 10: `df.replace([np.inf, -np.inf], np.nan).where(df.notna(), None)` for DataFrames; recursive `dict`/`list` walk for non-DataFrame payloads (LLM JSON outputs).
- `failed_symbols` JSON shape (D-03 + D-07): `[{"symbol": "BAD", "step": "crawl", "error": "ConnectionError: ..."}]` — keep `error` to first 200 chars to bound JSONB size.
- `/health/data` extension (D-05): keep the existing endpoint's response keys + add `data_freshness` block; frontend (Helios) doesn't currently consume `/health/data`, so no UI work needed in this phase.
- Shadow-mode metric dimension (D-06): `dq_violations_total{rule="rsi_anomaly", tier="advisory"}` always; `tier="strict"` after promotion. Existing Phase 23 metrics primitives in `localstock.observability.metrics` are the registration site.

## Downstream Hand-off Checklist (for gsd-phase-researcher)

- [ ] Investigate pandera 0.31 idioms for split Tier 1 / Tier 2 schema composition.
- [ ] Map every per-symbol loop in `services/`, `crawlers/`, `pipeline.py` (D-03 audit list).
- [ ] Enumerate every repo method writing to a JSONB column (D-04 wiring list).
- [ ] Confirm Phase 24's VN trading-calendar module location + its public API (D-05 reuse).
- [ ] Inventory current readers of `pipeline_runs.symbols_total/success/failed` (D-07 deprecation impact).
- [ ] Verify pandera does NOT pull in heavy transitive deps that conflict with current `pyproject.toml` (cross-check STACK.md compat table).

## Downstream Hand-off Checklist (for gsd-planner)

- [ ] 5-wave structure (D-08); plans inherit `wave` frontmatter.
- [ ] Wave 0 includes pandera install + Alembic migration + RED scaffolds.
- [ ] Wave 1 plans (DQ-04, DQ-08) marked parallelizable.
- [ ] Wave 2 plans encode dependency `DQ-05 depends_on: DQ-06` for `failed_symbols` schema.
- [ ] Wave 3 includes a docs plan for `docs/runbook/dq-tier2-promotion.md` (D-06).
- [ ] Wave 4 (DQ-07) extends `/health/data`, doesn't replace it (D-05).
- [ ] Every plan's `must_haves.truths` references the verbatim Success Criteria #1–#5 from ROADMAP.
