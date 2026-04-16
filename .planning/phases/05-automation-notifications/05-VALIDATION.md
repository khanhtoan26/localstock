---
phase: 5
slug: automation-notifications
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | AUTO-01 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AUTO-02 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | NOTI-01 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | NOTI-02 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SCOR-04 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SCOR-05 | — | N/A | unit | `uv run pytest tests/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_services/test_automation_service.py` — stubs for AUTO-01, AUTO-02
- [ ] `tests/test_services/test_telegram_service.py` — stubs for NOTI-01, NOTI-02
- [ ] `tests/test_services/test_score_change.py` — stubs for SCOR-04
- [ ] `tests/test_services/test_sector_rotation.py` — stubs for SCOR-05

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram messages arrive | NOTI-01, NOTI-02 | Requires live Telegram bot token | Set TELEGRAM_BOT_TOKEN, run pipeline, check channel |
| Scheduler fires at 15:30 | AUTO-01 | Requires waiting for real time | Verify via scheduler logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
