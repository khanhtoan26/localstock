---
phase: 22
slug: logging-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-04-23
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (auto mode) |
| **Config file** | apps/prometheus/pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest apps/prometheus/tests/test_observability/ -x` |
| **Full suite command** | `uv run pytest apps/prometheus/tests/ -x` |
| **Estimated runtime** | ~30s (quick) / ~120s (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command (logging tests)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green + `grep -rE 'logger\.[a-z]+\(f"' apps/prometheus/src/` returns 0
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | OBS-01 | — | All log lines parseable as JSON | unit | `pytest tests/test_observability/test_json_format.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OBS-02 | — | request_id propagated cross-module | integration | `pytest tests/test_observability/test_request_id.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OBS-03 | — | run_id present in pipeline logs | integration | `pytest tests/test_observability/test_run_id.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OBS-04 | T-22-01 | Request log middleware emits method/path/status/duration_ms | integration | `pytest tests/test_observability/test_request_log.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OBS-05 | — | Tokens/passwords/auth headers redacted as `***` | unit | `pytest tests/test_observability/test_redaction.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | OBS-06 | — | CI lint catches f-string logger calls | shell | `bash scripts/lint-no-fstring-logs.sh` | ❌ W0 | ⬜ pending |

*Final task IDs will be assigned by the planner. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/prometheus/tests/test_observability/__init__.py` — package marker
- [ ] `apps/prometheus/tests/test_observability/conftest.py` — `loguru_caplog` fixture (per D-08)
- [ ] `apps/prometheus/tests/test_observability/test_json_format.py` — stubs for OBS-01
- [ ] `apps/prometheus/tests/test_observability/test_request_id.py` — stubs for OBS-02
- [ ] `apps/prometheus/tests/test_observability/test_run_id.py` — stubs for OBS-03
- [ ] `apps/prometheus/tests/test_observability/test_redaction.py` — stubs for OBS-04 (also covers diagnose=False regression)
- [ ] `apps/prometheus/tests/test_observability/test_intercept.py` — stubs for OBS-05
- [ ] `apps/prometheus/scripts/lint-no-fstring-logs.sh` — CI lint shell script

*Framework already installed; only test files + lint script are new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Production stdout JSON parseability | OBS-01 | Requires running app + log shipper | Start uvicorn, hit endpoint, pipe stdout through `jq .` and confirm zero parse errors |
| Daily pipeline run_id in real logs | OBS-03 | Pipeline takes hours, async background | Trigger `/api/automation/run`, then `grep run_id=<uuid> logs/*` confirms full run trace |

*All other behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
