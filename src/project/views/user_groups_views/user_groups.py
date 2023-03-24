from telebot.types import InlineKeyboardButton

from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import UserWordGroupModel


class UserGroupsMessageSender(BaseMessageSender):
    """User Groups Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        page_num = self.view.callback.page_num or 1

        manager = UserWordGroupModel.manager().by_user(user.id)
        groups_count = await manager.count()
        groups: list[UserWordGroupModel] = await self.view.paginator.paginate(manager, page_num)

        groups_list = []
        for group in groups:
            callback = cb(view_name=r['USER_GROUP_VIEW'].value, group_id=group.group_id)
            btn = [await self.view.buttons.btn((await group.wordgroup()).name, callback)]
            groups_list.append(btn)

        return [
            *groups_list,
            *(await self.view.paginator.get_pagination(groups_count, page_num)),
            [await self.view.buttons.view_btn(r['CREATE_USER_GROUP_VIEW'], 1)],
            [await self.view.buttons.view_btn(r['MAIN_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        return self.view.labels[0]


class UserGroupsView(BaseView):
    """Отображение моих подборок"""

    view_name = 'USER_GROUPS_VIEW'
    edit_keyboard = True
    labels = [
        'Мои подборки',
        'В мои подборки',
    ]

    message_sender = UserGroupsMessageSender
