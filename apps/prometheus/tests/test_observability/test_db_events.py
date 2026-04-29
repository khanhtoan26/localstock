"""Phase 24-03 — DB query event listener tests (OBS-12, OBS-13).

RED phase: imports from `localstock.observability.db_events` MUST fail until
Task 2 (GREEN) creates the module.

Test surface (per 24-VALIDATION.md OBS-12 + OBS-13 rows):
  * test_query_type_classification     — unit, parametrize
  * test_table_class_classification    — unit, parametrize
  * test_query_duration_observed_for_select   — integration, requires_pg
  * test_alembic_statements_skipped    — integration, requires_pg
  * test_slow_query_emits_log_and_counter     — integration, requires_pg
  * test_fast_query_does_not_trigger_slow_log — integration, requires_pg
"""
from __future__ import annotations

import os

import pytest
from loguru import logger
from sqlalchemy import text

from localstock.observability.db_events import _classify, attach_query_listener


# ===========================================================================
# Unit tier — no DB required
# ===========================================================================

@pytest.mark.parametrize(
    "stmt,expected",
    [
        ("SELECT 1", "SELECT"),
        ("  select * from t", "SELECT"),
        ("INSERT INTO t VALUES (1)", "INSERT"),
        ("UPDATE t SET x=1", "UPDATE"),
        ("DELETE FROM t", "DELETE"),
        ("WITH x AS (SELECT 1) SELECT * FROM x", "OTHER"),
        ("VACUUM", "OTHER"),
    ],
)
def test_query_type_classification(stmt: str, expected: str) -> None:
    """OBS-12 — _classify extracts SELECT/INSERT/UPDATE/DELETE/OTHER."""
    assert _classify(stmt)[0] == expected


@pytest.mark.parametrize(
    "stmt,expected",
    [
        ("SELECT * FROM stock_prices LIMIT 1", "hot"),
        ("INSERT INTO stock_scores VALUES(1)", "hot"),
        ("UPDATE pipeline_runs SET status='ok'", "hot"),
        ("SELECT * FROM users", "cold"),
        ("SELECT 1", "cold"),
    ],
)
def test_table_class_classification(stmt: str, expected: str) -> None:
    """OBS-12 — hot tables: stock_prices / stock_scores / pipeline_runs."""
    assert _classify(stmt)[1] == expected


# ===========================================================================
# Integration tier — requires Postgres (gated by `requires_pg` marker)
# ===========================================================================

def _has_pg() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    if "postgres" in url.lower():
        return True
    # Fall back to Settings (which reads .env) — the .env is the source of
    # truth in dev; os.environ may be empty when pytest didn't load it.
    try:
        from localstock.config import get_settings

        return "postgres" in get_settings().database_url.lower()
    except Exception:
        return False


pytestmark_pg = pytest.mark.skipif(not _has_pg(), reason="DATABASE_URL is not Postgres")


def _metric_value(name: str, label_values: dict[str, str]) -> float:
    """Read a sample value from default REGISTRY by name + label dict."""
    from prometheus_client import REGISTRY

    c = REGISTRY._names_to_collectors.get(name)
    if c is None:
        return 0.0
    for fam in c.collect():
        for s in fam.samples:
            if s.name.endswith("_count") or s.name.endswith("_total"):
                if all(s.labels.get(k) == v for k, v in label_values.items()):
                    return s.value
    return 0.0


def _histogram_count(name: str, label_values: dict[str, str]) -> float:
    """Read histogram _count sample from default REGISTRY."""
    from prometheus_client import REGISTRY

    c = REGISTRY._names_to_collectors.get(name)
    if c is None:
        return 0.0
    total = 0.0
    for fam in c.collect():
        for s in fam.samples:
            if s.name.endswith("_count"):
                if all(s.labels.get(k) == v for k, v in label_values.items()):
                    total = s.value
    return total


@pytest.fixture
def loguru_warning_records():
    """Capture WARNING-level loguru records for the duration of a test."""
    records: list[dict] = []
    sink_id = logger.add(
        lambda msg: records.append(msg.record),
        level="WARNING",
        format="{message}",
        filter=lambda r: True,
    )
    yield records
    logger.remove(sink_id)


@pytest.fixture
async def pg_engine():
    """Fresh AsyncEngine bound to DATABASE_URL with the listener attached."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from localstock.config import get_settings

    settings = get_settings()
    eng = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"prepared_statement_cache_size": 0, "statement_cache_size": 0},
    )
    attach_query_listener(eng)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.mark.asyncio
@pytest.mark.requires_pg
@pytestmark_pg
async def test_query_duration_observed_for_select(pg_engine) -> None:
    """OBS-12 — SELECT increments db_query_duration_seconds{SELECT, cold}."""
    before = _histogram_count(
        "localstock_db_query_duration_seconds",
        {"query_type": "SELECT", "table_class": "cold"},
    )
    async with pg_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    after = _histogram_count(
        "localstock_db_query_duration_seconds",
        {"query_type": "SELECT", "table_class": "cold"},
    )
    assert after >= before + 1, f"histogram count not incremented: before={before} after={after}"


@pytest.mark.asyncio
@pytest.mark.requires_pg
@pytestmark_pg
async def test_alembic_statements_skipped(pg_engine) -> None:
    """OBS-12 — statements containing 'alembic_version' do NOT emit metric."""
    before = _histogram_count(
        "localstock_db_query_duration_seconds",
        {"query_type": "SELECT", "table_class": "cold"},
    )
    async with pg_engine.connect() as conn:
        # Use a literal SELECT containing 'alembic_version' as a string literal
        # so we don't depend on an actual alembic_version table existing.
        await conn.execute(text("SELECT 'alembic_version' AS marker"))
    after = _histogram_count(
        "localstock_db_query_duration_seconds",
        {"query_type": "SELECT", "table_class": "cold"},
    )
    assert after == before, f"alembic-skipped statement still observed: before={before} after={after}"


@pytest.mark.asyncio
@pytest.mark.requires_pg
@pytestmark_pg
async def test_slow_query_emits_log_and_counter(
    pg_engine, monkeypatch, loguru_warning_records
) -> None:
    """OBS-13 — query > threshold emits slow_query log + counter increment."""
    monkeypatch.setenv("SLOW_QUERY_THRESHOLD_MS", "50")
    from localstock.config import get_settings

    get_settings.cache_clear()  # RESEARCH Pitfall 3 — drop cached Settings
    try:
        before = _metric_value(
            "localstock_db_query_slow_total",
            {"query_type": "SELECT", "table_class": "cold"},
        )
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT pg_sleep(0.1)"))
        after = _metric_value(
            "localstock_db_query_slow_total",
            {"query_type": "SELECT", "table_class": "cold"},
        )
        assert after >= before + 1, f"slow counter not incremented: before={before} after={after}"

        slow_logs = [r for r in loguru_warning_records if r["message"] == "slow_query"]
        assert slow_logs, "no slow_query log line emitted"
        rec = slow_logs[-1]
        extra = rec["extra"]
        assert extra["threshold_ms"] == 50
        assert extra["query_type"] == "SELECT"
        assert extra["table_class"] == "cold"
        assert "duration_ms" in extra
        assert "statement_preview" in extra
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.requires_pg
@pytestmark_pg
async def test_fast_query_does_not_trigger_slow_log(
    pg_engine, monkeypatch, loguru_warning_records
) -> None:
    """OBS-13 — query < threshold: no slow_query log, counter unchanged."""
    monkeypatch.setenv("SLOW_QUERY_THRESHOLD_MS", "10000")
    from localstock.config import get_settings

    get_settings.cache_clear()
    try:
        before = _metric_value(
            "localstock_db_query_slow_total",
            {"query_type": "SELECT", "table_class": "cold"},
        )
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        after = _metric_value(
            "localstock_db_query_slow_total",
            {"query_type": "SELECT", "table_class": "cold"},
        )
        assert after == before, f"fast query falsely flagged slow: before={before} after={after}"
        slow_logs = [r for r in loguru_warning_records if r["message"] == "slow_query"]
        assert not slow_logs, f"unexpected slow_query log: {slow_logs}"
    finally:
        get_settings.cache_clear()
