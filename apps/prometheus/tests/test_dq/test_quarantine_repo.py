"""Phase 25 / DQ-08 — QuarantineRepository tests (RED until 25-03 lands).

The repo stub raises NotImplementedError, so the unit tests fail at the
``await repo.insert(...)`` call. The cross-check with sanitize_jsonb
(test_insert_sanitizes_nan_in_payload) doubles as a contract for the
25-02 ↔ 25-03 boundary.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from localstock.dq.quarantine_repo import QuarantineRepository


pytestmark = [pytest.mark.requires_pg, pytest.mark.asyncio]


# Test-local data cleanup wrapping the project-wide `db_session` fixture
# (Phase 26 / 26-01 Task 0 — promoted db_session to tests/conftest.py).
# The shared fixture is a plain async session with rollback teardown; the
# tests below call `session.commit()` to materialise rows, so we own the
# pre/post `DELETE` of our test symbols here.
@pytest_asyncio.fixture(autouse=True)
async def _clean_quarantine_test_rows(db_session):
    sql = text(
        "DELETE FROM quarantine_rows WHERE symbol IN ('BAD','OLD','NEW','NAN')"
    )
    await db_session.execute(sql)
    await db_session.commit()
    yield
    await db_session.execute(sql)
    await db_session.commit()


async def test_insert_persists_row(db_session) -> None:
    repo = QuarantineRepository(db_session)
    await repo.insert(
        source="ohlcv",
        symbol="BAD",
        payload={"open": -1.0},
        reason="negative_price",
        rule="negative_price",
        tier="strict",
    )
    await db_session.commit()
    result = await db_session.execute(
        text(
            "SELECT source, symbol, rule, tier FROM quarantine_rows "
            "WHERE symbol='BAD'"
        )
    )
    row = result.first()
    assert row == ("ohlcv", "BAD", "negative_price", "strict")


async def test_cleanup_30d_deletes_old_rows(db_session) -> None:
    repo = QuarantineRepository(db_session)
    # Insert one fresh + one stale via direct SQL (bypass repo's NOW() default).
    await db_session.execute(
        text(
            "INSERT INTO quarantine_rows(source,symbol,payload,reason,rule,tier,quarantined_at) "
            "VALUES('ohlcv','OLD','{}'::jsonb,'x','x','strict', now() - interval '40 days'),"
            "      ('ohlcv','NEW','{}'::jsonb,'x','x','strict', now())"
        )
    )
    await db_session.commit()
    n = await repo.cleanup_older_than(days=30)
    await db_session.commit()
    assert n == 1
    result = await db_session.execute(
        text("SELECT symbol FROM quarantine_rows WHERE symbol IN ('OLD','NEW')")
    )
    symbols = {r[0] for r in result.fetchall()}
    assert symbols == {"NEW"}


async def test_insert_sanitizes_nan_in_payload(db_session) -> None:
    """DQ-04 ↔ DQ-08 cross-check: quarantine repo applies sanitizer too."""
    repo = QuarantineRepository(db_session)
    await repo.insert(
        source="ohlcv",
        symbol="NAN",
        payload={"close": float("nan"), "open": 1.0},
        reason="nan_check",
        rule="negative_price",
        tier="strict",
    )
    await db_session.commit()
    result = await db_session.execute(
        text("SELECT payload FROM quarantine_rows WHERE symbol='NAN'")
    )
    payload = result.scalar_one()
    # asyncpg returns dict already parsed.
    assert payload["close"] is None
    assert payload["open"] == 1.0
