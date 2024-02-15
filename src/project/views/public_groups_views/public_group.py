import asyncio
from typing import Optional

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.db.models.words import UserWordGroupModel, WordGroupModel, WordModel


class PublicGroupMessageSender(BaseMessageSender):
    """Public Group Message Sender"""

    user_group: Optional[UserWordGroupModel] = None

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        group_id = self.view.callback.params.get('group_id')
        page_num = self.view.callback.page_num or 1
        user = await self.view.request.get_user()

        manager = WordModel.manager().by_wordgroup(group_id)
        user_words: list[WordModel] = await self.view.paginator.paginate(manager, page_num)
        self.user_group = (
            await UserWordGroupModel.manager().by_user(user.id).by_wordgroup(group_id).find_one(raise_exception=False)
        )

        # Вывод слов на клавиатуре, если слова вообще есть
        async def prepare_btn(word: WordModel) -> list[InlineKeyboardButton]:
            callback = cb(
                view_name=r['PUBLIC_WORD_VIEW'].value,
                params={'group_id': group_id, 'word_id': word.id},
                page_num=page_num,
            )
            return [await self.view.buttons.btn(word.label, callback)]

        words_btns = await asyncio.gather(*map(prepare_btn, user_words))
        additional_btns = []
        if not self.user_group:
            additional_btns.append(
                [
                    await self.view.buttons.btn(
                        '💾 Добавить к себе',
                        UserStateCb(
                            view_name=r['COPY_PUBLIC_GROUP_VIEW'].view.view_name,
                            page_num=self.view.callback.page_num,
                            params=self.view.callback.params,
                        ),
                    ),
                ]
            )

        return [
            *words_btns,
            *(await self.view.paginator.get_pagination(await manager.count(), page_num, params={'group_id': group_id})),
            *additional_btns,
            [await self.view.buttons.view_btn(r['PUBLIC_GROUPS_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        group_id = self.view.callback.params.get('group_id')
        groups = WordGroupModel.manager().filter({'_id': group_id})
        group: WordGroupModel = await groups.find_one()
        words_total = await WordModel.manager().by_wordgroup(group_id).count()
        text = f'{self.view.labels[0]} {group.name}'
        if self.user_group:
            text += ' [добавлено]'
        if words_total:
            text += f'\nСлов: {words_total}'
        return text


class PublicGroupView(BaseView):
    """Отображение списка слов в публичной подборке"""

    view_name = 'PUBLIC_GROUP_VIEW'
    edit_keyboard = True
    labels = [
        'Подборка',
        '🚶 В Подборку',
        'Подборки',
    ]

    message_sender = PublicGroupMessageSender
