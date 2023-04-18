import asyncio
from functools import partial
from typing import Any, Coroutine

from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import UserWordGroupModel, UserWordModel, UserWordModelManager, WordModel
from project.services.audios import concat_audios
from project.services.text_to_speech import add_voices_to_word


class LearnWordsMessageSender(BaseMessageSender):
    """Learn Words Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.group_id
        page_num = self.view.callback.page_num or 1
        cb = partial(UserStateCb, view_name=self.view.view_name, group_id=group_id, page_num=page_num)

        manager = await self.manager

        if self.view.callback.id == 'select_all':
            await manager.update_many({'$set': {'is_chosen': True}})

        elif self.view.callback.id == 'deselect_all':
            await manager.update_many({'$set': {'is_chosen': False}})

        elif self.view.callback.id == 'listen':
            await self.send_audio_to_listen()

        elif self.view.callback.word_id is not None:
            await manager.by_word(self.view.callback.word_id).update_many(
                [{'$set': {'is_chosen': {'$not': '$is_chosen'}}}]
            )

        user_words: list[UserWordModel] = await self.view.paginator.paginate(manager, page_num, prefetch_words=True)

        # Вывод слов на клавиатуре, если слова вообще есть
        words_btns = []
        for user_word in user_words:
            is_chosen = '✗✓'[user_word.is_chosen]
            text = f'{is_chosen}{await user_word.get_label()}'
            words_btns.append([await self.view.buttons.btn(text, cb(word_id=user_word.word_id))])

        return [
            *words_btns,
            *(await self.view.paginator.get_pagination(await manager.count(), page_num, group_id=group_id)),
            [
                await self.view.buttons.btn('Выбрать все', cb(id='select_all')),
                await self.view.buttons.btn('Отменить выбор', cb(id='deselect_all')),
            ],
            [
                await self.view.buttons.btn('Прослушать', cb(id='listen')),
                await self.view.buttons.view_btn(r['LEARNING_GAME_VIEW'], 0, group_id=group_id),
            ],
            [
                await self.view.buttons.view_btn(r['USER_GROUP_VIEW'], 1, group_id=group_id),
            ],
        ]

    async def send_audio_to_listen(self):
        user_words_ids = await (await self.manager).by_chosen(True).find_all(['word_id'])

        if not user_words_ids:
            self.view.callbacks.set_callback_answer('Нужно выбрать хотя бы одно слово.')
            return

        if len(user_words_ids) > 10:
            self.view.callbacks.set_callback_answer('Выбрано слишком много слов. Можно максимум 10 слов за раз.')
            return

        await bot.send_chat_action(self.view.request.message.chat.id, 'upload_audio', timeout=120)

        words_audios = (
            await WordModel.manager()
            .filter({'_id': {'$in': [word_id.word_id for word_id in user_words_ids]}})
            .find_all()
        )
        await asyncio.gather(*(add_voices_to_word(word, save=True) for word in words_audios))
        result_audio = concat_audios(
            *(item for word in words_audios for item in (word.value_voice, word.translation_voice))
        )
        group = await (await self.user_group).wordgroup()
        caption = f'Words: {len(words_audios)}\n'
        for word in words_audios:
            caption += f'{word.label}\n'
        await bot.send_audio(
            self.view.request.message.chat.id,
            result_audio,
            performer='English Learning Bot',
            title=group.name,
            caption=caption,
        )

    async def get_keyboard_text(self) -> str:
        words_total = await (await self.manager).count()
        words_chosen = await (await self.manager).by_chosen(True).count()
        user_group = await self.user_group
        text = f'Выбрано {words_chosen} слов из {words_total}'
        return f'{self.view.labels[0]}. Подборка {await user_group.get_label()}.\n{text}'

    @property
    def user_group(self) -> Coroutine[Any, Any, UserWordGroupModel]:
        async def inner() -> UserWordGroupModel:
            user = await self.view.request.get_user()
            groups = UserWordGroupModel.manager().by_user(user.id).by_wordgroup(self.view.callback.group_id)
            group: UserWordGroupModel = await groups.find_one()
            return group

        return inner()

    @property
    def manager(self) -> Coroutine[Any, Any, UserWordModelManager]:
        async def inner() -> UserWordModelManager:
            user = await self.view.request.get_user()
            group_id = self.view.callback.group_id
            return UserWordModel.manager().by_user(user.id).by_wordgroup(group_id)

        return inner()


class LearnWordsView(BaseView):
    """Отображение страницы начала изучения слов"""

    view_name = 'LEARN_WORDS_VIEW'
    labels = [
        'Учить слова',
        'К изучению слов',
    ]

    message_sender = LearnWordsMessageSender
