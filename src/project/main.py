import asyncio
import functools
import signal
from logging import getLogger

import telebot_views
from telebot_views.models.cache import CacheModel
from telebot_views.utils import now_utc

import project
from project.core.bot import bot, reports_bot
from project.core.settings import GENERAL
from project.db.models.reviews import init_reviews_collection
from project.db.mongodb import get_database
from project.views.routes import routes

logger = getLogger(__name__)


telebot_views.init(
    tele_bot=bot,
    routes=routes,
    skip_non_private=True,
    reports_bot=reports_bot,
    reports_chat_id=GENERAL.REPORTS_TELEGRAM_CHAT_ID,
    loop=project.loop,
)


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
    loop = asyncio.get_running_loop()
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame), functools.partial(_ask_exit, signame, loop))
    await get_database().list_collection_names()
    _ = loop.create_task(init_reviews_collection())

    long_running_tasks = [
        loop.create_task(task_clear_cache()),
    ]
    await bot.delete_webhook()
    await bot.polling(non_stop=True, skip_pending=True)
    await asyncio.gather(*long_running_tasks)


def run_loop(func=run):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_init_bot())
        loop.run_until_complete(func())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Caught KeyboardInterrupt')
    finally:
        _cancel_all_tasks(loop)
        logger.info('Async Tasks cancelled')
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
        logger.info('Loop closed')


async def _init_bot() -> None:
    bot._user = await bot.get_me()  # pylint: disable=protected-access


def _ask_exit(_signame, _loop: asyncio.BaseEventLoop):
    logger.info("got signal %s: exit", _signame)
    raise SystemExit


def _cancel_all_tasks(loop):
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    'message': 'unhandled exception during run() shutdown',
                    'exception': task.exception(),
                    'task': task,
                }
            )


if __name__ == '__main__':
    run_loop()
