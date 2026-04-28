# Phase 22: Logging Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 22-logging-foundation
**Areas discussed:** Log destinations, Request ID source, Pipeline run_id, Redaction strategy, Existing call site migration, Log level config, CI lint enforcement, Test env, Stdlib bridge, PII fields

---

## Gray Area Selection

User chose: "Your recommendation for best" — agent picked highest-leverage areas and locked recommended decisions per research/SUMMARY.md guidance.

---

## Log Destinations (D-01)

| Option | Description | Selected |
|--------|-------------|----------|
| stdout JSON only | 12-factor compliant, ops capture via supervisor/Docker | ✓ |
| stdout JSON + rotating file | Belt-and-suspenders, file rotation is sysadmin concern | |
| Pretty-only when TTY | Dev DX without polluting prod logs (combined with above) | ✓ |

**Notes:** Hybrid — JSON to stdout always, pretty to stderr when TTY.

## Request ID Source (D-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Server-generated UUID4 always | Simplest, no input validation surface | partial |
| Trust X-Request-ID header (validated) + fallback | Allows upstream correlation (Helios) | ✓ |
| Server-generated only, ignore header | Strict but loses upstream tracing | |

**Notes:** Header trusted only if matches `^[A-Za-z0-9-]{8,64}$`; else fallback. Echo back via response header.

## Pipeline run_id Source (D-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Generate new UUID at pipeline start | Decoupled from DB | |
| Reuse PipelineRun.id (already persisted) | One ID end-to-end, joinable with DB rows | ✓ |

## Redaction Strategy (D-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Allow-list (whitelist safe fields) | Strictest but brittle for diverse loguru call sites | |
| Deny-list (regex + key names) | Practical, covers known sensitive shapes | ✓ |
| No redaction (trust developers) | Pitfall 17 says no | |

## Existing Logger Migration (D-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-cut all f-string usage day one | Touch ~40 files, but lint stays green from PR1 | ✓ |
| Migrate gradually with grandfather list | Easier rollout, lint must allow exceptions | |
| Replace loguru with structlog | Massive scope creep; rejected by research | |

## Log Level Configuration (D-06)

| Option | Description | Selected |
|--------|-------------|----------|
| LOG_LEVEL env var (Pydantic Settings) | Standard, restart picks up | ✓ |
| Runtime override endpoint | Overkill for single-user; security surface | |
| Per-module config file | YAGNI | |

## CI Lint Enforcement (D-07)

| Option | Description | Selected |
|--------|-------------|----------|
| Ruff custom rule | No native rule for loguru f-string; would need plugin | |
| Pre-commit hook + CI grep step | Two layers, fast-fail local + PR gate | ✓ |
| Self-documented convention only | Pitfall 4 — relying on discipline fails at scale | |

## Test Environment (D-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Always enqueue=True | Risk: pytest hang on teardown | |
| enqueue=False when PYTEST_CURRENT_TEST | Safe in tests, async-safe in prod | ✓ |
| Manual logger.complete() in conftest | Backup safety net (combined) | ✓ |

## Stdlib Logging Bridge (D-09)

| Option | Description | Selected |
|--------|-------------|----------|
| InterceptHandler routing stdlib → loguru | Single source of truth for uvicorn/SQLA/APS | ✓ |
| Two parallel sinks (stdlib + loguru) | Inconsistent JSON shapes, ops nightmare | |

## PII Fields (D-10)

| Option | Description | Selected |
|--------|-------------|----------|
| Treat chat_id/symbol/IP as PII (redact) | Over-redaction, breaks debug | |
| Document as non-sensitive (single-user) | Honest re: app context, prevents future over-redact | ✓ |

---

## the agent's Discretion

- Exact file split inside `localstock/observability/`
- Helper function naming
- Pre-commit hook implementation
- Test fixture naming

## Deferred Ideas

- External log shipping (Loki/Datadog)
- Log sampling
- W3C Trace Context distributed IDs
- GDPR audit
- Log replay / time-travel debugging
- Per-route log level overrides
