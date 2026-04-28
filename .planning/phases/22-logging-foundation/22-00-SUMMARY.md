---
phase: 22
plan: 00
subsystem: observability/test-scaffolds
tags: [logging, observability, tests, lint, scaffolds, wave-0]
requires: []
provides:
  - apps/prometheus/tests/test_observability/ (RED test package, 8 stubs)
  - apps/prometheus/tests/test_observability/conftest.py (loguru_caplog fixture)
  - apps/prometheus/tests/conftest.py (PYTEST_CURRENT_TEST sentinel + _configure_test_logging)
  - apps/prometheus/scripts/lint-no-fstring-logs.sh (OBS-06 grep gate, executable)
affects: []
tech_stack:
  added: []
  patterns:
    - "Loguru capture fixture via `logger.add(lambda msg: records.append(msg.record))`"
    - "PYTEST_CURRENT_TEST sentinel set BEFORE configure_logging import (D-08 enqueue=False guard)"
    - "ImportError-tolerant conftest fallback during Wave 0 (allows existing 437 tests to keep collecting)"
    - "RED test stubs that import target modules so collection fails cleanly until Wave 1"
key_files:
  created:
    - apps/prometheus/tests/test_observability/__init__.py
    - apps/prometheus/tests/test_observability/conftest.py
    - apps/prometheus/tests/test_observability/test_json_format.py
    - apps/prometheus/tests/test_observability/test_redaction.py
    - apps/prometheus/tests/test_observability/test_request_id.py
    - apps/prometheus/tests/test_observability/test_request_log.py
    - apps/prometheus/tests/test_observability/test_run_id.py
    - apps/prometheus/tests/test_observability/test_intercept.py
    - apps/prometheus/tests/test_observability/test_idempotent.py
    - apps/prometheus/tests/test_observability/test_diagnose_no_pii.py
    - apps/prometheus/scripts/lint-no-fstring-logs.sh
  modified:
    - apps/prometheus/tests/conftest.py
decisions:
  - "Honor plan filename list (test_json_format / test_request_id / test_intercept) over RESEARCH naming (test_json_sink / test_correlation / test_async_sink) — plan frontmatter is canonical."
  - "Place PYTEST_CURRENT_TEST sentinel ABOVE all other imports in tests/conftest.py so any module-level loguru config performed at first import sees pytest mode (D-08)."
  - "Lint script root list per plan = src + tests + bin (tighter than RESEARCH §7 which only listed src + tests) — matches plan acceptance criteria."
metrics:
  duration_minutes: 6
  tasks_completed: 3
  files_changed: 12
  completed: 2026-04-28
---

# Phase 22 Plan 00: Test Scaffolds + Lint Skeleton — Summary

Drop-in Wave 0 anchor: 8 RED pytest stubs + loguru capture fixture + executable OBS-06 grep gate, so every downstream Phase 22 plan has a real `<automated>` verify target instead of "MISSING — Wave 0 must create".

## What Got Built

### 1. Observability test package (Task 1, commit `81762aa`)

- `apps/prometheus/tests/test_observability/__init__.py` — empty package marker.
- `apps/prometheus/tests/test_observability/conftest.py` — `loguru_caplog` fixture that adds a temporary loguru sink which appends `record` dicts to a list, then removes the sink on teardown. Per CONTEXT.md D-08b.
- `apps/prometheus/tests/conftest.py` (modified) — appended:
  - `os.environ.setdefault("PYTEST_CURRENT_TEST", "init")` placed BEFORE all other imports so even module-level loguru initialization at import time sees pytest mode and forces `enqueue=False` (D-08 background-thread teardown hang guard).
  - Session-scoped, autouse `_configure_test_logging` fixture that pins `LOG_LEVEL=DEBUG` and calls `configure_logging()` when the observability package exists, and silently no-ops via `ImportError` when it does not (Wave 0 must not break the existing 437-test suite).

### 2. Eight RED test stubs (Task 2, commit `4d2ffe5`)

| File | Phase req | What it asserts |
|---|---|---|
| `test_json_format.py` | OBS-01 | Round-trip basic extras through `json.loads`; `datetime` / `Decimal` / `uuid.UUID` extras serialize without raising (Pitfall 20). |
| `test_redaction.py` | OBS-05 | `_redact_url_creds` masks `user:pass@host`; `telegram_bot_token` extra → `***REDACTED***`, `symbol` stays `"VNM"` (D-10 non-PII). |
| `test_request_id.py` | OBS-02 | `TestClient(create_app())` — missing inbound → 32-hex generated; valid `testabcdefgh1234` → echoed verbatim; malicious inbound → replaced with hex (regex). |
| `test_request_log.py` | OBS-04 | `loguru_caplog` captures `http.request.completed` with `method=GET`, `path=/health`, `status=200`, float `duration_ms`. |
| `test_run_id.py` | OBS-03 | Inside `logger.contextualize(run_id=...)` block, every record carries the run_id; var defaults to `None` outside. |
| `test_intercept.py` | D-09 | `logging.getLogger("uvicorn").info("hi")` produces a JSON line via the loguru sink. |
| `test_idempotent.py` | Pitfall 5 | Two consecutive `configure_logging()` calls leave the same handler count — no duplicates. |
| `test_diagnose_no_pii.py` | Pitfall 17 | `logger.exception("boom")` after `1/0` does NOT include in-scope `AAA-SECRET-BBB` token (forces `diagnose=False`). |

All eight files import from `localstock.observability.*` so collection fails cleanly with `ModuleNotFoundError` until Wave 1 lands. This is the intended RED state, per plan + executor instructions ("Tests in this Wave 0 are SCAFFOLDS — they may FAIL initially because implementation hasn't landed yet"). Total assertable tests: 13 (≥10 required).

### 3. OBS-06 lint script (Task 3, commit `a8c8b2d`)

- `apps/prometheus/scripts/lint-no-fstring-logs.sh` — bash, executable (mode 100755 in git index).
- Greps `apps/prometheus/{src,tests,bin}` for `logger.<level>(\s*f["...]`, with `# noqa: log-fstring` escape.
- Currently exits non-zero against the working tree (existing f-string violations) — that's by design; Wave 3 (plan 22-05) drives this to zero and uses the script as its `<automated>` gate.
- `bash -n` syntax valid.

## Verification Snapshot

```
$ cd apps/prometheus && uv run pytest --collect-only tests/
... 437 tests collected ...   # existing suite uncorrupted
$ uv run pytest --collect-only tests/test_observability/
... 8 errors during collection ...   # RED — ModuleNotFoundError on localstock.observability (expected)
$ grep -l 'from localstock.observability' tests/test_observability/test_*.py | wc -l
8
$ bash apps/prometheus/scripts/lint-no-fstring-logs.sh; echo $?
1   # detection working — Wave 3 will drive to 0
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reverted `requirements mark-complete` side-effects**
- **Found during:** post-task state updates
- **Issue:** Running `gsd-sdk query requirements.mark-complete OBS-01..OBS-06` (per executor protocol, since the plan frontmatter listed those requirement IDs) did two wrong things: (a) it corrupted REQUIREMENTS.md formatting by inserting a newline inside the bold marker (`**OBS-01\n**:` instead of `**OBS-01**:`), and (b) it marked the requirements as complete even though Wave 0 only delivers RED scaffolds — the actual OBS-01..06 implementation lands in Waves 1-3.
- **Fix:** `git checkout -- .planning/REQUIREMENTS.md` to revert. Downstream impl plans (22-01 through 22-05) will mark these requirements complete when the implementation actually lands and the RED tests turn GREEN.
- **Files modified:** none (revert only)
- **Commit:** included in final docs commit below

### Other minor reconciliations

One naming reconciliation: the plan frontmatter `files_modified` list named the test files `test_json_format.py` / `test_request_id.py` / `test_intercept.py`, while RESEARCH §"Wave 0 Gaps" referred to `test_json_sink.py` / `test_correlation.py` / `test_async_sink.py`. The plan filenames are canonical (frontmatter wins, per executor protocol) and were used; the test bodies still cover the OBS criteria as RESEARCH §"Phase Requirements → Test Map" specifies.

## Known Stubs

The 8 test files are intentional RED stubs by plan design (Wave 0 Nyquist contract: tests-before-impl). They will go GREEN as Wave 1+ lands `localstock/observability/{logging,context,middleware}.py`. Acceptance was "tests exist with correct signatures and stubs", NOT "tests pass". Plan-level success criterion ("downstream plans can write `<automated>uv run pytest tests/test_observability/test_X.py</automated>` without 'MISSING — Wave 0 must create' placeholders") is satisfied — every downstream plan now has a stable pytest path to point at.

## Threat Flags

None — Wave 0 only adds test scaffolds and a static grep script; no new endpoints, no auth surface, no schema changes, no file I/O outside the test sandbox.

## Self-Check: PASSED

- ✅ `apps/prometheus/tests/test_observability/__init__.py` exists
- ✅ `apps/prometheus/tests/test_observability/conftest.py` exists (`loguru_caplog`)
- ✅ `apps/prometheus/tests/conftest.py` modified (`PYTEST_CURRENT_TEST` + `_configure_test_logging`)
- ✅ 8 test stub files exist, all importing `localstock.observability.*`
- ✅ `apps/prometheus/scripts/lint-no-fstring-logs.sh` exists, executable (100755)
- ✅ Commit `81762aa` present in `git log`
- ✅ Commit `4d2ffe5` present in `git log`
- ✅ Commit `a8c8b2d` present in `git log`
- ✅ Existing 437-test suite still collects cleanly
