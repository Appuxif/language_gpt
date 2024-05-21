import re
from datetime import timedelta
from typing import Any, TypedDict

from bson import ObjectId
from telebot.types import InlineKeyboardButton, InlineQueryResultBase
from telebot_views.base import BaseMessageSender, BaseView, InlineQueryResultSender
from telebot_views.dummy import DummyMessageSender
from telebot_views.models import UserModel, UserModelManager, UserStateCb, get_user_model
from telebot_views.models.cache import with_cache
from telebot_views.utils import now_utc


class UsersAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        # pylint: disable=too-many-locals
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        page_num = self.view.callback.page_num or user.constants.get('USERS_ADMIN_VIEW_PAGE_NUM') or 1
        user.constants['USERS_ADMIN_VIEW_PAGE_NUM'] = page_num

        query = self.view.callback.params.get('query') or user.constants.get('USERS_ADMIN_VIEW_QUERY')
        if len(query or '') < 3:
            query = ''
        user.constants['USERS_ADMIN_VIEW_QUERY'] = query
        self.view.callback.params['query'] = query
        manager = await self.get_manager()

        @with_cache(f'users_admin_view:{query}:{page_num}', 60)
        async def _inner() -> dict[str, Any]:
            _count = await manager.count()
            _users: list[UserModel] = await self.view.paginator.paginate(manager, page_num, _count)
            return {'count': _count, 'users': [{**_user.dict(), '_id': _user.id} for _user in _users]}

        result = await _inner()
        count = result['count']
        users: list[UserModel] = [get_user_model().parse_obj(user) for user in result['users']]

        users_list = []
        for user in users:
            callback = cb(
                view_name=r['USER_DETAIL_ADMIN_VIEW'].value,
                params={'user_oid': user.id, 'query': query},
                page_num=page_num,
            )
            btn = [await self.view.buttons.btn(_get_label(user), callback)]
            users_list.append(btn)

        return [
            *users_list,
            *(await self.view.paginator.get_pagination(count, page_num)),
            [InlineKeyboardButton('🔎 Поиск', switch_inline_query_current_chat='')],
            [await self.view.buttons.view_btn(r['MAIN_ADMIN_VIEW'], 0)],
        ]

    async def get_manager(self) -> UserModelManager:
        manager = get_user_model().manager()
        user = await self.view.request.get_user()
        query = self.view.callback.params.get('query') or user.constants.get('USERS_ADMIN_VIEW_QUERY')

        if query:
            try:
                int_query = int(query)
            except (ValueError, TypeError):
                int_query = None

            filters = []
            if query:
                if query == '[S]':
                    filters += [{'is_superuser': True}]
                elif query == '~[S]':
                    filters += [{'$or': [{'is_superuser': False}, {'is_superuser': None}]}]
                elif query == '[X]':
                    filters += [{'$or': [{'is_available': False}, {'is_available': None}]}]
                elif query == '~[X]':
                    filters += [{'is_available': True}]
                else:
                    try:
                        regex = re.compile(rf'^{query}', flags=re.IGNORECASE)
                        filters += [{'username': regex}, {'first_name': regex}, {'last_name': regex}]
                    except re.error:
                        pass
            if int_query:
                filters.append({'user_id': int_query})
            if filters:
                manager = manager.filter({'$or': filters})

        return manager

    async def get_keyboard_text(self) -> str:
        manager = await self.get_manager()
        user = await self.view.request.get_user()
        text = (await count_users(manager))['text']

        if user.constants.get('USERS_ADMIN_VIEW_QUERY'):
            text += '\n' + 'поиск: ' + user.constants['USERS_ADMIN_VIEW_QUERY']

        text += '\n\nФильтры:\n'
        text += '[S] - админ\n~[S] - не админ\n'
        text += '[X] - не доступный\n~[X] - доступный'

        return text


class UsersAdminInlineSender(InlineQueryResultSender):
    cache_time = 1
    is_personal = True

    async def get_results(self) -> tuple[list[InlineQueryResultBase], str | None]:
        results, offset = [], None
        user = await self.view.request.get_user()

        query = self.view.request.inline.query.strip()
        self.view.callback.params['query'] = query
        user.constants['USERS_ADMIN_VIEW_QUERY'] = query
        await self.view.message_sender(self.view).send()

        return results, offset


class UsersAdminView(BaseView):

    view_name = 'USERS_ADMIN_VIEW'
    delete_income_messages = True
    ignore_income_messages = True
    ignore_inline_query = False
    labels = [
        '🕵️‍♂️ Пользователи',
        '🕵️‍♂️ Пользователи',
    ]

    message_sender = UsersAdminMessageSender
    inline_sender = UsersAdminInlineSender


class UsersAdminViewProxy(UsersAdminView):

    view_name = 'USERS_ADMIN_VIEW_PROXY'
    message_sender = DummyMessageSender

    async def redirect(self) -> UsersAdminView:
        user = await self.request.get_user()
        user.constants.pop('USERS_ADMIN_VIEW_QUERY', None)
        return UsersAdminView(self.request, self.callback)


class CountUsers(TypedDict):
    text: str


async def count_users(manager: UserModelManager) -> CountUsers:
    @with_cache(f'admin_count_users:{manager.document_filter}', 120)
    async def _inner() -> CountUsers:
        text = ''
        total_users = await manager.count()
        text += f'Всего пользователей: {total_users}\n'

        week_users = await manager.filter(
            {'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=7))}}
        ).count()
        text += f'За прошедшую неделю: {week_users}\n'

        month_users = await manager.filter(
            {'_id': {'$gte': ObjectId.from_datetime(now_utc() - timedelta(days=30))}}
        ).count()
        text += f'За прошедший месяц: {month_users}\n'

        active_now = await manager.filter({'state.created_at': {'$gte': now_utc() - timedelta(seconds=30)}}).count()
        text += f'Сейчас активны: {active_now}\n'

        active_today = await manager.filter(
            {'state.created_at': {'$gte': now_utc() - timedelta(seconds=3600 * 24)}}
        ).count()
        text += f'Сегодня активны: {active_today}\n'
        return CountUsers(text=text)

    return await _inner()


def _get_label(user: UserModel) -> str:
    label = ' '.join(
        filter(
            None,
            (str(user.user_id), user.username, user.first_name, user.last_name),
        )
    )

    suffix = ''
    if user.is_superuser:
        suffix += '[S]'
    if not user.is_available:
        suffix += '[X]'
    if suffix:
        suffix = ' ' + suffix

    return label + suffix
