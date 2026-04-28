"""Tests for Phase 22 Pitfall 17: exception logs must not leak in-scope secrets.

# RED until Wave 1 — depends on configure_logging() installing the redaction patcher
# AND on loguru being configured with `diagnose=False` for production-safe tracebacks.
"""

from loguru import logger

from localstock.observability.logging import configure_logging


class TestDiagnoseNoPii:
    def test_exception_traceback_does_not_leak_secret_in_scope(self, capsys):
        configure_logging()
        token = "AAA-SECRET-BBB"  # noqa: S105 — test fixture, not a real secret
        try:
            _ = token  # ensure variable is in scope at point of failure
            1 / 0
        except ZeroDivisionError:
            logger.exception("boom")
        out = capsys.readouterr().out
        assert "AAA-SECRET-BBB" not in out, (
            "loguru `diagnose=True` (default) leaked an in-scope variable's value into "
            "the traceback — Phase 22 must run with diagnose=False in non-dev mode."
        )
