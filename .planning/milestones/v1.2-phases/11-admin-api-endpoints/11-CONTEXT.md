# Phase 11: Admin API Endpoints - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend REST API endpoints for admin operations: stock watchlist management (add/remove symbols), granular pipeline step triggers (crawl, analyze, score, report separately), and job history/status monitoring. All endpoints under `/api/admin/*` prefix, separate from existing public API.

</domain>

<decisions>
## Implementation Decisions

### API Structure
- **D-01:** New router at `/api/admin/*` — separate from existing `/api/automation/*` to cleanly distinguish admin operations from public endpoints. Easier to add auth later if needed.

### Job Tracking
- **D-02:** DB persistence for job tracking — use PostgreSQL (extend or leverage existing `pipeline_runs` table). Enables job history queries, survives server restart, aligns with existing async DB patterns.

### Stock Watchlist
- **D-03:** Add `is_tracked` boolean column to existing `stocks` table (default: true for backward compat). Pipeline and analysis services filter by `is_tracked=true`. No separate watchlist table — keeps it simple for a personal tool.
- **D-03a:** Alembic migration required for the new column.

### Granular Operations
- **D-04:** Individual step triggers — separate endpoints for crawl, analyze, score, and report generation. Each can target 1 or more symbols. More flexible than full pipeline only, easier to debug individual steps.
- **D-04a:** Each granular operation creates its own job record for tracking.

### Agent's Discretion
- Request/response Pydantic models — agent decides schema structure
- Error handling patterns — follow existing convention (HTTPException with detail)
- Job status enum values — agent picks appropriate states (e.g., pending/running/completed/failed)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing API Layer
- `apps/prometheus/src/localstock/api/routes/automation.py` — Current automation endpoints pattern (POST /run, GET /status)
- `apps/prometheus/src/localstock/api/routes/__init__.py` — Router registration pattern

### Service Layer
- `apps/prometheus/src/localstock/services/automation_service.py` — Pipeline orchestration, _pipeline_lock pattern
- `apps/prometheus/src/localstock/services/pipeline.py` — Crawl pipeline (run_full, run_single)
- `apps/prometheus/src/localstock/services/analysis_service.py` — Analysis service (run_full)
- `apps/prometheus/src/localstock/services/scoring_service.py` — Scoring service (run_full)
- `apps/prometheus/src/localstock/services/report_service.py` — Report generation (run_full)

### Data Layer
- `apps/prometheus/src/localstock/db/models.py` — ORM models (Stock, PipelineRun)
- `apps/prometheus/src/localstock/db/repositories/stock_repo.py` — Stock CRUD operations
- `apps/prometheus/src/localstock/db/database.py` — Session factory pattern
- `apps/prometheus/src/localstock/config.py` — Settings (Pydantic BaseSettings)

### Migration
- `apps/prometheus/alembic/` — Alembic migration directory

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AutomationService` — already orchestrates full pipeline; granular endpoints can call individual service methods directly
- `Pipeline` class — has `run_full()` and `run_single()` methods
- `StockRepository` — has `upsert_stocks()`, needs add/remove single stock methods
- `PipelineRun` model — already tracks pipeline runs; can be extended for granular job tracking
- `_pipeline_lock` — asyncio.Lock for preventing concurrent runs; reuse or extend pattern

### Established Patterns
- **Router pattern:** APIRouter with prefix, type-annotated path params, Pydantic validation
- **Service instantiation:** Services created per-request with session injection (no DI container)
- **Session factory:** `get_session_factory()` returns async context manager
- **Error handling:** HTTPException with status_code and detail string

### Integration Points
- New admin router registers in `api/routes/__init__.py` or `api/app.py`
- New `is_tracked` column needs Alembic migration
- StockRepository needs new methods: `add_stock()`, `remove_stock()`, `get_tracked_stocks()`
- Frontend (Phase 12) will call these endpoints via API client

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following existing codebase conventions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-admin-api-endpoints*
*Context gathered: 2026-04-21*
