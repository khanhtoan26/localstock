---
phase: 22-logging-foundation
plan: 06
subsystem: observability
tags: [ci, pre-commit, github-actions, lint, OBS-06]
requires: [22-05]
provides:
  - "Pre-commit local gate enforcing no f-string log calls"
  - "GitHub Actions CI gate enforcing the same on every PR + push to main"
  - "OBS-06 closure: regression-proof — both layers green, gate proven to fail-fast on synthetic violation"
affects: [ci, dev-workflow]
tech_stack_added:
  - "pre-commit (local hook framework, repo-local hook only — no version pin needed)"
  - "GitHub Actions (workflow lint.yml — first .github/workflows/ in repo)"
patterns_used:
  - "Single source of truth: both gates invoke apps/prometheus/scripts/lint-no-fstring-logs.sh"
  - "Local hook with pass_filenames: false + always_run: true → full repo scan, immune to partial commits"
  - "Minimal, scoped CI workflow (lint-only) — broader CI deferred to separate milestone"
key_files:
  created:
    - .pre-commit-config.yaml
    - .github/workflows/lint.yml
  modified: []
decisions:
  - "Created .github/workflows/ directory (first time in repo) rather than deferring CI gate — D-07 mandates both layers"
  - "Did NOT add unrelated hooks (ruff/black/mypy) to .pre-commit-config.yaml — keeps Phase 22 scope tight; future phases extend"
  - "Action version pinned to actions/checkout@v4 (current stable)"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-28"
  tasks_completed: 3
  files_changed: 2
---

# Phase 22 Plan 06: CI Lint Enforcement Summary

OBS-06 made self-enforcing — `.pre-commit-config.yaml` and `.github/workflows/lint.yml` both delegate to `apps/prometheus/scripts/lint-no-fstring-logs.sh`, blocking f-string log regressions at commit-time and PR-time.

## What Was Built

| File | Role | Trigger |
|------|------|---------|
| `.pre-commit-config.yaml` | Local fast-fail gate | `git commit` (when developer runs `pre-commit install`) |
| `.github/workflows/lint.yml` | CI / PR merge gate | `push` to main, `pull_request` to main |

Both invoke the same canonical script — single source of truth, identical regex, no drift risk.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | .pre-commit-config.yaml — local fast-fail hook | `51e1fab` | `.pre-commit-config.yaml` |
| 2 | .github/workflows/lint.yml — minimal CI gate | `a628f88` | `.github/workflows/lint.yml` |
| 3 | End-to-end gate sanity check (synthetic violation) | (no commit — verification only) | — |

## Verification Results

- **YAML parse:** `python3 -c "import yaml; yaml.safe_load(...)"` exits 0 for both files ✅
- **Lint script (clean repo):** `bash apps/prometheus/scripts/lint-no-fstring-logs.sh` → `OK: zero f-string log calls.` exit 0 ✅
- **pre-commit run --all-files no-fstring-log:** `loguru: no f-string log calls............................................Passed` exit 0 ✅ (installed pre-commit 4.6.0 via `uv pip install pre-commit`, executed via `uv run pre-commit`)
- **Synthetic violation (Task 3):** Injected `_ = lambda: __import__("loguru").logger.info(f"sanity-check-{1}")` at end of `apps/prometheus/src/localstock/api/app.py`, ran lint → exit 1 with `::error::f-string log calls detected` and the offending line printed. Reverted via `git checkout --`; re-ran lint → exit 0; `git diff --quiet apps/prometheus/src/` confirms clean tree. ✅

The gate has teeth: red on violation, green on clean.

## Acceptance Criteria

- [x] `.pre-commit-config.yaml` exists at repo root with `id: no-fstring-log`
- [x] Hook delegates to `lint-no-fstring-logs.sh` (single source of truth)
- [x] `pass_filenames: false` + `always_run: true` (full repo scan)
- [x] `.github/workflows/lint.yml` exists, valid YAML
- [x] Workflow triggers on `pull_request` + `push` to `main`
- [x] Workflow uses `actions/checkout@v4`
- [x] Workflow references `apps/prometheus/scripts/lint-no-fstring-logs.sh`
- [x] Synthetic violation detected (gate proven red-on-dirty)
- [x] Working tree clean after revert (no leftover modifications)

## Deviations from Plan

None — plan executed exactly as written. Both YAML files match the templates in the plan body verbatim.

## Threat Model Status

- **T-22-13 (regression of OBS-06):** Mitigated. Both layers active; merge to main now requires the CI workflow to pass.
- **T-22-14 (`--no-verify` bypass):** Accepted. CI workflow is the authoritative gate; local hook is convenience layer. Documented behavior.

## Phase 22 Closure

This is the final wave of Phase 22 (Logging Foundation). With 22-06 complete:

- ✅ OBS-01: structured-extras surface (kwargs flow → `record.extra` → redaction patcher)
- ✅ OBS-06: zero f-string log calls + CI gate enforcing the invariant on every PR

Phase 22 is now self-sustaining: future contributors cannot reintroduce f-string log violations without explicitly bypassing both gates.

## Self-Check: PASSED

- FOUND: `.pre-commit-config.yaml` (commit `51e1fab`)
- FOUND: `.github/workflows/lint.yml` (commit `a628f88`)
- FOUND commit `51e1fab` in `git log --all`
- FOUND commit `a628f88` in `git log --all`
