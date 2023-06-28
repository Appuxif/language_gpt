import asyncio
from logging import getLogger

import telebot_views

from project.core.bot import bot
from project.core.logging import configure_logging
from project.db.mongodb import get_database
from project.views.routes import routes

logger = getLogger(__name__)


telebot_views.init(bot, routes)


async def run():
    await get_database().list_collection_names()
    await bot.delete_webhook()
    await bot.polling(non_stop=True)


def run_loop():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())


configure_logging()

if __name__ == '__main__':
    run_loop()
