"""Phase 24 — SQLAlchemy 2.0 async-engine query timing (D-04, OBS-12, OBS-13).

Attaches ``before_cursor_execute`` / ``after_cursor_execute`` listeners to the
``sync_engine`` of an :class:`AsyncEngine`. These events fire for every
statement the async engine dispatches — including repository methods, ORM
lazy loads, and ``session.execute(text(...))`` calls.

Why ``sync_engine``: SQLAlchemy 2.0 routes all DBAPI cursor work through the
synchronous engine inside a worker thread. Attaching directly to the
:class:`AsyncEngine` silently no-ops (RESEARCH §2 Pitfall 2).

Out of scope: Alembic migrations (DDL pollutes the histogram). The runtime
async engine and Alembic's offline engine are different objects, so attaching
here (called from ``get_engine()``) leaves Alembic alone. A defensive guard
also skips any statement containing ``alembic_version`` in case test fixtures
ever cross-pollinate.
"""
from __future__ import annotations

import re
import time
from typing import Any

from loguru import logger
from prometheus_client import REGISTRY
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

# === Hot-table heuristic (D-04) ===
_HOT_TABLE_RE = re.compile(
    r"\b(stock_prices|stock_scores|pipeline_runs)\b", re.IGNORECASE
)
# === Query-type extraction ===
_QTYPE_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


def _classify(statement: str) -> tuple[str, str]:
    """Return ``(query_type, table_class)`` for a SQL statement.

    * ``query_type`` ∈ {SELECT, INSERT, UPDATE, DELETE, OTHER}
    * ``table_class`` ∈ {hot, cold} — ``hot`` iff the statement references
      ``stock_prices`` / ``stock_scores`` / ``pipeline_runs`` (case-insensitive).
    """
    m = _QTYPE_RE.match(statement)
    qtype = m.group(1).upper() if m else "OTHER"
    tclass = "hot" if _HOT_TABLE_RE.search(statement) else "cold"
    return qtype, tclass


def _get_collectors() -> dict[str, Any]:
    """Look up Phase 23 primitives + the new ``db_query_slow_total`` counter.

    Uses ``REGISTRY._names_to_collectors`` (private but stable since
    prometheus_client 0.8). Returns ``None`` for any missing collector so
    the listener degrades gracefully when ``init_metrics()`` hasn't been
    invoked on the default registry yet (e.g. in narrow unit-test setups).
    """
    n2c = REGISTRY._names_to_collectors
    return {
        "duration": n2c.get("localstock_db_query_duration_seconds"),
        "total": n2c.get("localstock_db_query_total"),
        "slow": n2c.get("localstock_db_query_slow_total"),
    }


def attach_query_listener(engine: AsyncEngine) -> None:
    """Attach ``before/after_cursor_execute`` listeners to ``engine.sync_engine``.

    Idempotent: a sentinel attribute on the underlying ``sync_engine`` ensures
    repeated calls (common in tests calling ``get_engine()``) attach handlers
    exactly once.
    """
    sync_engine = engine.sync_engine

    if getattr(sync_engine, "_localstock_query_listener_attached", False):
        return
    sync_engine._localstock_query_listener_attached = True

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        # Stash on context per SQLAlchemy convention. ``context`` is an
        # ExecutionContext per DBAPI cursor execution.
        context._localstock_t0 = time.perf_counter()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        t0 = getattr(context, "_localstock_t0", None)
        if t0 is None:
            return
        elapsed = time.perf_counter() - t0
        duration_ms = int(elapsed * 1000)

        # Defensive Alembic skip — Alembic uses a different engine in normal
        # operation, but tests may share. ``alembic_version`` is the canonical
        # marker (D-04).
        if "alembic_version" in statement:
            return

        qtype, tclass = _classify(statement)
        c = _get_collectors()
        if c["duration"] is not None:
            c["duration"].labels(qtype, tclass).observe(elapsed)
        if c["total"] is not None:
            c["total"].labels(qtype, tclass, "success").inc()

        # Slow-query branch (OBS-13). Late import avoids a config <-> db cycle.
        from localstock.config import get_settings

        threshold_ms = get_settings().slow_query_threshold_ms
        if duration_ms > threshold_ms:
            if c["slow"] is not None:
                c["slow"].labels(qtype, tclass).inc()
            logger.warning(
                "slow_query",
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                query_type=qtype,
                table_class=tclass,
                statement_preview=statement[:120],  # ASVS V8 — bounded
            )
