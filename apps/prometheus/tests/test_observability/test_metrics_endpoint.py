"""Phase 23 — /metrics endpoint integration tests (per 23-VALIDATION.md).

Uses TestClient against ``create_app()``. The autouse
``_isolate_app_from_infra`` fixture in this directory's conftest stubs out
the APScheduler lifespan and the DB session factory, so these tests focus
purely on HTTP middleware + endpoint behavior.

Tests share the global ``prometheus_client.REGISTRY``; safe because
``init_metrics()`` is idempotent (Plan 23-01, OBS-10).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from localstock.api.app import create_app


def test_metrics_endpoint_returns_200_with_correct_content_type() -> None:
    """OBS-07 SC#1 — GET /metrics returns 200 with Prometheus content-type.

    NOTE: prometheus_client 0.25.0 bumped CONTENT_TYPE_LATEST from
    ``text/plain; version=0.0.4`` to ``text/plain; version=1.0.0`` (OpenMetrics
    alignment). Either is a valid Prometheus text exposition format and is
    scrapable by Prometheus. We assert on ``text/plain`` + ``version=`` rather
    than pinning to a specific version (deviation from plan; library behavior).
    """
    client = TestClient(create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    ctype = response.headers.get("content-type", "")
    assert ctype.startswith("text/plain"), ctype
    assert "version=" in ctype, ctype
    assert "charset=utf-8" in ctype, ctype


def test_metrics_endpoint_exposes_default_http_histogram() -> None:
    """OBS-07 SC#1 — default histogram name is present after a request."""
    client = TestClient(create_app())
    # Drive at least one request through the instrumentator middleware so
    # the default histogram has a sample. /health/ is registered in Phase 22
    # and excluded from /metrics-self by the anchored regex (see app.py).
    client.get("/health/")
    body = client.get("/metrics").text
    assert "http_request_duration_seconds" in body, (
        "default Instrumentator histogram missing from /metrics body"
    )
