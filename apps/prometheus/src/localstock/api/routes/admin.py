"""Admin API endpoints for stock management, pipeline triggers, and job monitoring.

Pipeline triggers use a DB-queue pattern:
- Endpoints create a job record (status=pending) and return immediately.
- A background worker (APScheduler) picks up pending jobs and executes them.
- This decouples heavy work from API request handling.

Endpoints (per D-01: separate /api/admin/* prefix):
- GET    /api/admin/stocks          — list tracked stocks (ADMIN-01)
- POST   /api/admin/stocks          — add stock to watchlist (ADMIN-01)
- DELETE /api/admin/stocks/{symbol} — remove stock from watchlist (ADMIN-01)
- POST   /api/admin/crawl           — queue crawl job (ADMIN-02, D-04)
- POST   /api/admin/analyze         — queue analysis job (ADMIN-02, D-04)
- POST   /api/admin/score           — queue scoring job (ADMIN-02, D-04)
- POST   /api/admin/report          — queue report generation (ADMIN-02, D-04)
- POST   /api/admin/pipeline        — queue full pipeline (ADMIN-03)
- GET    /api/admin/jobs             — list recent jobs (ADMIN-04)
- GET    /api/admin/jobs/{id}        — get job detail (ADMIN-04)
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.job_repo import JobRepository
from localstock.db.repositories.stock_repo import StockRepository

router = APIRouter(prefix="/api/admin")


# --- Request Models ---

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
        description="Stock ticker symbol",
    )


# --- Stock Watchlist Endpoints (ADMIN-01) ---

@router.get("/stocks")
async def list_tracked_stocks(
    session: AsyncSession = Depends(get_session),
):
    """List all tracked stocks (is_tracked=True)."""
    repo = StockRepository(session)
    stocks = await repo.get_tracked_stocks()
    return {
        "stocks": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "exchange": s.exchange,
                "industry": s.industry_icb3,
                "is_tracked": s.is_tracked,
            }
            for s in stocks
        ],
        "count": len(stocks),
    }


@router.post("/stocks")
async def add_stock(
    request: AddStockRequest,
    session: AsyncSession = Depends(get_session),
):
    """Add a stock symbol to the watch list.

    If the stock exists in DB, sets is_tracked=True.
    If not, creates a minimal record (user should trigger crawl next).
    """
    repo = StockRepository(session)
    stock = await repo.add_stock(request.symbol.upper())
    if not stock:
        raise HTTPException(status_code=500, detail=f"Failed to add stock {request.symbol}")
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "is_tracked": stock.is_tracked,
        "message": f"Stock {stock.symbol} added to watchlist",
    }


@router.delete("/stocks/{symbol}")
async def remove_stock(
    symbol: str = Path(..., min_length=1, max_length=10, pattern="^[A-Z0-9]+$"),
    session: AsyncSession = Depends(get_session),
):
    """Remove a stock from the watch list by setting is_tracked=False."""
    repo = StockRepository(session)
    removed = await repo.remove_stock(symbol.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return {"symbol": symbol.upper(), "is_tracked": False, "message": f"Stock {symbol} removed from watchlist"}


# --- Pipeline Trigger Endpoints (ADMIN-02, ADMIN-03, D-04) ---

@router.post("/crawl")
async def trigger_crawl(
    request: SymbolsRequest,
    session: AsyncSession = Depends(get_session),
):
    """Queue crawl job for specified symbols. Returns job ID immediately (D-04a)."""
    job_repo = JobRepository(session)
    job = await job_repo.create_job(job_type="crawl", params={"symbols": request.symbols})
    return {"job_id": job.id, "status": "pending", "job_type": "crawl", "symbols": request.symbols}


@router.post("/analyze")
async def trigger_analyze(
    request: SymbolsRequest,
    session: AsyncSession = Depends(get_session),
):
    """Queue analysis job for specified symbols. Returns job ID immediately (D-04)."""
    job_repo = JobRepository(session)
    job = await job_repo.create_job(job_type="analyze", params={"symbols": request.symbols})
    return {"job_id": job.id, "status": "pending", "job_type": "analyze", "symbols": request.symbols}


@router.post("/score")
async def trigger_score(
    session: AsyncSession = Depends(get_session),
):
    """Queue scoring job for all tracked stocks. Returns job ID immediately (D-04)."""
    job_repo = JobRepository(session)
    job = await job_repo.create_job(job_type="score")
    return {"job_id": job.id, "status": "pending", "job_type": "score"}


@router.post("/report")
async def trigger_report(
    request: ReportRequest,
    session: AsyncSession = Depends(get_session),
):
    """Queue AI report generation for a specific symbol. Returns job ID immediately (D-04)."""
    job_repo = JobRepository(session)
    job = await job_repo.create_job(job_type="report", params={"symbol": request.symbol})
    return {"job_id": job.id, "status": "pending", "job_type": "report", "symbol": request.symbol}


@router.post("/pipeline")
async def trigger_pipeline(
    session: AsyncSession = Depends(get_session),
):
    """Queue full daily pipeline (crawl→analyze→score→report). Returns job ID (ADMIN-03)."""
    job_repo = JobRepository(session)
    job = await job_repo.create_job(job_type="pipeline")
    return {"job_id": job.id, "status": "pending", "job_type": "pipeline"}


# --- Job Monitoring Endpoints (ADMIN-04) ---

@router.get("/jobs")
async def list_jobs(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """List recent admin jobs with status."""
    job_repo = JobRepository(session)
    jobs = await job_repo.list_recent(limit=limit)
    return {
        "jobs": [
            {
                "id": j.id,
                "job_type": j.job_type,
                "status": j.status,
                "params": j.params,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
        "count": len(jobs),
    }


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed job status including result and errors."""
    job_repo = JobRepository(session)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "params": job.params,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
