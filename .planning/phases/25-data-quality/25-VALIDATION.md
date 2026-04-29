---
phase: 25
slug: data-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for Phase 25 (Data Quality). Closes ROADMAP
> Success Criteria #1–#5. Framework already exists from Phase 21 (pytest 8.x +
> pytest-asyncio); pandera is the new dependency installed in Wave 0.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + pytest-timeout |
| **Config file** | `apps/prometheus/pyproject.toml` (existing `[tool.pytest.ini_options]`) |
| **Quick run command** | `cd apps/prometheus && uv run pytest -q -k "dq_ or sanitize or quarantine or health_data or pipeline_run_stats or tier2"` |
| **Full suite command** | `cd apps/prometheus && uv run pytest -q` |
| **Estimated runtime** | ~25 s quick / ~3 min full |

---

## Sampling Rate

- **After every task commit:** quick run
- **After every plan wave:** full suite
- **Before `/gsd-verify-work`:** full suite must be green
- **Max feedback latency:** 30 s (quick), 180 s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 0 | DQ-01..08 | T-25-01-01 | pandera installed; dq/ pkg importable | unit | `uv run python -c "import pandera.pandas; import localstock.dq"` | ❌ W0 | ⬜ pending |
| 25-01-02 | 01 | 0 | DQ-06, DQ-08 | — | Alembic migration runs forward + back | integration | `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` | ❌ W0 | ⬜ pending |
| 25-01-03 | 01 | 0 | DQ-01..08 | — | Settings exposes new DQ fields | unit | `uv run pytest tests/test_config/test_dq_settings.py -q` | ❌ W0 | ⬜ pending |
| 25-01-04 | 01 | 0 | DQ-01..08 | — | dq_violations_total counter registered | unit | `uv run pytest tests/test_observability/test_dq_metric.py -q` | ❌ W0 | ⬜ pending |
| 25-01-05 | 01 | 0 | DQ-01..08 | — | RED scaffolds present and FAIL | unit | `uv run pytest tests/test_dq/ -q --collect-only` | ❌ W0 | ⬜ pending |
| 25-02-01 | 02 | 1 | DQ-04 (SC #2) | T-25-02-01 | sanitize_jsonb replaces NaN/inf with None | unit | `uv run pytest tests/test_dq/test_sanitize.py -q` | ❌ W0 | ⬜ pending |
| 25-02-02 | 02 | 1 | DQ-04 | T-25-02-01 | repos use sanitize_jsonb at write | integration | `uv run pytest tests/test_repos/test_jsonb_writes.py -q` | ❌ W0 | ⬜ pending |
| 25-02-03 | 02 | 1 | DQ-04 (SC #2) | — | _clean_nan removed from pipeline.py | static | `! grep -n '_clean_nan' apps/prometheus/src/localstock/services/pipeline.py` | n/a | ⬜ pending |
| 25-03-01 | 03 | 1 | DQ-08 | T-25-03-01 | QuarantineRepository.insert + cleanup_older_than | unit | `uv run pytest tests/test_dq/test_quarantine_repo.py -q` | ❌ W0 | ⬜ pending |
| 25-03-02 | 03 | 1 | DQ-08 | T-25-03-02 | dq_quarantine_cleanup APScheduler job registered | integration | `uv run pytest tests/test_scheduler/test_dq_cleanup_job.py -q` | ❌ W0 | ⬜ pending |
| 25-04-01 | 04 | 2 | DQ-06 (SC #3) | T-25-04-01 | _write_stats dual-writes JSONB + scalars | unit | `uv run pytest tests/test_pipeline/test_pipeline_run_stats.py -q` | ❌ W0 | ⬜ pending |
| 25-04-02 | 04 | 2 | DQ-06 | — | _truncate_error caps to 200 chars | unit | `uv run pytest tests/test_dq/test_truncate_error.py -q` | ❌ W0 | ⬜ pending |
| 25-05-01 | 05 | 3 | DQ-01 (SC #1) | T-25-05-01 | OHLCVSchema rejects bad rows to quarantine | integration | `uv run pytest tests/test_dq/test_ohlcv_validation.py -q` | ❌ W0 | ⬜ pending |
| 25-05-02 | 05 | 3 | DQ-01 (SC #1) | — | _crawl_prices dispatches partition_valid_invalid | integration | `uv run pytest tests/test_pipeline/test_crawl_prices_validation.py -q` | ❌ W0 | ⬜ pending |
| 25-06-01 | 06 | 4 | DQ-05 (SC #3) | T-25-06-01 | per-symbol try/except in analysis_service | unit | `uv run pytest tests/test_services/test_per_symbol_isolation.py::test_analysis -q` | ❌ W0 | ⬜ pending |
| 25-06-02 | 06 | 4 | DQ-05 | T-25-06-01 | per-symbol isolation in scoring/sentiment/admin/finance/report | unit | `uv run pytest tests/test_services/test_per_symbol_isolation.py -q` | ❌ W0 | ⬜ pending |
| 25-06-03 | 06 | 4 | DQ-05 | T-25-06-02 | NO asyncio.gather over per-symbol generators (Pitfall A) | static | `! grep -rn 'asyncio.gather' apps/prometheus/src/localstock/services/ \| grep -i symbol` | n/a | ⬜ pending |
| 25-07-01 | 07 | 5 | DQ-03 (SC #4) | T-25-07-01 | get_tier2_mode reads per-rule env flags | unit | `uv run pytest tests/test_dq/test_tier2_dispatch.py::test_mode_lookup -q` | ❌ W0 | ⬜ pending |
| 25-07-02 | 07 | 5 | DQ-02 (SC #4) | T-25-07-01 | evaluate_tier2 emits metric + does not block in shadow | unit | `uv run pytest tests/test_dq/test_tier2_dispatch.py -q` | ❌ W0 | ⬜ pending |
| 25-07-03 | 07 | 5 | DQ-03 | T-25-07-02 | promotion runbook contains required sections | static | `uv run pytest tests/test_docs/test_runbooks.py -q` | ❌ W0 | ⬜ pending |
| 25-08-01 | 08 | 6 | DQ-07 (SC #5) | T-25-08-03 | /health/data exposes data_freshness block | unit | `uv run pytest tests/test_health/test_health_data_freshness.py -q` | ❌ W0 | ⬜ pending |
| 25-08-02 | 08 | 6 | DQ-07 (SC #5) | T-25-08-03 | Phase 24 back-compat keys preserved | unit | `uv run pytest tests/test_health/test_health_data_freshness.py::test_sc5_health_data_response_shape -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (plan 25-01) MUST land before any Wave 1+ task can be considered
Nyquist-compliant. After 25-01 commits, set `wave_0_complete: true` and
`nyquist_compliant: true` here.

Test files created in Wave 0 (RED scaffolds):

- [ ] `tests/test_dq/test_sanitize.py` — DQ-04 (SC #2)
- [ ] `tests/test_dq/test_quarantine_repo.py` — DQ-08
- [ ] `tests/test_dq/test_truncate_error.py` — DQ-06
- [ ] `tests/test_dq/test_ohlcv_validation.py` — DQ-01 (SC #1)
- [ ] `tests/test_dq/test_tier2_dispatch.py` — DQ-02, DQ-03 (SC #4)
- [ ] `tests/test_repos/test_jsonb_writes.py` — DQ-04
- [ ] `tests/test_scheduler/test_dq_cleanup_job.py` — DQ-08
- [ ] `tests/test_pipeline/test_pipeline_run_stats.py` — DQ-06 (SC #3)
- [ ] `tests/test_pipeline/test_crawl_prices_validation.py` — DQ-01
- [ ] `tests/test_services/test_per_symbol_isolation.py` — DQ-05 (SC #3)
- [ ] `tests/test_health/test_health_data_freshness.py` — DQ-07 (SC #5)
- [ ] `tests/test_observability/test_dq_metric.py` — DQ-01..08
- [ ] `tests/test_config/test_dq_settings.py` — DQ-01..08
- [ ] `tests/test_docs/test_runbooks.py` — DQ-03

Code skeletons created in Wave 0:

- [ ] `localstock/dq/__init__.py` (with `MAX_ERROR_CHARS = 200`)
- [ ] `localstock/dq/sanitizer.py` (stub)
- [ ] `localstock/dq/quarantine.py` (stub)
- [ ] `localstock/dq/runner.py` (`evaluate_tier2` stub)
- [ ] `localstock/dq/shadow.py` (`get_tier2_mode` stub)
- [ ] `localstock/dq/schemas/__init__.py`
- [ ] `localstock/dq/schemas/ohlcv.py` (OHLCVSchema stub)
- [ ] `localstock/dq/schemas/indicators.py` (stub)
- [ ] `localstock/dq/repository.py` (`QuarantineRepository` stub)

Infrastructure created in Wave 0:

- [ ] `pyproject.toml` — `pandera>=0.31,<1.0` added
- [ ] `alembic/versions/25a0b1c2d3e4_phase25_dq_tables.py` — `quarantine_rows` table + `pipeline_runs.stats` JSONB
- [ ] `localstock/config.py` — Settings fields (`dq_default_tier2_mode`, `dq_tier2_{rsi,gap,missing}_mode`, `dq_stale_threshold_sessions`)
- [ ] `localstock/observability/metrics.py` — `localstock_dq_violations_total{rule, tier}` Counter
- [ ] `docs/runbook/dq-tier2-promotion.md` — placeholder (filled in 25-07)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* Tier 2 promotion in
production (DQ-03) requires a human runbook step (env flag flip + redeploy)
but the code path itself is fully tested via per-rule env override fixtures.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (✅ all 22 task rows above resolve to commands)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (✅)
- [ ] Wave 0 covers all MISSING references (✅ — all 14 test files created in 25-01)
- [ ] No watch-mode flags (✅ — all `pytest -q`, no `--ff` in inner loop)
- [ ] Feedback latency < 30 s (quick) / 180 s (full) (✅)
- [ ] `nyquist_compliant: true` set in frontmatter — flips to true after 25-01 lands

**Approval:** pending
