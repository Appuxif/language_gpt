from enum import Enum

from bson import ObjectId
from telebot.types import CallbackQuery

from project.core.bot import bot
from project.db.models.callbacks import (
    CallbackData,
    CallbackDataAddWord,
    CallbackDataDelGroup,
    CallbackDataDelWord,
    CallbackDataDummy,
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
from project.db.models.users import (
    UserModel,
    UserStateAddWord,
    UserStateCreateGroup,
    UserStateDelWord,
    UserStateEmpty,
    UserStateGame,
)
from project.db.models.words import UserWordModel, WordGroupModel
from project.services.keyboard import PageName, send_keyboard


async def noop(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataDummy)
    assert isinstance(user, UserModel)
    assert isinstance(callback, CallbackQuery)


async def create_group(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataDummy)
    # Если нажата кнопка "Создать группу"
    # Меняется статус юзера. Бот ждет сообщения с названием группы
    user.state = UserStateCreateGroup()
    await bot.send_message(callback.message.chat.id, 'Введи название группы:')


async def list_groups(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataDummy)
    # Если нажата кнопка "Список групп"
    user.state = UserStateEmpty()
    await send_keyboard(callback.message, 'Список твоих групп', user, PageName.MAIN, edit=True)


async def group_action(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataGroup)
    # Если нажата кнопка конкретной группы в списке групп
    user.state = UserStateEmpty()
    group = await WordGroupModel.manager().find_one(callback_data.group_id)
    await send_keyboard(
        callback.message, f'Группа "{group.name}"', user, PageName.GROUP, callback_data.group_id, edit=True
    )


async def add_word(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataAddWord)
    # Если нажата кнопка "Добавить слово" в группе
    user.state = UserStateAddWord(group_id=callback_data.group_id)
    await bot.send_message(callback.message.chat.id, 'Введи слово:')
    # Следующий шаг в listener!


async def delete_word(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataDelWord)
    # Если нажата кнопка "Удалить слово" в группе
    user.state = UserStateDelWord(group_id=callback_data.group_id)
    await bot.send_message(callback.message.chat.id, 'Нажми на слово, которое надо удалить')
    # Следующий шаг ниже


async def word_action(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataWord)
    if not isinstance(user.state, UserStateDelWord):
        return
    # Если выбрано слово в режиме удаления слов из группы
    user.state = UserStateEmpty()

    group = await WordGroupModel.manager().find_one(callback_data.group_id)
    user_words = UserWordModel.manager().by_user(user.id).by_wordgroup(callback_data.group_id)
    user_word = await user_words.by_word(callback_data.word_id).find_one()
    word = await user_word.word()

    await bot.send_message(callback.message.chat.id, f'Слово "{await user_word.get_label()}" удалено')
    await word.delete()
    await send_keyboard(callback.message, f'Группа "{group.name}"', user, PageName.GROUP, callback_data.group_id)


async def delete_group(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataDelGroup)
    # Если нажата кнопка "Удалить группу" в группе
    user.state = UserStateEmpty()
    group = await WordGroupModel.manager().find_one(callback_data.group_id)
    await send_keyboard(
        callback.message, f'Точно удалить группу "{group.name}"?', user, PageName.YES_OR_NO, callback_data.group_id
    )


async def yes_action(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataYes)
    # Если нажата кнопка "Удалить группу" в группе
    user.state = UserStateEmpty()
    group = await WordGroupModel.manager().find_one(callback_data.group_id)
    await group.delete()
    await bot.send_message(callback.message.chat.id, f'Группа "{group.name}" удалена')
    await send_keyboard(callback.message, 'Список твоих групп', user, PageName.MAIN, callback_data.group_id)


async def page_action(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataPage)
    if not isinstance(user.state, UserStateEmpty):
        return
    # Если нажата кнопка со страницей конкретной группы
    user.state = UserStateEmpty()
    group = await WordGroupModel.manager().find_one(callback_data.group_id)
    await send_keyboard(
        callback.message,
        f'Группа "{group.name}"',
        user,
        PageName.GROUP,
        callback_data.group_id,
        callback_data.page_num,
        edit=True,
    )


async def groups_page(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataGroupsPage)
    # Если нажата кнопка со страницей конкретной группы
    user.state = UserStateEmpty()
    await send_keyboard(callback.message, 'Список твоих групп', user, PageName.MAIN, page_num=callback_data.page_num)


async def words_menu(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataWordsMenu)

    page_num = 1
    words = UserWordModel.manager().by_user(user.id).by_wordgroup(callback_data.group_id)

    if callback_data.action == callback_data.Action.SELECT_ALL:
        # Если нажата кнопка "Выбрать все" - выбираются все слова
        await words.update_many({'$set': {'is_chosen': True}})
    elif callback_data.action == callback_data.Action.DESELECT_ALL:
        # Если нажата кнопка "Отменить выбор" - выбор слов сбрасывается
        await words.update_many({'$set': {'is_chosen': False}})
    elif callback_data.action == callback_data.Action.PAGE:
        # Если нажата кнопка со страницей при выборе слов - переключение страницы в этом меню
        page_num = callback_data.page_num
    elif callback_data.action == callback_data.Action.LEARN:
        # Если нажата кнопка "Учить" - включается игра для запоминания слов в виде теста.
        words_count = await words.by_chosen(True).count()
        if words_count:
            await send_keyboard(callback.message, 'Переведи слово', user, PageName.GAME, callback_data.group_id)
        else:
            setattr(callback, '__answer__', 'Не выбрано ни одного слова')
        return
    else:
        # Если нажата кнопка со словом при выборе слов - постановка или снятие выбора
        await words.by_word(callback_data.word_id).update_many([{'$set': {'is_chosen': {'$not': '$is_chosen'}}}])

    words_total = await words.count()
    words_chosen = await words.by_chosen(True).count()
    await send_keyboard(
        callback.message,
        f'Выбрано {words_chosen} слов из {words_total}',
        user,
        PageName.GROUP_DL,
        callback_data.group_id,
        page_num,
        edit=True,
    )


async def game_action(user: UserModel, callback: CallbackQuery, callback_data: CallbackData) -> None:
    assert isinstance(callback_data, CallbackDataGame)
    assert isinstance(user.state, UserStateGame)
    # Если нажаты кнопки из меню игры
    words = UserWordModel.manager().by_user(user.id).by_wordgroup(callback_data.group_id)
    words = words.by_word([callback_data.word_id, callback_data.word2_id])

    if user.state.game_level not in (1, 2):
        setattr(callback, '__answer__', 'Сейчас нужно ВВЕСТИ ответ в чат')
    # Если второй и третий уровень игры
    elif callback_data.word2_id is None:
        user_word = await words.by_word(callback_data.word_id).find_one()
        word = await user_word.word()
        setattr(callback, '__answer__', f'{word.label}')
        user_word.rating -= 25
        await user_word.update()
    # Это только для первого уровня игры
    elif callback_data.word_id == callback_data.word2_id:
        # Ответ верный
        setattr(callback, '__answer__', 'Ответ верный')
        await send_keyboard(callback.message, 'Переведи слово', user, PageName.GAME, callback_data.group_id)
        await words.update_many([{'$set': {'rating': {'$add': ['$rating', 10]}}}])
    elif callback_data.word_id != callback_data.word2_id:
        # ответ неверный
        setattr(callback, '__answer__', 'Ответ неверный')
        await words.update_many([{'$set': {'rating': {'$add': ['$rating', -10]}}}])
    # Второй и третий уровни игры обрабатываются в листенере


class CallbackDataAction(str, Enum):
    """Callback Data Action"""

    def __new__(cls, *args) -> 'CallbackDataAction':
        obj = str.__new__(cls, args[0])
        obj._value_, obj.action = args
        return obj

    DUMMY = CallbackDataType.DUMMY.value, noop
    CREATE_GROUP = CallbackDataType.CREATE_GROUP.value, create_group
    LIST_GROUPS = CallbackDataType.LIST_GROUPS.value, list_groups
    OPTIONS = CallbackDataType.OPTIONS.value, noop
    GROUP = CallbackDataType.GROUP.value, group_action
    ADD_WORD = CallbackDataType.ADD_WORD.value, add_word
    DELETE_WORD = CallbackDataType.DELETE_WORD.value, delete_word
    WORD = CallbackDataType.WORD.value, word_action
    DELETE_GROUP = CallbackDataType.DELETE_GROUP.value, delete_group
    YES = CallbackDataType.YES.value, yes_action
    PAGE = CallbackDataType.PAGE.value, page_action
    GROUPS_PAGE = CallbackDataType.GROUPS_PAGE.value, groups_page
    WORDS_MENU = CallbackDataType.WORDS_MENU.value, words_menu
    GAME = CallbackDataType.GAME.value, game_action

    @classmethod
    async def main_action(cls, user: UserModel, callback: CallbackQuery):
        callback_data = CallbackDataDummy(type=CallbackDataType.DUMMY)

        try:
            action = CallbackDataAction(callback.data).action
        except ValueError:
            instance = await CallbackModel.manager().find_one(ObjectId(callback.data))
            action = CallbackDataAction(instance.data.type.value).action
            callback_data = instance.data

        await action(user, callback, callback_data)


data: Enum
for data in CallbackDataAction:
    CallbackDataType(data.value)
for data in CallbackDataType:
    CallbackDataAction(data.value)
