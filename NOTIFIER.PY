"""
Send messages to Telegram using python-telegram-bot.
"""

import logging
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send(self, text: str):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    async def send_photo(self, photo_buffer, caption: str = ""):
        try:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo_buffer,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Error sending Telegram photo: {e}")
