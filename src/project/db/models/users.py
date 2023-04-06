from datetime import datetime
from typing import ClassVar, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from project.db.models.base import Model, ModelConfig, ModelManager, PyObjectId
from project.utils.timezones import now_utc


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


class WithUser(Model):
    """With User Mixin"""

    user_id: PyObjectId = Field(default_factory=PyObjectId)
