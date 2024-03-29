from enum import Enum, unique

from telebot.async_telebot import AsyncTeleBot

from project.core import settings

bot = AsyncTeleBot(settings.TELEGRAM.BOT_TOKEN)
reports_bot = AsyncTeleBot(settings.GENERAL.REPORTS_TELEGRAM_BOT_TOKEN)


@unique
class ParseMode(str, Enum):
    """Parse Mode"""

    MARKDOWN = 'MARKDOWN'
