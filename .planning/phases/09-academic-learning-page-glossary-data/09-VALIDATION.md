---
phase: 9
slug: academic-learning-page-glossary-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-07-18
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None installed — no test runner in helios app |
| **Config file** | None |
| **Quick run command** | `cd apps/helios && npm run build` |
| **Full suite command** | `cd apps/helios && npm run build && npm run lint` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/helios && npm run build`
- **After every plan wave:** Run `cd apps/helios && npm run build && npm run lint`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | LEARN-02 | — | N/A | unit | `npx tsx --eval "import {glossaryEntries} from './src/lib/glossary'; console.log(glossaryEntries.length >= 15 ? 'PASS' : 'FAIL')"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | LEARN-04 | — | N/A | unit | `npx tsx --eval "import {normalizeForSearch} from './src/lib/glossary'; console.log(normalizeForSearch('chỉ số') === normalizeForSearch('chi so') ? 'PASS' : 'FAIL')"` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | LEARN-01 | — | N/A | smoke | Manual: visit `/learn`, `/learn/technical`, `/learn/fundamental`, `/learn/macro` | ❌ | ⬜ pending |
| 09-02-02 | 02 | 2 | LEARN-03 | — | N/A | smoke | Manual: visit `/learn/invalid` → 404 | ❌ | ⬜ pending |
| 09-03-01 | 03 | 3 | LEARN-04 | T-09-01 | Search input client-side only | smoke | Manual: type in search, verify filter works with diacritics | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No test framework installed — validation relies on TypeScript compilation (`npm run build`) and manual smoke testing
- [ ] For LEARN-02 and LEARN-04, inline TypeScript checks via `npx tsx` can validate data integrity and search normalization

*Existing infrastructure covers build validation. Manual smoke tests required for page rendering.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Learn hub page renders 3 category cards | LEARN-01 | No test runner; visual check needed | Visit `/learn`, verify 3 cards visible |
| Category pages render entries | LEARN-01 | No test runner; visual check needed | Visit `/learn/technical`, verify entries render |
| Invalid category shows 404 | LEARN-03 | Server routing behavior | Visit `/learn/invalid`, verify 404 page |
| Sidebar shows "Học" nav item | LEARN-01 | Visual check | Click sidebar, verify "Học" with BookOpen icon |
| Search filters with diacritics | LEARN-04 | Interactive behavior | Type "chi so" in search, verify "chỉ số" entries appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
