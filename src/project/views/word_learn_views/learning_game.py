import asyncio
from random import choices, randint, shuffle

from telebot.types import InlineKeyboardButton

from project.core.bot import bot
from project.core.views.base import BaseMessageSender, BaseView, Route, UserStatesManager
from project.db.models.users import UserModel, UserStateCb
from project.db.models.words import UserWordModel, UserWordModelManager
from project.views.word_learn_views.utils import GameLevel


class LearningGameButtonsBuilder:
    """Learning Game Buttons Builder"""

    def __init__(self, view: BaseView, word: UserWordModel):
        self.view = view
        self.word = word
        self.game_level = GameLevel.choose_game_level(word.rating)
        self.value_or_translation = bool(randint(0, 1))

    @property
    def r(self) -> dict[str, Route]:
        return self.view.route_resolver.routes_registry

    async def get_chosen_word_btn(self) -> InlineKeyboardButton:
        chosen_word_cb = UserStateCb(
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

        chosen_word = await self.word.word()
        word_example = chosen_word
        if self.game_level == GameLevel.LEVEL_4 and chosen_word.examples:
            word_example = choices(chosen_word.examples)[0]
            chosen_word_cb.params['example_id'] = word_example.id

        chosen_word_btn = await self.view.buttons.btn(
            (word_example.value if self.value_or_translation else word_example.translation) or '--undefined--',
            chosen_word_cb,
        )
        return chosen_word_btn

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
        if self.game_level == 4 and example_id:
            _word_example = next((example for example in word_example.examples if example.id == example_id), None)
            word_example = _word_example or word_example
        word_to_translate = word_example.translation if value_or_translation else word_example.value

        msg_text = self.view.request.msg.text.lower().strip()
        tasks = []
        if msg_text == word_to_translate.lower():
            answer_text = f'✅ {self.view.request.msg.text}'
            tasks.append(asyncio.sleep(0.3))
            tasks.append(self.game_level.add_rating(words))
        else:
            answer_text = f'🚫 {self.view.request.msg.text}\nПравильный ответ: {word_to_translate}'
            tasks.append(self.game_level.sub_rating(words))
        tasks.append(bot.send_message(self.view.request.msg.chat.id, answer_text))
        await asyncio.gather(*tasks)


class LearningGameMessageSender(BaseMessageSender):
    """Learning Game Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:

        user = await self.view.request.get_user()
        await LearningGameAnswerProcessor(self.view, user).run()

        if self.view.callbacks.callback_answer:
            return []

        manager = UserWordModel.manager().by_user(user.id).by_wordgroup(self.view.callback.group_id).by_chosen(True)
        user_words: list[UserWordModel] = await manager.find_all(sort=[('rating', 1)], limit=10, prefetch_words=True)

        shuffle(user_words)
        user_word = user_words.pop()

        builder = LearningGameButtonsBuilder(self.view, user_word)

        view_btn_cb = UserStateCb(
            id=self.view.view_name,
            view_name=self.view.view_name,
            group_id=self.view.callback.group_id,
            word_id=user_word.word_id,
        )
        await self.view.buttons.btn(self.view.view_name, view_btn_cb)
        exit_cb = UserStateCb(
            view_name=builder.r['LEARN_WORDS_VIEW'].value,
            group_id=self.view.callback.group_id,
            view_params={'edit_keyboard': False},
        )
        return [
            [await builder.get_chosen_word_btn()],
            [await self.view.buttons.btn('---', UserStateCb(view_name=builder.r['DUMMY'].value))],
            *(await builder.get_buttons_to_choose(user_words)),
            [await self.view.buttons.btn('🤚 Завершить', exit_cb)],
        ]

    async def get_keyboard_text(self) -> str:
        if self.view.callbacks.callback_answer:
            return ''
        user = await self.view.request.get_user()
        chosen_word_callback = user.state.callbacks['chosen_word']
        game_level = GameLevel(chosen_word_callback.params['game_level'])
        return game_level.info_btn


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
