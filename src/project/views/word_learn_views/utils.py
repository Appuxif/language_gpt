from enum import Enum
from random import choices
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project.db.models.words import UserWordModelManager


MAX_RATING = 15.0


class GameLevel(int, Enum):
    """Game Levels
    Несколько типов игры в зависимости от рейтинга изучаемого слова
    """

    def __new__(cls, *args):
        obj = int.__new__(cls, args[0])
        obj._value_, obj.info_btn = args
        obj.index = obj._value_ - 1
        return obj

    # Если рейтинг слова меньше LEVEL_1, то включается только игра первого уровня
    # "Выбери перевод слова" - игра первого уровня сложности
    LEVEL_1 = 1, '👇 ВЫБЕРИ верный перевод'
    # Если рейтинг слова больше LEVEL_1 и меньше LEVEL_2, то возможны два типа игры,
    # с вероятностью, зависящей от рейтинга слова. Чем больше рейтинг слова, тем реже
    # будет появляться игра первого уровня сложности, но чаще второго уровня - (Введи перевод самостоятельно)
    # На втором уровне сложности все также будут предложены варианты ответа, но теперь их нужно ввести в чат.
    LEVEL_2 = 2, '✍️ Найди и ВВЕДИ верный перевод'
    # Если рейтинг слова больше LEVEL_2 и меньше LEVEL_3, то включаются игры второго и
    # третьего уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На третьем уровне сложности не видны варианты ответов. Перевод нужно вспомнить и ввести самостоятельно.
    LEVEL_3 = 3, '✍️ ВВЕДИ верный перевод'
    # Если рейтинг слова больше LEVEL_3 и меньше LEVEL_4, то включаются игры третьего и
    # четвертого уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На четвертом уровне сложности не видны варианты ответов. Будет отправлено аудио-озвучка слова, которое нужно
    # прослушать и ввести правильный вариант
    LEVEL_4 = 4, '✍️ Прослушай аудио и введи верное слово'
    # Если рейтинг слова больше LEVEL_4 и меньше LEVEL_5, то включаются игры четвертого и
    # пятого уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На пятом уровне сложности не видны варианты ответов. Будет преложено предложение, которое нужно
    # перевести самостоятельно набрав текст в чат.
    LEVEL_5 = 5, '✍️ ВВЕДИ верный перевод предложения'
    # Если рейтинг слова больше LEVEL_5 и меньше LEVEL_6, то включаются игры пятого и
    # шестого уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На шестом уровне сложности не видны варианты ответов. Будет отправлено аудио-озвучка предложения, которое нужно
    # прослушать и ввести правильный вариант
    LEVEL_6 = 6, '✍️ Прослушай аудио и введи верное предложение'
    LAST_LEVEL = 7, '✍️ ВВЕДИ верный перевод'  # Фиктивный уровень только для верхней планки рейтинга

    @classmethod
    def get_weights(cls, rating: float) -> list[float]:
        weights: list[float] = [0.0] * len(GameLevel)
        if rating < 2.0:
            weights[GameLevel.LEVEL_1.index] = 0.66
            weights[GameLevel.LEVEL_4.index] = 0.34
        elif 2.0 <= rating <= 4.0:
            weights[GameLevel.LEVEL_2.index] = 0.66
            weights[GameLevel.LEVEL_4.index] = 0.34
        elif 4.0 <= rating <= 6.0:
            weights[GameLevel.LEVEL_3.index] = 0.66
            weights[GameLevel.LEVEL_4.index] = 0.34
        elif 6.0 <= rating <= 9.0:
            weights[GameLevel.LEVEL_3.index] = 0.34
            weights[GameLevel.LEVEL_4.index] = 0.66
        elif 9.0 <= rating <= 12.0:
            weights[GameLevel.LEVEL_5.index] = 1
        elif 12.0 <= rating:
            weights[GameLevel.LEVEL_6.index] = 0.40
            weights[GameLevel.LEVEL_5.index] = 0.40
            weights[GameLevel.LEVEL_3.index] = 0.20
        return weights

    @classmethod
    def choose_game_level(cls, rating: float) -> 'GameLevel':
        weights = GameLevel.get_weights(rating)
        return choices(list(cls), weights, k=1)[0]

    async def add_rating(self, words: 'UserWordModelManager') -> None:
        await words.update_many([{'$set': {'rating': {'$min': [MAX_RATING, {'$add': ['$rating', 1]}]}}}])

    async def sub_rating(self, words: 'UserWordModelManager') -> None:
        await words.update_many([{'$set': {'rating': {'$max': [0, {'$add': ['$rating', -2]}]}}}])

    @staticmethod
    def compute_percent(rating: float) -> int:
        return min(int(rating / MAX_RATING * 100), 100)
