"""Tests for Phase 22 OBS-01: Structured JSON log format.

# RED until Wave 1 — depends on `localstock.observability.logging.configure_logging`.
"""

import json
import sys
import uuid
from datetime import datetime
from decimal import Decimal

from loguru import logger

from localstock.observability.logging import configure_logging


class TestJsonRoundTrip:
    """Every emitted log line must round-trip cleanly through `json.loads`."""

    def test_basic_extra_round_trips(self, capsys):
        configure_logging()
        logger.info("evt.basic", k=1)
        out = capsys.readouterr().out.strip().splitlines()[-1]
        record = json.loads(out)
        assert record["record"]["extra"]["k"] == 1
        assert record["record"]["message"] == "evt.basic"

    def test_unserializable_extras_do_not_raise(self, capsys):
        """Pitfall 20: datetime/Decimal/UUID must not crash the sink."""
        configure_logging()
        # If any of these explode, the test fails with TypeError; serialize must coerce.
        logger.bind(
            ts=datetime.utcnow(),
            amount=Decimal("3.14"),
            corr=uuid.uuid4(),
        ).info("evt.exotic")
        out = capsys.readouterr().out.strip().splitlines()[-1]
        record = json.loads(out)  # must be valid JSON
        assert record["record"]["message"] == "evt.exotic"
