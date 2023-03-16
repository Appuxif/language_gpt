import asyncio
from enum import Enum

from telebot.types import Message

from project.core.bot import bot
from project.db.models.users import (
    UserModel,
    UserStateAddTranslation,
    UserStateAddWord,
    UserStateCreateGroup,
    UserStateEmpty,
    UserStateGame,
    UserStateType,
)
from project.db.models.words import UserWordGroupModel, UserWordModel, WordGroupModel, WordModel
from project.services.keyboard import PageName, send_keyboard


async def noop(user: UserModel, msg: Message) -> None:
    # pylint: disable=unused-argument
    pass


async def empty(user: UserModel, msg: Message) -> None:
    assert isinstance(user.state, UserStateEmpty)

    await bot.delete_message(msg.chat.id, msg.message_id)


async def create_group(user: UserModel, msg: Message) -> None:
    assert isinstance(user.state, UserStateCreateGroup)

    if len(msg.text) > 20:
        await bot.send_message(msg.chat.id, 'Не больше двадцати символов в названии группы')
        return

    group = WordGroupModel(name=msg.text, is_public=False)
    await group.insert()

    user_group = UserWordGroupModel(user_id=user.id, group_id=group.id)
    await user_group.insert()
    await send_keyboard(msg, msg.text, user, PageName.GROUP, group.id)
    user.state = UserStateEmpty()


async def add_word(user: UserModel, msg: Message) -> None:
    assert isinstance(user.state, UserStateAddWord)

    word = WordModel(group_id=user.state.group_id, value=msg.text.strip())
    await word.insert()

    user_word = UserWordModel(user_id=user.id, word_id=word.id, group_id=user.state.group_id)
    await user_word.insert()

    await bot.send_message(msg.chat.id, 'Введи перевод:')
    user.state = UserStateAddTranslation(group_id=user.state.group_id, word_id=word.id)


async def add_translation(user: UserModel, msg: Message) -> None:
    assert isinstance(user.state, UserStateAddTranslation)

    group = await WordGroupModel.manager().find_one(user.state.group_id)
    word = await WordModel.manager().find_one(user.state.word_id)
    word.translation = msg.text.strip()
    await word.update()

    await bot.send_message(msg.chat.id, f'Введено слово: "{word.label}"')
    await send_keyboard(msg, f'Группа "{group.name}"', user, PageName.GROUP, user.state.group_id)
    user.state = UserStateEmpty()


async def game(user: UserModel, msg: Message) -> None:
    assert isinstance(user.state, UserStateGame)
    user_words = UserWordModel.manager().by_user(user.id).by_wordgroup(user.state.group_id)
    user_word: UserWordModel = await user_words.by_word(user.state.word_id).find_one()
    word = await user_word.word()

    msg_text = msg.text.lower().strip()
    example = next((example for example in word.examples if example.id == user.state.example_id), None)
    if user.state.game_level == 4 and example:
        word_to_translate = example.translation if user.state.value_or_translation else example.value
    else:
        word_to_translate = word.translation if user.state.value_or_translation else word.value

    if msg_text == word_to_translate.lower():
        await bot.send_message(msg.chat.id, f'Ответ верный: {msg.text}')
        await asyncio.sleep(0.3)
        if user.state.game_level == 2:
            user_word.rating += 25
        else:
            user_word.rating += 50
        await send_keyboard(msg, 'Переведи слово', user, PageName.GAME, user.state.group_id)
    else:
        await bot.send_message(msg.chat.id, f'Ответ неверный: {msg.text}\nПравильно: {word_to_translate}')
        if user.state.game_level == 2:
            user_word.rating -= 25
        else:
            user_word.rating -= 50

    await user_word.update()
    await bot.delete_message(msg.chat.id, msg.message_id)


class UserStateAction(str, Enum):
    """User State Action"""

    def __new__(cls, *args) -> 'UserStateAction':
        obj = str.__new__(cls, args[0])
        obj._value_, obj.action = args
        return obj

    EMPTY = UserStateType.EMPTY.value, empty
    CREATE_GROUP = UserStateType.CREATE_GROUP.value, create_group
    ADD_WORD = UserStateType.ADD_WORD.value, add_word
    DEL_WORD = UserStateType.DEL_WORD.value, noop
    ADD_TRANSLATION = UserStateType.ADD_TRANSLATION.value, add_translation
    GAME = UserStateType.GAME.value, game


status: Enum
for status in UserStateAction:
    UserStateType(status.value)
for status in UserStateType:
    UserStateAction(status.value)
