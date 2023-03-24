from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import WordModel


class EditWordMessageSender(BaseMessageSender):
    """Edit Word Message Sender"""

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

        return 'Введи слово:'


class EditWordView(BaseView):
    """Отображение редактирования слова в подборке"""

    view_name = 'EDIT_WORD_VIEW'
    labels = [
        'Редактировать слово',
        'Редактировать слово',
    ]
    delete_income_messages = False
    edit_keyboard = False

    message_sender = EditWordMessageSender

    async def redirect(self) -> BaseView | None:
        user = await self.request.get_user()
        r = self.route_resolver.routes_registry

        if self.view_name not in user.state.callbacks:
            group_id = self.callback.group_id
            word_id = self.callback.word_id
            check_cb = UserStateCb(
                id=self.view_name, view_name=self.view_name, page_num=1, group_id=group_id, word_id=word_id
            )
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        check_cb = user.state.callbacks[self.view_name]
        word: WordModel = await WordModel.manager().find_one(check_cb.word_id)
        word.value = self.request.msg.text.strip()
        await word.update()

        check_cb.word_id = word.id

        await bot.send_message(self.request.msg.chat.id, f'Введено слово: "{word.label}"')
        callback = UserStateCb(view_name=r['WORD_VIEW'].value, group_id=check_cb.group_id, word_id=check_cb.word_id)
        return r['WORD_VIEW'].view(self.request, callback=callback, edit_keyboard=False)
