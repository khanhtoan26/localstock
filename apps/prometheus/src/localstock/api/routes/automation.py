"""API endpoints for automation and on-demand analysis (AUTO-02).

Endpoints:
- POST /api/automation/run — Trigger full pipeline (on-demand)
- POST /api/automation/run/{symbol} — Trigger single-symbol analysis
- GET /api/automation/status — Check scheduler and pipeline status
"""

from fastapi import APIRouter, HTTPException, Path

from localstock.services.automation_service import AutomationService, _pipeline_lock

router = APIRouter(prefix="/api")


@router.post("/automation/run")
async def run_full_pipeline():
    """Trigger full pipeline run on demand (AUTO-02).

    Forces execution regardless of trading day (on-demand = user intent).
    Returns 409 if pipeline already running.
    """
    if _pipeline_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Pipeline already in progress",
        )
    service = AutomationService()
    result = await service.run_on_demand()
    return result


@router.post("/automation/run/{symbol}")
async def run_single_symbol(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Z0-9]+$"),
):
    """Trigger analysis for a single stock symbol (AUTO-02).

    Args:
        symbol: Stock ticker (e.g., VNM, FPT, HPG). Must be uppercase alphanumeric.

    Returns 409 if pipeline already running.
    """
    if _pipeline_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Pipeline already in progress",
        )
    service = AutomationService()
    result = await service.run_on_demand(symbol=symbol.upper())
    return result


@router.get("/automation/status")
async def get_automation_status():
    """Get current automation status — scheduler jobs and pipeline lock state."""
    from localstock.scheduler.scheduler import scheduler

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })

    return {
        "scheduler_running": scheduler.running,
        "pipeline_locked": _pipeline_lock.locked(),
        "scheduled_jobs": jobs,
    }
