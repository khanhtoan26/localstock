"""Phase 24 — test_scheduler shared fixtures."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from loguru import logger


@pytest.fixture
def mock_telegram_send(monkeypatch):
    """Replace TelegramNotifier.send_message with AsyncMock; force is_configured=True.

    Phase 24-05 / OBS-16. Used by error_listener tests so the fire-and-forget
    Telegram dispatch path never reaches the real Bot HTTP call.
    """
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "localstock.notifications.telegram.TelegramNotifier.send_message", sent
    )
    monkeypatch.setattr(
        "localstock.notifications.telegram.TelegramNotifier.is_configured",
        property(lambda self: True),
    )
    return sent


@pytest.fixture
def loguru_caplog():
    """Capture loguru records for the duration of the test."""
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
