import asyncio

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.db.models.words import WordGroupModel


class PublicGroupsMessageSender(BaseMessageSender):
    """Public Groups Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        page_num = self.view.callback.page_num or user.constants.get('PUBLIC_GROUPS_VIEW_PAGE_NUM') or 1
        user.constants['PUBLIC_GROUPS_VIEW_PAGE_NUM'] = page_num

        manager = WordGroupModel.manager().filter({'is_public': True})
        groups_count = await manager.count()
        groups: list[WordGroupModel] = await self.view.paginator.paginate(manager, page_num, groups_count)

        async def prepare_btn(group: WordGroupModel) -> list[InlineKeyboardButton]:
            callback = cb(view_name=r['PUBLIC_GROUP_VIEW'].value, params={'group_id': group.id})
            return [await self.view.buttons.btn(group.name, callback)]

        return [
            *(await asyncio.gather(*map(prepare_btn, groups))),
            *(await self.view.paginator.get_pagination(groups_count, page_num)),
            [await self.view.buttons.view_btn(r['MAIN_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        return self.view.labels[0]


class PublicGroupsView(BaseView):
    """Отображение публичных подборок"""

    view_name = 'PUBLIC_GROUPS_VIEW'
    edit_keyboard = True
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Публичные подборки',
        '🌎 В публичные подборки',
    ]

    message_sender = PublicGroupsMessageSender
