---
phase: 1
slug: foundation-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-01-27
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | — | N/A | integration | `uv run pytest tests/test_crawlers/test_price_crawler.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DATA-02 | — | N/A | integration | `uv run pytest tests/test_db/test_price_repo.py -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | DATA-03 | — | N/A | integration | `uv run pytest tests/test_crawlers/test_finance_crawler.py -x` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | DATA-04 | — | N/A | integration | `uv run pytest tests/test_crawlers/test_company_crawler.py -x` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 1 | DATA-05 | — | N/A | unit | `uv run pytest tests/test_services/test_price_adjuster.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project configuration with all dependencies
- [ ] `tests/conftest.py` — shared fixtures (async session, mock vnstock responses)
- [ ] `pyproject.toml [tool.pytest]` — pytest configuration with asyncio mode
- [ ] Framework install: `uv add --dev pytest pytest-asyncio`
- [ ] `tests/test_services/test_price_adjuster.py` — unit tests for price adjustment (pure logic, no I/O)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backfill 2yr history | DATA-02 | Requires live vnstock API + Supabase | Run `python -m localstock.crawlers.backfill` and verify row count |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
