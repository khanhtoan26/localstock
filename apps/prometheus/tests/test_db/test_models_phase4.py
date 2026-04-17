"""Tests for Phase 4 models (MacroIndicator, AnalysisReport) and repositories."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from localstock.db.models import AnalysisReport, MacroIndicator


# ── Model field & constraint tests ──────────────────────────────────────────


class TestMacroIndicatorModel:
    """Tests for MacroIndicator ORM model."""

    def test_tablename(self):
        assert MacroIndicator.__tablename__ == "macro_indicators"

    def test_has_required_columns(self):
        col_names = {c.name for c in MacroIndicator.__table__.columns}
        expected = {
            "id",
            "indicator_type",
            "value",
            "period",
            "source",
            "trend",
            "recorded_at",
            "fetched_at",
        }
        assert expected.issubset(col_names), f"Missing: {expected - col_names}"

    def test_indicator_type_string_length(self):
        col = MacroIndicator.__table__.c.indicator_type
        assert col.type.length == 30

    def test_period_string_length(self):
        col = MacroIndicator.__table__.c.period
        assert col.type.length == 20

    def test_source_string_length(self):
        col = MacroIndicator.__table__.c.source
        assert col.type.length == 50

    def test_trend_nullable(self):
        col = MacroIndicator.__table__.c.trend
        assert col.nullable is True

    def test_trend_string_length(self):
        col = MacroIndicator.__table__.c.trend
        assert col.type.length == 20

    def test_recorded_at_is_date(self):
        from sqlalchemy import Date

        col = MacroIndicator.__table__.c.recorded_at
        assert isinstance(col.type, Date)

    def test_fetched_at_is_tz_aware_datetime(self):
        from sqlalchemy import DateTime

        col = MacroIndicator.__table__.c.fetched_at
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True

    def test_unique_constraint_name(self):
        constraint_names = [
            c.name
            for c in MacroIndicator.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_macro_indicator" in constraint_names

    def test_unique_constraint_columns(self):
        from sqlalchemy import UniqueConstraint

        for c in MacroIndicator.__table__.constraints:
            if isinstance(c, UniqueConstraint) and c.name == "uq_macro_indicator":
                col_names = [col.name for col in c.columns]
                assert col_names == ["indicator_type", "period"]
                return
        pytest.fail("uq_macro_indicator constraint not found")

    def test_id_is_primary_key(self):
        col = MacroIndicator.__table__.c.id
        assert col.primary_key is True

    def test_id_autoincrement(self):
        col = MacroIndicator.__table__.c.id
        assert col.autoincrement is True or col.autoincrement == "auto"

    def test_value_is_float(self):
        from sqlalchemy import Float

        col = MacroIndicator.__table__.c.value
        assert isinstance(col.type, Float)


class TestAnalysisReportModel:
    """Tests for AnalysisReport ORM model."""

    def test_tablename(self):
        assert AnalysisReport.__tablename__ == "analysis_reports"

    def test_has_required_columns(self):
        col_names = {c.name for c in AnalysisReport.__table__.columns}
        expected = {
            "id",
            "symbol",
            "date",
            "report_type",
            "content_json",
            "summary",
            "recommendation",
            "t3_prediction",
            "model_used",
            "total_score",
            "grade",
            "generated_at",
        }
        assert expected.issubset(col_names), f"Missing: {expected - col_names}"

    def test_symbol_indexed(self):
        col = AnalysisReport.__table__.c.symbol
        assert col.index is True

    def test_symbol_string_length(self):
        col = AnalysisReport.__table__.c.symbol
        assert col.type.length == 10

    def test_date_indexed(self):
        col = AnalysisReport.__table__.c.date
        assert col.index is True

    def test_report_type_string_length(self):
        col = AnalysisReport.__table__.c.report_type
        assert col.type.length == 20

    def test_content_json_type(self):
        from sqlalchemy import JSON

        col = AnalysisReport.__table__.c.content_json
        assert isinstance(col.type, JSON)

    def test_summary_is_text(self):
        from sqlalchemy import Text

        col = AnalysisReport.__table__.c.summary
        assert isinstance(col.type, Text)

    def test_recommendation_string_length(self):
        col = AnalysisReport.__table__.c.recommendation
        assert col.type.length == 20

    def test_t3_prediction_nullable(self):
        col = AnalysisReport.__table__.c.t3_prediction
        assert col.nullable is True

    def test_t3_prediction_string_length(self):
        col = AnalysisReport.__table__.c.t3_prediction
        assert col.type.length == 20

    def test_model_used_string_length(self):
        col = AnalysisReport.__table__.c.model_used
        assert col.type.length == 50

    def test_total_score_is_float(self):
        from sqlalchemy import Float

        col = AnalysisReport.__table__.c.total_score
        assert isinstance(col.type, Float)

    def test_grade_string_length(self):
        col = AnalysisReport.__table__.c.grade
        assert col.type.length == 2

    def test_generated_at_is_tz_aware_datetime(self):
        from sqlalchemy import DateTime

        col = AnalysisReport.__table__.c.generated_at
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True

    def test_unique_constraint_name(self):
        constraint_names = [
            c.name
            for c in AnalysisReport.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_analysis_report" in constraint_names

    def test_unique_constraint_columns(self):
        from sqlalchemy import UniqueConstraint

        for c in AnalysisReport.__table__.constraints:
            if isinstance(c, UniqueConstraint) and c.name == "uq_analysis_report":
                col_names = [col.name for col in c.columns]
                assert col_names == ["symbol", "date", "report_type"]
                return
        pytest.fail("uq_analysis_report constraint not found")

    def test_id_is_primary_key(self):
        col = AnalysisReport.__table__.c.id
        assert col.primary_key is True


# ── Repository tests ────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    return session


class TestMacroRepository:
    """Tests for MacroRepository CRUD methods."""

    def test_init_accepts_session(self, mock_session):
        from localstock.db.repositories.macro_repo import MacroRepository

        repo = MacroRepository(mock_session)
        assert repo.session is mock_session

    @pytest.mark.asyncio
    async def test_bulk_upsert_returns_count(self, mock_session):
        from localstock.db.repositories.macro_repo import MacroRepository

        repo = MacroRepository(mock_session)
        rows = [
            {
                "indicator_type": "interest_rate",
                "value": 4.5,
                "period": "2026-Q1",
                "source": "SBV",
                "recorded_at": date(2026, 3, 31),
            },
            {
                "indicator_type": "cpi",
                "value": 3.2,
                "period": "2026-03",
                "source": "GSO",
                "recorded_at": date(2026, 3, 15),
            },
        ]
        count = await repo.bulk_upsert(rows)
        assert count == 2
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_empty_list(self, mock_session):
        from localstock.db.repositories.macro_repo import MacroRepository

        repo = MacroRepository(mock_session)
        count = await repo.bulk_upsert([])
        assert count == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_latest_by_type_calls_execute(self, mock_session):
        from localstock.db.repositories.macro_repo import MacroRepository

        repo = MacroRepository(mock_session)
        result = await repo.get_latest_by_type("interest_rate")
        assert result is None  # mock returns None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_latest_calls_execute(self, mock_session):
        from localstock.db.repositories.macro_repo import MacroRepository

        repo = MacroRepository(mock_session)
        result = await repo.get_all_latest()
        assert result == []
        mock_session.execute.assert_called()


class TestReportRepository:
    """Tests for ReportRepository CRUD methods."""

    def test_init_accepts_session(self, mock_session):
        from localstock.db.repositories.report_repo import ReportRepository

        repo = ReportRepository(mock_session)
        assert repo.session is mock_session

    @pytest.mark.asyncio
    async def test_upsert_calls_execute(self, mock_session):
        from localstock.db.repositories.report_repo import ReportRepository

        repo = ReportRepository(mock_session)
        row = {
            "symbol": "VNM",
            "date": date(2026, 4, 15),
            "report_type": "daily",
            "content_json": {"analysis": "test"},
            "summary": "Test summary",
            "recommendation": "buy",
            "model_used": "qwen2.5:14b",
            "total_score": 85.0,
            "grade": "A",
        }
        await repo.upsert(row)
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_for_missing(self, mock_session):
        from localstock.db.repositories.report_repo import ReportRepository

        repo = ReportRepository(mock_session)
        result = await repo.get_latest("VNM")
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_date_returns_list(self, mock_session):
        from localstock.db.repositories.report_repo import ReportRepository

        repo = ReportRepository(mock_session)
        result = await repo.get_by_date(date(2026, 4, 15))
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_symbol_and_date(self, mock_session):
        from localstock.db.repositories.report_repo import ReportRepository

        repo = ReportRepository(mock_session)
        result = await repo.get_by_symbol_and_date("VNM", date(2026, 4, 15))
        assert result is None
        mock_session.execute.assert_called_once()
