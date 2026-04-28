"""Tests for Phase 22 Pitfall 5: configure_logging() must be idempotent.

# RED until Wave 1 — depends on `localstock.observability.logging.configure_logging`.
Calling configure_logging() twice must NOT register duplicate sinks (would emit each
record N times, blow up tests, double-redact).
"""

from loguru import logger

from localstock.observability.logging import configure_logging


class TestIdempotentConfigureLogging:
    def test_double_configure_yields_single_sink(self):
        configure_logging()
        first = len(logger._core.handlers)
        configure_logging()
        second = len(logger._core.handlers)
        assert first == second, (
            f"configure_logging() is not idempotent: handler count went {first} → {second}"
        )
