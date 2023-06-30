from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import ParseMode, bot
from project.db.models.words import WordGroupModel


class DeleteUserGroupMessageSender(BaseMessageSender):
    """Delete User Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()

        if self.view.view_name in user.state.callbacks:
            return []

        callback = cb(view_name=self.view.view_name, params={'group_id': self.view.callback.params.get('group_id')})
        return [
            [await self.view.buttons.btn('Да', callback)],
            [await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.request.callback and self.view.view_name in user.state.callbacks:
            return ''
        group = await WordGroupModel.manager().find_one(self.view.callback.params.get('group_id'))
        return f'Удалить подборку {group.name}?'


class DeleteUserGroupView(BaseView):
    """Отображение удаления подборки пользователя"""

    view_name = 'DELETE_USER_GROUP_VIEW'
    edit_keyboard = True
    labels = [
        'Удалить подборку?',
        '♻ Удалить подборку',
    ]

    message_sender = DeleteUserGroupMessageSender

    async def redirect(self) -> BaseView | None:

        user = await self.request.get_user()
        r = self.route_resolver.routes_registry
        if self.request.callback is None:
            return None

        if self.view_name not in user.state.callbacks:
            check_cb = UserStateCb(id=self.view_name, view_name=self.view_name, page_num=1)
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        group_id = self.callback.params.get('group_id')
        group = await WordGroupModel.manager().find_one(group_id)
        await group.delete()
        text = f'Подборка *{group.name}* удалена'
        await bot.send_message(self.request.callback.message.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)

        return r['USER_GROUPS_VIEW'].view(
            self.request,
            callback=UserStateCb(view_name=r['USER_GROUPS_VIEW'].value),
            edit_keyboard=False,
        )
