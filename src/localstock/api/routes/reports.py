"""API endpoints for AI-generated stock reports.

Endpoints:
- GET /api/reports/top — Latest generated reports for top-ranked stocks
- GET /api/reports/{symbol} — Latest report for a specific stock
- POST /api/reports/run — Trigger report generation for top-ranked stocks
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.services.report_service import ReportService

router = APIRouter(prefix="/api")
# NOTE: Per-process lock — prevents concurrent generation within a single worker.
# For multi-worker deployment, use a database-level advisory lock instead.
_report_lock = asyncio.Lock()


@router.get("/reports/top")
async def get_top_reports(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get latest generated reports for top-ranked stocks.

    Returns list of report summaries with key fields.
    """
    service = ReportService(session)
    reports = await service.get_reports(limit=limit)
    if not reports:
        return {
            "reports": [],
            "count": 0,
            "message": "No reports available. Run POST /api/reports/run first.",
        }
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{symbol}")
async def get_report(
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """Get latest report for a specific stock.

    Returns full report with content_json and metadata.
    """
    service = ReportService(session)
    report = await service.get_report(symbol.upper())
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for {symbol.upper()}. Run POST /api/reports/run first.",
        )
    return report


@router.post("/reports/run")
async def trigger_reports(
    top_n: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Trigger report generation for top-ranked stocks.

    Uses asyncio.Lock to prevent concurrent generation.
    Per T-04-10: top_n capped at 50; lock prevents DoS via concurrent calls.
    """
    if _report_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Report generation already in progress",
        )
    async with _report_lock:
        service = ReportService(session)
        result = await service.run_full(top_n=top_n)
        return result
