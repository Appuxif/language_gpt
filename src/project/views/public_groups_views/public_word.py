from typing import Any, Coroutine

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import bot
from project.core.settings import GENERAL
from project.db.models.words import WordModel, WordModelManager
from project.services.audios import concat_audios
from project.services.text_to_speech import add_voices_to_word


class PublicWordMessageSender(BaseMessageSender):
    """Public Word Message Sender"""

    word: WordModel

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.params.get('group_id')
        page_num = self.view.callback.page_num

        self.word: WordModel = await (await self.manager).find_one()

        if self.view.callback.id == 'listen':
            await bot.send_chat_action(self.view.request.message.chat.id, 'upload_audio', timeout=120)
            await add_voices_to_word(self.word, save=True)
            await bot.send_audio(
                self.view.request.message.chat.id,
                concat_audios(self.word.value_voice, self.word.translation_voice),
                performer=f'{GENERAL.SECOND_LANG.value.title()} Learning Bot',
                title=self.word.value,
                caption=self.word.label,
            )

        return [
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
                await self.view.buttons.btn(
                    '🚶 Назад',
                    UserStateCb(
                        view_name=r['PUBLIC_GROUP_VIEW'].value,
                        page_num=page_num,
                        params={'group_id': group_id},
                    ),
                ),
            ],
        ]

    async def get_keyboard_text(self) -> str:
        result = f'Слово "{self.word.label}"'
        if self.word.examples:
            result += '\nПримеры:\n'
            result += '\n'.join(example.label for example in self.word.examples)
        return result

    @property
    def manager(self) -> Coroutine[Any, Any, WordModelManager]:
        async def inner() -> WordModelManager:
            word_id = self.view.callback.params.get('word_id')
            group_id = self.view.callback.params.get('group_id')
            return WordModel.manager().by_wordgroup(group_id).filter({'_id': word_id})

        return inner()


class PublicWordView(BaseView):
    """Отображение слова в публичной подборке"""

    view_name = 'PUBLIC_WORD_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Слово',
        'Слово',
    ]

    message_sender = PublicWordMessageSender
