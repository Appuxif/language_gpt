from typing import Optional

from asyncio_functools.lru_cache import async_lru_cache
from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserModel, get_user_model

from project.db.models.reviews import ReviewModel


class ReviewDetailAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        review = await self.get_review()

        return [
            [
                await self.view.buttons.view_btn(
                    r['USER_DETAIL_ADMIN_VIEW'],
                    0,
                    page_num=self.view.callback.page_num,
                    view_params={'edit_keyboard': False},
                    params={'user_oid': review.user_oid},
                )
            ],
            [
                await self.view.buttons.view_btn(
                    r['REVIEWS_ADMIN_VIEW'],
                    0,
                    page_num=self.view.callback.page_num,
                    params={'query': self.view.callback.params.get('query')},
                )
            ],
        ]

    @async_lru_cache()
    async def get_review(self) -> Optional[ReviewModel]:
        review_oid = self.view.callback.params['review_oid']
        return await ReviewModel.manager().find_one(review_oid, raise_exception=False)

    @async_lru_cache()
    async def get_review_user(self) -> Optional[UserModel]:
        review = await self.get_review()
        if review is None:
            return None
        user_oid = review.user_oid
        return await get_user_model().manager().find_one(user_oid, raise_exception=False)

    async def get_keyboard_text(self) -> str:
        review_oid = self.view.callback.params['review_oid']
        review = await self.get_review()
        user = await self.get_review_user()
        if review is None:
            return f'Отзыв не найден: {review_oid}'
        text = ''
        text += f'oid: {review_oid}\n'
        text += f'user_oid: {review.user_oid}\n'
        text += f'user_id: {review.tg_user_id}\n'

        if user and user.username:
            text += f'username: @{user.username}'

        text += '\n\n'
        text += review.text
        return text


class ReviewDetailAdminView(BaseView):

    view_name = 'REVIEW_DETAIL_ADMIN_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Отзыв',
        'Отзыв',
    ]

    message_sender = ReviewDetailAdminMessageSender
