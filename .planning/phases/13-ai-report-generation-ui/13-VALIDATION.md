---
phase: 13
slug: ai-report-generation-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest 7.x (backend — existing) |
| **Config file** | `apps/helios/vitest.config.ts` (if exists) or component tests via Next.js |
| **Quick run command** | `cd apps/helios && npx tsc --noEmit` |
| **Full suite command** | `cd apps/helios && npm run lint && npx tsc --noEmit` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/helios && npx tsc --noEmit`
- **After every plan wave:** Run `cd apps/helios && npm run lint && npx tsc --noEmit`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | ADMIN-08 | — | N/A | type-check | `npx tsc --noEmit` | ✅ | ⬜ pending |
| 13-01-02 | 01 | 1 | ADMIN-08 | — | N/A | type-check | `npx tsc --noEmit` | ✅ | ⬜ pending |
| 13-02-01 | 02 | 2 | ADMIN-08 | — | N/A | type-check + lint | `npm run lint && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. shadcn Sheet + Progress components installed via `npx shadcn@latest add sheet progress`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report button triggers generation and sheet opens | ADMIN-08 SC-1 | UI interaction flow | Select stock in Pipeline tab, click Report, verify sheet opens with progress |
| Progress indicator shows during LLM processing | ADMIN-08 SC-2 | Requires running Ollama | Trigger report, observe step indicator transitions queued→generating→complete |
| Generated report visible in stock detail page | ADMIN-08 SC-3 | E2E data flow | After generation, navigate to stock page, verify report displays |
| Batch generation processes stocks sequentially | ADMIN-08 | Backend integration | Select 2+ stocks, trigger report, verify sequential processing in Jobs tab |
| Error state shows when Ollama offline | ADMIN-08 | Requires Ollama shutdown | Stop Ollama, trigger report, verify error message displays |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
