from functools import partial
from typing import Optional

from asyncio_functools.lru_cache import async_lru_cache
from bson import ObjectId
from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserModel, UserStateCb, get_user_model

from project.services import reviews

SEE_REVIEWS_CB_ID = 'see_reviews'


class UserDetailAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry

        cb = partial(
            UserStateCb,
            view_name=self.view.view_name,
            page_num=self.view.callback.page_num,
            params=self.view.callback.params,
        )

        review_cb = cb(id='set_review')
        review_cb_text = 'Открыть кнопку "Отзывы"'
        see_reviews_cb = cb(id=SEE_REVIEWS_CB_ID)

        user = await self.get_user()
        if self.view.callback.id == review_cb.id:
            reviews.set_waiting_for_review(user)
            await reviews.save_reviews_info(user)

        elif self.view.callback.id == SEE_REVIEWS_CB_ID:
            return []

        review_cb_text = '✗✓'[reviews.is_waiting_for_review(user)] + review_cb_text

        return [
            [await self.view.buttons.btn(review_cb_text, review_cb)],
            [await self.view.buttons.btn('Посмотреть все отзывы', see_reviews_cb)],
            [
                await self.view.buttons.view_btn(
                    r['USERS_ADMIN_VIEW'],
                    0,
                    page_num=self.view.callback.page_num,
                    params={'query': self.view.callback.params.get('query')},
                )
            ],
        ]

    @async_lru_cache()
    async def get_user(self) -> Optional[UserModel]:
        user_oid = self.view.callback.params['user_oid']
        user = await get_user_model().manager().find_one(user_oid, raise_exception=False)
        if user is None:
            return None
        req_user = await self.view.request.get_user()
        if req_user.id == user.id:
            user = req_user
        return user

    async def get_keyboard_text(self) -> str:
        if self.view.callback.id == SEE_REVIEWS_CB_ID:
            return ''

        user_oid = self.view.callback.params['user_oid']
        user = await self.get_user()
        if user is None:
            return f'Пользователь не найден: {user_oid}'
        text = ''
        text += f'oid: {user_oid}\n'
        text += f'user_id: {user.user_id}\n'
        username = ''
        if user.username:
            username = f'@{user.username}'
        text += f'username: {username}\n'
        fields = set(user.__fields__) - {'username', 'user_id', 'constants', 'state', 'id'}
        for field in sorted(fields):
            if (value := getattr(user, field)) and isinstance(value, (str, int, float, bool, ObjectId)):
                text += f'{field}: {value}\n'
        return text


class UserDetailAdminView(BaseView):

    view_name = 'USER_DETAIL_ADMIN_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Пользователь',
        'Пользователь',
    ]

    message_sender = UserDetailAdminMessageSender

    async def redirect(self) -> Optional['BaseView']:
        r = self.route_resolver.routes_registry

        if self.callback.id == SEE_REVIEWS_CB_ID:
            user = await self.request.get_user()
            user.constants['REVIEWS_ADMIN_VIEW_QUERY'] = self.callback.params['user_oid']
            return r['REVIEWS_ADMIN_VIEW'].view(self.request, UserStateCb(view_name='REVIEWS_ADMIN_VIEW'))
        return None
