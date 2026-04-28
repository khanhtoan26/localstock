---
phase: 22-logging-foundation
plan: 02
subsystem: config
tags: [observability, config, validation, pydantic, fail-fast]
requirements: [OBS-01]
status: complete
dependency_graph:
  requires:
    - "22-00 (Wave 0 RED scaffolds — conftest LOG_LEVEL=DEBUG fixture)"
  provides:
    - "Settings.log_level validated + uppercase-normalized for configure_logging()"
  affects:
    - "apps/prometheus/src/localstock/config.py"
tech_stack:
  added: []
  patterns:
    - "Pydantic v2 field_validator(mode='before') — mirrors ensure_asyncpg_driver"
    - "Fail-fast normalization (ValueError → ValidationError at Settings construction)"
key_files:
  created:
    - "apps/prometheus/tests/test_config_log_level.py"
  modified:
    - "apps/prometheus/src/localstock/config.py"
decisions:
  - "Kept log_level as str (not Enum) per CONTEXT.md D-06 for .env ergonomics"
  - "Used `mode='before'` so lowercase env values can be normalized prior to type validation"
  - "Default field value 'INFO' left unchanged — already in allowed set"
metrics:
  duration_minutes: 4
  completed_at: "2026-04-28T10:36:06Z"
  tasks_completed: 1
  files_changed: 2
  tests_added: 12
  tests_passing: 449
---

# Phase 22 Plan 02: Settings.log_level Validator Summary

Added a Pydantic `field_validator` to `Settings.log_level` that normalizes case and rejects unknown loguru levels at app startup, ensuring `configure_logging()` can pass the value directly to `logger.add(level=...)` without runtime surprises.

## What Changed

### `apps/prometheus/src/localstock/config.py`
Added `normalize_log_level` `field_validator(mode="before")` immediately after the existing `ensure_asyncpg_driver` validator. The validator:
- Rejects non-string input with `ValueError("log_level must be a string")`
- Uppercases the value
- Validates against the loguru level set `{TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL}`
- Raises `ValueError(f"log_level must be one of {sorted(allowed)}, got {v!r}")` on miss

Field default `log_level: str = "INFO"` and the existing import line `from pydantic import field_validator` were both already correct — no other edits needed.

### `apps/prometheus/tests/test_config_log_level.py` (new)
12 tests covering:
- Default `INFO` when env unset (uses `monkeypatch.delenv` + `_env_file=None` to bypass `conftest.py`'s `LOG_LEVEL=DEBUG` fixture and the project `.env`)
- Lowercase / mixed-case → uppercase normalization
- Parametrized acceptance of all 7 loguru levels
- `ValidationError` for invalid levels with required substring `"log_level must be one of"`
- `ValidationError` for non-string with required substring `"log_level must be a string"`

## Verification

- `uv run pytest tests/test_config_log_level.py` → **12 passed**
- `uv run pytest tests/ -x --ignore=tests/test_observability` → **449 passed** (no regressions)
- Plan one-liner round-trip → **OK**
- `grep -c 'normalize_log_level' apps/prometheus/src/localstock/config.py` → 1
- `grep -c 'def ensure_asyncpg_driver' apps/prometheus/src/localstock/config.py` → 1 (untouched)

## TDD Cycle

| Phase | Commit  | Description                                             |
| ----- | ------- | ------------------------------------------------------- |
| RED   | 6ab85c9 | `test(22-02): add failing tests for log_level validator` |
| GREEN | 42e8cf7 | `feat(22-02): add log_level validator to Settings`       |

REFACTOR phase skipped — implementation is 11 lines and already mirrors the existing validator style verbatim per PATTERNS.md.

## Deviations from Plan

**1. [Rule 1 - Test correctness] Default-value test needed env override**
- **Found during:** Task 1 RED phase
- **Issue:** `tests/conftest.py` autouse fixture sets `os.environ["LOG_LEVEL"] = "DEBUG"`, so `Settings()` did not return the field default `INFO` even with `_env_file=None`.
- **Fix:** Added `monkeypatch.delenv("LOG_LEVEL", raising=False)` to `test_log_level_default_is_info` so the default-value assertion isolates from the conftest fixture and the project `.env`.
- **Files modified:** `apps/prometheus/tests/test_config_log_level.py`
- **Commit:** 6ab85c9 (test was edited before being committed)

No other deviations. No auth gates.

## Threat Flags

None — change strengthens validation surface only; no new endpoints, file access, or trust-boundary crossings introduced.

## Self-Check: PASSED

- FOUND: apps/prometheus/src/localstock/config.py (modified, contains `normalize_log_level`)
- FOUND: apps/prometheus/tests/test_config_log_level.py (new)
- FOUND: 6ab85c9 (RED commit)
- FOUND: 42e8cf7 (GREEN commit)
