"""Tests for TelegramNotifier."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from localstock.notifications.telegram import TelegramNotifier


class TestTelegramNotifier:

    def test_is_configured_false_when_empty_token(self):
        notifier = TelegramNotifier(bot_token="", chat_id="123")
        assert notifier.is_configured is False

    def test_is_configured_false_when_empty_chat_id(self):
        notifier = TelegramNotifier(bot_token="token123", chat_id="")
        assert notifier.is_configured is False

    def test_is_configured_true_when_both_set(self):
        notifier = TelegramNotifier(bot_token="token123", chat_id="chat456")
        assert notifier.is_configured is True

    async def test_send_message_skips_when_not_configured(self):
        notifier = TelegramNotifier(bot_token="", chat_id="")
        result = await notifier.send_message("test")
        assert result is False

    @patch("localstock.notifications.telegram.Bot")
    async def test_send_message_calls_bot(self, MockBot):
        mock_bot = AsyncMock()
        MockBot.return_value = mock_bot

        notifier = TelegramNotifier(bot_token="tok123", chat_id="chat456")
        notifier._bot = mock_bot

        result = await notifier.send_message("<b>Hello</b>")
        assert result is True
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == "chat456"
        assert call_kwargs.kwargs["text"] == "<b>Hello</b>"

    @patch("localstock.notifications.telegram.Bot")
    async def test_send_message_returns_false_on_error(self, MockBot):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Network error")
        MockBot.return_value = mock_bot

        notifier = TelegramNotifier(bot_token="tok123", chat_id="chat456")
        notifier._bot = mock_bot

        result = await notifier.send_message("test")
        assert result is False

    def test_split_message_short(self):
        result = TelegramNotifier._split_message("short text", 4000)
        assert result == ["short text"]

    def test_split_message_long(self):
        # Create a 5000-char message with newlines every 100 chars
        text = "\n".join(["x" * 99 for _ in range(51)])
        parts = TelegramNotifier._split_message(text, 4000)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 4000
