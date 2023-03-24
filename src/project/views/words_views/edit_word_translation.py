from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import WordModel


class EditWordTranslationMessageSender(BaseMessageSender):
    """Edit Word Translation Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.group_id
        word_id = self.view.callback.word_id
        callback = UserStateCb(view_name=r['WORD_VIEW'].value, group_id=group_id, word_id=word_id)
        return [[await self.view.buttons.btn('Отмена', callback)]]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.view_name in user.state.callbacks:
            return ''

        return 'Введи перевод:'


class EditWordTranslationView(BaseView):
    """Отображение редактирования перевода слова в подборке"""

    view_name = 'EDIT_WORD_TRANSLATION_VIEW'
    labels = [
        'Редактировать перевод',
        'Редактировать перевод',
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
        word: WordModel = await WordModel.manager().find_one(check_cb.word_id)
        word.translation = self.request.msg.text.strip()
        await word.update()

        await bot.send_message(self.request.msg.chat.id, f'Введено слово: "{word.label}"')
        callback = UserStateCb(view_name=r['WORD_VIEW'].value, group_id=check_cb.group_id, word_id=check_cb.word_id)
        return r['WORD_VIEW'].view(self.request, callback=callback, edit_keyboard=False)
