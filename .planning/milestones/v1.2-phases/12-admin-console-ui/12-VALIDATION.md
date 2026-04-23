---
phase: 12
slug: admin-console-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Next.js build verification + manual UI testing |
| **Config file** | `apps/helios/next.config.ts` |
| **Quick run command** | `cd apps/helios && npm run lint` |
| **Full suite command** | `cd apps/helios && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/helios && npm run lint`
- **After every plan wave:** Run `cd apps/helios && npm run build`
- **Before `/gsd-verify-work`:** Full build must succeed
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|--------------------|--------|
| 12-01-01 | 01 | 1 | ADMIN-05 | build | `npm run build` | ⬜ pending |
| 12-01-02 | 01 | 1 | ADMIN-05 | lint | `npm run lint` | ⬜ pending |
| 12-02-01 | 02 | 2 | ADMIN-05,06 | build | `npm run build` | ⬜ pending |
| 12-02-02 | 02 | 2 | ADMIN-06 | build | `npm run build` | ⬜ pending |
| 12-03-01 | 03 | 2 | ADMIN-07 | build | `npm run build` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `npx shadcn add checkbox toast` — install missing shadcn components
- [ ] i18n keys added to `en.json` and `vi.json` message files

*Existing infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin page renders 3 tabs | ADMIN-05 | Visual UI rendering | Navigate to /admin, verify Stocks/Pipeline/Jobs tabs visible |
| Stock add/remove works | ADMIN-05 | UI interaction | Add a stock symbol, verify it appears in table, remove it |
| Pipeline triggers create jobs | ADMIN-06 | Requires running backend | Select stocks, click Crawl, verify job appears in Jobs tab |
| Job polling updates status | ADMIN-07 | Real-time behavior | Trigger pipeline, watch Jobs tab for status updates every 3s |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
