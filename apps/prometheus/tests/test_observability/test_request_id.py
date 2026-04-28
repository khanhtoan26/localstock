"""Tests for Phase 22 OBS-02: X-Request-ID middleware.

# RED until Wave 1 — depends on CorrelationIdMiddleware wired into create_app().
Per CONTEXT.md D-02: trust inbound header matching ^[A-Za-z0-9-]{8,64}$,
otherwise generate uuid4().hex; always echo back via response header.
"""

import re

from fastapi.testclient import TestClient

from localstock.api.app import create_app
from localstock.observability.middleware import CorrelationIdMiddleware  # noqa: F401


_HEX32 = re.compile(r"^[A-Fa-f0-9]{32}$")
_VALID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class TestRequestIdHeader:
    def setup_method(self):
        self.client = TestClient(create_app())

    def test_missing_inbound_header_generates_hex(self):
        resp = self.client.get("/health")
        rid = resp.headers.get("X-Request-ID", "")
        assert _HEX32.match(rid), f"expected 32-hex-char request id, got {rid!r}"

    def test_valid_inbound_header_echoed_verbatim(self):
        resp = self.client.get("/health", headers={"X-Request-ID": "testabcdefgh1234"})
        assert resp.headers.get("X-Request-ID") == "testabcdefgh1234"

    def test_malicious_inbound_header_replaced(self):
        # Header injection / control characters must be rejected and replaced.
        resp = self.client.get("/health", headers={"X-Request-ID": "BAD_INJECT!"})
        rid = resp.headers.get("X-Request-ID", "")
        assert _HEX32.match(rid), f"malicious id must be replaced by hex, got {rid!r}"
        assert _VALID.match(rid)
