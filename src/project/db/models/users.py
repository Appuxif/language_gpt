from datetime import datetime
from enum import Enum
from typing import ClassVar, Type
from uuid import uuid4

from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo.results import UpdateResult

from project.db.models.base import Model, ModelConfig, ModelManager, PyObjectId
from project.utils.timezones import now_utc


class UserStateType(str, Enum):
    """User State Type"""

    EMPTY = ''
    CREATE_GROUP = 'create_group'
    ADD_WORD = 'add_word'
    DEL_WORD = 'del_word'
    ADD_TRANSLATION = 'add_translation'
    GAME = 'game'


class UserStateEmpty(ModelConfig, BaseModel):
    """User State Empty"""

    type: UserStateType = Field(UserStateType.EMPTY, const=True)


class UserStateCreateGroup(ModelConfig, BaseModel):
    """User State Create Group"""

    type: UserStateType = Field(UserStateType.CREATE_GROUP, const=True)


class UserStateAddWord(ModelConfig, BaseModel):
    """User State Add"""

    type: UserStateType = Field(UserStateType.ADD_WORD, const=True)
    group_id: PyObjectId = Field(default_factory=ObjectId)


class UserStateAddTranslation(ModelConfig, BaseModel):
    """User State Add Translation"""

    type: UserStateType = Field(UserStateType.ADD_TRANSLATION, const=True)
    group_id: PyObjectId = Field(default_factory=PyObjectId)
    word_id: PyObjectId = Field(default_factory=PyObjectId)


class UserStateDelWord(ModelConfig, BaseModel):
    """User State Del"""

    type: UserStateType = Field(UserStateType.DEL_WORD, const=True)
    group_id: PyObjectId = Field(default_factory=ObjectId)


class UserStateGame(ModelConfig, BaseModel):
    """User State Game"""

    type: UserStateType = Field(UserStateType.GAME, const=True)
    group_id: PyObjectId = Field(default_factory=PyObjectId)
    word_id: PyObjectId = Field(default_factory=PyObjectId)
    example_id: PyObjectId | None = Field(None)
    value_or_translation: bool = False
    game_level: int = 1


class UserStateCb(ModelConfig, BaseModel):
    """User State Callback"""

    id: str = Field(default_factory=lambda: uuid4().hex)
    view_name: str = ''
    page_num: int | None = None
    group_id: PyObjectId | None = None
    word_id: PyObjectId | None = None
    created_at: datetime | None = Field(default_factory=now_utc)
    view_params: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)


class UserMainState(ModelConfig, BaseModel):
    """User Main State"""

    view_name: str = ''
    callbacks: dict[str, UserStateCb] = Field(default_factory=dict)


UserState = (
    UserStateEmpty
    | UserStateCreateGroup
    | UserStateAddWord
    | UserStateAddTranslation
    | UserStateDelWord
    | UserStateGame
    | UserMainState
)


class UserModel(Model):
    """User Model"""

    user_id: int = ''
    username: str = ''
    first_name: str = ''
    last_name: str = ''
    state: UserMainState = Field(default_factory=UserMainState)
    keyboard_id: int | None = None

    manager: ClassVar[Type['UserModelManager']]


class UserModelManager(ModelManager[UserModel]):
    """User Model Manager"""

    collection = 'users'
    model = UserModel

    async def set_state(self, state: UserState) -> UpdateResult:
        return self.get_collection().update_one(self.document_filter, {'$set': {'state': state.dict()}})


class WithUser(Model):
    """With User Mixin"""

    user_id: PyObjectId = Field(default_factory=PyObjectId)
