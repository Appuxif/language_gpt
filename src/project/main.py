import asyncio
from logging import getLogger

import telebot_views
from telebot_views.models.cache import CacheModel
from telebot_views.utils import now_utc

import project
from project.core.bot import bot
from project.db.mongodb import get_database
from project.views.routes import routes

logger = getLogger(__name__)


telebot_views.init(bot, routes, skip_non_private=True, loop=project.loop)


async def task_clear_cache() -> None:
    loop = asyncio.get_running_loop()
    while True:
        start = loop.time()
        logger.info('Clearing invalid cache...')
        result = await CacheModel.manager().filter({'valid_until': {'$lte': now_utc()}}).delete_many()
        logger.info(
            'Clearing invalid cache finished. Took %s sec. Deleted %s', loop.time() - start, result.deleted_count
        )
        await asyncio.sleep(3600 * 24)


async def run():
    _task = asyncio.create_task(task_clear_cache())
    await get_database().list_collection_names()
    await bot.delete_webhook()
    await bot.polling(non_stop=True, skip_pending=True)
    await _task


def run_loop():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Caught KeyboardInterrupt')
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())


if __name__ == '__main__':
    run_loop()
