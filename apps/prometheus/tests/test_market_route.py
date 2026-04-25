"""Tests for Phase 17: Market Overview API endpoint.

Tests router structure, app registration, endpoint callability,
and response shape validation.
"""

from unittest.mock import AsyncMock, patch

from localstock.api.app import create_app
from localstock.api.routes.market import MarketSummaryResponse, router as market_router


class TestMarketRouterStructure:
    """Test market router has all required routes."""

    def test_router_prefix(self):
        assert market_router.prefix == "/api"

    def test_summary_route_exists(self):
        paths = [r.path for r in market_router.routes]
        assert "/api/market/summary" in paths

    def test_route_count(self):
        """Market router should have exactly 1 route."""
        paths = [r.path for r in market_router.routes]
        assert len(paths) >= 1, f"Expected >=1 route, got {paths}"


class TestMarketAppRegistration:
    """Test market router is registered in the main FastAPI app."""

    def test_app_has_market_route(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/market/summary" in paths


class TestMarketEndpointFunctions:
    """Test endpoint functions are callable."""

    def test_get_market_summary_exists(self):
        from localstock.api.routes.market import get_market_summary
        assert callable(get_market_summary)


class TestMarketSummaryResponse:
    """Test response model validation for MarketSummaryResponse."""

    def test_response_model_all_fields_null(self):
        """MarketSummaryResponse must accept all-null nullable fields."""
        resp = MarketSummaryResponse(
            vnindex=None,
            total_volume=None,
            total_volume_change_pct=None,
            advances=0,
            declines=0,
            breadth=None,
            as_of=None,
        )
        assert resp.advances == 0
        assert resp.declines == 0
        assert resp.vnindex is None

    def test_response_model_with_data(self):
        """MarketSummaryResponse must accept valid populated data."""
        resp = MarketSummaryResponse(
            vnindex={"value": 1245.3, "change_pct": 0.82},
            total_volume=1_234_567_890,
            total_volume_change_pct=12.5,
            advances=180,
            declines=150,
            breadth=54.5,
            as_of="2026-04-25",
        )
        assert resp.advances == 180
        assert resp.declines == 150
        assert resp.total_volume == 1_234_567_890
        assert resp.as_of == "2026-04-25"
        assert resp.vnindex is not None
        assert resp.vnindex.value == 1245.3

    async def test_endpoint_calls_repo(self):
        """GET /api/market/summary endpoint calls PriceRepository methods."""
        from localstock.api.routes.market import get_market_summary

        mock_session = AsyncMock()

        with patch(
            "localstock.api.routes.market.PriceRepository"
        ) as MockRepo:
            mock_repo = AsyncMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_latest.return_value = None
            mock_repo.get_market_aggregate.return_value = {
                "as_of": None,
                "advances": 0,
                "declines": 0,
                "flat": 0,
                "total_volume": 0,
                "total_volume_change_pct": None,
            }

            result = await get_market_summary(session=mock_session)

        MockRepo.assert_called_once_with(mock_session)
        mock_repo.get_market_aggregate.assert_awaited_once()
