import asyncio
from functools import partial
from logging import Handler, LogRecord
from logging.config import dictConfig

from project.core import settings
from project.core.bot import reports_bot

config = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'common': {
            'format': '%(asctime)s %(levelname)7s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'common',
            'level': 'DEBUG',
        },
        'telegram-reports': {
            'class': 'project.core.logging.TelegramReportsHandler',
            'formatter': 'common',
            'level': 'ERROR',
        },
    },
    'loggers': {
        '__main__': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'project': {
            'level': 'DEBUG',
            'handlers': ['console', 'telegram-reports'],
            'propagate': False,
        },
        'TeleBot': {
            'level': 'DEBUG',
            'handlers': ['console', 'telegram-reports'],
            'propagate': True,
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'flower': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

configure_logging = partial(dictConfig, config)


class TelegramReportsHandler(Handler):
    """Telegram Reports Handler"""

    def filter(self, record: LogRecord) -> bool:
        result = super().filter(record)
        return (
            result
            and bool(settings.GENERAL.REPORTS_TELEGRAM_BOT_TOKEN)
            and bool(settings.GENERAL.REPORTS_TELEGRAM_CHAT_ID)
        )

    def emit(self, record: LogRecord) -> None:
        coro = self.async_emit(record)
        try:
            asyncio.create_task(coro)
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(coro)

    async def async_emit(self, record: LogRecord) -> None:
        if record.exc_info and len(record.exc_info) >= 2:
            record.exc_text = f'{record.exc_info[0].__name__}: {record.exc_info[1]}'
        record.exc_info = None
        msg = self.format(record)
        await reports_bot.send_message(settings.GENERAL.REPORTS_TELEGRAM_CHAT_ID, msg[:3000])
