import asyncio
import re
from logging import getLogger
from random import choices, randint, shuffle
from typing import Coroutine

from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView, Route, UserStatesManager
from project.db.models.users import UserModel, UserStateCb
from project.db.models.words import UserWordGroupModel, UserWordModel, UserWordModelManager
from project.services.openai_gpt import add_examples_to_word, whether_translation_is_correct
from project.views.word_learn_views.utils import GameLevel

logger = getLogger(__name__)


class LearningGameButtonsBuilder:
    """Learning Game Buttons Builder"""

    def __init__(self, view: BaseView, word: UserWordModel):
        self.view = view
        self.word = word
        self.game_level = GameLevel.choose_game_level(word.rating)
        self.value_or_translation = bool(randint(0, 1))
        self.chosen_word_cb = UserStateCb(
            id='chosen_word',
            view_name=self.r['DUMMY'].value,
            group_id=self.view.callback.group_id,
            word_id=self.word.word_id,
            params={
                'game_level': self.game_level.value,
                'example_id': None,
                'value_or_translation': self.value_or_translation,
            },
        )

    @property
    def r(self) -> dict[str, Route]:
        return self.view.route_resolver.routes_registry

    async def get_chosen_word(self) -> str:
        chosen_word = await self.word.word()
        word_example = chosen_word
        if self.game_level in (GameLevel.LEVEL_4,):
            if not chosen_word.examples:
                await add_examples_to_word(chosen_word)
            if chosen_word.examples:
                word_example = choices(chosen_word.examples)[0]
                self.chosen_word_cb.params['example_id'] = word_example.id
        return (word_example.value if self.value_or_translation else word_example.translation) or '--undefined--'

    async def get_buttons_to_choose(self, user_words: list[UserWordModel]) -> list[InlineKeyboardButton]:
        group_id = self.view.callback.group_id
        chosen_word = await self.word.word()
        buttons = []
        if self.game_level in (GameLevel.LEVEL_1, GameLevel.LEVEL_2):
            buttons = [
                await self.view.buttons.btn(
                    (await word.word()).translation if self.value_or_translation else (await word.word()).value,
                    UserStateCb(view_name=self.view.view_name, group_id=group_id, word_id=word.word_id),
                )
                for word in user_words[:4]
            ]
            buttons.append(
                await self.view.buttons.btn(
                    chosen_word.translation if self.value_or_translation else chosen_word.value,
                    UserStateCb(view_name=self.view.view_name, group_id=group_id, word_id=chosen_word.id),
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
        return UserWordModel.manager().by_user(self.user.id).by_wordgroup(self.view.callback.group_id)

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

        words = self.words.by_word([self.view.callback.word_id, self.chosen_word_callback.word_id])

        if self.view.callback.word_id == self.chosen_word_callback.word_id:
            await self.game_level.add_rating(words)
        else:
            self.view.callbacks.set_callback_answer('🚫 Ответ неверный')
            await self.game_level.sub_rating(words)

    async def process_answer_text(self) -> None:
        def clean_word(_word: str):
            _word = _word.lower().strip()
            _word = re.sub(r'[^\w\d ]', '', _word)
            return ' '.join(_word.split())

        if self.game_level == GameLevel.LEVEL_1:
            self.view.callbacks.set_callback_answer('☝️ Сейчас нужно ВЫБРАТЬ вариант ответа')
            await bot.send_message(self.view.request.msg.chat.id, self.view.callbacks.callback_answer)
            return

        self.view.delete_income_messages = False

        example_id = self.chosen_word_callback.params.get('example_id')
        value_or_translation = self.chosen_word_callback.params.get('value_or_translation')
        words = self.words.by_word(self.chosen_word_callback.word_id)

        user_word: UserWordModel = await words.find_one()
        word_example = await user_word.word()
        if self.game_level in (GameLevel.LEVEL_4,) and example_id:
            _word_example = next((example for example in word_example.examples if example.id == example_id), None)
            word_example = _word_example or word_example
        word_to_translate = word_example.translation if value_or_translation else word_example.value

        first_decision = clean_word(self.view.request.msg.text) == clean_word(word_to_translate)
        decision = first_decision
        answer_text = self.view.request.msg.text
        if self.game_level in (GameLevel.LEVEL_4,) and example_id and decision is False:
            try:
                decision, answer_text = await whether_translation_is_correct(
                    await user_word.word(),
                    word_example,
                    self.view.request.msg.text,
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
        else:
            answer_text = f'🚫 {answer_text}\nПравильный ответ: {word_to_translate}'
            self.view.callbacks.set_callback_answer(answer_text)
            tasks.append(self.game_level.sub_rating(words))

        tasks.append(bot.send_message(self.view.request.msg.chat.id, answer_text))
        await asyncio.gather(*tasks)


class LearningGameMessageSender(BaseMessageSender):
    """Learning Game Message Sender"""

    builder: LearningGameButtonsBuilder | None = None

    @property
    def manager(self) -> Coroutine[None, None, UserWordModel.manager]:
        async def _manager():
            user = await self.view.request.get_user()
            return UserWordModel.manager().by_user(user.id).by_wordgroup(self.view.callback.group_id).by_chosen(True)

        return _manager()

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:

        user = await self.view.request.get_user()
        await LearningGameAnswerProcessor(self.view, user).run()

        if self.view.callbacks.callback_answer:
            return []

        user_words: list[UserWordModel] = await (await self.manager).find_all(
            sort=[('rating', 1)], limit=10, prefetch_words=True
        )

        shuffle(user_words)
        user_word = user_words.pop()

        self.builder = LearningGameButtonsBuilder(self.view, user_word)

        view_btn_cb = UserStateCb(
            id=self.view.view_name,
            view_name=self.view.view_name,
            group_id=self.view.callback.group_id,
            word_id=user_word.word_id,
        )
        await self.view.buttons.btn(self.view.view_name, view_btn_cb)
        exit_cb = UserStateCb(
            view_name=self.builder.r['LEARN_WORDS_VIEW'].value,
            group_id=self.view.callback.group_id,
            view_params={'edit_keyboard': False},
        )
        return [
            *(await self.builder.get_buttons_to_choose(user_words)),
            [await self.view.buttons.btn('🤚 Завершить', exit_cb)],
        ]

    async def get_keyboard_text(self) -> str:
        if self.view.callbacks.callback_answer:
            return ''

        user = await self.view.request.get_user()
        chosen_word = await self.builder.get_chosen_word()
        group = await UserWordGroupModel.manager().by_wordgroup(self.builder.word.group_id).by_user(user.id).find_one()
        await self.view.buttons.btn(chosen_word, self.builder.chosen_word_cb)
        chosen_word_callback = user.state.callbacks['chosen_word']
        game_level = GameLevel(chosen_word_callback.params['game_level'])
        text = await group.get_label() + '\n\n'
        text += game_level.info_btn + '\n\n'
        text += chosen_word

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
        'Учить',
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
