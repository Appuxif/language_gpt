from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import bot
from project.db.models.words import WordModel


class EditWordTranslationMessageSender(BaseMessageSender):
    """Edit Word Translation Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.params.get('group_id')
        word_id = self.view.callback.params.get('word_id')
        callback = UserStateCb(
            view_name=r['WORD_VIEW'].value,
            params={'group_id': group_id, 'word_id': word_id},
        )
        return [[await self.view.buttons.btn('✖ Отмена', callback)]]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.view_name in user.state.callbacks:
            return ''

        return 'Введи перевод:'


class EditWordTranslationView(BaseView):
    """Отображение редактирования перевода слова в подборке"""

    view_name = 'EDIT_WORD_TRANSLATION_VIEW'
    labels = [
        '✏️ Перевод',
        '✏️ Перевод',
    ]
    delete_income_messages = False
    edit_keyboard = False

    message_sender = EditWordTranslationMessageSender

    async def redirect(self) -> BaseView | None:
        user = await self.request.get_user()
        r = self.route_resolver.routes_registry

        if self.view_name not in user.state.callbacks:
            self.callback.id = self.view_name
            await self.buttons.btn(self.callback.id, self.callback)
            return None

        check_cb = user.state.callbacks[self.view_name]
        word: WordModel = await WordModel.manager().find_one(check_cb.params.get('word_id'))
        word.translation = self.request.msg.text.strip()
        word.translation_voice = b''
        word.examples.clear()
        await word.update()

        msg = await bot.send_message(self.request.msg.chat.id, f'Введено слово: "{word.label}"')
        self.user_states.add_message_to_delete(msg.chat.id, msg.message_id)
        callback = UserStateCb(
            view_name=r['WORD_VIEW'].value,
            params={'group_id': check_cb.params.get('group_id'), 'word_id': check_cb.params.get('word_id')},
        )
        return r['WORD_VIEW'].view(self.request, callback=callback, edit_keyboard=False)
