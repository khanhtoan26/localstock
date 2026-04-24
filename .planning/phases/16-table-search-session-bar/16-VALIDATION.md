---
phase: 16
slug: table-search-session-bar
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest |
| **Config file** | apps/helios/vitest.config.ts (exists, no test files yet) |
| **Quick run command** | `cd apps/helios && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd apps/helios && npx vitest run` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/helios && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd apps/helios && npx vitest run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | TBL-01 | — | N/A | unit | `cd apps/helios && npx vitest run tests/sort-comparator.test.ts` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | TBL-02 | — | N/A | unit | `cd apps/helios && npx vitest run tests/sort-comparator.test.ts` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 0 | TBL-03 | — | Input sanitization | unit | `cd apps/helios && npx vitest run tests/search-filter.test.ts` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 0 | MKT-01 | — | N/A | unit | `cd apps/helios && npx vitest run tests/hose-session.test.ts` | ❌ W0 | ⬜ pending |
| 16-03-02 | 03 | 0 | MKT-02 | — | N/A | unit | `cd apps/helios && npx vitest run tests/hose-session.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/helios/tests/sort-comparator.test.ts` — stubs for TBL-01, TBL-02 (numeric sort + tiebreaker, grade semantic sort)
- [ ] `apps/helios/tests/search-filter.test.ts` — stubs for TBL-03 (symbol prefix match, name substring, case-insensitive)
- [ ] `apps/helios/tests/hose-session.test.ts` — stubs for MKT-01, MKT-02 (phase boundaries, closed countdown)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sort icon renders (ChevronUp/Down) on active column | TBL-02 | Visual assertion | Open rankings page, click a numeric column, verify arrow icon appears |
| Search URL persistence across navigation | TBL-04 | Browser navigation | Add ?q=VNM in search, navigate to a stock page, use back button, verify ?q=VNM is in URL and input shows "VNM" |
| Session bar updates live (1-minute tick) | MKT-01 | Real-time behavior | Open header at boundary minute, watch for phase/countdown update |
| Weekend closed state shows "Reopens Monday" | MKT-02 | Calendar-dependent | Run on a weekend or mock Date to Saturday |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
