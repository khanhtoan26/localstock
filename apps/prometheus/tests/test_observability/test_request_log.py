"""Tests for Phase 22 OBS-04: RequestLogMiddleware emits structured access logs.

# RED until Wave 1 — depends on RequestLogMiddleware wired into create_app().
"""

from fastapi.testclient import TestClient

from localstock.api.app import create_app
from localstock.observability.middleware import RequestLogMiddleware  # noqa: F401


class TestRequestLogMiddleware:
    def test_request_completed_event_emitted(self, loguru_caplog):
        client = TestClient(create_app())
        resp = client.get("/health")
        assert resp.status_code == 200

        matches = [r for r in loguru_caplog.records if r["message"] == "http.request.completed"]
        assert matches, "expected at least one http.request.completed log record"

        rec = matches[-1]
        extra = rec["extra"]
        assert extra["method"] == "GET"
        assert extra["path"] == "/health"
        assert extra["status"] == 200
        assert isinstance(extra["duration_ms"], float)
        assert extra["duration_ms"] >= 0.0
