"""Phase 25 / DQ-08 — Quarantine repository (D-02).

Polymorphic destination for rejected OHLCV/financial/indicator rows.
Inserts wrap payload in ``sanitize_jsonb`` (belt + suspenders with DQ-04).
Retention is 30 days (CONTEXT D-02), enforced by the APScheduler cron in
``scheduler.py`` (registered separately).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.dq.sanitizer import sanitize_jsonb


class QuarantineRepository:
    """Persist rejected rows from Tier 1 validation into ``quarantine_rows``."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        *,
        source: str,
        symbol: str | None,
        payload: dict | list,
        reason: str,
        rule: str,
        tier: str,
    ) -> None:
        """Insert one rejected row. Caller commits.

        Payload is sanitized via ``sanitize_jsonb`` (NaN/Inf → None) as a
        belt-and-suspenders cross-check with DQ-04 — even if a future caller
        forgets to pre-sanitize, the JSONB write boundary stays clean.
        """
        clean = sanitize_jsonb(payload)
        await self.session.execute(
            text(
                "INSERT INTO quarantine_rows "
                "(source, symbol, payload, reason, rule, tier) "
                "VALUES (:source, :symbol, CAST(:payload AS JSONB), "
                "        :reason, :rule, :tier)"
            ),
            {
                "source": source,
                "symbol": symbol,
                "payload": json.dumps(clean),
                "reason": reason,
                "rule": rule,
                "tier": tier,
            },
        )

    async def cleanup_older_than(self, *, days: int = 30) -> int:
        """Delete rows where ``quarantined_at`` is older than ``days``.

        Caller commits. Returns affected row count. Default 30 days per
        CONTEXT D-02.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            text("DELETE FROM quarantine_rows WHERE quarantined_at < :cutoff"),
            {"cutoff": cutoff},
        )
        n = result.rowcount or 0
        logger.info("dq.quarantine.cleanup", deleted=n, days=days)
        return n
