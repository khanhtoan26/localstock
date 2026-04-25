---
phase: 17
slug: market-overview-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (auto mode) |
| **Config file** | `apps/prometheus/pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_market_route.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_market_route.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | MKT-04 | — | N/A | unit | `pytest tests/test_market_route.py::TestMarketRouterStructure -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | MKT-04 | — | N/A | unit | `pytest tests/test_market_route.py::TestMarketAppRegistration -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 2 | MKT-04 | — | N/A | unit | `pytest tests/test_market_route.py::TestMarketSummaryResponse -x` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 3 | MKT-03 | — | N/A | type | `cd apps/helios && npm run build` | ✅ exists | ⬜ pending |
| 17-02-02 | 02 | 4 | MKT-03 | — | N/A | visual | manual browser check | ✅ exists | ⬜ pending |
| 17-02-03 | 02 | 4 | MKT-03 | — | N/A | visual | manual browser check | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/prometheus/tests/test_market_route.py` — stubs for MKT-03, MKT-04 (router structure, app registration, response shape)

*Existing infrastructure covers framework — pytest and pytest-asyncio already configured. No new installs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MarketSummaryCards renders skeleton while loading | MKT-03 | No DOM test environment in backend; Helios has no Playwright setup | Open market page while API is slow; verify skeleton appears |
| MarketSummaryCards renders ErrorState on error | MKT-03 | Visual state requires real browser | Stop backend; reload market page; verify ErrorState shows |
| VN-Index card shows real value after VNINDEX crawl | MKT-03 | Depends on vnstock crawlability (LOW confidence assumption A1) | Run admin crawl for VNINDEX; verify card shows non-null value |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
