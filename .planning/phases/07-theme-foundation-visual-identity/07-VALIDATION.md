---
phase: 7
slug: theme-foundation-visual-identity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Next.js build + TypeScript type-check |
| **Config file** | `apps/helios/tsconfig.json`, `apps/helios/next.config.ts` |
| **Quick run command** | `cd apps/helios && npx tsc --noEmit` |
| **Full suite command** | `cd apps/helios && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/helios && npx tsc --noEmit`
- **After every plan wave:** Run `cd apps/helios && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | THEME-01 | — | N/A | build | `npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | THEME-02 | — | N/A | build | `npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | THEME-03 | — | N/A | build | `npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | THEME-04 | — | N/A | build | `npm run build` | ✅ | ⬜ pending |
| TBD | TBD | TBD | THEME-05 | — | N/A | manual | Visual inspection | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No FOUC on first visit | THEME-02 | Requires browser load observation | Open app in incognito, verify warm-light loads without dark flash |
| Chart colors update on toggle | THEME-04 | Canvas rendering not testable via DOM | Toggle theme, verify chart colors change without reload |
| Grade badge contrast on cream | THEME-05 | Visual contrast verification | Toggle to warm-light, check all grade badges are readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
