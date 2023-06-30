from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.db.models.words import UserWordModel, WordModel


class AddWordMessageSender(BaseMessageSender):
    """Add Word Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry

        callback = UserStateCb(
            view_name=r['USER_GROUP_VIEW'].value,
            params={'group_id': self.view.callback.params.get('group_id')},
        )
        return [[await self.view.buttons.btn('✖ Отмена', callback)]]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.view_name in user.state.callbacks:
            return ''

        return 'Введи слово (English):'


class AddWordView(BaseView):
    """Отображение добавления слова в подборку"""

    view_name = 'ADD_WORD_VIEW'
    labels = [
        '📝 Добавить слово',
        '📝 Добавить слово',
    ]
    delete_income_messages = False
    edit_keyboard = False

    message_sender = AddWordMessageSender

    async def redirect(self) -> BaseView | None:
        user = await self.request.get_user()
        r = self.route_resolver.routes_registry

        if self.view_name not in user.state.callbacks:
            group_id = self.callback.params.get('group_id')
            word_id = self.callback.params.get('word_id')
            check_cb = UserStateCb(
                id=self.view_name,
                view_name=self.view_name,
                page_num=1,
                params={'group_id': group_id, 'word_id': word_id},
            )
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        check_cb = user.state.callbacks[self.view_name]
        word = WordModel(group_id=check_cb.params.get('group_id'), value=self.request.msg.text.strip())
        await word.insert()
        user_word = UserWordModel(user_id=user.id, word_id=word.id, group_id=check_cb.params.get('group_id'))
        await user_word.insert()

        check_cb.params['word_id'] = word.id
        check_cb.view_name = r['ADD_WORD_TRANSLATION_VIEW'].value

        return r['ADD_WORD_TRANSLATION_VIEW'].view(self.request, callback=check_cb)
