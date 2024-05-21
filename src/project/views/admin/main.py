from datetime import timedelta

from bson import ObjectId
from telebot.types import InlineKeyboardButton
from telebot_views import bot
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb, get_user_model
from telebot_views.models.cache import with_cache
from telebot_views.utils import now_utc

from project.db.models.words import WordGroupModel, WordModel


class MainAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry

        error_cb = UserStateCb(id='call_error', view_name=self.view.view_name)
        words_cb = UserStateCb(id='words_count', view_name=self.view.view_name)

        if self.view.callback.id == error_cb.id:
            raise Exception('Debug exception')

        if self.view.callback.id == words_cb.id:
            text = await count_words()
            await bot.bot.send_message(self.view.request.message.chat.id, text['text'])

        return [
            [await self.view.buttons.btn('Вызвать ошибку', error_cb)],
            [await self.view.buttons.view_btn(r['USERS_ADMIN_VIEW_PROXY'], 0)],
            [await self.view.buttons.btn('Слова', words_cb)],
            [await self.view.buttons.view_btn(r['REVIEWS_ADMIN_VIEW_PROXY'], 0)],
            [await self.view.buttons.view_btn(r['MAIN_VIEW'], 0)],
        ]

    async def get_keyboard_text(self) -> str:
        return self.view.labels[0]


class MainAdminView(BaseView):

    view_name = 'MAIN_ADMIN_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        '⚙️ Админ',
        '⚙️ Админ',
    ]

    message_sender = MainAdminMessageSender


@with_cache('admin_count_users', 120)
async def count_users() -> dict[str, str]:
    text = ''
    total_users = await get_user_model().manager().count()
    text += f'Всего пользователей: {total_users}\n'

    week_users = (
        await get_user_model()
        .manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=7))}})
        .count()
    )
    text += f'За прошедшую неделю: {week_users}\n'

    month_users = (
        await get_user_model()
        .manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=30))}})
        .count()
    )
    text += f'За прошедший месяц: {month_users}\n'

    active_now = (
        await get_user_model()
        .manager()
        .filter({'state.created_at': {'$gte': now_utc() - timedelta(seconds=30)}})
        .count()
    )
    text += f'Сейчас активны: {active_now}\n'

    active_today = (
        await get_user_model()
        .manager()
        .filter({'state.created_at': {'$gte': now_utc() - timedelta(seconds=3600 * 24)}})
        .count()
    )
    text += f'Сегодня активны: {active_today}\n'
    return {'text': text}


@with_cache('admin_count_words', 120)
async def count_words() -> dict[str, str]:
    text = ''

    total_words = await WordModel.manager().count()
    text += f'Всего слов: {total_words}\n'

    week_words = (
        await WordModel.manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=7))}})
        .count()
    )
    text += f'За прошедшую неделю: {week_words}\n'

    month_words = (
        await WordModel.manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=30))}})
        .count()
    )
    text += f'За прошедший месяц: {month_words}\n'

    text += '\n'

    total_groups = await WordGroupModel.manager().count()
    text += f'Всего групп: {total_groups}\n'

    week_group = (
        await WordGroupModel.manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=7))}})
        .count()
    )
    text += f'За прошедшую неделю: {week_group}\n'

    month_group = (
        await WordGroupModel.manager()
        .filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=30))}})
        .count()
    )
    text += f'За прошедший месяц: {month_group}\n'

    return {'text': text}
