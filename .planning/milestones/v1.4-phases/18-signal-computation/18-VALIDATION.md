---
phase: 18
slug: signal-computation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (auto mode) |
| **Config file** | `apps/prometheus/pyproject.toml` |
| **Quick run command** | `uv run pytest apps/prometheus/tests/test_analysis/test_technical.py apps/prometheus/tests/test_analysis/test_signals.py -x` |
| **Full suite command** | `uv run pytest apps/prometheus/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest apps/prometheus/tests/test_analysis/test_technical.py apps/prometheus/tests/test_analysis/test_signals.py -x`
- **After every plan wave:** Run `uv run pytest apps/prometheus/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_doji_detected -x` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_doji_not_present -x` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_inside_bar_detected -x` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_hammer_detected -x` | ❌ W0 | ⬜ pending |
| 18-01-05 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_shooting_star_detected -x` | ❌ W0 | ⬜ pending |
| 18-01-06 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_engulfing_bullish -x` | ❌ W0 | ⬜ pending |
| 18-01-07 | 01 | 1 | SIGNAL-01 | — | Returns all-False on empty/short df, never raises | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_engulfing_bearish -x` | ❌ W0 | ⬜ pending |
| 18-01-08 | 01 | 1 | SIGNAL-01 | T-18-01 | Returns safe all-False dict, no AttributeError | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeCandlestickPatterns::test_empty_df -x` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | SIGNAL-02 | T-18-02 | Returns None (not raises) for low-liquidity stocks | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_bullish_signal -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 1 | SIGNAL-02 | T-18-02 | Returns None (not raises) for low-liquidity stocks | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_bearish_signal -x` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 1 | SIGNAL-02 | T-18-02 | Returns None (not raises) for low-liquidity stocks | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_neutral_signal -x` | ❌ W0 | ⬜ pending |
| 18-02-04 | 02 | 1 | SIGNAL-02 | T-18-02 | Returns None for avg_volume < 100k, no exception | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_low_liquidity_gate -x` | ❌ W0 | ⬜ pending |
| 18-02-05 | 02 | 1 | SIGNAL-02 | T-18-02 | Returns None when df < 15 rows (NaN guard) | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_short_df -x` | ❌ W0 | ⬜ pending |
| 18-02-06 | 02 | 1 | SIGNAL-02 | — | Output has exactly keys: signal, value, indicator | unit | `uv run pytest tests/test_analysis/test_technical.py::TestComputeVolumeDivergence::test_output_shape -x` | ❌ W0 | ⬜ pending |
| 18-03-01 | 03 | 2 | SIGNAL-03 | — | Returns None for None input, never raises | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_strong_inflow -x` | ❌ W0 | ⬜ pending |
| 18-03-02 | 03 | 2 | SIGNAL-03 | — | Returns None for None input, never raises | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_mild_inflow -x` | ❌ W0 | ⬜ pending |
| 18-03-03 | 03 | 2 | SIGNAL-03 | — | Returns None for None input, never raises | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_mild_outflow -x` | ❌ W0 | ⬜ pending |
| 18-03-04 | 03 | 2 | SIGNAL-03 | — | Returns None for None input, never raises | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_strong_outflow -x` | ❌ W0 | ⬜ pending |
| 18-03-05 | 03 | 2 | SIGNAL-03 | — | Returns None for None input, never raises | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_none_input -x` | ❌ W0 | ⬜ pending |
| 18-03-06 | 03 | 2 | SIGNAL-03 | — | Returns None when avg_score_change is None | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_none_score_change -x` | ❌ W0 | ⬜ pending |
| 18-03-07 | 03 | 2 | SIGNAL-03 | — | Output has keys: label, score_change, group_code | unit | `uv run pytest tests/test_analysis/test_signals.py::TestComputeSectorMomentum::test_output_shape -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/prometheus/tests/test_analysis/test_technical.py` — extend with `TestComputeCandlestickPatterns` (8 tests) and `TestComputeVolumeDivergence` (6 tests) stub classes
- [ ] `apps/prometheus/tests/test_analysis/test_signals.py` — new file with `TestComputeSectorMomentum` (7 tests) stubs
- [ ] `apps/prometheus/src/localstock/analysis/signals.py` — new module file (stub, empty function)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Output is JSON-serializable for LLM prompt injection | SIGNAL-01/02/03 | End-to-end signal→prompt flow requires Phase 19 | Verify by calling `json.dumps(result)` on each signal output in a REPL test |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
