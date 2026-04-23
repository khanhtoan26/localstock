# Phase 11: Admin API Endpoints - Research

**Researched:** 2026-04-22
**Domain:** FastAPI REST API, PostgreSQL schema migration, async background tasks
**Confidence:** HIGH

## Summary

Phase 11 adds a new `/api/admin/*` router to the existing FastAPI backend with endpoints for stock watchlist management (add/remove symbols), granular pipeline step triggers (crawl, analyze, score, report), and job history/status monitoring. The codebase already has all the service-layer building blocks — Pipeline, AnalysisService, ScoringService, ReportService — and established patterns for router registration, session injection, Pydantic validation, and asyncio-based concurrency control.

The main new work is: (1) an Alembic migration adding `is_tracked` to the `stocks` table, (2) a new `AdminJob` model for granular job tracking with its own table, (3) new StockRepository methods for watchlist operations, (4) the admin router module with 8 endpoints, and (5) `asyncio.create_task` for fire-and-forget execution that returns a job ID immediately. The existing automation endpoint pattern (`POST /automation/run` with `_pipeline_lock`) provides a close template, but admin endpoints differ by returning a job ID immediately rather than blocking until completion.

**Primary recommendation:** Follow existing codebase patterns exactly — new `admin.py` router file, Pydantic request models inline, services instantiated per-request with session injection. Use `asyncio.create_task` for background execution (not FastAPI `BackgroundTasks`, which ties to request lifecycle). Create a dedicated `admin_jobs` table rather than overloading the existing `pipeline_runs` table.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** New router at `/api/admin/*` — separate from existing `/api/automation/*` to cleanly distinguish admin operations from public endpoints. Easier to add auth later if needed.
- **D-02:** DB persistence for job tracking — use PostgreSQL (extend or leverage existing `pipeline_runs` table). Enables job history queries, survives server restart, aligns with existing async DB patterns.
- **D-03:** Add `is_tracked` boolean column to existing `stocks` table (default: true for backward compat). Pipeline and analysis services filter by `is_tracked=true`. No separate watchlist table.
- **D-03a:** Alembic migration required for the new column.
- **D-04:** Individual step triggers — separate endpoints for crawl, analyze, score, and report generation. Each can target 1 or more symbols.
- **D-04a:** Each granular operation creates its own job record for tracking.

### Agent's Discretion
- Request/response Pydantic models — agent decides schema structure
- Error handling patterns — follow existing convention (HTTPException with detail)
- Job status enum values — agent picks appropriate states (e.g., pending/running/completed/failed)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADMIN-01 | Stock watchlist management (add/remove symbols) | Stock model `is_tracked` column + new StockRepository methods + POST/DELETE endpoints |
| ADMIN-02 | Granular pipeline triggers (crawl, analyze, score, report) | Direct calls to existing service layer (Pipeline, AnalysisService, ScoringService, ReportService) + asyncio.create_task for background execution |
| ADMIN-03 | Full pipeline trigger | AutomationService.run_daily_pipeline(force=True) via admin endpoint + job tracking |
| ADMIN-04 | Job history and status monitoring | New AdminJob model + JobRepository + GET endpoints for list/detail |
</phase_requirements>

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135+ | REST API framework | Already the project's API framework, provides APIRouter, HTTPException, BackgroundTasks, Depends [VERIFIED: pyproject.toml] |
| Pydantic | 2.13+ | Request/response validation | Already a FastAPI dependency, used in macro.py for request models [VERIFIED: codebase macro.py] |
| SQLAlchemy | 2.0+ | ORM & async DB operations | Already used for all models and repositories [VERIFIED: codebase models.py] |
| Alembic | 1.18+ | Database migrations | Already used for schema changes [VERIFIED: alembic/versions/] |
| asyncpg | 0.31+ | Async PostgreSQL driver | Already used for database connections [VERIFIED: pyproject.toml] |

### Supporting (no new packages needed)
This phase requires zero new Python dependencies. All needed functionality is covered by the existing stack.

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
apps/prometheus/src/localstock/
├── api/routes/
│   └── admin.py              # NEW — admin router with all 8 endpoints
├── db/
│   ├── models.py             # MODIFIED — add is_tracked to Stock, add AdminJob model
│   └── repositories/
│       ├── stock_repo.py     # MODIFIED — add watchlist methods
│       └── job_repo.py       # NEW — AdminJob CRUD
├── services/
│   └── admin_service.py      # NEW — orchestrates admin operations with job tracking
└── api/
    └── app.py                # MODIFIED — register admin router
apps/prometheus/alembic/versions/
    └── add_phase11_admin_columns.py  # NEW — migration
apps/prometheus/tests/
    └── test_api/
        └── test_admin.py     # NEW — admin endpoint tests
```

### Pattern 1: Router Registration (Established)
**What:** Each feature gets its own router file, imported and included in `app.py`.
**When to use:** Every new set of API endpoints.
**Example (from existing codebase):**
```python
# Source: apps/prometheus/src/localstock/api/app.py [VERIFIED: codebase]
from localstock.api.routes.admin import router as admin_router
app.include_router(admin_router, tags=["admin"])
```

### Pattern 2: Session Injection via Depends (Established)
**What:** Routes receive AsyncSession via FastAPI Depends, pass to services.
**When to use:** Every endpoint that accesses the database.
**Example (from existing codebase):**
```python
# Source: apps/prometheus/src/localstock/api/routes/scores.py [VERIFIED: codebase]
from localstock.db.database import get_session

@router.get("/admin/jobs")
async def list_jobs(
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    jobs = await repo.list_recent(limit=50)
    return {"jobs": jobs, "count": len(jobs)}
```

### Pattern 3: Pydantic Request Models (Established)
**What:** Inline Pydantic BaseModel classes for request body validation.
**When to use:** POST endpoints with structured request bodies.
**Example (from existing codebase):**
```python
# Source: apps/prometheus/src/localstock/api/routes/macro.py [VERIFIED: codebase]
class MacroInput(BaseModel):
    indicator_type: str = Field(
        pattern=r"^(interest_rate|exchange_rate_usd_vnd|cpi|gdp)$",
    )
```

### Pattern 4: Background Task Execution with Job Tracking
**What:** Long-running operations launched via `asyncio.create_task()`, tracked with a job record in DB.
**When to use:** Admin endpoints that trigger crawl, analyze, score, or pipeline (operations taking seconds to minutes).
**Why not FastAPI BackgroundTasks:** FastAPI's `BackgroundTasks` runs after the response is sent but still within the request lifecycle. For long-running tasks (minutes), `asyncio.create_task()` with an explicit session factory is more robust — matches the existing `AutomationService` pattern which creates its own sessions.
**Example:**
```python
# Pattern: create job record → return job ID → run in background
async def trigger_crawl(request: CrawlRequest, session: AsyncSession = Depends(get_session)):
    job_repo = JobRepository(session)
    job = await job_repo.create_job(
        job_type="crawl",
        params={"symbols": request.symbols},
    )
    # Fire and forget — AdminService manages its own sessions
    asyncio.create_task(_run_crawl_background(job.id, request.symbols))
    return {"job_id": job.id, "status": "pending"}

async def _run_crawl_background(job_id: int, symbols: list[str]):
    """Background task with its own session lifecycle."""
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            job_repo = JobRepository(session)
            await job_repo.update_status(job_id, "running")
        # ... do work with separate sessions per step ...
        async with session_factory() as session:
            job_repo = JobRepository(session)
            await job_repo.update_status(job_id, "completed", result={...})
    except Exception as e:
        async with session_factory() as session:
            job_repo = JobRepository(session)
            await job_repo.update_status(job_id, "failed", error=str(e))
```

### Pattern 5: Concurrency Lock (Established)
**What:** Module-level `asyncio.Lock()` prevents concurrent execution of the same operation.
**When to use:** Any admin operation that should not run concurrently (pipeline, crawl).
**Example (from existing codebase):**
```python
# Source: apps/prometheus/src/localstock/api/routes/automation.py [VERIFIED: codebase]
_pipeline_lock = asyncio.Lock()

if _pipeline_lock.locked():
    raise HTTPException(status_code=409, detail="Pipeline already in progress")
```

### Anti-Patterns to Avoid
- **Don't block the response:** Admin endpoints that trigger long operations MUST return a job ID immediately, not block for minutes. The success criteria explicitly states "returns job ID".
- **Don't share sessions across async boundaries:** Background tasks must create their own sessions via `get_session_factory()`, not reuse the request session (which is scoped to the request lifecycle).
- **Don't create a separate watchlist table:** D-03 explicitly says `is_tracked` column on `stocks` table. No separate table.
- **Don't modify PipelineRun for admin jobs:** The existing PipelineRun has crawl-specific columns (symbols_total, symbols_success, symbols_failed). A new `AdminJob` table with generic JSON result/error columns is cleaner for tracking diverse operation types (crawl, analyze, score, report, pipeline).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation | Manual input checking | Pydantic BaseModel with Field constraints | Already used in macro.py; handles type coercion, error messages, OpenAPI docs [VERIFIED: codebase] |
| Path parameter validation | Manual regex/validation | FastAPI Path(..., pattern=...) | Already used in automation.py for symbol validation [VERIFIED: codebase] |
| Database migrations | Raw SQL ALTER TABLE | Alembic revision with `op.add_column()` | Existing migration infrastructure [VERIFIED: codebase] |
| Concurrent execution guard | Custom locking | asyncio.Lock() at module level | Established pattern in automation.py, scores.py, reports.py [VERIFIED: codebase] |
| JSON serialization | Manual dict building | Pydantic model `.model_dump()` for responses | Ensures consistent response shapes |
| Session management | Manual engine/connection | `get_session()` dependency + `get_session_factory()` for background tasks | Established patterns [VERIFIED: codebase] |

**Key insight:** This phase is almost entirely "glue code" — connecting existing services to new HTTP endpoints with job tracking. The services (Pipeline, AnalysisService, ScoringService, ReportService) already expose the right methods (`run_full()`, `run_single()`). The main new logic is the job tracking layer and the background task orchestration.

## Common Pitfalls

### Pitfall 1: Session Lifecycle in Background Tasks
**What goes wrong:** Using the request-scoped session (from `Depends(get_session)`) in a background task — session closes when request ends, background task fails with "Session is closed".
**Why it happens:** FastAPI's `get_session()` yields a session tied to the request lifecycle.
**How to avoid:** Background tasks MUST call `get_session_factory()` and create their own sessions. This is already the pattern used by `AutomationService.__init__()` which calls `self.session_factory = get_session_factory()`.
**Warning signs:** `sqlalchemy.exc.InvalidRequestError: This Session's transaction has been committed` or similar session-closed errors in background task logs.

### Pitfall 2: is_tracked=True Default and Existing Data
**What goes wrong:** Adding `is_tracked` column with `default=True` in the ORM model but NOT setting `server_default` in the migration, leaving existing rows as NULL.
**Why it happens:** SQLAlchemy's Python-side `default` only applies to new inserts through the ORM, not to existing rows.
**How to avoid:** In the Alembic migration, use `server_default=sa.text("true")` so existing rows get `is_tracked=TRUE`. Then the Python default in the model handles new ORM inserts.
**Warning signs:** `WHERE is_tracked = true` filtering out all existing stocks.

### Pitfall 3: Pipeline Lock Scope for Granular Operations
**What goes wrong:** Using a single `_pipeline_lock` for all admin operations — triggering a crawl blocks analyze, score, etc.
**Why it happens:** Copy-pasting the automation endpoint pattern without thinking about granularity.
**How to avoid:** Consider separate locks per operation type, OR use a single admin lock since these operations share DB state and running concurrently could cause data inconsistency (e.g., scoring while crawl is still updating prices). A single `_admin_lock` is simpler and safer for a personal tool.
**Warning signs:** User tries to run analysis while crawl is happening; either both run (data consistency issues) or one is incorrectly blocked.

### Pitfall 4: Missing CORS for Admin Endpoints
**What goes wrong:** Admin endpoints return CORS errors from the frontend.
**Why it happens:** New router uses different prefix but CORS middleware is already configured globally in `create_app()`. This should NOT be an issue since CORS is middleware-level.
**How to avoid:** The existing CORS middleware in app.py covers all routes. No action needed. [VERIFIED: app.py line 33-38]
**Warning signs:** None expected — just verify in testing.

### Pitfall 5: Forgetting to Filter Services by is_tracked
**What goes wrong:** After adding `is_tracked`, the pipeline/analysis/scoring services still process ALL stocks, including untracked ones.
**Why it happens:** Services call `stock_repo.get_all_hose_symbols()` which doesn't filter by `is_tracked`.
**How to avoid:** Either (a) modify `get_all_hose_symbols()` to filter by `is_tracked=true` (breaking change for existing callers — but all callers want this), or (b) add a new method `get_tracked_symbols()` and update service callers. Option (a) is cleaner since the whole point of `is_tracked` is to filter the watchlist.
**Warning signs:** Untracked stocks still appearing in daily pipeline results.

### Pitfall 6: Job ID Type Mismatch
**What goes wrong:** Admin endpoint returns `job_id` as integer but frontend sends it as string in URL path, or vice versa.
**Why it happens:** Inconsistent type handling between creation and lookup.
**How to avoid:** Use integer job IDs consistently (auto-increment primary key). FastAPI's Path type annotation will handle coercion: `job_id: int = Path(...)`.
**Warning signs:** 422 validation errors on GET /api/admin/jobs/{id}.

## Code Examples

### AdminJob Model
```python
# Source: pattern derived from existing PipelineRun model [VERIFIED: codebase models.py]
class AdminJob(Base):
    """Admin-triggered job tracking."""
    __tablename__ = "admin_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(30))  # 'crawl', 'analyze', 'score', 'report', 'pipeline'
    status: Mapped[str] = mapped_column(String(20))  # 'pending', 'running', 'completed', 'failed'
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"symbols": ["VNM", "FPT"]}
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # service return dict
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Alembic Migration for is_tracked
```python
# Source: pattern from add_phase5_automation_tables.py [VERIFIED: codebase]
def upgrade() -> None:
    # Add is_tracked to stocks table (D-03)
    op.add_column(
        "stocks",
        sa.Column("is_tracked", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    # Create admin_jobs table (D-02)
    op.create_table(
        "admin_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_jobs_status", "admin_jobs", ["status"])
    op.create_index("ix_admin_jobs_created_at", "admin_jobs", ["created_at"])
```

### Request Models
```python
# Source: pattern from macro.py BaseModel usage [VERIFIED: codebase]
class AddStockRequest(BaseModel):
    """Request to add a stock symbol to the watch list."""
    symbol: str = Field(
        ..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$",
        description="Stock ticker symbol (e.g., VNM, FPT, HPG)",
    )

class SymbolsRequest(BaseModel):
    """Request targeting one or more symbols."""
    symbols: list[str] = Field(
        ..., min_length=1,
        description="List of stock ticker symbols",
    )

class ReportRequest(BaseModel):
    """Request to generate AI report for a specific symbol."""
    symbol: str = Field(
        ..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$",
    )
```

### Endpoint Pattern with Background Execution
```python
# Source: pattern derived from automation.py + scores.py lock pattern [VERIFIED: codebase]
router = APIRouter(prefix="/api/admin")
_admin_lock = asyncio.Lock()

@router.post("/crawl")
async def trigger_crawl(
    request: SymbolsRequest,
    session: AsyncSession = Depends(get_session),
):
    """Trigger crawl for specified symbols. Returns job ID immediately."""
    if _admin_lock.locked():
        raise HTTPException(status_code=409, detail="An admin operation is already running")
    
    job_repo = JobRepository(session)
    job = await job_repo.create_job(
        job_type="crawl",
        params={"symbols": request.symbols},
    )
    asyncio.create_task(_run_crawl(job.id, request.symbols))
    return {"job_id": job.id, "status": "pending", "symbols": request.symbols}
```

### Stock Watchlist Repository Methods
```python
# Source: pattern from stock_repo.py [VERIFIED: codebase]
async def add_stock(self, symbol: str) -> Stock | None:
    """Add a stock to the watch list by setting is_tracked=True.
    
    If stock exists, just set is_tracked=True.
    If stock doesn't exist in DB, return None (stock must be crawled first).
    """
    stock = await self.get_by_symbol(symbol)
    if not stock:
        return None
    stock.is_tracked = True
    await self.session.commit()
    return stock

async def remove_stock(self, symbol: str) -> bool:
    """Remove a stock from the watch list by setting is_tracked=False."""
    stock = await self.get_by_symbol(symbol)
    if not stock:
        return False
    stock.is_tracked = False
    await self.session.commit()
    return True

async def get_tracked_symbols(self) -> list[str]:
    """Return all tracked symbols (is_tracked=True) on HOSE."""
    stmt = (
        select(Stock.symbol)
        .where(Stock.exchange == "HOSE", Stock.is_tracked == True)
        .order_by(Stock.symbol)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastAPI BackgroundTasks | asyncio.create_task for long ops | N/A | BackgroundTasks still fine for quick tasks; create_task better for minutes-long operations |
| Separate status polling endpoints | Same approach (GET /jobs/{id}) | N/A | SSE/WebSocket could be added later for Phase 12 UI, but polling is simpler for API layer |

**Deprecated/outdated:**
- None relevant — the existing stack is current and well-suited.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asyncio.create_task()` is preferable to FastAPI `BackgroundTasks` for long-running admin operations | Architecture Patterns | If BackgroundTasks handles this fine, the pattern is slightly simpler but functionally equivalent. Low risk — both work. |
| A2 | A single `_admin_lock` is sufficient (vs per-operation locks) | Pitfall 3 | If user needs to run crawl and analyze concurrently, separate locks needed. Low risk for personal tool. |
| A3 | ADMIN-01 through ADMIN-04 requirement IDs exist based on roadmap reference | Phase Requirements | Requirements not formally defined in REQUIREMENTS.md but described in ROADMAP.md success criteria. Planning uses success criteria as spec. |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | `apps/prometheus/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd apps/prometheus && uv run pytest tests/test_api/test_admin.py -x` |
| Full suite command | `cd apps/prometheus && uv run pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | POST /api/admin/stocks adds symbol to watchlist | unit | `uv run pytest tests/test_api/test_admin.py::TestStockWatchlist -x` | ❌ Wave 0 |
| ADMIN-01 | DELETE /api/admin/stocks/{symbol} removes from watchlist | unit | `uv run pytest tests/test_api/test_admin.py::TestStockWatchlist -x` | ❌ Wave 0 |
| ADMIN-02 | POST /api/admin/crawl returns job ID and triggers crawl | unit | `uv run pytest tests/test_api/test_admin.py::TestCrawlEndpoint -x` | ❌ Wave 0 |
| ADMIN-02 | POST /api/admin/analyze triggers analysis | unit | `uv run pytest tests/test_api/test_admin.py::TestAnalyzeEndpoint -x` | ❌ Wave 0 |
| ADMIN-02 | POST /api/admin/report triggers report generation | unit | `uv run pytest tests/test_api/test_admin.py::TestReportEndpoint -x` | ❌ Wave 0 |
| ADMIN-03 | POST /api/admin/pipeline triggers full pipeline | unit | `uv run pytest tests/test_api/test_admin.py::TestPipelineEndpoint -x` | ❌ Wave 0 |
| ADMIN-04 | GET /api/admin/jobs lists recent jobs | unit | `uv run pytest tests/test_api/test_admin.py::TestJobEndpoints -x` | ❌ Wave 0 |
| ADMIN-04 | GET /api/admin/jobs/{id} returns detailed job status | unit | `uv run pytest tests/test_api/test_admin.py::TestJobEndpoints -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd apps/prometheus && uv run pytest tests/test_api/test_admin.py -x`
- **Per wave merge:** `cd apps/prometheus && uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api/__init__.py` — package init
- [ ] `tests/test_api/test_admin.py` — covers ADMIN-01 through ADMIN-04
- No framework install needed — pytest + pytest-asyncio already in dev dependencies [VERIFIED: pyproject.toml]

## Project Constraints (from copilot-instructions.md)

The `copilot-instructions.md` contains project-level technology stack documentation and conventions. Key directives relevant to Phase 11:

1. **Backend:** Python + FastAPI + SQLAlchemy + Alembic + PostgreSQL [VERIFIED: copilot-instructions.md]
2. **No paid APIs** — all local/free tools only [VERIFIED: copilot-instructions.md]
3. **No multi-user/auth** — personal tool, no authentication needed [VERIFIED: copilot-instructions.md]
4. **GSD workflow enforcement** — use GSD commands for planned work [VERIFIED: copilot-instructions.md]
5. **Anti-stack:** No LangChain, no Redis, no Kafka — keep it simple [VERIFIED: copilot-instructions.md]

## Open Questions

1. **Should `get_all_hose_symbols()` be modified to filter by is_tracked?**
   - What we know: This method is called by Pipeline, AnalysisService, ScoringService, SentimentService, and ReportService to get the list of symbols to process.
   - What's unclear: Modifying it changes behavior for ALL callers including the daily scheduled pipeline. This is likely the desired behavior (only process tracked stocks), but should be confirmed.
   - Recommendation: Modify `get_all_hose_symbols()` to filter by `is_tracked=True`. Since `is_tracked` defaults to `True` for all existing stocks, this is backward-compatible. Only stocks explicitly removed from the watchlist will be excluded. This aligns with D-03's stated intent.

2. **Should adding a symbol that's not in the DB auto-crawl it?**
   - What we know: `POST /api/admin/stocks` should add a symbol. But if the symbol doesn't exist in the `stocks` table (never been crawled), we can't just set `is_tracked=True`.
   - What's unclear: Should the endpoint create a minimal stock record, or require the user to crawl first?
   - Recommendation: Create a minimal stock record with just the symbol and `is_tracked=True`, then the user triggers a crawl to populate full data. This is simpler and gives the user immediate feedback.

## Sources

### Primary (HIGH confidence)
- Codebase: `apps/prometheus/src/localstock/api/routes/automation.py` — existing endpoint patterns, lock pattern, router structure
- Codebase: `apps/prometheus/src/localstock/api/routes/scores.py` — session dependency injection, lock pattern
- Codebase: `apps/prometheus/src/localstock/api/routes/reports.py` — lock pattern, query params
- Codebase: `apps/prometheus/src/localstock/api/routes/macro.py` — Pydantic BaseModel for request validation
- Codebase: `apps/prometheus/src/localstock/api/app.py` — router registration pattern
- Codebase: `apps/prometheus/src/localstock/db/models.py` — ORM model patterns, Stock model, PipelineRun model
- Codebase: `apps/prometheus/src/localstock/db/repositories/stock_repo.py` — repository pattern, upsert
- Codebase: `apps/prometheus/src/localstock/db/database.py` — session factory, get_session dependency
- Codebase: `apps/prometheus/src/localstock/services/automation_service.py` — orchestration, session factory in background context
- Codebase: `apps/prometheus/src/localstock/services/pipeline.py` — Pipeline.run_full(), Pipeline.run_single()
- Codebase: `apps/prometheus/src/localstock/services/analysis_service.py` — AnalysisService.run_full()
- Codebase: `apps/prometheus/src/localstock/services/scoring_service.py` — ScoringService.run_full()
- Codebase: `apps/prometheus/src/localstock/services/report_service.py` — ReportService.run_full()
- Codebase: `apps/prometheus/alembic/versions/add_phase5_automation_tables.py` — migration pattern
- Codebase: `apps/prometheus/tests/test_services/test_automation_service.py` — test patterns with AsyncMock
- Codebase: `apps/prometheus/pyproject.toml` — test framework config

### Secondary (MEDIUM confidence)
- `.planning/phases/11-admin-api-endpoints/11-CONTEXT.md` — locked decisions D-01 through D-04a
- `.planning/ROADMAP.md` — phase success criteria and requirement IDs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, everything already installed and used
- Architecture: HIGH — all patterns derived from existing codebase, not hypothetical
- Pitfalls: HIGH — identified from direct codebase analysis (session lifecycle, migration defaults, lock scope)

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable — no external dependencies changing)
