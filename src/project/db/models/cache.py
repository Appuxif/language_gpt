from datetime import datetime
from typing import ClassVar, Type

from pydantic import Field
from telebot_models.models import BaseModelManager, Model
from typing_extensions import Self

from project.utils.timezones import now_utc


class CacheModel(Model):
    """Cache Model"""

    key: str
    data: dict = Field(default_factory=dict)
    valid_until: datetime | None = None

    manager: ClassVar[Type['CacheModelManager']]


class CacheModelManager(BaseModelManager[CacheModel]):
    """Cache Model Manager"""

    collection = 'caches'
    model: Type[CacheModel] = CacheModel

    def by_key(self, key: str) -> Self:
        return self.filter({'key': key})

    def is_valid(self) -> Self:
        return self.filter({'valid_until': {'$gt': now_utc()}})
