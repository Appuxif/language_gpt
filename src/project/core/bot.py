from telebot.async_telebot import AsyncTeleBot
from telebot_views.bot import ParseMode

from project.core import settings

bot = AsyncTeleBot(settings.TELEGRAM.BOT_TOKEN)
reports_bot = AsyncTeleBot(settings.GENERAL.REPORTS_TELEGRAM_BOT_TOKEN)


__all__ = (
    'bot',
    'reports_bot',
    'ParseMode',
)
