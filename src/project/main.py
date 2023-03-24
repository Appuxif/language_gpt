import asyncio
from logging import getLogger

from telebot.types import CallbackQuery, Message

from project.core.bot import bot
from project.core.views.base import Request
from project.core.views.dispatcher import ViewDispatcher
from project.db.mongodb import get_database

logger = getLogger(__name__)


@bot.message_handler()
async def message_handler(msg: Message):
    request = Request(msg=msg)
    await ViewDispatcher(request=request).dispatch()
    return


@bot.callback_query_handler(func=lambda call: True)
async def callback_query(callback: CallbackQuery):
    request = Request(callback=callback)
    await ViewDispatcher(request=request).dispatch()
    return


async def run():
    await get_database().list_collection_names()
    await bot.delete_webhook()
    await bot.polling(non_stop=True)


def exception_handler(_loop, context) -> None:
    exc = context.get('exception')
    msg = context.get('message')
    if exc and msg:
        logger.error('Exception in loop: `%s: %s`', type(exc).__name__, str(exc))
    elif msg:
        logger.error('Exception in loop: `%s`', msg)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(exception_handler)
    try:
        loop.run_until_complete(run())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
