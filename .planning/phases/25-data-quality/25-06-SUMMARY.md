---
phase: 25-data-quality
plan: 06
subsystem: dq.isolation
tags: [dq, isolation, sc3-closed, dq-05]
requires: [25-01, 25-04, 25-05]
provides:
  - "Per-symbol try/except isolation across analysis_service, scoring_service, sentiment_service, admin_service, report_service, finance_crawler"
  - "AnalysisService/ScoringService/SentimentService/ReportService.get_failed_symbols(reset=True) — drainable {symbol,step,error} buffer for AutomationService aggregation"
  - "Pipeline.run_full failed_symbols dedup keyed on (symbol, step) tuple — CONTEXT D-03 step-level granularity"
  - "Pitfall A guardrail test (test_no_gather_in_per_symbol_loops) — fails CI if asyncio.gather is added over per-symbol loops"
  - "ROADMAP Success Criterion #3 ✅ closed (jointly with 25-04 DQ-06)"
affects:
  - apps/prometheus/src/localstock/services/analysis_service.py
  - apps/prometheus/src/localstock/services/scoring_service.py
  - apps/prometheus/src/localstock/services/sentiment_service.py
  - apps/prometheus/src/localstock/services/admin_service.py
  - apps/prometheus/src/localstock/services/report_service.py
  - apps/prometheus/src/localstock/services/pipeline.py
  - apps/prometheus/src/localstock/crawlers/finance_crawler.py
  - apps/prometheus/tests/test_services/test_pipeline_isolation.py
tech-stack:
  added: []
  patterns:
    - "Serial per-symbol try/except (NOT asyncio.gather) — CONTEXT D-03 LOCKED"
    - "Per-service _failed_symbols buffer + get_failed_symbols(reset=True) drain pattern"
    - "Structured warning logs: {symbol, step, exception_class, message[:200]} — Phase 22 OBS-01 vocabulary"
key-files:
  created: []
  modified:
    - apps/prometheus/src/localstock/services/analysis_service.py
    - apps/prometheus/src/localstock/services/scoring_service.py
    - apps/prometheus/src/localstock/services/sentiment_service.py
    - apps/prometheus/src/localstock/services/admin_service.py
    - apps/prometheus/src/localstock/services/report_service.py
    - apps/prometheus/src/localstock/services/pipeline.py
    - apps/prometheus/src/localstock/crawlers/finance_crawler.py
    - apps/prometheus/tests/test_services/test_pipeline_isolation.py
decisions:
  - "Pipeline.run_full failed_symbols dedup keyed on (symbol, step) tuple — CONTEXT D-03 step-level granularity (was symbol-only in 25-04 transitional shape)"
  - "AutomationService caller-side aggregation contract — analyze/score/sentiment/report buffers drained via svc.get_failed_symbols(reset=True); Pipeline.run_full only aggregates crawl-step failures (Q-3 scope)"
  - "RESEARCH Open Q4 closed: report_service.py:137 IS a per-symbol loop (`for score in scores:` where symbol = score.symbol). Already isolated in try/except; now appends to _failed_symbols buffer with step='report'"
  - "Pitfall A guardrail (test_no_gather_in_per_symbol_loops) — comment-skipping inspection fails CI if any service module adds `asyncio.gather` near `symbol` token. Bounded concurrency deferred to Phase 27"
metrics:
  duration: ~30 minutes
  completed: 2026-04-29
---

# Phase 25 Plan 06: DQ-05 Per-Symbol Error Isolation Summary

Wrap every per-symbol loop across services + crawlers in serial try/except so one bad symbol cannot abort the batch — failures are buffered as `{symbol, step, error: _truncate_error(e)}` and aggregated into `PipelineRun.stats.failed_symbols`. Closes ROADMAP Success Criterion #3.

## What Landed

**Task 1 — analysis/scoring/sentiment service isolation** (commit `67595f5`):
- Added `from localstock.services.pipeline import _truncate_error` to all 3 services (no circular: pipeline.py does not import any of them).
- Added `self._failed_symbols: list[dict] = []` to each service `__init__` and `get_failed_symbols(reset=True) -> list[dict]` drain method.
- `analysis_service.py`:
  - Existing per-symbol except blocks at lines 119 (technical) and 129 (fundamental) now log structured `{symbol, step='analyze', exception_class, message}` and append to buffer.
  - **Wrapped previously-unisolated** `_compute_all_industry_averages` per-symbol reads at lines 456 (`for symbol in symbols`) and 474 (`for sym in symbols`) — group ratio fetch and first-ratio lookup.
- `scoring_service.py`:
  - Existing run_full per-symbol except (line 79 loop body) buffers as `step='score'`.
  - **Wrapped previously-unisolated** `get_top_stocks` per-symbol report lookup at line 176.
- `sentiment_service.py`:
  - Existing classify-loop except (line 100 ticker iteration) buffers as `step='sentiment'`.
  - **Wrapped previously-unisolated** `_get_funnel_candidates` per-symbol indicator/ratio reads at line 145.

**Task 2 — admin/report/finance + pipeline aggregation** (commit `16825a1`):
- `admin_service.py`: Added `_truncate_error` import. The 5 cited loops (lines 115, 164, 191, 207, 228) already had try/except — adapted log shape to structured fields and replaced `str(e)` in result dicts with `_truncate_error(e)`. Step labels: `admin.crawl`, `admin.report`, `admin.pipeline.crawl`, `admin.pipeline.analyze`, `admin.pipeline.report`.
- `report_service.py`:
  - Added `_truncate_error` import + `_failed_symbols` buffer + `get_failed_symbols`.
  - Existing per-symbol except at line 344 (the `for score in scores:` loop) now logs structured + appends `{symbol, step='report', error}` to buffer.
- `finance_crawler.py:109`: Verified isolated, added DQ-05 audit comment.
- `pipeline.py`: Tightened failed_symbols aggregation dedup to `(symbol, step)` tuple per CONTEXT D-03 step-level granularity (was symbol-only in 25-04 transitional code). Updated docstring documenting AutomationService caller-side aggregation contract.

**Task 3 — RED→GREEN tests + Pitfall A guardrail** (commit `412d736`):
- Replaced `requires_pg` placeholders in `test_pipeline_isolation.py` with 4 GREEN tests using AsyncMock-session harness (no Postgres dependency, sibling pattern from `test_pipeline_step_timing.py`):
  1. `test_one_bad_symbol_completes_batch` — SC #3 verbatim
  2. `test_failed_symbols_step_recorded` — `{symbol, step, error}` keyset
  3. `test_analyze_step_isolation` — AnalysisService run_full with one bad symbol
  4. `test_no_gather_in_per_symbol_loops` — Pitfall A guardrail (inspects 5 service modules, fails if any non-comment line contains both `asyncio.gather` and `symbol`)

## Audit-List Closure (RESEARCH §Audit List D-03)

| File | Line | Status before | Status after | Step label |
|------|------|---------------|--------------|-----------|
| `services/pipeline.py:341` (`_crawl_prices`) | KEEP — already isolated | unchanged loop body; structured log via existing T-25-04-01 path | `crawl` |
| `services/analysis_service.py:119` (technical) | try/except already | + buffer append + structured log | `analyze` |
| `services/analysis_service.py:129` (fundamental) | try/except already | + buffer append + structured log | `analyze` |
| `services/analysis_service.py:456` (industry avg ratios) | **unwrapped** | wrapped + buffer | `analyze` |
| `services/analysis_service.py:474` (first ratio) | **unwrapped** | wrapped + buffer | `analyze` |
| `services/scoring_service.py:79` (run_full) | try/except already | + buffer + structured log | `score` |
| `services/scoring_service.py:176` (get_top_stocks) | **unwrapped** | wrapped + buffer | `score` |
| `services/sentiment_service.py:100` (classify) | try/except already | + buffer + structured log | `sentiment` |
| `services/sentiment_service.py:145` (funnel) | **unwrapped** | wrapped + buffer | `sentiment` |
| `services/admin_service.py:115` (run_crawl) | try/except already | + structured log + `_truncate_error` in result | `admin.crawl` |
| `services/admin_service.py:164` (run_report) | try/except already | + structured log + `_truncate_error` in result | `admin.report` |
| `services/admin_service.py:191` (run_pipeline crawl) | try/except already | + structured log + `_truncate_error` | `admin.pipeline.crawl` |
| `services/admin_service.py:207` (run_pipeline analyze) | try/except already | + structured log + `_truncate_error` | `admin.pipeline.analyze` |
| `services/admin_service.py:228` (run_pipeline report) | try/except already | + structured log + `_truncate_error` | `admin.pipeline.report` |
| `services/report_service.py:137` (Open Q4) | **per-symbol loop confirmed; try/except already** | + buffer append + structured log | `report` |
| `crawlers/finance_crawler.py:109` (fetch_batch) | KEEP — already isolated | + DQ-05 audit comment | `crawl` |
| `crawlers/base.py:39` (BaseCrawler.fetch_batch) | KEEP — already isolated | unchanged | `crawl` |

## Open Question Q4 — Resolution

`report_service.py` **does** contain a per-symbol loop:

```python
# services/report_service.py:137
for score in scores:
    symbol = score.symbol
    try:
        # ... gather data, generate, store ...
    except Exception as e:
        # line 344
```

The loop iterates over `Score` rows from `score_repo.get_top_ranked()` and was already isolated in try/except. 25-06 added `_truncate_error` formatting + the `_failed_symbols` buffer drain pattern + structured logging fields. RESEARCH Open Q4 closed.

## ROADMAP SC #3 — Verbatim Closure

> Pipeline with one symbol injecting an error completes the full run; PipelineRun.stats shows `{succeeded: 399, failed: 1, failed_symbols: [...]}` instead of aborting.

`test_one_bad_symbol_completes_batch` asserts the verbatim contract with N=3 symbols (1 BAD, 2 GOOD): `run.status == "completed"`, `stats["succeeded"] == 2`, `stats["failed"] == 1`, `bad_symbols == {"BAD"}`, `"crawl" in bad_steps`. The aggregation generalizes to N=400. SC #3 ✅ **CLOSED** (jointly with 25-04 DQ-06).

## Verification

```bash
cd apps/prometheus
uv run pytest tests/test_services/test_pipeline_isolation.py -x -q
# 4 passed in 0.72s

uv run pytest tests/test_services/ -x -q
# 62 passed (58 sibling + 4 isolation) in ~2s

uv run pytest tests/test_services/ tests/test_db/ tests/test_observability/ \
  tests/test_dq/test_quarantine_repo.py tests/test_dq/test_sanitizer.py \
  tests/test_dq/test_ohlcv_schema.py -q --timeout=10
# 184 passed, 1 failed (test_migration_24_pipeline_durations.py — Phase-24
# pre-existing failure noted in prompt; not a 25-06 regression)
```

Full-suite Phase-25 RED scaffolds (`test_tier2_dispatch.py` × 4, `test_health_data_freshness.py` × 3) remain RED — they belong to 25-07 (DQ-02/03 Tier 2) and 25-08 (DQ-07 freshness probes). Untouched per prompt.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Tightened pipeline.py failed_symbols dedup to `(symbol, step)` tuple**
- **Found during:** Task 2
- **Issue:** 25-04's transitional aggregation deduped on `symbol` only — silently swallowed multi-step failures (a symbol failing in both crawl AND finance crawls would record only once).
- **Fix:** Replaced `seen: set[str]` with `seen_pairs: set[tuple[str, str]]` + separate `failed_symbol_set: set[str]` for the failed-counter tally. Aligns with CONTEXT D-03 "step-level granularity" requirement and the must_have "deduped on (symbol, step) tuple — one symbol can fail in multiple steps and each is recorded separately".
- **Files modified:** `apps/prometheus/src/localstock/services/pipeline.py`
- **Commit:** `16825a1`

### Acceptance Criteria — Plan Note

The plan acceptance for Task 1 said "all 3 services import `_truncate_error` and append to a `_failed_symbols` buffer" + "all cited loop lines now in try/except". Both satisfied:
- `grep -l _truncate_error src/localstock/services/{analysis,scoring,sentiment}_service.py` → all 3 match.
- All cited audit lines are in try/except (4 were already wrapped, 4 newly wrapped per the table above).

The verify command `! grep -nE "asyncio\.gather\(.*for.*in" ...` passes — zero matches.

## Commits

| Hash | Type | Subject |
|------|------|---------|
| `67595f5` | feat | per-symbol try/except isolation in analysis/scoring/sentiment services (DQ-05) |
| `16825a1` | feat | per-symbol isolation in admin/report services + finance_crawler verify + pipeline aggregation contract (DQ-05) |
| `412d736` | test | turn DQ-05 isolation tests GREEN + add Pitfall A guardrail (SC #3) |

All commits include `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer.

## Self-Check: PASSED

- [x] `apps/prometheus/src/localstock/services/analysis_service.py` exists & contains `_truncate_error`
- [x] `apps/prometheus/src/localstock/services/scoring_service.py` exists & contains `_truncate_error`
- [x] `apps/prometheus/src/localstock/services/sentiment_service.py` exists & contains `_truncate_error`
- [x] `apps/prometheus/src/localstock/services/admin_service.py` contains `_truncate_error`
- [x] `apps/prometheus/src/localstock/services/report_service.py` contains `_truncate_error` + `_failed_symbols`
- [x] `apps/prometheus/src/localstock/services/pipeline.py` `seen_pairs` dedup landed
- [x] `apps/prometheus/src/localstock/crawlers/finance_crawler.py` DQ-05 comment landed
- [x] `apps/prometheus/tests/test_services/test_pipeline_isolation.py` 4 GREEN tests
- [x] Commits `67595f5`, `16825a1`, `412d736` exist on master
- [x] `test_pipeline_isolation.py` — 4 passed
- [x] `test_services/` excluding isolation — 58 passed
- [x] No `asyncio.gather` over per-symbol generators in any touched service module (Pitfall A guardrail asserts this)
- [x] ROADMAP SC #3 verbatim contract verified by `test_one_bad_symbol_completes_batch`
