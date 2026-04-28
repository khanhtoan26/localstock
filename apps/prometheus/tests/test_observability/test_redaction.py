"""Tests for Phase 22 OBS-05: Redaction patcher.

# RED until Wave 1 — depends on `localstock.observability.logging`.
Per CONTEXT.md D-04 (deny-list keys) + D-10 (symbol/chat_id are non-sensitive).
"""

import json

from loguru import logger

from localstock.observability.logging import (
    _redact_url_creds,
    configure_logging,
)


class TestRedactionPatcher:
    def test_url_credentials_redacted(self):
        assert (
            _redact_url_creds("connecting to postgresql://user:hunter2@db:5432/x")
            == "connecting to postgresql://***:***@db:5432/x"
        )

    def test_token_extra_redacted(self, capsys):
        configure_logging()
        logger.bind(telegram_bot_token="123:ABC", symbol="VNM").info("telegram.send")
        out = capsys.readouterr().out
        record = json.loads(out.strip().splitlines()[-1])
        assert record["record"]["extra"]["telegram_bot_token"] == "***REDACTED***"
        # D-10: symbol is NOT a PII surface in this app — must remain intact.
        assert record["record"]["extra"]["symbol"] == "VNM"
