from datetime import datetime
from logging import getLogger
from typing import ClassVar, Type

from pydantic import Field
from telebot_models.models import BaseModelManager, Model, PyObjectId
from telebot_views.utils import now_utc

logger = getLogger(__name__)


class ReviewModel(Model):
    """Review Model"""

    text: str
    user_oid: PyObjectId
    tg_user_id: int
    created_at: datetime = Field(default_factory=now_utc)

    manager: ClassVar[Type['ReviewModelManager']]


class ReviewModelManager(BaseModelManager[ReviewModel]):

    collection = 'reviews'
    model = ReviewModel


async def init_reviews_collection() -> None:
    logger.info('Init reviews collection...')
    col = ReviewModelManager.get_collection()
    await col.create_index('user_oid')
    await col.create_index('tg_user_id')
    logger.info('Init reviews collection done')
