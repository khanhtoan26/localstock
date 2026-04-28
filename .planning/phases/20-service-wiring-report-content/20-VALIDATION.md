---
phase: 20
slug: service-wiring-report-content
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `apps/prometheus/pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_services/test_report_service.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_services/test_report_service.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | TBD | TBD | REPORT-01 | unit | `uv run pytest tests/test_services/test_report_service.py -k entry_zone -x` | ⬜ pending |
| TBD | TBD | TBD | REPORT-02 | unit | `uv run pytest tests/test_services/test_report_service.py -k stop_loss -x` | ⬜ pending |
| TBD | TBD | TBD | REPORT-03 | unit | `uv run pytest tests/test_services/test_report_service.py -k risk_rating -x` | ⬜ pending |
| TBD | TBD | TBD | REPORT-04 | unit | `uv run pytest tests/test_services/test_report_service.py -k signal_conflict -x` | ⬜ pending |
| TBD | TBD | TBD | REPORT-05 | unit | `uv run pytest tests/test_services/test_report_service.py -k catalyst -x` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full report content quality | All | LLM output varies | Run `generate_for_symbol("VCB")` and inspect all 6 new fields are populated |

