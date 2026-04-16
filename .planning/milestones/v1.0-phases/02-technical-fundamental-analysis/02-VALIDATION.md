---
phase: 02
slug: technical-fundamental-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-07-17
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 + pytest-asyncio 0.26.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `uv run pytest tests/ -v --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ -v --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | TECH-01..04, FUND-01..03 | unit | `uv run python -c "from localstock.db.models import TechnicalIndicator, FinancialRatio, IndustryGroup"` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | TECH-01..04, FUND-01..03 | unit | `uv run python -c "from localstock.db.repositories.indicator_repo import IndicatorRepository"` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | TECH-01..04, FUND-01..03 | integration | `uv run alembic upgrade head` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | TECH-01, TECH-02 | unit | `uv run pytest tests/test_analysis/test_technical.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | TECH-03, TECH-04 | unit | `uv run pytest tests/test_analysis/test_trend.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | FUND-01, FUND-02 | unit | `uv run pytest tests/test_analysis/test_fundamental.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | FUND-03 | unit | `uv run pytest tests/test_analysis/test_industry.py -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 3 | TECH-01..04, FUND-01..03 | unit | `uv run pytest tests/test_services/test_analysis_service.py -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 3 | TECH-01..04, FUND-01..03 | unit | `uv run python -c "from localstock.api.routes.analysis import router"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis/` directory — new test directory for Phase 2
- [ ] `tests/test_analysis/__init__.py` — package marker
- [ ] `tests/test_analysis/test_technical.py` — covers TECH-01, TECH-02
- [ ] `tests/test_analysis/test_trend.py` — covers TECH-03, TECH-04
- [ ] `tests/test_analysis/test_fundamental.py` — covers FUND-01, FUND-02
- [ ] `tests/test_analysis/test_industry.py` — covers FUND-03
- [ ] `tests/test_services/test_analysis_service.py` — covers service orchestration

*Existing infrastructure covers pytest framework and conftest setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alembic migration applies cleanly to live Supabase | TECH-01..FUND-03 | Requires live DB connection | Run `uv run alembic upgrade head` against Supabase |
| Indicators computed for all ~400 HOSE stocks | TECH-01 | Requires live data + long runtime | Run `AnalysisService.run_full()` and check row counts |
| Industry averages match manual calculation | FUND-03 | Requires real financial data | Compare API output with manual spreadsheet check |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
