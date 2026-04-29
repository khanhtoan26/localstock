"""Phase 25 / DQ-08 — Quarantine repository (D-02).

Implementation lands in 25-03. Wave 0 stub.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


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
        raise NotImplementedError("DQ-08: implemented in 25-03-PLAN.md")

    async def cleanup_older_than(self, *, days: int = 30) -> int:
        raise NotImplementedError("DQ-08: implemented in 25-03-PLAN.md")
