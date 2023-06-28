from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import bot
from project.db.models.words import UserWordModel, WordModel


class AddWordTranslationMessageSender(BaseMessageSender):
    """Add Word Translation Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        callback = UserStateCb(
            view_name=r['USER_GROUP_VIEW'].value,
            params={'group_id': self.view.callback.params.get('group_id')},
        )
        return [[await self.view.buttons.btn('Отмена', callback)]]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.view_name in user.state.callbacks:
            return ''

        return 'Введи перевод:'


class AddWordTranslationView(BaseView):
    """Отображение добавления перевода слова в подборку"""

    view_name = 'ADD_WORD_TRANSLATION_VIEW'
    labels = [
        'Добавить перевод',
        'Добавить перевод',
    ]
    delete_income_messages = False
    edit_keyboard = False

    message_sender = AddWordTranslationMessageSender

    async def redirect(self) -> BaseView | None:
        user = await self.request.get_user()
        r = self.route_resolver.routes_registry

        if self.view_name not in user.state.callbacks:
            check_cb = user.state.callbacks['ADD_WORD_VIEW']
            check_cb.id = self.view_name
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        check_cb = user.state.callbacks[self.view_name]
        user_words = (
            UserWordModel.manager()
            .by_user(user.id)
            .by_word(check_cb.params.get('word_id'))
            .by_wordgroup(check_cb.params.get('group_id'))
        )
        user_word: UserWordModel = await user_words.by_active([True, False]).find_one()
        user_word.is_active = True
        await user_word.update()
        word: WordModel = await user_word.word()
        word.translation = self.request.msg.text.strip()
        word.is_active = True
        await word.update()

        await bot.send_message(self.request.msg.chat.id, f'Введено слово: "{word.label}"')
        callback = UserStateCb(
            view_name=r['USER_GROUP_VIEW'].value,
            params={'group_id': check_cb.params.get('group_id')},
        )
        return r['USER_GROUP_VIEW'].view(self.request, callback=callback, edit_keyboard=False)
