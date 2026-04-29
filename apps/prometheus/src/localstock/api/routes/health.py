"""Phase 24 / OBS-14 — Health probes (D-03).

Four ops-ready endpoints + one deprecated alias:

  GET /health/live      Liveness — process up, performs zero I/O. Always 200.
  GET /health/ready     Readiness — DB pool reachable. 200 on `SELECT 1`
                         success within 2s, 503 on timeout/OperationalError.
                         Body includes pool stats (size/checked_in/checked_out
                         /overflow).
  GET /health/pipeline  Pipeline freshness — last completed PipelineRun age.
                         Always 200 (informational).
  GET /health/data      Data freshness — MAX(stock_prices.date) vs the VN
                         trading calendar. Always 200 (informational); the
                         ``stale`` boolean flips when the lag exceeds 1
                         trading day.
  GET /health           DEPRECATED — alias of /health/ready. Mirrors the
                         body and adds an ``X-Deprecated`` response header
                         pointing callers at the new path. Removal targeted
                         for v1.7 (D-03).

All probes are read-only (no INSERT/UPDATE/DELETE). The handlers emit no
metrics and no log lines themselves; the Phase 23-02 Prometheus
Instrumentator already records HTTP histograms for /health/ready,
/health/pipeline, /health/data and /health (the legacy alias is
intentionally NOT excluded so dashboards can detect lingering callers),
and ``/health/live`` is excluded so liveness probes don't pollute the
HTTP histogram cardinality.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.database import get_engine, get_session
from localstock.db.models import PipelineRun, StockPrice

router = APIRouter()

# Minimal static VN holiday list covering 2025–2026 — this intentionally
# leaves out the long tail of the official Vietnamese trading calendar.
# A full calendar (e.g. via vnstock.trading_dates() or a maintained
# JSON file) is deferred to backlog per D-03 and Open Q-2 in the phase
# research doc.
# TODO(backlog): full VN trading calendar — D-03 + Open Q-2
_VN_HOLIDAYS_2025_2026: frozenset[date] = frozenset(
    {
        # 2025 — Solar new year + Tết Ất Tỵ + Hùng Kings + Reunification + Labour + National
        date(2025, 1, 1),
        date(2025, 1, 28),
        date(2025, 1, 29),
        date(2025, 1, 30),
        date(2025, 1, 31),
        date(2025, 2, 3),
        date(2025, 4, 7),
        date(2025, 4, 30),
        date(2025, 5, 1),
        date(2025, 9, 2),
        # 2026 — Solar new year + Tết Bính Ngọ + Hùng Kings + Reunification + Labour + National
        date(2026, 1, 1),
        date(2026, 2, 16),
        date(2026, 2, 17),
        date(2026, 2, 18),
        date(2026, 2, 19),
        date(2026, 2, 20),
        date(2026, 4, 27),
        date(2026, 4, 30),
        date(2026, 5, 1),
        date(2026, 9, 2),
    }
)


def _is_trading_day(d: date) -> bool:
    """True iff ``d`` is a Mon–Fri and not in the static VN holiday set."""
    return d.weekday() < 5 and d not in _VN_HOLIDAYS_2025_2026


def _trading_days_lag(latest: date, today: date) -> int:
    """Count trading days strictly after ``latest`` up to and including ``today``.

    Returns 0 when ``latest >= today``. Excludes weekends and the static
    ``_VN_HOLIDAYS_2025_2026`` set.
    """
    if latest >= today:
        return 0
    lag = 0
    cur = latest + timedelta(days=1)
    while cur <= today:
        if _is_trading_day(cur):
            lag += 1
        cur += timedelta(days=1)
    return lag


def _last_trading_day_on_or_before(today: date) -> date:
    """Return the most recent VN trading day on or before ``today``.

    Walks backwards skipping weekends and ``_VN_HOLIDAYS_2025_2026``.
    Loop is bounded defensively (worst-case Tet ~9 holidays + weekend
    gives < 14 calendar steps; cap at 20 with a fall-through return).
    """
    d = today
    for _ in range(20):
        if _is_trading_day(d):
            return d
        d = d - timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# /health/live — liveness, zero I/O
# ---------------------------------------------------------------------------
@router.get("/health/live", summary="Liveness probe — process is up")
async def health_live() -> dict:
    """Liveness — pure response, no DB or external I/O involved."""
    return {"status": "alive"}


# ---------------------------------------------------------------------------
# /health/ready — readiness (shared with /health alias via _ready_payload)
# ---------------------------------------------------------------------------
async def _ready_payload(session: AsyncSession) -> tuple[int, dict]:
    """Run a bounded ``SELECT 1`` and snapshot the pool counters.

    Returns ``(status_code, body)``. The 2s timeout is enforced via
    ``asyncio.wait_for`` so a hung pool can't block the probe forever.
    On timeout or any SQLAlchemy DB error the probe returns 503 with
    ``db="down"`` and the exception class name in ``error_type`` for
    fast triage by ops.
    """
    engine = get_engine()
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=2.0)
    except (TimeoutError, asyncio.TimeoutError, OperationalError, SQLAlchemyError) as exc:
        return status.HTTP_503_SERVICE_UNAVAILABLE, {
            "status": "not_ready",
            "db": "down",
            "error_type": type(exc).__name__,
        }
    pool = engine.pool
    return status.HTTP_200_OK, {
        "status": "ready",
        "db": "ok",
        "pool": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
    }


@router.get("/health/ready", summary="Readiness probe — DB reachable")
async def health_ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict:
    code, body = await _ready_payload(session)
    response.status_code = code
    return body


# ---------------------------------------------------------------------------
# /health/pipeline — last completed PipelineRun age
# ---------------------------------------------------------------------------
@router.get("/health/pipeline", summary="Pipeline freshness — last completed run age")
async def health_pipeline(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None or run.completed_at is None:
        return {
            "last_run_status": None,
            "last_pipeline_age_seconds": None,
            "started_at": None,
            "completed_at": None,
        }
    age = (datetime.now(UTC) - run.completed_at).total_seconds()
    return {
        "last_run_status": run.status,
        "last_pipeline_age_seconds": int(age),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# /health/data — MAX(stock_prices.date) vs trading calendar
# ---------------------------------------------------------------------------
@router.get("/health/data", summary="Data freshness — max price date vs calendar")
async def health_data(session: AsyncSession = Depends(get_session)) -> dict:
    # Local import: avoid module-load cost + lets tests monkeypatch
    # DQ_STALE_THRESHOLD_SESSIONS via ``get_settings.cache_clear()`` + setenv
    # at request time without reloading the route module.
    from localstock.config import get_settings

    result = await session.execute(select(func.max(StockPrice.date)))
    max_date: date | None = result.scalar_one_or_none()
    today = date.today()
    last_trading = _last_trading_day_on_or_before(today)
    threshold = get_settings().dq_stale_threshold_sessions

    if max_date is None:
        # Cold start — preserve back-compat keys (D-05), mark unknown in
        # the new data_freshness block so dashboards can distinguish a
        # cold start from a true stale alert.
        return {
            "max_price_date": None,
            "trading_days_lag": None,
            "stale": True,
            "data_freshness": {
                "last_trading_day": last_trading.isoformat(),
                "max_data_date": None,
                "sessions_behind": None,
                "status": "unknown",
                "threshold_sessions": threshold,
            },
        }

    lag = _trading_days_lag(max_date, today)
    sessions_behind = lag
    status_str = "fresh" if sessions_behind <= threshold else "stale"
    return {
        # Phase 24 contract — preserved verbatim (CONTEXT D-05 hard rule).
        "max_price_date": max_date.isoformat(),
        "trading_days_lag": lag,
        "stale": lag > 1,
        # DQ-07 / SC #5 — configurable-threshold freshness block.
        "data_freshness": {
            "last_trading_day": last_trading.isoformat(),
            "max_data_date": max_date.isoformat(),
            "sessions_behind": sessions_behind,
            "status": status_str,
            "threshold_sessions": threshold,
        },
    }


# ---------------------------------------------------------------------------
# /health — DEPRECATED alias → mirrors /health/ready + X-Deprecated header
# ---------------------------------------------------------------------------
@router.get("/health", summary="DEPRECATED — alias of /health/ready")
async def health_deprecated(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict:
    code, body = await _ready_payload(session)
    response.status_code = code
    response.headers["X-Deprecated"] = "use /health/ready instead"
    return body
