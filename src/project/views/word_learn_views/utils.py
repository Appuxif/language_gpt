from enum import Enum
from random import choices
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project.db.models.words import UserWordModelManager


class GameLevel(int, Enum):
    """Game Levels
    Несколько типов игры в зависимости от рейтинга изучаемого слова
    """

    def __new__(cls, *args):
        obj = int.__new__(cls, args[0])
        obj._value_, obj.min_rating, obj.info_btn = args
        return obj

    # Если рейтинг слова меньше LEVEL_1, то включается только игра
    # "Выбери перевод слова" - игра первого уровня сложности
    LEVEL_1 = 1, 2.0, '👇 ВЫБЕРИ верный перевод'
    # Если рейтинг слова больше LEVEL_1 и меньше LEVEL_2, то возможны два типа игры,
    # с вероятностью, зависящей от рейтинга слова. Чем больше рейтинг слова, тем реже
    # будет появляться игра первого уровня сложности, но чаще второго уровня - (Введи перевод самостоятельно)
    # На втором уровне сложности все также будут предложены варианты ответа, но теперь их нужно ввести в чат.
    LEVEL_2 = 2, 4.0, '✍️ Найди и ВВЕДИ верный перевод'
    # Если рейтинг слова больше LEVEL_2 и меньше LEVEL_3, то включаются игры второго и
    # третьего уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На третьем уровне сложности не видны варианты ответов. Перевод нужно вспомнить и ввести самостоятельно.
    LEVEL_3 = 3, 8.0, '✍️ ВВЕДИ верный перевод'
    # Если рейтинг слова больше LEVEL_3 и меньше LEVEL_4, то включаются игры третьего и
    # четвертого уровня сложности с вероятностью, зависящей от рейтинга слова.
    # На четвертом уровне сложности не видны варианты ответов. Будет преложено предложение, которое нужно
    # перевести самостоятельно набрав текст в чат.
    LEVEL_4 = 4, 12.0, '✍️ ВВЕДИ верный перевод'
    LAST_LEVEL = 5, 15.0, '✍️ ВВЕДИ верный перевод'  # Фиктивный уровень только для верхней планки рейтинга

    @classmethod
    def get_weights(cls, rating: float) -> list[float]:
        weights: list[float] = [0] * len(GameLevel)
        if rating < GameLevel.LEVEL_1.min_rating:
            weights[0] = 1
        elif GameLevel.LEVEL_1.min_rating <= rating <= GameLevel.LEVEL_2.min_rating:
            weights[1] = rating / GameLevel.LEVEL_2.min_rating
            weights[0] = 1 - weights[1]
        elif GameLevel.LEVEL_2.min_rating <= rating <= GameLevel.LEVEL_3.min_rating:
            weights[2] = rating / GameLevel.LEVEL_3.min_rating
            weights[1] = 1 - weights[2]
        elif GameLevel.LEVEL_3.min_rating <= rating <= GameLevel.LEVEL_4.min_rating:
            weights[3] = rating / GameLevel.LEVEL_4.min_rating
            weights[2] = 1 - weights[3]
        elif GameLevel.LEVEL_4.min_rating <= rating:
            weights[3] = 1
        return weights

    @classmethod
    def choose_game_level(cls, rating: float) -> 'GameLevel':
        weights = GameLevel.get_weights(rating)
        return choices(list(cls), weights, k=1)[0]

    async def add_rating(self, words: 'UserWordModelManager') -> None:
        max_rating = max(GameLevel).min_rating
        await words.update_many([{'$set': {'rating': {'$min': [max_rating, {'$add': ['$rating', 1]}]}}}])

    async def sub_rating(self, words: 'UserWordModelManager') -> None:
        min_rating = 0
        await words.update_many([{'$set': {'rating': {'$max': [min_rating, {'$add': ['$rating', -2]}]}}}])

    @staticmethod
    def compute_percent(rating: float) -> int:
        return min(int(rating / max(GameLevel).min_rating * 100), 100)
