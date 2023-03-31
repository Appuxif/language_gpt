import asyncio
from logging import getLogger

from telebot.types import CallbackQuery, Message

from project.core.bot import bot
from project.core.logging import configure_logging
from project.core.views.base import Request, RouteResolver
from project.core.views.dispatcher import ViewDispatcher
from project.db.mongodb import get_database
from project.views.routes import routes

logger = getLogger(__name__)


for route in routes:
    RouteResolver.register_route(route)


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
