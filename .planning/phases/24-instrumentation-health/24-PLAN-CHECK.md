# Phase 24 — Plan Check Report

**Phase**: 24-instrumentation-health
**Plans verified**: 6 (24-01..24-06)
**Methodology**: Goal-backward verification against ROADMAP success criteria, CONTEXT.md decisions (D-01..D-10), VALIDATION.md (27 tests), RESEARCH.md (incl. Open Q-1..Q-5).

---

## Verdict: **NEEDS_REVISION**

- **1 BLOCKER** (B-1): scope reduction on `@observe` rollout
- **3 WARNINGS** (W-1..W-3): D-08 boundary docs, RESEARCH Open Questions marker, Wave-2 dep slack
- All other dimensions PASS

---

## Coverage Table — ROADMAP Success Criteria → Plan/Test

| # | Success Criterion | Plan(s) | Test(s) | Status |
|---|---|---|---|---|
| SC-1 | `@observe("crawl.ohlcv.fetch")` shows in `/metrics` + log line | 24-01 (defines), 24-06 (uses via `_step_timer` emitting `op_duration_seconds{domain="pipeline",subsystem="step",action="crawl"}`) | `test_observe_sync_success`, `test_observe_async_success`, `test_observe_*_reraises_*`, `test_pipeline_run_persists_step_durations` | ⚠️ Histogram appears under different labels than literal example — see B-1 |
| SC-2 | Slow query > 250ms emits `slow_query` log + counter | 24-03 | `test_slow_query_emits_log_and_counter`, `test_fast_query_does_not_trigger_slow_log` | ✅ |
| SC-3 | 4 health probes incl. `/health/ready` 503 on DB unhealthy | 24-04 | `test_health_live_returns_200`, `test_health_ready_503_when_db_ping_fails`, `test_health_ready_200_with_pool_stats`, `test_health_pipeline_returns_age_seconds`, `test_health_data_returns_freshness`, `test_health_legacy_alias_has_deprecation_header` | ✅ |
| SC-4 | Scheduler job error → counter + Telegram alert | 24-05 | `test_job_error_increments_counter`, `test_job_error_sends_telegram_alert`, `test_job_error_dedup_within_window`, `test_different_error_types_not_deduped` | ✅ |
| SC-5 | PipelineRun has all 4 `*_duration_ms` populated | 24-02 (schema) + 24-06 (population) | `test_migration_upgrade_adds_columns`, `test_migration_downgrade_removes_columns`, `test_pipeline_run_persists_step_durations`, `test_step_timer_records_duration_on_exception` | ⚠️ `score_duration_ms` and `report_duration_ms` left NULL by Q-3 design — documented in 24-06 truths #6 |

**Requirement coverage** (OBS-11..17 → frontmatter `requirements:` field):
- OBS-11 → 24-01 ✓ · OBS-12 → 24-03 ✓ · OBS-13 → 24-03 ✓ · OBS-14 → 24-04 ✓ · OBS-15 → 24-05 ✓ · OBS-16 → 24-05 ✓ · OBS-17 → 24-02, 24-06 ✓

**Nyquist sufficiency**: VALIDATION.md lists 27 distinct tests. All 27 are produced by some plan task. 24-01 adds 2 bonus tests (`test_observe_log_false_suppresses_log_but_emits_metric`, `test_timed_query_emits_op_metric`) for a total of 28. ✅

---

## Decision Adherence — D-01..D-10

| ID | Decision | Plan(s) | Status | Notes |
|---|---|---|---|---|
| D-01 | `@observe` sync+async dual via `inspect.iscoroutinefunction`; 3-token name validation at decoration time; re-raise; lives in `observability/decorators.py` NEW | 24-01 | ⚠️ PARTIAL | Decorator defined correctly. **But application scope is reduced** — see B-1. CONTEXT D-01 lists "scheduler jobs (`scheduler.py`) + pipeline step methods + key crawler entry points (`crawlers/*.py` `.fetch`)" as initial scope. Plans only cover pipeline step methods (via 24-06 context manager, not even the decorator itself). No plan applies `@observe` to `daily_job` or any crawler `.fetch`. |
| D-02 | `Settings.slow_query_threshold_ms: int = Field(default=250, ge=1, le=10000)` | 24-03 Step D | ✅ | Pydantic Field with bounds 1..10000 |
| D-03 | 4 endpoints + `/health` deprecated alias; **single** `health.py` file | 24-04 truth #9 | ✅ | Truth: "Single file health.py contains all 4 endpoints + alias — NO splitting" |
| D-04 | Listener attached to `engine.sync_engine`; idempotent; Alembic skip | 24-03 truths #1-5 | ✅ | Truth #1 explicit: "registers on engine.sync_engine, NOT on the AsyncEngine itself" + Pitfall 2 reference |
| D-05 | New gauges go into existing `metrics.py` via `_register` (single-file rule) | 24-05 Task 1 | ✅ | All 5 new primitives (1 Counter + 4 Gauges) added inside `init_metrics()` via existing `_register` helper. Phase 23 `EXPECTED_FAMILIES`/`EXPECTED_LABELS` updated. No new metrics file. |
| D-06 | 15-min dedup; `threading.Lock`; fire-and-forget Telegram via `asyncio.create_task`; different `(job_id, error_type)` not deduped together | 24-05 truths #7-10 | ✅ | `_DEDUP_WINDOW = timedelta(minutes=15)` exact (verified by Task 3 acceptance). `threading.Lock` justified per RESEARCH Pitfall 4 (defensive against worker-thread dispatch). 4 dedup tests cover same-key dedup AND distinct-error-type non-dedup. |
| D-07 | Migration adds 4 nullable Integer columns; reversible | 24-02 Task 1 | ✅ | `upgrade()` adds 4 cols; `downgrade()` drops in reverse order. Round-trip test in Task 2. `down_revision = "f11a1b2c3d4e"` (verified Phase 11 head). |
| D-08 | `_step_timer` records duration on exception (try/yield/except/finally) | 24-06 Task 2 Step B | ✅ | Code skeleton uses correct ordering: `try / yield / except (set fail, raise) / finally (record duration + observe)`. Pitfall 7 cited explicitly. Test `test_step_timer_records_duration_on_exception` covers it. |
| D-09 | pg_sleep with `requires_pg` skip marker; fault injection; mock Telegram fixture | 24-02, 24-03, 24-05, 24-06 | ✅ | `requires_pg` marker registered in 24-03 Task 1 Step A (`pyproject.toml`). `mock_telegram_send` fixture added in 24-05 Task 2 Step A. Fault injection used in OBS-16 + OBS-14 503 test. |
| D-10 | Wave 1: {24-01, 24-02} parallel; Wave 2: {24-03, 24-04}; Wave 3: {24-05, 24-06} | All | ✅ | Frontmatter `wave:` and `depends_on:` match D-10 exactly. |

---

## Wave / Dependency Correctness

| Plan | Wave | depends_on | Files modified (key) |
|---|---|---|---|
| 24-01 | 1 | `[]` | `observability/decorators.py` (NEW), `observability/__init__.py` |
| 24-02 | 1 | `[]` | `alembic/versions/24a1b2c3d4e5_*.py` (NEW), `db/models.py` |
| 24-03 | 2 | `[24-01]` | `observability/db_events.py` (NEW), `db/database.py`, `observability/metrics.py`, `config.py`, `.env.example`, `pyproject.toml` |
| 24-04 | 2 | `[]` | `api/routes/health.py` |
| 24-05 | 3 | `[24-01, 24-04]` | `scheduler/health_probe.py` (NEW), `scheduler/error_listener.py` (NEW), `scheduler/scheduler.py`, `observability/metrics.py` |
| 24-06 | 3 | `[24-01, 24-02]` | `services/pipeline.py` |

**Dep graph valid**: ✅ no cycles, no forward refs, all referenced plans exist.

**File overlap analysis (write-conflict risk per wave):**
- Wave 1: 24-01 vs 24-02 — disjoint file sets ✅
- Wave 2: 24-03 vs 24-04 — disjoint ✅
- Wave 3: 24-05 vs 24-06 — disjoint ✅
- **Cross-wave on `observability/metrics.py`**: 24-03 (W2) AND 24-05 (W3) both modify it. Different waves → serialized. ✅
- **Cross-wave on `tests/test_observability/test_metrics.py`**: same as above. ✅

⚠️ **W-3 (minor)**: 24-04 has `wave: 2` but `depends_on: []`. Strict invariant `wave = max(deps)+1` would put it in Wave 1. CONTEXT D-10 explicitly assigns it to Wave 2 for batching/resource pacing (parallel with 24-03). Tolerable but worth noting — could equally be promoted to Wave 1 to shorten critical path.

---

## Blockers

### B-1 — Scope reduction on `@observe` rollout (Dimension 7b — BLOCKER)

**File**: `.planning/phases/24-instrumentation-health/24-01-PLAN.md` lines 56-58 + objective.

**Issue**: 24-01 explicitly states "THIS PLAN ONLY DEFINES the decorator — retroactive application is out of scope (24-06 wires it into the pipeline step timer; broader sweep deferred to Phase 25 hygiene per Open Q-1)." But:

1. **CONTEXT D-01 lock** (lines 32) lists the initial scope explicitly:
   > "Files using it (initial scope): scheduler jobs (`scheduler/scheduler.py` job functions), pipeline step methods (`services/pipeline.py:run_full` step calls), key crawler entry points (`crawlers/*.py` top-level fetch functions)."

2. **Q-1 "minimal" scope** (RESEARCH §11) recommendation:
   > "Minimal scope in Phase 24 — apply only to: `daily_job` in `scheduler.py`; the 4 step-timer wrap sites in `Pipeline.run_full` (handled by `_step_timer`, no extra decorator needed); Top-level `PriceCrawler.fetch`, `FinanceCrawler.fetch`, `CompanyCrawler.fetch`, `EventCrawler.fetch`."

3. **Across the 6 plans**: only the step-timer (24-06) is wired. **No plan decorates `daily_job` or any crawler `.fetch()`**. The decorator defined in 24-01 has zero call sites at phase end other than the indirect `_step_timer` reuse of the same histogram.

4. **ROADMAP SC-1** literally requires `@observe("crawl.ohlcv.fetch")` to appear in `/metrics`. Without applying the decorator to a crawler entry point, the label combination `domain="crawl",subsystem="ohlcv",action="fetch"` will never be produced. Only `domain="pipeline",subsystem="step",action="crawl"` appears (via 24-06 context manager). The phase technically does not satisfy SC-1 verbatim.

**Suggested fixes** (pick one):

- **Option A (preferred)** — Add a small Task 3 to 24-05 (or new Wave 3 plan 24-07) applying `@observe(...)` to:
  - `scheduler.daily_job` → `@observe("scheduler.daily.job")`
  - `PriceCrawler.fetch` → `@observe("crawl.ohlcv.fetch")` (matches ROADMAP SC-1 literally)
  - `FinanceCrawler.fetch`, `CompanyCrawler.fetch`, `EventCrawler.fetch` → analogous names
  - 5 LOC each, no new tests required (decorator already covered by 24-01 unit tests; smoke test that `/metrics` exposes the family is enough).
  - This makes 24-05 Wave 3 dependency on 24-01 already correct.

- **Option B** — Update CONTEXT.md D-01 to remove "scheduler jobs + key crawler entry points" from initial scope, AND amend ROADMAP SC-1 to use the `pipeline.step.crawl` label as the demonstration. Requires user re-approval since CONTEXT decisions are locked.

- **Option C** — Accept this gap and explicitly defer to Phase 25 hygiene with a roadmap addendum. Requires changing ROADMAP SC-1 wording (currently the literal example will fail validation).

---

## Warnings

### W-1 — Phase 23 D-08 boundary documentation incomplete in 24-05

**File**: `24-05-PLAN.md`.

**Issue**: 24-05 introduces `.inc()` calls in `scheduler/error_listener.py` and `.set()` calls in `scheduler/health_probe.py`. Both files are inside the Phase 23 D-08 audit roots (`{services,crawlers,scheduler,api}/`). The plan's `<verification>` block does not include the D-08 grep, and there is no acknowledgment that this is a documented exception (24-06 Step D acknowledges its own `.observe()` exception in `services/pipeline.py`).

**Suggested fix**: Add to 24-05 Task 3 Step C a final paragraph:
> "**D-08 boundary documentation**: this plan introduces metric calls (`.inc()`, `.set()`) inside `scheduler/`, which is inside the Phase 23 D-08 audit scope. This is a documented exception (the alternative is to inline-extract every gauge update into `observability/metrics.py`, which would invert the dependency direction). Document in `24-05-SUMMARY.md` D-08 section."

Also append a D-08 grep to 24-05's `<verification>` block matching 24-01 / 24-03 style.

### W-2 — RESEARCH Open Questions section not marked `(RESOLVED)` (Dimension 11)

**File**: `24-RESEARCH.md` line 1133.

**Issue**: Section header reads `## §11. Open Questions` without the `(RESOLVED)` suffix mandated by Dimension 11. Substantively all 5 questions have "Recommendation:" lines and CONTEXT.md locks decisions matching them. Pure hygiene.

**Suggested fix**: Rename the heading to `## §11. Open Questions (RESOLVED)` and append `RESOLVED:` markers to each Q-N body, e.g.:
- `### Q-1: ... — RESOLVED: minimal scope (4 fetches + daily_job + step-timer) — see CONTEXT D-01`
- `### Q-3: ... — RESOLVED: crawl + analyze populated; score/report NULL placeholder — see 24-06 truths`

### W-3 — Wave-2 dep slack on 24-04

**File**: `24-04-PLAN.md` line 7.

**Issue**: `wave: 2` with `depends_on: []` violates the strict `wave = max(deps)+1` invariant. CONTEXT D-10 explicitly assigns it to Wave 2 (parallel with 24-03), so plans match CONTEXT — this is informational only.

**Suggested fix**: Either (a) accept as-is (CONTEXT-driven scheduling decision), or (b) promote 24-04 to Wave 1 to widen Wave-1 parallelism (24-04 has zero shared files with 24-01/24-02 ✓).

---

## Anti-pattern Spot-checks (all PASS)

- ✅ 24-01 only DEFINES decorator, no retroactive sweep (also flagged at B-1 — same root cause)
- ✅ 24-02 has `downgrade()` reversing exact `op.add_column` calls
- ✅ 24-05 dedup logic has 4 dedicated tests: `_increments_counter`, `_sends_telegram_alert`, `_dedup_within_window`, `_different_error_types_not_deduped`
- ✅ 24-06 `_step_timer` records duration before re-raise (try/yield/except/finally ordering verified, RESEARCH Pitfall 7 cited inline)
- ✅ All new metric primitives added inside existing `init_metrics()` via the `_register` helper (24-03 Step B, 24-05 Step A) — no duplicate registries, no new files
- ✅ No `bin/*.py` modifications across all 6 plans
- ✅ No AI-module modifications across all 6 plans
- ✅ Q-5 lint analysis correct: `lint-no-fstring-logs.sh` is regex-based for f-string log calls. New decorator + listener code uses structured kwargs (`logger.info("event", key=val, ...)`), so the script will not flag them. No allowlist edit required. 24-01 Step C's deviation #1 reasoning is sound.

## Boundary Check (Phase 23 D-08)

| Plan | Files in `{services,crawlers,scheduler,api}/` calling `.inc()`/`.observe()`/`.set()` | Acknowledged as exception? |
|---|---|---|
| 24-01 | None (decorators.py is in `observability/`) | N/A ✅ |
| 24-02 | None | N/A ✅ |
| 24-03 | None (db_events.py is in `observability/`) | N/A ✅ |
| 24-04 | None (truth #8: "No log/metric calls inside health.py") | N/A ✅ |
| 24-05 | `scheduler/error_listener.py` (`.inc()`), `scheduler/health_probe.py` (`.set()`) | ❌ NOT acknowledged → W-1 |
| 24-06 | `services/pipeline.py` (`.observe()` inside `_step_timer`) | ✅ acknowledged in Task 2 Step D |

`@observe` calls themselves are NOT scattered randomly — they are confined to the new decorator/listener/timer code, exactly per CONTEXT boundary. ✅

---

## Required Revision Summary

To move to PASSED:

1. **B-1** (must-fix): Resolve `@observe` rollout gap. Recommended: add ~5-LOC application task to 24-05 (or new 24-07) decorating `scheduler.daily_job` + 4 crawler `.fetch()` methods. This makes ROADMAP SC-1's literal example label appear in `/metrics`.
2. **W-1** (should-fix): Append D-08 boundary acknowledgment + grep to 24-05.
3. **W-2** (should-fix): Mark RESEARCH §11 as `(RESOLVED)` with per-Q tags.
4. **W-3** (info): Decide whether to promote 24-04 to Wave 1 (no functional impact).

Once B-1 + W-1 + W-2 are addressed, re-run `/gsd-plan-phase 24 --check` for final gate.

---

## Re-check (after revision)

**Verdict: PASSED**

| Issue | Status | Evidence |
|---|---|---|
| **B-1** — `@observe` rollout scope reduction | **RESOLVED** | 24-05 Task 4 (lines 501-705) decorates concrete targets: `daily_job` closure with `@observe("scheduler.daily.run")` (line 573), and the four crawler classes `PriceCrawler.fetch` / `FinanceCrawler.fetch` / `CompanyCrawler.fetch` / `EventCrawler.fetch` with `@observe("crawl.{ohlcv,financial,company,event}.fetch")` (table at lines 552-555, code skeleton lines 541-546). ROADMAP SC-1 verbatim label `@observe("crawl.ohlcv.fetch")` is present (line 541, 552). New integration test `test_crawl_fetch_emits_op_metric` is producible by Task 4 — full skeleton at lines 596-660 stubs `httpx.AsyncClient.get`, calls `await PriceCrawler().fetch(...)`, asserts `localstock_op_duration_seconds_count{domain="crawl",subsystem="ohlcv",action="fetch",outcome="success"} >= 1`. VALIDATION.md row added (line 12, OBS-11 integration) + SC-1 coverage row updated to cite the new test (line 43). 24-01 cross-references 24-05 Task 4 at lines 57-61. |
| **W-1** — D-08 boundary docs in 24-05 | **RESOLVED** | Explicit `<d8_audit>` block at lines 710-742 enumerates the three call-site clusters: `error_listener.py .inc()` (Task 3 / OBS-16), `health_probe.py .set()` ×4 (Task 3 / OBS-15), `@observe`-induced `.observe()` in `scheduler/scheduler.py` + 4 crawler files (Task 4). Block declares the boundary "lifted in this phase by design", documents lint impact (zero — regex doesn't match), and instructs SUMMARY.md to quote the paragraph. The verification block at lines 752-755 includes the manual D-08 grep with explicit "matches are EXPECTED" comment. |
| **W-2** — RESEARCH §11 (RESOLVED) marker | **RESOLVED** | Header at line 1133 reads `## §11. Open Questions (RESOLVED)`. All five questions Q-1..Q-5 carry a bolded `**RESOLVED:**` paragraph (lines 1147, 1152, 1162, 1168, 1173) cross-linking to the binding CONTEXT decision and/or implementing plan task. Q-1 explicitly cites the new 24-05 Task 4. |

### No regressions

- **24-01 minor edit**: Diff is confined to lines 57-61 of `<objective>` (cross-reference paragraph naming 24-05 Task 4 + Phase 25 deferral). No tasks added/removed, no `must_haves` change, no file list change, no test surface change. Scope strictly preserved. ✅
- **24-02/03/04/06 untouched**: Spot-checked — all original PASS verdicts from the initial check still apply (D-02..D-09 lock evidence unchanged; dep graph unchanged).
- **VALIDATION.md**: One new row added (OBS-11 integration, line 12), SC-1 coverage row enriched (line 43). Test count goes from 27 → 28. Out-of-scope note at line 74 still correctly says "retroactive sweep across ALL service methods" remains deferred (only D-01 initial scope is in-phase). ✅
- **Wave/dep graph**: Unchanged. 24-05 still Wave 3 with `depends_on: [24-01, 24-04]` — Task 4 imports `observability.decorators.observe` which 24-01 produces, so dependency direction is correct. ✅

### New observations (informational only — non-blocking)

1. **24-05 task count = 4** (was 3). Sits at the soft-warning boundary (target 2-3, blocker at 5+). Justified — Task 4 is intrinsically distinct work (apply decorator at call sites) and could not be folded into Tasks 1-3 without conflating concerns. Tolerable.
2. **W-3** (Wave-2 dep slack on 24-04) was informational in the original check and remains untouched. No action expected.
3. The integration test at lines 621-660 monkey-patches `PriceCrawler.fetch` by re-applying `observe(...)` to a stub coroutine, with a `try/finally` restore. This is a slightly unusual pattern (typically one stubs the network layer underneath, not the wrapped method), but it correctly proves "decorator fires at the call site" which is what B-1 demanded. Non-blocking.

**Outcome**: All blockers and should-fix warnings cleared. Phase 24 plans are ready for execution. Run `/gsd-execute-phase 24` to proceed.
