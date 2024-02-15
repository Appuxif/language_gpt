import asyncio
from typing import Any

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.core.bot import ParseMode, bot
from project.db.models.words import UserWordGroupModel, UserWordModel, WordGroupModel, WordModel


class CopyPublicGroupMessageSender(BaseMessageSender):
    """Add Public Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        cb = UserStateCb
        user = await self.view.request.get_user()

        if self.view.view_name in user.state.callbacks:
            return []

        callback = cb(
            view_name=self.view.view_name,
            params=self.view.callback.params,
            page_num=self.view.callback.page_num,
        )
        return [
            [await self.view.buttons.btn('Да', callback)],
            [
                await self.view.buttons.view_btn(
                    r['PUBLIC_GROUP_VIEW'], 1, page_num=self.view.callback.page_num, params=self.view.callback.params
                )
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        if self.view.request.callback and self.view.view_name in user.state.callbacks:
            return ''

        group_id = self.view.callback.params.get('group_id')
        groups = WordGroupModel.manager().filter({'_id': group_id})
        group: WordGroupModel = await groups.find_one()
        return f"Добавить подборку \"{group.name}\" в свой список для изучения?"


class CopyPublicGroupView(BaseView):
    """Отображение для добавления публичной подборки в свои"""

    view_name = 'COPY_PUBLIC_GROUP_VIEW'
    edit_keyboard = True
    labels = [
        'Подборка',
        '🚶 В Подборку',
        'Подборки',
    ]

    message_sender = CopyPublicGroupMessageSender

    async def redirect(self) -> BaseView | None:

        user = await self.request.get_user()
        r = self.route_resolver.routes_registry
        if self.request.callback is None:
            return None

        if self.view_name not in user.state.callbacks:
            check_cb = UserStateCb(
                id=self.view_name,
                view_name=self.view_name,
                page_num=1,
                params=self.callback.params,
            )
            await self.buttons.btn(check_cb.id, check_cb)
            return None

        group_id = self.callback.params.get('group_id')
        group = await WordGroupModel.manager().find_one(group_id)
        if not group.is_public:
            text = f'Подборка *{group.name}* больше не публичная'
            await bot.send_message(self.request.callback.message.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)
            return r['PUBLIC_GROUPS_VIEW'].view(
                self.request,
                callback=UserStateCb(view_name=r['PUBLIC_GROUPS_VIEW'].value, page_num=1, params=self.callback.params),
                edit_keyboard=False,
            )

        user_group = UserWordGroupModel(user_id=user.id, group_id=group_id)
        words = await WordModel.manager().by_wordgroup(group_id).filter({'is_active': True}).find_all()

        # TODO: add to manager insert_many method
        documents: list[dict[Any, Any]] = []
        for word in words:
            user_word = UserWordModel(user_id=user.id, group_id=group_id, word_id=word.id, is_active=True)
            documents.append(user_word.dict(by_alias=True, exclude={'id'}))
        await asyncio.gather(
            user_group.insert(),
            UserWordModel.manager().get_collection().insert_many(documents),
        )

        text = f'Подборка *{group.name}* добавлена'
        await bot.send_message(self.request.callback.message.chat.id, text, parse_mode=ParseMode.MARKDOWN.value)

        return r['USER_GROUP_VIEW'].view(
            self.request,
            callback=UserStateCb(view_name=r['USER_GROUP_VIEW'].value, page_num=1, params=self.callback.params),
            edit_keyboard=False,
        )
