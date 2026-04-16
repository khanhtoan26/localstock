"""API endpoints for dashboard-specific data.

Endpoints:
- GET /api/sectors/latest — Latest sector snapshots with Vietnamese names (DASH-03)
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.models import IndustryGroup, SectorSnapshot

router = APIRouter(prefix="/api")


@router.get("/sectors/latest")
async def get_latest_sectors(
    session: AsyncSession = Depends(get_session),
):
    """Get latest sector snapshots with Vietnamese group names.

    Finds the most recent date with sector data, then returns
    all sector snapshots for that date joined with industry group names.
    """
    # Find most recent date with sector data
    max_date_stmt = select(func.max(SectorSnapshot.date))
    result = await session.execute(max_date_stmt)
    latest_date = result.scalar()
    if not latest_date:
        return {"sectors": [], "count": 0, "date": None}

    # Get all sectors for that date, joined with group names
    stmt = (
        select(SectorSnapshot, IndustryGroup.group_name_vi)
        .outerjoin(IndustryGroup, SectorSnapshot.group_code == IndustryGroup.group_code)
        .where(SectorSnapshot.date == latest_date)
        .order_by(SectorSnapshot.avg_score.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    return {
        "date": str(latest_date),
        "count": len(rows),
        "sectors": [
            {
                "group_code": snap.group_code,
                "group_name_vi": name_vi or snap.group_code,
                "avg_score": round(snap.avg_score, 1),
                "stock_count": snap.stock_count,
                "avg_score_change": round(snap.avg_score_change, 1) if snap.avg_score_change else None,
            }
            for snap, name_vi in rows
        ],
    }
