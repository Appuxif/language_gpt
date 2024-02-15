from typing import Any, Callable, ClassVar, Coroutine, Type

from pydantic import Field, validator
from telebot_models.models import BaseModelManager, Model, PyObjectId
from telebot_views.models import UserModelManager

from project.db.models.users import WithUser
from project.views.word_learn_views.utils import GameLevel


class WordGroupModel(Model):
    """Word Group Model"""

    name: str = ''
    is_public: bool = False
    stars: int = 0  # TODO: implement starring public groups

    manager: ClassVar[Type['WordGroupModelManager']]


class WordGroupModelManager(BaseModelManager[WordGroupModel]):
    """Word Group Model Manager"""

    collection = 'word_groups'
    model = WordGroupModel


class WithGroup(Model):
    """With Group Mixin"""

    group_id: PyObjectId = Field(default_factory=PyObjectId)


class WithUserGroup(WithUser):
    """With Group Mixin"""

    group_id: PyObjectId = Field(default_factory=PyObjectId)


class WordExample(Model):
    """Word Example"""

    value: str = ''
    translation: str = ''
    value_voice: bytes = b''
    translation_voice: bytes = b''

    @validator('value', 'translation')
    def validate_strings(cls, value: str) -> str:
        value = value.strip()
        value = value[:1].title() + value[1:]
        return value

    @property
    def label(self) -> str:
        return f'{self.value} - {self.translation}'

    def __hash__(self):
        return hash((self.value, self.translation))

    class Config:
        """Config"""

        validate_assignment = True


@WordGroupModelManager.relation_map('group_id', 'id')
class WordModel(WordExample, WithGroup):
    """Word Model"""

    examples: list[WordExample] = Field(default_factory=list)
    is_active: bool = False
    manager: ClassVar[Type['WordModelManager']]

    def add_examples(self, examples: list[dict[str, str]]):
        self.examples = list(set(self.examples + [WordExample.parse_obj(item) for item in examples]))


class WordModelManager(BaseModelManager[WordModel]):
    """Word Model Manager"""

    collection = 'words'
    model = WordModel

    by_wordgroup: Callable[[PyObjectId | list[PyObjectId]], 'WordModelManager']


@WordGroupModelManager.relation_map('group_id', 'id')
@UserModelManager.relation_map('user_id', 'id')
class UserWordGroupModel(WithUserGroup, Model):
    """User Word Group Model"""

    manager: ClassVar[Type['UserWordGroupModelManager']]

    async def get_label(self) -> str:
        group = await self.wordgroup()
        words = UserWordModelManager().by_wordgroup(self.group_id).by_user(self.user_id)
        pipelines = [
            {'$match': words.document_filter},
            {'$group': {'_id': None, 'rating': {'$sum': '$rating'}, 'count': {'$sum': 1}}},
        ]
        aggregation = await UserWordModelManager.get_collection().aggregate(pipelines).to_list(None)
        rating = 0
        if aggregation:
            rating = GameLevel.compute_percent(aggregation[0]['rating'] / aggregation[0]['count'])
        result = f'{group.name} [{rating}%]'
        if group.is_public:
            result += ' [PUB]'
        return result

    wordgroup: ClassVar[Callable[[], Coroutine[Any, Any, WordGroupModel]]]


class UserWordGroupModelManager(BaseModelManager[UserWordGroupModel]):
    """User Word Group Model Manager"""

    collection = 'user_word_groups'
    model = UserWordGroupModel

    by_user: ClassVar[Callable[[PyObjectId | list[PyObjectId]], 'UserWordGroupModelManager']]
    by_wordgroup: ClassVar[Callable[[PyObjectId | list[PyObjectId]], 'UserWordGroupModelManager']]


@UserModelManager.relation_map('user_id', 'id')
@WordGroupModelManager.relation_map('group_id', 'id')
@WordModelManager.relation_map('word_id', 'id')
@UserWordGroupModelManager.relation_map('group_id', 'group_id')
class UserWordModel(WithUserGroup, Model):
    """User Word Model"""

    word_id: PyObjectId = Field(default_factory=PyObjectId)
    is_chosen: bool = False
    rating: float = 0.0
    is_active: bool = False

    manager: ClassVar[Type['UserWordModelManager']]

    async def get_label(self) -> str:
        word = await self.word()
        rating = GameLevel.compute_percent(self.rating)
        return f'{word.label} [{rating}%]'

    word: ClassVar[Callable[[], Coroutine[Any, Any, WordModel]]]
    wordgroup: ClassVar[Callable[[], Coroutine[Any, Any, WordGroupModel]]]


class UserWordModelManager(BaseModelManager[UserWordModel]):
    """User Word Model Manager"""

    collection = 'user_words'
    model = UserWordModel

    def __init__(self, document_filter: dict | None = None):
        super().__init__(document_filter)
        self.document_filter.setdefault('is_active', True)

    def by_chosen(self, is_chosen: bool):
        return self.filter({'is_chosen': is_chosen})

    def by_active(self, is_active: bool | list[bool]):
        if isinstance(is_active, list):
            return self.filter({'is_active': {'$in': is_active}})
        return self.filter({'is_active': is_active})

    async def find_all(self, *args, prefetch_words: bool = False, **kwargs) -> list[UserWordModel]:
        result: list[UserWordModel] = await super().find_all(*args, **kwargs)
        if prefetch_words:
            words = await WordModel.manager({'_id': {'$in': [obj.word_id for obj in result]}}).find_all()
            words_dict = {word.id: word for word in words}
            for obj in result:
                obj.__custom_cache__.__cached_word__ = words_dict[obj.word_id]
        return result

    by_user: ClassVar[Callable[[PyObjectId | list[PyObjectId]], 'UserWordModelManager']]
    by_wordgroup: Callable[[PyObjectId | list[PyObjectId]], 'UserWordModelManager']
    by_word: Callable[[PyObjectId | list[PyObjectId]], 'UserWordModelManager']
