"""Phase 25 / DQ-06 + DQ-08 — migration smoke test (RED until upgrade run).

Verifies that ``25a0b1c2d3e4_phase25_dq_tables`` produced the expected DDL:
- ``quarantine_rows`` table exists
- ``pipeline_runs.stats`` JSONB column exists
- ``ix_quarantine_rows_*`` indexes registered

Marked ``requires_pg`` so they skip in environments without a real Postgres
backend. The tests assume the migration has already been applied (Wave 0
acceptance gate runs ``alembic upgrade head`` once).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from localstock.config import get_settings


pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]


async def _engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )


async def test_quarantine_rows_table_exists() -> None:
    eng = await _engine()
    try:
        async with eng.begin() as conn:
            result = await conn.execute(
                text("SELECT to_regclass('public.quarantine_rows')")
            )
            assert result.scalar() is not None
    finally:
        await eng.dispose()


async def test_pipeline_runs_stats_column_exists() -> None:
    eng = await _engine()
    try:
        async with eng.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name='pipeline_runs' AND column_name='stats'"
                )
            )
            row = result.first()
            assert row is not None
            # JSONB shows up as 'jsonb' in information_schema
            assert row[0].lower() == "jsonb"
    finally:
        await eng.dispose()


async def test_quarantine_rows_indexes_exist() -> None:
    eng = await _engine()
    try:
        async with eng.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename='quarantine_rows'"
                )
            )
            names = {r[0] for r in result.fetchall()}
            assert "ix_quarantine_rows_source_qa" in names
            assert "ix_quarantine_rows_symbol" in names
    finally:
        await eng.dispose()
