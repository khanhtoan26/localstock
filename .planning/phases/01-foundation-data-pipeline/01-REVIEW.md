---
phase: 01-foundation-data-pipeline
reviewed: 2025-07-18T10:45:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - alembic/env.py
  - src/localstock/api/app.py
  - src/localstock/api/routes/health.py
  - src/localstock/config.py
  - src/localstock/crawlers/base.py
  - src/localstock/crawlers/company_crawler.py
  - src/localstock/crawlers/event_crawler.py
  - src/localstock/crawlers/finance_crawler.py
  - src/localstock/crawlers/price_crawler.py
  - src/localstock/db/database.py
  - src/localstock/db/models.py
  - src/localstock/db/repositories/event_repo.py
  - src/localstock/db/repositories/financial_repo.py
  - src/localstock/db/repositories/price_repo.py
  - src/localstock/db/repositories/stock_repo.py
  - src/localstock/services/pipeline.py
  - src/localstock/services/price_adjuster.py
  - tests/conftest.py
  - tests/test_crawlers/test_company_crawler.py
  - tests/test_crawlers/test_finance_crawler.py
  - tests/test_crawlers/test_price_crawler.py
  - tests/test_db/test_price_repo.py
  - tests/test_db/test_stock_repo.py
  - tests/test_services/test_pipeline.py
  - tests/test_services/test_price_adjuster.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2025-07-18T10:45:00Z
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

Phase 01 implements the foundation data pipeline: ORM models, crawlers (price, company, finance, events), repositories with upsert semantics, backward price adjustment, pipeline orchestrator, and a health check endpoint. The code is well-structured with clear separation of concerns, good docstrings, and solid test coverage.

**Key concerns:**
1. **Critical:** The database session factory creates a new engine (and connection pool) on every request — connection pooling is completely defeated.
2. **Deprecated APIs:** `asyncio.get_event_loop()` and `datetime.utcnow` are used throughout, both deprecated in Python 3.12+ (the project targets 3.12+).
3. **Event loop blocking:** `fetch_and_store_listings()` calls synchronous vnstock in an async method without `run_in_executor()`.
4. **Logic gap:** Corporate events with null ratio/exright_date are never marked as processed, causing infinite re-evaluation on every pipeline run.

## Critical Issues

### CR-01: Database engine recreated on every session request — connection pooling defeated

**File:** `src/localstock/db/database.py:32-36`
**Issue:** `get_session()` calls `get_session_factory()` which calls `get_engine()` on every invocation. Since none of these are cached, a **new** `AsyncEngine` with a new connection pool is created for every request. This defeats the purpose of `pool_size=5` and `max_overflow=10` — the pool is thrown away immediately. Under load, this will exhaust database connections and cause connection refused errors.
**Fix:**
```python
from functools import lru_cache

@lru_cache
def get_engine():
    """Create async SQLAlchemy engine from settings (cached singleton)."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )

@lru_cache
def get_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    """Create async session factory (cached singleton)."""
    if engine is None:
        engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
```

## Warnings

### WR-01: `asyncio.get_event_loop()` deprecated — use `asyncio.get_running_loop()`

**File:** `src/localstock/crawlers/company_crawler.py:62`, `src/localstock/crawlers/event_crawler.py:65`, `src/localstock/crawlers/finance_crawler.py:100`, `src/localstock/crawlers/price_crawler.py:61`
**Issue:** `asyncio.get_event_loop()` has been deprecated since Python 3.10 and emits a `DeprecationWarning` in 3.12+. When called from an async context (which all these crawlers are), `asyncio.get_running_loop()` is the correct replacement. `get_event_loop()` can also create a new event loop in non-async contexts, which would silently produce incorrect behavior.
**Fix:** In all four crawler files, replace:
```python
loop = asyncio.get_event_loop()
df = await loop.run_in_executor(None, _sync_fetch)
```
with:
```python
loop = asyncio.get_running_loop()
df = await loop.run_in_executor(None, _sync_fetch)
```

### WR-02: `datetime.utcnow` deprecated — use `datetime.now(UTC)`

**File:** `src/localstock/db/models.py:38`, `src/localstock/db/models.py:102`
**Issue:** `datetime.utcnow` is deprecated in Python 3.12+ (PEP 728). It returns a naive datetime without timezone info, which can lead to ambiguous timestamp comparisons. The rest of the codebase already uses `datetime.now(UTC)` correctly (e.g., `stock_repo.py:54`, `financial_repo.py:55`), making this inconsistent.
**Fix:**
```python
from datetime import UTC, datetime

# Line 38 (Stock model)
updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

# Line 102 (FinancialStatement model)
fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

### WR-03: `fetch_and_store_listings()` blocks the event loop with synchronous vnstock call

**File:** `src/localstock/db/repositories/stock_repo.py:95-99`
**Issue:** `fetch_and_store_listings()` is an async method but calls `Vnstock().stock().listing.all_symbols()` synchronously on lines 97-99. All other crawlers correctly wrap synchronous vnstock calls in `loop.run_in_executor()`. This call will block the async event loop, freezing all concurrent requests until the vnstock API responds.
**Fix:**
```python
async def fetch_and_store_listings(self, source: str = "VCI") -> int:
    import asyncio
    from vnstock import Vnstock

    def _sync_fetch():
        client = Vnstock(source=source)
        listing = client.stock().listing
        return listing.all_symbols()

    loop = asyncio.get_running_loop()
    all_symbols_df = await loop.run_in_executor(None, _sync_fetch)

    # Filter to HOSE exchange
    hose_df = all_symbols_df[all_symbols_df["exchange"] == "HOSE"].copy()
    # ... rest unchanged
```

### WR-04: Corporate events with null ratio or exright_date are never marked as processed

**File:** `src/localstock/services/pipeline.py:181-233`
**Issue:** The `_apply_price_adjustments()` method has two branches: (1) adjustable events with valid ratio + exright_date (line 182-226), and (2) non-adjustable events with valid ratio + exright_date (line 227-233). Events where `ratio` is None/0.0 **or** `exright_date` is None fall through both branches without being marked as processed. These events will be re-evaluated on every pipeline run indefinitely, accumulating as a growing list over time.
**Fix:** Add a final `else` branch to handle events that can never be processed:
```python
            elif event.ratio and event.exright_date:
                # Mark non-adjustable events as processed (cash dividends, etc.)
                await self.event_repo.mark_processed(event.id)
                logger.info(
                    f"Skipped adjustment for {event.symbol} "
                    f"({event.event_type}): not an adjustable event type"
                )
            else:
                # Events missing ratio or exright_date — mark processed to avoid infinite loop
                await self.event_repo.mark_processed(event.id)
                logger.warning(
                    f"Marking event {event.id} for {event.symbol} as processed: "
                    f"missing ratio ({event.ratio}) or exright_date ({event.exright_date})"
                )
```

### WR-05: `get_latest_period` uses string sort on period column — fragile ordering

**File:** `src/localstock/db/repositories/financial_repo.py:107-109`
**Issue:** `FinancialStatement.period.desc()` sorts period strings in reverse alphabetical order. For values `Q1`, `Q2`, `Q3`, `Q4`, `annual`: alphabetical sort places `annual` > `Q4` > `Q3` > `Q2` > `Q1`. This coincidentally works because 'annual' comes after 'Q4' alphabetically and also chronologically represents the full year. However, this ordering is fragile and will break if new period values are introduced (e.g., `H1` for half-year would sort between `Q1` and `Q2`, incorrectly treated as more recent than `Q2`).
**Fix:** Use a SQL `CASE` expression for deterministic ordering, or document the constraint that only `Q1`-`Q4` and `annual` are valid period values:
```python
from sqlalchemy import case

period_order = case(
    (FinancialStatement.period == "annual", 5),
    (FinancialStatement.period == "Q4", 4),
    (FinancialStatement.period == "Q3", 3),
    (FinancialStatement.period == "Q2", 2),
    (FinancialStatement.period == "Q1", 1),
    else_=0,
)

stmt = (
    select(FinancialStatement.year, FinancialStatement.period)
    .where(...)
    .order_by(FinancialStatement.year.desc(), period_order.desc())
    .limit(1)
)
```

## Info

### IN-01: Redundant individual `symbol` index alongside composite index

**File:** `src/localstock/db/models.py:47,60`
**Issue:** `StockPrice.symbol` has `index=True` (line 47), and a composite index `ix_stock_prices_symbol_date` on `(symbol, date)` is defined at line 60. The composite index already covers queries filtering by `symbol` alone, making the individual `symbol` index redundant. The individual `date` index (line 48) is still useful for date-only queries.
**Fix:** Remove `index=True` from the `symbol` column:
```python
symbol: Mapped[str] = mapped_column(String(10))  # covered by composite index
```

### IN-02: Inline `import pandas` inside pipeline method body

**File:** `src/localstock/services/pipeline.py:193`
**Issue:** `import pandas as pd` is placed inside `_apply_price_adjustments()` method body, while pandas is already imported at the top of every other module that uses it. This appears to be an oversight rather than a deliberate lazy import.
**Fix:** Move to top of file with other imports:
```python
import pandas as pd  # at top of file
```

### IN-03: Redundant null guard in health endpoint

**File:** `src/localstock/api/routes/health.py:49`
**Issue:** The `completed_at` formatting (line 49) checks `if run and run.completed_at`, but the entire dict is already inside a ternary `{...} if run else None` (line 55). The `run and` part is redundant since `run` is guaranteed to be truthy within the dict construction.
**Fix:**
```python
"completed_at": run.completed_at.isoformat() if run.completed_at else None,
```

---

_Reviewed: 2025-07-18T10:45:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
