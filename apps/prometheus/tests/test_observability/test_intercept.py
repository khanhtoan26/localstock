"""Tests for Phase 22 D-09: stdlib logging → loguru bridge via InterceptHandler.

# RED until Wave 1 — depends on configure_logging() installing the InterceptHandler
# on the root stdlib logger so uvicorn / SQLAlchemy / asyncpg logs become JSON too.
"""

import json
import logging

from localstock.observability.logging import configure_logging


class TestInterceptHandler:
    def test_stdlib_logger_emits_through_loguru(self, capsys):
        configure_logging()
        logging.getLogger("uvicorn").info("hi")
        out = capsys.readouterr().out.strip()
        assert out, "stdlib logger emitted nothing through loguru sink"
        last = out.splitlines()[-1]
        record = json.loads(last)
        assert record["record"]["message"] == "hi"
        assert record["record"]["level"]["name"] in {"INFO"}
