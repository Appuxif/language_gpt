from typing import Any, Coroutine

from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import UserWordModel, UserWordModelManager
from project.services.audios import concat_audios
from project.services.text_to_speech import add_voices_to_word


class WordMessageSender(BaseMessageSender):
    """Word Message Sender"""

    user_word: UserWordModel

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.group_id
        word_id = self.view.callback.word_id
        page_num = self.view.callback.page_num

        self.user_word: UserWordModel = await (await self.manager).find_one()

        if self.view.callback.id == 'listen':
            await bot.send_chat_action(self.view.request.message.chat.id, 'upload_audio', timeout=120)
            word = await self.user_word.word()
            await add_voices_to_word(word, save=True)
            await bot.send_audio(
                self.view.request.message.chat.id,
                concat_audios(word.value_voice, word.translation_voice),
                performer='English Learning Bot',
                title=word.value,
                caption=word.label,
            )

        return [
            [
                await self.view.buttons.view_btn(r['EDIT_WORD_VIEW'], 1, group_id=group_id, word_id=word_id),
                await self.view.buttons.view_btn(
                    r['EDIT_WORD_TRANSLATION_VIEW'], 1, group_id=group_id, word_id=word_id
                ),
            ],
            [
                await self.view.buttons.btn(
                    'Прослушать',
                    UserStateCb(
                        id='listen',
                        view_name=self.view.view_name,
                        group_id=group_id,
                        page_num=page_num,
                        word_id=word_id,
                    ),
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
        word = await self.user_word.word()
        result = f'Слово "{await self.user_word.get_label()}"'
        if word.examples:
            result += '\nПримеры:\n'
            result += '\n'.join(example.label for example in word.examples)
        return result

    @property
    def manager(self) -> Coroutine[Any, Any, UserWordModelManager]:
        async def inner() -> UserWordModelManager:
            user = await self.view.request.get_user()
            word_id = self.view.callback.word_id
            group_id = self.view.callback.group_id
            return UserWordModel.manager().by_user(user.id).by_wordgroup(group_id).by_word(word_id)

        return inner()


class WordView(BaseView):
    """Отображение слова в подборке"""

    view_name = 'WORD_VIEW'
    labels = [
        'Слово',
        'Слово',
    ]

    message_sender = WordMessageSender
