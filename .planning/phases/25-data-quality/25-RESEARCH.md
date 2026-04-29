---
phase: 25
phase_name: Data Quality
researched: 2026-04-29
domain: pandera schemas, JSONB sanitization, per-symbol isolation, quarantine, stale-data probe
confidence: HIGH
---

# Phase 25: Data Quality — Research

## Summary

Phase 25 closes four DQ gaps before Phase 27 parallelism turns them into amplified bugs:
(1) corrupt OHLCV/financials silently land in the DB; (2) NaN/Inf leak into JSONB and break
`/api/reports`; (3) one bad symbol can kill 399 healthy ones; (4) `/health/data` doesn't
flag stale snapshots loud enough. CONTEXT.md has eight locked decisions (D-01..D-08); this
research informs **how** to implement them, not whether.

The good news: most of the substrate is already in place. `_clean_nan` is already inlined in
`services/pipeline.py:_store_financials` (proves the recipe works) — Phase 25 promotes it to a
shared `localstock.dq.sanitizer` module and wires it into every JSONB-writing repo. `/health/data`
already returns `{max_price_date, trading_days_lag, stale}` (24-04) with a static VN trading
calendar; Phase 25 just nests this into a `data_freshness` block plus the existing keys for back-compat
(D-05). PipelineRun already tracks `symbols_total/success/failed`; Phase 25 adds `stats` JSONB and
dual-writes through v1.5 (D-07).

The genuinely new surfaces are (a) the `dq/` package with pandera schemas and a shadow-mode
dispatcher, (b) the polymorphic `quarantine_rows` table + 30-day APScheduler retention job, and
(c) auditing per-symbol loops to apply `gather(return_exceptions=True)` consistently across
`services/` and `crawlers/`.

**Primary recommendation:** Land Wave 0 (RED tests + `pandera[pandas]` install + Alembic
migration for both `quarantine_rows` and `pipeline_runs.stats`) in a single PR. From Wave 1
forward, the sanitizer is the foundation everyone else builds on — it must merge first.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** Pandera schemas live in per-domain modules under `src/localstock/dq/schemas/`
  (`ohlcv.py`, `financials.py`, `indicators.py`). New package `src/localstock/dq/` is the single
  home for schemas, sanitizer, quarantine repo, shadow-mode dispatcher.
- **D-02** Single polymorphic `quarantine_rows` table: `(id, source, symbol, payload JSONB,
  reason, rule, tier, quarantined_at)`. 30-day retention via APScheduler cron at off-hours.
  `source` indexed alongside `quarantined_at`. Replay = manual SQL; automated replay deferred to v1.6.
- **D-03** Per-stock isolation at **every** per-symbol step (crawl, analyze, score, report).
  Use `asyncio.gather(*coros, return_exceptions=True)` or equivalent loop with try/except.
  Failures logged with `{symbol, step, exception_class, message}` and recorded in
  `failed_symbols` with step name (e.g. `{"BAD": "crawl"}`).
- **D-04** `localstock.dq.sanitizer.sanitize_jsonb(value)` recurses into nested dict/list,
  replaces `±inf` and `NaN` with `None`. Called at the **repository layer** before every
  JSONB write — not service layer, not SQLAlchemy event listener.
- **D-05** `/health/data` extends 24-04 endpoint, reuses static `_VN_HOLIDAYS_2025_2026`
  calendar from `api/routes/health.py`. Threshold = `settings.dq_stale_threshold_sessions`
  (default 1). Adds nested `data_freshness: {last_trading_day, max_data_date, sessions_behind, status}`
  while keeping existing top-level keys for back-compat.
- **D-06** Per-rule env flags `DQ_TIER2_<RULE>_MODE=shadow|enforce` (e.g.
  `DQ_TIER2_RSI_MODE`); fallback `DQ_DEFAULT_TIER2_MODE=shadow`. Counter
  `dq_violations_total{rule, tier}` always emits — `tier="advisory"` in shadow,
  `tier="strict"` after promotion.
- **D-07** New `PipelineRun.stats: JSONB | None` with shape
  `{succeeded, failed, skipped, failed_symbols: [{symbol, step, error}, ...]}`.
  Existing scalar columns dual-written through v1.5; deprecation in v1.6.
  Truncate `error` to first 200 chars.
- **D-08** 5 waves: **Wave 0** RED scaffolds + `pandera[pandas]` install + `dq/` skeleton +
  Alembic migration. **Wave 1** DQ-04 sanitizer + DQ-08 quarantine repo (parallel).
  **Wave 2** DQ-01 Tier 1 schemas + DQ-05 isolation audit + DQ-06 stats (DQ-05 depends on
  DQ-06 schema). **Wave 3** DQ-02 Tier 2 + DQ-03 shadow runbook (sequential). **Wave 4** DQ-07.

### Discretion Areas

None — CONTEXT.md is fully locked. Researcher/planner choices live inside each decision
(e.g., exact pandera idiom, which fields to log, test fixture shapes).

### Deferred Ideas (OUT OF SCOPE)

- Automated quarantine replay (v1.6 backlog).
- Trading-calendar 2027+ extension (24-04 backlog).
- DQ rules for non-OHLCV sources (news, macro, fund flows).
- Per-symbol rate-limit / throttle (Phase 27 owns this).
- Dropping scalar `symbols_total/success/failed` (v1.6).
- Telegram alerting on quarantine spikes (future ops phase).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DQ-01 | Tier 1 OHLCV pandera schemas (block per-symbol, reject to quarantine) | §Pandera Idioms, §Quarantine Repo Pattern |
| DQ-02 | Tier 2 advisory schemas (RSI > 99.5, gap > 30%, missing > 20%) — log + metric, no block | §Tier 2 Dispatcher, §Custom Checks |
| DQ-03 | Shadow-mode default 14 days; runbook for promotion | §Shadow-Mode Dispatcher |
| DQ-04 | `sanitize_jsonb` at JSONB write boundary | §Sanitizer Recipes, §Audit List D-04 |
| DQ-05 | Per-stock try/except isolation everywhere | §asyncio.gather pattern, §Audit List D-03 |
| DQ-06 | `PipelineRun.stats` JSONB column with succeeded/failed/failed_symbols | §PipelineRun.stats migration |
| DQ-07 | `/health/data` stale-data extension | §/health/data extension |
| DQ-08 | Quarantine table for rejected rows | §Quarantine Repo Pattern, §Retention Cron |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tier 1 / Tier 2 schema declarations | `dq/schemas/` (new pkg) | — | Domain-pure; no SQLAlchemy/FastAPI deps |
| `sanitize_jsonb` helper | `dq/sanitizer.py` (new) | — | Pure function; called from repos |
| JSONB write sanitization | Repository layer | — | Chokepoint per D-04 |
| Per-symbol isolation | Service layer (`pipeline.py`, `analysis_service.py`, etc.) | Crawler `base.fetch_batch` | Service owns the loop; crawler base already returns `(results, failed)` |
| Quarantine writes | New `dq/quarantine_repo.py` | Validators (call site) | Validator decides "reject", repo persists |
| Quarantine 30-day retention | `scheduler/scheduler.py` APScheduler job | — | Same place as daily pipeline + admin worker |
| `/health/data` stale flag | `api/routes/health.py` | Reuses `_VN_HOLIDAYS_2025_2026` | Extends 24-04 endpoint |
| Tier 2 shadow dispatch | `dq/shadow.py` (or `dq/dispatcher.py`) | `Settings` (env flags) | One helper, env-driven |
| `PipelineRun.stats` write | `services/pipeline.py` | Alembic migration | Single source of truth in orchestrator |

## Standard Stack

### Core (existing — no new core deps required, one addition)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandera[pandas] | `>=0.31,<1.0` (latest 0.31.1 per STACK.md) [VERIFIED: STACK.md compat table] | DataFrame schema validation, Tier 1 + Tier 2 OHLCV checks | Native pandas 2.2 + Pydantic v2 support; lazy-eval with structured `SchemaErrors`; lightweight (~3 deps) vs Great Expectations [CITED: STACK.md] |
| pandas | `>=2.2,<3.0` (existing) | DataFrame substrate | Already in pyproject [VERIFIED: pyproject.toml] |
| numpy | `>=2.0,<3.0` (existing) | `np.inf`, `np.nan` for sanitizer | Already in pyproject [VERIFIED: pyproject.toml] |
| sqlalchemy[asyncio] | `>=2.0,<3.0` (existing) | Async ORM for `quarantine_rows` repo | [VERIFIED: pyproject.toml] |
| alembic | `>=1.18,<2.0` (existing) | Migration for `quarantine_rows` + `pipeline_runs.stats` | [VERIFIED: pyproject.toml] |
| apscheduler | `>=3.11,<4.0` (existing) | 30-day retention cron | [VERIFIED: pyproject.toml] |
| prometheus-client | `>=0.21,<1.0` (existing) | `dq_violations_total{rule, tier}` counter | [VERIFIED: pyproject.toml] |
| pydantic-settings | `>=2.0,<3.0` (existing) | Per-rule env flags | [VERIFIED: pyproject.toml] |
| loguru | `>=0.7,<1.0` (existing) | Structured `dq_warn` log lines | [VERIFIED: pyproject.toml] |

### Test deps (Wave 0)

| Library | Version | Purpose |
|---------|---------|---------|
| hypothesis | `>=6.0` [ASSUMED — not currently in pyproject] | Property-test for `sanitize_jsonb` over nested dict/list |

> **Action for Wave 0:** if hypothesis is desired for the sanitizer property test, add it under
> `[dependency-groups].dev`; otherwise hand-roll a small fuzz table — this is the planner's
> call. CONTEXT.md doesn't lock the choice.

**Installation (Wave 0):**

```bash
cd apps/prometheus
uv add 'pandera[pandas]>=0.31,<1.0'
# Optional, only if hypothesis-based property testing chosen:
uv add --group dev 'hypothesis>=6.0'
```

**Version verification:** STACK.md line documenting `pandera>=0.31,<1.0` (latest 0.31.1) is
treated as the source of truth [CITED: .planning/research/STACK.md]. Re-confirm at install
time with `uv tree` and `pip index versions pandera`.

### Alternatives Considered (locked-out by CONTEXT.md)

| Instead of | Could Use | Why rejected (per CONTEXT.md / STACK.md) |
|------------|-----------|------------------------------------------|
| pandera | Great Expectations | Heavy framework, slow imports, JSON config files [CITED: STACK.md "Don't Use" table] |
| pandera | Hand-rolled Pydantic per row | Loses pandas semantics; 400×500 row-by-row is slow [CITED: STACK.md] |
| Repo-layer sanitizer (D-04) | SQLAlchemy event listener | Silent magic — too easy to forget the layering [CITED: 25-CONTEXT.md D-04 rationale] |
| Per-domain quarantine tables | Single polymorphic table | Per-source migration churn [CITED: 25-CONTEXT.md D-02 rationale] |
| Global `DQ_TIER2_MODE` flag | Per-rule flags | All-or-nothing promotion blocks ops [CITED: 25-CONTEXT.md D-06 rationale] |

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────┐
                     │     Pipeline.run_full (services)    │
                     └──────────────┬──────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
  per-symbol crawl           per-symbol analyze            per-symbol score/report
  (gather, ret_exc=True)     (gather, ret_exc=True)        (gather, ret_exc=True)
       │                            │                            │
       ▼                            ▼                            ▼
  ┌─────────────┐           ┌──────────────────┐        ┌──────────────────┐
  │ DataFrame   │           │ DataFrame +      │        │ Report dict      │
  │ from        │           │ indicators       │        │ (LLM JSON)       │
  │ vnstock/VCI │           │                  │        │                  │
  └──────┬──────┘           └────────┬─────────┘        └────────┬─────────┘
         │                           │                           │
         ▼ Tier 1 (block)            ▼ Tier 2 (shadow)           │
   ┌──────────────────┐        ┌─────────────────┐               │
   │ pandera          │        │ pandera lazy    │               │
   │ OHLCVSchema      │        │ + dispatcher    │               │
   │ .validate(lazy)  │        │ get_tier2_mode()│               │
   └────┬─────┬───────┘        └────────┬────────┘               │
   pass │     │ fail                    │ violation              │
        │     ▼                         ▼                        │
        │  quarantine_rows         dq_violations_total           │
        │  (source, payload,       {rule, tier=advisory}         │
        │   reason, rule, tier)    + loguru "dq_warn"            │
        │                                                        │
        ▼                                                        ▼
   ┌──────────────────────────────────────────────────────────────┐
   │   Repository layer: every JSONB-bound write calls            │
   │   sanitize_jsonb(payload) → no NaN/Inf in DB                 │
   └──────────────────────┬───────────────────────────────────────┘
                          ▼
                   ┌──────────────┐
                   │  Postgres    │
                   │  stock_*     │
                   │  pipeline_   │
                   │  runs.stats  │
                   │  quarantine_ │
                   │  rows        │
                   └──────────────┘
                          │
                          ▼
              ┌────────────────────────────┐
              │ APScheduler nightly cron   │
              │ DELETE FROM quarantine_rows│
              │ WHERE quarantined_at <     │
              │   now() - INTERVAL '30 d'  │
              └────────────────────────────┘

      ┌────────────────────────────────────────────────────────┐
      │ /health/data probe: MAX(stock_prices.date) vs static   │
      │ _VN_HOLIDAYS_2025_2026 → data_freshness block + stale  │
      └────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (D-01)

```
apps/prometheus/src/localstock/dq/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── ohlcv.py          # OHLCVSchema (Tier 1) + OHLCVAdvisorySchema (Tier 2)
│   ├── financials.py     # Tier 1 financials shape checks (numeric coercion)
│   └── indicators.py     # Tier 2 indicator anomalies (RSI > 99.5, gap > 30%)
├── sanitizer.py          # sanitize_jsonb(value) — D-04
├── shadow.py             # get_tier2_mode(rule) -> 'shadow' | 'enforce' — D-06
├── quarantine_repo.py    # async insert_quarantined_row(...), cleanup_old(days=30)
└── runner.py             # validate_and_quarantine(df, schema, source) helper
```

### Pattern 1 — Pandera Tier 1 schema, lazy validation, per-row partition (D-01, DQ-01)

**What:** A Tier 1 schema declares hard correctness rules (negative price, future date,
duplicate PK). `validate(lazy=True)` collects ALL failures into a single `SchemaErrors` (note plural —
that's the multi-failure variant) instead of failing on the first row. The `SchemaErrors.failure_cases`
attribute is a DataFrame describing every offending row; we use it to partition the input frame
into "passed" and "rejected" subsets. Passed rows go to `stock_prices`; rejected rows go to
`quarantine_rows`. [CITED: pandera docs — "Lazy Validation" — https://pandera.readthedocs.io/en/stable/lazy_validation.html]

**When to use:** Every Tier 1 validator (DQ-01).

**Example (illustrative; planner produces final form):**

```python
# src/localstock/dq/schemas/ohlcv.py
from datetime import date
import pandas as pd
import pandera.pandas as pa
from pandera import Check, Column, DataFrameSchema

# Tier 1 — block-on-fail. Schema must be tight.
OHLCVSchema = DataFrameSchema(
    columns={
        "symbol": Column(str, Check.str_matches(r"^[A-Z0-9]{3,5}$")),
        "date":   Column("datetime64[ns]"),
        "open":   Column(float, Check.gt(0)),
        "high":   Column(float, Check.gt(0)),
        "low":    Column(float, Check.gt(0)),
        "close":  Column(float, Check.gt(0)),
        "volume": Column(int,   Check.ge(0)),
    },
    checks=[
        # composite: future date — runs over the whole frame
        Check(lambda df: df["date"].dt.date <= date.today(),
              error="future_date"),
        # composite: NaN ratio threshold (allow up to 5% NaN per column)
        Check(lambda df: df.isna().mean().max() <= 0.05,
              error="nan_ratio_exceeded"),
    ],
    unique=["symbol", "date"],   # duplicate PK
    strict=True,                 # reject unknown columns
    coerce=True,
)
```

```python
# src/localstock/dq/runner.py — illustrative partition helper
import pandera.errors as pae

def partition_valid_invalid(df, schema):
    """Return (valid_df, invalid_rows: list[dict], failure_cases_df).

    pandera 0.31 `SchemaErrors.failure_cases` has columns
    {schema_context, column, check, check_number, failure_case, index}.
    """
    try:
        valid = schema.validate(df, lazy=True)
        return valid, [], None
    except pae.SchemaErrors as exc:
        failure_cases = exc.failure_cases  # DataFrame
        bad_idx = failure_cases["index"].dropna().astype(int).unique()
        invalid_rows = df.loc[bad_idx].to_dict(orient="records")
        valid_df = df.drop(index=bad_idx)
        return valid_df, invalid_rows, failure_cases
```

> **Source provenance:** Pandera 0.31 ships the `pandera.pandas` accessor namespace and
> the lazy-validation `SchemaErrors` (plural) error type. [CITED: https://pandera.readthedocs.io/en/stable/lazy_validation.html]
> The exact dataframe-level Check signature (lambda over df) is the canonical idiom.
> [CITED: https://pandera.readthedocs.io/en/stable/dataframe_schemas.html#dataframe-checks]
> The `index` column on `failure_cases` is documented behavior. [ASSUMED — confirm during Wave 0
> by running a deliberately bad fixture; if shape differs, planner adapts the partition helper.]

### Pattern 2 — Tier 2 advisory dispatcher (D-06, DQ-02, DQ-03)

**What:** Tier 2 validators **always emit** the metric and the log; only the action (raise vs.
return) depends on the per-rule env flag. This keeps dashboards stable through the
shadow→strict promotion: same metric, only the `tier` label changes.

**Example:**

```python
# src/localstock/dq/shadow.py
from typing import Literal
from localstock.config.settings import settings  # Pydantic Settings

Mode = Literal["shadow", "enforce"]

def get_tier2_mode(rule_name: str) -> Mode:
    """Return per-rule mode, falling back to default."""
    explicit = getattr(settings, f"dq_tier2_{rule_name}_mode", None)
    return explicit or settings.dq_default_tier2_mode  # default 'shadow'
```

```python
# src/localstock/dq/runner.py — Tier 2 dispatch
from prometheus_client import REGISTRY
from loguru import logger
from localstock.dq.shadow import get_tier2_mode

def evaluate_tier2(rule: str, df, predicate, *, symbol: str | None = None):
    """Predicate returns offending rows DataFrame (empty = pass)."""
    bad = predicate(df)
    if bad.empty:
        return
    mode = get_tier2_mode(rule)
    tier = "advisory" if mode == "shadow" else "strict"
    counter = REGISTRY._names_to_collectors.get("localstock_dq_violations_total")
    if counter is not None:
        counter.labels(rule=rule, tier=tier).inc(len(bad))
    logger.warning("dq_warn", rule=rule, tier=tier, symbol=symbol,
                   violation_count=len(bad))
    if mode == "enforce":
        raise Tier2Violation(rule, bad)
```

> **D-06 implication:** the metric name `localstock_dq_violations_total{rule, tier}` must be
> registered in `observability/metrics.py` alongside the existing `op_*` family — this is the
> Phase 23 primitive registration site. [VERIFIED: `apps/prometheus/src/localstock/observability/metrics.py:36`]

### Pattern 3 — `sanitize_jsonb` (D-04, DQ-04, Pitfall 10)

**What:** Recursive walk over nested dict/list/scalar. Convert `float('inf')`, `float('-inf')`,
`NaN` to `None`. Handle pandas/numpy scalar types (`np.float64`, `pd.Timestamp`) since LLM
report dicts and DataFrame `.to_dict()` outputs both produce them.

**Example:**

```python
# src/localstock/dq/sanitizer.py
from __future__ import annotations
import math
from typing import Any

def sanitize_jsonb(value: Any) -> Any:
    """Replace NaN / +inf / -inf with None; recurse into dict/list/tuple.

    Idempotent and safe on None. Converts numpy scalars via float() so the
    output is always a JSON-native type.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: sanitize_jsonb(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_jsonb(v) for v in value]
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    # numpy float64 etc. — duck-type via __float__
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
    except (TypeError, ValueError):
        pass
    return value
```

> **Existing prior art:** `services/pipeline.py:_store_financials._clean_nan` (lines 275–283)
> already does this for the financial path. Phase 25 promotes it to a module and replaces the
> inlined helper. [VERIFIED: `apps/prometheus/src/localstock/services/pipeline.py:275`]

**For DataFrames specifically** (Pitfall 10 recipe):

```python
import numpy as np
clean_df = df.replace([np.inf, -np.inf], np.nan).where(df.notna(), None)
records = clean_df.to_dict(orient="records")
sanitized = sanitize_jsonb(records)  # belt-and-suspenders for nested
```

### Pattern 4 — `gather(return_exceptions=True)` per step (D-03, DQ-05)

**What:** Replace `for symbol in symbols: try/except` with `asyncio.gather(*coros,
return_exceptions=True)`, then partition results into successes and `(symbol, step, exception)`
failures. Surface failure detail through `failed_symbols` JSON.

**Example:**

```python
# Pattern for any per-symbol step
import asyncio
from loguru import logger

async def crawl_one(symbol: str):
    return symbol, await price_crawler.fetch(symbol)

async def crawl_all(symbols: list[str]) -> tuple[dict, list[dict]]:
    results = await asyncio.gather(
        *(crawl_one(s) for s in symbols),
        return_exceptions=True,
    )
    ok, failed = {}, []
    for s, r in zip(symbols, results):
        if isinstance(r, Exception):
            logger.warning("pipeline.step.failed",
                           symbol=s, step="crawl",
                           exception_class=type(r).__name__,
                           message=str(r)[:200])
            failed.append({"symbol": s, "step": "crawl",
                           "error": f"{type(r).__name__}: {str(r)[:200]}"})
        else:
            ok[r[0]] = r[1]
    return ok, failed
```

> **Interaction with `@observe`:** `@observe` wraps the **outer** function; per-symbol failures
> are inner. Don't decorate `crawl_one` — emit metrics from the loop itself or attach `@observe`
> to the batch function with `outcome='success'` if the batch completed (it does, even with
> per-symbol failures). [VERIFIED via `observability/decorators.py:73`]

> **CRITICAL — concurrency note:** `asyncio.gather` is **unbounded**. STACK.md "Don't Use" table
> explicitly flags this for the 400-stock fan-out: it will trip vnstock rate limits and exhaust
> the Postgres pool. CONTEXT.md D-03 says "or equivalent loop with try/except" — i.e. the safest
> minimum for Phase 25 is **keep the existing serial `for` loops but ensure each iteration is
> wrapped in try/except**. Concurrency tuning (`anyio.Semaphore`) is Phase 27. [CITED: STACK.md
> "Don't Use" table; 25-CONTEXT.md D-03; ROADMAP "Phase 27 Pipeline Performance"]

> **Recommended planner guidance:** in Wave 2, prefer the serial-with-try/except shape
> (Pitfall avoidance: don't introduce concurrency without bounded semaphore). The literal
> `gather(return_exceptions=True)` should only be used where concurrency is already bounded
> (e.g., `crawlers/base.py:fetch_batch` which already has its own pacing).

### Pattern 5 — Quarantine repo + retention cron (D-02, D-08)

**Schema (Alembic, Wave 0):**

```python
# Alembic migration excerpt — illustrative
op.create_table(
    "quarantine_rows",
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
    sa.Column("source", sa.String(32), nullable=False),  # 'ohlcv' | 'financials' | 'indicators'
    sa.Column("symbol", sa.String(16), nullable=True),
    sa.Column("payload", postgresql.JSONB(), nullable=False),
    sa.Column("reason", sa.Text, nullable=False),       # human-readable
    sa.Column("rule", sa.String(64), nullable=False),   # machine-readable: 'negative_price', etc.
    sa.Column("tier", sa.String(16), nullable=False),   # 'strict' | 'advisory'
    sa.Column("quarantined_at", sa.DateTime(timezone=True),
              server_default=sa.func.now(), nullable=False),
)
op.create_index("ix_quarantine_rows_source_qa",
                "quarantine_rows", ["source", "quarantined_at"])
op.create_index("ix_quarantine_rows_symbol",
                "quarantine_rows", ["symbol"])
```

**Repo:**

```python
# src/localstock/dq/quarantine_repo.py
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, UTC
from localstock.dq.sanitizer import sanitize_jsonb

class QuarantineRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, *, source: str, symbol: str | None,
                     payload: dict | list, reason: str, rule: str, tier: str):
        await self.session.execute(
            text("""INSERT INTO quarantine_rows
                    (source, symbol, payload, reason, rule, tier)
                    VALUES (:source, :symbol, CAST(:payload AS JSONB),
                            :reason, :rule, :tier)"""),
            {"source": source, "symbol": symbol,
             "payload": json.dumps(sanitize_jsonb(payload)),  # belt + suspenders
             "reason": reason, "rule": rule, "tier": tier},
        )

    async def cleanup_older_than(self, *, days: int = 30) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            text("DELETE FROM quarantine_rows WHERE quarantined_at < :cutoff"),
            {"cutoff": cutoff},
        )
        return result.rowcount or 0
```

**Retention cron (D-02, D-08 Wave 1):**

```python
# Add to scheduler/scheduler.py setup_scheduler()
@observe("dq.quarantine.cleanup")
async def _quarantine_cleanup_job():
    async with AsyncSessionLocal() as s:
        repo = QuarantineRepository(s)
        n = await repo.cleanup_older_than(days=30)
        await s.commit()
        logger.info("dq.quarantine.cleanup.done", deleted=n)

scheduler.add_job(
    _quarantine_cleanup_job,
    trigger=CronTrigger(hour=3, minute=15, timezone="Asia/Ho_Chi_Minh"),
    id="dq_quarantine_cleanup",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
)
```

> **Pitfall 6 echo:** explicit `timezone="Asia/Ho_Chi_Minh"` on the trigger — same convention
> as the existing daily pipeline job. [VERIFIED: `scheduler/scheduler.py:20`]

### Pattern 6 — `/health/data` extension (D-05, DQ-07)

**Current state:** Returns `{max_price_date, trading_days_lag, stale}` (lag > 1 → stale).
[VERIFIED: `api/routes/health.py:184-196`]

**Phase 25 extension:** Wrap into `data_freshness` nested block while keeping the existing
top-level keys for back-compat. Add `last_trading_day` (the calendar reference), `sessions_behind`
(synonym for `trading_days_lag` but explicit), `status` (`fresh` | `stale`). Configurable
threshold via `settings.dq_stale_threshold_sessions`.

```python
@router.get("/health/data")
async def health_data(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(func.max(StockPrice.date)))
    max_date = result.scalar_one_or_none()
    today = date.today()
    last_trading_day = _last_trading_day_on_or_before(today)  # NEW helper
    threshold = settings.dq_stale_threshold_sessions  # default 1

    if max_date is None:
        status_ = "stale"
        sessions_behind = None
    else:
        sessions_behind = _trading_days_lag(max_date, last_trading_day)
        status_ = "stale" if sessions_behind > threshold else "fresh"

    body = {
        # existing keys (back-compat — Helios doesn't consume but other ops scripts may)
        "max_price_date": max_date.isoformat() if max_date else None,
        "trading_days_lag": sessions_behind,
        "stale": status_ == "stale",
        # NEW (D-05)
        "data_freshness": {
            "last_trading_day": last_trading_day.isoformat(),
            "max_data_date": max_date.isoformat() if max_date else None,
            "sessions_behind": sessions_behind,
            "status": status_,
            "threshold_sessions": threshold,
        },
    }
    return body
```

**Testing strategy (date-rollback fixture):** existing test (`test_health_data_returns_freshness`)
already mocks the DB scalar to return a date. Phase 25 adds parametrized tests:
- `today` (lag=0) → `status='fresh'`
- `today - 1` (lag=1) → `status='fresh'` (default threshold)
- `today - 2` (lag=2) → `status='stale'`
- threshold=2 + `today - 2` → `status='fresh'` (env override test)
- `None` (empty DB) → `status='stale'`

[VERIFIED: existing test pattern at `apps/prometheus/tests/test_api/test_health_endpoints.py:88`]

### Pattern 7 — `PipelineRun.stats` migration + dual-write (D-07, DQ-06)

**Migration (Wave 0):**

```python
op.add_column(
    "pipeline_runs",
    sa.Column("stats", postgresql.JSONB(), nullable=True),
)
# No backfill — old rows keep stats=NULL, new rows get the dict.
```

**Model:**

```python
# db/models.py PipelineRun additions
stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

> **JSON vs JSONB note:** existing model uses generic `JSON` type. Postgres maps `JSON` →
> `JSON` (not `JSONB`). For new `stats` and `quarantine_rows.payload`, **explicitly use
> `postgresql.JSONB`** in the migration so we get index/GIN potential for free. The model
> column type can remain `sa.JSON` (SQLAlchemy will read JSONB transparently) — the migration's
> column type wins at the DDL level. [ASSUMED — verify by running the migration against a
> Postgres test DB and inspecting `\d pipeline_runs`. Existing `errors`, `content_json`, etc.
> are likely already JSONB at the DDL level despite the model declaring `JSON`; planner should
> confirm with `pg_dump --schema-only` or by checking earlier migrations.]

**Dual-write helper (D-07):**

```python
# In services/pipeline.py — replace lines 210-214
def _write_stats(run: PipelineRun, *, succeeded: int, failed: int,
                 skipped: int, failed_symbols: list[dict]) -> None:
    run.stats = {
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "failed_symbols": failed_symbols,  # [{"symbol": "BAD", "step": "crawl", "error": "..."}]
    }
    # Dual-write scalars through v1.5
    run.symbols_total = succeeded + failed + skipped
    run.symbols_success = succeeded
    run.symbols_failed = failed
    # Note: existing `errors` field stays for back-compat with rescue path (line 222).
    if failed_symbols and run.errors is None:
        run.errors = {"failed_symbols": [fs["symbol"] for fs in failed_symbols]}
```

**Tests verify mirroring is exact:** `assert run.symbols_success == run.stats["succeeded"]`.

## Audit List — D-03 (per-symbol loop fix surface)

Every per-symbol loop discovered by `grep -rn "for symbol in\|for sym in" services/ crawlers/`:
[VERIFIED: live grep output 2026-04-29]

| File | Line | Loop purpose | Currently isolated? | Action |
|------|------|--------------|---------------------|--------|
| `services/pipeline.py` | 341 | `_crawl_prices` per-symbol fetch | ✅ try/except already | Keep; add structured `step="crawl"` to log |
| `services/analysis_service.py` | 119 | per-symbol analyze | ❓ verify | Wrap in try/except; record `failed_symbols` with `step="analyze"` |
| `services/analysis_service.py` | 129 | per-symbol persist | ❓ verify | Wrap |
| `services/analysis_service.py` | 456 | per-symbol (helper) | ❓ verify | Wrap |
| `services/analysis_service.py` | 474 | per-symbol (helper) | ❓ verify | Wrap |
| `services/scoring_service.py` | 79 | `score_all` per-symbol | ❓ verify | Wrap with `step="score"` |
| `services/scoring_service.py` | 176 | scoring helper | ❓ verify | Wrap |
| `services/sentiment_service.py` | 100 | per-ticker sentiment | ❓ verify | Wrap with `step="sentiment"` |
| `services/sentiment_service.py` | 145 | per-symbol persist | ❓ verify | Wrap |
| `services/admin_service.py` | 115, 164, 191, 207, 228 | admin job dispatch | ❓ verify | Wrap with appropriate step name |
| `crawlers/finance_crawler.py` | 109 | per-symbol financial fetch | ❓ verify (likely returns failed list) | Confirm against `crawlers/base.py:39` shape |
| `crawlers/base.py` | 39 | base `fetch_batch` per-symbol | ✅ likely; returns `(results, failed)` | Confirm; this is the "good" pattern to mirror |

**Planner action:** Wave 2 plan for DQ-05 should:
1. Open each "❓ verify" file and confirm whether try/except already wraps the loop body.
2. For each unwrapped loop, apply the same `(results, failed)` return shape used by
   `crawlers/base.fetch_batch` (the canonical pattern in this codebase).
3. Plumb the `failed_symbols` list (with `step` field) up to `pipeline.py` so `_write_stats`
   can build the unified `stats.failed_symbols` JSON.

> Note: `report_service.py` is not in the grep result — confirm it has no per-symbol loop or
> uses a different idiom. Report generation likely already uses gather inside the LLM client.

## Audit List — D-04 (JSONB write call sites for sanitizer wiring)

Every call site that writes a JSONB column. [VERIFIED: grep `db/models.py` for `JSON` columns
+ ripgrep for setter patterns]

| Model.column | Write call site | Sanitizer wiring needed? |
|--------------|-----------------|--------------------------|
| `FinancialStatement.data` (line 105) | `db/repositories/financial_repo.py:52` (`upsert_statement(data=...)`) — caller in `services/pipeline.py:298,310` | YES — sanitize at repo entry point |
| `PipelineRun.errors` (line 130) | `services/pipeline.py:212-214, 222, 233, 249, 233`; `scheduler/scheduler.py:156` | YES — wrap dict at construction OR at repo write |
| `PipelineRun.stats` (NEW, D-07) | `services/pipeline.py:_write_stats` (new) | YES — sanitize before assignment |
| `CompositeScore.weights_json` (line 352) | `services/scoring_service.py:136` (`weights_json=weights`) | YES — wrap at scoring repo write |
| `Report.content_json` (line 392) | `services/report_service.py:331, 567` (`content_json=report.model_dump()`) | YES — wrap LLM-produced dict at repo entry |
| `IndicatorRun.details` (line 463) | `analysis/technical.py:72` (`params=params`)? — verify | YES — wrap params dict |
| `Job.params` (line 478) | `db/repositories/job_repo.py:31` (`params=params`); callers in `api/routes/admin.py:126,137,148,159,170` | LIKELY NO (params are user-supplied symbol lists, never NaN) — but cheap to add for uniformity |
| `Job.result` (line 479) | wherever job results are persisted (likely `services/admin_service.py`) | YES — job results may include numeric fields |
| `Notification.details` (line 463 — same line as IndicatorRun? verify) | `db/repositories/notification_repo.py:32` (`details=details`) | YES |

**Planner action:** Wave 1 plan for DQ-04 should:
1. Add `from localstock.dq.sanitizer import sanitize_jsonb` import to each repo.
2. Wrap every JSONB-bound parameter at the repository method entry: `data = sanitize_jsonb(data)`
   as the first line of the method body.
3. Add a unit test per repo that calls the method with `{"x": float('nan')}` and asserts the
   persisted row has `null` (or `None`) — Postgres test session required.
4. Replace inlined `_clean_nan` in `services/pipeline.py:_store_financials` (lines 275–283)
   with a call to the canonical `sanitize_jsonb`.
5. Property-test the helper itself with hypothesis (or table-driven if hypothesis not added).

> **Cross-check needed:** the audit assumes `services/pipeline.py:222, 233, 249` are the only
> "manual" `errors=...` constructions. Wave 1 should grep `errors\s*=\s*\{` once more to be safe.

## Audit List — Readers of `pipeline_runs.symbols_total/success/failed` (D-07 deprecation impact)

[VERIFIED: live grep output 2026-04-29]

| File | Line | Usage |
|------|------|-------|
| `services/automation_service.py` | 86, 87, 93, 94 | Reads `symbols_success`, `symbols_total` for Telegram digest formatting |
| `services/pipeline.py` | 135, 210, 211 | Writes (replace with `_write_stats` dual-write) |
| `scheduler/health_probe.py` | 64 | Reads `symbols_success` for Prometheus self-probe gauge |
| `observability/metrics.py` | 250 | Doc string only ("symbols_success of the most recent PipelineRun") — update doc to mention `stats.succeeded` |
| `tests/test_services/test_automation_service.py` | 71, 72, 122, 123, 165, 166, 211, 212, 251, 252, 364, 365 | Test mocks |
| `tests/test_scheduler/test_health_self_probe.py` | 50 | Test mock |

**Conclusion:** Two production readers (`automation_service`, `health_probe`) plus tests.
Dual-write through v1.5 keeps both working untouched. v1.6 cleanup means switching these two
files to read `run.stats["succeeded"]` instead. **No external consumers found** (no Helios
frontend usage; admin API doesn't expose these fields directly).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DataFrame schema validation | row-by-row Pydantic loop | pandera `DataFrameSchema` with `lazy=True` | [CITED: STACK.md "Don't Use" table] |
| Multi-error reporting from validation | accumulate-and-raise loop | pandera `SchemaErrors` (plural) + `failure_cases` DataFrame | Built-in, with row indices for partition |
| Recursive NaN/Inf sanitization | re-implement per call site | one shared `sanitize_jsonb` helper | D-04 makes this a hard requirement; chokepoint discipline |
| Cron-style retention | shell script + crontab | APScheduler in-process job | Already wired (Phase 22), survives container restart |
| VN trading-day calendar | re-derive | reuse `_VN_HOLIDAYS_2025_2026` + `_is_trading_day` | D-05 explicitly mandates this |
| Per-symbol failure tracking | log-only + post-hoc grep | `stats.failed_symbols` JSON list with `{symbol, step, error}` | D-07 explicit shape |
| Tier 2 promotion ramp | binary global flag | per-rule env flag with `tier` metric label | D-06 explicit |

## Common Pitfalls

### Pitfall A — `gather` without bounded concurrency

**What goes wrong:** Replacing `for symbol in symbols: try/except` with
`asyncio.gather(*coros)` looks like an "isolation upgrade" but explodes vnstock rate limits and
the Postgres pool. STACK.md "Don't Use" table flags this exact mistake.

**Why it happens:** Engineer reads "use `gather(return_exceptions=True)`" in the requirement
and applies it literally without noticing the existing serial loop is concurrency-bounded.

**How to avoid:** For Wave 2, prefer `for symbol in symbols: try/except` (per-iteration
isolation). Only use `gather` where the batch is already bounded (e.g., `crawlers/base.fetch_batch`).
Bounded concurrency tuning is **Phase 27, not Phase 25**.

**Warning signs:** Pipeline first run after Wave 2 lights up vnstock 429s; pool exhaustion
errors in `/health/ready`; runtime increases instead of decreases.

### Pitfall B — Pitfall 10 (NaN/Inf into JSONB) regressed via a new write path

**What goes wrong:** A new repo method or service forgets to call `sanitize_jsonb`, and one
column on one row poisons `/api/reports`.

**How to avoid:** D-04 wiring is mechanical — every JSONB column gets sanitizer at repo entry.
Wave 1 must include a unit test per repo. Add a lint rule (or just a doc-string convention) that
JSONB-bound repos call sanitizer on the first line.

**Warning signs:** `Out of range float values are not JSON compliant: nan` in logs;
`SELECT ... WHERE content_json::text LIKE '%NaN%'` returns rows.

### Pitfall C — Pitfall 11 (Tier 2 hard-gate aborts day one)

**What goes wrong:** Promoting a Tier 2 rule to enforce mode without reviewing 14-day shadow
data — pipeline starts rejecting 30%+ of symbols.

**How to avoid:** D-06 per-rule flags + D-03 14-day shadow policy. Runbook
`docs/runbook/dq-tier2-promotion.md` (Wave 3) is explicit: read `dq_violations_total{rule,
tier="advisory"}` over 14 days; only promote rules where rate is < 5%.

**Warning signs:** Spike in `dq_violations_total{tier="strict"}` immediately after promotion;
Telegram digest shows < 350 stocks.

### Pitfall D — `JSONB` vs `JSON` column type drift

**What goes wrong:** Migration declares `JSON` (text serialization) instead of `JSONB`
(binary). No GIN index possible; harder to query.

**How to avoid:** New columns explicitly use `postgresql.JSONB()` in Alembic migrations
(quarantine `payload`, `pipeline_runs.stats`). The SQLAlchemy model column type can stay
generic `JSON` — DDL is what matters at write time.

### Pitfall E — Pandera coerce side-effect on dates

**What goes wrong:** `coerce=True` on a `Column("datetime64[ns]")` silently parses any string;
a malformed `date` field that should reject becomes a `NaT` and may pass other checks.

**How to avoid:** Either drop coercion on the date column OR add an explicit `Check` for
`pd.notna(df["date"])` after coercion. Add a deliberate "malformed date" fixture in the Wave 0
RED tests so this is exercised.

### Pitfall F — APScheduler retention job collides with daily pipeline

**What goes wrong:** Cleanup job runs at 03:15, but a backfill admin job runs at 03:14 and
holds a long transaction; cleanup blocks on the table.

**How to avoid:** `quarantine_rows` is a separate table from the hot path — collision risk is
low. Still: schedule cleanup **at 03:15** explicitly (not midnight), away from the daily
15:46 pipeline window. `max_instances=1, coalesce=True` on the job (same as existing
`health_self_probe`).

### Pitfall G — `failed_symbols` blowing JSONB row size

**What goes wrong:** A 200-char error × 400 symbols × deeply nested traceback can push the
`stats` JSONB into MB territory.

**How to avoid:** CONTEXT.md specifies error truncation at 200 chars. Make this a constant in
`dq/__init__.py` (`MAX_ERROR_CHARS = 200`) and use everywhere. Add a unit test asserting
truncation.

## Runtime State Inventory

> **Not applicable** — Phase 25 is additive (new package, new table, new column, new env
> flags). No rename/refactor/migration of existing names. No stored data carries the new names
> until Phase 25 lands.
>
> - **Stored data:** None (Wave 0 migration creates new structures).
> - **Live service config:** New env flags (`DQ_TIER2_*_MODE`, `DQ_DEFAULT_TIER2_MODE`,
>   `DQ_STALE_THRESHOLD_SESSIONS`) — must be added to `.env.example` and any deployment manifest.
>   None of these break if unset (defaults are safe).
> - **OS-registered state:** None.
> - **Secrets/env vars:** None new — all DQ_* flags are non-secret config.
> - **Build artifacts:** `pandera[pandas]` install requires `uv sync` after the dep is added
>   to `pyproject.toml`. CI must re-resolve lockfile.

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | per `requires-python = ">=3.12"` | — |
| pandas | DQ-01 schema validation | ✓ | `>=2.2,<3.0` | — |
| numpy | DQ-04 sanitizer (`np.inf`) | ✓ | `>=2.0,<3.0` | — |
| pandera[pandas] | DQ-01, DQ-02 | ✗ | — | Wave 0 installs via `uv add` |
| Postgres + JSONB | DQ-08 quarantine, DQ-06 stats | ✓ (prod), tests use sqlite where possible | — | Tests gated by `requires_pg` marker (existing pattern) |
| APScheduler | DQ-08 retention cron | ✓ | `>=3.11,<4.0` | — |
| prometheus-client | DQ-02 violation counter | ✓ | `>=0.21,<1.0` | — |

**Missing dependencies with no fallback:** None (pandera is installed in Wave 0).

**Missing dependencies with fallback:** None.

## Validation Architecture

> Phase 25 must publish a VALIDATION.md per the Nyquist contract (config has
> `nyquist_validation: true`). The planner builds VALIDATION.md from this section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24 + pytest-timeout 2.x [VERIFIED: pyproject.toml] |
| Config file | `apps/prometheus/pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode=auto, timeout=30) |
| Marker for PG tests | `@pytest.mark.requires_pg` (existing) |
| Quick run command | `cd apps/prometheus && uv run pytest -x -k "dq_ or sanitize or quarantine or health_data or pipeline_run_stats"` |
| Full suite command | `cd apps/prometheus && uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Status |
|--------|----------|-----------|-------------------|-------------|
| DQ-01 | OHLCV row with negative price → quarantined | unit | `uv run pytest tests/test_dq/test_ohlcv_schema.py::test_negative_price_quarantined -x` | ❌ Wave 0 |
| DQ-01 | OHLCV row with future date → quarantined | unit | `... ::test_future_date_quarantined -x` | ❌ Wave 0 |
| DQ-01 | NaN ratio > 5% → quarantined | unit | `... ::test_nan_ratio_threshold -x` | ❌ Wave 0 |
| DQ-01 | Duplicate (symbol,date) → quarantined | unit | `... ::test_duplicate_pk -x` | ❌ Wave 0 |
| DQ-02 | RSI > 99.5 emits `dq_violations_total{rule="rsi_anomaly", tier="advisory"}` | unit | `tests/test_dq/test_tier2_dispatch.py::test_rsi_advisory_metric -x` | ❌ Wave 0 |
| DQ-02 | Gap > 30% emits warning, does NOT raise | unit | `... ::test_gap_shadow_no_raise -x` | ❌ Wave 0 |
| DQ-02 | Missing > 20% rows emits warning | unit | `... ::test_missing_rows_advisory -x` | ❌ Wave 0 |
| DQ-03 | `DQ_TIER2_RSI_MODE=enforce` causes raise | unit | `... ::test_promotion_to_strict_raises -x` | ❌ Wave 0 |
| DQ-03 | Runbook file exists at `docs/runbook/dq-tier2-promotion.md` | smoke | `pytest tests/test_docs/test_runbooks.py::test_tier2_promotion_runbook_exists -x` | ❌ Wave 0 |
| DQ-04 | `sanitize_jsonb({"x": nan})` returns `{"x": None}` | unit | `tests/test_dq/test_sanitizer.py::test_nan_to_none -x` | ❌ Wave 0 |
| DQ-04 | `sanitize_jsonb` recurses into nested dict/list | unit/property | `... ::test_recursive_sanitize -x` | ❌ Wave 0 |
| DQ-04 | `report_repo.upsert(content_json={"x": inf})` persists `null` | integration (PG) | `... ::test_report_repo_sanitizes -x -m requires_pg` | ❌ Wave 0 |
| DQ-04 | `financial_repo.upsert_statement` sanitizes | integration | `... ::test_financial_repo_sanitizes -x -m requires_pg` | ❌ Wave 0 |
| DQ-04 | `score_repo` sanitizes `weights_json` | integration | `... ::test_score_repo_sanitizes -x -m requires_pg` | ❌ Wave 0 |
| DQ-05 | One symbol raising in `_crawl_prices` doesn't kill batch | unit | `tests/test_services/test_pipeline_isolation.py::test_one_bad_symbol_completes_batch -x` | ❌ Wave 0 |
| DQ-05 | Failure recorded with `{symbol, step, error}` | unit | `... ::test_failed_symbols_step_recorded -x` | ❌ Wave 0 |
| DQ-05 | Analyze/score/report steps also isolate | unit | `... ::test_analyze_step_isolation -x` (etc per service) | ❌ Wave 0 |
| DQ-06 | `PipelineRun.stats` JSONB present after run | integration | `tests/test_services/test_pipeline_stats.py::test_stats_jsonb_written -x -m requires_pg` | ❌ Wave 0 |
| DQ-06 | Scalar columns mirror `stats` (`symbols_success == stats.succeeded`) | integration | `... ::test_dual_write_mirror -x -m requires_pg` | ❌ Wave 0 |
| DQ-06 | `stats.failed_symbols` truncates `error` to 200 chars | unit | `... ::test_error_truncation -x` | ❌ Wave 0 |
| DQ-07 | `/health/data` `status='stale'` when `max_date` lags > threshold | unit | `tests/test_api/test_health_data_freshness.py::test_stale_status -x` | ❌ Wave 0 |
| DQ-07 | `/health/data` `data_freshness` block contains 5 keys | unit | `... ::test_data_freshness_shape -x` | ❌ Wave 0 |
| DQ-07 | `DQ_STALE_THRESHOLD_SESSIONS=2` overrides default | unit | `... ::test_threshold_override -x` | ❌ Wave 0 |
| DQ-08 | `quarantine_rows` table exists | smoke | `tests/test_db/test_migrations.py::test_quarantine_rows_exists -x -m requires_pg` | ❌ Wave 0 |
| DQ-08 | `QuarantineRepository.insert(...)` persists row | integration | `tests/test_dq/test_quarantine_repo.py::test_insert -x -m requires_pg` | ❌ Wave 0 |
| DQ-08 | `cleanup_older_than(days=30)` deletes old rows only | integration | `... ::test_cleanup_30d -x -m requires_pg` | ❌ Wave 0 |
| DQ-08 | APScheduler job registered as `dq_quarantine_cleanup` | unit | `tests/test_scheduler/test_quarantine_cleanup.py::test_job_registered -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** Run the test files touched: `uv run pytest tests/test_dq/<file>.py -x`
  (typically < 5s).
- **Per wave merge:** Run `uv run pytest -x -k "dq_ or sanitize or quarantine or health_data or pipeline_run_stats"`
  (cross-cutting smoke).
- **Phase gate:** `uv run pytest` full suite green before `/gsd-verify-work`.

### Wave 0 Gaps (RED tests + scaffolds to land first)

- [ ] `tests/test_dq/__init__.py`
- [ ] `tests/test_dq/test_ohlcv_schema.py` — DQ-01 (4 tests)
- [ ] `tests/test_dq/test_tier2_dispatch.py` — DQ-02 + DQ-03 (4 tests)
- [ ] `tests/test_dq/test_sanitizer.py` — DQ-04 unit + property (3 tests)
- [ ] `tests/test_dq/test_quarantine_repo.py` — DQ-08 PG integration (2 tests)
- [ ] `tests/test_services/test_pipeline_isolation.py` — DQ-05 (3+ tests)
- [ ] `tests/test_services/test_pipeline_stats.py` — DQ-06 PG integration (3 tests)
- [ ] `tests/test_api/test_health_data_freshness.py` — DQ-07 (3 tests)
- [ ] `tests/test_db/test_migrations.py::test_quarantine_rows_exists` — DQ-08 smoke
- [ ] `tests/test_scheduler/test_quarantine_cleanup.py` — DQ-08 cron registration
- [ ] `tests/test_docs/test_runbooks.py` — DQ-03 runbook existence
- [ ] `src/localstock/dq/__init__.py`, `dq/schemas/__init__.py`, `dq/sanitizer.py`,
      `dq/shadow.py`, `dq/quarantine_repo.py`, `dq/runner.py`, `dq/schemas/ohlcv.py`,
      `dq/schemas/financials.py`, `dq/schemas/indicators.py` — empty/skeletal modules with
      RED-failing imports
- [ ] Alembic migration `<rev>_phase25_dq_tables.py` — `quarantine_rows` table +
      `pipeline_runs.stats` column
- [ ] `pyproject.toml` adds `pandera[pandas]>=0.31,<1.0`; `uv lock` regenerated
- [ ] `Settings` model adds `dq_tier2_*_mode`, `dq_default_tier2_mode`,
      `dq_stale_threshold_sessions` fields with safe defaults
- [ ] Metric `localstock_dq_violations_total{rule, tier}` registered in
      `observability/metrics.py`
- [ ] `docs/runbook/dq-tier2-promotion.md` placeholder file (filled in Wave 3)

## Project Constraints (from copilot-instructions.md / CLAUDE.md)

[VERIFIED: read CLAUDE.md, copilot-instructions.md absent at repo root — `copilot-instructions.md`
exists per `view` directory listing; treating CLAUDE.md as the canonical source for now.]

- **Async-first SQLAlchemy:** All repos use `AsyncSession`. Quarantine repo and stats
  writes follow the same pattern. [CITED: existing repos under
  `apps/prometheus/src/localstock/db/repositories/`]
- **Vietnamese content where applicable:** Runbook for Tier 2 promotion (DQ-03) — tone may be
  English (operational doc), but error messages user-facing in Helios stay Vietnamese; this
  phase has no user-facing UI changes.
- **`uv` for dep management:** Wave 0 uses `uv add` not `pip install`.
- **`@observe` decorator:** New service-layer entry points (`_quarantine_cleanup_job`,
  `_write_stats` if it grows) wear `@observe("dq.<subsystem>.<action>")`. [VERIFIED:
  pattern in `scheduler/scheduler.py:34`]
- **Idempotent metric registration:** `localstock_dq_violations_total` must use the
  duplicate-name try/except guard already established in `observability/metrics.py:60`.
- **Naming convention:** Counter is `localstock_dq_violations_total` — matches Phase 23 D-01
  prefix rule (`localstock_` namespace).
- **No `symbol` label on metrics:** Phase 23 D-06/OBS-09 hard rule. `dq_violations_total`
  carries `{rule, tier}`, never `symbol`. Symbol stays in structured logs only.
  [CITED: `observability/metrics.py:11`]
- **APScheduler timezone explicit:** `timezone="Asia/Ho_Chi_Minh"` on every job, per
  Pitfall 6.

## Security Domain

> Note: this phase is data-quality not auth-critical. Security surface is narrow but real
> (quarantine table holds raw third-party payloads; env flags affect production behavior).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no new auth surface) |
| V3 Session | no | — |
| V4 Access Control | no | — (no new endpoints with auth) |
| V5 Input Validation | **yes** | pandera schemas validate every OHLCV/financials write; sanitizer scrubs LLM-produced JSON. **This phase IS the V5 control.** |
| V6 Cryptography | no | — |
| V7 Error handling & logging | yes | Structured logs (loguru) for `dq_warn`; PII not in payloads (only HOSE tickers + market data). Error truncation (200 chars) prevents log injection bloat. |
| V9 Data protection | partial | Quarantine `payload` JSONB stores raw third-party data — no PII expected, but planner should add a doc note that quarantine is operational and 30-day retention applies. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM JSON injection (NaN/Inf strings) | Tampering | `sanitize_jsonb` strips them; D-04 |
| Pipeline DoS via one bad symbol | DoS | Per-symbol isolation; D-03/D-05 |
| Tier 2 promotion blast radius | DoS (self-inflicted) | Per-rule env flags, 14-day shadow window; D-06 |
| Quarantine table unbounded growth | Resource exhaustion | 30-day retention cron; D-02 |
| `errors` field as log injection sink | Log injection | 200-char truncation; D-07 |
| JSON parse errors at API boundary | Information disclosure | Sanitizer catches NaN/Inf at write time, not read time; Pitfall 10 |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled `_clean_nan` inlined per service (`pipeline.py:275`) | Shared `dq.sanitizer.sanitize_jsonb` | Phase 25 | Single source of truth; testable |
| `for symbol in symbols:` with no try/except | Per-iteration try/except + `failed_symbols` JSON | Phase 25 (D-03) | Pipeline doesn't abort on first bad symbol |
| Scalar `symbols_total/success/failed` only | Dual-write to `PipelineRun.stats` JSONB | Phase 25 (D-07); cleanup v1.6 | Forward-compat for warnings/skipped counts |
| `/health/data` returns 3 fields | Adds `data_freshness` block + configurable threshold | Phase 25 (D-05) | Better ops signal; back-compat preserved |
| No DataFrame-level schema validation | pandera `DataFrameSchema` Tier 1 + Tier 2 | Phase 25 (D-01) | Bad data quarantined, not silently stored |

**Deprecated/outdated:**
- Inlined `_clean_nan` in `services/pipeline.py:_store_financials` — replace with shared helper.
- Reading `run.symbols_success` directly — prefer `run.stats.get("succeeded")` going forward
  (deprecation in v1.6, dual-write through v1.5).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SchemaErrors.failure_cases` has an `index` column referencing original row position | Pattern 1 | LOW — verify with a deliberate bad fixture in Wave 0; if shape differs, partition helper adapts |
| A2 | Existing model `JSON` column type maps to Postgres JSONB at the DDL level (per earlier migrations) | Pattern 7 / Pitfall D | MEDIUM — planner should `pg_dump --schema-only pipeline_runs` to confirm; if it's `JSON` not `JSONB`, GIN-index option lost but functionality unaffected |
| A3 | Hypothesis is acceptable to add as a dev-dependency for sanitizer property tests | Standard Stack / Wave 0 | LOW — falls back to table-driven test if rejected |
| A4 | All currently unwrapped per-symbol loops in `services/` are safely wrappable without changing public service signatures | Audit List D-03 | MEDIUM — planner should open each "❓ verify" entry before committing wave 2 plan dependency graph |
| A5 | LLM JSON outputs (`Report.content_json`) won't include nested non-JSON-native types beyond float/int/str/dict/list | Pattern 3 sanitizer | LOW — sanitizer falls through unchanged for unknown types; worst case is asyncpg rejects on insert (loud failure, not silent corruption) |
| A6 | `copilot-instructions.md` exists at repo root but is consistent with CLAUDE.md | Project Constraints | LOW — both should be re-read during Wave 0 if ambiguity surfaces |
| A7 | `_VN_HOLIDAYS_2025_2026` semantics in `health.py` produce a `last_trading_day` correctly (the existing 24-04 helper computes lag, not the calendar's `last <= today` directly) | Pattern 6 | LOW — Phase 25 adds `_last_trading_day_on_or_before` helper; existing `_trading_days_lag` is reusable |

## Open Questions

1. **Should `Job.params` and `Job.result` (admin queue) get sanitizer wiring?**
   - What we know: `params` is user-supplied symbol list (low NaN risk); `result` may contain
     numeric stats from job execution.
   - What's unclear: whether D-04 ("every JSONB column") is meant literally or only for
     pipeline-data columns.
   - Recommendation: apply uniformly — D-04 says "every", and the cost is one line per repo.

2. **Pandera schema reuse vs. duplication for Tier 1/Tier 2 OHLCV?**
   - What we know: D-01 says "schemas can be unit-tested in isolation"; both tiers operate on
     the same DataFrame shape.
   - What's unclear: whether Tier 2 should `extend()` Tier 1 or stand alone.
   - Recommendation: stand-alone schemas. Tier 2 is advisory and may run independently when
     Tier 1 has already partitioned the frame; sharing complicates the dispatch.

3. **Should `quarantine_rows.payload` be `JSONB` (preferred) or `JSON`?**
   - Recommendation: `JSONB` — explicitly in Alembic migration. Future ad-hoc queries (`payload
     ->> 'symbol'`) become indexable.

4. **Where do `report_service.py` per-symbol loops live (D-03 audit gap)?**
   - The grep didn't find them. Either report generation already uses concurrency primitives
     (e.g., `gather` inside the LLM client) or it's serial-internal-to-the-method.
   - Recommendation: Wave 2 plan must include a "open `report_service.py` and confirm" task
     before declaring DQ-05 complete.

5. **Is the Pydantic `Settings` model in `config/settings.py` or elsewhere?**
   - Not verified in this research. Wave 0 plan should `grep -rn "BaseSettings"` and confirm.

## Sources

### Primary (HIGH confidence)
- `apps/prometheus/src/localstock/services/pipeline.py` (lines 117–369) — pipeline structure,
  existing `_clean_nan` helper, `_step_timer` pattern.
- `apps/prometheus/src/localstock/api/routes/health.py` (lines 30–196) — `_VN_HOLIDAYS_2025_2026`,
  `/health/data` current shape.
- `apps/prometheus/src/localstock/db/models.py` (lines 117–479) — JSONB-bearing columns inventory.
- `apps/prometheus/src/localstock/observability/metrics.py` (lines 1–120) — metric registration
  patterns, idempotent registration helper.
- `apps/prometheus/src/localstock/scheduler/scheduler.py` (lines 1–100) — APScheduler
  `add_job` patterns, timezone convention.
- `.planning/phases/25-data-quality/25-CONTEXT.md` — locked decisions D-01..D-08.
- `.planning/research/STACK.md` — pandera version pin, "Don't Use" table (gather, GE).
- `.planning/research/PITFALLS.md` Pitfalls 10 + 11 — NaN/Inf JSONB; Tier 2 hard-gate.
- `.planning/REQUIREMENTS.md` — DQ-01..DQ-08 verbatim.

### Secondary (MEDIUM confidence)
- pandera 0.31 documentation: lazy validation, DataFrame-level checks, `SchemaErrors`. [CITED:
  https://pandera.readthedocs.io/en/stable/lazy_validation.html ;
  https://pandera.readthedocs.io/en/stable/dataframe_schemas.html]
- APScheduler `add_job` + `CronTrigger` semantics — already exercised in this codebase
  (Phase 22).

### Tertiary (LOW confidence — flagged in Assumptions Log)
- Exact shape of `SchemaErrors.failure_cases.index` column (A1).
- DDL-level `JSON` vs `JSONB` for existing columns (A2).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already pinned in pyproject or STACK.md.
- Architecture (D-01..D-08): HIGH — CONTEXT.md is fully locked, this research only fills idioms.
- Sanitizer recipe: HIGH — already proven in `pipeline.py:275`.
- Pandera idioms: MEDIUM — version pinned but exact `failure_cases.index` shape is A1.
- Audit list D-03: MEDIUM — grep is comprehensive but "❓ verify" entries need eyes-on per file.
- Audit list D-04: HIGH — every JSONB column accounted for.
- `/health/data` extension: HIGH — existing endpoint and tests are precise references.

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (30 days — pandera and pandas are stable; refresh if Phase 25 slips
> 1 month or pandera 1.0 ships).

## RESEARCH COMPLETE
