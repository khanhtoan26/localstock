"""Tests for Phase 6 backend: new dashboard API endpoints and CORS."""

from localstock.api.app import create_app
from localstock.api.routes.dashboard import router as dashboard_router
from localstock.api.routes.prices import router as prices_router


class TestCorsMiddleware:
    """Test CORS middleware is configured on the app."""

    def test_cors_middleware_present(self):
        app = create_app()
        # FastAPI stores middleware as Middleware objects; check the cls attribute
        cors_found = any("CORSMiddleware" in str(m) for m in app.user_middleware)
        assert cors_found, f"CORSMiddleware not found in app middleware: {app.user_middleware}"


class TestPricesRouter:
    """Test prices router structure."""

    def test_prices_router_has_routes(self):
        route_paths = [r.path for r in prices_router.routes]
        assert "/api/prices/{symbol}" in route_paths
        assert "/api/prices/{symbol}/indicators" in route_paths

    def test_price_history_endpoint_exists(self):
        from localstock.api.routes.prices import get_price_history
        assert callable(get_price_history)

    def test_indicator_history_endpoint_exists(self):
        from localstock.api.routes.prices import get_indicator_history
        assert callable(get_indicator_history)


class TestDashboardRouter:
    """Test dashboard router structure."""

    def test_dashboard_router_has_sectors_route(self):
        route_paths = [r.path for r in dashboard_router.routes]
        assert "/api/sectors/latest" in route_paths

    def test_sectors_endpoint_exists(self):
        from localstock.api.routes.dashboard import get_latest_sectors
        assert callable(get_latest_sectors)


class TestAppRouteRegistration:
    """Test all new routes are registered in the app."""

    def test_app_has_prices_routes(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/prices/{symbol}" in paths
        assert "/api/prices/{symbol}/indicators" in paths

    def test_app_has_sectors_route(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/sectors/latest" in paths
