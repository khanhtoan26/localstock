"""Tests for sector rotation service (SCOR-05)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.services.sector_service import SectorService


def _make_score(symbol, total_score, grade):
    score = MagicMock()
    score.symbol = symbol
    score.total_score = total_score
    score.grade = grade
    return score


def _make_group(group_code, group_name_vi):
    group = MagicMock()
    group.group_code = group_code
    group.group_name_vi = group_name_vi
    return group


def _make_snapshot(group_code, avg_score, avg_score_change, snap_date, stock_count=5):
    snap = MagicMock()
    snap.group_code = group_code
    snap.avg_score = avg_score
    snap.avg_score_change = avg_score_change
    snap.date = snap_date
    snap.stock_count = stock_count
    return snap


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestSectorServiceComputeSnapshot:

    async def test_compute_snapshot_aggregates_by_group(self, mock_session):
        service = SectorService.__new__(SectorService)
        service.session = mock_session
        service.score_repo = AsyncMock()
        service.industry_repo = AsyncMock()
        service.sector_repo = AsyncMock()

        today = date(2026, 4, 16)
        service.score_repo.get_latest_date = AsyncMock(return_value=today)
        service.score_repo.get_by_date = AsyncMock(return_value=[
            _make_score("VCB", 80.0, "A"),
            _make_score("ACB", 70.0, "B"),
            _make_score("HPG", 60.0, "B"),
        ])

        service.industry_repo.get_all_groups = AsyncMock(return_value=[
            _make_group("NGAN_HANG", "Ngân hàng"),
            _make_group("THEP", "Thép"),
        ])
        service.industry_repo.get_symbols_by_group = AsyncMock(side_effect=[
            ["VCB", "ACB"],  # NGAN_HANG
            ["HPG"],         # THEP
        ])
        service.sector_repo.get_latest = AsyncMock(return_value=None)
        service.sector_repo.bulk_upsert = AsyncMock(return_value=2)

        snapshots = await service.compute_snapshot(today)
        assert len(snapshots) == 2
        # NGAN_HANG: avg of 80+70=75
        bank_snap = next(s for s in snapshots if s["group_code"] == "NGAN_HANG")
        assert bank_snap["avg_score"] == 75.0
        assert bank_snap["stock_count"] == 2
        # THEP: avg of 60
        steel_snap = next(s for s in snapshots if s["group_code"] == "THEP")
        assert steel_snap["avg_score"] == 60.0


class TestSectorServiceRotationSummary:

    async def test_classifies_inflow_outflow(self, mock_session):
        service = SectorService.__new__(SectorService)
        service.session = mock_session
        service.score_repo = AsyncMock()
        service.industry_repo = AsyncMock()
        service.sector_repo = AsyncMock()

        today = date(2026, 4, 16)
        service.score_repo.get_latest_date = AsyncMock(return_value=today)
        service.sector_repo.get_by_date = AsyncMock(return_value=[
            _make_snapshot("NGAN_HANG", 75.0, 5.0, today),   # inflow
            _make_snapshot("BDS", 45.0, -4.0, today),         # outflow
            _make_snapshot("THEP", 60.0, 0.5, today),          # stable
        ])
        service.industry_repo.get_all_groups = AsyncMock(return_value=[
            _make_group("NGAN_HANG", "Ngân hàng"),
            _make_group("BDS", "Bất động sản"),
            _make_group("THEP", "Thép"),
        ])

        result = await service.get_rotation_summary(today)
        assert len(result["inflow"]) == 1
        assert result["inflow"][0]["group_code"] == "NGAN_HANG"
        assert len(result["outflow"]) == 1
        assert result["outflow"][0]["group_code"] == "BDS"
        assert len(result["stable"]) == 1

    async def test_returns_empty_when_no_data(self, mock_session):
        service = SectorService.__new__(SectorService)
        service.session = mock_session
        service.score_repo = AsyncMock()
        service.score_repo.get_latest_date = AsyncMock(return_value=None)

        result = await service.get_rotation_summary()
        assert result["inflow"] == []
        assert result["outflow"] == []
