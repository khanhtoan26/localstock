---
phase: 19
slug: prompt-schema-restructuring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd apps/prometheus && python -m pytest tests/test_reports/test_generator.py tests/test_ai/test_client.py -q` |
| **Full suite command** | `cd apps/prometheus && python -m pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/prometheus && python -m pytest tests/test_reports/test_generator.py tests/test_ai/test_client.py -q`
- **After every plan wave:** Run `cd apps/prometheus && python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | PROMPT-02 | — | N/A | unit | `pytest tests/test_reports/test_generator.py -k "backward" -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 0 | PROMPT-04 | T-19-01 | Rejects hallucinated prices | unit | `pytest tests/test_reports/test_generator.py -k "validate_price" -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 0 | PROMPT-03 | — | N/A | unit | `pytest tests/test_reports/test_generator.py -k "format_signal" -x` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 1 | PROMPT-01 | — | N/A | unit | `pytest tests/test_ai/test_client.py -k "correct_params" -x` | ✅ (update) | ⬜ pending |
| 19-02-02 | 02 | 1 | PROMPT-02 | — | N/A | unit | `pytest tests/test_reports/test_generator.py -k "TestStockReportModel" -x` | ✅ (update) | ⬜ pending |
| 19-03-01 | 03 | 1 | PROMPT-03 | — | N/A | unit | `pytest tests/test_reports/test_generator.py -k "section_markers" -x` | ✅ (add check) | ⬜ pending |
| 19-03-02 | 03 | 1 | PROMPT-03 | — | N/A | unit | `pytest tests/test_reports/test_generator.py -k "TestReportDataBuilder" -x` | ✅ (extend) | ⬜ pending |
| 19-04-01 | 04 | 2 | PROMPT-04 | T-19-01 | Nulls invalid prices | unit | `pytest tests/test_reports/test_generator.py -k "validate_price" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reports/test_generator.py::TestStockReportBackwardCompat` — stubs for PROMPT-02 backward compat
- [ ] `tests/test_reports/test_generator.py::TestValidatePriceLevels` — stubs for PROMPT-04 (ordering, range, partial null)
- [ ] `tests/test_reports/test_generator.py::TestFormatSignals` — stubs for signal serialization helpers
- [ ] Update `test_exactly_9_fields` → `test_exactly_15_fields`
- [ ] Update `test_calls_chat_with_correct_params` assertion: `num_ctx == 8192`
- [ ] Update `test_under_3000_chars` threshold to ~4000

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ollama anyOf handling with Qwen2.5 | PROMPT-02 | Requires live Ollama + GPU | Generate report for VCB; check new fields are `null` or valid floats |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
