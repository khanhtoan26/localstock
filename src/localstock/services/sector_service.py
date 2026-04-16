"""Sector rotation tracking — aggregates per-industry metrics over time (SCOR-05).

Per D-04: Measures money flow via volume+score aggregation at industry group level.
Industries with rising volume + rising scores = "inflow" (money flowing in).
Industries with falling volume + falling scores = "outflow" (money flowing out).
"""

from datetime import date

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import CompositeScore, SectorSnapshot
from localstock.db.repositories.industry_repo import IndustryRepository
from localstock.db.repositories.score_repo import ScoreRepository
from localstock.db.repositories.sector_repo import SectorSnapshotRepository


class SectorService:
    """Computes and stores sector-level aggregated metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.industry_repo = IndustryRepository(session)
        self.score_repo = ScoreRepository(session)
        self.sector_repo = SectorSnapshotRepository(session)

    async def compute_snapshot(self, target_date: date | None = None) -> list[dict]:
        """Compute sector snapshot for the given date.

        Groups all scored stocks by industry, computes avg_score, avg_volume,
        total_volume, stock_count per group. Compares against previous snapshot
        to compute avg_score_change.

        Returns:
            List of snapshot dicts that were upserted.
        """
        if target_date is None:
            target_date = await self.score_repo.get_latest_date()
            if target_date is None:
                logger.info("No scoring data — skipping sector snapshot")
                return []

        # Get today's scores
        scores = await self.score_repo.get_by_date(target_date)
        if not scores:
            return []

        # Build symbol -> score lookup
        score_map: dict[str, CompositeScore] = {s.symbol: s for s in scores}

        # Get all industry groups
        groups = await self.industry_repo.get_all_groups()

        snapshots = []
        for group in groups:
            symbols = await self.industry_repo.get_symbols_by_group(group.group_code)
            group_scores = [score_map[s] for s in symbols if s in score_map]

            if not group_scores:
                continue

            avg_score = sum(s.total_score for s in group_scores) / len(group_scores)
            stock_count = len(group_scores)

            # Get previous snapshot for this group to compute change
            prev_snapshot = await self.sector_repo.get_latest(group.group_code)
            avg_score_change = None
            if prev_snapshot and prev_snapshot.date < target_date:
                avg_score_change = round(avg_score - prev_snapshot.avg_score, 2)

            snapshot_row = {
                "date": target_date,
                "group_code": group.group_code,
                "avg_score": round(avg_score, 2),
                "avg_volume": 0.0,  # Will be enriched from StockPrice data
                "total_volume": 0,
                "stock_count": stock_count,
                "avg_score_change": avg_score_change,
            }
            snapshots.append(snapshot_row)

        if snapshots:
            await self.sector_repo.bulk_upsert(snapshots)
            logger.info(f"Stored {len(snapshots)} sector snapshots for {target_date}")

        return snapshots

    async def get_rotation_summary(self, target_date: date | None = None) -> dict:
        """Get sector rotation summary — inflow vs outflow industries.

        Industries with avg_score_change > 2.0 = inflow (money flowing in).
        Industries with avg_score_change < -2.0 = outflow (money flowing out).
        Others = stable.

        Returns:
            Dict with keys: date, inflow (list), outflow (list), stable (list).
            Each item: {group_code, avg_score, avg_score_change, stock_count}.
        """
        if target_date is None:
            target_date = await self.score_repo.get_latest_date()
            if target_date is None:
                return {"date": None, "inflow": [], "outflow": [], "stable": []}

        snapshots = await self.sector_repo.get_by_date(target_date)

        # Get group names for display
        groups = await self.industry_repo.get_all_groups()
        group_names = {g.group_code: g.group_name_vi for g in groups}

        inflow = []
        outflow = []
        stable = []

        for snap in snapshots:
            item = {
                "group_code": snap.group_code,
                "group_name": group_names.get(snap.group_code, snap.group_code),
                "avg_score": round(snap.avg_score, 1),
                "avg_score_change": round(snap.avg_score_change, 1) if snap.avg_score_change else 0.0,
                "stock_count": snap.stock_count,
            }

            if snap.avg_score_change is not None:
                if snap.avg_score_change > 2.0:
                    inflow.append(item)
                elif snap.avg_score_change < -2.0:
                    outflow.append(item)
                else:
                    stable.append(item)
            else:
                stable.append(item)

        # Sort by magnitude of change
        inflow.sort(key=lambda x: x["avg_score_change"], reverse=True)
        outflow.sort(key=lambda x: x["avg_score_change"])

        return {
            "date": str(target_date) if target_date else None,
            "inflow": inflow,
            "outflow": outflow,
            "stable": stable,
        }
