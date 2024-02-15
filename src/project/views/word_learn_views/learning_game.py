import asyncio
import re
from enum import Enum
from functools import cache
from logging import getLogger
from random import choices, randint, shuffle
from typing import Coroutine

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView, Route, UserStatesManager
from telebot_views.models import UserModel, UserStateCb

from project.core.bot import bot
from project.db.models.words import UserWordGroupModel, UserWordModel, UserWordModelManager, WordExample
from project.services.openai_gpt import add_examples_to_word, whether_translation_is_correct
from project.services.text_to_speech import add_voices_to_word, add_voices_to_word_example
from project.views.word_learn_views.utils import MIN_WORDS_TO_START_GAME, GameLevel

logger = getLogger(__name__)


class LearningGameButtonsBuilder:
    """Learning Game Buttons Builder"""

    class DataType(str, Enum):
        """Типы данных для отправки пользователю"""

        TEXT = 'text'
        AUDIO = 'audio'

    def __init__(self, view: BaseView, word: UserWordModel):
        self.view = view
        self.word = word
        self.game_level = GameLevel.choose_game_level(word.rating)
        self.chosen_word_cb = UserStateCb(
            id='chosen_word',
            view_name=self.r['DUMMY'].value,
            params={
                'group_id': self.view.callback.params.get('group_id'),
                'word_id': self.word.word_id,
                'game_level': self.game_level.value,
                'example_id': None,
                'value_or_translation': bool(randint(0, 1)),
            },
        )

    @property
    def value_or_translation(self) -> bool:
        return bool(self.chosen_word_cb.params.get('value_or_translation'))

    @value_or_translation.setter
    def value_or_translation(self, value: bool) -> None:
        self.chosen_word_cb.params['value_or_translation'] = value

    @property
    def r(self) -> dict[str, Route]:
        return self.view.route_resolver.routes_registry

    async def define_game_level(self):
        self.game_level = GameLevel.choose_game_level(self.word.rating)
        chosen_word = await self.word.word()

        if self.game_level in (GameLevel.LEVEL_5, GameLevel.LEVEL_6):
            if not chosen_word.examples:
                asyncio.create_task(add_examples_to_word(chosen_word))
                self.game_level = GameLevel.LEVEL_4

        if self.game_level in (GameLevel.LEVEL_6,):
            for word_example in chosen_word.examples:
                if not word_example.value_voice or not word_example.translation_voice:
                    asyncio.create_task(add_voices_to_word_example(chosen_word, word_example))
                    self.game_level = GameLevel.LEVEL_5

        if self.game_level in (GameLevel.LEVEL_4,):
            if not chosen_word.value_voice or not chosen_word.translation_voice:
                asyncio.create_task(add_voices_to_word(chosen_word))
                self.game_level = GameLevel.LEVEL_3

        self.chosen_word_cb.params['game_level'] = self.game_level.value

    async def get_chosen_word(self) -> tuple[WordExample, DataType]:
        data_type = self.DataType.TEXT
        chosen_word = await self.word.word()
        word_example = chosen_word

        if self.game_level in (GameLevel.LEVEL_4,):
            await add_voices_to_word(word_example)
            data_type = self.DataType.AUDIO
            self.value_or_translation = True

        if self.game_level in (GameLevel.LEVEL_5, GameLevel.LEVEL_6):
            if not chosen_word.examples:
                await add_examples_to_word(chosen_word)
            word_example = choices(chosen_word.examples)[0]
            self.chosen_word_cb.params['example_id'] = word_example.id

        if self.game_level in (GameLevel.LEVEL_6,):
            await add_voices_to_word_example(chosen_word, word_example)
            data_type = self.DataType.AUDIO
            self.value_or_translation = True

        return word_example, data_type

    async def get_buttons_to_choose(self, user_words: list[UserWordModel]) -> list[InlineKeyboardButton]:
        group_id = self.view.callback.params.get('group_id')
        chosen_word = await self.word.word()
        buttons = []

        if self.game_level in (GameLevel.LEVEL_1, GameLevel.LEVEL_2):
            buttons = [
                await self.view.buttons.btn(
                    (await word.word()).translation if self.value_or_translation else (await word.word()).value,
                    UserStateCb(view_name=self.view.view_name, params={'group_id': group_id, 'word_id': word.word_id}),
                )
                for word in user_words[:4]
            ]
            buttons.append(
                await self.view.buttons.btn(
                    chosen_word.translation if self.value_or_translation else chosen_word.value,
                    UserStateCb(
                        view_name=self.view.view_name, params={'group_id': group_id, 'word_id': chosen_word.id}
                    ),
                )
            )

            shuffle(buttons)
            buttons = ([btn] for btn in buttons)
        return buttons


class LearningGameAnswerProcessor:
    """Learning Game Answer Processor"""

    def __init__(self, view: BaseView, user: UserModel):
        self.view = view
        self.user = user

    @property
    def chosen_word_callback(self) -> UserStateCb:
        return self.user.state.callbacks['chosen_word']

    @property
    def game_level(self) -> GameLevel:
        return GameLevel(self.chosen_word_callback.params['game_level'])

    @property
    def words(self) -> UserWordModelManager:
        return UserWordModel.manager().by_user(self.user.id).by_wordgroup(self.view.callback.params.get('group_id'))

    async def run(self):
        if 'chosen_word' in self.user.state.callbacks:
            if self.view.request.callback:
                await self.process_answer_callback()
            elif self.view.request.msg:
                await self.process_answer_text()

    async def process_answer_callback(self) -> None:

        if self.game_level != GameLevel.LEVEL_1:
            self.view.callbacks.set_callback_answer('✍️ Сейчас нужно ВВЕСТИ ответ в чат')
            return

        words = self.words.by_word(
            [self.view.callback.params.get('word_id'), self.chosen_word_callback.params.get('word_id')]
        )

        if self.view.callback.params.get('word_id') == self.chosen_word_callback.params.get('word_id'):
            await self.game_level.add_rating(words)
        else:
            self.view.callbacks.set_callback_answer('🚫 Ответ неверный')
            await self.game_level.sub_rating(words)

    async def process_answer_text(self) -> None:
        @cache
        def clean_word(_word: str):
            _word = _word.lower().strip()
            _word = re.sub(r'[^\w\d ]', '', _word)
            return ' '.join(_word.split())

        if self.game_level == GameLevel.LEVEL_1:
            self.view.callbacks.set_callback_answer('☝️ Сейчас нужно ВЫБРАТЬ вариант ответа')
            msg = await bot.send_message(self.view.request.msg.chat.id, self.view.callbacks.callback_answer)
            self.view.user_states.add_message_to_delete(self.view.request.msg.chat.id, msg.message_id)
            return

        example_id = self.chosen_word_callback.params.get('example_id')
        value_or_translation = self.chosen_word_callback.params.get('value_or_translation')
        words = self.words.by_word(self.chosen_word_callback.params.get('word_id'))

        user_word: UserWordModel = await words.find_one()
        word_example = await user_word.word()
        if self.game_level in (GameLevel.LEVEL_5, GameLevel.LEVEL_6) and example_id:
            word_example = (
                next((example for example in word_example.examples if example.id == example_id), None) or word_example
            )

        if self.game_level in (GameLevel.LEVEL_4, GameLevel.LEVEL_6):
            word_to_translate = word_example.value if value_or_translation else word_example.translation
        else:
            word_to_translate = word_example.translation if value_or_translation else word_example.value

        answer_text = self.view.request.msg.text
        first_decision = clean_word(answer_text) == clean_word(word_to_translate)
        decision = first_decision
        if self.game_level in (GameLevel.LEVEL_5,) and example_id and decision is False:
            try:
                decision, answer_text = await whether_translation_is_correct(
                    await user_word.word(),
                    word_example,
                    answer_text,
                )
            except ValueError:
                logger.exception('whether_translation_is_correct error')

        tasks = []
        if decision is True:
            answer_text = answer_text or self.view.request.msg.text
            answer_text = f'✅ {answer_text} [{GameLevel.compute_percent(user_word.rating)}%]'
            if first_decision is False:
                answer_text += f'\nОтвет принимается. Но более точно будет: {word_to_translate}'
            tasks.append(asyncio.sleep(0.5))
            tasks.append(self.game_level.add_rating(words))
            only_next = True
        else:
            answer_text = f'🚫 {answer_text}\nПравильный ответ: {word_to_translate}'
            self.view.callbacks.set_callback_answer(answer_text)
            tasks.append(self.game_level.sub_rating(words))
            only_next = False

        tasks.append(bot.send_message(self.view.request.msg.chat.id, answer_text))
        results = await asyncio.gather(*tasks)

        self.view.user_states.add_message_to_delete(
            self.view.request.msg.chat.id,
            results[-1].message_id,
            only_next=only_next,
        )


class LearningGameMessageSender(BaseMessageSender):
    """Learning Game Message Sender"""

    builder: LearningGameButtonsBuilder | None = None

    @property
    def manager(self) -> Coroutine[None, None, UserWordModel.manager]:
        async def _manager():
            user = await self.view.request.get_user()
            return (
                UserWordModel.manager()
                .by_user(user.id)
                .by_wordgroup(self.view.callback.params.get('group_id'))
                .by_chosen(True)
            )

        return _manager()

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:

        user = await self.view.request.get_user()
        await LearningGameAnswerProcessor(self.view, user).run()

        if self.view.callbacks.callback_answer:
            return []

        user_words: list[UserWordModel] = await (await self.manager).find_all(
            sort=[('rating', 1)], limit=10, prefetch_words=True
        )

        if len(user_words) < MIN_WORDS_TO_START_GAME:
            self.view.callbacks.set_callback_answer('Нужно выбрать хотя бы пять слов')
            return []

        shuffle(user_words)
        user_word = user_words.pop()

        self.builder = LearningGameButtonsBuilder(self.view, user_word)
        await self.builder.define_game_level()

        view_btn_cb = UserStateCb(
            id=self.view.view_name,
            view_name=self.view.view_name,
            params={'group_id': self.view.callback.params.get('group_id'), 'word_id': user_word.word_id},
        )
        await self.view.buttons.btn(self.view.view_name, view_btn_cb)
        exit_cb = UserStateCb(
            view_name=self.builder.r['LEARN_WORDS_VIEW'].value,
            view_params={'edit_keyboard': False},
            params={'group_id': self.view.callback.params.get('group_id')},
        )
        return [
            *(await self.builder.get_buttons_to_choose(user_words)),
            [await self.view.buttons.btn('🤚 Завершить', exit_cb)],
        ]

    async def get_keyboard_text(self) -> str:
        if self.view.callbacks.callback_answer:
            return ''

        user = await self.view.request.get_user()
        group = await UserWordGroupModel.manager().by_wordgroup(self.builder.word.group_id).by_user(user.id).find_one()

        chosen_word, data_type = await self.builder.get_chosen_word()
        chosen_word_value = (
            chosen_word.value if self.builder.value_or_translation else chosen_word.translation
        ) or '--undefined--'

        await self.view.buttons.btn(chosen_word_value, self.builder.chosen_word_cb)
        chosen_word_callback = user.state.callbacks['chosen_word']
        game_level = GameLevel(chosen_word_callback.params['game_level'])

        text = await group.get_label() + '\n\n'
        text += game_level.info_btn + '\n\n'

        if data_type == self.builder.DataType.TEXT:
            text += chosen_word_value

        elif data_type == self.builder.DataType.AUDIO:
            msg = await bot.send_audio(
                self.view.request.message.chat.id,
                chosen_word.value_voice,
                performer='English Learning Bot',
                title=await group.get_label(),
            )
            self.view.user_states.add_message_to_delete(self.view.request.message.chat.id, msg.message_id)

        return text


class LearningGameUserStatesManager(UserStatesManager):
    """Learning Game User States Manager"""

    async def set(self) -> None:
        if self.view.callbacks.callback_answer:
            return
        await super().set()


class LearningGameView(BaseView):
    """Отображение игры по изучению слов"""

    view_name = 'LEARNING_GAME_VIEW'
    labels = [
        '🎓 Учить',
        'К изучению слов',
    ]
    edit_keyboard = False

    message_sender = LearningGameMessageSender
    user_states_manager = LearningGameUserStatesManager

    async def dispatch(self) -> Route:
        user = await self.request.get_user()
        if not self._callback.view_name:
            self._callback = user.state.callbacks[self.view_name]

        return await super().dispatch()
