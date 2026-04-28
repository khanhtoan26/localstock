"""Loguru capture fixture for Phase 22 observability tests (per CONTEXT.md D-08b)."""
import pytest
from loguru import logger


@pytest.fixture
def loguru_caplog():
    records: list[dict] = []
    sink_id = logger.add(
        lambda msg: records.append(msg.record),
        level="DEBUG",
        format="{message}",
    )

    class _Capture:
        @property
        def records(self):
            return records

    yield _Capture()
    logger.remove(sink_id)
