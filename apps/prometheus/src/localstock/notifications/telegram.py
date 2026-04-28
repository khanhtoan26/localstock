"""Telegram bot notification sender (NOTI-01, NOTI-02).

Per D-01: Uses python-telegram-bot Bot class for send-only operation (no command handlers).
Silently skips if bot token not configured. Uses HTML parse mode for simpler escaping.
Per Pitfall 4: Splits messages exceeding 4000 chars.
Per Pitfall 2: Caller should check NotificationRepository.was_sent_today before calling.
"""

from loguru import logger
from telegram import Bot
from telegram.constants import ParseMode

from localstock.config import get_settings


class TelegramNotifier:
    """Sends stock analysis notifications via Telegram."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self._bot: Bot | None = None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram credentials are set."""
        return bool(self.bot_token) and bool(self.chat_id)

    def _get_bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def send_message(self, text: str) -> bool:
        """Send a message to the configured Telegram chat.

        Uses HTML parse mode. Splits long messages at ~4000 chars.
        Returns True if sent successfully, False on error.
        Silently returns False if not configured (no token/chat_id).
        """
        if not self.is_configured:
            logger.debug("Telegram not configured — skipping notification")
            return False

        try:
            bot = self._get_bot()
            if len(text) > 4000:
                parts = self._split_message(text, 4000)
                for part in parts:
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=part,
                        parse_mode=ParseMode.HTML,
                    )
            else:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                )
            return True
        except Exception:
            logger.exception("telegram.send.failed")
            return False

    @staticmethod
    def _split_message(text: str, max_len: int = 4000) -> list[str]:
        """Split a long message at newline boundaries.

        Args:
            text: Full message text.
            max_len: Maximum characters per part.

        Returns:
            List of message parts, each <= max_len chars.
        """
        parts = []
        while len(text) > max_len:
            # Find last newline before max_len
            split_idx = text.rfind("\n", 0, max_len)
            if split_idx == -1:
                split_idx = max_len  # No newline found, hard split
            parts.append(text[:split_idx])
            text = text[split_idx:].lstrip("\n")
        if text:
            parts.append(text)
        return parts
