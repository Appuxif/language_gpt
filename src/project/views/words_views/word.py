import asyncio
from typing import Any, Coroutine

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import bot
from project.core.settings import GENERAL
from project.db.models.words import UserWordModel, UserWordModelManager
from project.services.audios import concat_audios
from project.services.openai_gpt import add_examples_to_word
from project.services.text_to_speech import add_voices_to_word


class WordMessageSender(BaseMessageSender):
    """Word Message Sender"""

    user_word: UserWordModel

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.params.get('group_id')
        page_num = self.view.callback.page_num

        self.user_word: UserWordModel = await (await self.manager).find_one()
        word, group = await asyncio.gather(
            self.user_word.word(),
            self.user_word.wordgroup(),
        )

        if self.view.callback.id == 'listen':
            await asyncio.gather(
                bot.send_chat_action(self.view.request.message.chat.id, 'upload_audio', timeout=120),
                add_voices_to_word(word, save=True),
            )
            await bot.send_audio(
                self.view.request.message.chat.id,
                concat_audios(word.value_voice, word.translation_voice),
                performer=f'{GENERAL.SECOND_LANG.value.title()} Learning Bot',
                title=word.value,
                caption=word.label,
            )

        if self.view.callback.id == 'load_examples':
            await asyncio.gather(
                bot.send_chat_action(self.view.request.message.chat.id, 'typing', timeout=120),
                add_examples_to_word(word, save=True),
            )

        edit_btns = []
        delete_btns = []
        if not group.is_public:
            edit_btns.append(
                [
                    await self.view.buttons.view_btn(r['EDIT_WORD_VIEW'], 1, params=self.view.callback.params),
                    await self.view.buttons.view_btn(
                        r['EDIT_WORD_TRANSLATION_VIEW'], 1, params=self.view.callback.params
                    ),
                ]
            )
            delete_btns.append(
                await self.view.buttons.view_btn(r['DELETE_WORD_VIEW'], 1, params=self.view.callback.params)
            )

        if not word.examples:
            edit_btns.append(
                [
                    await self.view.buttons.btn(
                        '🔍 Загрузить примеры',
                        UserStateCb(
                            id='load_examples',
                            view_name=self.view.view_name,
                            page_num=page_num,
                            params=self.view.callback.params,
                        ),
                    )
                ]
            )

        return [
            *edit_btns,
            [
                await self.view.buttons.btn(
                    '👂 Прослушать',
                    UserStateCb(
                        id='listen',
                        view_name=self.view.view_name,
                        page_num=page_num,
                        params=self.view.callback.params,
                    ),
                ),
            ],
            [
                *delete_btns,
                await self.view.buttons.btn(
                    '🚶 Назад',
                    UserStateCb(
                        view_name=r['USER_GROUP_VIEW'].value,
                        page_num=page_num,
                        params={'group_id': group_id},
                    ),
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
            word_id = self.view.callback.params.get('word_id')
            group_id = self.view.callback.params.get('group_id')
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
