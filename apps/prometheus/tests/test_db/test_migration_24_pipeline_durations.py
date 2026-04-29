"""Phase 24 / OBS-17 — migration round-trip integration tests.

Verifies that the 24a1b2c3d4e5 migration adds + removes the 4 *_duration_ms
columns cleanly on the live Postgres test DB. Marked ``requires_pg`` so the
tests skip in environments without a real Postgres backend.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa

from localstock.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]

EXPECTED = {
    "crawl_duration_ms",
    "analyze_duration_ms",
    "score_duration_ms",
    "report_duration_ms",
}

# tests/test_db/<this file>  ->  apps/prometheus
APP_ROOT = Path(__file__).resolve().parents[2]


async def _columns() -> set[str]:
    """Open a fresh async engine for the current event loop, then dispose.

    ``localstock.db.database.get_engine`` caches a single async engine at
    module scope. Across pytest-asyncio function-scoped event loops, that
    cached engine becomes bound to a closed loop and fails on the second
    test in the file. Creating + disposing a per-call engine sidesteps the
    issue without polluting global state.
    """
    settings = get_settings()
    url = settings.database_url
    eng = create_async_engine(
        url,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    try:
        async with eng.begin() as conn:
            rows = await conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='pipeline_runs'"
                )
            )
            return {r[0] for r in rows}
    finally:
        await eng.dispose()


async def test_migration_upgrade_adds_columns() -> None:
    """At head, all 4 *_duration_ms columns must exist on pipeline_runs."""
    # Ensure DB is at head (idempotent).
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=APP_ROOT,
        check=True,
        capture_output=True,
    )
    cols = await _columns()
    missing = EXPECTED - cols
    assert not missing, f"Missing columns: {missing}"


async def test_migration_downgrade_removes_columns() -> None:
    """downgrade -1 drops the 4 columns; upgrade head restores them."""
    subprocess.run(
        ["uv", "run", "alembic", "downgrade", "-1"],
        cwd=APP_ROOT,
        check=True,
        capture_output=True,
    )
    try:
        cols_after_down = await _columns()
        leaked = EXPECTED & cols_after_down
        assert not leaked, f"Columns not dropped on downgrade: {leaked}"
    finally:
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=APP_ROOT,
            check=True,
            capture_output=True,
        )
    cols_after_up = await _columns()
    assert EXPECTED.issubset(cols_after_up), (
        f"Columns missing after re-upgrade: {EXPECTED - cols_after_up}"
    )
