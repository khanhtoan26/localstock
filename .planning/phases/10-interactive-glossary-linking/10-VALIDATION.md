---
phase: 10
slug: interactive-glossary-linking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2025-07-18
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Next.js build + TypeScript compiler |
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
| 10-01-01 | 01 | 1 | GLOSS-01 | — | N/A | build | `cd apps/helios && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | GLOSS-02 | — | N/A | build | `cd apps/helios && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | GLOSS-03 | — | N/A | build | `cd apps/helios && npm run build` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | GLOSS-04 | — | N/A | build | `cd apps/helios && npm run build` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hover card appears on mouse hover over glossary term | GLOSS-03 | Browser interaction required | Hover over dotted-underline term in AI report, verify popover appears after 200ms |
| Tap to toggle on mobile | GLOSS-03 | Touch interaction required | Tap glossary term on mobile viewport, verify popover toggles |
| Deep link navigates to learn page with hash | GLOSS-04 | Navigation + hash detection | Click "Xem chi tiết →" in hover card, verify /learn/[category]#[term] loads with card expanded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
