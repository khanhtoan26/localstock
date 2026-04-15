---
phase: 03
slug: sentiment-analysis-scoring-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-07-16
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.26+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest tests/ --timeout=30 -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=30 -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1 | 03-01 | 1 | SENT-01 | RSS tampering | Sanitize HTML | unit | `uv run pytest tests/test_crawlers/test_news_crawler.py -x` | ❌ | pending |
| T2 | 03-02 | 2 | SENT-02 | LLM prompt injection | Truncate input, structured output | integration | `uv run pytest tests/test_analysis/test_sentiment.py -x` | ❌ | pending |
| T3 | 03-02 | 2 | SENT-03 | — | — | unit | `uv run pytest tests/test_analysis/test_sentiment.py::test_aggregate -x` | ❌ | pending |
| T4 | 03-03 | 3 | SCOR-01 | — | — | unit | `uv run pytest tests/test_scoring/test_engine.py -x` | ❌ | pending |
| T5 | 03-03 | 3 | SCOR-02 | — | — | unit | `uv run pytest tests/test_scoring/test_engine.py::test_weights -x` | ❌ | pending |
| T6 | 03-03 | 3 | SCOR-03 | — | — | unit | `uv run pytest tests/test_scoring/test_engine.py::test_ranking -x` | ❌ | pending |

---

## Wave 0 Gaps

- [ ] `tests/test_crawlers/test_news_crawler.py` — covers SENT-01
- [ ] `tests/test_analysis/test_sentiment.py` — covers SENT-02, SENT-03
- [ ] `tests/test_scoring/__init__.py` — new test directory
- [ ] `tests/test_scoring/test_engine.py` — covers SCOR-01, SCOR-02, SCOR-03
- [ ] `tests/test_scoring/test_normalizer.py` — covers dimension normalization
- [ ] `tests/test_ai/__init__.py` — new test directory
- [ ] `tests/test_ai/test_client.py` — covers Ollama client wrapper
