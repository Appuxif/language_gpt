from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import ParseMode, bot
from project.db.models.words import UserWordGroupModel, WordGroupModel


class CreateUserGroupMessageSender(BaseMessageSender):
    """Create User Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        if self.view.view_name in user.state.callbacks:
            return []
        return [
            [await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.request.msg and self.view.view_name in user.state.callbacks:
            return ''
        return 'Введи название подборки:'


class CreateUserGroupView(BaseView):
    """Отображение создания подборки пользователя"""

    view_name = 'CREATE_USER_GROUP_VIEW'
    edit_keyboard = False
    delete_income_messages = False
    ignore_income_messages = False
    labels = [
        'Создать подборку?',
        '📝 Создать подборку',
    ]

    message_sender = CreateUserGroupMessageSender

    async def redirect(self) -> BaseView | None:

        user = await self.request.get_user()
        r = self.route_resolver.routes_registry

        if self.view_name not in user.state.callbacks:
            check_cb = UserStateCb(id=self.view_name, view_name=self.view_name, page_num=1)
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        if self.request.msg is None:
            return None

        if len(self.request.msg.text) > 20:
            await bot.send_message(self.request.msg.chat.id, 'Не больше двадцати символов в названии группы')
            return None

        group = WordGroupModel(name=self.request.msg.text, is_public=False)
        await group.insert()

        user_group = UserWordGroupModel(user_id=user.id, group_id=group.id)
        await user_group.insert()

        text = f'Подборка *{self.request.msg.text}* создана успешно'
        msg = await bot.send_message(self.request.msg.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)
        self.user_states.add_message_to_delete(msg.chat.id, msg.message_id)

        self.callback.view_name = r['USER_GROUP_VIEW'].value
        self.callback.params['group_id'] = group.id
        return r['USER_GROUP_VIEW'].view(
            self.request,
            callback=self.callback,
            edit_keyboard=False,
            ignore_income_messages=False,
        )
