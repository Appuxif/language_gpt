from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import ParseMode, bot
from project.db.models.words import WordModel


class DeleteWordMessageSender(BaseMessageSender):
    """Delete Word Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.params.get('group_id')
        word_id = self.view.callback.params.get('word_id')
        user = await self.view.request.get_user()

        if self.view.view_name in user.state.callbacks:
            return []

        return [
            [
                await self.view.buttons.btn(
                    'Да',
                    cb(
                        view_name=self.view.view_name,
                        params={'group_id': group_id, 'word_id': word_id},
                    ),
                )
            ],
            [
                await self.view.buttons.btn(
                    '✖ Отмена',
                    cb(
                        view_name=r['WORD_VIEW'].value,
                        params={'group_id': group_id, 'word_id': word_id},
                    ),
                )
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.request.callback and self.view.view_name in user.state.callbacks:
            return ''
        word: WordModel = await WordModel.manager().find_one(self.view.callback.params.get('word_id'))
        return f'Удалить слово {word.label}?'


class DeleteWordView(BaseView):
    """Отображение удаления слова"""

    view_name = 'DELETE_WORD_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Удалить слово?',
        '♻ Удалить слово',
    ]

    message_sender = DeleteWordMessageSender

    async def redirect(self) -> BaseView | None:

        user = await self.request.get_user()
        r = self.route_resolver.routes_registry
        if self.view_name not in user.state.callbacks:
            check_cb = UserStateCb(id=self.view_name, view_name=self.view_name, page_num=1)
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        if self.request.callback is None:
            return None

        word: WordModel = await WordModel.manager().find_one(self.callback.params.get('word_id'))
        await word.delete()
        text = f'Слово *{word.label}* удалено'
        await bot.send_message(self.request.callback.message.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)

        callback = UserStateCb(
            view_name=r['USER_GROUP_VIEW'].value,
            params={'group_id': self.callback.params.get('group_id')},
        )
        return r['USER_GROUP_VIEW'].view(self.request, callback=callback, edit_keyboard=False)
