from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import get_user_model


class UserDetailAdminMessageSender(BaseMessageSender):

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry

        return [
            [
                await self.view.buttons.view_btn(
                    r['USERS_ADMIN_VIEW'],
                    0,
                    page_num=self.view.callback.page_num,
                    params={'query': self.view.callback.params.get('query')},
                )
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user_oid = self.view.callback.params['user_oid']
        user = await get_user_model().manager().find_one(user_oid, raise_exception=False)
        if user is None:
            return f'Пользователь не найден: {user_oid}'
        text = ''
        text += f'oid: {user_oid}\n'
        text += f'user_id: {user.user_id}\n'
        username = ''
        if user.username:
            username = f'@{user.username}'
        text += f'username: {username}\n'
        text += f'first_name: {user.first_name}\n'
        text += f'last_name: {user.last_name}\n'
        text += f'is_superuser: {user.is_superuser}\n'
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
