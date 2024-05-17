from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import ParseMode, bot
from project.db.models.words import WordGroupModel


class PublishUserGroupMessageSender(BaseMessageSender):
    """Publish User Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()

        if self.view.view_name in user.state.callbacks:
            return []

        callback = cb(view_name=self.view.view_name, params=self.view.callback.params)
        return [
            [await self.view.buttons.btn('Да', callback)],
            [
                await self.view.buttons.view_btn(
                    r['USER_GROUP_VIEW'], 1, params=self.view.callback.params, page_num=self.view.callback.page_num
                )
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.request.callback and self.view.view_name in user.state.callbacks:
            return ''
        group = await WordGroupModel.manager().find_one(self.view.callback.params.get('group_id'))
        return (
            f'Опубликовать подборку {group.name}?'
            f'\n\nЭто действие нельзя отменить. '
            f'В опубликованных подборках нельзя добавлять или удалять слова. '
            f'Можно будет только учить существующие слова, прослушивать и смотреть примеры.'
        )


class PublishUserGroupView(BaseView):
    """Отображение публикации подборки пользователя"""

    view_name = 'PUBLISH_USER_GROUP_VIEW'
    edit_keyboard = True
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Опубликовать подборку?',
        '🌎 Опубликовать подборку',
    ]

    message_sender = PublishUserGroupMessageSender

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
        group.is_public = True
        await group.update()
        text = f'Подборка *{group.name}* опубликована'
        await bot.send_message(self.request.callback.message.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)

        return r['USER_GROUP_VIEW'].view(
            self.request,
            callback=UserStateCb(
                view_name=r['USER_GROUP_VIEW'].value,
                params=self.callback.params,
                page_num=self.callback.page_num,
            ),
            edit_keyboard=False,
        )
