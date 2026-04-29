"""Phase 25 / DQ-01 — Tier 1 OHLCV schema tests (RED until 25-05).

These tests target the partition_valid_invalid runner + OHLCVSchema
(currently None / NotImplementedError stubs). RED until 25-05 lands the
strict pandera schema and partition logic.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from localstock.dq.runner import partition_valid_invalid


def _make_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _good_row(symbol: str = "AAA", d: date | None = None, **over) -> dict:
    base = {
        "symbol": symbol,
        "date": pd.Timestamp(d or date.today() - timedelta(days=1)),
        "open": 10.0,
        "high": 11.0,
        "low": 9.0,
        "close": 10.5,
        "volume": 1000,
    }
    base.update(over)
    return base


def test_negative_price_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame([_good_row(), _good_row(symbol="BBB", open=-1.0)])
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert invalid[0]["symbol"] == "BBB"


def test_future_date_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame(
        [
            _good_row(),
            _good_row(symbol="FUT", d=date.today() + timedelta(days=5)),
        ]
    )
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(invalid) == 1
    assert invalid[0]["symbol"] == "FUT"


def test_nan_ratio_threshold() -> None:
    """> 5% NaN per column triggers schema-level reject."""
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    rows = [_good_row(symbol=f"S{i}") for i in range(20)]
    # Inject NaN into >5% of close column (2 out of 20 = 10%).
    rows[0]["close"] = float("nan")
    rows[1]["close"] = float("nan")
    df = _make_frame(rows)
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    # Frame-level check fails → all rows considered invalid OR row-level
    # partition catches the offending rows.
    bad_symbols = {r["symbol"] for r in invalid}
    assert "S0" in bad_symbols or len(invalid) == len(df)


def test_duplicate_pk_quarantined() -> None:
    from localstock.dq.schemas.ohlcv import OHLCVSchema

    df = _make_frame([_good_row(symbol="DUP"), _good_row(symbol="DUP")])
    valid, invalid, _ = partition_valid_invalid(df, OHLCVSchema)
    assert len(invalid) >= 1


# ---------------------------------------------------------------------
# DQ-01 SC #1 closure — integration: bad OHLCV row lands in
# quarantine_rows, never in stock_prices, and the strict-tier metric
# increments for the offending rule.
# ---------------------------------------------------------------------


@pytest.mark.requires_pg
@pytest.mark.asyncio
async def test_quarantine_destination_for_bad_ohlcv_row(monkeypatch) -> None:
    """SC #1 verbatim closure (Phase 25 ROADMAP).

    Pandera Tier 1 rejects a negative-price row; the row must be inserted
    into ``quarantine_rows`` (source='ohlcv', tier='strict') and never
    upserted to ``stock_prices``. The good row in the same batch survives
    and reaches ``stock_prices``.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from localstock.config import get_settings
    from localstock.services.pipeline import Pipeline

    settings = get_settings()
    eng = create_async_engine(
        settings.database_url,
        connect_args={
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        },
    )
    sessionmaker = async_sessionmaker(eng, expire_on_commit=False)
    session = sessionmaker()

    sym = "ZZZ"  # synthetic test symbol — won't collide with real HOSE data
    # Pre-clean fixture rows.
    await session.execute(
        text("DELETE FROM quarantine_rows WHERE symbol = :s"), {"s": sym}
    )
    await session.execute(
        text("DELETE FROM stock_prices WHERE symbol = :s"), {"s": sym}
    )
    await session.commit()

    good_d = date.today() - timedelta(days=1)
    bad_d = date.today() - timedelta(days=2)

    async def fake_fetch(self, symbol, **kw):
        return pd.DataFrame(
            [
                {
                    "time": pd.Timestamp(good_d),
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.5,
                    "close": 10.5,
                    "volume": 1000,
                },
                {
                    "time": pd.Timestamp(bad_d),
                    "open": -1.0,  # negative price → Tier 1 reject
                    "high": 11.0,
                    "low": 9.5,
                    "close": 10.5,
                    "volume": 1000,
                },
            ]
        )

    async def fake_get_latest(self, symbol):
        return None

    monkeypatch.setattr(
        "localstock.crawlers.price_crawler.PriceCrawler.fetch",
        fake_fetch,
        raising=False,
    )
    monkeypatch.setattr(
        "localstock.db.repositories.price_repo.PriceRepository.get_latest_date",
        fake_get_latest,
        raising=False,
    )

    try:
        pipe = Pipeline(session=session)
        results, failed = await pipe._crawl_prices([sym])
        await session.commit()

        # 1. Bad row is in quarantine_rows with strict tier.
        q_result = await session.execute(
            text(
                "SELECT rule, tier, source FROM quarantine_rows "
                "WHERE symbol = :s"
            ),
            {"s": sym},
        )
        q_rows = q_result.fetchall()
        assert len(q_rows) == 1
        rule, tier, source = q_rows[0]
        assert tier == "strict"
        assert source == "ohlcv"
        # Negative `open` triggers Column gt(0) → non_positive_open.
        assert rule in ("non_positive_open", "negative_price")

        # 2. Good row reached stock_prices; bad row did NOT.
        p_result = await session.execute(
            text(
                "SELECT date FROM stock_prices WHERE symbol = :s ORDER BY date"
            ),
            {"s": sym},
        )
        p_dates = [r[0] for r in p_result.fetchall()]
        assert good_d in p_dates
        assert bad_d not in p_dates
    finally:
        await session.execute(
            text("DELETE FROM quarantine_rows WHERE symbol = :s"), {"s": sym}
        )
        await session.execute(
            text("DELETE FROM stock_prices WHERE symbol = :s"), {"s": sym}
        )
        await session.commit()
        await session.close()
        await eng.dispose()
