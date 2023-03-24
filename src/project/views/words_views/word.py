from telebot.types import InlineKeyboardButton

from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import UserWordModel


class WordMessageSender(BaseMessageSender):
    """Word Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.group_id
        word_id = self.view.callback.word_id
        page_num = self.view.callback.page_num
        return [
            [
                await self.view.buttons.view_btn(r['EDIT_WORD_VIEW'], 1, group_id=group_id, word_id=word_id),
                await self.view.buttons.view_btn(
                    r['EDIT_WORD_TRANSLATION_VIEW'], 1, group_id=group_id, word_id=word_id
                ),
            ],
            [
                await self.view.buttons.view_btn(r['DELETE_WORD_VIEW'], 1, group_id=group_id, word_id=word_id),
                await self.view.buttons.btn(
                    'Назад', UserStateCb(view_name=r['USER_GROUP_VIEW'].value, group_id=group_id, page_num=page_num)
                ),
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        word_id = self.view.callback.word_id
        group_id = self.view.callback.group_id
        user_words = UserWordModel.manager().by_user(user.id).by_wordgroup(group_id).by_word(word_id)
        user_word: UserWordModel = await user_words.find_one()
        return f'Слово {await user_word.get_label()}'


class WordView(BaseView):
    """Отображение слова в подборке"""

    view_name = 'WORD_VIEW'
    labels = [
        'Слово',
        'Слово',
    ]

    message_sender = WordMessageSender
