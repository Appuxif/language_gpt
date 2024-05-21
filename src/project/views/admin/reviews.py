from datetime import timedelta
from typing import Any, TypedDict

import bson
from bson import ObjectId
from telebot.types import InlineKeyboardButton, InlineQueryResultBase
from telebot_views.base import BaseMessageSender, BaseView, InlineQueryResultSender
from telebot_views.dummy import DummyMessageSender
from telebot_views.models import UserStateCb
from telebot_views.models.cache import with_cache
from telebot_views.utils import now_utc

from project.db.models.reviews import ReviewModel, ReviewModelManager


class ReviewsAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        # pylint: disable=too-many-locals
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        page_num = self.view.callback.page_num or user.constants.get('REVIEWS_ADMIN_VIEW_PAGE_NUM') or 1
        user.constants['REVIEWS_ADMIN_VIEW_PAGE_NUM'] = page_num

        query = self.view.callback.params.get('query') or user.constants.get('REVIEWS_ADMIN_VIEW_QUERY')
        user.constants['REVIEWS_ADMIN_VIEW_QUERY'] = query
        manager = await self.get_manager()

        @with_cache(f'reviews_admin_view:{query}:{page_num}', 60)
        async def _inner() -> dict[str, Any]:
            _count = await manager.count()
            _reviews: list[ReviewModel] = await self.view.paginator.paginate(
                manager, page_num, _count, sort=[('_id', -1)]
            )
            return {'count': _count, 'reviews': [{**_review.dict(), '_id': _review.id} for _review in _reviews]}

        result = await _inner()
        count = result['count']
        reviews: list[ReviewModel] = [ReviewModel.parse_obj(review) for review in result['reviews']]

        reviews_list = []
        for review in reviews:
            callback = cb(
                view_name=r['REVIEW_DETAIL_ADMIN_VIEW'].value,
                params={'review_oid': review.id, 'query': query},
                page_num=page_num,
            )
            label = ' '.join(filter(None, (str(review.tg_user_id), review.text[:10] + '...')))
            btn = [await self.view.buttons.btn(label, callback)]
            reviews_list.append(btn)

        return [
            *reviews_list,
            *(await self.view.paginator.get_pagination(count, page_num)),
            [await self.view.buttons.view_btn(r['MAIN_ADMIN_VIEW'], 0)],
        ]

    async def get_manager(self) -> ReviewModelManager:

        user = await self.view.request.get_user()

        manager = ReviewModel.manager()

        query = self.view.callback.params.get('query') or user.constants.get('REVIEWS_ADMIN_VIEW_QUERY')
        if query:
            for typ in [int, ObjectId]:
                try:
                    query = typ(query)
                    break
                except (ValueError, TypeError, bson.errors.InvalidId):
                    continue
            else:
                query = None
                user.constants.pop('REVIEWS_ADMIN_VIEW_QUERY', None)

        if query:
            filters = []
            if isinstance(query, int):
                filters.append({'tg_user_id': query})
            elif isinstance(query, ObjectId):
                filters.append({'user_oid': query})
            manager = manager.filter({'$or': filters})
        return manager

    async def get_keyboard_text(self) -> str:

        manager = await self.get_manager()
        user = await self.view.request.get_user()
        text = (await count_reviews(manager))['text']

        if user.constants.get('REVIEWS_ADMIN_VIEW_QUERY'):
            text += '\n' + 'поиск: ' + str(user.constants['REVIEWS_ADMIN_VIEW_QUERY'])

        return text


class ReviewsAdminInlineSender(InlineQueryResultSender):
    cache_time = 1
    is_personal = True

    async def get_results(self) -> tuple[list[InlineQueryResultBase], str | None]:
        results, offset = [], None
        user = await self.view.request.get_user()

        query = self.view.request.inline.query.strip()
        self.view.callback.params['query'] = query
        user.constants['REVIEWS_ADMIN_VIEW_QUERY'] = query
        await self.view.message_sender(self.view).send()

        return results, offset


class ReviewsAdminView(BaseView):

    view_name = 'REVIEWS_ADMIN_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    ignore_inline_query = False
    labels = [
        '💬 Отзывы',
        '💬 Отзывы',
    ]

    message_sender = ReviewsAdminMessageSender
    inline_sender = ReviewsAdminInlineSender


class ReviewsAdminViewProxy(ReviewsAdminView):

    view_name = 'REVIEWS_ADMIN_VIEW_PROXY'
    message_sender = DummyMessageSender

    async def redirect(self) -> ReviewsAdminView:
        user = await self.request.get_user()
        user.constants.pop('REVIEWS_ADMIN_VIEW_QUERY', None)
        return ReviewsAdminView(self.request, self.callback)


class CountReviews(TypedDict):
    text: str


async def count_reviews(manager: ReviewModelManager) -> CountReviews:
    @with_cache(f'admin_count_reviews:{manager.document_filter}', 30)
    async def _inner() -> CountReviews:
        text = ''
        total = await manager.count()
        text += f'Всего отзывов: {total}\n'

        week = await manager.filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=7))}}).count()
        text += f'За прошедшую неделю: {week}\n'

        month = await manager.filter({'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=30))}}).count()
        text += f'За прошедший месяц: {month}\n'

        return CountReviews(text=text)

    return await _inner()
