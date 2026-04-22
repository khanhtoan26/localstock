---
phase: 11
slug: admin-api-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | apps/prometheus/pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_api/test_admin.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_api/test_admin.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | ADMIN-01 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_add_stock` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | ADMIN-02 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_remove_stock` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | ADMIN-03 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_trigger_crawl` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | ADMIN-03 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_trigger_analyze` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | ADMIN-03 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_trigger_pipeline` | ❌ W0 | ⬜ pending |
| 11-02-04 | 02 | 1 | ADMIN-04 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_trigger_report` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | ADMIN-04 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_list_jobs` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 1 | ADMIN-04 | — | N/A | unit | `uv run pytest tests/test_api/test_admin.py::test_get_job_detail` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api/test_admin.py` — stubs for ADMIN-01 through ADMIN-04
- [ ] Test fixtures for mock DB session and services

*Existing infrastructure covers test framework and conftest basics.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
