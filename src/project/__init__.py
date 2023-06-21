import asyncio
from logging import getLogger

import telebot_models.models

from project.db.mongodb import get_collection

logger = getLogger('project')


telebot_models.models.set_collection_getter(get_collection)


def exception_handler(_loop, context) -> None:
    exc = context.get('exception')
    msg = context.get('message')
    if exc and msg:
        logger.error('Exception in loop: `%s: %s`', type(exc).__name__, str(exc))
    elif msg:
        logger.error('Exception in loop: `%s`', msg)


loop = asyncio.new_event_loop()
loop.set_exception_handler(exception_handler)
asyncio.set_event_loop(loop)
