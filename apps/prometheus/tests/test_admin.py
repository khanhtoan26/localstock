"""Tests for Phase 11: Admin API endpoints.

Tests router structure, endpoint availability, request model validation,
and concurrency lock behavior.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from localstock.api.app import create_app
from localstock.api.routes.admin import (
    AddStockRequest,
    ReportRequest,
    SymbolsRequest,
    router as admin_router,
)


class TestAdminRouterStructure:
    """Test admin router has all required routes."""

    def test_router_prefix(self):
        assert admin_router.prefix == "/api/admin"

    def test_stock_routes_exist(self):
        paths = [r.path for r in admin_router.routes]
        assert "/api/admin/stocks" in paths
        assert "/api/admin/stocks/{symbol}" in paths

    def test_trigger_routes_exist(self):
        paths = [r.path for r in admin_router.routes]
        assert "/api/admin/crawl" in paths
        assert "/api/admin/analyze" in paths
        assert "/api/admin/score" in paths
        assert "/api/admin/report" in paths
        assert "/api/admin/pipeline" in paths

    def test_job_routes_exist(self):
        paths = [r.path for r in admin_router.routes]
        assert "/api/admin/jobs" in paths
        assert "/api/admin/jobs/{job_id}" in paths

    def test_route_count(self):
        """Admin router should have at least 7 unique paths."""
        paths = [r.path for r in admin_router.routes]
        unique_paths = set(paths)
        assert len(unique_paths) >= 7, f"Expected >=7 unique paths, got {unique_paths}"


class TestAdminAppRegistration:
    """Test admin router is registered in the main app."""

    def test_app_has_admin_routes(self):
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/api/admin/stocks" in paths
        assert "/api/admin/crawl" in paths
        assert "/api/admin/jobs" in paths
        assert "/api/admin/jobs/{job_id}" in paths
        assert "/api/admin/pipeline" in paths

    def test_admin_tag_present(self):
        app = create_app()
        admin_paths = [r.path for r in app.routes if "/api/admin" in r.path]
        assert len(admin_paths) >= 7


class TestAdminEndpointFunctions:
    """Test endpoint functions are callable."""

    def test_list_tracked_stocks_exists(self):
        from localstock.api.routes.admin import list_tracked_stocks
        assert callable(list_tracked_stocks)

    def test_add_stock_exists(self):
        from localstock.api.routes.admin import add_stock
        assert callable(add_stock)

    def test_remove_stock_exists(self):
        from localstock.api.routes.admin import remove_stock
        assert callable(remove_stock)

    def test_trigger_crawl_exists(self):
        from localstock.api.routes.admin import trigger_crawl
        assert callable(trigger_crawl)

    def test_trigger_analyze_exists(self):
        from localstock.api.routes.admin import trigger_analyze
        assert callable(trigger_analyze)

    def test_trigger_score_exists(self):
        from localstock.api.routes.admin import trigger_score
        assert callable(trigger_score)

    def test_trigger_report_exists(self):
        from localstock.api.routes.admin import trigger_report
        assert callable(trigger_report)

    def test_trigger_pipeline_exists(self):
        from localstock.api.routes.admin import trigger_pipeline
        assert callable(trigger_pipeline)

    def test_list_jobs_exists(self):
        from localstock.api.routes.admin import list_jobs
        assert callable(list_jobs)

    def test_get_job_detail_exists(self):
        from localstock.api.routes.admin import get_job_detail
        assert callable(get_job_detail)


class TestRequestModels:
    """Test Pydantic request model validation."""

    def test_add_stock_valid(self):
        req = AddStockRequest(symbol="VNM")
        assert req.symbol == "VNM"

    def test_add_stock_rejects_lowercase(self):
        with pytest.raises(ValidationError):
            AddStockRequest(symbol="vnm")

    def test_add_stock_rejects_empty(self):
        with pytest.raises(ValidationError):
            AddStockRequest(symbol="")

    def test_add_stock_rejects_too_long(self):
        with pytest.raises(ValidationError):
            AddStockRequest(symbol="A" * 11)

    def test_symbols_request_valid(self):
        req = SymbolsRequest(symbols=["VNM", "FPT", "HPG"])
        assert len(req.symbols) == 3

    def test_symbols_request_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            SymbolsRequest(symbols=[])

    def test_report_request_valid(self):
        req = ReportRequest(symbol="FPT")
        assert req.symbol == "FPT"

    def test_report_request_rejects_special_chars(self):
        with pytest.raises(ValidationError):
            ReportRequest(symbol="VN-M")


class TestAdminServiceStructure:
    """Test AdminService has required methods."""

    def test_admin_service_importable(self):
        from localstock.services.admin_service import AdminService
        assert AdminService is not None

    def test_admin_lock_exists(self):
        from localstock.services.admin_service import _admin_lock
        assert isinstance(_admin_lock, asyncio.Lock)

    def test_run_methods_exist(self):
        from localstock.services.admin_service import AdminService
        service = AdminService.__new__(AdminService)
        assert hasattr(service, "run_crawl")
        assert hasattr(service, "run_analyze")
        assert hasattr(service, "run_score")
        assert hasattr(service, "run_report")
        assert hasattr(service, "run_pipeline")


class TestReportServiceExtension:
    """Test ReportService has generate_for_symbol method."""

    def test_generate_for_symbol_exists(self):
        from localstock.services.report_service import ReportService
        assert hasattr(ReportService, "generate_for_symbol")
        assert callable(getattr(ReportService, "generate_for_symbol"))
