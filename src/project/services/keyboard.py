from enum import Enum, unique
from random import choices, randint, shuffle

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from project.core.bot import bot
from project.db.models.base import PyObjectId
from project.db.models.callbacks import (
    CallbackDataAddWord,
    CallbackDataDelGroup,
    CallbackDataDelWord,
    CallbackDataGame,
    CallbackDataGroup,
    CallbackDataGroupsPage,
    CallbackDataPage,
    CallbackDataType,
    CallbackDataWord,
    CallbackDataWordsMenu,
    CallbackDataYes,
    CallbackModel,
)
from project.db.models.users import UserModel, UserStateGame
from project.db.models.words import UserWordGroupModel, UserWordModel, WordModel


@unique
class PageName(str, Enum):
    """Page Name"""

    MAIN = 'main'
    GROUP = 'group'
    GROUP_DL = 'group_dl'
    GAME = 'game'
    YES_OR_NO = 'yes_or_no'
    OPTIONS = 'options'
    OPTIONS_SP = 'options_sp'
    OPTIONS_PA = 'options_pa'


async def send_keyboard(
    message: Message,
    text: str,
    user: UserModel,
    page: PageName,
    group_id: PyObjectId | None = None,
    page_num: int = 1,
    edit: bool = False,
):  # pylint: disable=too-many-arguments
    markup = await generate_markup(user, page, group_id, page_num)
    if edit and user.keyboard_id is not None:
        await bot.edit_message_text(
            text,
            message.chat.id,
            user.keyboard_id,
            reply_markup=markup,
        )
    else:
        if user.keyboard_id:
            await bot.delete_message(message.chat.id, user.keyboard_id)
        keyboard = await bot.send_message(message.chat.id, text, reply_markup=markup)
        user.keyboard_id = keyboard.message_id
    await user.update()


async def generate_markup(user: UserModel, page: PageName, group_id: PyObjectId | None = None, page_num: int = 1):
    """Генерирует инлайн клавиатуру"""
    if page == PageName.MAIN:
        builder = MainMenuMarkupBuilder(user, page_num)
        await builder.add_main_rows()
        return builder.get_markup()

    assert group_id

    builder = MarkupBuilder(group_id, page, user, page_num)

    if page == PageName.GROUP:
        await builder.add_group_rows()

    elif page == PageName.GROUP_DL:
        await builder.add_group_dl_rows()

    elif page == PageName.GAME:
        await builder.add_game_rows()

    elif page == PageName.YES_OR_NO:
        await builder.add_yes_or_no_rows()

    elif page == PageName.OPTIONS:
        await builder.add_options_rows()

    elif page == PageName.OPTIONS_SP:
        await builder.add_options_sp_rows()

    elif page == PageName.OPTIONS_PA:
        await builder.add_options_pa_rows()

    return builder.get_markup()


class BaseMarkupBuilder:
    """Base Markup Builder"""

    def __init__(self, user: UserModel, page_num: int):
        self._markup = InlineKeyboardMarkup(row_width=5)
        self._user = user
        self._page_num = page_num

    def get_markup(self):
        return self._markup


class MarkupBuilder(BaseMarkupBuilder):
    """Inline Keyboard Markup Builder"""

    def __init__(self, group_id: PyObjectId, page: str, user: UserModel, page_num: int):
        super().__init__(user, page_num)
        self._group_id = group_id
        self._page = page

    async def add_group_rows(self):
        # Что-то типа пагинатора
        user_words_dict: dict[PyObjectId, UserWordModel] = {
            user_word.word_id: user_word
            for user_word in await UserWordModel.manager()
            .by_user(self._user.id)
            .by_wordgroup(self._group_id)
            .find_all()
        }
        words = WordModel.manager({'group_id': self._group_id})
        words_count = await words.count()
        words_amount = 5

        # Количество страниц вывода слов
        pages = words_count // words_amount
        if words_count / words_amount > pages:
            pages += 1

        # Вывод слов на клавиатуре, если слова вообще есть
        word: WordModel
        words_coro = words.find_all(sort=[('_id', 1)], limit=words_amount, skip=(self._page_num - 1) * words_amount)
        for i, word in enumerate(await words_coro):
            user_word = user_words_dict[word.id]
            user_word.__custom_cache__.__cached_word__ = word
            callback_data = await CallbackModel.get_button_callback(
                CallbackDataWord(group_id=self._group_id, word_id=word.id)
            )
            self._markup.row(InlineKeyboardButton(await user_word.get_label(), callback_data=callback_data))

        # Дополнительные кнопки выбора страниц
        if pages > 1:
            # Эта кнопка информативная, отображает номер текущей страницы
            self._markup.row(
                InlineKeyboardButton(f'Страница {self._page_num} из {pages}', callback_data=CallbackDataType.DUMMY)
            )

            # Кнопки с номерами страниц
            btns = []
            for i in range(pages):
                callback_data = await CallbackModel.get_button_callback(
                    CallbackDataPage(group_id=self._group_id, page_num=i + 1)
                )
                btns.append(InlineKeyboardButton(i + 1, callback_data=callback_data))
            self._markup.add(*btns)

        words_exist = bool(words_count)
        btns = []
        btns_ = []
        callback_data = await CallbackModel.get_button_callback(CallbackDataAddWord(group_id=self._group_id))
        btns.append(InlineKeyboardButton('Добавить слово', callback_data=callback_data))

        # Если нет слов в группе, эти кнопки не добавляются
        if words_exist:
            callback_data = await CallbackModel.get_button_callback(CallbackDataDelWord(group_id=self._group_id))
            btns.append(InlineKeyboardButton('Удалить слово', callback_data=callback_data))
            callback_data = await CallbackModel.get_button_callback(
                CallbackDataWordsMenu(group_id=self._group_id, action=CallbackDataWordsMenu.Action.PAGE, page_num=1)
            )
            btns_.append(InlineKeyboardButton('Учить слова', callback_data=callback_data))

        self._markup.add(*btns)
        self._markup.add(*btns_)
        callback_data = await CallbackModel.get_button_callback(CallbackDataDelGroup(group_id=self._group_id))
        self._markup.add(
            InlineKeyboardButton('Удалить группу', callback_data=callback_data),
            InlineKeyboardButton('Список групп', callback_data=CallbackDataType.LIST_GROUPS),
        )

    async def add_group_dl_rows(self):  # pylint: disable=too-many-locals
        # Что-то типа пагинатора
        user_words = UserWordModel.manager().by_user(self._user.id).by_wordgroup(self._group_id)
        user_words_dict: dict[PyObjectId, UserWordModel] = {
            user_word.word_id: user_word for user_word in await user_words.find_all()
        }
        words = WordModel.manager({'group_id': self._group_id})
        words_count = await words.count()
        words_amount = 5

        # Количество страниц вывода слов
        pages = words_count // words_amount
        if words_count / words_amount > pages:
            pages += 1

        # Вывод слов на клавиатуре, если слова вообще есть
        words_coro = words.find_all(sort=[('_id', 1)], limit=words_amount, skip=(self._page_num - 1) * words_amount)
        for i, word in enumerate(await words_coro):
            user_word = user_words_dict[word.id]
            user_word.__custom_cache__.__cached_word__ = word
            is_chosen = '✗✓'[user_word.is_chosen]
            callback_data = await CallbackModel.get_button_callback(
                CallbackDataWordsMenu(group_id=self._group_id, word_id=word.id, page_num=self._page_num)
            )
            self._markup.row(
                InlineKeyboardButton(f'{is_chosen}{await user_word.get_label()}', callback_data=callback_data)
            )

        # Дополнительные кнопки выбора страниц
        if pages > 1:
            # Эта кнопка информативная, отображает номер текущей страницы
            self._markup.row(
                InlineKeyboardButton(f'Страница {self._page_num} из {pages}', callback_data=CallbackDataType.DUMMY)
            )

            # Кнопки с номерами страниц
            btns = []
            for i in range(pages):
                callback_data = await CallbackModel.get_button_callback(
                    CallbackDataWordsMenu(
                        group_id=self._group_id, page_num=i + 1, action=CallbackDataWordsMenu.Action.PAGE
                    )
                )
                btns.append(InlineKeyboardButton(i + 1, callback_data=callback_data))
            self._markup.add(*btns)

        dl_all = await CallbackModel.get_button_callback(
            CallbackDataWordsMenu(
                group_id=self._group_id, action=CallbackDataWordsMenu.Action.SELECT_ALL, page_num=self._page_num
            )
        )
        dl_no = await CallbackModel.get_button_callback(
            CallbackDataWordsMenu(
                group_id=self._group_id, action=CallbackDataWordsMenu.Action.DESELECT_ALL, page_num=self._page_num
            )
        )
        self._markup.add(
            InlineKeyboardButton('Выбрать все', callback_data=dl_all),
            InlineKeyboardButton('Отменить выбор', callback_data=dl_no),
        )
        dl_lear = await CallbackModel.get_button_callback(
            CallbackDataWordsMenu(
                group_id=self._group_id, page_num=self._page_num, action=CallbackDataWordsMenu.Action.LEARN
            )
        )
        self._markup.add(
            InlineKeyboardButton('Учить', callback_data=dl_lear),
        )  # Нажатие на эту кнопку включает страницу 'game'
        callback_data = await CallbackModel.get_button_callback(CallbackDataGroup(group_id=self._group_id))
        self._markup.row(InlineKeyboardButton('Назад', callback_data=callback_data))

    async def add_game_rows(self) -> None:  # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        # Несколько типов игры в зависимости от рейтинга изучаемого слова.
        # Если рейтинг слова меньше level_1, то включается только игра
        # "Выбери перевод слова" - игра первого уровня сложности
        level_1 = 30
        # Если рейтинг слова больше level_1 и меньше level_2, то возможны два типа игры,
        # с вероятностью, зависящей от рейтинга слова. Чем больше рейтинг слова, тем реже
        # будет появляться игра первого уровня сложности, но чаще второго уровня - (Введи перевод самостоятельно)
        # На втором уровне сложности все также будут предложены варианты ответа, но теперь их нужно ввести в чат.
        level_2 = 100
        # Если рейтинг слова больше level_2 и меньше level_3, то включаются игры второго и
        # третьего уровня сложности с вероятностью, зависящей от рейтинга слова.
        # На третьем уровне сложности не видны варианты ответов. Перевод нужно вспомнить и ввести самостоятельно.
        level_3 = 200
        # Если рейтинг слова больше level_3 и меньше level_4, то включаются игры третьего и
        # четвертого уровня сложности с вероятностью, зависящей от рейтинга слова.
        # На четвертом уровне сложности не видны варианты ответов. Будет преложено предложение, которое нужно
        # перевести самостоятельно набрав текст в чат.
        level_4 = 300
        levels = [1, 2, 3, 4]

        manager = UserWordModel.manager().by_user(self._user.id).by_wordgroup(self._group_id).by_chosen(True)
        words_count = await manager.count()
        user_words: list[UserWordModel] = await manager.find_all(sort=[('rating', 1)], limit=min(words_count // 2, 10))

        # Список слов, участвующих в процессе текущей игры
        shuffle(user_words)
        # Слово, которое надо перевести
        user_word = user_words.pop()
        e_word = await user_word.word()

        weights: list = [0] * len(levels)
        if user_word.rating < level_1:
            weights[0] = 1
        elif level_1 <= user_word.rating <= level_2:
            weights[1] = user_word.rating / level_2
            weights[0] = 1 - weights[1]
        elif level_2 <= user_word.rating <= level_3:
            weights[2] = user_word.rating / level_3
            weights[1] = 1 - weights[1]
        elif level_3 <= user_word.rating <= level_4:
            weights[3] = user_word.rating / level_4
            weights[2] = 1 - weights[1]
        elif level_4 <= user_word.rating:
            weights[3] = 1
        else:
            weights = [1 / len(levels)] * len(levels)

        game_level = choices(levels, weights, k=1)[0]

        # Выбор русского или английского слова выбирается рандомно
        value_or_translation = randint(0, 1)

        # Слово для перевода
        example = None
        callback_data = await CallbackModel.get_button_callback(
            CallbackDataGame(group_id=self._group_id, word_id=e_word.id)
        )
        if game_level == 4 and e_word.examples:
            example = choices(e_word.examples)[0]
            self._markup.row(
                InlineKeyboardButton(
                    (example.value if value_or_translation else example.translation) or '--undefined--',
                    callback_data=callback_data,
                )
            )
        else:
            self._markup.row(
                InlineKeyboardButton(
                    (e_word.value if value_or_translation else e_word.translation) or '--undefined--',
                    callback_data=callback_data,
                )
            )

        # сбор клавиатуры
        if game_level in (1, 2):  # Первый уровень
            info_btn = '-ВЫБЕРИ верный перевод-'
            btns = [
                InlineKeyboardButton(
                    (await word.word()).translation if value_or_translation else (await word.word()).value,
                    callback_data=await CallbackModel.get_button_callback(
                        CallbackDataGame(group_id=self._group_id, word_id=e_word.id, word2_id=word.word_id)
                    ),
                )
                for word in user_words[0:4]
            ]
            btns.append(
                InlineKeyboardButton(
                    e_word.translation if value_or_translation else e_word.value,
                    callback_data=await CallbackModel.get_button_callback(
                        CallbackDataGame(group_id=self._group_id, word_id=e_word.id, word2_id=e_word.id)
                    ),
                )
            )
        else:
            info_btn = '-ВВЕДИ верный перевод-'
            btns = []

        if game_level == 2:
            info_btn = '-Найди и ВВЕДИ верный перевод-'

        self._markup.row(InlineKeyboardButton(info_btn, callback_data=CallbackDataType.DUMMY))

        if btns:
            shuffle(btns)
            for btn in btns:
                self._markup.row(btn)

        self._user.state = UserStateGame(
            group_id=self._group_id,
            word_id=e_word.id,
            value_or_translation=bool(value_or_translation),
            game_level=game_level,
            example_id=example.id if example else None,
        )
        callback_data = await CallbackModel.get_button_callback(
            CallbackDataWordsMenu(group_id=self._group_id, page_num=1, action=CallbackDataWordsMenu.Action.PAGE)
        )
        self._markup.row(InlineKeyboardButton('-Закончить-', callback_data=callback_data))

    async def add_yes_or_no_rows(self) -> None:
        yes = await CallbackModel.get_button_callback(CallbackDataYes(group_id=self._group_id))
        no = await CallbackModel.get_button_callback(CallbackDataGroup(group_id=self._group_id))
        self._markup.add(
            InlineKeyboardButton('Да', callback_data=yes),
            InlineKeyboardButton('Нет', callback_data=no),
        )

    async def add_options_rows(self) -> None:
        self._markup.row(InlineKeyboardButton('Скорость произношения', callback_data='opt_sp'))
        self._markup.row(InlineKeyboardButton('Пауза между словами', callback_data='opt_pa'))
        self._markup.row(InlineKeyboardButton('Назад', callback_data=CallbackDataType.LIST_GROUPS))

    async def add_options_sp_rows(self) -> None:
        self._markup.row(InlineKeyboardButton('100%', callback_data='opt_sp_100'))
        self._markup.row(InlineKeyboardButton('75%', callback_data='opt_sp_75'))
        self._markup.row(InlineKeyboardButton('50%', callback_data='opt_sp_50'))
        self._markup.row(InlineKeyboardButton('Назад', callback_data=CallbackDataType.OPTIONS))

    async def add_options_pa_rows(self) -> None:
        self._markup.row(InlineKeyboardButton('1000ms', callback_data='opt_pa_1000'))
        self._markup.row(InlineKeyboardButton('600ms', callback_data='opt_pa_600'))
        self._markup.row(InlineKeyboardButton('300ms', callback_data='opt_pa_300'))
        self._markup.row(InlineKeyboardButton('100ms', callback_data='opt_pa_100'))
        self._markup.row(InlineKeyboardButton('Назад', callback_data=CallbackDataType.OPTIONS))


class MainMenuMarkupBuilder(BaseMarkupBuilder):
    """Main Menu Markup Builder"""

    async def add_main_rows(self):
        manager = UserWordGroupModel.manager({'user_id': self._user.id})
        groups_amount = 5  # Количество групп на одной странице
        groups: list[UserWordGroupModel] = await manager.find_all(
            sort=[('_id', 1)], skip=(self._page_num - 1) * groups_amount, limit=groups_amount
        )
        # groups_count = await manager.count()

        # Количество страниц вывода групп
        pages = len(groups) // groups_amount
        if len(groups) / groups_amount > pages:
            pages += 1

        # Добавление групп на страницу списка
        for i, group in enumerate(groups):
            callback_data = await CallbackModel.get_button_callback(CallbackDataGroup(group_id=group.group_id))
            self._markup.row(InlineKeyboardButton((await group.wordgroup()).name, callback_data=callback_data))

        # Дополнительные кнопки выбора страниц
        if pages > 1:
            # Эта кнопка информативная, отображает номер текущей страницы
            self._markup.row(
                InlineKeyboardButton(f'Страница {self._page_num} из {pages}', callback_data=CallbackDataType.DUMMY)
            )

            # Кнопки с номерами страниц
            btns = []
            for i in range(pages):
                callback_data = await CallbackModel.get_button_callback(CallbackDataGroupsPage(page_num=i + 1))
                btns.append(InlineKeyboardButton(i + 1, callback_data=callback_data))
            self._markup.add(*btns)

        # Последняя кнопка
        self._markup.row(InlineKeyboardButton('Создать группу', callback_data=CallbackDataType.CREATE_GROUP))
        self._markup.row(InlineKeyboardButton('Настройки', callback_data=CallbackDataType.OPTIONS))
