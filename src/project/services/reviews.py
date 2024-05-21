from datetime import datetime

from pydantic import BaseModel
from telebot_views.models import UserModel
from telebot_views.utils import now_utc

from project.db.models.reviews import ReviewModel

REVIEWS_INFO_KEY = 'REVIEWS_INFO_KEY'


class ReviewsInfo(BaseModel):
    is_waiting_for_review: bool
    last_review_at: datetime | None = None


default_reviews_info = ReviewsInfo(is_waiting_for_review=False)


def is_waiting_for_review(user: UserModel) -> bool:
    return get_reviews_info(user).is_waiting_for_review


def set_waiting_for_review(user: UserModel) -> None:
    info = get_reviews_info(user)
    info.is_waiting_for_review = True
    set_reviews_info(user, info)


def set_last_review_at(user: UserModel) -> None:
    info = get_reviews_info(user)
    info.last_review_at = now_utc()
    set_reviews_info(user, info)


def unset_waiting_for_review(user: UserModel) -> None:
    info = get_reviews_info(user)
    info.is_waiting_for_review = False
    set_reviews_info(user, info)


def set_reviews_info(user: UserModel, info: ReviewsInfo) -> None:
    user.constants[REVIEWS_INFO_KEY] = info.dict()


def get_reviews_info(user: UserModel) -> ReviewsInfo:
    result = user.constants.setdefault(REVIEWS_INFO_KEY, default_reviews_info.copy())
    if isinstance(result, ReviewsInfo):
        return result
    if isinstance(result, dict):
        return ReviewsInfo.parse_obj(result)
    raise TypeError(f'Unknown type: {type(result)}')


async def save_reviews_info(user: UserModel) -> None:
    await user.manager().get_collection().update_one(
        {'_id': user.id},
        {
            '$set': {
                f'constants.{REVIEWS_INFO_KEY}.is_waiting_for_review': get_reviews_info(user).is_waiting_for_review,
                f'constants.{REVIEWS_INFO_KEY}.last_review_at': get_reviews_info(user).last_review_at,
            }
        },
    )


async def create_new_review(user: UserModel, text: str) -> ReviewModel:
    unset_waiting_for_review(user)
    set_last_review_at(user)
    review = ReviewModel(text=text, user_oid=user.id, tg_user_id=user.user_id)
    await review.insert()
    return review
