import asyncio
from logging import getLogger

from telebot.types import CallbackQuery, Message

from project.core.bot import bot
from project.db.models.users import UserStateEmpty
from project.db.mongodb import get_database
from project.services.callback_data_actions import CallbackDataAction
from project.services.keyboard import PageName, send_keyboard
from project.services.user_state_actions import UserStateAction
from project.services.users import UsersService

logger = getLogger(__name__)


@bot.message_handler()
async def message_handler(msg: Message):
    user = await UsersService.get_user_for_message(msg)
    if msg.text == '/start':
        user.state = UserStateEmpty()
        await send_keyboard(msg, 'Список групп', user, PageName.MAIN)
        await bot.delete_message(msg.chat.id, msg.message_id)
    else:
        await UserStateAction(user.state.type.value).action(user, msg)
    await user.update()


@bot.callback_query_handler(func=lambda call: True)
async def callback_query(callback: CallbackQuery):
    try:
        user = await UsersService.get_user_for_message(callback)

        await CallbackDataAction.main_action(user, callback)

        await user.update()
    finally:
        await bot.answer_callback_query(callback.id, getattr(callback, '__answer__', None))


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
