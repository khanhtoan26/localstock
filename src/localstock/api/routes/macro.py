"""API endpoints for macro economic data.

Endpoints:
- GET /api/macro/latest — Latest macro indicators
- POST /api/macro — Manual macro data entry
- POST /api/macro/fetch-exchange-rate — Trigger VCB exchange rate fetch
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_session
from localstock.db.repositories.macro_repo import MacroRepository
from localstock.macro.crawler import MacroCrawler

router = APIRouter(prefix="/api")


class MacroInput(BaseModel):
    """Validated input for manual macro indicator entry.

    Per T-04-09: indicator_type constrained to 4 valid values via regex.
    """

    indicator_type: str = Field(
        pattern=r"^(interest_rate|exchange_rate_usd_vnd|cpi|gdp)$",
        description="One of: interest_rate, exchange_rate_usd_vnd, cpi, gdp",
    )
    value: float = Field(description="Indicator value (numeric)")
    period: str = Field(
        min_length=4,
        max_length=20,
        description="Period string, e.g., '2026-Q1', '2026-04'",
    )
    source: str = Field(
        default="manual",
        max_length=50,
        description="Data source identifier",
    )


@router.get("/macro/latest")
async def get_latest_macro(
    session: AsyncSession = Depends(get_session),
):
    """Get latest macro indicators.

    Returns list of current macro indicator values with metadata.
    """
    repo = MacroRepository(session)
    indicators = await repo.get_all_latest()

    return {
        "indicators": [
            {
                "indicator_type": ind.indicator_type,
                "value": ind.value,
                "period": ind.period,
                "source": ind.source,
                "trend": ind.trend,
                "recorded_at": str(ind.recorded_at),
            }
            for ind in indicators
        ],
        "count": len(indicators),
    }


@router.post("/macro")
async def add_macro_indicator(
    data: MacroInput,
    session: AsyncSession = Depends(get_session),
):
    """Manual entry for macro economic indicators.

    Accepts interest_rate, exchange_rate_usd_vnd, cpi, or gdp values.
    Per T-04-09: Input validated via Pydantic MacroInput model.
    """
    repo = MacroRepository(session)

    # Compute trend from previous value
    trend = None
    previous = await repo.get_latest_by_type(data.indicator_type)
    if previous is not None:
        if data.value > previous.value:
            trend = "rising"
        elif data.value < previous.value:
            trend = "falling"
        else:
            trend = "stable"

    today = date.today()
    row = {
        "indicator_type": data.indicator_type,
        "value": data.value,
        "period": data.period,
        "source": data.source,
        "trend": trend,
        "recorded_at": today,
        "fetched_at": datetime.now(UTC),
    }

    await repo.bulk_upsert([row])

    return {
        "status": "ok",
        "indicator": {
            "indicator_type": data.indicator_type,
            "value": data.value,
            "period": data.period,
            "source": data.source,
            "trend": trend,
            "recorded_at": str(today),
        },
    }


@router.post("/macro/fetch-exchange-rate")
async def fetch_exchange_rate(
    session: AsyncSession = Depends(get_session),
):
    """Trigger exchange rate fetch from VCB.

    Fetches USD/VND sell rate from Vietcombank XML endpoint.
    Stores result in macro_indicators table.
    """
    repo = MacroRepository(session)

    # Get previous rate for trend calculation
    previous = await repo.get_latest_by_type("exchange_rate_usd_vnd")
    previous_value = previous.value if previous else None

    crawler = MacroCrawler()
    result = await crawler.fetch_exchange_rate(previous_value=previous_value)

    if not result:
        return {"status": "failed", "error": "Could not fetch exchange rate from VCB"}

    await repo.bulk_upsert([result])

    return {
        "status": "ok",
        "rate": {
            "indicator_type": result["indicator_type"],
            "value": result["value"],
            "source": result["source"],
            "trend": result.get("trend"),
            "recorded_at": str(result["recorded_at"]),
        },
    }
